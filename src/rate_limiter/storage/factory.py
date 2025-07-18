from .base import RateLimitStorage
from .storage_memory import MemoryStorage
from .storage_redis import RedisStorage


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
            return RedisStorage(**kwargs)
        else:
            raise ValueError(f"Unknown storage type: {storage_type}")