import threading
import time
import random
from collections import deque


class Scheduler(threading.Thread):
    """
    Planificador de procesos.

    Cambios respecto a la versión vieja:
    - Usa state._set_state() para TODAS las transiciones, así los
      acumuladores ready_acc / running_acc se llenan automáticamente
      y las métricas no se inventan.
    - Apps (kind="app") NUNCA terminan por burst. Pelean por la CPU
      mientras estén abiertas, igual que un proceso de usuario real.
    - Sigue durmiendo en una Condition variable (sin busy-wait).
    """

    WAIT_TIMEOUT = 0.5

    def __init__(self, state, quantum: float = 0.4):
        super().__init__(daemon=True)
        self.state = state
        self.quantum = quantum
        self._rr_queue: deque = deque()
        self._pick_lock = threading.Lock()

    def run(self):
        while self.state.running:
            # ─── Esperar (sin polling) hasta que haya algún proceso READY ───
            with self.state.ready_cv:
                while self.state.running:
                    pacientes_ready = [
                        p for p in self.state.pacientes.values() if p.state == "READY"
                    ]
                    if pacientes_ready:
                        break
                    self.state.ready_cv.wait(timeout=self.WAIT_TIMEOUT)

                if not self.state.running:
                    return
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
                    # Usar _set_state para que running_acc se acumule bien
                    self.state._set_state(paciente, "RUNNING")
                    self.state.clock_tick += 1
                    tick = self.state.clock_tick

                self.state.log("CPU", f"t={tick}: atendiendo a {paciente.name}")
                time.sleep(self.quantum)

                # ─── Fin del quantum ───
                with self.state.ready_cv:
                    if paciente.pid in self.state.pacientes:
                        paciente = self.state.pacientes[paciente.pid]
                        paciente.cpu_used += 1

                        # Apps nunca terminan naturalmente: siguen vivas
                        # hasta que el usuario las cierre.
                        natural_finish = (
                            paciente.kind != "app"
                            and paciente.cpu_used >= paciente.burst
                        )

                        if natural_finish:
                            now = time.time()
                            self.state._set_state(paciente, paciente.state, now)
                            paciente.completed_at = now

                            self.state.log("ALTA",
                                f"{paciente.name} terminó su atención · "
                                f"esperó {paciente.waiting_time():.1f}s")

                            for r in list(paciente.holding):
                                self.state._force_release(paciente.pid, r)

                            self.state.completed_history.append(paciente)
                            if len(self.state.completed_history) > 200:
                                self.state.completed_history = \
                                    self.state.completed_history[-200:]

                            del self.state.pacientes[paciente.pid]
                        else:
                            if paciente.state == "RUNNING":
                                self.state._set_state(paciente, "READY")
                                self._rr_queue.append(paciente.pid)
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