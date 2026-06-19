"""
番茄钟 - 桌面番茄钟应用
A beautiful desktop Pomodoro Timer built with Python/tkinter.
Zero external dependencies — uses only Python standard library.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
import time
import threading
import math
import winsound
from datetime import date, timedelta
from pathlib import Path

# ============================================================
# Configuration
# ============================================================
APP_NAME = "番茄钟"
DATA_DIR = Path.home() / ".pomodoro_timer"
SETTINGS_FILE = DATA_DIR / "settings.json"
HISTORY_FILE = DATA_DIR / "history.json"

DEFAULT_SETTINGS = {
    "focus_duration": 25,          # minutes
    "short_break_duration": 5,     # minutes
    "long_break_duration": 15,     # minutes
    "long_break_interval": 4,      # focus sessions before long break
    "always_on_top": False,
    "auto_start_break": True,
    "auto_start_focus": False,
    "volume": 80,
}

# Color scheme
COLORS = {
    "bg_primary": "#1a1a2e",
    "bg_secondary": "#16213e",
    "bg_tertiary": "#0f3460",
    "accent_focus": "#e94560",
    "accent_break": "#4ecca3",
    "accent_long_break": "#3498db",
    "text_primary": "#eeeeee",
    "text_secondary": "#a0a0b0",
    "text_muted": "#666666",
    "border": "#2a2a4a",
    "white": "#ffffff",
}


def load_json(path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return {**default, **json.load(f)}
    except Exception:
        pass
    return {**default}


def save_json(path, data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ============================================================
# Main Application
# ============================================================
class PomodoroTimer(tk.Tk):
    def __init__(self):
        super().__init__()

        # Load data
        self.settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
        self.history = load_json(HISTORY_FILE, {})

        # Timer state
        self.mode = "focus"           # focus | short_break | long_break
        self.timer_state = "idle"     # idle | running | paused
        self.time_left = self.settings["focus_duration"] * 60
        self.total_time = self.time_left
        self.pomodoros_today = 0
        self.pomodoro_cycle = 0       # count within current cycle
        self.tasks = []
        self.timer_thread = None
        self.timer_lock = threading.Lock()
        self._stop_timer = False
        self._settings_visible = False
        self._history_window = None

        # Setup window
        self._setup_window()
        self._build_ui()
        self._bind_events()

        # Load today's data (must be after _build_ui so UI elements exist)
        self._load_today()

        # Apply settings
        self.attributes("-topmost", self.settings["always_on_top"])
        self._apply_theme_to_mode()

        # Center the window
        self.update_idletasks()
        w = 380
        h = 600
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.update_timer_display()
        self.update_ring()
        self.update_session_dots()

    # ---- Window Setup ----
    def _setup_window(self):
        self.title(APP_NAME)
        self.configure(bg=COLORS["bg_primary"])
        self.resizable(True, True)
        self.minsize(340, 500)

        # Use standard window frame for best Windows compatibility
        self.overrideredirect(False)

        # Set dark title bar on Windows 10+
        try:
            import ctypes
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int(2))
            )
        except Exception:
            pass

        # Set icon
        try:
            icon_path = Path(__file__).parent / "assets" / "icon.ico"
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except Exception:
            pass

    # ---- Build UI ----
    def _build_ui(self):
        self._build_titlebar()
        self._build_main_content()

    def _build_titlebar(self):
        """Decorative header bar with app name and pin toggle."""
        titlebar = tk.Frame(self, bg=COLORS["bg_secondary"], height=38,
                            highlightthickness=0, bd=0, relief="flat")
        titlebar.pack(fill="x", side="top")
        titlebar.pack_propagate(False)

        title_label = tk.Label(titlebar, text="🍅  番茄钟", bg=COLORS["bg_secondary"],
                               fg=COLORS["text_secondary"], font=("Microsoft YaHei", 10, "bold"),
                               anchor="w", padx=14)
        title_label.pack(side="left", fill="both", expand=True)

        # Pin button
        self.btn_pin = tk.Button(titlebar, text="📌", command=self._toggle_pin,
                                 bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
                                 font=("Segoe UI", 10), bd=0, relief="flat",
                                 activebackground=COLORS["bg_tertiary"], activeforeground=COLORS["white"],
                                 width=3, cursor="hand2")
        self.btn_pin.pack(side="right", padx=(0, 6))

        if self.settings["always_on_top"]:
            self.btn_pin.configure(fg=COLORS["accent_focus"])

    def _set_hover(self, widget, hover_bg, hover_fg):
        orig_bg = widget.cget("bg")
        orig_fg = widget.cget("fg")

        def on_enter(e):
            widget.configure(bg=hover_bg, fg=hover_fg)

        def on_leave(e):
            widget.configure(bg=orig_bg, fg=orig_fg)

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def _build_main_content(self):
        """Main scrollable content area."""
        # Scrollable container
        self.main_canvas = tk.Canvas(self, bg=COLORS["bg_primary"], highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.main_canvas.yview)

        self.content_frame = tk.Frame(self.main_canvas, bg=COLORS["bg_primary"])

        self.content_frame.bind("<Configure>",
                                lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all")))

        self.main_canvas.create_window((0, 0), window=self.content_frame, anchor="nw", tags="content")
        self.main_canvas.configure(yscrollcommand=scrollbar.set)

        self.main_canvas.pack(side="left", fill="both", expand=True)
        # Scrollbar hidden by default — only show on hover
        # self.main_canvas.bind("<Enter>", lambda e: scrollbar.pack(side="right", fill="y"))
        # self.main_canvas.bind("<Leave>", lambda e: scrollbar.pack_forget())

        # Bind mousewheel
        def on_mousewheel(event):
            self.main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.main_canvas.bind_all("<MouseWheel>", on_mousewheel)

        # Inner padding frame
        inner = tk.Frame(self.content_frame, bg=COLORS["bg_primary"], padx=24, pady=16)
        inner.pack(fill="both", expand=True)

        # ---- Mode Tabs ----
        tabs_frame = tk.Frame(inner, bg=COLORS["bg_secondary"], bd=0, relief="flat")
        tabs_frame.pack(pady=(0, 20))

        # Use custom styling for tabs
        self.mode_tabs = {}
        for mode_key, label in [("focus", "🍅 专注"), ("short_break", "☕ 短休息"), ("long_break", "🌿 长休息")]:
            btn = tk.Button(tabs_frame, text=label, command=lambda m=mode_key: self.switch_mode(m),
                            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
                            font=("Microsoft YaHei", 10), bd=0, relief="flat",
                            activebackground=COLORS["bg_tertiary"], activeforeground=COLORS["text_primary"],
                            padx=14, pady=6, cursor="hand2")
            btn.pack(side="left", padx=3, pady=3)
            self.mode_tabs[mode_key] = btn

        # ---- Timer Ring (Canvas) ----
        self.timer_frame = tk.Frame(inner, bg=COLORS["bg_primary"])
        self.timer_frame.pack(pady=(0, 16))

        self.timer_canvas = tk.Canvas(self.timer_frame, width=220, height=220,
                                      bg=COLORS["bg_primary"], highlightthickness=0, bd=0)
        self.timer_canvas.pack()

        # Draw the ring
        cx, cy, r = 110, 110, 90
        self._ring_cx, self._ring_cy, self._ring_r = cx, cy, r

        # Background ring
        self.timer_canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                      outline=COLORS["border"], width=8, tags="ring_bg")

        # Progress ring (drawn as arc)
        self.ring_progress = self.timer_canvas.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=90, extent=0, outline=COLORS["accent_focus"], width=8,
            style="arc", tags="ring_progress"
        )

        # Center text
        self.timer_text = self.timer_canvas.create_text(
            cx, cy - 8, text="25:00", fill=COLORS["text_primary"],
            font=("Consolas", 34, "bold"), tags="timer_text"
        )
        self.status_text = self.timer_canvas.create_text(
            cx, cy + 22, text="准备开始", fill=COLORS["text_secondary"],
            font=("Microsoft YaHei", 10), tags="status_text"
        )

        # ---- Session Dots ----
        dots_frame = tk.Frame(inner, bg=COLORS["bg_primary"])
        dots_frame.pack(pady=(0, 16))
        tk.Label(dots_frame, text="今日番茄", bg=COLORS["bg_primary"],
                 fg=COLORS["text_muted"], font=("Microsoft YaHei", 9)).pack(side="left", padx=(0, 8))

        self.dots_canvas = tk.Canvas(dots_frame, width=120, height=14,
                                     bg=COLORS["bg_primary"], highlightthickness=0)
        self.dots_canvas.pack(side="left")
        self._dot_items = []

        # ---- Control Buttons ----
        ctrl_frame = tk.Frame(inner, bg=COLORS["bg_primary"])
        ctrl_frame.pack(pady=(0, 18))

        self.btn_reset = tk.Button(ctrl_frame, text="↺", command=self.reset_session,
                                   bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
                                   font=("Segoe UI", 14), bd=0, relief="flat",
                                   activebackground=COLORS["bg_tertiary"], activeforeground=COLORS["text_primary"],
                                   width=3, height=1, cursor="hand2")
        self.btn_reset.pack(side="left", padx=10)
        self._make_round_btn(self.btn_reset, 42)

        self.btn_start = tk.Button(ctrl_frame, text="▶", command=self.toggle_timer,
                                   bg=COLORS["accent_focus"], fg=COLORS["white"],
                                   font=("Segoe UI", 16, "bold"), bd=0, relief="flat",
                                   activebackground=COLORS["accent_focus"], activeforeground=COLORS["white"],
                                   width=4, height=1, cursor="hand2")
        self.btn_start.pack(side="left", padx=10)
        self._make_round_btn(self.btn_start, 56)

        self.btn_skip = tk.Button(ctrl_frame, text="⏭", command=self.skip_session,
                                  bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
                                  font=("Segoe UI", 14), bd=0, relief="flat",
                                  activebackground=COLORS["bg_tertiary"], activeforeground=COLORS["text_primary"],
                                  width=3, height=1, cursor="hand2")
        self.btn_skip.pack(side="left", padx=10)
        self._make_round_btn(self.btn_skip, 42)

        # ---- Task Section ----
        task_frame = tk.Frame(inner, bg=COLORS["bg_primary"])
        task_frame.pack(fill="x", pady=(0, 12))

        tk.Label(task_frame, text="当前任务", bg=COLORS["bg_primary"],
                 fg=COLORS["text_muted"], font=("Microsoft YaHei", 9, "bold"),
                 anchor="w").pack(fill="x")

        input_frame = tk.Frame(task_frame, bg=COLORS["bg_primary"])
        input_frame.pack(fill="x", pady=(6, 8))

        self.task_var = tk.StringVar()
        self.task_entry = tk.Entry(input_frame, textvariable=self.task_var,
                                   bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
                                   insertbackground=COLORS["text_primary"],
                                   font=("Microsoft YaHei", 10), bd=0, relief="flat",
                                   highlightthickness=1, highlightbackground=COLORS["border"],
                                   highlightcolor=COLORS["accent_focus"])
        self.task_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 6))
        self.task_entry.bind("<Return>", lambda e: self.add_task())

        add_btn = tk.Button(input_frame, text="+", command=self.add_task,
                            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
                            font=("Segoe UI", 14), bd=0, relief="flat",
                            activebackground=COLORS["accent_focus"], activeforeground=COLORS["white"],
                            width=2, cursor="hand2")
        add_btn.pack(side="right")

        # Task list
        self.task_list_frame = tk.Frame(task_frame, bg=COLORS["bg_primary"])
        self.task_list_frame.pack(fill="x")

        # ---- Settings Panel (hidden) ----
        self.settings_frame = tk.Frame(inner, bg=COLORS["bg_secondary"], bd=0, relief="flat")

        tk.Label(self.settings_frame, text="⚙ 设置", bg=COLORS["bg_secondary"],
                 fg=COLORS["text_primary"], font=("Microsoft YaHei", 11, "bold"),
                 anchor="w").pack(fill="x", pady=(12, 10), padx=14)

        self.setting_vars = {}
        settings_fields = [
            ("focus_duration", "专注时长（分钟）", 1, 120),
            ("short_break_duration", "短休息（分钟）", 1, 30),
            ("long_break_duration", "长休息（分钟）", 1, 60),
            ("long_break_interval", "长休息间隔（次）", 1, 10),
        ]

        for key, label, vmin, vmax in settings_fields:
            row = tk.Frame(self.settings_frame, bg=COLORS["bg_secondary"])
            row.pack(fill="x", padx=14, pady=3)
            tk.Label(row, text=label, bg=COLORS["bg_secondary"],
                     fg=COLORS["text_secondary"], font=("Microsoft YaHei", 10),
                     anchor="w").pack(side="left", fill="x", expand=True)

            var = tk.IntVar(value=self.settings[key])
            self.setting_vars[key] = var
            spin = tk.Spinbox(row, textvariable=var, from_=vmin, to=vmax, width=5,
                              bg=COLORS["bg_primary"], fg=COLORS["text_primary"],
                              buttonbackground=COLORS["bg_tertiary"],
                              font=("Consolas", 10), bd=0, relief="flat",
                              justify="center", readonlybackground=COLORS["bg_primary"])
            spin.pack(side="right")

        # Checkboxes
        for key, label in [("auto_start_break", "自动开始休息"), ("auto_start_focus", "自动开始专注")]:
            row = tk.Frame(self.settings_frame, bg=COLORS["bg_secondary"])
            row.pack(fill="x", padx=14, pady=3)
            tk.Label(row, text=label, bg=COLORS["bg_secondary"],
                     fg=COLORS["text_secondary"], font=("Microsoft YaHei", 10),
                     anchor="w").pack(side="left", fill="x", expand=True)
            var = tk.BooleanVar(value=self.settings[key])
            self.setting_vars[key] = var
            cb = tk.Checkbutton(row, variable=var, bg=COLORS["bg_secondary"],
                                activebackground=COLORS["bg_secondary"],
                                selectcolor=COLORS["bg_primary"], fg=COLORS["bg_primary"],
                                bd=0, highlightthickness=0)
            cb.pack(side="right")

        # Volume slider
        row = tk.Frame(self.settings_frame, bg=COLORS["bg_secondary"])
        row.pack(fill="x", padx=14, pady=3)
        tk.Label(row, text="音量", bg=COLORS["bg_secondary"],
                 fg=COLORS["text_secondary"], font=("Microsoft YaHei", 10),
                 anchor="w").pack(side="left", fill="x", expand=True)
        vol_var = tk.IntVar(value=self.settings["volume"])
        self.setting_vars["volume"] = vol_var
        scale = tk.Scale(row, variable=vol_var, from_=0, to=100, orient="horizontal",
                         bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
                         highlightthickness=0, bd=0, length=100,
                         activebackground=COLORS["bg_tertiary"],
                         troughcolor=COLORS["bg_primary"])
        scale.pack(side="right")

        save_btn = tk.Button(self.settings_frame, text="保存设置", command=self._save_settings,
                             bg=COLORS["accent_focus"], fg=COLORS["white"],
                             font=("Microsoft YaHei", 10, "bold"), bd=0, relief="flat",
                             activebackground=COLORS["accent_focus"], activeforeground=COLORS["white"],
                             padx=20, pady=6, cursor="hand2")
        save_btn.pack(pady=(10, 12))

        # ---- Footer ----
        footer = tk.Frame(inner, bg=COLORS["bg_primary"])
        footer.pack(side="bottom", fill="x", pady=(8, 0))

        self.btn_settings = tk.Button(footer, text="⚙", command=self._toggle_settings,
                                      bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
                                      font=("Segoe UI", 12), bd=0, relief="flat",
                                      activebackground=COLORS["bg_tertiary"], activeforeground=COLORS["text_primary"],
                                      width=2, cursor="hand2")
        self.btn_settings.pack(side="left", padx=(0, 6))

        self.btn_history = tk.Button(footer, text="📊", command=self._show_history,
                                     bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
                                     font=("Segoe UI", 12), bd=0, relief="flat",
                                     activebackground=COLORS["bg_tertiary"], activeforeground=COLORS["text_primary"],
                                     width=2, cursor="hand2")
        self.btn_history.pack(side="left")

        # Info label
        self.info_label = tk.Label(footer, text="空格=开始/暂停  R=重置  S=跳过  1/2/3=切换模式",
                                   bg=COLORS["bg_primary"], fg=COLORS["text_muted"],
                                   font=("Microsoft YaHei", 7), anchor="e")
        self.info_label.pack(side="right")

    def _make_round_btn(self, btn, size):
        """Make a button appear round by setting width/height."""
        btn.configure(width=int(size / 18), height=1)

    def _toggle_pin(self):
        self.settings["always_on_top"] = not self.settings["always_on_top"]
        self.attributes("-topmost", self.settings["always_on_top"])
        self.btn_pin.configure(
            fg=COLORS["accent_focus"] if self.settings["always_on_top"] else COLORS["text_secondary"]
        )
        save_json(SETTINGS_FILE, self.settings)

    # ---- Timer Logic ----
    def _get_mode_duration(self):
        if self.mode == "focus":
            return self.settings["focus_duration"] * 60
        elif self.mode == "short_break":
            return self.settings["short_break_duration"] * 60
        else:
            return self.settings["long_break_duration"] * 60

    def switch_mode(self, mode):
        if mode == self.mode and self.timer_state != "idle":
            return
        self._stop_timer_thread()
        self.mode = mode
        self.timer_state = "idle"
        self.total_time = self._get_mode_duration()
        self.time_left = self.total_time
        self._apply_theme_to_mode()
        self._update_mode_tabs()
        self.update_timer_display()
        self.update_ring()
        self.update_start_button()
        self._update_status("准备开始")

    def _apply_theme_to_mode(self):
        colors = {
            "focus": COLORS["accent_focus"],
            "short_break": COLORS["accent_break"],
            "long_break": COLORS["accent_long_break"],
        }
        self._current_accent = colors.get(self.mode, COLORS["accent_focus"])
        # Update the ring progress color
        self.timer_canvas.itemconfig(self.ring_progress, outline=self._current_accent)

    def _update_mode_tabs(self):
        for m, btn in self.mode_tabs.items():
            if m == self.mode:
                btn.configure(bg=COLORS["bg_tertiary"], fg=COLORS["text_primary"])
            else:
                btn.configure(bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"])

    def update_timer_display(self):
        mins = self.time_left // 60
        secs = self.time_left % 60
        text = f"{mins:02d}:{secs:02d}"
        self.timer_canvas.itemconfig(self.timer_text, text=text)

    def update_ring(self):
        progress = self.time_left / self.total_time if self.total_time > 0 else 0
        extent = -359.999 * progress  # negative for clockwise from 12 o'clock
        self.timer_canvas.itemconfig(self.ring_progress, start=90, extent=extent)

    def update_start_button(self):
        if self.timer_state == "running":
            self.btn_start.configure(text="⏸", bg=COLORS["accent_break"])
        else:
            self.btn_start.configure(text="▶", bg=self._current_accent)

    def _update_status(self, text):
        self.timer_canvas.itemconfig(self.status_text, text=text)

    def update_session_dots(self):
        """Draw dots for current cycle progress."""
        self.dots_canvas.delete("dot")
        interval = self.settings["long_break_interval"]
        # Determine completed count in current cycle
        completed = self.pomodoro_cycle % interval
        if self.mode != "focus" and self.pomodoro_cycle > 0 and completed == 0:
            completed = interval  # just finished a full cycle
        elif completed == 0 and self.pomodoro_cycle > 0:
            completed = interval

        for i in range(interval):
            x = 8 + i * 13
            y = 7
            r = 4
            if i < completed:
                self.dots_canvas.create_oval(x - r, y - r, x + r, y + r,
                                             fill=COLORS["accent_focus"],
                                             outline=COLORS["accent_focus"],
                                             tags="dot")
            else:
                self.dots_canvas.create_oval(x - r, y - r, x + r, y + r,
                                             fill="",
                                             outline=COLORS["border"],
                                             width=2, tags="dot")

    def toggle_timer(self):
        if self.timer_state == "running":
            self._pause()
        else:
            self._start()

    def _start(self):
        self.timer_state = "running"
        self.update_start_button()

        if self.mode == "focus":
            self._update_status("正在专注…")
        else:
            self._update_status("休息中…")

        self._stop_timer = False
        self.timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self.timer_thread.start()

    def _pause(self):
        self._stop_timer_thread()
        self.timer_state = "paused"
        self.update_start_button()
        self._update_status("已暂停")

    def _stop_timer_thread(self):
        if self.timer_thread and self.timer_thread.is_alive():
            self._stop_timer = True
            self.timer_thread.join(timeout=1.5)
            self.timer_thread = None

    def _timer_loop(self):
        """Runs in a background thread. Updates time_left every second."""
        while not self._stop_timer and self.time_left > 0:
            time.sleep(1)
            if self._stop_timer:
                return
            self.time_left -= 1
            # Schedule UI updates on the main thread
            self.after(0, self._on_timer_tick)

        if not self._stop_timer and self.time_left <= 0:
            self.after(0, self._on_session_complete)

    def _on_timer_tick(self):
        self.update_timer_display()
        self.update_ring()

    def _on_session_complete(self):
        self._stop_timer = True
        self._play_sound()

        if self.mode == "focus":
            self.pomodoros_today += 1
            self.pomodoro_cycle += 1
            self.update_session_dots()
            self._save_history()

            self._show_toast("🍅 专注完成！",
                             f"太棒了！已完成 {self.pomodoros_today} 个番茄。休息一下吧~")

            # Determine next break
            if self.pomodoro_cycle % self.settings["long_break_interval"] == 0:
                next_mode = "long_break"
                msg = "该长休息了~"
            else:
                next_mode = "short_break"
                msg = "休息一下~"

            self.switch_mode(next_mode)
            self._update_status(msg)

            if self.settings["auto_start_break"]:
                self.after(500, self._start)
        else:
            # Break completed
            bk_type = "长休息" if self.mode == "long_break" else "短休息"
            self._show_toast("⏰ 休息结束",
                             f"{bk_type}时间到！准备开始新的专注吧~")

            self.switch_mode("focus")
            self._update_status("准备开始新的专注")

            if self.settings["auto_start_focus"]:
                self.after(500, self._start)

    def reset_session(self):
        self._stop_timer_thread()
        self.timer_state = "idle"
        self.total_time = self._get_mode_duration()
        self.time_left = self.total_time
        self.update_timer_display()
        self.update_ring()
        self.update_start_button()
        self._update_status("准备开始")

    def skip_session(self):
        self._stop_timer_thread()

        if self.mode == "focus":
            self.pomodoro_cycle += 1
            if self.pomodoro_cycle % self.settings["long_break_interval"] == 0:
                self.switch_mode("long_break")
            else:
                self.switch_mode("short_break")
        else:
            self.switch_mode("focus")

    # ---- Sound ----
    def _play_sound(self):
        """Play a notification sound using winsound."""
        vol = self.settings["volume"] / 100.0
        if vol <= 0:
            return

        def _play():
            # Two-tone beep
            freq1, dur1 = 880, 150
            freq2, dur2 = 1100, 200
            try:
                winsound.Beep(freq1, dur1)
                winsound.Beep(freq2, dur2)
            except Exception:
                winsound.MessageBeep()

        threading.Thread(target=_play, daemon=True).start()

    # ---- Toast Notification ----
    def _show_toast(self, title, message):
        """Show a popup notification (non-blocking, from main thread)."""
        def _show():
            # Flash the taskbar by briefly changing the title
            orig_title = self.title()
            self.title(f"🔔 {title}")
            self.after(1000, lambda: self.title(orig_title))

            # Bring window to front briefly
            self.lift()
            self.focus_force()
            self.after(300, lambda: self.attributes("-topmost", self.settings["always_on_top"]))

        self.after(0, _show)

    # ---- Task Management ----
    def add_task(self):
        text = self.task_var.get().strip()
        if not text:
            return
        task = {"id": int(time.time() * 1000), "text": text, "done": False}
        self.tasks.append(task)
        self.task_var.set("")
        self._render_tasks()

    def _toggle_task(self, task_id):
        for t in self.tasks:
            if t["id"] == task_id:
                t["done"] = not t["done"]
                break
        self._render_tasks()

    def _delete_task(self, task_id):
        self.tasks = [t for t in self.tasks if t["id"] != task_id]
        self._render_tasks()

    def _render_tasks(self):
        for widget in self.task_list_frame.winfo_children():
            widget.destroy()

        if not self.tasks:
            lbl = tk.Label(self.task_list_frame, text="暂无任务，添加一个吧~",
                           bg=COLORS["bg_primary"], fg=COLORS["text_muted"],
                           font=("Microsoft YaHei", 9), anchor="w")
            lbl.pack(fill="x", pady=(0, 4))
            return

        for task in self.tasks[-10:]:  # show last 10
            row = tk.Frame(self.task_list_frame, bg=COLORS["bg_primary"])
            row.pack(fill="x", pady=1)

            # Check circle
            cb_size = 16
            cb = tk.Canvas(row, width=cb_size, height=cb_size,
                           bg=COLORS["bg_primary"], highlightthickness=0, cursor="hand2")
            cb.pack(side="left", padx=(0, 8))

            if task["done"]:
                cb.create_oval(2, 2, cb_size - 2, cb_size - 2,
                               fill=COLORS["accent_break"], outline=COLORS["accent_break"])
                cb.create_text(cb_size // 2, cb_size // 2, text="✓",
                               fill="white", font=("Segoe UI", 8, "bold"))
            else:
                cb.create_oval(2, 2, cb_size - 2, cb_size - 2,
                               fill="", outline=COLORS["text_muted"], width=2)

            cb.bind("<Button-1>", lambda e, tid=task["id"]: self._toggle_task(tid))

            # Text
            text_widget = tk.Label(row, text=task["text"][:50], bg=COLORS["bg_primary"],
                                   fg=COLORS["text_muted"] if task["done"] else COLORS["text_primary"],
                                   font=("Microsoft YaHei", 10),
                                   anchor="w")
            if task["done"]:
                text_widget.configure(font=("Microsoft YaHei", 10, "overstrike"))
            text_widget.pack(side="left", fill="x", expand=True)

            # Delete button
            del_btn = tk.Button(row, text="✕", command=lambda tid=task["id"]: self._delete_task(tid),
                                bg=COLORS["bg_primary"], fg=COLORS["text_muted"],
                                font=("Segoe UI", 8), bd=0, relief="flat",
                                activebackground=COLORS["accent_focus"], activeforeground=COLORS["white"],
                                width=2, cursor="hand2")
            del_btn.pack(side="right")

            # Re-color on hover
            self._set_hover(del_btn, COLORS["accent_focus"], COLORS["white"])

    # ---- Settings ----
    def _toggle_settings(self):
        if self._settings_visible:
            self.settings_frame.pack_forget()
            self.btn_settings.configure(fg=COLORS["text_secondary"])
        else:
            self.settings_frame.pack(after=self.task_list_frame, fill="x", pady=(0, 8))
            # Update form values
            for key, var in self.setting_vars.items():
                if key in self.settings:
                    var.set(self.settings[key])
            self.btn_settings.configure(fg=COLORS["accent_focus"])
        self._settings_visible = not self._settings_visible

    def _save_settings(self):
        for key, var in self.setting_vars.items():
            if isinstance(self.settings.get(key), bool):
                self.settings[key] = bool(var.get())
            else:
                self.settings[key] = var.get()

        save_json(SETTINGS_FILE, self.settings)

        # Apply settings
        if self.timer_state == "idle":
            self.total_time = self._get_mode_duration()
            self.time_left = self.total_time
            self.update_timer_display()
            self.update_ring()

        self.update_session_dots()
        self._toggle_settings()

        # Update always-on-top
        self.attributes("-topmost", self.settings["always_on_top"])
        self.btn_pin.configure(
            fg=COLORS["accent_focus"] if self.settings["always_on_top"] else COLORS["text_secondary"]
        )

    # ---- History ----
    def _load_today(self):
        today = date.today().isoformat()
        if today in self.history:
            self.pomodoros_today = self.history[today].get("pomodoros", 0)
            self.tasks = self.history[today].get("tasks", [])
            # Determine current cycle position
            interval = self.settings["long_break_interval"]
            self.pomodoro_cycle = self.pomodoros_today % interval

        self._render_tasks()

    def _save_history(self):
        today = date.today().isoformat()
        self.history[today] = {
            "pomodoros": self.pomodoros_today,
            "tasks": self.tasks,
        }
        # Keep last 90 days
        keys = sorted(self.history.keys())
        while len(keys) > 90:
            del self.history[keys.pop(0)]
        save_json(HISTORY_FILE, self.history)

    def _show_history(self):
        if self._history_window and self._history_window.winfo_exists():
            self._history_window.lift()
            self._history_window.focus_force()
            return

        win = tk.Toplevel(self)
        win.title("历史记录")
        win.configure(bg=COLORS["bg_secondary"])
        win.geometry("340x400")
        win.resizable(False, False)
        win.transient(self)

        # Center relative to main window
        win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 340) // 2
        y = self.winfo_y() + (self.winfo_height() - 400) // 2
        win.geometry(f"+{x}+{y}")

        # Title
        tk.Label(win, text="📊 历史记录", bg=COLORS["bg_secondary"],
                 fg=COLORS["text_primary"], font=("Microsoft YaHei", 13, "bold"),
                 anchor="w").pack(fill="x", padx=16, pady=(14, 10))

        # List
        list_frame = tk.Frame(win, bg=COLORS["bg_secondary"])
        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        canvas = tk.Canvas(list_frame, bg=COLORS["bg_secondary"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=COLORS["bg_secondary"])

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind mousewheel for history window
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        win.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"))

        dates = sorted(self.history.keys(), reverse=True)

        if not dates:
            tk.Label(scroll_frame, text="暂无记录", bg=COLORS["bg_secondary"],
                     fg=COLORS["text_muted"], font=("Microsoft YaHei", 10),
                     anchor="w").pack(fill="x", pady=4)
        else:
            for d in dates:
                row = tk.Frame(scroll_frame, bg=COLORS["bg_secondary"])
                row.pack(fill="x", pady=3)

                # Date
                try:
                    dt = date.fromisoformat(d)
                    date_str = dt.strftime("%Y-%m-%d")
                except Exception:
                    date_str = d

                tk.Label(row, text=date_str, bg=COLORS["bg_secondary"],
                         fg=COLORS["text_secondary"], font=("Consolas", 10),
                         anchor="w").pack(side="left")

                # Count
                count = self.history[d].get("pomodoros", 0)
                dots = "🍅 " * min(count, 20)
                if count > 20:
                    dots += f"+{count - 20}"

                tk.Label(row, text=f"× {count}", bg=COLORS["bg_secondary"],
                         fg=COLORS["accent_focus"], font=("Microsoft YaHei", 10, "bold"),
                         anchor="e").pack(side="right")

                # Separator
                sep = tk.Frame(scroll_frame, bg=COLORS["border"], height=1)
                sep.pack(fill="x", pady=1)

        # Close button
        close_btn = tk.Button(win, text="关闭", command=win.destroy,
                              bg=COLORS["bg_tertiary"], fg=COLORS["text_primary"],
                              font=("Microsoft YaHei", 10), bd=0, relief="flat",
                              activebackground=COLORS["accent_focus"], activeforeground=COLORS["white"],
                              padx=16, pady=6, cursor="hand2")
        close_btn.pack(pady=(0, 14))

        self._history_window = win

    # ---- Keyboard Shortcuts ----
    def _is_editing(self):
        """Check if focus is on an input widget — suppress shortcuts when typing."""
        focused = self.focus_get()
        if focused is None:
            return False
        return isinstance(focused, (tk.Entry, tk.Spinbox, tk.Scale, tk.Text))

    def _bind_events(self):
        # Click outside input → defocus (so shortcuts always work)
        self.bind_all("<Button-1>", self._on_global_click)

        # Only trigger shortcuts when not editing text
        self.bind("<space>", lambda e: self._is_editing() or self.toggle_timer())

        for key in ("<Key-r>", "<Key-R>"):
            self.bind(key, lambda e: self._is_editing() or self.reset_session())
        for key in ("<Key-s>", "<Key-S>"):
            self.bind(key, lambda e: self._is_editing() or self.skip_session())

        self.bind("<Key-1>", lambda e: self._is_editing() or self.switch_mode("focus"))
        self.bind("<Key-2>", lambda e: self._is_editing() or self.switch_mode("short_break"))
        self.bind("<Key-3>", lambda e: self._is_editing() or self.switch_mode("long_break"))

        # Save settings on window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_global_click(self, event):
        """Move focus away from input when clicking elsewhere."""
        if not isinstance(event.widget, (tk.Entry, tk.Spinbox, tk.Text)):
            self.focus_set()

    def _on_close(self):
        self._stop_timer_thread()
        save_json(SETTINGS_FILE, self.settings)
        self._save_history()
        self.destroy()

    def destroy(self):
        self._stop_timer_thread()
        save_json(SETTINGS_FILE, self.settings)
        self._save_history()
        super().destroy()


# ============================================================
# Entry Point
# ============================================================
def main():
    app = PomodoroTimer()
    app.mainloop()


if __name__ == "__main__":
    main()
