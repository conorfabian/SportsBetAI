import requests
import time

print("Testing minimal Flask app...")

# Test root endpoint
try:
    print("Testing root endpoint...")
    response = requests.get("http://localhost:8000/", timeout=5)
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error testing root: {e}")

# Test API endpoint
try:
    print("\nTesting API endpoint...")
    response = requests.get("http://localhost:8000/api/test", timeout=5)
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error testing API: {e}")

print("\nTest complete") 