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
        self._demo_pids = []

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
                    self.state.deadlock_since = time.time()
                    names = []
                    with self.state.lock:
                        for pid in cycle:
                            p = self.state.pacientes.get(pid)
                            if p:
                                names.append(p.name)
                    self.state.log("DEADLOCK",
                        f"⚠️ DEADLOCK: {' → '.join(names)} se bloquean mutuamente")
                    self.state.log("DEADLOCK",
                        "Se derivará un paciente en 10s, o tocá 'Resolver Deadlock'")

                if self.state.deadlock_resolve_now:
                    self.state.deadlock_resolve_now = False
                    self.state.log("DEADLOCK", "Resolución manual solicitada")
                    self.state.break_deadlock(cycle)
                    self.state.deadlock_since = None
                    continue

                if self.state.deadlock_since and \
                   (time.time() - self.state.deadlock_since) > self.AUTO_RESOLVE_SECONDS:
                    self.state.log("DEADLOCK", "⏰ Timeout: derivando paciente")
                    self.state.break_deadlock(cycle)
                    self.state.deadlock_since = None
            else:
                if self.state.deadlock_active:
                    self.state.deadlock_active = False
                    self.state.deadlock_since = None

    def _launch_demo(self):
        # Limpiar pacientes de demos anteriores para liberar recursos
        had_prev = bool(self._demo_pids)
        for pid in self._demo_pids:
            self.state.dar_alta(pid)
        self._demo_pids.clear()
        if had_prev:
            time.sleep(0.4)  # dar tiempo a que los workers previos suelten los locks

        self.state.log("DEADLOCK",
                       "Iniciando demo: dos pacientes pelearán por Quirófano + Cirujano")
        name_a = f"Paciente {self.state.pid_counter}"
        a = self.state.admitir(name_a, priority=4, burst=999)
        name_b = f"Paciente {self.state.pid_counter}"
        b = self.state.admitir(name_b, priority=6, burst=999)
        if not a or not b:
            return
        self._demo_pids = [a.pid, b.pid]

        # Ambos threads deben adquirir su primer recurso antes de que cualquiera
        # intente el segundo, garantizando que el deadlock siempre se forme.
        barrier = threading.Barrier(2)

        def worker(pid, first, second):
            if not self.state.request_resource(pid, first, timeout=5.0):
                try:
                    barrier.abort()
                except Exception:
                    pass
                return
            try:
                barrier.wait(timeout=5.0)
            except threading.BrokenBarrierError:
                self.state.release_resource(pid, first)
                return
            self.state.request_resource(pid, second, timeout=15.0)
            self.state.release_resource(pid, second)
            self.state.release_resource(pid, first)

        threading.Thread(target=worker,
                         args=(a.pid, "QUIROFANO", "CIRUJANO"),
                         daemon=True).start()
        threading.Thread(target=worker,
                         args=(b.pid, "CIRUJANO", "QUIROFANO"),
                         daemon=True).start()