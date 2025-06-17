"""
WebSocket transport adapter for agent:// protocol.

This module implements the WebSocket transport for the agent:// protocol,
providing support for real-time streaming communication with agents.
"""

import json
import logging
import threading
import time
from queue import Empty, Queue
from typing import Any, Dict, Iterator, Optional

# Try importing websocket library, provide clear error message if missing
try:
    import websocket
except ImportError:
    raise ImportError(
        "The 'websocket-client' package is required. "
        "Please install it using: pip install websocket-client"
    )

from ..base import AgentTransport, TransportError, TransportTimeoutError

logger = logging.getLogger(__name__)


class WebSocketTransport(AgentTransport):
    """
    WebSocket transport adapter for agent:// protocol.

    This transport handles WebSocket connections to agent endpoints,
    supporting both synchronous (invoke) and streaming (stream) patterns.
    """

    def __init__(
        self,
        user_agent: str = "AgentURI-Transport/1.0",
        verify_ssl: bool = True,
        ping_interval: int = 30,
        ping_timeout: int = 10,
        reconnect_tries: int = 3,
        reconnect_delay: int = 2,
    ):
        """
        Initialize a WebSocket transport adapter.

        Args:
            user_agent: User-Agent header to include in WebSocket handshake
            verify_ssl: Whether to verify SSL certificates
            ping_interval: Interval between ping messages (seconds)
            ping_timeout: Timeout waiting for pong response (seconds)
            reconnect_tries: Number of reconnection attempts
            reconnect_delay: Delay between reconnection attempts (seconds)
        """
        self._user_agent = user_agent
        self._verify_ssl = verify_ssl
        self._ping_interval = ping_interval
        self._ping_timeout = ping_timeout
        self._reconnect_tries = reconnect_tries
        self._reconnect_delay = reconnect_delay

        # Connection state
        self._ws = None
        self._is_connected = False
        self._message_queue = Queue()
        self._response_queue = Queue()
        self._ws_thread = None
        self._request_id = 0
        self._active_requests = {}
        self._request_callbacks = {}

    @property
    def protocol(self) -> str:
        """Return the transport protocol identifier."""
        return "wss"

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
        Invoke an agent capability via WebSocket.

        This method follows a request/response pattern over WebSocket.

        Args:
            endpoint: The endpoint URL for the agent
            capability: The capability to invoke (path component)
            params: Optional parameters to pass to the capability
            headers: Optional headers to include in the handshake
            timeout: Optional timeout in seconds
            **kwargs: Additional transport-specific parameters
                - json_rpc: Whether to use JSON-RPC format (default: True)
                - message_format: Format for non-JSON-RPC messages

        Returns:
            The response from the agent

        Raises:
            TransportError: If there is an error communicating with the agent
            TransportTimeoutError: If the request times out
        """
        if timeout is None:
            timeout = 60  # Default timeout

        # Create full URL
        url = self._build_url(endpoint, capability)

        # Prepare request message
        request_id = self._get_next_request_id()

        # Determine message format
        json_rpc = kwargs.get("json_rpc", True)

        if json_rpc:
            # JSON-RPC format
            message = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": capability,
                "params": params or {},
            }
        else:
            # Custom message format
            message_format = kwargs.get("message_format", {})
            message = {
                "id": request_id,
                "capability": capability,
                **(message_format or {}),
            }
            if params:
                message["params"] = params

        # Connect if not already connected
        if not self._is_connected:
            self._connect(url, headers)

        # Set up a response future
        response_event = threading.Event()
        response = [None]  # Use list for mutable closure

        def on_response(resp):
            response[0] = resp
            response_event.set()

        # Register callback for this request
        self._request_callbacks[request_id] = on_response

        # Send message
        message_str = json.dumps(message)
        try:
            self._ws.send(message_str)
        except Exception as e:
            del self._request_callbacks[request_id]
            raise TransportError(f"Error sending WebSocket message: {str(e)}")

        # Wait for response with timeout
        if not response_event.wait(timeout):
            del self._request_callbacks[request_id]
            raise TransportTimeoutError(
                f"WebSocket request timed out after {timeout} seconds"
            )

        del self._request_callbacks[request_id]

        # Check for errors
        if isinstance(response[0], Exception):
            raise TransportError(f"WebSocket error: {str(response[0])}")

        return self.parse_response(response[0])

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
        Stream responses from an agent capability via WebSocket.

        This method establishes a WebSocket connection and yields
        messages as they arrive.

        Args:
            endpoint: The endpoint URL for the agent
            capability: The capability to invoke (path component)
            params: Optional parameters to pass to the capability
            headers: Optional headers to include in the handshake
            timeout: Optional timeout in seconds
            **kwargs: Additional transport-specific parameters
                - json_rpc: Whether to use JSON-RPC format (default: True)
                - close_on_complete: Whether to close connection when done
                - message_format: Format for non-JSON-RPC messages

        Returns:
            An iterator that yields response messages

        Raises:
            TransportError: If there is an error communicating with the agent
            TransportTimeoutError: If the connection times out
        """
        if timeout is None:
            timeout = 60  # Default connection timeout

        # Create full URL
        url = self._build_url(endpoint, capability)

        # Check if connection should be closed when streaming completes
        close_on_complete = kwargs.get("close_on_complete", True)

        # Connect if not already connected
        if not self._is_connected:
            self._connect(url, headers)

        # Prepare request message
        request_id = self._get_next_request_id()

        # Determine message format
        json_rpc = kwargs.get("json_rpc", True)

        if json_rpc:
            # JSON-RPC format
            message = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": capability,
                "params": params or {},
            }
        else:
            # Custom message format
            message_format = kwargs.get("message_format", {})
            message = {
                "id": request_id,
                "capability": capability,
                "stream": True,
                **(message_format or {}),
            }
            if params:
                message["params"] = params

        # Set up message queue for this request
        message_queue = Queue()
        streaming_complete = threading.Event()

        def on_stream_message(msg):
            try:
                if isinstance(msg, dict) and msg.get("type") == "complete":
                    streaming_complete.set()
                else:
                    message_queue.put(msg)
            except Exception as e:
                message_queue.put(e)
                streaming_complete.set()

        # Register callback for this request
        self._request_callbacks[request_id] = on_stream_message

        # Send message
        message_str = json.dumps(message)
        try:
            self._ws.send(message_str)
        except Exception as e:
            del self._request_callbacks[request_id]
            raise TransportError(f"Error sending WebSocket message: {str(e)}")

        # Yield messages as they arrive
        try:
            while not streaming_complete.is_set():
                try:
                    msg = message_queue.get(timeout=timeout)
                    if isinstance(msg, Exception):
                        raise TransportError(f"WebSocket error: {str(msg)}")
                    yield self.parse_response(msg)
                except Empty:
                    # No message received within timeout
                    if self._ws.connected:
                        continue  # Still connected, keep waiting
                    else:
                        raise TransportError("WebSocket connection closed")
                except Exception as e:
                    if isinstance(e, TransportError):
                        raise
                    raise TransportError(f"Error processing stream: {str(e)}")
        finally:
            # Clean up
            del self._request_callbacks[request_id]
            if close_on_complete and self._is_connected:
                self._disconnect()

    def _connect(self, url: str, headers: Optional[Dict[str, str]] = None) -> None:
        """
        Establish a WebSocket connection.

        Args:
            url: The WebSocket URL to connect to
            headers: Optional headers to include in the handshake

        Raises:
            TransportError: If connection fails
        """
        if self._is_connected:
            return

        # Prepare headers
        ws_headers = {"User-Agent": self._user_agent}
        if headers:
            ws_headers.update(headers)

        # Convert from wss:// to https:// if needed for websocket-client
        ws_url = url
        if ws_url.startswith("http"):
            ws_url = ws_url.replace("http", "ws")
        elif not (ws_url.startswith("ws://") or ws_url.startswith("wss://")):
            ws_url = f"wss://{ws_url}"

        # Create WebSocket client
        try:
            self._ws = websocket.WebSocketApp(
                ws_url,
                header=ws_headers,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )

            # Start WebSocket thread
            self._ws_thread = threading.Thread(
                target=self._ws.run_forever,
                kwargs={
                    "ping_interval": self._ping_interval,
                    "ping_timeout": self._ping_timeout,
                    "sslopt": {"cert_reqs": 2 if self._verify_ssl else 0},
                },
                daemon=True,
            )
            self._ws_thread.start()

            # Wait for connection to establish
            for _ in range(10):  # Wait up to 5 seconds
                if self._is_connected:
                    break
                time.sleep(0.5)

            if not self._is_connected:
                raise TransportError("Failed to establish WebSocket connection")

        except Exception as e:
            raise TransportError(f"WebSocket connection error: {str(e)}")

    def _disconnect(self) -> None:
        """Close the WebSocket connection."""
        if self._ws and self._is_connected:
            try:
                self._ws.close()
            except Exception:  # nosec B110
                pass  # Ignore errors on close

            self._is_connected = False
            self._ws = None

            # Clear queues
            self._clear_queue(self._message_queue)
            self._clear_queue(self._response_queue)

    def _clear_queue(self, queue: Queue) -> None:
        """Clear all items from a queue."""
        while not queue.empty():
            try:
                queue.get_nowait()
                queue.task_done()
            except Empty:
                break

    def _on_open(self, ws) -> None:
        """Handle WebSocket open event."""
        self._is_connected = True
        logger.debug("WebSocket connection established")

    def _on_message(self, ws, message: str) -> None:
        """
        Handle incoming WebSocket messages.

        Args:
            ws: WebSocket instance
            message: Message received
        """
        try:
            # Parse message as JSON
            if isinstance(message, bytes):
                message = message.decode("utf-8")

            data = json.loads(message)

            # Check if this is a response to a specific request
            if isinstance(data, dict):
                # Handle JSON-RPC response
                if "id" in data:
                    request_id = data.get("id")
                    if request_id in self._request_callbacks:
                        callback = self._request_callbacks[request_id]
                        callback(data)
                        return

                # Handle stream message with a result field
                if "result" in data and "id" in data:
                    request_id = data.get("id")
                    if request_id in self._request_callbacks:
                        callback = self._request_callbacks[request_id]
                        callback(data.get("result"))
                        return

            # Put in the general message queue if no specific handler
            self._message_queue.put(data)

        except json.JSONDecodeError:
            # Handle non-JSON messages
            self._message_queue.put(message)
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {str(e)}")
            self._message_queue.put(e)

    def _on_error(self, ws, error) -> None:
        """
        Handle WebSocket error event.

        Args:
            ws: WebSocket instance
            error: Error that occurred
        """
        logger.error(f"WebSocket error: {str(error)}")

        # Notify waiting requests
        for callback in self._request_callbacks.values():
            callback(error)

        self._message_queue.put(error)

    def _on_close(self, ws, close_status_code, close_reason) -> None:
        """
        Handle WebSocket close event.

        Args:
            ws: WebSocket instance
            close_status_code: Status code for closure
            close_reason: Reason for closure
        """
        self._is_connected = False
        logger.debug(
            f"WebSocket closed (code: {close_status_code}, " f"reason: {close_reason})"
        )

    def _build_url(self, endpoint: str, capability: str) -> str:
        """
        Build the full WebSocket URL for a capability.

        Args:
            endpoint: The base endpoint URL
            capability: The capability to invoke

        Returns:
            The full URL including the capability path
        """
        # Ensure endpoint doesn't end with slash
        endpoint = endpoint.rstrip("/")

        # Ensure capability doesn't start with slash
        capability = capability.lstrip("/")

        # Handle WebSocket URL conversion
        if not (endpoint.startswith("ws://") or endpoint.startswith("wss://")):
            if endpoint.startswith("http://"):
                endpoint = endpoint.replace("http://", "ws://")
            elif endpoint.startswith("https://"):
                endpoint = endpoint.replace("https://", "wss://")
            else:
                # Default to secure WebSocket
                endpoint = f"wss://{endpoint}"

        # Combine to form the full URL
        return f"{endpoint}/{capability}"

    def _get_next_request_id(self) -> str:
        """Get a unique request ID."""
        self._request_id += 1
        return f"req-{self._request_id}"
