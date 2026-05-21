import threading
import time
import random


class Scheduler(threading.Thread):
    def __init__(self, state):
        super().__init__(daemon=True)
        self.state = state
        self.index = 0

    def run(self):
        while self.state.running:
            heroes = self.state.get_heroes()
            if not heroes:
                time.sleep(0.4)
                continue

            if self.state.chaos_mode:
                hero = random.choice(heroes)
            elif self.state.scheduler_mode == "PRIORITY":
                hero = sorted(heroes, key=lambda h: h.priority)[0]
            else:
                hero = heroes[self.index % len(heroes)]
                self.index += 1

            with self.state.lock:
                if hero.pid in self.state.heroes:
                    self.state.heroes[hero.pid].state = "RUNNING"

            self.state.clock_tick += 1
            self.state.log("CPU", f"Tick {self.state.clock_tick}: turno de {hero.name}")
            time.sleep(0.8)

            with self.state.lock:
                if hero.pid in self.state.heroes:
                    self.state.heroes[hero.pid].state = "READY"