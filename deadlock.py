import threading
import time


class DeadlockDetector(threading.Thread):
    def __init__(self, state):
        super().__init__(daemon=True)
        self.state = state

    def run(self):
        while self.state.running:
            if self.state.deadlock_demo:
                self.state.log("DEADLOCK", "El Deadlock Demon despierta...")
                time.sleep(2)

                heroes = self.state.get_heroes()
                if len(heroes) >= 2:
                    a = heroes[0]
                    b = heroes[1]
                    self.state.log("DEADLOCK", f"{a.name} espera a {b.name}. {b.name} espera a {a.name}.")
                    time.sleep(1)
                    self.state.log("DEADLOCK", "Detección de ciclo activa. Resolviendo conflicto...")
                    self.state.kill_hero(b.name)
                    self.state.log("DEADLOCK", f"Se sacrificó a {b.name} para liberar el sistema.")

                self.state.deadlock_demo = False

            time.sleep(1)