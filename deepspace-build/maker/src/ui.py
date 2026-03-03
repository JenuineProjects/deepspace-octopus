"""
DeepSpace Tkinter UI
Minimal dark-themed always-on-top focus timer window.
"""

import logging
import tkinter as tk
from collections import deque
from typing import Deque

from timer import FocusTimer, TimerState
from blocker import MockDistractionsBlocker
from session_store import SessionStore

logger = logging.getLogger("deepspace.ui")


# ---- colour palette --------------------------------------------------------

BG = "#1a1a2e"
BG_CARD = "#16213e"
FG = "#e0e0e0"
ACCENT = "#0f3460"
ACCENT_ACTIVE = "#533483"
BTN_START = "#00b894"
BTN_PAUSE = "#fdcb6e"
BTN_STOP = "#d63031"
BTN_FG = "#ffffff"
TIMER_FG = "#00cec9"
DIM = "#636e72"


def _fmt_time(seconds: int) -> str:
    m, s = divmod(max(seconds, 0), 60)
    return f"{m:02d}:{s:02d}"


class DeepSpaceUI:
    """Main application window."""

    FOCUS_DURATION = 25 * 60  # 25 minutes in seconds

    def __init__(self) -> None:
        # ---- core components ------------------------------------------------
        self._store = SessionStore()
        self._blocker = MockDistractionsBlocker()
        self._timer = FocusTimer(
            duration_seconds=self.FOCUS_DURATION,
            on_tick=self._on_tick,
            on_state_change=self._on_state_change,
            on_complete=self._on_complete,
        )

        # ---- root window ----------------------------------------------------
        self._root = tk.Tk()
        self._root.title("DeepSpace")
        self._root.configure(bg=BG)
        self._root.resizable(False, False)
        self._root.attributes("-topmost", True)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Centre the window
        w, h = 340, 420
        sx = self._root.winfo_screenwidth() // 2 - w // 2
        sy = self._root.winfo_screenheight() // 2 - h // 2
        self._root.geometry(f"{w}x{h}+{sx}+{sy}")

        # Track pending after() ids for cleanup (bounded to avoid unbounded growth)
        self._after_ids: Deque[str] = deque(maxlen=200)

        self._build_widgets()
        self._show_idle()

    # ---- widget construction -----------------------------------------------

    def _build_widgets(self) -> None:
        # Title
        tk.Label(
            self._root, text="DeepSpace", font=("Helvetica", 20, "bold"),
            bg=BG, fg=FG,
        ).pack(pady=(18, 2))

        tk.Label(
            self._root, text="Focus Timer", font=("Helvetica", 10),
            bg=BG, fg=DIM,
        ).pack()

        # Timer card
        self._card = tk.Frame(self._root, bg=BG_CARD, bd=0, highlightthickness=0)
        self._card.pack(padx=24, pady=18, fill="x")

        self._time_label = tk.Label(
            self._card, text=_fmt_time(self.FOCUS_DURATION),
            font=("Courier", 48, "bold"), bg=BG_CARD, fg=TIMER_FG,
        )
        self._time_label.pack(pady=(18, 4))

        self._status_label = tk.Label(
            self._card, text="Ready to focus", font=("Helvetica", 11),
            bg=BG_CARD, fg=DIM,
        )
        self._status_label.pack(pady=(0, 14))

        # Button area
        self._btn_frame = tk.Frame(self._root, bg=BG)
        self._btn_frame.pack(pady=6)

        self._btn_primary = tk.Button(
            self._btn_frame, text="Start Focus", width=16, font=("Helvetica", 12, "bold"),
            bg=BTN_START, fg=BTN_FG, activebackground=ACCENT_ACTIVE,
            activeforeground=BTN_FG, relief="flat", bd=0, cursor="hand2",
            command=self._on_start,
        )
        self._btn_primary.pack(pady=4)

        self._btn_secondary = tk.Button(
            self._btn_frame, text="", width=16, font=("Helvetica", 11),
            bg=BTN_STOP, fg=BTN_FG, activebackground=ACCENT,
            activeforeground=BTN_FG, relief="flat", bd=0, cursor="hand2",
        )
        # secondary button is hidden initially
        self._btn_secondary.pack(pady=4)
        self._btn_secondary.pack_forget()

        # Stats footer
        self._stats_label = tk.Label(
            self._root, text="", font=("Helvetica", 9),
            bg=BG, fg=DIM,
        )
        self._stats_label.pack(side="bottom", pady=(0, 12))
        self._update_stats()

    # ---- view helpers ------------------------------------------------------

    def _show_idle(self) -> None:
        self._time_label.config(text=_fmt_time(self.FOCUS_DURATION), fg=TIMER_FG)
        self._status_label.config(text="Ready to focus")
        self._btn_primary.config(text="Start Focus", bg=BTN_START, command=self._on_start)
        self._btn_secondary.pack_forget()

    def _show_focusing(self) -> None:
        self._status_label.config(text="Focusing...")
        self._btn_primary.config(text="Pause", bg=BTN_PAUSE, command=self._on_pause)
        self._btn_secondary.config(text="Stop", bg=BTN_STOP, command=self._on_stop)
        self._btn_secondary.pack(pady=4)

    def _show_paused(self) -> None:
        self._status_label.config(text="Paused")
        self._btn_primary.config(text="Resume", bg=BTN_START, command=self._on_resume)
        self._btn_secondary.config(text="Stop", bg=BTN_STOP, command=self._on_stop)
        self._btn_secondary.pack(pady=4)

    def _show_completed(self) -> None:
        self._time_label.config(text="00:00", fg=BTN_START)
        self._status_label.config(text="Session complete!")
        self._btn_primary.config(text="Start Again", bg=BTN_START, command=self._on_restart)
        self._btn_secondary.pack_forget()
        self._update_stats()

    def _update_stats(self) -> None:
        today = self._store.today_count()
        total = self._store.total_focus_minutes()
        self._stats_label.config(
            text=f"Today: {today} session{'s' if today != 1 else ''}  |  "
                 f"Total: {total:.0f} min focused"
        )

    # ---- button callbacks --------------------------------------------------

    def _on_start(self) -> None:
        try:
            self._blocker.activate()
            self._timer.start()
        except Exception:
            logger.exception("Error in _on_start")
            self._show_idle()

    def _on_pause(self) -> None:
        try:
            self._timer.pause()
        except Exception:
            logger.exception("Error in _on_pause")
            self._show_idle()

    def _on_resume(self) -> None:
        try:
            self._timer.resume()
        except Exception:
            logger.exception("Error in _on_resume")
            self._show_idle()

    def _on_stop(self) -> None:
        try:
            self._blocker.deactivate()
            self._timer.stop()
        except Exception:
            logger.exception("Error in _on_stop")
        finally:
            self._show_idle()
            self._update_stats()

    def _on_restart(self) -> None:
        self._timer.reset()
        self._on_start()

    # ---- timer callbacks (called from background thread) -------------------

    def _on_tick(self, remaining: int) -> None:
        aid = self._root.after(0, self._time_label.config, {"text": _fmt_time(remaining)})
        self._after_ids.append(aid)

    def _on_state_change(self, new_state: TimerState) -> None:
        view_map = {
            TimerState.IDLE: self._show_idle,
            TimerState.FOCUSING: self._show_focusing,
            TimerState.PAUSED: self._show_paused,
            TimerState.COMPLETED: self._show_completed,
        }
        fn = view_map.get(new_state)
        if fn:
            aid = self._root.after(0, fn)
            self._after_ids.append(aid)

    def _on_complete(self) -> None:
        self._blocker.deactivate()
        self._store.record(self.FOCUS_DURATION, completed=True)
        aid = self._root.after(0, self._update_stats)
        self._after_ids.append(aid)

    # ---- lifecycle ---------------------------------------------------------

    def _on_close(self) -> None:
        """Graceful shutdown: cancel pending callbacks, stop timer, destroy window."""
        # Cancel all pending after() callbacks
        for aid in self._after_ids:
            try:
                self._root.after_cancel(aid)
            except Exception:
                pass
        self._after_ids.clear()

        # Shut down timer thread
        self._timer.shutdown()

        # Deactivate blocker if still active
        if self._blocker.is_active:
            self._blocker.deactivate()

        self._root.destroy()

    def run(self) -> None:
        self._root.mainloop()
