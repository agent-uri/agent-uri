"""
Server SDK for agents that implement the agent:// protocol.

This package provides utilities and framework components for creating
server-side agent implementations that conform to the agent:// protocol.
"""

__version__ = "0.1.0"

from agent_server.server import AgentServer, FastAPIAgentServer
from agent_server.capability import Capability, capability
from agent_server.descriptor import AgentDescriptorGenerator
from agent_server.handler import BaseHandler, HTTPHandler, WebSocketHandler

__all__ = [
    "AgentServer",
    "FastAPIAgentServer",
    "Capability",
    "capability",
    "AgentDescriptorGenerator",
    "BaseHandler",
    "HTTPHandler",
    "WebSocketHandler"
]
