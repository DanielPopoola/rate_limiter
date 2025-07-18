from functools import wraps
from typing import Optional, Callable, Union
from fastapi import Request, HTTPException
from .algorithms.token_bucket import TokenBucket, parse_rate_limit_string
from .storage.factory import StorageFactory
import asyncio


def rate_limit(
        limit: Union[int, str],
        refill_rate: Optional[float] = None,
        refill_time: Optional[float] = None,
        key_func: Optional[Callable[[Request], str]] = None,
        storage_type: str = "memory",
        storage_config: Optional[dict] = None
):
    """
    Distributed rate limiting decorator that works with Redis or local memory.
    
    Args:
        limit: Either an integer (capacity) or string like "10/minute"
        refill_rate: Tokens to add per refill period (if using numeric format)
        refill_time: Seconds between refills (if using numeric format)
        key_func: Function to extract user identifier from request
        storage_type: "memory" or "redis"
        storage_config: Additional configuration for storage backend
    
    Examples:
        # Local memory (same as before)
        @rate_limit("10/minute")
        
        # Redis storage
        @rate_limit("10/minute", storage_type="redis")
        
        # Redis with custom config
        @rate_limit(
            "10/minute", 
            storage_type="redis",
            storage_config={"host": "localhost", "port": 6379}
        )
    """
    if isinstance(limit, str):
        if refill_rate is not None or refill_time is not None:
            raise ValueError("Cannot specify refill_rate or refill_time with string format")
        capacity, refill_rate, refill_time = parse_rate_limit_string(limit)
    else:
        # Handle numeric format
        capacity = float(limit)
        if refill_rate is None or refill_time is None:
            raise ValueError("Must specify refill_rate and refill_time with numeric format")
    
    storage_config = storage_config or {}
    storage = StorageFactory.create_storage(storage_type, **storage_config)

    bucket = TokenBucket(capacity, refill_rate, refill_time, storage)

    def default_key_func(request) -> str:
        if hasattr(request, 'client') and hasattr(request.client, 'host'):
            return request.client.host
        elif hasattr(request,'remote_addr'):
            return request.remote_addr
        else:
            return "test-client"
        
    get_key = key_func or default_key_func

    def decorator(func):
        is_async = asyncio.iscoroutinefunction(func)
        
        if is_async:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                request = None
                for arg in args:
                    if hasattr(arg, 'client') and hasattr(arg, 'headers'):
                        request = arg
                        break
                if not request:
                    for value in kwargs.values():
                        if hasattr(value, 'client') and hasattr(value, 'headers'):
                            request = value
                            break
                if not request:
                    available_types = [type(arg).__name__ for arg in args] + [type(v).__name__ for v in kwargs.values()]
                    raise ValueError(
                        f"No Request object found in function parameters. "
                        f"Available parameter types: {available_types}. "
                        f"Make sure your function includes 'request: Request' as a parameter."
                    )
                
                user_key = get_key(request)

                if bucket.allow_request(user_key):
                    return await func(*args, **kwargs)
                else:
                    # Get bucket info for error response
                    bucket_info = bucket.get_bucket_info(user_key)
                    
                    # Calculate retry after
                    seconds_per_token = refill_time / refill_rate
                    retry_after = int(seconds_per_token)
                    
                    # Detailed error response
                    headers = {
                        "X-RateLimit-Limit": str(int(capacity)),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(retry_after),
                        "Retry-After": str(retry_after)
                    }
                    
                    raise HTTPException(
                        status_code=429,
                        detail={
                            "message": "Rate limit exceeded",
                            "limit": int(capacity),
                            "remaining": 0,
                            "reset_in_seconds": retry_after,
                            "storage_type": storage_type
                        },
                        headers=headers
                    )
                
            return async_wrapper
        
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                request = None
                for arg in args:
                    if hasattr(arg, 'client') and hasattr(arg, 'headers'):
                        request = arg
                        break
                if not request:
                    for value in kwargs.values():
                        if hasattr(value, 'client') and hasattr(value, 'headers'):
                            request = value
                            break
                if not request:
                    available_types = [type(arg).__name__ for arg in args] + [type(v).__name__ for v in kwargs.values()]
                    raise ValueError(
                        f"No Request object found in function parameters. "
                        f"Available parameter types: {available_types}. "
                        f"Make sure your function includes 'request: Request' as a parameter."
                    )
                
                user_key = get_key(request)

                if bucket.allow_request(user_key):
                    return func(*args, **kwargs)
                else:
                    # Get bucket info for error response
                    bucket_info = bucket.get_bucket_info(user_key)
                    
                    # Calculate retry after
                    seconds_per_token = refill_time / refill_rate
                    retry_after = int(seconds_per_token)
                    
                    # Detailed error response
                    headers = {
                        "X-RateLimit-Limit": str(int(capacity)),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(retry_after),
                        "Retry-After": str(retry_after)
                    }
                    
                    raise HTTPException(
                        status_code=429,
                        detail={
                            "message": "Rate limit exceeded",
                            "limit": int(capacity),
                            "remaining": 0,
                            "reset_in_seconds": retry_after,
                            "storage_type": storage_type
                        },
                        headers=headers
                    )

            return sync_wrapper
    
    return decorator


# Convenience functions for common configurations
def rate_limit_memory(
    limit: Union[int, str],
    refill_rate: Optional[float] = None,
    refill_time: Optional[float] = None,
    key_func: Optional[Callable[[Request], str]] = None
):
    """Convenience function for memory-based rate limiting"""
    return rate_limit(limit, refill_rate, refill_time, key_func, "memory")


def rate_limit_redis(
    limit: Union[int, str],
    refill_rate: Optional[float] = None,
    refill_time: Optional[float] = None,
    key_func: Optional[Callable[[Request], str]] = None,
    redis_host: str = "localhost",
    redis_port: int = 6379,
    redis_db: int = 0,
    key_prefix: str = "rate_limit:"
):
    """Convenience function for Redis-based rate limiting"""
    storage_config = {
        "redis_client": None,  # Will use defaults
        "key_prefix": key_prefix
    }
    
    return rate_limit(
        limit, refill_rate, refill_time, key_func, 
        "redis", storage_config
    )
            
