#!/usr/bin/env python3
"""
Echo Agent Client Test Script

This script demonstrates how to use the custom HTTP transport
to interact with the Echo Agent directly.
"""

import json
import logging
import datetime
import asyncio

from http_transport import HttpTransport

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_echo_capability():
    """Demonstrate invoking the Echo Agent's echo capability using agent:// protocol."""
    print("\n=== Echo Agent Test ===\n")
    
    # Create a transport
    transport = HttpTransport()
    
    try:
        # Create test data
        current_time = datetime.datetime.now().isoformat()
        message = f"Hello, Echo Agent! Current time: {current_time}"
        
        # Use agent+http:// protocol URI to explicitly specify HTTP transport
        agent_uri = "agent+http://localhost:8765"
        capability = "echo"
        print(f"Using agent+http:// URI: {agent_uri}/{capability}")
        
        # Add X-Session-ID header to be passed to the server
        custom_headers = {"X-Session-ID": "test-session-123"}
        
        # Invoke the capability using the agent:// protocol
        response = await transport.invoke(
            endpoint=agent_uri,
            capability=capability,
            params={"message": message},
            headers=custom_headers
        )
        
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
        print("Make sure the Echo Agent server is running on "
              "http://localhost:8765")


async def main():
    """Run the Echo Agent client test."""
    try:
        # Run the test
        await test_echo_capability()
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
