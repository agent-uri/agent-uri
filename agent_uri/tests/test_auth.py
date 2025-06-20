"""
Tests for the authentication module.
"""

import time
from unittest.mock import Mock

import pytest

from ..auth import ApiKeyAuth, AuthProvider, BearerTokenAuth
from ..exceptions import AuthenticationError


class TestAuthProvider:
    """Tests for the abstract AuthProvider class."""

    def test_base_methods(self):
        """Test the default implementations of base methods."""

        # Create a concrete implementation for testing
        class TestAuth(AuthProvider):
            def get_auth_headers(self):
                return {"Auth": "Test"}

            def refresh(self):
                pass

        auth = TestAuth()

        # Default implementations
        assert auth.get_auth_params() == {}
        assert auth.is_expired is False

        # No error should be raised
        auth.refresh()


class TestBearerTokenAuth:
    """Tests for the BearerTokenAuth provider."""

    def test_initialization(self):
        """Test basic initialization."""
        auth = BearerTokenAuth(token="test-token")

        assert auth.token == "test-token"
        assert auth.token_type == "Bearer"
        assert auth.expires_at is None
        assert auth.refresh_callback is None

    def test_get_auth_headers(self):
        """Test that auth headers are correctly generated."""
        auth1 = BearerTokenAuth(token="test-token")
        assert auth1.get_auth_headers() == {"Authorization": "Bearer test-token"}

        auth2 = BearerTokenAuth(token="test-token", token_type="Custom")
        assert auth2.get_auth_headers() == {"Authorization": "Custom test-token"}

    def test_is_expired(self):
        """Test expiration checking."""
        # Token without expiration
        auth1 = BearerTokenAuth(token="test-token")
        assert auth1.is_expired is False

        # Token that is not expired
        future_time = int(time.time()) + 3600  # 1 hour in the future
        auth2 = BearerTokenAuth(token="test-token", expires_at=future_time)
        assert auth2.is_expired is False

        # Token that is expired
        past_time = int(time.time()) - 3600  # 1 hour in the past
        auth3 = BearerTokenAuth(token="test-token", expires_at=past_time)
        assert auth3.is_expired is True

    def test_refresh(self):
        """Test token refresh mechanism."""
        # Token without refresh callback
        auth1 = BearerTokenAuth(token="test-token", expires_at=0)
        with pytest.raises(AuthenticationError):
            auth1.refresh()

        # Token with refresh callback
        mock_callback = Mock(return_value="new-token")
        auth2 = BearerTokenAuth(
            token="test-token", expires_at=0, refresh_callback=mock_callback
        )
        auth2.refresh()
        assert mock_callback.called
        assert auth2.token == "new-token"

        # Token with refresh callback returning dict
        mock_callback = Mock(
            return_value={"access_token": "new-token-from-dict", "expires_at": 12345}
        )
        auth3 = BearerTokenAuth(
            token="test-token", expires_at=0, refresh_callback=mock_callback
        )
        auth3.refresh()
        assert mock_callback.called
        assert auth3.token == "new-token-from-dict"
        assert auth3.expires_at == 12345

        # Token with refresh callback that raises exception
        mock_callback = Mock(side_effect=ValueError("Refresh failed"))
        auth4 = BearerTokenAuth(
            token="test-token", expires_at=0, refresh_callback=mock_callback
        )
        with pytest.raises(AuthenticationError):
            auth4.refresh()


class TestApiKeyAuth:
    """Tests for the ApiKeyAuth provider."""

    def test_initialization(self):
        """Test basic initialization."""
        auth = ApiKeyAuth(api_key="test-api-key")

        assert auth.api_key == "test-api-key"
        assert auth.header_name == "X-API-Key"
        assert auth.param_name is None

    def test_get_auth_headers(self):
        """Test that auth headers are correctly generated."""
        # Default header name
        auth1 = ApiKeyAuth(api_key="test-api-key")
        assert auth1.get_auth_headers() == {"X-API-Key": "test-api-key"}

        # Custom header name
        auth2 = ApiKeyAuth(api_key="test-api-key", header_name="API-Key")
        assert auth2.get_auth_headers() == {"API-Key": "test-api-key"}

        # When using param, no headers should be returned
        auth3 = ApiKeyAuth(api_key="test-api-key", param_name="api_key")
        assert auth3.get_auth_headers() == {}

    def test_get_auth_params(self):
        """Test that auth parameters are correctly generated."""
        # When using header, no params should be returned
        auth1 = ApiKeyAuth(api_key="test-api-key")
        assert auth1.get_auth_params() == {}

        # When using param
        auth2 = ApiKeyAuth(api_key="test-api-key", param_name="api_key")
        assert auth2.get_auth_params() == {"api_key": "test-api-key"}
