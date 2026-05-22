import tkinter as tk
from ui.theme import *
from PIL import Image, ImageTk


class _Tooltip:
    """Tooltip simple que aparece al hacer hover."""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, event=None):
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
        y = self.widget.winfo_rooty() - 38
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(
            self.tip, text=self.text,
            bg="#1e293b", fg="white",
            font=("Aptos", 9), padx=8, pady=4,
            relief="flat"
        ).pack()

    def _hide(self, event=None):
        if self.tip:
            try:
                self.tip.destroy()
            except Exception:
                pass
            self.tip = None


class Dock:
    def __init__(self, master, state, desktop):
        self.master = master
        self.state = state
        self.desktop = desktop

        self.frame = tk.Frame(master, bg="#edf3fa", height=100, highlightthickness=0, bd=0)
        self.frame.pack(side="bottom", fill="x")

        self.inner = tk.Frame(self.frame, bg="#edf3fa", bd=0, highlightthickness=0)
        self.inner.pack(anchor="center", pady=8)

        self.icons = []

    def add_icon(self, title, image_path, command, description=""):
        frame = tk.Frame(self.inner, bg="#edf3fa", bd=0, highlightthickness=0)
        frame.pack(side="left", padx=14)

        img = Image.open(image_path).convert("RGBA")
        img = img.resize((44, 44), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        frame.photo = photo

        btn = tk.Button(
            frame,
            image=photo,
            bg="#edf3fa",
            relief="flat",
            bd=0,
            command=command,
            activebackground="#d1e0f5",
            highlightthickness=0,
            cursor="hand2",
            padx=0,
            pady=0
        )
        btn.pack()

        lbl = tk.Label(
            frame, text=title,
            bg="#edf3fa", fg="#334155",
            font=("Aptos", 8, "bold")
        )
        lbl.pack(pady=(3, 0))

        if description:
            tooltip_text = f"{title}: {description}"
            _Tooltip(btn, tooltip_text)
            _Tooltip(lbl, tooltip_text)

        self.icons.append(frame)