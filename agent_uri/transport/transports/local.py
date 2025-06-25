"""
Local transport adapter for agent:// protocol.

This module implements the local transport for the agent:// protocol,
enabling communication with agents running in the local environment
through inter-process communication.
"""

import json
import logging
import os
import socket
import sys
import tempfile
import threading
import time
import uuid
from typing import Any, Callable, Dict, Iterator, Optional

from ..base import AgentTransport, TransportError, TransportTimeoutError

logger = logging.getLogger(__name__)


class LocalAgentRegistry:
    """
    Registry for local agents.

    This class maintains a mapping of local agent names to their
    handler functions/objects, allowing other processes to invoke
    them through the local transport.
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        """Get the singleton registry instance."""
        if cls._instance is None:
            cls._instance = LocalAgentRegistry()
        return cls._instance

    def __init__(self):
        """Initialize the local agent registry."""
        self._agents = {}
        self._socket_paths = {}
        self._server_sockets = {}
        self._running = False
        self._server_threads = {}

    def register_agent(
        self, name: str, handler: Callable, socket_path: Optional[str] = None
    ) -> str:
        """
        Register a local agent.

        Args:
            name: Name of the agent
            handler: Function or object that handles agent invocations
            socket_path: Optional custom socket path

        Returns:
            Socket path for the agent
        """
        if not socket_path:
            # Create a socket path based on agent name
            if sys.platform.startswith("win"):
                # Windows uses named pipes differently, use a port-based approach
                socket_path = f"127.0.0.1:{self._find_free_port()}"
            else:
                # Unix-based systems can use Unix domain sockets
                socket_dir = tempfile.gettempdir()
                socket_name = (
                    f"agent_{name.replace('/', '_')}_{uuid.uuid4().hex[:8]}.sock"
                )
                socket_path = os.path.join(socket_dir, socket_name)

        self._agents[name] = handler
        self._socket_paths[name] = socket_path

        # Start server for this agent if registry is running
        if self._running:
            self._start_agent_server(name)

        return socket_path

    def unregister_agent(self, name: str) -> bool:
        """
        Unregister a local agent.

        Args:
            name: Name of the agent to unregister

        Returns:
            True if agent was unregistered, False if not found
        """
        if name in self._agents:
            # Stop the server socket if running
            if name in self._server_sockets:
                socket_obj = self._server_sockets.pop(name)
                try:
                    socket_obj.close()
                except Exception:  # nosec B110
                    pass  # Ignore errors when closing socket

                if name in self._server_threads:
                    # Let thread complete gracefully
                    self._server_threads.pop(name)

            # Clean up socket file if it exists (Unix domain sockets)
            socket_path = self._socket_paths.pop(name)
            if not socket_path.startswith("127.0.0.1"):
                try:
                    if os.path.exists(socket_path):
                        os.unlink(socket_path)
                except Exception:  # nosec B110
                    pass

            # Remove agent from registry
            del self._agents[name]
            return True

        return False

    def get_agent(self, name: str) -> Optional[Callable]:
        """
        Get a registered agent by name.

        Args:
            name: Name of the agent

        Returns:
            Agent handler or None if not found
        """
        return self._agents.get(name)

    def get_socket_path(self, name: str) -> Optional[str]:
        """
        Get the socket path for a registered agent.

        Args:
            name: Name of the agent

        Returns:
            Socket path or None if agent not found
        """
        return self._socket_paths.get(name)

    def list_agents(self) -> Dict[str, str]:
        """
        List all registered agents and their socket paths.

        Returns:
            Dictionary mapping agent names to socket paths
        """
        return dict(self._socket_paths)

    def start(self) -> None:
        """Start the registry server for all registered agents."""
        if self._running:
            return

        self._running = True

        # Start a server for each registered agent
        for name in list(self._agents.keys()):
            self._start_agent_server(name)

    def stop(self) -> None:
        """Stop the registry server."""
        if not self._running:
            return

        self._running = False

        # Close all server sockets
        for _name, socket_obj in list(self._server_sockets.items()):
            try:
                socket_obj.close()
            except Exception:  # nosec B110
                pass

        self._server_sockets.clear()

        # Wait for all server threads to complete
        for thread in list(self._server_threads.values()):
            if thread.is_alive():
                thread.join(1.0)  # Wait up to 1 second

        self._server_threads.clear()

        # Clean up socket files (Unix domain sockets)
        for socket_path in self._socket_paths.values():
            if not socket_path.startswith("127.0.0.1"):
                try:
                    if os.path.exists(socket_path):
                        os.unlink(socket_path)
                except Exception:  # nosec B110
                    pass

    def _start_agent_server(self, name: str) -> None:
        """
        Start a server for a specific agent.

        Args:
            name: Name of the agent to start server for
        """
        socket_path = self._socket_paths[name]

        if name in self._server_sockets:
            # Server already running for this agent
            return

        # Create and configure socket
        if socket_path.startswith("127.0.0.1"):
            # TCP socket (Windows or explicit TCP)
            host, port = socket_path.split(":")
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((host, int(port)))
        else:
            # Unix domain socket (Unix-based systems)
            if os.path.exists(socket_path):
                os.unlink(socket_path)

            # Set restrictive umask before socket creation to prevent race condition
            old_umask = os.umask(0o077)  # Creates files with 0o600 permissions
            try:
                server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                server_socket.bind(socket_path)
                # Socket is now created with secure permissions from the start
                # Additional chmod for explicit permission setting
                os.chmod(socket_path, 0o700)
            finally:
                # Restore original umask
                os.umask(old_umask)

        server_socket.listen(5)
        self._server_sockets[name] = server_socket

        # Start server thread
        thread = threading.Thread(
            target=self._agent_server_loop, args=(name, server_socket), daemon=True
        )
        thread.start()
        self._server_threads[name] = thread

        logger.debug(f"Started local agent server for '{name}' on {socket_path}")

    def _agent_server_loop(self, name: str, server_socket: socket.socket) -> None:
        """
        Server loop for an agent.

        Args:
            name: Name of the agent
            server_socket: Socket to listen on
        """
        while self._running and name in self._agents:
            try:
                server_socket.settimeout(1.0)
                try:
                    client_socket, _ = server_socket.accept()
                except socket.timeout:
                    continue

                # Handle client in a new thread
                threading.Thread(
                    target=self._handle_client, args=(name, client_socket), daemon=True
                ).start()

            except Exception as e:
                if self._running:
                    logger.error(f"Error in agent server loop for '{name}': {str(e)}")
                    time.sleep(0.1)

    def _handle_client(self, name: str, client_socket: socket.socket) -> None:
        """
        Handle a client connection.

        Args:
            name: Name of the agent
            client_socket: Client socket
        """
        try:
            # Set timeout to prevent hanging
            client_socket.settimeout(60.0)

            # Read request from client
            data = b""
            while True:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                data += chunk
                if data.endswith(b"\n"):
                    break

            if not data:
                return

            # Parse request
            request = json.loads(data.decode("utf-8"))

            # Get agent handler
            handler = self._agents.get(name)
            if not handler:
                response = {"error": f"Agent '{name}' not found", "code": 404}
            else:
                # Process the request
                try:
                    capability = request.get("capability", "")
                    params = request.get("params", {})

                    # Check if streaming is requested
                    streaming = request.get("streaming", False)

                    if streaming:
                        # Send initial response to acknowledge
                        client_socket.sendall(
                            json.dumps(
                                {"status": "streaming", "id": request.get("id")}
                            ).encode("utf-8")
                            + b"\n"
                        )

                        # Process with streaming
                        for chunk in handler(capability, params):
                            chunk_data = (
                                json.dumps(
                                    {"chunk": chunk, "id": request.get("id")}
                                ).encode("utf-8")
                                + b"\n"
                            )
                            client_socket.sendall(chunk_data)

                        # Send final message
                        client_socket.sendall(
                            json.dumps(
                                {"complete": True, "id": request.get("id")}
                            ).encode("utf-8")
                            + b"\n"
                        )
                    else:
                        # Regular request/response
                        result = handler(capability, params)

                        # Check if result is a generator and convert to list
                        # for JSON serialization
                        if hasattr(result, "__iter__") and hasattr(result, "__next__"):
                            # It's a generator, convert to list
                            result = list(result)

                        response = {"result": result, "id": request.get("id")}

                        # Send response
                        client_socket.sendall(
                            json.dumps(response).encode("utf-8") + b"\n"
                        )

                except Exception as e:
                    # Send error response
                    response = {
                        "error": f"Error processing request: {str(e)}",
                        "code": 500,
                        "id": request.get("id"),
                    }
                    client_socket.sendall(json.dumps(response).encode("utf-8") + b"\n")

        except Exception as e:
            logger.error(f"Error handling client for '{name}': {str(e)}")
        finally:
            try:
                client_socket.close()
            except Exception:  # nosec B110
                pass

    def _find_free_port(self) -> int:
        """Find a free port to use for TCP socket."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        _, port = s.getsockname()
        s.close()
        return port


