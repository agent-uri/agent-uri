#!/usr/bin/env python3
"""
Echo Agent — reference implementation using the agent:// protocol.

Exposes a single ``echo`` skill that returns the input message appended
with a timestamp. Aligned with draft-narvaneni-agent-uri-03.
"""

import datetime
import json
import logging
import os
from typing import Any, Dict

import uvicorn

from agent_uri import FastAPIAgentServer, skill

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@skill(
    id="echo",
    name="echo",
    description="Echoes back the input message appended with the timestamp",
    version="1.0.0",
    tags=["utility", "demo"],
    idempotent=False,
    input_schema={
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "required": ["message"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "result": {"type": "string"},
            "timestamp": {"type": "string", "format": "date-time"},
            "original_message": {"type": "string"},
        },
    },
)
async def echo(
    *,
    message: str = "",
    session_id: str = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Return ``message`` appended with a timestamp."""
    if not isinstance(message, str):
        message = str(message) if message is not None else ""

    if session_id:
        logger.info("Request from session: %s", session_id)

    now = datetime.datetime.now().isoformat()
    return {
        "result": f"{message} [{now}]",
        "timestamp": now,
        "original_message": message,
    }


def create_echo_agent_server(host: str = "0.0.0.0", port: int = 8765):
    """Build a ready-to-run FastAPI echo-agent server."""
    server = FastAPIAgentServer(
        name="echo-agent",
        version="1.0.0",
        description="An example agent that echoes messages with timestamps",
        provider={"organization": "Agent URI Project"},
        documentation_url=(
            "https://github.com/agent-uri/agent-uri/tree/main/examples/echo-agent"
        ),
        interaction_model=["agent2agent"],
        server_url=f"http://{host}:{port}",
        conformance_level=2,
        environment="development",
        enable_cors=True,
        enable_docs=True,
        enable_agent_json=True,
    )

    server.register_skill("echo", echo._skill)

    os.makedirs("./output", exist_ok=True)
    server.save_agent_descriptor("./output/agent.json")
    return server


def main() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8765"))

    server = create_echo_agent_server(host, port)

    print("\nEcho Agent Descriptor:")
    print(json.dumps(server.get_agent_descriptor(), indent=2))

    print(f"\nStarting Echo Agent server on http://{host}:{port}")
    print(f"- API docs: http://{host}:{port}/docs")
    print(f"- Agent descriptor: http://{host}:{port}/agent.json")

    uvicorn.run(server.app, host=host, port=port)


if __name__ == "__main__":
    main()
