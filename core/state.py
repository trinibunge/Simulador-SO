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

        # Histórico de procesos terminados (pacientes Y apps, para métricas del sistema)
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

        # ─── Historia Clínica (Lectores-Escritores Courtois 1971) ───
        # write_lock lo toma el escritor o el PRIMER lector.
        # readers_lock protege el contador de lectores.
        self.historia_write_lock = threading.Lock()
        self.historia_readers_lock = threading.Lock()
        self.historia_reader_count = 0
        self.historia_record = (
            "Temp: 36.8°C · PA: 120/80 · FC: 72 bpm · Sin novedades"
        )
        self.historia_history: List[str] = []
        # PID → nombre (para que la UI sepa quién está leyendo/escribiendo)
        self.historia_active_readers: Dict[int, str] = {}
        self.historia_active_writer: Optional[str] = None
        self.historia_waiting_writers: Dict[int, str] = {}

        self.running = True
        self.scheduler_mode = "ROUNDROBIN"
        self.chaos_mode = False
        self.deadlock_demo = False
        self.deadlock_active = False
        self.deadlock_resolve_now = False
        self.deadlock_since: Optional[float] = None
        self.ram_limit = 12
        self.clock_tick = 0

    # ─────────────────────────────────────────────────────────────────
    #  Transición de estado central (instrumentada)
    # ─────────────────────────────────────────────────────────────────

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

    # ─────────────────────────────────────────────────────────────────
    #  Logging
    # ─────────────────────────────────────────────────────────────────

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

    # ─────────────────────────────────────────────────────────────────
    #  Procesos / Scheduling
    # ─────────────────────────────────────────────────────────────────

    def admitir(self, name: str, priority: int, burst: int = 8,
                kind: str = "patient", symbol: Optional[str] = None):
        """
        Registra un nuevo proceso (paciente o aplicación) en el sistema.

        - kind="patient": termina cuando cpu_used >= burst
        - kind="app":     nunca termina por burst (es una aplicación interactiva
                          que compite por la CPU mientras esté abierta)
        """
        with self.ready_cv:
            # Las apps NO compiten por la sala de espera del hospital.
            # Una app es un proceso del SO ficticio (Snake, Asistente), no
            # un paciente físico que ocupe cama. Si limitáramos las apps al
            # ram_limit, un hospital lleno volvería las apps no-abribles —
            # exactamente al revés del modelo: las apps siempre pueden correr,
            # los pacientes son los que llenan la sala.
            if kind == "patient" and len(self.pacientes) >= self.ram_limit:
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

                    # Archivar TODOS los procesos terminados (apps + pacientes)
                    # para que las métricas reflejen al sistema completo, no
                    # solo el hospital.
                    self.completed_history.append(paciente)
                    if len(self.completed_history) > 200:
                        self.completed_history = self.completed_history[-200:]

                    if paciente.kind == "app":
                        self.log("APP",
                            f"'{paciente.name}' (PID {pid}) cerrada por el usuario")
                    else:
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

    # ─────────────────────────────────────────────────────────────────
    #  Recursos
    # ─────────────────────────────────────────────────────────────────

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

    # ─────────────────────────────────────────────────────────────────
    #  Farmacia — Productor / Consumidor (instrumentado)
    # ─────────────────────────────────────────────────────────────────
    #
    # En un SO real, cuando un proceso hace una operación de I/O o se
    # bloquea en un semáforo, el SO lo saca de la CPU y lo pone en
    # BLOCKED. Estas primitivas hacen exactamente eso: marcan el proceso
    # como BLOCKED mientras espera espacio (productor) o un item
    # (consumidor), y lo vuelven a READY al desbloquearse.
    #
    # El thread Python sigue siendo el portador real del trabajo, pero
    # las TRANSICIONES DE ESTADO quedan registradas en los acumuladores
    # del Paciente, y por lo tanto en las métricas del sistema.

    def pharmacy_put(self, pid: int, item: str, timeout: float = 2.0) -> bool:
        """Productor instrumentado: BLOCKED si el buffer está lleno."""
        blocked = False
        with self.lock:
            p = self.pacientes.get(pid)
            if p is None:
                return False
            if self.pharmacy_queue.full():
                self._set_state(p, "BLOCKED")
                blocked = True
                self.log("FARMACIA",
                         f"{p.name} bloqueado: buffer lleno")

        try:
            self.pharmacy_queue.put(item, timeout=timeout)
            ok = True
        except Exception:
            ok = False

        with self.ready_cv:
            p = self.pacientes.get(pid)
            if p is not None and blocked:
                self._set_state(p, "READY")
                self.ready_cv.notify_all()
            if ok:
                self.pharmacy_stats["producidos"] += 1
        return ok

    def pharmacy_get(self, pid: int, timeout: float = 2.0) -> Optional[str]:
        """Consumidor instrumentado: BLOCKED si el buffer está vacío."""
        blocked = False
        with self.lock:
            p = self.pacientes.get(pid)
            if p is None:
                return None
            if self.pharmacy_queue.empty():
                self._set_state(p, "BLOCKED")
                blocked = True
                self.log("FARMACIA",
                         f"{p.name} bloqueado: buffer vacío")

        item = None
        try:
            item = self.pharmacy_queue.get(timeout=timeout)
        except Exception:
            item = None

        with self.ready_cv:
            p = self.pacientes.get(pid)
            if p is not None and blocked:
                self._set_state(p, "READY")
                self.ready_cv.notify_all()
            if item is not None:
                self.pharmacy_stats["consumidos"] += 1
        return item

    # ─────────────────────────────────────────────────────────────────
    #  Historia Clínica — Lectores / Escritores (Courtois, instrumentado)
    # ─────────────────────────────────────────────────────────────────
    #
    # Varios lectores pueden leer a la vez. Un escritor necesita acceso
    # EXCLUSIVO (ningún lector ni otro escritor activo).
    #
    # Cada proceso que entra como lector o escritor:
    #  1. Pasa a BLOCKED mientras espera el lock
    #  2. Pasa a READY cuando obtiene el acceso
    #  3. El thread Python representa el "trabajo de I/O" durante la
    #     lectura/escritura (sleep en el caller)
    #  4. Al soltar, el state lo libera del registro de activos.

    def historia_start_read(self, pid: int) -> bool:
        """El proceso quiere leer. Se bloquea hasta poder hacerlo."""
        with self.lock:
            p = self.pacientes.get(pid)
            if p is None:
                return False
            self._set_state(p, "BLOCKED")
            name = p.name
            self.log("HISTORIA",
                     f"{name} llega a consultar la historia clínica")

        # Protocolo lector (Courtois): el PRIMER lector toma el write_lock,
        # bloqueando así a cualquier escritor. Los lectores siguientes
        # solo incrementan el contador.
        with self.historia_readers_lock:
            self.historia_reader_count += 1
            if self.historia_reader_count == 1:
                self.historia_write_lock.acquire()  # bloqueante
            count = self.historia_reader_count

        with self.ready_cv:
            p = self.pacientes.get(pid)
            if p is None:
                # el proceso fue dado de alta mientras esperaba; rollback
                self.historia_readers_lock.acquire()
                try:
                    self.historia_reader_count -= 1
                    if self.historia_reader_count == 0:
                        try:
                            self.historia_write_lock.release()
                        except RuntimeError:
                            pass
                finally:
                    self.historia_readers_lock.release()
                return False
            self.historia_active_readers[pid] = p.name
            self._set_state(p, "READY")
            self.ready_cv.notify_all()
            self.log("HISTORIA",
                     f"{p.name} comienza a leer (lectores activos: {count})")
        return True

    def historia_end_read(self, pid: int):
        """El lector termina de consultar."""
        with self.lock:
            name = self.historia_active_readers.pop(pid, None)
            if name is None:
                p = self.pacientes.get(pid)
                name = p.name if p else f"PID {pid}"
            self.log("HISTORIA", f"{name} termina su consulta")

        with self.historia_readers_lock:
            self.historia_reader_count -= 1
            if self.historia_reader_count == 0:
                try:
                    self.historia_write_lock.release()
                except RuntimeError:
                    pass
                self.log("HISTORIA",
                         "Último lector se retira: historia clínica "
                         "disponible para escritura")

    def historia_start_write(self, pid: int) -> bool:
        """El proceso quiere escribir. Espera acceso exclusivo."""
        with self.lock:
            p = self.pacientes.get(pid)
            if p is None:
                return False
            self._set_state(p, "BLOCKED")
            self.historia_waiting_writers[pid] = p.name
            self.log("HISTORIA",
                     f"{p.name} llega a actualizar la historia clínica")

        self.historia_write_lock.acquire()  # bloqueante

        with self.ready_cv:
            p = self.pacientes.get(pid)
            if p is None:
                try:
                    self.historia_write_lock.release()
                except RuntimeError:
                    pass
                with self.lock:
                    self.historia_waiting_writers.pop(pid, None)
                return False
            self.historia_waiting_writers.pop(pid, None)
            self.historia_active_writer = p.name
            self._set_state(p, "READY")
            self.ready_cv.notify_all()
            self.log("HISTORIA",
                     f"{p.name} obtiene acceso EXCLUSIVO y comienza a escribir")
        return True

    def historia_end_write(self, pid: int, new_entry: str):
        """El escritor termina. Publica el nuevo registro."""
        with self.lock:
            p = self.pacientes.get(pid)
            name = p.name if p else f"PID {pid}"
            ts = time.strftime("%H:%M:%S")
            self.historia_record = new_entry
            self.historia_history.append(f"[{ts}] {name}: {new_entry}")
            if len(self.historia_history) > 7:
                self.historia_history = self.historia_history[-7:]
            self.historia_active_writer = None
            self.log("HISTORIA",
                     f"{name} termina la actualización: {new_entry}")

        try:
            self.historia_write_lock.release()
        except RuntimeError:
            pass

    # ─────────────────────────────────────────────────────────────────
    #  Deadlock
    # ─────────────────────────────────────────────────────────────────

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

    # ─────────────────────────────────────────────────────────────────
    #  Shutdown
    # ─────────────────────────────────────────────────────────────────

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