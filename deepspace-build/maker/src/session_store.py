"""
DeepSpace Session Store
Persists completed focus sessions to a local JSON file.
"""

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List


_DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions.json")


class SessionStore:
    """Thread-safe JSON-backed session history."""

    def __init__(self, path: str = _DEFAULT_PATH):
        self._path = path
        self._lock = threading.Lock()
        self._sessions: List[Dict[str, Any]] = self._load()

    # ---- public API --------------------------------------------------------

    def record(self, duration_seconds: int, completed: bool = True) -> Dict[str, Any]:
        """Record a session and return the entry."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": duration_seconds,
            "completed": completed,
        }
        with self._lock:
            self._sessions.append(entry)
            self._save()
        return entry

    def history(self) -> List[Dict[str, Any]]:
        """Return a copy of all sessions."""
        with self._lock:
            return list(self._sessions)

    def today_count(self) -> int:
        """Number of completed sessions recorded today (UTC)."""
        today = datetime.now(timezone.utc).date().isoformat()
        with self._lock:
            return sum(
                1
                for s in self._sessions
                if s.get("completed") and s["timestamp"].startswith(today)
            )

    def total_focus_minutes(self) -> float:
        """Total completed focus time across all sessions, in minutes."""
        with self._lock:
            return sum(
                s["duration_seconds"] / 60.0
                for s in self._sessions
                if s.get("completed")
            )

    # ---- persistence -------------------------------------------------------

    def _load(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self._path):
            return []
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            pass
        return []

    def _save(self) -> None:
        tmp = self._path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._sessions, f, indent=2)
        # Atomic-ish rename (os.replace works whether or not dest exists)
        os.replace(tmp, self._path)
