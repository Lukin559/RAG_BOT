# bot/state.py
import asyncio

class SupportStore:
    """Потокобезопасное in‑memory хранилище обращений."""
    def __init__(self):
        self._lock = asyncio.Lock()
        self._sessions: set[int] = set()     # user_ids

    async def enter(self, user_id: int):
        async with self._lock:
            self._sessions.add(user_id)

    async def leave(self, user_id: int):
        async with self._lock:
            self._sessions.discard(user_id)

    async def active(self, user_id: int) -> bool:
        async with self._lock:
            return user_id in self._sessions


support_store = SupportStore()