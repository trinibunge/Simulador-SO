import threading
import multiprocessing as mp
import queue
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Paciente:
    """Representa un proceso (paciente o app) en el simulador."""
    pid: int
    name: str
    priority: int          # 1 = crítico, 10 = leve
    state: str = "READY"   # READY | RUNNING | BLOCKED
    symbol: str = "🤒"
    cpu_used: int = 0      # ticks de quantum (mantengo por compatibilidad con UI Hospital)
    burst: int = 8
    holding: list = field(default_factory=list)
    waiting_for: Optional[str] = None

    # ─── Instrumentación para métricas reales ───
    kind: str = "patient"  # "patient" | "app". Las apps no terminan por burst.
    admitted_at: float = 0.0
    first_run_at: Optional[float] = None
    completed_at: Optional[float] = None
    last_state_change: float = 0.0
    ready_acc: float = 0.0     # tiempo total en READY (segundos)
    running_acc: float = 0.0   # tiempo total en RUNNING (segundos)
    blocked_acc: float = 0.0   # tiempo total en BLOCKED (segundos)

    # Métricas derivadas (las usa metrics.py — no mutan el objeto)
    def turnaround(self) -> float:
        end = self.completed_at if self.completed_at is not None else time.time()
        return max(0.0, end - self.admitted_at)

    def response_time(self) -> float:
        if self.first_run_at is None:
            return 0.0
        return max(0.0, self.first_run_at - self.admitted_at)

    def waiting_time(self) -> float:
        return self.ready_acc


