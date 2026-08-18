import time
import logging
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

logger = logging.getLogger(__name__)


class AntifraudMiddleware(BaseMiddleware):
    def __init__(self, default_limit: int = 30, window_seconds: int = 60):
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self._requests = {}
        super().__init__()

    async def __call__(self, handler, event, data):
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id

        if user_id:
            now = time.time()
            key = f"{user_id}:{type(event).__name__}"
            if key not in self._requests:
                self._requests[key] = []
            self._requests[key] = [t for t in self._requests[key] if now - t < self.window_seconds]
            if len(self._requests[key]) >= self.default_limit:
                logger.warning(f"Rate limit exceeded for user {user_id}")
                if isinstance(event, Message):
                    await event.answer("⏱ Слишком много запросов. Подождите.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("⏱ Слишком много запросов.", show_alert=True)
                return None
            self._requests[key].append(now)

        return await handler(event, data)
