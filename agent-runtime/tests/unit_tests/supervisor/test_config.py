"""Regression tests for conversation supervisor model configuration."""

import model_service  # noqa: F401  -- register the ``studio`` model provider

from agent_runtime.common.config import settings
from agent_runtime.supervisor.config import build_react_config


def test_build_react_config_propagates_llm_ssl_verification(monkeypatch):
    """The supervisor must not fall back to the SDK's verify_ssl=True default."""
    monkeypatch.setattr(settings.llm, "ssl_verify", False)

    config = build_react_config("You are a supervisor.", "deployment-1")

    assert config.model_client_config.verify_ssl is False
