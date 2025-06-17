"""
HTTPS transport adapter for agent:// protocol.

This module implements the HTTPS transport for the agent:// protocol,
providing support for both synchronous and streaming HTTP(S) requests.
"""

import json
import logging
import urllib.parse
from typing import Any, Dict, Iterator, Optional

# Try importing requests, provide clear error message if missing
try:
    import requests
    import sseclient  # For server-sent events (streaming)
    from requests.exceptions import ConnectionError, RequestException, Timeout
except ImportError:
    raise ImportError(
        "The 'requests' and 'sseclient-py' packages are required. "
        "Please install them using: pip install requests sseclient-py"
    )

from ..base import AgentTransport, TransportError, TransportTimeoutError

logger = logging.getLogger(__name__)


class HttpsTransport(AgentTransport):
    """
    HTTPS transport adapter for agent:// protocol.

    This transport handles HTTP and HTTPS requests to agent endpoints,
    supporting both synchronous (invoke) and streaming (stream) patterns.
    """

    def format_body(self, data):
        """Format data as JSON for request body."""
        return json.dumps(data)

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        verify_ssl: bool = True,
        user_agent: str = "AgentURI-Transport/1.0",
    ):
        """
        Initialize an HTTPS transport adapter.

        Args:
            session: Optional requests session to use (creates a new one if None)
            verify_ssl: Whether to verify SSL certificates
            user_agent: User-Agent header to include in requests
        """
        self._session = session or requests.Session()
        self._verify_ssl = verify_ssl
        self._user_agent = user_agent

        # Set default headers
        self._session.headers.update(
            {"User-Agent": self._user_agent, "Accept": "application/json"}
        )

    @property
    def protocol(self) -> str:
        """Return the transport protocol identifier."""
        return "https"

    @property
    def session(self) -> requests.Session:
        """Get the requests session being used."""
        return self._session

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
        Invoke an agent capability via HTTPS.

        Args:
            endpoint: The endpoint URL for the agent
            capability: The capability to invoke (path component)
            params: Optional parameters to pass to the capability
            headers: Optional headers to include in the request
            timeout: Optional timeout in seconds
            **kwargs: Additional transport-specific parameters
                - method: HTTP method to use ('GET' or 'POST', default based on params)
                - auth: Authentication tuple or object for requests
                - verify: Whether to verify SSL certificates (overrides init)
                - allow_redirects: Whether to follow redirects

        Returns:
            The parsed response from the agent

        Raises:
            TransportError: If there is an error communicating with the agent
            TransportTimeoutError: If the request times out
        """
        # Create full URL
        url = self._build_url(endpoint, capability)

        # Prepare request arguments
        request_kwargs = self._prepare_request_args(
            params=params, headers=headers, timeout=timeout, **kwargs
        )

        # Determine HTTP method (POST if params present, otherwise GET)
        method = kwargs.get("method")
        if method is None:
            method = "POST" if params else "GET"

        # Make the request
        try:
            # Remove method from kwargs if present to avoid passing it twice
            if "method" in request_kwargs:
                request_kwargs.pop("method")

            if method.upper() == "GET":
                # For GET, params go in query string
                response = self._session.get(url, **request_kwargs)
            else:
                # For POST and others, params go in request body
                # Remove params from kwargs to avoid duplicating in query string
                query_params = request_kwargs.pop("params", None)

                # Add query params to URL if present
                if query_params:
                    query_string = urllib.parse.urlencode(query_params)
                    url = f"{url}?{query_string}"

                # Convert params to JSON body
                if params:
                    request_kwargs["data"] = self.format_body(params)
                    if "headers" in request_kwargs:
                        request_kwargs["headers"]["Content-Type"] = "application/json"
                    else:
                        request_kwargs["headers"] = {"Content-Type": "application/json"}

                response = self._session.request(method, url, **request_kwargs)

            # Check for errors
            response.raise_for_status()

            # Parse and return the response
            return self._parse_response(response)

        except Timeout:
            raise TransportTimeoutError(f"Request to {url} timed out")
        except ConnectionError as e:
            raise TransportError(f"Connection error: {str(e)}")
        except RequestException as e:
            if hasattr(e, "response") and e.response is not None:
                status_code = e.response.status_code
                error_detail = self._extract_error_detail(e.response)
                raise TransportError(f"HTTP {status_code} error: {error_detail}")
            raise TransportError(f"Request failed: {str(e)}")

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
        Stream responses from an agent capability via HTTPS.

        This method supports different streaming protocols:
        - Server-Sent Events (SSE)
        - Newline-delimited JSON (NDJSON)
        - Raw streaming responses

        Args:
            endpoint: The endpoint URL for the agent
            capability: The capability to invoke (path component)
            params: Optional parameters to pass to the capability
            headers: Optional headers to include in the request
            timeout: Optional timeout in seconds
            **kwargs: Additional transport-specific parameters
                - method: HTTP method to use ('GET' or 'POST', default based on params)
                - auth: Authentication tuple or object for requests
                - verify: Whether to verify SSL certificates (overrides init)
                - allow_redirects: Whether to follow redirects
                - stream_format: Format of the stream ('sse', 'ndjson', 'raw')

        Returns:
            An iterator that yields response parts

        Raises:
            TransportError: If there is an error communicating with the agent
            TransportTimeoutError: If the request times out
        """
        # Create full URL
        url = self._build_url(endpoint, capability)

        # Prepare request arguments
        request_kwargs = self._prepare_request_args(
            params=params, headers=headers, timeout=timeout, **kwargs
        )

        # Streaming requires stream=True
        request_kwargs["stream"] = True

        # Determine HTTP method (POST if params present, otherwise GET)
        method = kwargs.get("method")
        if method is None:
            method = "POST" if params else "GET"

        # Get the stream format and remove it from request_kwargs
        stream_format = kwargs.get("stream_format", "ndjson")
        if "stream_format" in request_kwargs:
            request_kwargs.pop("stream_format")

        try:
            if method.upper() == "GET":
                # For GET, params go in query string
                response = self._session.get(url, **request_kwargs)
            else:
                # For POST and others, params go in request body
                # Remove params from kwargs to avoid duplicating in query string
                query_params = request_kwargs.pop("params", None)

                # Add query params to URL if present
                if query_params:
                    query_string = urllib.parse.urlencode(query_params)
                    url = f"{url}?{query_string}"

                # Convert params to JSON body
                if params:
                    request_kwargs["data"] = self.format_body(params)
                    if "headers" in request_kwargs:
                        request_kwargs["headers"]["Content-Type"] = "application/json"
                    else:
                        request_kwargs["headers"] = {"Content-Type": "application/json"}

                # Remove method and other non-requests params from kwargs
                if "method" in request_kwargs:
                    request_kwargs.pop("method")

                response = self._session.request(method, url, **request_kwargs)

            # Check for errors
            response.raise_for_status()

            # Process the streaming response based on format
            if stream_format == "sse":
                # Server-Sent Events
                client = sseclient.SSEClient(response)
                for event in client.events():
                    # Parse the event data
                    try:
                        yield json.loads(event.data)
                    except Exception:
                        yield event.data

            elif stream_format == "ndjson":
                # Newline-delimited JSON
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode("utf-8")
                        try:
                            yield json.loads(line_str)
                        except Exception:
                            # Yield raw line if parsing fails
                            yield line_str

            else:
                # Raw streaming (yield chunks as they arrive)
                for chunk in response.iter_content(chunk_size=4096):
                    if chunk:
                        yield chunk

        except Timeout:
            raise TransportTimeoutError(f"Streaming request to {url} timed out")
        except ConnectionError as e:
            raise TransportError(f"Connection error: {str(e)}")
        except RequestException as e:
            if hasattr(e, "response") and e.response is not None:
                status_code = e.response.status_code
                error_detail = self._extract_error_detail(e.response)
                raise TransportError(f"HTTP {status_code} error: {error_detail}")
            raise TransportError(f"Streaming request failed: {str(e)}")

    def _build_url(self, endpoint: str, capability: str) -> str:
        """
        Build the full URL for a capability.

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

        # Combine to form the full URL
        return f"{endpoint}/{capability}"

    def _prepare_request_args(
        self,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Prepare arguments for a requests call.

        Args:
            params: Request parameters
            headers: HTTP headers
            timeout: Request timeout in seconds
            **kwargs: Additional request arguments

        Returns:
            Dictionary of request arguments
        """
        # Start with provided kwargs
        request_kwargs = dict(kwargs)

        # Add parameters if present
        if params is not None:
            request_kwargs["params"] = params

        # Add headers if present
        if headers is not None:
            request_kwargs["headers"] = headers

        # Add timeout if specified
        if timeout is not None:
            request_kwargs["timeout"] = timeout

        # Set SSL verification (from instance default, can be overridden)
        if "verify" not in request_kwargs:
            request_kwargs["verify"] = self._verify_ssl

        return request_kwargs

    def _parse_response(self, response: requests.Response) -> Any:
        """
        Parse an HTTP response based on content type.

        Args:
            response: The HTTP response to parse

        Returns:
            Parsed response content
        """
        try:
            content_type = response.headers.get("Content-Type", "")

            if "application/json" in content_type:
                return response.json()
            elif "text/plain" in content_type:
                return response.text
            else:
                # Try JSON first, fall back to text
                try:
                    return response.json()
                except ValueError:
                    return response.text

        except Exception as e:
            logger.warning(f"Error parsing response: {str(e)}")
            return response.text

    def _extract_error_detail(self, response: requests.Response) -> str:
        """
        Extract error details from a response.

        Attempts to parse the response as a RFC7807 problem detail object.

        Args:
            response: The HTTP error response

        Returns:
            Error detail string
        """
        try:
            content_type = response.headers.get("Content-Type", "")

            if "application/problem+json" in content_type:
                problem = response.json()
                return f"{problem.get('title', 'Error')}: {problem.get('detail', '')}"
            elif "application/json" in content_type:
                # Try to get error info from JSON
                data = response.json()
                if "error" in data:
                    if isinstance(data["error"], dict):
                        return f"{data['error'].get('message', 'Unknown error')}"
                    return str(data["error"])
                elif "message" in data:
                    return data["message"]
                else:
                    return "Unknown error"
            else:
                # Return text or default message
                return response.text.strip() or f"HTTP {response.status_code}"

        except Exception:
            # Fall back to default error message
            return f"HTTP {response.status_code} error"
