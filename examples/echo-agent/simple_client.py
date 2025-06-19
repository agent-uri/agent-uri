#!/usr/bin/env python3
"""
Simple Echo Agent Client with agent:// Protocol Support

This client demonstrates how to use the agent:// protocol directly
without using the transport layer or SDK abstractions.
"""

import asyncio
import datetime
import json
import logging
import re

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configure agent URI endpoint with explicit http transport
AGENT_URI = "agent+http://localhost:8765"


def resolve_agent_uri(uri, capability=None):
    """
    Resolve an agent:// URI to an HTTP endpoint.

    Args:
        uri: The agent URI (e.g., agent://localhost:8765)
        capability: Optional capability to append to the path

    Returns:
        HTTP endpoint URL
    """
    # Match agent URI patterns
    agent_uri_pattern = r"^(agent)(\+([a-z]+))?://([^/]+)(/.*)?$"
    match = re.match(agent_uri_pattern, uri)

    if not match:
        # If not an agent URI, return as is (assume it's a direct HTTP URL)
        return uri

    # Extract components
    protocol = match.group(3) or "http"  # Default to HTTP if not specified
    authority = match.group(4)
    path = match.group(5) or ""

    # Construct HTTP URL
    endpoint = f"{protocol}://{authority}{path}"

    # Append capability if provided and not already in path
    if capability and not path.endswith(f"/{capability}"):
        endpoint = f"{endpoint}/{capability}"

    return endpoint


async def test_echo_capability():
    """Test the echo capability using the agent:// protocol."""
    print("\n=== Simple Echo Agent Test ===\n")

    try:
        # Create test data
        current_time = datetime.datetime.now().isoformat()
        message = f"Hello, Echo Agent! Current time: {current_time}"

        # Resolve agent URI to HTTP endpoint
        agent_endpoint = resolve_agent_uri(AGENT_URI, "echo")

        print(f"Using agent+http URI: {AGENT_URI}/echo")
        print(f"Resolved to HTTP endpoint: {agent_endpoint}")
        print(f"Message: {message}")

        # Send request with error handling
        try:
            # Do not include any session ID at all to avoid the duplication issue
            response = requests.post(
                url=agent_endpoint,
                json={"message": message},
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    # No session ID header for now to avoid potential conflicts
                },
            )

            # Raise for HTTP errors
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

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            if hasattr(e, "response") and e.response is not None:
                print(f"Status code: {e.response.status_code}")
                try:
                    error_body = e.response.json()
                    print(f"Error details: {json.dumps(error_body, indent=2)}")
                except ValueError:
                    print(f"Error response: {e.response.text}")

            print("\n❌ Server error - please check:")
            print(f"1. Is the agent server running at {AGENT_URI}?")
            print("2. Run 'python echo_agent.py' in a separate terminal")
            print("3. Check server logs for error details")
            print("4. The echo capability might need troubleshooting")

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")


async def main():
    """Run the Echo Agent test."""
    await test_echo_capability()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
