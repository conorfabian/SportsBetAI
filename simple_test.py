import requests
import time

print("Starting test...")

# Add a delay to ensure server is fully started
time.sleep(2)

# Basic test to see if server is up
try:
    print("Testing root endpoint...")
    start_time = time.time()
    r = requests.get("http://localhost:8002/", timeout=5)
    elapsed = time.time() - start_time
    print(f"Root request took {elapsed:.2f} seconds")
    print(f"Status code: {r.status_code}")
    print(f"Content: {r.text[:100]}...")
except Exception as e:
    print(f"Error with root endpoint: {e}")

# Test props endpoint
try:
    print("\nTesting props endpoint...")
    start_time = time.time()
    r = requests.get("http://localhost:8002/api/props/?date=2025-04-18", timeout=10)
    elapsed = time.time() - start_time
    print(f"Props request took {elapsed:.2f} seconds")
    print(f"Status code: {r.status_code}")
    if r.status_code == 200:
        print(f"Response length: {len(r.text)} characters")
        print(f"First 100 characters: {r.text[:100]}...")
    else:
        print(f"Error response: {r.text}")
except Exception as e:
    print(f"Error with props endpoint: {e}")

print("\nTest complete") 