class HospitalState:
    """
    Estado global del hospital-SO.

    Sincronización REAL:
    - lock (RLock): exclusión mutua sobre los pacientes y acumuladores.
    - ready_cv (Condition): el scheduler duerme acá cuando no hay READY;
      cualquier transición a READY le hace notify().
    - cpu_sem (Semaphore): N doctores disponibles a la vez.
    - resources (Locks): Quirófano y Cirujano, uno a la vez.
    - log_in_queue / log_out_queue (multiprocessing.Queue):
      IPC con el proceso del demonio de logging.
    - logs (queue.Queue): cola local que la UI consume; un thread "bridge"
      mueve mensajes desde log_out_queue hacia esta cola intra-proceso.
    - pharmacy_queue (Queue acotada): productor-consumidor de medicamentos.
    """

    PHARMACY_CAPACITY = 8

    def __init__(self, num_cpus: int = 2):
        self.lock = threading.RLock()
        self.ready_cv = threading.Condition(self.lock)

        self.num_cpus = num_cpus
        self.cpu_sem = threading.Semaphore(num_cpus)

        self.resources: Dict[str, threading.Lock] = {
            "QUIROFANO": threading.Lock(),
            "CIRUJANO":  threading.Lock(),
        }
        self.resource_owner: Dict[str, Optional[int]] = {k: None for k in self.resources}
        self.resource_waiters: Dict[str, list] = {k: [] for k in self.resources}

        self.pid_counter = 1
        self.pacientes: Dict[int, Paciente] = {}

        # Histórico de procesos terminados (solo pacientes, para métricas)
        self.completed_history: List[Paciente] = []
        self.simulation_start = time.time()

        # ─── Logging IPC ───
        self.log_in_queue: "mp.Queue" = mp.Queue()
        self.log_out_queue: "mp.Queue" = mp.Queue()
        self.logs: "queue.Queue[str]" = queue.Queue()
        self._log_bridge_thread: Optional[threading.Thread] = None
        self.log_process = None

        # ─── Farmacia ───
        self.pharmacy_queue: "queue.Queue[str]" = queue.Queue(maxsize=self.PHARMACY_CAPACITY)
        self.pharmacy_running = False
        self.pharmacy_stats = {"producidos": 0, "consumidos": 0}

        self.running = True
        self.scheduler_mode = "ROUNDROBIN"
        self.chaos_mode = False
        self.deadlock_demo = False
        self.deadlock_active = False
        self.deadlock_resolve_now = False
        self.deadlock_since: Optional[float] = None
        self.ram_limit = 12
        self.clock_tick = 0

    # ─────────────────────────────────────────────────────────────────────
    #  Transición de estado central (instrumentada)
    # ─────────────────────────────────────────────────────────────────────

    def _set_state(self, paciente: Paciente, new_state: str, now: Optional[float] = None):
        """
        Cambia el estado de un paciente acumulando el tiempo que pasó en el
        estado anterior. CALLER DEBE TENER self.lock.

        Es la única forma legítima de cambiar paciente.state. Si lo hacés
        manualmente (paciente.state = "..."), las métricas mienten.
        """
        if now is None:
            now = time.time()

        elapsed = max(0.0, now - paciente.last_state_change)

        if paciente.state == "READY":
            paciente.ready_acc += elapsed
        elif paciente.state == "RUNNING":
            paciente.running_acc += elapsed
        elif paciente.state == "BLOCKED":
            paciente.blocked_acc += elapsed

        # Primera vez que arranca CPU
        if new_state == "RUNNING" and paciente.first_run_at is None:
            paciente.first_run_at = now

        paciente.state = new_state
        paciente.last_state_change = now

    # ─────────────────────────────────────────────────────────────────────
    #  Logging
    # ─────────────────────────────────────────────────────────────────────

    def start_log_bridge(self):
        if self._log_bridge_thread is not None:
            return

        def bridge():
            while self.running:
                try:
                    msg = self.log_out_queue.get(timeout=0.3)
                except Exception:
                    continue
                if msg is None:
                    break
                try:
                    self.logs.put(msg, timeout=0.1)
                except Exception:
                    pass

        self._log_bridge_thread = threading.Thread(target=bridge, daemon=True)
        self._log_bridge_thread.start()

    def log(self, tag: str, message: str):
        try:
            self.log_in_queue.put((tag, message), timeout=0.1)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────
    #  Procesos / Scheduling
    # ─────────────────────────────────────────────────────────────────────

    def admitir(self, name: str, priority: int, burst: int = 8,
                kind: str = "patient", symbol: Optional[str] = None):
        """
        Registra un nuevo proceso (paciente o aplicación) en el sistema.

        - kind="patient": termina cuando cpu_used >= burst
        - kind="app":     nunca termina por burst (es una aplicación interactiva
                          que compite por la CPU mientras esté abierta)
        """
        with self.ready_cv:
            if len(self.pacientes) >= self.ram_limit:
                self.log("HOSPITAL", "Sala llena. No se admiten más pacientes.")
                return None

            pid = self.pid_counter
            self.pid_counter += 1

            if symbol is None:
                if kind == "app":
                    symbol = "🖥️"
                else:
                    symbol = "🚨" if priority <= 2 else ("🤕" if priority <= 5 else "🤒")

            now = time.time()
            paciente = Paciente(
                pid=pid, name=name, priority=priority,
                state="READY", symbol=symbol, burst=burst, kind=kind,
                admitted_at=now, last_state_change=now,
            )
            self.pacientes[pid] = paciente

            if kind == "app":
                self.log("APP",
                    f"'{name}' se registra como proceso (PID {pid}, prio {priority})")
            else:
                self.log("ADMIT",
                    f"{name} admitido (PID {pid}, gravedad {priority})")

            self.ready_cv.notify_all()
            return paciente

    def dar_alta(self, target):
        with self.lock:
            for pid, paciente in list(self.pacientes.items()):
                if paciente.name == target or str(paciente.pid) == str(target):
                    now = time.time()
                    # cerrar acumuladores del estado actual
                    self._set_state(paciente, paciente.state, now)
                    paciente.completed_at = now

                    for res in list(paciente.holding):
                        self._force_release(pid, res)

                    del self.pacientes[pid]

                    if paciente.kind == "app":
                        self.log("APP",
                            f"'{paciente.name}' (PID {pid}) cerrada por el usuario")
                    else:
                        # archivar paciente terminado para métricas
                        self.completed_history.append(paciente)
                        if len(self.completed_history) > 200:
                            self.completed_history = self.completed_history[-200:]
                        self.log("ALTA",
                            f"{paciente.name} (PID {pid}) dado de alta "
                            f"· esperó {paciente.waiting_time():.1f}s")
                    return True
        self.log("WARN", f"No existe paciente {target}")
        return False

    def set_mode(self, mode: str):
        mode = mode.upper()
        if mode in ("ROUNDROBIN", "PRIORITY"):
            self.scheduler_mode = mode
            label = "orden de llegada" if mode == "ROUNDROBIN" else "por gravedad"
            self.log("TRIAGE", f"Atención: {label}")
            return True
        return False

    def get_pacientes(self) -> List[Paciente]:
        """Devuelve TODOS los procesos (pacientes + apps). Compat con UI vieja."""
        with self.lock:
            return list(self.pacientes.values())

    def get_active_patients(self) -> List[Paciente]:
        """Solo procesos kind='patient' — para la app Hospital."""
        with self.lock:
            return [p for p in self.pacientes.values() if p.kind == "patient"]

    def notify_ready(self):
        with self.ready_cv:
            self.ready_cv.notify_all()

    # ─────────────────────────────────────────────────────────────────────
    #  Recursos
    # ─────────────────────────────────────────────────────────────────────

    def request_resource(self, pid: int, res_name: str, timeout: float = 0.3) -> bool:
        if res_name not in self.resources:
            return False

        with self.lock:
            paciente = self.pacientes.get(pid)
            if not paciente:
                return False
            paciente.waiting_for = res_name
            self._set_state(paciente, "BLOCKED")
            if pid not in self.resource_waiters[res_name]:
                self.resource_waiters[res_name].append(pid)
            self.log("RECURSO", f"{paciente.name} solicita {res_name}")

        got = self.resources[res_name].acquire(timeout=timeout)

        with self.ready_cv:
            paciente = self.pacientes.get(pid)
            if not paciente:
                if got:
                    self.resources[res_name].release()
                return False
            if pid in self.resource_waiters[res_name]:
                self.resource_waiters[res_name].remove(pid)
            if got:
                self.resource_owner[res_name] = pid
                paciente.holding.append(res_name)
                paciente.waiting_for = None
                self._set_state(paciente, "READY")
                self.log("RECURSO", f"{paciente.name} obtuvo {res_name}")
                self.ready_cv.notify_all()
                return True
            else:
                self.log("RECURSO", f"{paciente.name} bloqueado esperando {res_name}")
                return False

    def release_resource(self, pid: int, res_name: str):
        with self.lock:
            paciente = self.pacientes.get(pid)
            if not paciente or res_name not in paciente.holding:
                return
            paciente.holding.remove(res_name)
            self.resource_owner[res_name] = None
            self.log("RECURSO", f"{paciente.name} libera {res_name}")
        try:
            self.resources[res_name].release()
        except RuntimeError:
            pass

    def _force_release(self, pid: int, res_name: str):
        if self.resource_owner.get(res_name) == pid:
            self.resource_owner[res_name] = None
            try:
                self.resources[res_name].release()
            except RuntimeError:
                pass

    # ─────────────────────────────────────────────────────────────────────
    #  Deadlock
    # ─────────────────────────────────────────────────────────────────────

    def detect_deadlock(self) -> Optional[list]:
        with self.lock:
            edges: Dict[int, list] = {}
            for pid, paciente in self.pacientes.items():
                if paciente.waiting_for:
                    owner = self.resource_owner.get(paciente.waiting_for)
                    if owner is not None and owner != pid:
                        edges.setdefault(pid, []).append(owner)

            for start in edges:
                stack = [(start, [start])]
                while stack:
                    node, path = stack.pop()
                    for nxt in edges.get(node, []):
                        if nxt in path:
                            cycle = path[path.index(nxt):] + [nxt]
                            return cycle
                        stack.append((nxt, path + [nxt]))
        return None

    def break_deadlock(self, cycle: list):
        with self.lock:
            victims = [self.pacientes[p] for p in cycle if p in self.pacientes]
            if not victims:
                return
            victim = max(victims, key=lambda p: p.priority)
        self.log("DEADLOCK",
                 f"Resolviendo: {victim.name} es derivado a otro hospital")
        self.dar_alta(victim.pid)
        self.deadlock_active = False

    # ─────────────────────────────────────────────────────────────────────
    #  Shutdown
    # ─────────────────────────────────────────────────────────────────────

    def shutdown(self):
        self.running = False
        self.pharmacy_running = False
        try:
            with self.ready_cv:
                self.ready_cv.notify_all()
        except Exception:
            pass
        try:
            self.log_in_queue.put(None, timeout=0.5)
        except Exception:
            pass