import time
from collections import defaultdict


class RateLimiter:
    def __init__(self, max_messages=5, window_seconds=60):
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self._history = defaultdict(list)

    def is_limited(self, user_id):
        now = time.time()
        window_start = now - self.window_seconds
        timestamps = self._history[user_id]

        timestamps[:] = [t for t in timestamps if t > window_start]

        if len(timestamps) >= self.max_messages:
            return True

        timestamps.append(now)
        return False

    def get_remaining(self, user_id):
        now = time.time()
        window_start = now - self.window_seconds
        timestamps = self._history[user_id]
        timestamps[:] = [t for t in timestamps if t > window_start]
        return self.max_messages - len(timestamps)

    def clear(self, user_id):
        self._history.pop(user_id, None)


rate_limiter = RateLimiter()
