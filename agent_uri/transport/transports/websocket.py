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
from typing import Any, Callable, Dict, Iterator, Optional, Union

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

# Security configuration constants
MAX_MESSAGE_SIZE = 1048576  # 1MB maximum message size
MAX_JSON_DEPTH = 64  # Maximum JSON nesting depth
MAX_JSON_OBJECTS = 10000  # Maximum JSON objects/arrays
MAX_QUEUE_SIZE = 1000  # Maximum message queue size


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
        max_message_size: int = MAX_MESSAGE_SIZE,
        max_json_depth: int = MAX_JSON_DEPTH,
        max_queue_size: int = MAX_QUEUE_SIZE,
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
            max_message_size: Maximum allowed message size in bytes
            max_json_depth: Maximum allowed JSON nesting depth
            max_queue_size: Maximum number of queued messages
        """
        self._user_agent = user_agent
        self._verify_ssl = verify_ssl
        self._ping_interval = ping_interval
        self._ping_timeout = ping_timeout
        self._reconnect_tries = reconnect_tries
        self._reconnect_delay = reconnect_delay

        # Security configuration
        self._max_message_size = max_message_size
        self._max_json_depth = max_json_depth
        self._max_queue_size = max_queue_size

        # Connection state
        self._ws: Optional[websocket.WebSocketApp] = None
        self._is_connected = False
        # Security: Limit queue sizes to prevent memory exhaustion
        self._message_queue: Queue[Union[Dict[str, Any], str, Exception]] = Queue(
            maxsize=self._max_queue_size
        )
        self._response_queue: Queue[Dict[str, Any]] = Queue(
            maxsize=self._max_queue_size
        )
        self._ws_thread: Optional[threading.Thread] = None
        self._request_id = 0
        self._active_requests: Dict[str, Dict[str, Any]] = {}
        self._request_callbacks: Dict[
            str, Callable[[Union[Dict[str, Any], Exception]], None]
        ] = {}

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

        message: Dict[str, Any]
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

        # Set up a response queue for this request
        response_queue: Queue[Any] = Queue()

        # Register active request
        self._active_requests[request_id] = {
            "capability": capability,
            "response_queue": response_queue,
        }

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
            if self._ws is None:
                raise TransportError("WebSocket connection not established")
            self._ws.send(message_str)
        except Exception as e:
            # Clean up on error
            if request_id in self._request_callbacks:
                del self._request_callbacks[request_id]
            if request_id in self._active_requests:
                del self._active_requests[request_id]
            raise TransportError(f"Error sending WebSocket message: {str(e)}")

        # Wait for response with timeout
        if not response_event.wait(timeout):
            # Clean up on timeout
            if request_id in self._request_callbacks:
                del self._request_callbacks[request_id]
            if request_id in self._active_requests:
                del self._active_requests[request_id]
            raise TransportTimeoutError(
                f"WebSocket request timed out after {timeout} seconds"
            )

        # Clean up after response
        if request_id in self._request_callbacks:
            del self._request_callbacks[request_id]
        if request_id in self._active_requests:
            del self._active_requests[request_id]

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

        message: Dict[str, Any]
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
            }
            if message_format:
                message.update(message_format)
            if params:
                message["params"] = params

        # Set up message queue for this request
        message_queue: Queue[Dict[str, Any]] = Queue()
        streaming_complete = threading.Event()

        def on_stream_message(msg):
            try:
                if isinstance(msg, dict) and msg.get("type") == "complete":
                    streaming_complete.set()
                elif isinstance(msg, Exception):
                    # Handle error by putting it in queue, but don't mark complete yet
                    # The stream loop will process the error and then complete
                    message_queue.put(msg)
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
            if self._ws is None:
                raise TransportError("WebSocket connection not established")
            self._ws.send(message_str)
        except Exception as e:
            # Clean up on send error
            if request_id in self._request_callbacks:
                del self._request_callbacks[request_id]
            raise TransportError(f"Error sending WebSocket message: {str(e)}")

        # Yield messages as they arrive
        import time

        start_time = time.time()
        max_wait_time = timeout or 60  # Default to 60 seconds total

        try:
            while not streaming_complete.is_set():
                # Check total elapsed time to prevent infinite loops
                elapsed = time.time() - start_time
                if elapsed >= max_wait_time:
                    raise TransportTimeoutError(
                        f"Streaming timed out after {elapsed:.1f} seconds"
                    )

                # Calculate remaining timeout for this iteration
                remaining_timeout = min(
                    1.0, max_wait_time - elapsed
                )  # Use 1 second chunks for better responsiveness
                if remaining_timeout <= 0:
                    raise TransportTimeoutError("Streaming timeout exceeded")

                try:
                    msg = message_queue.get(timeout=remaining_timeout)
                    if isinstance(msg, Exception):
                        # Error received - mark stream as complete and raise
                        streaming_complete.set()
                        raise TransportError(f"WebSocket error: {str(msg)}")
                    yield self.parse_response(msg)
                except Empty:
                    # No message received within timeout
                    if self._ws and self._is_connected:
                        continue  # Still connected, keep waiting
                    else:
                        raise TransportError("WebSocket connection closed")
                except Exception as e:
                    if isinstance(e, TransportError):
                        raise
                    raise TransportError(f"Error processing stream: {str(e)}")
        finally:
            # Clean up - use safe deletion in case callback was already removed
            if request_id in self._request_callbacks:
                del self._request_callbacks[request_id]
            if close_on_complete and self._is_connected:
                self._disconnect()

    def _connect(self, url: str, headers: Optional[Dict[str, str]] = None) -> None:
        """
        Establish a WebSocket connection with retry logic.

        Args:
            url: The WebSocket URL to connect to
            headers: Optional headers to include in the handshake

        Raises:
            TransportError: If connection fails after all retries
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

        # Retry connection attempts
        last_error = None
        for attempt in range(self._reconnect_tries + 1):  # +1 for initial attempt
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
                if self._ws_thread is not None:
                    self._ws_thread.start()

                # Wait for connection to establish
                for _ in range(10):  # Wait up to 5 seconds
                    if self._is_connected:
                        return  # Success!

                    # Check for errors that occurred during connection
                    try:
                        error = self._message_queue.get_nowait()
                        if isinstance(error, Exception):
                            last_error = error
                            break
                    except Exception:  # nosec B110
                        pass  # No error queued

                    time.sleep(0.5)

                # Connection failed, prepare for retry
                self._is_connected = False
                # Only set timeout error if no previous error was captured
                if last_error is None:
                    last_error = Exception("Connection timeout")
            except Exception as e:
                last_error = e
                self._is_connected = False

            # If this wasn't the last attempt, wait before retrying
            if attempt < self._reconnect_tries:
                time.sleep(self._reconnect_delay)

        # All attempts failed
        attempts = self._reconnect_tries + 1
        error_msg = (
            f"Failed to establish WebSocket connection after {attempts} attempts"
        )
        raise TransportError(f"{error_msg}: {str(last_error)}")

    def close(self) -> None:
        """Close the WebSocket connection."""
        self._disconnect()

    def _disconnect(self) -> None:
        """Close the WebSocket connection."""
        if self._ws and self._is_connected:
            try:
                self._ws.close()
            except Exception:  # nosec B110
                pass  # Ignore errors on close

        # Always clear connection state
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

    def _validate_message_size(self, message: Union[str, bytes]) -> None:
        """
        Validate message size against security limits.

        Args:
            message: Message to validate

        Raises:
            TransportError: If message exceeds size limits
        """
        if isinstance(message, bytes):
            size = len(message)
        else:
            size = len(message.encode("utf-8"))

        if size > self._max_message_size:
            raise TransportError(
                f"Message size {size} bytes exceeds maximum allowed size "
                f"{self._max_message_size} bytes"
            )

    def _validate_json_structure(self, data: Any, depth: int = 0) -> None:
        """
        Validate JSON structure against security limits.

        Args:
            data: Parsed JSON data to validate
            depth: Current nesting depth

        Raises:
            TransportError: If JSON structure violates security limits
        """
        if depth > self._max_json_depth:
            raise TransportError(
                f"JSON nesting depth {depth} exceeds maximum allowed depth "
                f"{self._max_json_depth}"
            )

        if isinstance(data, dict):
            if len(data) > MAX_JSON_OBJECTS:
                raise TransportError(
                    f"JSON object count exceeds maximum allowed {MAX_JSON_OBJECTS}"
                )
            for value in data.values():
                self._validate_json_structure(value, depth + 1)
        elif isinstance(data, list):
            if len(data) > MAX_JSON_OBJECTS:
                raise TransportError(
                    f"JSON array length exceeds maximum allowed {MAX_JSON_OBJECTS}"
                )
            for item in data:
                self._validate_json_structure(item, depth + 1)

    def _safe_json_parse(self, message: str) -> Any:
        """
        Safely parse JSON with validation.

        Args:
            message: JSON string to parse

        Returns:
            Parsed JSON data

        Raises:
            TransportError: If JSON is invalid or violates security limits
        """
        try:
            data = json.loads(message)
            self._validate_json_structure(data)
            return data
        except json.JSONDecodeError as e:
            raise TransportError(f"Invalid JSON format: {e}")
        except TransportError:
            raise  # Re-raise security validation errors
        except Exception as e:
            raise TransportError(f"JSON parsing error: {e}")

    def _sanitize_error_message(self, error_msg: str) -> str:
        """
        Sanitize error messages to prevent information disclosure.

        Args:
            error_msg: Raw error message

        Returns:
            Sanitized error message safe for client exposure
        """
        # Remove potentially sensitive information
        import re

        # Remove file paths (absolute and relative)
        error_msg = re.sub(r"[/\\][\w\-_./\\]+", "[path]", error_msg)

        # Remove IP addresses
        error_msg = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[ip]", error_msg)

        # Remove port numbers
        error_msg = re.sub(r":\d{1,5}\b", ":[port]", error_msg)

        # Remove stack trace patterns
        error_msg = re.sub(
            r'File "[^"]*", line \d+', 'File "[file]", line [line]', error_msg
        )

        # Remove internal variable names and memory addresses
        error_msg = re.sub(r"0x[0-9a-fA-F]+", "[address]", error_msg)

        # Limit message length to prevent information leakage
        max_length = 200
        if len(error_msg) > max_length:
            error_msg = error_msg[:max_length] + "..."

        return error_msg

    def _on_open(self, ws) -> None:
        """Handle WebSocket open event."""
        self._is_connected = True
        logger.debug("WebSocket connection established")

    def _on_message(self, ws, message: str) -> None:
        """
        Handle incoming WebSocket messages with security validation.

        Args:
            ws: WebSocket instance
            message: Message received
        """
        try:
            # Security: Validate message size before processing
            self._validate_message_size(message)

            # Convert bytes to string if needed
            if isinstance(message, bytes):
                message = message.decode("utf-8")

            # First try to parse as JSON
            try:
                parsed_data = json.loads(message)
                # Security: Validate the parsed JSON structure
                self._validate_json_structure(parsed_data)
                data = parsed_data
            except json.JSONDecodeError:
                # Not valid JSON - queue as-is for backward compatibility
                self._message_queue.put(message)
                return
            except TransportError:
                # Security validation failed - reraise to be caught below
                raise

            # Check if this is a response to a specific request
            if isinstance(data, dict) and "id" in data:
                request_id = data.get("id")

                # Check for active requests first (used by invoke)
                if request_id in self._active_requests:
                    request_info = self._active_requests[request_id]
                    response_queue = request_info.get("response_queue")

                    if response_queue:
                        # Handle JSON-RPC error response
                        if "error" in data:
                            error_info = data.get("error", {})
                            raw_error_msg = error_info.get("message", "Unknown error")
                            error_code = error_info.get("code", -1)
                            # Security: Sanitize error message before exposing to client
                            sanitized_msg = self._sanitize_error_message(raw_error_msg)
                            error = TransportError(
                                f"{sanitized_msg} (code: {error_code})"
                            )
                            response_queue.put(error)
                            # Also trigger callback if exists to unblock waiting threads
                            if request_id in self._request_callbacks:
                                self._request_callbacks[request_id](error)
                            return

                        # Handle JSON-RPC result
                        if "result" in data:
                            response_queue.put(data["result"])
                            # Also trigger callback if exists to unblock waiting threads
                            if request_id in self._request_callbacks:
                                self._request_callbacks[request_id](data["result"])
                            return

                        # Handle streaming complete
                        if data.get("complete"):
                            # Mark stream as complete
                            response_queue.put({"type": "complete"})
                            # Clean up active request and callback
                            if request_id in self._active_requests:
                                del self._active_requests[request_id]
                            if request_id in self._request_callbacks:
                                del self._request_callbacks[request_id]
                            return

                # Check for request callbacks (used by stream)
                if request_id in self._request_callbacks:
                    callback = self._request_callbacks[request_id]

                    # Handle JSON-RPC error response
                    if "error" in data:
                        error_info = data.get("error", {})
                        raw_error_msg = error_info.get("message", "Unknown error")
                        error_code = error_info.get("code", -1)
                        # Security: Sanitize error message before exposing to client
                        sanitized_msg = self._sanitize_error_message(raw_error_msg)
                        error = TransportError(f"{sanitized_msg} (code: {error_code})")
                        callback(error)  # type: ignore[arg-type]
                        # Remove callback for non-streaming responses
                        del self._request_callbacks[request_id]
                        return

                    # Handle streaming chunk
                    if "chunk" in data and data.get("streaming"):
                        callback(data["chunk"])
                        # Keep callback for more chunks
                        return

                    # Handle streaming complete
                    if data.get("complete"):
                        # Signal completion to the stream
                        callback({"type": "complete"})
                        # Remove callback when streaming is complete
                        del self._request_callbacks[request_id]
                        return

                    # Handle JSON-RPC result
                    if "result" in data:
                        callback(data["result"])
                        # Remove callback for non-streaming responses
                        del self._request_callbacks[request_id]
                        return

                    # Handle simple response with just id
                    callback(data)
                    # Remove callback for non-streaming responses
                    del self._request_callbacks[request_id]
                    return

            # Put in the general message queue if no specific handler
            self._message_queue.put(data)

        except TransportError as e:
            # Security validation failed - log error and queue the error
            logger.error(f"Security validation failed for WebSocket message: {str(e)}")
            self._message_queue.put(e)
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

        # Clear all pending requests and callbacks
        self._active_requests.clear()
        self._request_callbacks.clear()

        # Clear message queues
        self._clear_queue(self._message_queue)
        self._clear_queue(self._response_queue)

    def format_body(self, params: Any) -> Union[str, bytes]:
        """
        Format the parameters into a request body.

        Handles strings as plain text, and dicts/lists as pretty-printed JSON.
        """
        if isinstance(params, str):
            return params  # Return strings as-is
        elif isinstance(params, (dict, list)):
            return json.dumps(params, indent=2)
        return json.dumps(params)

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
