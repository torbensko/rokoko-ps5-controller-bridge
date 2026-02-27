"""Rokoko PS5 Controller Bridge — GUI Application.

A minimal tkinter UI that shows connection status, button mapping,
and an activity log. Designed for double-click-and-forget usage on Windows.
"""

import os
import sys
import time
import socket
import threading
import queue
import tkinter as tk
from datetime import datetime

# Handle PyInstaller --windowed mode where stdout/stderr are None
if getattr(sys, "frozen", False):
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

try:
    import pygame
except ImportError:
    _root = tk.Tk()
    _root.withdraw()
    from tkinter import messagebox

    messagebox.showerror(
        "Missing Dependency",
        "pygame is required.\nInstall with:  pip install pygame",
    )
    sys.exit(1)

from controller_bridge import (
    rokoko_api,
    ROKOKO_BASE_URL,
    CALIBRATE_BUTTON,
    RECORD_BUTTON,
    STOP_BUTTON,
    DEBOUNCE_SECONDS,
)


# ── Theme ──────────────────────────────────────────────────────────────────────

BG = "#1a1b26"
CARD_BG = "#24283b"
TEXT = "#c0caf5"
TEXT_DIM = "#565f89"
GREEN = "#9ece6a"
RED = "#f7768e"
YELLOW = "#e0af68"
BLUE = "#7aa2f7"
BORDER = "#414868"


# ── Helpers ────────────────────────────────────────────────────────────────────


def check_rokoko_connection():
    """Check if Rokoko Studio is reachable via TCP."""
    try:
        sock = socket.create_connection(("127.0.0.1", 14053), timeout=1)
        sock.close()
        return True
    except (socket.timeout, socket.error, OSError):
        return False


# ── Application ────────────────────────────────────────────────────────────────


