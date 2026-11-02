"""Bearer 访问控制与 fail-closed 行为。"""

from __future__ import annotations

import pytest

from agent import AgentAuth, AgentUnauthorized


def test_auth_is_disabled_by_default() -> None:
    auth = AgentAuth()
    assert auth.enabled is False
    assert auth.user_for(None) is None
    assert auth.user_for("anything") is None


def test_single_token_maps_to_default_user() -> None:
    auth = AgentAuth.from_env({"RETIRENEST_AGENT_TOKEN": "secret"})
    assert auth.enabled is True
    assert auth.user_for("secret") == "default"


def test_token_map_maps_tokens_to_users() -> None:
    auth = AgentAuth.from_env(
        {"RETIRENEST_AGENT_TOKENS": "tok-a:alice, tok-b:bob ,tok-c:"}
    )
    assert auth.user_for("tok-a") == "alice"
    assert auth.user_for("tok-b") == "bob"
    assert auth.user_for("tok-c") == "default"


def test_tokens_env_takes_precedence() -> None:
    auth = AgentAuth.from_env(
        {
            "RETIRENEST_AGENT_TOKENS": "a:alice",
            "RETIRENEST_AGENT_TOKEN": "single",
        }
    )
    assert auth.user_for("a") == "alice"
    with pytest.raises(AgentUnauthorized):
        auth.user_for("single")


def test_missing_or_wrong_token_is_rejected() -> None:
    auth = AgentAuth.from_env({"RETIRENEST_AGENT_TOKEN": "secret"})
    with pytest.raises(AgentUnauthorized):
        auth.user_for(None)
    with pytest.raises(AgentUnauthorized):
        auth.user_for("wrong")


def test_malformed_token_list_fails_closed() -> None:
    auth = AgentAuth.from_env({"RETIRENEST_AGENT_TOKENS": "garbage,also-garbage"})
    assert auth.enabled is True
    assert auth.tokens == {}
    with pytest.raises(AgentUnauthorized):
        auth.user_for("garbage")


def test_blank_env_is_disabled() -> None:
    auth = AgentAuth.from_env(
        {"RETIRENEST_AGENT_TOKEN": "  ", "RETIRENEST_AGENT_TOKENS": " "}
    )
    assert auth.enabled is False


def test_repr_does_not_leak_tokens() -> None:
    auth = AgentAuth.from_env({"RETIRENEST_AGENT_TOKEN": "super-secret"})
    assert "super-secret" not in repr(auth)


def test_unauthorized_error_shape() -> None:
    error = AgentUnauthorized()
    assert error.status == 401
    assert error.code == "AGENT_UNAUTHORIZED"
