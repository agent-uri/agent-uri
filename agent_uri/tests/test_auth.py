"""
Tests for the authentication module.
"""

import base64
import json
import time
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from ..auth import (
    ApiKeyAuth,
    AuthProvider,
    BearerTokenAuth,
    JWSDescriptorVerifier,
    MessageSignatureVerifier,
    MutualTLSAuth,
    OAuthASMetadata,
    ProtectedResourceMetadata,
    TokenExchangeClient,
    _verify_scope_narrowing,
    jcs_canonicalize,
)
from ..exceptions import (
    AuthenticationError,
    DelegationError,
    KeyDiscoveryError,
    ScopeNarrowingViolationError,
    SignatureVerificationError,
)


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


class TestMutualTLSAuth:
    def test_no_headers_no_params(self, tmp_path):
        cert = tmp_path / "cert.pem"
        cert.write_text("")
        auth = MutualTLSAuth(cert_path=str(cert))
        assert auth.get_auth_headers() == {}
        assert auth.get_auth_params() == {}

    def test_refresh_is_noop(self, tmp_path):
        cert = tmp_path / "cert.pem"
        cert.write_text("")
        MutualTLSAuth(cert_path=str(cert)).refresh()  # no-op


class TestScopeNarrowing:
    def test_inner_subset_of_outer_ok(self):
        _verify_scope_narrowing("read write admin", "read write")

    def test_inner_empty_inherits(self):
        _verify_scope_narrowing("read", None)
        _verify_scope_narrowing("read", "")

    def test_outer_empty_allows_anything(self):
        # Spec: empty outer scope is treated as unconstrained.
        _verify_scope_narrowing(None, "read write")

    def test_inner_widens_raises(self):
        with pytest.raises(ScopeNarrowingViolationError):
            _verify_scope_narrowing("read", "read write")


# --------------------------------------------------------------------------
# OAuth metadata fetchers
# --------------------------------------------------------------------------


def _mock_response(json_data, status=200):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status
    resp.json = Mock(return_value=json_data)
    resp.raise_for_status = Mock()
    if status >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError("fail")
    return resp


class TestOAuthASMetadata:
    def test_fetch_caches(self):
        md = OAuthASMetadata(ttl_seconds=60)
        data = {
            "issuer": "https://issuer.example.com",
            "token_endpoint": "https://issuer.example.com/token",
            "jwks_uri": "https://issuer.example.com/jwks",
        }
        with patch(
            "agent_uri.auth.requests.get", return_value=_mock_response(data)
        ) as m:
            first = md.fetch("https://issuer.example.com")
            second = md.fetch("https://issuer.example.com")
        assert first == data
        assert second == data
        assert m.call_count == 1  # second call served from cache

    def test_token_endpoint(self):
        md = OAuthASMetadata()
        data = {"token_endpoint": "https://x.example.com/token"}
        with patch("agent_uri.auth.requests.get", return_value=_mock_response(data)):
            assert md.token_endpoint("https://x.example.com") == (
                "https://x.example.com/token"
            )

    def test_token_endpoint_missing_raises(self):
        md = OAuthASMetadata()
        with patch("agent_uri.auth.requests.get", return_value=_mock_response({})):
            with pytest.raises(KeyDiscoveryError):
                md.token_endpoint("https://x.example.com")

    def test_fetch_network_error(self):
        md = OAuthASMetadata()
        with patch(
            "agent_uri.auth.requests.get",
            side_effect=requests.ConnectionError("down"),
        ):
            with pytest.raises(KeyDiscoveryError):
                md.fetch("https://x.example.com")

    def test_jwks_uri_optional(self):
        md = OAuthASMetadata()
        with patch(
            "agent_uri.auth.requests.get",
            return_value=_mock_response({"token_endpoint": "https://x/token"}),
        ):
            assert md.jwks_uri("https://x.example.com") is None


