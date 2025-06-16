#!/usr/bin/env python3
"""
Agent URI Protocol Client for Echo Agent

This script demonstrates how to use the agent:// protocol to interact with 
the Echo Agent server.
"""

import asyncio
import datetime
import json
import logging

from http_transport import HttpTransport

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_echo_capability():
    """Demonstrate invoking the Echo Agent's echo capability using agent:// protocol."""
    print("\n=== Echo Agent Direct Test ===\n")

    # Create a transport
    transport = HttpTransport()

    try:
        # Create a test message with the current time
        current_time = datetime.datetime.now().isoformat()
        message = f"Hello, Echo Agent! Current time: {current_time}"

        # Invoke the capability via agent:// protocol
        print("Invoking echo capability via agent:// protocol:")

        # Start the server first if it's not running
        print("Checking if echo agent server is running...")
        try:
            # Use the agent+http:// explicit transport binding
            response = await transport.invoke(
                endpoint="agent+http://localhost:8765",
                capability="echo",
                params={"message": message},
                headers={"X-Session-ID": "direct-client-test-session"},
            )
        except Exception as e:
            print(f"Error: {e}")
            print("❌ Starting echo server first...")
            print("Please run 'python echo_agent.py' in a separate terminal")
            print("Then run this client script again")
            return

        print(f"Message sent: {message}")
        print(f"Response: {json.dumps(response, indent=2)}\n")

        # Verify the response contains our original message
        if response.get("original_message") == message:
            print("✅ Test passed: Original message matched in response")
        else:
            print("❌ Test failed: Original message not found or didn't match")

        # Verify the response contains a timestamp
        if "timestamp" in response:
            print("✅ Test passed: Timestamp found in response")
        else:
            print("❌ Test failed: Timestamp not found in response")

        # Verify the result is formatted correctly
        if "result" in response:
            print("✅ Test passed: Result found in response")
        else:
            print("❌ Test failed: Result not found in response")

    except Exception as e:
        print(f"Error: {e}")
        print("❌ Test failed: Could not connect to Echo Agent")
        print("Make sure the Echo Agent server is running on agent://localhost:8765")


def main():
    """Run the direct Echo Agent client test."""
    try:
        asyncio.run(test_echo_capability())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
