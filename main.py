import os
import tkinter as tk
import multiprocessing as mp

from core.state import HospitalState
from core.scheduler import Scheduler
from core.deadlock import DeadlockDetector
from core.log_daemon import log_daemon
from ui.boot_screen import BootScreen
from ui.desktop import Desktop


def main():
    # En Windows, multiprocessing requiere 'spawn' y __main__ guard.
    # mp.freeze_support() ya está implícito; el if __name__ == "__main__" sí importa.

    root = tk.Tk()
    root.withdraw()

    state = HospitalState(num_cpus=1)

    # ── Demonio de logging en un PROCESO separado (no hilo) ──
    # Justificación: el daemon hace I/O a disco y no necesita compartir memoria
    # con el resto del kernel.  Aislarlo en su propio espacio de direcciones
    # demuestra IPC real con multiprocessing.Queue, y replica el patrón UNIX
    # de syslogd.
    log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hospital.log")
    log_proc = mp.Process(
        target=log_daemon,
        args=(state.log_in_queue, state.log_out_queue, log_file),
        daemon=True,
        name="HospitalMS-logd",
    )
    log_proc.start()
    state.log_process = log_proc  # para shutdown ordenado

    # Bridge: trae logs desde el proceso del daemon hacia la UI
    state.start_log_bridge()

    # ── Hilos del kernel ──
    # Estos sí son hilos porque COMPARTEN MEMORIA con el HospitalState
    # (pacientes, recursos, locks).  Mantenerlos como hilos evita el overhead
    # de serializar/copiar el estado en cada operación.
    Scheduler(state).start()
    DeadlockDetector(state).start()

    def launch():
        root.deiconify()
        root.geometry("1280x720")
        root.minsize(1280, 720)
        Desktop(root, state)

    BootScreen(root, launch, state=state)
    root.mainloop()


if __name__ == "__main__":
    # Importante para Windows con multiprocessing
    mp.freeze_support()
    main()