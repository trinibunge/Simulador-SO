import tkinter as tk
from core.state import CatacumbaState
from core.scheduler import Scheduler
from core.deadlock import DeadlockDetector
from ui.boot_screen import BootScreen
from ui.desktop import Desktop


def main():
    root = tk.Tk()
    root.withdraw()

    state = CatacumbaState()

    Scheduler(state).start()
    DeadlockDetector(state).start()

    def launch():
        root.deiconify()
        root.geometry("1280x720")
        root.minsize(1280, 720)
        Desktop(root, state)

    BootScreen(root, launch)
    root.mainloop()


if __name__ == "__main__":
    main()