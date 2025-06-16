#!/usr/bin/env python3
"""
Standalone Echo Server - Implements a simple echo server without using the agent-server SDK.

This is a simplified version that avoids the session_id parameter handling issues.
"""

import datetime
import json
import logging
import os
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Echo Agent",
    description="An example agent that echoes messages with timestamps",
    version="1.0.0",
)

# Descriptor for the agent
AGENT_DESCRIPTOR = {
    "name": "echo-agent",
    "version": "1.0.0",
    "description": "An example agent that echoes messages with timestamps",
    "url": "http://0.0.0.0:8765",
    "provider": {"organization": "Agent URI Project"},
    "documentationUrl": "https://github.com/username/agent-uri/examples/echo-agent",
    "interactionModel": "request-response",
    "capabilities": [
        {
            "name": "echo",
            "version": "1.0.0",
            "description": "Echoes back the input message appended with the timestamp",
            "tags": ["utility", "demo"],
            "input": {
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
            },
            "output": {
                "type": "object",
                "properties": {
                    "result": {"type": "string"},
                    "timestamp": {"type": "string", "format": "date-time"},
                    "original_message": {"type": "string"},
                },
            },
            "isDeterministic": False,
            "expectedOutputVariability": "medium",
            "requiresContext": False,
            "memoryEnabled": False,
            "responseLatency": "medium",
            "confidenceEstimation": False,
            "contentTypes": {
                "inputFormat": ["application/json"],
                "outputFormat": ["application/json"],
            },
        }
    ],
}

# Create the output directory
os.makedirs("./output", exist_ok=True)

# Save the agent descriptor
with open("./output/agent.json", "w") as f:
    json.dump(AGENT_DESCRIPTOR, f, indent=2)


@app.get("/agent.json")
async def get_agent_json():
    """Return the agent descriptor."""
    return JSONResponse(content=AGENT_DESCRIPTOR)


@app.post("/echo")
async def echo_capability(request: Request):
    """
    Echo capability implementation that avoids session_id parameter issues.

    Args:
        request: The FastAPI request

    Returns:
        The echoed message with timestamp
    """
    try:
        # Get request body
        body = await request.json()

        # Extract the message
        message = body.get("message", "")
        if not message:
            raise HTTPException(status_code=400, detail="Missing 'message' parameter")

        # Log incoming request
        session_id = request.headers.get("X-Session-ID")
        if session_id:
            logger.info(f"Request from session: {session_id}")

        logger.info(f"Echo capability called with message: {message}")

        # Generate response
        current_time = datetime.datetime.now().isoformat()
        result = f"{message} [{current_time}]"

        # Return the response
        return {
            "result": result,
            "timestamp": current_time,
            "original_message": message,
        }

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    except Exception as e:
        logger.exception("Error processing request")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Run the standalone Echo server."""
    # Configure host and port
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8765"))

    # Print server info
    print("\nEcho Agent Descriptor:")
    print(json.dumps(AGENT_DESCRIPTOR, indent=2))

    print(f"\nStarting Echo Agent server on http://{host}:{port}")
    print(f"- API docs: http://{host}:{port}/docs")
    print(f"- Agent descriptor: http://{host}:{port}/agent.json")

    # Start the server
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
