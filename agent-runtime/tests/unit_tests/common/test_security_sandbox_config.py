#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""SecuritySandboxSettings unit tests."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from agent_runtime.common.config import SecuritySandboxSettings, Settings


class TestSecuritySandboxSettingsDefaults:
    @staticmethod
    def test_default_values():
        env_vars_to_clear = [
            "SECURITY_SANDBOX_SERVER",
            "SECURITY_SANDBOX_SSL_VERIFY",
            "SECURITY_SANDBOX_IDLE_TTL",
            "SECURITY_SANDBOX_TIMEOUT",
            "SECURITY_SANDBOX_SCOPE",
        ]
        saved = {k: os.environ.pop(k, None) for k in env_vars_to_clear}
        try:
            s = SecuritySandboxSettings(_env_file=None)
            assert s.server == ""
            assert s.ssl_verify is False
            assert s.idle_ttl_seconds == 600
            assert s.timeout_seconds == 900
            assert s.scope == "system"
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v

    @staticmethod
    def test_env_override_server():
        with patch.dict(os.environ, {"SECURITY_SANDBOX_SERVER": "http://xxx:9090"}):
            s = SecuritySandboxSettings()
            assert s.server == "http://xxx:9090"

    @staticmethod
    def test_env_override_ssl_verify():
        with patch.dict(os.environ, {"SECURITY_SANDBOX_SSL_VERIFY": "true"}):
            s = SecuritySandboxSettings()
            assert s.ssl_verify is True

    @staticmethod
    def test_env_override_idle_ttl():
        with patch.dict(os.environ, {"SECURITY_SANDBOX_IDLE_TTL": "1200"}):
            s = SecuritySandboxSettings()
            assert s.idle_ttl_seconds == 1200

    @staticmethod
    def test_env_override_timeout():
        with patch.dict(os.environ, {"SECURITY_SANDBOX_TIMEOUT": "600"}):
            s = SecuritySandboxSettings()
            assert s.timeout_seconds == 600

    @staticmethod
    def test_invalid_timeout_raises():
        with patch.dict(os.environ, {"SECURITY_SANDBOX_TIMEOUT": "abc"}):
            with pytest.raises(ValidationError):
                SecuritySandboxSettings()

    @staticmethod
    def test_scope_session():
        with patch.dict(os.environ, {"SECURITY_SANDBOX_SCOPE": "session"}):
            s = SecuritySandboxSettings()
            assert s.scope == "session"

    @staticmethod
    def test_scope_system():
        with patch.dict(os.environ, {"SECURITY_SANDBOX_SCOPE": "system"}):
            s = SecuritySandboxSettings()
            assert s.scope == "system"


class TestSettingsIntegration:
    @staticmethod
    def test_settings_has_security_sandbox():
        s = Settings()
        assert isinstance(s.security_sandbox, SecuritySandboxSettings)

    @staticmethod
    def test_settings_security_sandbox_defaults():
        env_vars_to_clear = [
            "SECURITY_SANDBOX_SERVER",
            "SECURITY_SANDBOX_SSL_VERIFY",
            "SECURITY_SANDBOX_IDLE_TTL",
            "SECURITY_SANDBOX_TIMEOUT",
            "SECURITY_SANDBOX_SCOPE",
        ]
        saved = {k: os.environ.pop(k, None) for k in env_vars_to_clear}
        try:
            s = SecuritySandboxSettings(_env_file=None)
            assert s.server == ""
            assert s.ssl_verify is False
            assert s.idle_ttl_seconds == 600
            assert s.timeout_seconds == 900
            assert s.scope == "system"
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v
