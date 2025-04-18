import requests
import json

print("Starting API test with a 5 second timeout...")

# Test the props endpoint
try:
    print("Testing props endpoint...")
    response = requests.get("http://localhost:8001/api/props/?date=2025-04-18", timeout=5)
    print(f"Response received. Status code: {response.status_code}")
    
    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
        print(f"Success! Received {len(data)} props.")
        # Print just the first prop to keep output manageable
        if data:
            print("First prop:")
            print(json.dumps(data[0], indent=2))
    else:
        print(f"Error: Status code {response.status_code}")
        print(response.text)
except requests.exceptions.Timeout:
    print("Request timed out after 5 seconds. The server might be slow or unresponsive.")
except Exception as e:
    print(f"Error connecting to API: {e}")

# Test the player props endpoint
try:
    print("\nTesting player props endpoint...")
    response = requests.get("http://localhost:8001/api/props/player?name=lebron&date=2025-04-18", timeout=5)
    print(f"Response received. Status code: {response.status_code}")
    
    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
        print("Success! Player props data received.")
        print("Player name:", data.get("player", {}).get("name", "Unknown"))
    else:
        print(f"Error with player endpoint: Status code {response.status_code}")
        print(response.text)
except requests.exceptions.Timeout:
    print("Player props request timed out after 5 seconds. The server might be slow or unresponsive.")
except Exception as e:
    print(f"Error connecting to player API: {e}")

print("\nAll tests complete.") 