class App:
    def __init__(self):
        # Initialize pygame on the main thread (no visible window without set_mode)
        pygame.init()

        self.root = tk.Tk()
        self.root.title("Rokoko Controller Bridge")
        self.root.configure(bg=BG)
        self.root.geometry("440x520")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.msg_queue = queue.Queue()
        self.running = True
        self.joystick = None
        self._last_times = {}

        self._build_ui()

        # Poll pygame events on the main thread (avoids SDL threading issues)
        self._poll_controller()
        # Poll the message queue for background-thread results
        self._poll_queue()
        # Rokoko connectivity check runs in a background thread
        threading.Thread(target=self._rokoko_check_loop, daemon=True).start()

    # ── UI Construction ────────────────────────────────────────────────────

    def _build_ui(self):
        pad = 12

        # Title
        tk.Label(
            self.root,
            text="Rokoko Controller Bridge",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=(pad, 2))

        tk.Label(
            self.root,
            text="PS5 DualSense \u2192 Rokoko Studio",
            bg=BG,
            fg=TEXT_DIM,
            font=("Segoe UI", 9),
        ).pack(pady=(0, pad))

        # ── Status card ────────────────────────────────────────────────
        status_card, status_inner = self._make_card(self.root, "STATUS")
        status_card.pack(fill="x", padx=pad, pady=(0, 8))

        self.ctrl_dot, self.ctrl_val = self._status_row(
            status_inner, "Controller", "Searching\u2026", YELLOW
        )
        self.roko_dot, self.roko_val = self._status_row(
            status_inner, "Rokoko Studio", "Checking\u2026", YELLOW
        )
        self.rec_dot, self.rec_val = self._status_row(
            status_inner, "Recording", "Idle", TEXT_DIM
        )

        # ── Button mapping card ────────────────────────────────────────
        map_card, map_inner = self._make_card(self.root, "BUTTON MAPPING")
        map_card.pack(fill="x", padx=pad, pady=(0, 8))

        for symbol, label, action in [
            ("\u25b3", "Triangle", "Calibrate"),
            ("\u2715", "Cross", "Start Recording"),
            ("\u25cb", "Circle", "Stop Recording"),
        ]:
            row = tk.Frame(map_inner, bg=CARD_BG)
            row.pack(fill="x", pady=2)
            tk.Label(
                row,
                text=f"{symbol}  {label}",
                bg=CARD_BG,
                fg=BLUE,
                font=("Segoe UI", 10),
                width=16,
                anchor="w",
            ).pack(side="left")
            tk.Label(
                row, text="\u2192", bg=CARD_BG, fg=TEXT_DIM, font=("Segoe UI", 10)
            ).pack(side="left", padx=4)
            tk.Label(
                row,
                text=action,
                bg=CARD_BG,
                fg=TEXT,
                font=("Segoe UI", 10),
                anchor="w",
            ).pack(side="left")

        # ── Log card ──────────────────────────────────────────────────
        log_card, log_inner = self._make_card(self.root, "ACTIVITY LOG")
        log_card.pack(fill="both", expand=True, padx=pad, pady=(0, pad))

        self.log_text = tk.Text(
            log_inner,
            bg=CARD_BG,
            fg=TEXT,
            font=("Consolas", 9),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            wrap="word",
            state="disabled",
            cursor="arrow",
        )
        scrollbar = tk.Scrollbar(
            log_inner, command=self.log_text.yview, bg=CARD_BG, troughcolor=CARD_BG
        )
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)

        self.log_text.tag_configure("ts", foreground=TEXT_DIM)
        self.log_text.tag_configure("info", foreground=TEXT)
        self.log_text.tag_configure("success", foreground=GREEN)
        self.log_text.tag_configure("error", foreground=RED)

        self._add_log("Application started")

    def _make_card(self, parent, title):
        """Create a card widget with a thin border and header. Returns (outer, inner)."""
        outer = tk.Frame(parent, bg=BORDER)
        card = tk.Frame(outer, bg=CARD_BG)
        card.pack(fill="both", expand=True, padx=1, pady=1)

        tk.Label(
            card,
            text=title,
            bg=CARD_BG,
            fg=TEXT_DIM,
            font=("Segoe UI", 8, "bold"),
            anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 4))

        inner = tk.Frame(card, bg=CARD_BG)
        inner.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        return outer, inner

    def _status_row(self, parent, label, initial_text, initial_color):
        """Create a status row: dot Label Value. Returns (dot_label, value_label)."""
        row = tk.Frame(parent, bg=CARD_BG)
        row.pack(fill="x", pady=2)

        dot = tk.Label(
            row, text="\u25cf", bg=CARD_BG, fg=initial_color, font=("Segoe UI", 11)
        )
        dot.pack(side="left")

        tk.Label(
            row,
            text=label,
            bg=CARD_BG,
            fg=TEXT,
            font=("Segoe UI", 10),
            width=14,
            anchor="w",
        ).pack(side="left", padx=(6, 0))

        val = tk.Label(
            row,
            text=initial_text,
            bg=CARD_BG,
            fg=initial_color,
            font=("Segoe UI", 10),
            anchor="w",
        )
        val.pack(side="left")
        return dot, val

    # ── Logging ────────────────────────────────────────────────────────────

    def _add_log(self, message, tag="info"):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{ts}  ", "ts")
        self.log_text.insert("end", f"{message}\n", tag)
        # Keep log trimmed to 500 lines
        lines = int(self.log_text.index("end-1c").split(".")[0])
        if lines > 500:
            self.log_text.delete("1.0", f"{lines - 500}.0")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # ── Status helpers ─────────────────────────────────────────────────────

    def _set_status(self, dot, val, text, color):
        dot.configure(fg=color)
        val.configure(text=text, fg=color)

    # ── Controller polling (main thread) ───────────────────────────────────

    def _poll_controller(self):
        if not self.running:
            return

        for event in pygame.event.get():
            if event.type == pygame.JOYDEVICEADDED:
                if self.joystick is None:
                    try:
                        self.joystick = pygame.joystick.Joystick(event.device_index)
                        name = self.joystick.get_name()
                        self._set_status(self.ctrl_dot, self.ctrl_val, name, GREEN)
                        self._add_log(f"Controller connected: {name}", "success")
                    except pygame.error:
                        pass

            elif event.type == pygame.JOYDEVICEREMOVED:
                self.joystick = None
                self._set_status(
                    self.ctrl_dot, self.ctrl_val, "Searching\u2026", YELLOW
                )
                self._add_log("Controller disconnected", "error")

            elif event.type == pygame.JOYBUTTONDOWN and self.joystick is not None:
                btn = event.button
                if btn not in (CALIBRATE_BUTTON, RECORD_BUTTON, STOP_BUTTON):
                    continue
                now = time.time()
                if now - self._last_times.get(btn, 0) < DEBOUNCE_SECONDS:
                    self._add_log("Debounced \u2014 ignoring repeated press")
                    continue
                self._last_times[btn] = now
                # Run API call in a worker thread so the UI stays responsive
                threading.Thread(
                    target=self._handle_button, args=(btn,), daemon=True
                ).start()

        self.root.after(10, self._poll_controller)

    # ── Button actions (run in worker threads) ─────────────────────────────

    def _handle_button(self, button):
        if button == CALIBRATE_BUTTON:
            self.msg_queue.put(("log", "Triangle \u2192 Calibrating (3 s countdown)\u2026", "info"))
            code, status, desc = rokoko_api(
                "calibrate",
                {
                    "countdown_delay": 3,
                    "skip_suit": False,
                    "skip_gloves": False,
                    "use_custom_pose": False,
                    "pose": "straight-arms-down",
                },
            )
            if code == 0:
                self.msg_queue.put(("log", f"Calibration OK: {desc}", "success"))
            elif code is None:
                self.msg_queue.put(
                    ("log", "Calibration failed \u2014 Rokoko unreachable", "error")
                )
            else:
                self.msg_queue.put(("log", f"Calibration: {status} \u2014 {desc}", "error"))

        elif button == RECORD_BUTTON:
            self.msg_queue.put(("log", "Cross \u2192 Starting recording\u2026", "info"))
            code, status, desc = rokoko_api("recording/start", {"filename": ""})
            if code == 0:
                self.msg_queue.put(("log", "Recording started", "success"))
                self.msg_queue.put(("recording", True))
            elif code is None:
                self.msg_queue.put(
                    ("log", "Record failed \u2014 Rokoko unreachable", "error")
                )
            else:
                self.msg_queue.put(("log", f"Record: {status} \u2014 {desc}", "error"))

        elif button == STOP_BUTTON:
            self.msg_queue.put(("log", "Circle \u2192 Stopping recording\u2026", "info"))
            code, status, desc = rokoko_api(
                "recording/stop", {"back_to_live": True}
            )
            if code == 0:
                self.msg_queue.put(("log", "Recording stopped", "success"))
                self.msg_queue.put(("recording", False))
            elif code is None:
                self.msg_queue.put(
                    ("log", "Stop failed \u2014 Rokoko unreachable", "error")
                )
            else:
                self.msg_queue.put(("log", f"Stop: {status} \u2014 {desc}", "error"))

    # ── Rokoko connectivity (background thread) ───────────────────────────

    def _rokoko_check_loop(self):
        while self.running:
            connected = check_rokoko_connection()
            self.msg_queue.put(("rokoko", connected))
            time.sleep(3)

    # ── Queue processing (main thread) ─────────────────────────────────────

    def _poll_queue(self):
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                kind = msg[0]

                if kind == "log":
                    self._add_log(msg[1], msg[2] if len(msg) > 2 else "info")

                elif kind == "rokoko":
                    if msg[1]:
                        self._set_status(
                            self.roko_dot, self.roko_val, "Connected", GREEN
                        )
                    else:
                        self._set_status(
                            self.roko_dot, self.roko_val, "Not reachable", RED
                        )

                elif kind == "recording":
                    if msg[1]:
                        self._set_status(
                            self.rec_dot, self.rec_val, "Recording", RED
                        )
                    else:
                        self._set_status(
                            self.rec_dot, self.rec_val, "Idle", TEXT_DIM
                        )

        except queue.Empty:
            pass

        if self.running:
            self.root.after(50, self._poll_queue)

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def _on_close(self):
        self.running = False
        pygame.quit()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
