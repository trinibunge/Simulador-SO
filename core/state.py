import threading
import queue
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Hero:
    """Representa un 'proceso' (paciente) en el simulador."""
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
    - cpu_sem (Semaphore): N doctores disponibles a la vez.
    - resources (Locks): Quirófano y Cirujano, uno a la vez.
    - logs (Queue): productor-consumidor logs.
    - pharmacy_queue (Queue acotada): productor-consumidor de medicamentos.
    """

    PHARMACY_CAPACITY = 8

    def __init__(self, num_cpus: int = 2):
        self.lock = threading.RLock()
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
        self.heroes: Dict[int, Hero] = {}
        self.logs: "queue.Queue[str]" = queue.Queue()

        # ─── Farmacia: productor-consumidor clásico con buffer acotado ───
        # La Queue de Python ya es thread-safe e implementa el patrón:
        # put() bloquea si está llena, get() bloquea si está vacía.
        self.pharmacy_queue: "queue.Queue[str]" = queue.Queue(maxsize=self.PHARMACY_CAPACITY)
        self.pharmacy_running = False
        self.pharmacy_stats = {"producidos": 0, "consumidos": 0}

        self.running = True
        self.scheduler_mode = "ROUNDROBIN"
        self.chaos_mode = False
        self.deadlock_demo = False
        self.deadlock_active = False
        self.deadlock_resolve_now = False
        self.ram_limit = 12
        self.clock_tick = 0

    def log(self, tag: str, message: str):
        self.logs.put(f"[{tag}] {message}")

    def add_hero(self, name: str, priority: int, burst: int = 8):
        with self.lock:
            if len(self.heroes) >= self.ram_limit:
                self.log("HOSPITAL", "Sala llena. No se admiten más pacientes.")
                return None
            pid = self.pid_counter
            self.pid_counter += 1
            symbol = "🚨" if priority <= 2 else ("🤕" if priority <= 5 else "🤒")
            hero = Hero(pid=pid, name=name, priority=priority,
                        state="READY", symbol=symbol, burst=burst)
            self.heroes[pid] = hero
            self.log("ADMIT", f"{name} admitido (PID {pid}, gravedad {priority})")
            return hero

    def kill_hero(self, target):
        with self.lock:
            for pid, hero in list(self.heroes.items()):
                if hero.name == target or str(hero.pid) == str(target):
                    for res in list(hero.holding):
                        self._force_release(pid, res)
                    del self.heroes[pid]
                    self.log("ALTA", f"{hero.name} (PID {pid}) dado de alta")
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

    def get_heroes(self) -> List[Hero]:
        with self.lock:
            return list(self.heroes.values())

    def request_resource(self, pid: int, res_name: str, timeout: float = 0.3) -> bool:
        if res_name not in self.resources:
            return False

        with self.lock:
            hero = self.heroes.get(pid)
            if not hero:
                return False
            hero.waiting_for = res_name
            hero.state = "BLOCKED"
            if pid not in self.resource_waiters[res_name]:
                self.resource_waiters[res_name].append(pid)
            self.log("RECURSO", f"{hero.name} solicita {res_name}")

        got = self.resources[res_name].acquire(timeout=timeout)

        with self.lock:
            hero = self.heroes.get(pid)
            if not hero:
                if got:
                    self.resources[res_name].release()
                return False
            if pid in self.resource_waiters[res_name]:
                self.resource_waiters[res_name].remove(pid)
            if got:
                self.resource_owner[res_name] = pid
                hero.holding.append(res_name)
                hero.waiting_for = None
                hero.state = "READY"
                self.log("RECURSO", f"{hero.name} obtuvo {res_name}")
                return True
            else:
                self.log("RECURSO", f"{hero.name} bloqueado esperando {res_name}")
                return False

    def release_resource(self, pid: int, res_name: str):
        with self.lock:
            hero = self.heroes.get(pid)
            if not hero or res_name not in hero.holding:
                return
            hero.holding.remove(res_name)
            self.resource_owner[res_name] = None
            self.log("RECURSO", f"{hero.name} libera {res_name}")
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

    def detect_deadlock(self) -> Optional[list]:
        with self.lock:
            edges: Dict[int, list] = {}
            for pid, hero in self.heroes.items():
                if hero.waiting_for:
                    owner = self.resource_owner.get(hero.waiting_for)
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
            victims = [self.heroes[p] for p in cycle if p in self.heroes]
            if not victims:
                return
            victim = max(victims, key=lambda h: h.priority)
        self.log("DEADLOCK",
                 f"Resolviendo: {victim.name} es derivado a otro hospital")
        self.kill_hero(victim.pid)
        self.deadlock_active = False

    def shutdown(self):
        self.running = False
        self.pharmacy_running = False