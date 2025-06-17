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

### ✅ Working Examples:
- `echo_agent.py`: **FIXED** - Server implementation with the echo capability  
- `simple_client.py`: **FIXED** - Simple HTTP client for testing the echo agent
- `direct_client.py`: Direct HTTP client using custom HTTP transport
- Basic URI parsing functionality

### ⚠️ Examples that need testing:
- `client_test.py`: Agent client SDK implementation (full agent:// protocol)
- `http_transport.py`: HTTP transport implementation  
- `tests.py`: Unit and integration tests

> **Note**: Most examples are now working with the single `agent-uri` package!

## How it Works

The Echo Agent implements a simple capability that:
1. Receives a message parameter
2. Appends a timestamp to it
3. Returns the original message, timestamp, and combined result

## Prerequisites

- Python 3.9+
- Install the agent-uri package:
  ```bash
  # Option 1: Install from PyPI (once published)
  pip install agent-uri
  
  # Option 2: Install from local development (for now)
  # From the agent-uri root directory:
  pip install -e .
  ```

## Running the Example

### 1. Start the Echo Agent server

```bash
# From the agent-uri root directory:
python examples/echo-agent/echo_agent.py
```

This will:
- Start the server on http://0.0.0.0:8765
- Register the echo capability
- Generate and save the agent descriptor at ./output/agent.json
- Provide API docs at http://0.0.0.0:8765/docs

### 2. Run a client (in a separate terminal)

```bash
# Simple HTTP client (works now):
python examples/echo-agent/simple_client.py

# Direct HTTP client (works now):
python examples/echo-agent/direct_client.py
```

### Other examples (need testing):

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

```bash
# Start the server first:
python examples/echo-agent/echo_agent.py

# In another terminal, test the client:
python examples/echo-agent/simple_client.py

# Full integration tests (need testing):
python examples/echo-agent/tests.py
```

## Expected Output

### Simple URI Example Output:

```
🤖 Agent URI Simple Example
========================================

1. Basic URI Parsing:
   Original URI: agent://example.com/echo-agent
   Host: example.com
   Path: echo-agent
   Authority: example.com

2. URI with Transport Binding:
   Original URI: agent+https://api.example.com:8443/my-agent
   Full scheme: agent+https
   Transport: https
   Host: api.example.com
   Port: 8443
   Path: my-agent

3. URI with Query Parameters:
   Original URI: agent://service.ai/gpt-agent?version=4&temperature=0.7&max_tokens=150
   Host: service.ai
   Path: gpt-agent
   Query parameters:
     version: 4
     temperature: 0.7
     max_tokens: 150

✅ All examples completed successfully!
📦 Package Info:
   agent-uri version: 0.2.0
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
