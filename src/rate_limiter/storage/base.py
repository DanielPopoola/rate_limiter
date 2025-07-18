from abc import ABC, abstractmethod
from typing import Tuple, Optional


class RateLimitStorage(ABC):
    """Abstract base class for rate limit storage backends"""

    @abstractmethod
    def get_bucket_state(self, key: str) -> Optional[Tuple[int | float, float]]:
        """
        Get the current state of a token bucket.

        Args:
            key: The user/bucket identifier

        Returns:
            Tuple of (tokens, timsetamp) or None if bucket doesn't exist
        """
        pass

    @abstractmethod
    def set_bucket_state(self, key: str, tokens: int | float, timestamp: float) -> None:
        """
        Set the state of a token bucket.
        
        Args:
            key: The user/bucket identifier
            tokens: Current token count
            timestamp: Last update timestamp
        """
        pass

    @abstractmethod
    def atomic_consume_token(self, key: str, capacity: int | float, refill_rate: int | float, refill_time: float) -> bool:
        """
        Atomically check if a token can be consumed and consume it if possible.
        This is the critical method that prevents race conditions.

        Args:
            key: The user/bucket identifier
            capacity: Maximum tokens the bucket can hold
            refill_rate: How many tokens to add per refill period
            refill_time: Seconds between refills
            
        Returns:
            True if token was consumed, False if rate limit exceeded
        """
        pass