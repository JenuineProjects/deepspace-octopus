"""
DeepSpace Distraction Blocker (Mock)
Simulates blocking distracting websites/apps during focus sessions.
All OS-level blocking is mocked via log statements.
"""

import logging
from typing import List, Optional

logger = logging.getLogger("deepspace.blocker")

# Default list of "blocked" distractions (for simulation)
DEFAULT_BLOCKLIST: List[str] = [
    "twitter.com",
    "reddit.com",
    "youtube.com",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "news.ycombinator.com",
]


class MockDistractionsBlocker:
    """Mock blocker that logs activation/deactivation instead of touching the OS."""

    def __init__(self, blocklist: Optional[List[str]] = None):
        self._blocklist = blocklist if blocklist is not None else list(DEFAULT_BLOCKLIST)
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active

    def activate(self) -> None:
        if self._active:
            logger.warning("Blocker already active — ignoring duplicate activate()")
            return
        self._active = True
        logger.info("=== DISTRACTION BLOCKER ACTIVATED ===")
        for site in self._blocklist:
            logger.info("  [BLOCKED] %s", site)
        logger.info("Distraction blocker ON  — %d sites blocked", len(self._blocklist))

    def deactivate(self) -> None:
        if not self._active:
            logger.warning("Blocker already inactive — ignoring duplicate deactivate()")
            return
        self._active = False
        logger.info("=== DISTRACTION BLOCKER DEACTIVATED ===")
        for site in self._blocklist:
            logger.info("  [UNBLOCKED] %s", site)
        logger.info("Distraction blocker OFF — all sites unblocked")

    def add_site(self, site: str) -> None:
        if site not in self._blocklist:
            self._blocklist.append(site)
            logger.info("Added %s to blocklist", site)

    def remove_site(self, site: str) -> None:
        if site in self._blocklist:
            self._blocklist.remove(site)
            logger.info("Removed %s from blocklist", site)
