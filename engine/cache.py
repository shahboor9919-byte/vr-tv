from typing import Any, Optional
import time

class SimpleCache:
    def __init__(self):
        self.data = {}

    async def get(self, key: str) -> Optional[Any]:
        item = self.data.get(key)
        if item:
            if item['expiry'] is None or item['expiry'] > time.time():
                return item['value']
            else:
                del self.data[key]
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        expiry = time.time() + ttl if ttl else None
        self.data[key] = {'value': value, 'expiry': expiry}

channel_cache = SimpleCache()
stream_cache = SimpleCache()
