import threading
import time


class DeadlockDetector(threading.Thread):
    """
    Detector y demo de deadlock real.
    Espera hasta 10s antes de resolverlo solo, o bien hasta que el
    usuario toque "Resolver Deadlock".
    """

    AUTO_RESOLVE_SECONDS = 10

    def __init__(self, state, interval: float = 0.5):
        super().__init__(daemon=True)
        self.state = state
        self.interval = interval
        self.deadlock_since = None

    def run(self):
        while self.state.running:
            time.sleep(self.interval)

            if self.state.deadlock_demo:
                self.state.deadlock_demo = False
                self._launch_demo()

            cycle = self.state.detect_deadlock()
            if cycle:
                if not self.state.deadlock_active:
                    self.state.deadlock_active = True
                    self.deadlock_since = time.time()
                    names = []
                    with self.state.lock:
                        for pid in cycle:
                            h = self.state.heroes.get(pid)
                            if h:
                                names.append(h.name)
                    self.state.log("DEADLOCK",
                        f"⚠️ DEADLOCK: {' → '.join(names)} se bloquean mutuamente")
                    self.state.log("DEADLOCK",
                        "Se derivará un paciente en 10s, o tocá 'Resolver Deadlock'")

                if self.state.deadlock_resolve_now:
                    self.state.deadlock_resolve_now = False
                    self.state.log("DEADLOCK", "Resolución manual solicitada")
                    self.state.break_deadlock(cycle)
                    self.deadlock_since = None
                    continue

                if self.deadlock_since and \
                   (time.time() - self.deadlock_since) > self.AUTO_RESOLVE_SECONDS:
                    self.state.log("DEADLOCK", "⏰ Timeout: derivando paciente")
                    self.state.break_deadlock(cycle)
                    self.deadlock_since = None
            else:
                if self.state.deadlock_active:
                    self.state.deadlock_active = False
                    self.deadlock_since = None

    def _launch_demo(self):
        self.state.log("DEADLOCK",
                       "Iniciando demo: dos pacientes pelearán por Quirófano + Cirujano")
        a = self.state.add_hero("Paciente Demo 1", priority=4, burst=999)
        b = self.state.add_hero("Paciente Demo 2", priority=6, burst=999)
        if not a or not b:
            return

        def worker(pid, first, second):
            if not self.state.request_resource(pid, first, timeout=2.0):
                return
            time.sleep(0.5)
            self.state.request_resource(pid, second, timeout=12.0)
            self.state.release_resource(pid, second)
            self.state.release_resource(pid, first)

        threading.Thread(target=worker,
                         args=(a.pid, "QUIROFANO", "CIRUJANO"),
                         daemon=True).start()
        threading.Thread(target=worker,
                         args=(b.pid, "CIRUJANO", "QUIROFANO"),
                         daemon=True).start()