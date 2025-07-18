from datetime import datetime

class TokenBucket:
    def __init__(self, capacity, refill_rate, refill_time):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.refill_time = refill_time
        self.buckets = {}

    def _refill(self, key):
        tokens, last_time = self.buckets[key]
        now = datetime.now()
        elapsed = (now - last_time).total_seconds()
        added_tokens = (elapsed / self.refill_time) * self.refill_rate
        tokens = min(self.capacity, tokens + added_tokens)
        
        self.buckets[key] = (tokens, now)

    def _allow_request(self, key):
        if key not in self.buckets:
            self.buckets[key] = (self.capacity, datetime.now())

        self._refill(key)
        token, last_time = self.buckets[key]

        if token >= 1:
            self.buckets[key] = (token - 1, last_time)
            return True
        return False

    def get_token_info(self, key):
        if key not in self.buckets:
            self.buckets[key] = (self.capacity, datetime.now())

        self._refill(key)
        return self.buckets[key]
    

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