class TestProtectedResourceMetadata:
    def test_fetch(self):
        prm = ProtectedResourceMetadata()
        data = {
            "resource": "https://api.example.com",
            "authorization_servers": ["https://issuer.example.com"],
        }
        with patch("agent_uri.auth.requests.get", return_value=_mock_response(data)):
            assert prm.fetch("https://api.example.com") == data


# --------------------------------------------------------------------------
# RFC 8693 Token Exchange
# --------------------------------------------------------------------------


class TestTokenExchangeClient:
    def test_build_act_claim(self):
        act = TokenExchangeClient.build_act_claim(
            "actor-sub", issuer="https://issuer.example.com"
        )
        assert act["sub"] == "actor-sub"
        assert act["iss"] == "https://issuer.example.com"
        assert "act" not in act

    def test_build_nested_act(self):
        inner = TokenExchangeClient.build_act_claim("a")
        outer = TokenExchangeClient.build_act_claim("b", inner_act=inner)
        assert outer["act"] == inner

    def test_verify_delegation_chain_ok(self):
        chain = [{"scope": "read write"}, {"scope": "read"}, {"scope": "read"}]
        TokenExchangeClient.verify_delegation_chain(chain)  # no raise

    def test_verify_delegation_chain_widens(self):
        chain = [{"scope": "read"}, {"scope": "read admin"}]
        with pytest.raises(ScopeNarrowingViolationError):
            TokenExchangeClient.verify_delegation_chain(chain)

    def test_exchange_rejects_widening_scope(self):
        client = TokenExchangeClient()
        with pytest.raises(ScopeNarrowingViolationError):
            client.exchange(
                issuer="https://issuer.example.com",
                subject_token="abc",
                requested_scope="read admin",
                current_scope="read",
            )

    def test_exchange_success(self):
        md = MagicMock(spec=OAuthASMetadata)
        md.token_endpoint.return_value = "https://issuer.example.com/token"
        client = TokenExchangeClient(metadata=md)

        response = MagicMock()
        response.status_code = 200
        response.json = Mock(return_value={"access_token": "xyz", "expires_in": 3600})
        with patch("agent_uri.auth.requests.post", return_value=response) as m:
            result = client.exchange(
                issuer="https://issuer.example.com",
                subject_token="abc",
                requested_scope="read",
                current_scope="read write",
                audience="https://resource.example.com",
                actor_token="actor",
            )
        assert result == {"access_token": "xyz", "expires_in": 3600}
        sent = m.call_args.kwargs["data"]
        assert sent["grant_type"].endswith("token-exchange")
        assert sent["scope"] == "read"
        assert sent["audience"] == "https://resource.example.com"
        assert sent["actor_token"] == "actor"

    def test_exchange_http_error_becomes_delegation_error(self):
        md = MagicMock(spec=OAuthASMetadata)
        md.token_endpoint.return_value = "https://issuer.example.com/token"
        client = TokenExchangeClient(metadata=md)

        response = MagicMock()
        response.status_code = 403
        response.text = "forbidden"
        with patch("agent_uri.auth.requests.post", return_value=response):
            with pytest.raises(DelegationError):
                client.exchange(
                    issuer="https://issuer.example.com",
                    subject_token="abc",
                )

    def test_exchange_network_error(self):
        md = MagicMock(spec=OAuthASMetadata)
        md.token_endpoint.return_value = "https://issuer.example.com/token"
        client = TokenExchangeClient(metadata=md)
        with patch(
            "agent_uri.auth.requests.post",
            side_effect=requests.ConnectionError("down"),
        ):
            with pytest.raises(DelegationError):
                client.exchange(
                    issuer="https://issuer.example.com",
                    subject_token="abc",
                )


# --------------------------------------------------------------------------
# RFC 9421 HTTP Message Signatures
# --------------------------------------------------------------------------


def _gen_ed25519_keypair():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    private = ed25519.Ed25519PrivateKey.generate()
    public = private.public_key()
    public_pem = public.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private, public_pem


