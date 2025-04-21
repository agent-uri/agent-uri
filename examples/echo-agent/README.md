# Echo Agent Example

This example demonstrates a simple agent implementation using the agent:// protocol. The Echo Agent receives messages and echoes them back with a timestamp appended.

## Overview

The Echo Agent demonstrates:

1. Basic capability implementation
2. Agent URI protocol 
3. HTTP transport
4. Server and client implementations
5. Different ways to interact with an agent

## Components

- `echo_agent.py`: Server implementation with the echo capability
- `client_test.py`: Agent client SDK implementation (full agent:// protocol)
- `direct_client.py`: Direct HTTP client using custom HTTP transport
- `simple_client.py`: Simple HTTP client without agent:// protocol dependencies
- `http_transport.py`: HTTP transport implementation
- `tests.py`: Unit and integration tests

## How it Works

The Echo Agent implements a simple capability that:
1. Receives a message parameter
2. Appends a timestamp to it
3. Returns the original message, timestamp, and combined result

## Prerequisites

- Python 3.8+
- Install required packages:
  ```bash
  # From the agent-uri root directory:
  pip install -e packages/common
  pip install -e packages/uri-parser
  pip install -e packages/descriptor
  pip install -e packages/resolver
  pip install -e packages/transport
  pip install -e packages/client
  pip install -e packages/server
  
  # Additional requirements
  pip install uvicorn fastapi requests
  ```

## Running the Example

### 1. Start the Echo Agent server

```bash
python echo_agent.py
```

This will:
- Start the server on http://0.0.0.0:8765
- Register the echo capability
- Generate and save the agent descriptor at ./output/agent.json
- Provide API docs at http://0.0.0.0:8765/docs

### 2. Run a client (in a separate terminal)

There are three different clients you can use:

#### Standard Agent Client (using agent:// protocol)

```bash
python client_test.py
```

This client uses the full agent:// protocol stack with:
- URI parsing
- Transport binding
- Agent descriptor resolution

#### Direct HTTP Client 

```bash
python direct_client.py
```

This client uses a custom HTTP transport but skips the agent:// URI parsing.

#### Simple HTTP Client

```bash
python simple_client.py
```

This client uses pure HTTP without any agent:// protocol dependencies.

## Running Tests

Run the unit and integration tests:

```bash
python tests.py
```

## Expected Output

When running the Echo Agent, you'll see that it:

1. Registers the echo capability
2. Saves a descriptor file
3. Prints the descriptor
4. Starts the server

Example client output:

```
=== Echo Agent Test ===

Invoking echo capability:
Message sent: Hello, Echo Agent! Current time: 2025-04-18T18:34:42.123456
Response: {
  "result": "Hello, Echo Agent! Current time: 2025-04-18T18:34:42.123456 [2025-04-18T18:34:42.654321]",
  "timestamp": "2025-04-18T18:34:42.654321",
  "original_message": "Hello, Echo Agent! Current time: 2025-04-18T18:34:42.123456"
}

✅ Test passed: Original message matched in response
✅ Test passed: Timestamp found in response
✅ Test passed: Result found in response
```

## Agent Descriptor

The agent descriptor provides metadata about the agent and its capabilities:
- Name, version, and description
- Provider information
- Interaction model
- Capability inputs and outputs
- Documentation URL

## Notes

- The example handles session_id properly for server-client interactions
- The capability has proper parameter extraction
- Full error handling is implemented
- The client prints helpful debugging information
