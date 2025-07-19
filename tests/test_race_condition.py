import threading
import time
import redis
from concurrent.futures import ThreadPoolExecutor
from src.rate_limiter.storage.storage_memory import MemoryStorage
from src.rate_limiter.storage.storage_redis import RedisStorage



def test_race_condition_memory():
    """Test memory storage with concurrent access - may show race condition"""
    print("=== Testing Memory Storage Race Condition ===")
    
    storage = MemoryStorage()
    results = []
    
    def make_request(thread_id):
        # Simulate multiple requests hitting at the same time
        allowed = storage.atomic_consume_token("test_user", 1, 1, 60)  # 1 token, refill 1 per minute
        results.append((thread_id, allowed))
        if allowed:
            print(f"Thread {thread_id}: Request ALLOWED")
        else:
            print(f"Thread {thread_id}: Request DENIED")
    
    # Start multiple threads simultaneously
    threads = []
    for i in range(5):
        thread = threading.Thread(target=make_request, args=(i,))
        threads.append(thread)
    
    # Start all threads at roughly the same time
    for thread in threads:
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    allowed_count = sum(1 for _, allowed in results if allowed)
    print(f"Total requests allowed: {allowed_count} (should be 1)")
    
    if allowed_count > 1:
        print("⚠️  Race condition detected in memory storage!")
    else:
        print("✅ No race condition in memory storage (this time)")
    
    print()


def test_race_condition_redis():
    """Test Redis storage with concurrent access - should prevent race condition"""
    print("=== Testing Redis Storage Race Condition ===")
    
    try:
        # Connect to Redis
        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        redis_client.ping()  # Test connection
        
        # Clear any existing data
        redis_client.flushdb()
        
        storage = RedisStorage(redis_client, "test:")
        results = []
        
        def make_request(thread_id):
            # Simulate multiple requests hitting at the same time
            allowed = storage.atomic_consume_token("test_user", 1, 1, 60)  # 1 token, refill 1 per minute
            results.append((thread_id, allowed))
            if allowed:
                print(f"Thread {thread_id}: Request ALLOWED")
            else:
                print(f"Thread {thread_id}: Request DENIED")
        
        # Start multiple threads simultaneously
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
        
        # Start all threads at roughly the same time
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        allowed_count = sum(1 for _, allowed in results if allowed)
        print(f"Total requests allowed: {allowed_count} (should be 1)")
        
        if allowed_count == 1:
            print("✅ Redis prevented race condition!")
        else:
            print("❌ Unexpected result with Redis")
        
    except redis.ConnectionError:
        print("❌ Could not connect to Redis. Make sure Redis is running on localhost:6379")
    except Exception as e:
        print(f"❌ Error testing Redis: {e}")
    
    print()


def stress_test_redis():
    """Stress test Redis with many concurrent requests"""
    print("=== Redis Stress Test ===")
    
    try:
        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        redis_client.ping()
        redis_client.flushdb()
        
        storage = RedisStorage(redis_client, "stress:")
        
        # Test with 10 tokens, 100 concurrent requests
        results = []
        
        def make_request(request_id):
            allowed = storage.atomic_consume_token("stress_user", 10, 5, 60)  # 10 tokens
            results.append(allowed)
            return allowed
        
        # Use ThreadPoolExecutor for better concurrency control
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request, i) for i in range(100)]
            
            # Wait for all requests to complete
            for future in futures:
                future.result()
        
        allowed_count = sum(1 for allowed in results if allowed)
        denied_count = sum(1 for allowed in results if not allowed)
        
        print(f"Total requests: {len(results)}")
        print(f"Allowed: {allowed_count}")
        print(f"Denied: {denied_count}")
        print(f"Expected allowed: 10")
        
        if allowed_count == 10:
            print("✅ Redis stress test passed!")
        else:
            print(f"⚠️  Expected 10 allowed requests, got {allowed_count}")
        
    except redis.ConnectionError:
        print("❌ Could not connect to Redis. Make sure Redis is running on localhost:6379")
    except Exception as e:
        print(f"❌ Error in stress test: {e}")


def test_token_refill_redis():
    """Test that tokens refill correctly over time with Redis"""
    print("=== Testing Token Refill with Redis ===")
    
    try:
        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        redis_client.ping()
        redis_client.flushdb()
        
        storage = RedisStorage(redis_client, "refill:")
        
        # Use small refill time for testing
        capacity = 2
        refill_rate = 1
        refill_time = 2  # 1 token every 2 seconds
        
        # Consume all tokens
        result1 = storage.atomic_consume_token("refill_user", capacity, refill_rate, refill_time)
        result2 = storage.atomic_consume_token("refill_user", capacity, refill_rate, refill_time)
        result3 = storage.atomic_consume_token("refill_user", capacity, refill_rate, refill_time)
        
        print(f"Initial requests: {result1}, {result2}, {result3}")
        print("Expected: True, True, False")
        
        # Wait for refill
        print("Waiting 3 seconds for token refill...")
        time.sleep(3)
        
        # Should be able to make one more request
        result4 = storage.atomic_consume_token("refill_user", capacity, refill_rate, refill_time)
        print(f"After refill: {result4}")
        print("Expected: True")
        
        if result1 and result2 and not result3 and result4:
            print("✅ Token refill test passed!")
        else:
            print("❌ Token refill test failed")
        
    except redis.ConnectionError:
        print("❌ Could not connect to Redis. Make sure Redis is running on localhost:6379")
    except Exception as e:
        print(f"❌ Error in refill test: {e}")


if __name__ == "__main__":
    print("Testing Race Conditions and Redis Functionality\n")
    
    # Test memory storage (may show race condition)
    test_race_condition_memory()
    
    # Test Redis storage (should prevent race condition)
    test_race_condition_redis()
    
    # Stress test Redis
    stress_test_redis()
    
    # Test token refill
    test_token_refill_redis()
    
    print("Tests completed!")
    
    # Instructions for running
    print("\nTo run these tests:")
    print("1. Install Redis: https://redis.io/download")
    print("2. Start Redis server: redis-server")
    print("3. Install redis-py: pip install redis")
    print("4. Run this script: python -m tests.test_race_condition.py")