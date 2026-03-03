"""
DeepSpace Timer Engine
State machine: idle -> focusing -> paused -> completed
Thread-safe countdown timer with pause/resume/stop.
"""

import logging
import threading
import time
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger("deepspace.timer")


class TimerState(Enum):
    IDLE = "idle"
    FOCUSING = "focusing"
    PAUSED = "paused"
    COMPLETED = "completed"


# Valid transitions: (from_state, to_state)
_VALID_TRANSITIONS = {
    (TimerState.IDLE, TimerState.FOCUSING),
    (TimerState.FOCUSING, TimerState.PAUSED),
    (TimerState.FOCUSING, TimerState.COMPLETED),
    (TimerState.FOCUSING, TimerState.IDLE),       # stop
    (TimerState.PAUSED, TimerState.FOCUSING),      # resume
    (TimerState.PAUSED, TimerState.IDLE),           # stop from paused
    (TimerState.COMPLETED, TimerState.IDLE),        # reset
}


class FocusTimer:
    """Countdown timer with an explicit state machine."""

    def __init__(
        self,
        duration_seconds: int = 25 * 60,
        on_tick: Optional[Callable[[int], None]] = None,
        on_state_change: Optional[Callable[[TimerState], None]] = None,
        on_complete: Optional[Callable[[], None]] = None,
    ):
        self._total_duration = duration_seconds
        self._remaining = duration_seconds
        self._state = TimerState.IDLE
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # not paused initially
        self._thread: Optional[threading.Thread] = None

        # Callbacks
        self._on_tick = on_tick
        self._on_state_change = on_state_change
        self._on_complete = on_complete

    # ---- properties --------------------------------------------------------

    @property
    def state(self) -> TimerState:
        with self._lock:
            return self._state

    @property
    def remaining(self) -> int:
        with self._lock:
            return self._remaining

    @property
    def total_duration(self) -> int:
        return self._total_duration

    # ---- state transitions -------------------------------------------------

    def _set_state(self, new_state: TimerState) -> None:
        """Transition to *new_state*, raising on invalid moves."""
        with self._lock:
            pair = (self._state, new_state)
            if pair not in _VALID_TRANSITIONS:
                raise RuntimeError(
                    f"Invalid transition: {self._state.value} -> {new_state.value}"
                )
            self._state = new_state
        # NOTE: Callback is intentionally fired outside the lock to avoid
        # holding the lock during potentially slow UI updates.  This means a
        # rapid sequence of transitions could deliver callbacks slightly out of
        # order.  Acceptable for the current tkinter after(0, ...) usage but
        # should be revisited if stricter ordering guarantees are needed.
        if self._on_state_change:
            self._on_state_change(new_state)

    # ---- public API --------------------------------------------------------

    def start(self) -> None:
        """Begin a new focus session."""
        # Ensure any previous timer thread is fully stopped before resetting
        # state, preventing a data race on self._remaining (Issue #3).
        self._join_thread()
        with self._lock:
            self._remaining = self._total_duration
        self._stop_event.clear()
        self._pause_event.set()
        self._set_state(TimerState.FOCUSING)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def pause(self) -> None:
        self._pause_event.clear()
        self._set_state(TimerState.PAUSED)

    def resume(self) -> None:
        self._set_state(TimerState.FOCUSING)
        self._pause_event.set()

    def stop(self) -> None:
        """Stop the timer and return to idle (from focusing or paused)."""
        current = self.state
        if current in (TimerState.FOCUSING, TimerState.PAUSED):
            self._stop_event.set()
            self._pause_event.set()  # unblock thread if paused
            self._set_state(TimerState.IDLE)
            self._join_thread()

    def reset(self) -> None:
        """Move from completed back to idle."""
        if self.state == TimerState.COMPLETED:
            self._set_state(TimerState.IDLE)
            self._remaining = self._total_duration

    def shutdown(self) -> None:
        """Force-stop everything for clean exit."""
        self._stop_event.set()
        self._pause_event.set()
        self._join_thread()
        with self._lock:
            self._state = TimerState.IDLE

    # ---- internals ---------------------------------------------------------

    def _join_thread(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2)
            if self._thread.is_alive():
                logger.warning(
                    "Timer thread still alive after join timeout — "
                    "orphaned daemon thread will be cleaned up at process exit"
                )
            self._thread = None

    def _run(self) -> None:
        """Background countdown loop (~1 s resolution)."""
        while not self._stop_event.is_set():
            # honour pause
            self._pause_event.wait(timeout=0.25)
            if self._stop_event.is_set():
                break
            if not self._pause_event.is_set():
                continue

            time.sleep(1)
            if self._stop_event.is_set():
                break

            with self._lock:
                if self._remaining > 0:
                    self._remaining -= 1
                remaining = self._remaining

            if self._on_tick:
                self._on_tick(remaining)

            if remaining <= 0:
                self._set_state(TimerState.COMPLETED)
                if self._on_complete:
                    self._on_complete()
                break
