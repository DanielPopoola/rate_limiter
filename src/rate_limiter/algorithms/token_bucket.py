from ..storage.base import RateLimitStorage

class TokenBucket:
    def __init__(self, capacity, refill_rate, refill_time, storage: RateLimitStorage):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.refill_time = refill_time
        self.storage = storage

    def allow_request(self, key: str) -> bool:
        """
        Check if a request should be allowed for the given key.
        
        This method delegates to the storage backend's atomic_consume_token method,
        which handles all the complexity of refilling tokens and consuming them atomically.
        """
        return self.storage.atomic_consume_token(key, self.capacity, self.refill_rate, self.refill_time)
    
    def get_bucket_info(self, key: str) -> dict:
        """
        Get information about a bucket's current state.
        Useful for debugging and monitoring.
        """
        state = self.storage.get_bucket_state(key)

        if state is None:
            return {
                'tokens': self.capacity,
                'capacity': self.capacity,
                'refill_rate': self.refill_rate,
                'refill_time': self.refill_time,
                'last_refill': None
            }
        
        tokens, last_time = state
        return {
            'tokens': tokens,
            'capacity': self.capacity,
            'refill_rate': self.refill_rate,
            'refill_time': self.refill_time,
            'last_refill': last_time
        }
    

def parse_rate_limit_string(rate_string):
    if '/' not in rate_string:
        raise ValueError("Rate limit string must be in 'N/period' format")
    
    requests, period = rate_string.split('/')
    requests = int(requests)

    period_map = {
        'second': 1,
        'minute': 60,
        'hour': 3600,
        'day': 86400
    }

    if period not in period_map:
        raise ValueError(f"Unsupported period: {period}. Use : {list(period_map.keys())}")
    
    refill_time = period_map[period]
    capacity = requests
    refill_rate = requests

    return capacity, refill_rate, refill_time


