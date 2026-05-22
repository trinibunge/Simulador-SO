import threading
import time
import random
from collections import deque


class Scheduler(threading.Thread):
    def __init__(self, state, quantum: float = 0.4):
        super().__init__(daemon=True)
        self.state = state
        self.quantum = quantum
        self._rr_queue: deque = deque()
        self._pick_lock = threading.Lock()

    def run(self):
        while self.state.running:
            pacientes = [p for p in self.state.get_pacientes() if p.state == "READY"]

            if not pacientes:
                time.sleep(0.15)
                continue

            if self.state.chaos_mode:
                paciente = random.choice(pacientes)
            elif self.state.scheduler_mode == "PRIORITY":
                paciente = min(pacientes, key=lambda p: p.priority)
            else:
                paciente = self._pick_rr(pacientes)
                if paciente is None:
                    time.sleep(0.15)
                    continue

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

                with self.state.lock:
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
