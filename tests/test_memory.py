from src.rate_limiter.decorator import rate_limit_memory
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from datetime import datetime
import uvicorn
import time


app = FastAPI()

@app.get("/test-basic")
@rate_limit_memory("3/minute")
def basic_memory(request: Request):
    return {
        "message": "Success!",
        "timestamp": datetime.now().isoformat(),
        "client_info": str(type(request.client)) if hasattr(request, 'client') else "no client"
    }

def get_test_user_id(request):
    if hasattr(request, 'headers'):
        return request.headers.get("X-User-ID", "test-user")
    return "test-user"

@app.get("/test-user")
@rate_limit_memory("5/minute", key_func=get_test_user_id)
def user_route_memory(request: Request):
    user_id = get_test_user_id(request)
    return {
        "message": "User-specific rate limiting",
        "user_id": user_id,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/test-numeric")
@rate_limit_memory(2, 1, 30)
def numeric(request: Request):
    return {
        "message": "Numeric rate limiting",
        "timestamp": datetime.now().isoformat()
    }

def test_basic_functionality():
    """Test basic rate limiting functionality"""
    client = TestClient(app)

    print("=== Testing Basic Rate Limiting (3/minute) ===")

    for i in range(3):
        response = client.get("/test-basic")
        print(f"Request {i+1}: Status {response.status_code}")
        assert response.status_code == 200

    response = client.get("/test-basic")
    print(f"Request 4: Status {response.status_code}")
    assert response.status_code == 429

    # Check error response
    error_data = response.json()
    print(f"Error response: {error_data}")
    assert "message" in error_data["detail"]
    assert "limit" in error_data["detail"]
    assert "remaining" in error_data["detail"]

    # Check rate limit headers
    print(f"Rate limit headers: {dict(response.headers)}")
    assert "X-RateLimit-Limit" in response.headers
    assert "Retry-After" in response.headers
    
    print("✅ Basic rate limiting test passed!\n")

def test_user_specific_limiting():
    """Test rate limiting with custom key function"""
    client = TestClient(app)

    print("=== Testing User-Specific Rate Limiting (5/minute) ===")

    for i in range(5):
        response = client.get("/test-user", headers={"X-User-ID": "user_a"})
        print(f"User A Request {i+1}: Status {response.status_code}")
        assert response.status_code == 200

    response = client.get("/test-user", headers={"X-User-ID": "user_a"})
    print(f"User A Request 6: Status {response.status_code}")
    assert response.status_code == 429

    # User B should still be able to make requests
    response = client.get("/test-user", headers={"X-User-ID": "user_b"})
    print(f"User B Request 1: Status {response.status_code}")
    assert response.status_code == 200

    print("✅ User-specific rate limiting test passed!\n")

def test_numeric_format():
    """Test numeric format rate limiting"""
    client = TestClient(app)
    
    print("=== Testing Numeric Format (2 tokens, 1 per 30 seconds) ===")

    for i in range(2):
        response = client.get("/test-numeric")
        print(f"Request {i+1}: Status {response.status_code}")
        assert response.status_code == 200

    response = client.get("/test-numeric")
    print(f"Request 3: Status {response.status_code}")
    assert response.status_code == 429

    print("✅ Numeric format test passed!\n")

def test_token_refill():
    """Test that tokens refill over time"""
    client = TestClient(app)

    print("=== Testing Token Refill (waiting for refill) ===")

    @app.get("/test-refill")
    @rate_limit_memory(1, 1, 2)
    def test_refill(request: Request):
        return {"message": "Refill test"}

    response = client.get("/test-refill")
    print(f"Initial request: Status {response.status_code}")
    assert response.status_code == 200

    response = client.get("/test-refill")
    print(f"Immediate second request: Status {response.status_code}")
    assert response.status_code == 429

    print("Waiting 3 seconds for token refill...")
    time.sleep(3)

    response = client.get("/test-refill")
    print(f"After waiting: Status {response.status_code}")
    assert response.status_code == 200
    
    print("✅ Token refill test passed!\n")

if __name__ == "__main__":
    print("Starting Rate Limiter Tests...\n")
    
    try:
        test_basic_functionality()
        test_user_specific_limiting()
        test_numeric_format()
        test_token_refill()
        
        print("🎉 All tests passed! Your rate limiter is working correctly.")
        
        # Optional: Start the server for manual testing
        print("\nStarting server for manual testing...")
        print("Visit: http://127.0.0.1:8000/test-basic")
        print("Try hitting the endpoint multiple times to see rate limiting in action")
        
        uvicorn.run(app, host="127.0.0.1", port=8000)
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()