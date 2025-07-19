from .base import RateLimitStorage
from .storage_memory import MemoryStorage
from .storage_redis import RedisStorage
import redis


class StorageFactory:
    """Factory to create storage backends based on configuration"""
    
    @staticmethod
    def create_storage(storage_type: str = "memory", **kwargs) -> RateLimitStorage:
        """
        Create a storage backend.
        
        Args:
            storage_type: Either "memory" or "redis"
            **kwargs: Additional arguments for the storage backend
            
        Returns:
            A storage backend instance
        """
        if storage_type == "memory":
            return MemoryStorage()
        elif storage_type == "redis":
            # Extract Redis-specific connection parameters
            host = kwargs.pop("host", "localhost")
            port = kwargs.pop("port", 6379)
            db = kwargs.pop("db", 0)
            key_prefix = kwargs.pop("key_prefix", "rate_limit:")

            # Create Redis client
            redis_client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
            return RedisStorage(redis_client=redis_client, key_prefix=key_prefix)
        else:
            raise ValueError(f"Unknown storage type: {storage_type}")