def _sign_and_build_headers(
    private_key,
    *,
    method: str,
    target_uri: str,
    keyid: str = "key-1",
    covered_headers: dict | None = None,
    created: int | None = None,
    alg: str = "ed25519",
    label: str = "sig1",
):
    """Produce matching Signature-Input / Signature headers using our own base."""
    created = created if created is not None else int(time.time())
    covered_headers = covered_headers or {}

    params = {"created": created, "keyid": keyid, "alg": alg}
    covered = ["@method", "@target-uri", *[k.lower() for k in covered_headers.keys()]]

    # Reuse the verifier's base builder so we stay in lockstep.
    base = MessageSignatureVerifier(lambda _k: b"")._build_signature_base(
        method=method,
        target_uri=target_uri,
        headers=covered_headers,
        covered=covered,
        params_raw=MessageSignatureVerifier._serialize_params(params),
    )
    signature = private_key.sign(base.encode("utf-8"))
    covered_quoted = " ".join('"{}"'.format(c) for c in covered)
    sig_input = (
        f"{label}=({covered_quoted});"
        f"{MessageSignatureVerifier._serialize_params(params)}"
    )
    sig_header = f"{label}=:{base64.b64encode(signature).decode()}:"
    return {
        **covered_headers,
        "Signature-Input": sig_input,
        "Signature": sig_header,
    }


class TestMessageSignatureVerifier:
    def test_verify_valid_signature(self):
        private, public_pem = _gen_ed25519_keypair()
        verifier = MessageSignatureVerifier(lambda keyid: public_pem)
        headers = _sign_and_build_headers(
            private,
            method="POST",
            target_uri="https://example.com/echo",
            covered_headers={"content-type": "application/json"},
        )
        result = verifier.verify(
            method="POST",
            target_uri="https://example.com/echo",
            headers=headers,
        )
        assert result["keyid"] == "key-1"
        assert result["alg"] == "ed25519"

    def test_verify_fails_on_tampered_body_header(self):
        private, public_pem = _gen_ed25519_keypair()
        verifier = MessageSignatureVerifier(lambda keyid: public_pem)
        headers = _sign_and_build_headers(
            private,
            method="POST",
            target_uri="https://example.com/echo",
            covered_headers={"content-type": "application/json"},
        )
        # Mutate a covered header after signing.
        headers["content-type"] = "text/plain"
        with pytest.raises(SignatureVerificationError):
            verifier.verify(
                method="POST",
                target_uri="https://example.com/echo",
                headers=headers,
            )

    def test_missing_headers(self):
        verifier = MessageSignatureVerifier(lambda k: b"")
        with pytest.raises(SignatureVerificationError):
            verifier.verify(method="POST", target_uri="/", headers={})

    def test_alg_not_in_allowlist(self):
        private, public_pem = _gen_ed25519_keypair()
        verifier = MessageSignatureVerifier(
            lambda k: public_pem, allowed_algs=["ecdsa-p256-sha256"]
        )
        headers = _sign_and_build_headers(
            private,
            method="GET",
            target_uri="https://example.com/",
            alg="ed25519",
        )
        with pytest.raises(SignatureVerificationError, match="not in allowlist"):
            verifier.verify(
                method="GET",
                target_uri="https://example.com/",
                headers=headers,
            )

    def test_expired_signature(self):
        private, public_pem = _gen_ed25519_keypair()
        verifier = MessageSignatureVerifier(lambda k: public_pem, max_age_seconds=60)
        old = int(time.time()) - 600
        # Manually build an "expires" param in the past.
        label = "sig1"
        params = {
            "created": old,
            "expires": old + 10,
            "keyid": "k",
            "alg": "ed25519",
        }
        covered = ["@method", "@target-uri"]
        base = verifier._build_signature_base(
            method="GET",
            target_uri="https://example.com/",
            headers={},
            covered=covered,
            params_raw=verifier._serialize_params(params),
        )
        sig = private.sign(base.encode("utf-8"))
        covered_quoted = " ".join('"{}"'.format(c) for c in covered)
        headers = {
            "Signature-Input": (
                f"{label}=({covered_quoted});" f"{verifier._serialize_params(params)}"
            ),
            "Signature": f"{label}=:{base64.b64encode(sig).decode()}:",
        }
        with pytest.raises(SignatureVerificationError, match="expired"):
            verifier.verify(
                method="GET", target_uri="https://example.com/", headers=headers
            )

    def test_missing_keyid(self):
        private, public_pem = _gen_ed25519_keypair()
        verifier = MessageSignatureVerifier(lambda k: public_pem)
        label = "sig1"
        params = {"created": int(time.time()), "alg": "ed25519"}
        covered = ["@method", "@target-uri"]
        base = verifier._build_signature_base(
            method="GET",
            target_uri="https://example.com/",
            headers={},
            covered=covered,
            params_raw=verifier._serialize_params(params),
        )
        sig = private.sign(base.encode("utf-8"))
        covered_quoted = " ".join('"{}"'.format(c) for c in covered)
        headers = {
            "Signature-Input": (
                f"{label}=({covered_quoted});" f"{verifier._serialize_params(params)}"
            ),
            "Signature": f"{label}=:{base64.b64encode(sig).decode()}:",
        }
        with pytest.raises(SignatureVerificationError, match="keyid"):
            verifier.verify(
                method="GET", target_uri="https://example.com/", headers=headers
            )

    def test_unsupported_derived_component(self):
        private, _public = _gen_ed25519_keypair()
        verifier = MessageSignatureVerifier(lambda k: b"")
        # Directly invoke the base builder to exercise the guard.
        with pytest.raises(SignatureVerificationError):
            verifier._build_signature_base(
                method="GET",
                target_uri="https://x/",
                headers={},
                covered=["@authority"],
                params_raw="",
            )


