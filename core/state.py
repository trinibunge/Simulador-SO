import threading
import multiprocessing as mp
import queue
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Paciente:
    """Representa un proceso (paciente) en el simulador."""
    pid: int
    name: str
    priority: int          # 1 = crítico, 10 = leve
    state: str = "READY"   # READY | RUNNING | BLOCKED
    symbol: str = "🤒"
    cpu_used: int = 0
    burst: int = 8
    holding: list = field(default_factory=list)
    waiting_for: Optional[str] = None


class HospitalState:
    """
    Estado global del hospital-SO.

    Sincronización REAL:
    - lock (RLock): exclusión mutua sobre los pacientes.
    - ready_cv (Condition): el scheduler duerme acá cuando no hay READY;
      cualquier transición a READY le hace notify().  Reemplaza el viejo
      busy-wait con time.sleep().
    - cpu_sem (Semaphore): N doctores disponibles a la vez.
    - resources (Locks): Quirófano y Cirujano, uno a la vez.
    - log_in_queue / log_out_queue (multiprocessing.Queue):
      IPC con el proceso del demonio de logging.
    - logs (queue.Queue): cola local que la UI consume; un thread "bridge"
      mueve mensajes desde log_out_queue (cruzando el límite de proceso) a
      esta cola intra-proceso, así la UI no tiene que saber de multiprocessing.
    - pharmacy_queue (Queue acotada): productor-consumidor de medicamentos.
    """

    PHARMACY_CAPACITY = 8

    def __init__(self, num_cpus: int = 2):
        self.lock = threading.RLock()
        # Condition variable: el scheduler espera acá cuando no hay READY.
        # Comparte el mismo RLock que protege a pacientes, así notify() es
        # consistente con cualquier cambio de estado.
        self.ready_cv = threading.Condition(self.lock)

        self.num_cpus = num_cpus
        self.cpu_sem = threading.Semaphore(num_cpus)

        # Solo dos recursos: los del deadlock
        self.resources: Dict[str, threading.Lock] = {
            "QUIROFANO": threading.Lock(),
            "CIRUJANO":  threading.Lock(),
        }
        self.resource_owner: Dict[str, Optional[int]] = {k: None for k in self.resources}
        self.resource_waiters: Dict[str, list] = {k: [] for k in self.resources}

        self.pid_counter = 1
        self.pacientes: Dict[int, Paciente] = {}

        # ─── Logging IPC: dos colas que cruzan al proceso del daemon ───
        # Estas son mp.Queue (no queue.Queue): viajan entre procesos.
        self.log_in_queue: "mp.Queue" = mp.Queue()    # padre -> daemon
        self.log_out_queue: "mp.Queue" = mp.Queue()   # daemon -> padre

        # La UI consume de esta cola intra-proceso (más simple para Tkinter).
        # Un thread "bridge" la alimenta desde log_out_queue.
        self.logs: "queue.Queue[str]" = queue.Queue()
        self._log_bridge_thread: Optional[threading.Thread] = None

        # ─── Farmacia: productor-consumidor clásico con buffer acotado ───
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
    #  Logging
    # ─────────────────────────────────────────────────────────────────────

    def start_log_bridge(self):
        """
        Arranca un thread que mueve mensajes desde log_out_queue (mp.Queue,
        viene del proceso del daemon) hacia self.logs (queue.Queue local
        que la UI consume).  Sin esto, la UI tendría que hablar mp.Queue.
        """
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
        """Envía el evento al proceso del demonio de logging vía IPC."""
        try:
            self.log_in_queue.put((tag, message), timeout=0.1)
        except Exception:
            # Si la cola está saturada, dropeamos el log antes que bloquear
            # un hilo del kernel. Es un trade-off típico de loggers.
            pass

    # ─────────────────────────────────────────────────────────────────────
    #  Procesos / Scheduling
    # ─────────────────────────────────────────────────────────────────────

    def admitir(self, name: str, priority: int, burst: int = 8):
        with self.ready_cv:  # equivale a self.lock + notify() abajo
            if len(self.pacientes) >= self.ram_limit:
                self.log("HOSPITAL", "Sala llena. No se admiten más pacientes.")
                return None
            pid = self.pid_counter
            self.pid_counter += 1
            symbol = "🚨" if priority <= 2 else ("🤕" if priority <= 5 else "🤒")
            paciente = Paciente(pid=pid, name=name, priority=priority,
                                state="READY", symbol=symbol, burst=burst)
            self.pacientes[pid] = paciente
            self.log("ADMIT", f"{name} admitido (PID {pid}, gravedad {priority})")
            # Despertar al scheduler: hay un nuevo READY
            self.ready_cv.notify_all()
            return paciente

    def dar_alta(self, target):
        with self.lock:
            for pid, paciente in list(self.pacientes.items()):
                if paciente.name == target or str(paciente.pid) == str(target):
                    for res in list(paciente.holding):
                        self._force_release(pid, res)
                    del self.pacientes[pid]
                    self.log("ALTA", f"{paciente.name} (PID {pid}) dado de alta")
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
        with self.lock:
            return list(self.pacientes.values())

    def notify_ready(self):
        """Despierta al scheduler.  Llamar después de poner un proceso en READY."""
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
            paciente.state = "BLOCKED"
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
                paciente.state = "READY"
                self.log("RECURSO", f"{paciente.name} obtuvo {res_name}")
                # Volvió a READY: despertar al scheduler
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
        # Despertar a cualquier hilo bloqueado en la CV
        try:
            with self.ready_cv:
                self.ready_cv.notify_all()
        except Exception:
            pass
        # Señal de fin al proceso del daemon
        try:
            self.log_in_queue.put(None, timeout=0.5)
        except Exception:
            pass