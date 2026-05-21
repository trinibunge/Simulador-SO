import threading
import time
import random


class Scheduler(threading.Thread):
    def __init__(self, state, quantum: float = 0.4):
        super().__init__(daemon=True)
        self.state = state
        self.quantum = quantum
        self.rr_index = 0

    def run(self):
        while self.state.running:
            heroes = [h for h in self.state.get_heroes() if h.state == "READY"]

            if not heroes:
                time.sleep(0.15)
                continue

            if self.state.chaos_mode:
                hero = random.choice(heroes)
            elif self.state.scheduler_mode == "PRIORITY":
                hero = min(heroes, key=lambda h: h.priority)
            else:
                self.rr_index = (self.rr_index + 1) % len(heroes)
                hero = heroes[self.rr_index]

            if not self.state.cpu_sem.acquire(timeout=0.3):
                continue

            try:
                with self.state.lock:
                    if hero.pid not in self.state.heroes:
                        continue
                    hero = self.state.heroes[hero.pid]
                    if hero.state != "READY":
                        continue
                    hero.state = "RUNNING"
                    self.state.clock_tick += 1
                    tick = self.state.clock_tick

                self.state.log("CPU", f"t={tick}: atendiendo a {hero.name}")
                time.sleep(self.quantum)

                with self.state.lock:
                    if hero.pid in self.state.heroes:
                        hero = self.state.heroes[hero.pid]
                        hero.cpu_used += 1
                        if hero.cpu_used >= hero.burst:
                            self.state.log("ALTA",
                                f"{hero.name} terminó su atención y es dado de alta")
                            for r in list(hero.holding):
                                self.state._force_release(hero.pid, r)
                            del self.state.heroes[hero.pid]
                        else:
                            if hero.state == "RUNNING":
                                hero.state = "READY"
            finally:
                self.state.cpu_sem.release()