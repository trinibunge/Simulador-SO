import threading
import queue
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Hero:
    pid: int
    name: str
    priority: int
    state: str = "READY"
    symbol: str = "🧙"


class CatacumbaState:
    def __init__(self):
        self.lock = threading.RLock()
        self.pid_counter = 1
        self.heroes: Dict[int, Hero] = {}
        self.logs = queue.Queue()

        self.running = True
        self.scheduler_mode = "ROUNDROBIN"
        self.chaos_mode = False
        self.deadlock_demo = False
        self.ram_limit = 12

        self.clock_tick = 0
        self.menu_open = False

    def log(self, tag: str, message: str):
        self.logs.put(f"[{tag}] {message}")

    def add_hero(self, name: str, priority: int):
        with self.lock:
            if len(self.heroes) >= self.ram_limit:
                self.log("MEM", f"RAM llena. SegFault en la Catacumba.")
                return None

            pid = self.pid_counter
            self.pid_counter += 1

            symbol = "🧙" if priority <= 2 else "⚔️" if priority <= 5 else "🐢"
            self.heroes[pid] = Hero(pid, name, priority, "READY", symbol)
            self.log("SPAWN", f"{name} creado con PID {pid}")
            return self.heroes[pid]

    def kill_hero(self, target):
        with self.lock:
            for pid, hero in list(self.heroes.items()):
                if hero.name == target or str(hero.pid) == str(target):
                    del self.heroes[pid]
                    self.log("KILL", f"{hero.name} ha caído")
                    return True
        self.log("WARN", f"No existe {target}")
        return False

    def set_mode(self, mode: str):
        mode = mode.upper()
        if mode in ("ROUNDROBIN", "PRIORITY"):
            self.scheduler_mode = mode
            self.log("SCHED", f"Modo {mode} activado")
            return True
        return False

    def get_heroes(self) -> List[Hero]:
        with self.lock:
            return list(self.heroes.values())