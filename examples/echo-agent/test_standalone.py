#!/usr/bin/env python3
"""
Test client for standalone Echo server.

This client directly communicates with the standalone echo server.
"""

import datetime
import json

import requests


def test_echo_server():
    """Test the standalone echo server."""
    print("\n=== Testing Standalone Echo Server ===\n")

    # Create test data
    current_time = datetime.datetime.now().isoformat()
    message = f"Hello, Standalone Echo Server! Time: {current_time}"

    # Define endpoint
    url = "http://localhost:8765/echo"

    try:
        print(f"Sending request to: {url}")
        print(f"Message: {message}")

        # Send the request
        response = requests.post(
            url=url,
            json={"message": message},
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )

        # Check if request was successful
        response.raise_for_status()

        # Parse response
        data = response.json()
        print(f"\nResponse status: {response.status_code}")
        print(f"Response body: {json.dumps(data, indent=2)}\n")

        # Validate response
        if data.get("original_message") == message:
            print("✅ Test passed: Original message matched")
        else:
            print("❌ Test failed: Message mismatch")

        if "timestamp" in data:
            print("✅ Test passed: Timestamp present")
        else:
            print("❌ Test failed: No timestamp")

        if "result" in data:
            print("✅ Test passed: Result present")
        else:
            print("❌ Test failed: No result")

        print("\nSUCCESS: Standalone echo server is working correctly!")

    except requests.exceptions.ConnectionError:
        print("\n❌ Connection error: Could not connect to standalone echo server.")
        print("Make sure you're running it with: python echo_standalone.py")

    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP error: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"Status code: {e.response.status_code}")
            try:
                error_body = e.response.json()
                print(f"Error details: {json.dumps(error_body, indent=2)}")
            except ValueError:
                print(f"Error response: {e.response.text}")

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    test_echo_server()
