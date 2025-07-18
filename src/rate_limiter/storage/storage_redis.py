from .base import RateLimitStorage
from typing import Tuple, Optional
import json
import redis
import time


class RedisStorage(RateLimitStorage):
    """Redis-based storage backend with atomic operations"""
    
    def __init__(self, redis_client: redis.Redis, key_prefix: str = "rate_limit:"):
        if redis_client is None:
            redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

        self.redis  = redis_client
        self.key_prefix = key_prefix

        self.consume_token_script = self.redis.register_script(self._get_consume_token_lua_script())

    def _make_key(self, key: str) -> str:
        """Create a Redis key with our prefix"""
        return f"{self.key_prefix}{key}"
    
    def get_bucket_state(self, key: str) -> Optional[Tuple[float, float]]:
        redis_key = self._make_key(key)
        data = self.redis.get(redis_key)

        if data is None:
            return None
        
        try:
            if isinstance(data, bytes):
                data = data.decode('utf-8')
                bucket_data = json.loads(data)
                return bucket_data['tokens'], bucket_data['timestamp']
        except (json.JSONDecodeError, KeyError):
            return None
        
    def set_bucket_state(self, key: str, tokens:float, timestamp: float) -> None:
        redis_key = self._make_key(key)
        data = {
            'tokens': tokens,
            'timestamp': timestamp
        }
        self.redis.setex(redis_key, 7200, json.dumps(data))
    
    def atomic_consume_token(self, key: str, capacity: float, refill_rate: float, refill_time: float) -> bool:
        """
        Use a Lua script to atomically consume a token.
        """
        redis_key = self._make_key(key)
        current_time = time.time()

        # Execute the Lua script
        result = self.consume_token_script(
            keys=[redis_key],
            args=[capacity, refill_rate, refill_time, current_time, 7200]
        )

        return bool(result)
    
    def _get_consume_token_lua_script(self) -> str:
        """
        Lua script that runs atomically on Redis server.
        This prevents race conditions by doing all operations in one atomic step.
        """
        return """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local refill_time = tonumber(ARGV[3])
        local current_time = tonumber(ARGV[4])
        local expiration = tonumber(ARGV[5])
        
        -- Get current bucket state
        local bucket_data = redis.call('GET', key)
        local tokens, last_time
        
        if bucket_data == false then
            -- New bucket - start with full capacity
            tokens = capacity
            last_time = current_time
        else
            -- Parse existing bucket data
            local data = cjson.decode(bucket_data)
            tokens = data.tokens
            last_time = data.timestamp
        end
        
        -- Calculate refill
        local elapsed = current_time - last_time
        local added_tokens = (elapsed / refill_time) * refill_rate
        tokens = math.min(capacity, tokens + added_tokens)
        
        -- Try to consume a token
        if tokens >= 1 then
            -- Success - consume token and update state
            tokens = tokens - 1
            local new_data = cjson.encode({
                tokens = tokens,
                timestamp = current_time
            })
            redis.call('SETEX', key, expiration, new_data)
            return 1
        else
            -- Failure - update timestamp but don't consume token
            local new_data = cjson.encode({
                tokens = tokens,
                timestamp = current_time
            })
            redis.call('SETEX', key, expiration, new_data)
            return 0
        end
        """