import threading
import time
import random
from collections import deque


class Scheduler(threading.Thread):
    """
    Planificador de procesos.

    Diferencia clave respecto a versiones anteriores: ya NO hace busy-wait
    con time.sleep() cuando no hay procesos READY.  Ahora duerme sobre una
    Condition variable (state.ready_cv) y se despierta cuando algún hilo
    le hace notify (admitir, request_resource exitoso, fin de quantum, etc).

    Esto es el patrón canónico de un scheduler real: bloquearse en una CV
    es lo que hace, por ejemplo, el scheduler de Linux cuando no hay tareas
    runnable en su cola.
    """

    WAIT_TIMEOUT = 0.5  # timeout defensivo por si nos perdemos un notify

    def __init__(self, state, quantum: float = 0.4):
        super().__init__(daemon=True)
        self.state = state
        self.quantum = quantum
        self._rr_queue: deque = deque()
        self._pick_lock = threading.Lock()

    def run(self):
        while self.state.running:
            # ─── Esperar (sin polling) a que haya algún proceso READY ───
            with self.state.ready_cv:
                while self.state.running:
                    pacientes_ready = [
                        p for p in self.state.pacientes.values() if p.state == "READY"
                    ]
                    if pacientes_ready:
                        break
                    # No hay nada que correr: dormimos en la CV.  Salimos
                    # solo cuando notify_all() (timeout es defensa, no la regla).
                    self.state.ready_cv.wait(timeout=self.WAIT_TIMEOUT)

                if not self.state.running:
                    return
                # Snapshot bajo el lock
                pacientes = list(pacientes_ready)

            # ─── Elegir víctima según política ───
            if self.state.chaos_mode:
                paciente = random.choice(pacientes)
            elif self.state.scheduler_mode == "PRIORITY":
                paciente = min(pacientes, key=lambda p: p.priority)
            else:
                paciente = self._pick_rr(pacientes)
                if paciente is None:
                    continue

            # ─── Adquirir CPU (semáforo) ───
            if not self.state.cpu_sem.acquire(timeout=0.3):
                continue

            try:
                with self.state.lock:
                    if paciente.pid not in self.state.pacientes:
                        continue
                    paciente = self.state.pacientes[paciente.pid]
                    if paciente.state != "READY":
                        continue
                    paciente.state = "RUNNING"
                    self.state.clock_tick += 1
                    tick = self.state.clock_tick

                self.state.log("CPU", f"t={tick}: atendiendo a {paciente.name}")
                time.sleep(self.quantum)

                # ─── Fin del quantum: actualizar estado ───
                with self.state.ready_cv:
                    if paciente.pid in self.state.pacientes:
                        paciente = self.state.pacientes[paciente.pid]
                        paciente.cpu_used += 1
                        if paciente.cpu_used >= paciente.burst:
                            self.state.log("ALTA",
                                f"{paciente.name} terminó su atención y es dado de alta")
                            for r in list(paciente.holding):
                                self.state._force_release(paciente.pid, r)
                            del self.state.pacientes[paciente.pid]
                        else:
                            if paciente.state == "RUNNING":
                                paciente.state = "READY"
                                self._rr_queue.append(paciente.pid)
                                # Despertar a nosotros mismos / a otro scheduler
                                self.state.ready_cv.notify_all()
            finally:
                self.state.cpu_sem.release()

    def _pick_rr(self, pacientes: list):
        with self._pick_lock:
            ready_pids = {p.pid for p in pacientes}
            pid_map = {p.pid: p for p in pacientes}
            queued = set(self._rr_queue)

            for p in pacientes:
                if p.pid not in queued:
                    self._rr_queue.append(p.pid)

            self._rr_queue = deque(p for p in self._rr_queue if p in ready_pids)

            if not self._rr_queue:
                return None

            return pid_map[self._rr_queue.popleft()]