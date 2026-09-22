"""
Limitation des tentatives de connexion (protection contre le bruteforce).
Stockage en mémoire : suffisant pour une instance unique de l'API.
"""
import threading
import time
from collections import deque


class LoginRateLimiter:
    """Bloque une clé (IP + identifiant) après `max_attempts` échecs sur `window_seconds`."""

    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._failures: dict[str, deque] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque:
        attempts = self._failures.setdefault(key, deque())
        while attempts and now - attempts[0] > self.window_seconds:
            attempts.popleft()
        return attempts

    def retry_after(self, key: str) -> int:
        """Secondes à attendre avant une nouvelle tentative (0 si autorisé)."""
        now = time.monotonic()
        with self._lock:
            attempts = self._prune(key, now)
            if len(attempts) < self.max_attempts:
                return 0
            return max(1, int(self.window_seconds - (now - attempts[0])))

    def register_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._prune(key, now).append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()