class TestContentDigest:
    def test_sha256_match(self):
        import hashlib

        body = b'{"msg":"hi"}'
        digest = base64.b64encode(hashlib.sha256(body).digest()).decode()
        MessageSignatureVerifier.verify_content_digest(body, f"sha-256=:{digest}:")

    def test_sha512_match(self):
        import hashlib

        body = b"hello"
        digest = base64.b64encode(hashlib.sha512(body).digest()).decode()
        MessageSignatureVerifier.verify_content_digest(body, f"sha-512=:{digest}:")

    def test_mismatch_raises(self):
        import hashlib

        body = b"hello"
        digest = base64.b64encode(hashlib.sha256(b"other").digest()).decode()
        with pytest.raises(SignatureVerificationError):
            MessageSignatureVerifier.verify_content_digest(body, f"sha-256=:{digest}:")

    def test_missing_header(self):
        with pytest.raises(SignatureVerificationError):
            MessageSignatureVerifier.verify_content_digest(b"hi", "")

    def test_unsupported_algo(self):
        with pytest.raises(SignatureVerificationError):
            MessageSignatureVerifier.verify_content_digest(b"hi", "blake2=:aaaa:")


# --------------------------------------------------------------------------
# JCS + JWS descriptor signing
# --------------------------------------------------------------------------


class TestJCSCanonicalization:
    def test_sorts_keys_and_compacts(self):
        obj = {"b": 2, "a": 1, "nested": {"y": 1, "x": 2}}
        canon = jcs_canonicalize(obj).decode()
        assert canon == '{"a":1,"b":2,"nested":{"x":2,"y":1}}'


class TestJWSDescriptorVerifier:
    def test_requires_kid(self):
        import jwt as pyjwt
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ed25519

        key = ed25519.Ed25519PrivateKey.generate()
        priv_pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        # Build a JWS without kid — verification should fail.
        token = pyjwt.encode({"x": 1}, priv_pem, algorithm="EdDSA")
        head, _payload, sig = token.split(".")
        detached = f"{head}..{sig}"
        verifier = JWSDescriptorVerifier(lambda k: b"")
        with pytest.raises(SignatureVerificationError):
            verifier.verify({"x": 1}, detached)
