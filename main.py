from fastapi import FastAPI, Request
import redis
from src.rate_limiter.decorator import rate_limit, rate_limit_memory, rate_limit_redis


app = FastAPI()

# Memory-based rate limiting (same as before)
@app.get("/memory")
@rate_limit_memory("10/minute")
def memory_endpoint(request: Request):
    return {"message": "Memory-based rate limiting"}

# Redis-based rate limiting (distributed)
@app.get("/redis")
@rate_limit_redis("10/minute")
def redis_endpoint(request: Request):
    return {"message": "Redis-based rate limiting"}

# Custom Redis configuration
@app.get("/redis-custom")
@rate_limit(
    "20/hour",
    storage_type="redis",
    storage_config={
        "redis_client": redis.Redis(host="redis-cluster.example.com", port=6379),
        "key_prefix": "myapp:limits:"
    }
)
def redis_custom_endpoint(request: Request):
    return {"message": "Custom Redis rate limiting"}

# Custom key function with Redis
def get_api_key(request):
    return request.headers.get("X-API-Key", "anonymous")

@app.get("/api")
@rate_limit_redis("100/hour", key_func=get_api_key)
def api_endpoint(request: Request):
    return {"message": "API key rate limiting with Redis"}