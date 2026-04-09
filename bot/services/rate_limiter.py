import random
import asyncio
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self):
        self._flood_counts = {}

    def get_delay(self, account_id, base_min, base_max):
        flood_count = self._flood_counts.get(account_id, 0)
        multiplier = min(2 ** flood_count, 16)
        return random.uniform(base_min * multiplier, base_max * multiplier)

    def record_flood(self, account_id):
        prev = self._flood_counts.get(account_id, 0)
        self._flood_counts[account_id] = prev + 1

    def reset_flood(self, account_id):
        self._flood_counts[account_id] = 0

    async def wait(self, account_id, base_min, base_max):
        delay = self.get_delay(account_id, base_min, base_max)
        await asyncio.sleep(delay)


rate_limiter = RateLimiter()
