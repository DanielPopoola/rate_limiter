from base import RateLimitStorage
from typing import Optional, Tuple
import time


class MemoryStorage(RateLimitStorage):
    """In-memory storage backend"""
    def __init__(self) -> None:
        self.buckets = {}

    def get_bucket_state(self, key: str) -> Optional[Tuple[float, float]]:
        return self.buckets.get(key)
    
    def set_bucket_state(self, key: str, tokens: int | float, timestamp: float) -> None:
        self.buckets[key] = (tokens, timestamp)

    def atomic_consume_token(self, key: str, capacity: int | float, refill_rate: int | float, refill_time: float) -> bool:
        """
        Note: This is NOT truly atomic for concurrent access,
        but works fine for single-threaded scenarios.
        """
        current_time = time.time()

        if key not in self.buckets:
            self.buckets[key] = (capacity, current_time)

        tokens, last_time = self.buckets[key]

        # Calculate refill
        elapsed = current_time - last_time
        added_tokens = (elapsed / refill_time) * refill_rate
        tokens = min(capacity, tokens + added_tokens)

        if tokens >= 1:
            self.buckets[key] = (tokens - 1, current_time)
            return True
        else:
            self.buckets[key] = (tokens, current_time)
            return False
        