class LocalTransport(AgentTransport):
    """
    Local transport adapter for agent:// protocol.

    This transport handles communication with agents running in the
    local environment, using inter-process communication mechanisms.
    """

    def __init__(self):
        """Initialize a local transport adapter."""
        self._registry = LocalAgentRegistry.get_instance()

        # Start the registry server if not already running
        if not getattr(self._registry, "_running", False):
            self._registry.start()

    @property
    def protocol(self) -> str:
        """Return the transport protocol identifier."""
        return "local"

    def invoke(
        self,
        endpoint: str,
        capability: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> Any:
        """
        Invoke a local agent capability.

        Args:
            endpoint: The agent name or socket path
            capability: The capability to invoke
            params: Optional parameters to pass to the capability
            headers: Ignored for local transport
            timeout: Optional timeout in seconds
            **kwargs: Additional transport-specific parameters

        Returns:
            The response from the agent

        Raises:
            TransportError: If there is an error communicating with the agent
            TransportTimeoutError: If the request times out
        """
        if timeout is None:
            timeout = 60  # Default timeout

        # Extract agent name from endpoint
        agent_name = self._parse_endpoint(endpoint)

        # Check if agent is directly available in this process
        local_handler = self._registry.get_agent(agent_name)
        if local_handler:
            # Direct invocation
            try:
                result = local_handler(capability, params or {})
                # Check if result is a generator and convert to list
                # for JSON serialization
                if hasattr(result, "__iter__") and hasattr(result, "__next__"):
                    # It's a generator, convert to list
                    return list(result)
                return result
            except Exception as e:
                raise TransportError(f"Error invoking local agent: {str(e)}")

        # Get socket path from registry or use endpoint directly
        socket_path = self._registry.get_socket_path(agent_name)
        if not socket_path:
            # Assume endpoint is a direct socket path if not in registry
            socket_path = endpoint

        # Use socket to communicate with the agent
        try:
            return self._send_request(
                socket_path,
                capability,
                params or {},
                timeout=timeout,
                request_id=kwargs.get("request_id", str(uuid.uuid4())),
            )
        except TimeoutError:
            raise TransportTimeoutError(
                f"Local transport request timed out after {timeout} seconds"
            )
        except Exception as e:
            raise TransportError(f"Local transport error: {str(e)}")

    def stream(
        self,
        endpoint: str,
        capability: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> Iterator[Any]:
        """
        Stream responses from a local agent capability.

        Args:
            endpoint: The agent name or socket path
            capability: The capability to invoke
            params: Optional parameters to pass to the capability
            headers: Ignored for local transport
            timeout: Optional timeout in seconds
            **kwargs: Additional transport-specific parameters

        Returns:
            An iterator that yields response parts

        Raises:
            TransportError: If there is an error communicating with the agent
            TransportTimeoutError: If the connection times out
        """
        if timeout is None:
            timeout = 60  # Default timeout

        # Extract agent name from endpoint
        agent_name = self._parse_endpoint(endpoint)

        # Check if agent is directly available in this process
        local_handler = self._registry.get_agent(agent_name)
        if local_handler:
            # Direct streaming invocation
            try:
                for item in local_handler(capability, params or {}):
                    yield self.parse_response(item)
                return
            except Exception as e:
                raise TransportError(f"Error streaming from local agent: {str(e)}")

        # Get socket path from registry or use endpoint directly
        socket_path = self._registry.get_socket_path(agent_name)
        if not socket_path:
            # Assume endpoint is a direct socket path if not in registry
            socket_path = endpoint

        # Use socket to stream from the agent
        try:
            for chunk in self._stream_request(
                socket_path,
                capability,
                params or {},
                timeout=timeout,
                request_id=kwargs.get("request_id", str(uuid.uuid4())),
            ):
                yield self.parse_response(chunk)
        except TimeoutError:
            raise TransportTimeoutError(
                f"Local streaming timed out after {timeout} seconds"
            )
        except Exception as e:
            raise TransportError(f"Local transport error: {str(e)}")

    def register_agent(
        self, name: str, handler: Callable, socket_path: Optional[str] = None
    ) -> str:
        """
        Register a local agent with this transport.

        Args:
            name: Name of the agent
            handler: Function or object that handles agent invocations
            socket_path: Optional custom socket path

        Returns:
            Socket path for the agent
        """
        return self._registry.register_agent(name, handler, socket_path)

    def unregister_agent(self, name: str) -> bool:
        """
        Unregister a local agent.

        Args:
            name: Name of the agent to unregister

        Returns:
            True if agent was unregistered, False if not found
        """
        return self._registry.unregister_agent(name)

    def list_local_agents(self) -> Dict[str, str]:
        """
        List all registered local agents.

        Returns:
            Dictionary mapping agent names to socket paths
        """
        return self._registry.list_agents()

    def _parse_endpoint(self, endpoint: str) -> str:
        """
        Parse an endpoint to extract the agent name.

        Args:
            endpoint: The endpoint string

        Returns:
            Agent name
        """
        # Remove protocol prefix if present
        if endpoint.startswith(("local://", "agent+local://", "agent://")):
            if endpoint.startswith("local://"):
                agent_name = endpoint[len("local://") :]
            elif endpoint.startswith("agent+local://"):
                agent_name = endpoint[len("agent+local://") :]
            else:  # agent://
                agent_name = endpoint[len("agent://") :]
        else:
            agent_name = endpoint

        # Remove path components if present
        if "/" in agent_name:
            agent_name = agent_name.split("/", 1)[0]

        # Remove query parameters if present
        if "?" in agent_name:
            agent_name = agent_name.split("?", 1)[0]

        return agent_name

    def _send_request(
        self,
        socket_path: str,
        capability: str,
        params: Dict[str, Any],
        timeout: int = 60,
        request_id: str = None,
    ) -> Any:
        """
        Send a request to a local agent via socket.

        Args:
            socket_path: Socket path to connect to
            capability: Capability to invoke
            params: Parameters to pass to the capability
            timeout: Timeout in seconds
            request_id: Optional request ID

        Returns:
            Response from the agent

        Raises:
            Various exceptions for connection and timeout errors
        """
        request_id = request_id or str(uuid.uuid4())

        # Prepare request
        request = {
            "capability": capability,
            "params": params,
            "id": request_id,
            "streaming": False,
        }

        # Connect to socket
        sock = None
        try:
            if socket_path.startswith("127.0.0.1"):
                # TCP socket
                host, port = socket_path.split(":")
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((host, int(port)))
            else:
                # Unix domain socket
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(socket_path)

            # Set timeout
            sock.settimeout(timeout)

            # Send request
            sock.sendall(json.dumps(request).encode("utf-8") + b"\n")

            # Read response
            data = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
                if data.endswith(b"\n"):
                    break

            if not data:
                raise TransportError("No response received from local agent")

            # Parse response
            response = json.loads(data.decode("utf-8"))

            # Check for errors
            if "error" in response:
                raise TransportError(f"Local agent error: {response['error']}")

            # Return result
            return response.get("result")

        finally:
            if sock:
                try:
                    sock.close()
                except Exception:  # nosec B110
                    pass

    def _stream_request(
        self,
        socket_path: str,
        capability: str,
        params: Dict[str, Any],
        timeout: int = 60,
        request_id: str = None,
    ) -> Iterator[Any]:
        """
        Stream a request from a local agent via socket.

        Args:
            socket_path: Socket path to connect to
            capability: Capability to invoke
            params: Parameters to pass to the capability
            timeout: Timeout in seconds
            request_id: Optional request ID

        Returns:
            Iterator yielding chunks of the response

        Raises:
            Various exceptions for connection and timeout errors
        """
        request_id = request_id or str(uuid.uuid4())

        # Prepare request
        request = {
            "capability": capability,
            "params": params,
            "id": request_id,
            "streaming": True,
        }

        # Connect to socket
        sock = None
        try:
            if socket_path.startswith("127.0.0.1"):
                # TCP socket
                host, port = socket_path.split(":")
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((host, int(port)))
            else:
                # Unix domain socket
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(socket_path)

            # Set timeout
            sock.settimeout(timeout)

            # Send request
            sock.sendall(json.dumps(request).encode("utf-8") + b"\n")

            # Read streaming response
            buffer = b""
            complete = False

            while not complete:
                chunk = sock.recv(4096)
                if not chunk:
                    break

                buffer += chunk

                # Process any complete messages in the buffer
                while b"\n" in buffer:
                    message, buffer = buffer.split(b"\n", 1)
                    if not message:
                        continue

                    try:
                        data = json.loads(message.decode("utf-8"))

                        # Check for completion
                        if data.get("complete", False):
                            complete = True
                            break

                        # Check for errors
                        if "error" in data:
                            raise TransportError(f"Local agent error: {data['error']}")

                        # Yield chunk if present
                        if "chunk" in data:
                            yield data["chunk"]

                    except json.JSONDecodeError:
                        # Skip invalid messages
                        continue

        finally:
            if sock:
                try:
                    sock.close()
                except Exception:  # nosec B110
                    pass
