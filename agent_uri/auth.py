"""
Authentication providers for the agent client SDK.

This module defines authentication providers that can be used to
authenticate requests to agents.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Callable, Dict, Optional

try:
    import jwt  # type: ignore[import]
except ImportError:
    jwt = None  # type: ignore[assignment] # Make JWT optional

from .exceptions import AuthenticationError

logger = logging.getLogger(__name__)


class AuthProvider(ABC):
    """
    Abstract base class for authentication providers.

    Authentication providers are responsible for adding authentication
    information to requests, such as headers or query parameters.
    """

    @abstractmethod
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers to include in requests.

        Returns:
            Dict of headers to add to requests
        """
        pass

    def get_auth_params(self) -> Dict[str, str]:
        """
        Get authentication parameters to include in query strings.

        Returns:
            Dict of parameters to add to requests
        """
        return {}

    @abstractmethod
    def refresh(self) -> None:
        """
        Refresh authentication credentials if needed.

        This method is called before each request if credentials
        are expired or about to expire.
        """
        pass

    @property
    def is_expired(self) -> bool:
        """
        Check if authentication credentials are expired.

        Returns:
            True if credentials are expired, False otherwise
        """
        return False


class BearerTokenAuth(AuthProvider):
    """
    Bearer token authentication provider.

    This provider uses a bearer token for authentication, such as
    an OAuth2 access token or a JWT.
    """

    def __init__(
        self,
        token: str,
        token_type: str = "Bearer",  # nosec B107
        expires_at: Optional[int] = None,
        refresh_callback: Optional[Callable[[], str]] = None,
    ):
        """
        Initialize a bearer token authentication provider.

        Args:
            token: The bearer token
            token_type: The token type, defaults to "Bearer"
            expires_at: Optional Unix timestamp when the token expires
            refresh_callback: Optional callback to refresh the token
        """
        self.token = token
        self.token_type = token_type
        self.expires_at = expires_at
        self.refresh_callback = refresh_callback

        # Try to extract expiration from JWT if not provided
        if expires_at is None and jwt is not None and token:
            try:
                # JWT tokens are often in the format header.payload.signature
                # We can decode the payload without verification to get expiration
                unverified_payload = jwt.decode(
                    token, options={"verify_signature": False}
                )
                if "exp" in unverified_payload:
                    self.expires_at = unverified_payload["exp"]
            except Exception as e:
                # Not a JWT or other error, ignore and continue
                logger.debug(f"Could not extract expiration from token: {e}")

    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get bearer token authentication headers.

        Returns:
            Dict with Authorization header
        """
        return {"Authorization": f"{self.token_type} {self.token}"}

    @property
    def is_expired(self) -> bool:
        """
        Check if token is expired.

        Returns:
            True if token is expired, False otherwise
        """
        if self.expires_at is None:
            return False

        # Consider the token expired 30 seconds before actual expiration
        # to avoid using a token that's about to expire
        buffer_time = 30
        return time.time() > (self.expires_at - buffer_time)

    def refresh(self) -> None:
        """
        Refresh the token if needed and a refresh callback is provided.

        Raises:
            AuthenticationError: If token is expired and can't be refreshed
        """
        if self.is_expired:
            if self.refresh_callback:
                try:
                    new_token_data = self.refresh_callback()
                    if isinstance(new_token_data, dict):
                        self.token = new_token_data.get("access_token", "")
                        self.expires_at = new_token_data.get("expires_at")
                    else:
                        self.token = new_token_data
                except Exception as e:
                    raise AuthenticationError(f"Failed to refresh token: {str(e)}")
            else:
                raise AuthenticationError(
                    "Token is expired and no refresh callback provided"
                )


class ApiKeyAuth(AuthProvider):
    """
    API key authentication provider.

    This provider uses an API key for authentication, either in a header
    or as a query parameter.
    """

    def __init__(
        self,
        api_key: str,
        header_name: str = "X-API-Key",
        param_name: Optional[str] = None,
    ):
        """
        Initialize an API key authentication provider.

        Args:
            api_key: The API key
            header_name: The header name to use, defaults to "X-API-Key"
            param_name: Optional query parameter name to use instead of header
        """
        self.api_key = api_key
        self.header_name = header_name
        self.param_name = param_name

    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get API key authentication headers.

        Returns:
            Dict with API key header if using header authentication
        """
        if self.param_name is None:
            return {self.header_name: self.api_key}
        return {}

    def get_auth_params(self) -> Dict[str, str]:
        """
        Get API key authentication parameters.

        Returns:
            Dict with API key parameter if using parameter authentication
        """
        if self.param_name is not None:
            return {self.param_name: self.api_key}
        return {}

    def refresh(self) -> None:
        """Refresh authentication credentials if needed."""
        pass
