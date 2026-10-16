# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for StudioModelClient._resolve_inputs (config / headers / env_vars 归一)."""

# pylint: disable=protected-access  # 白盒单测：需直接调用 _resolve_inputs

import pytest

from model_service.client import StudioModelClient
from model_service.ports import (
    set_env_variables,
    set_request_headers,
)


class _FakeConfig:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestResolveInputs:
    @staticmethod
    def test_defaults(reset_model_service_ports, reset_common_utils_state):
        client = StudioModelClient.__new__(StudioModelClient)
        client.model_client_config = _FakeConfig()
        set_request_headers(lambda: {})
        set_env_variables(lambda: {})

        inputs = client._resolve_inputs()
        assert inputs.model_service_id == ""
        assert inputs.auth_id == ""
        assert inputs.refresh is False
        assert inputs.project_id == "0"
        assert inputs.workspace_id == ""
        assert inputs.env_vars == {}

    @staticmethod
    def test_extracts_from_config(reset_model_service_ports, reset_common_utils_state):
        client = StudioModelClient.__new__(StudioModelClient)
        client.model_client_config = _FakeConfig(
            model_service_id="ms-1", auth_id="a-1", refresh=True,
        )
        set_request_headers(lambda: {})
        set_env_variables(lambda: {})

        inputs = client._resolve_inputs()
        assert inputs.model_service_id == "ms-1"
        assert inputs.auth_id == "a-1"
        assert inputs.refresh is True

    @staticmethod
    def test_extracts_project_and_workspace(reset_model_service_ports, reset_common_utils_state):
        client = StudioModelClient.__new__(StudioModelClient)
        client.model_client_config = _FakeConfig()
        set_request_headers(lambda: {
            "X-Owner-Project-Id": "proj-9",
            "X-Workspace-Id": "ws-9",
        })
        set_env_variables(lambda: {})

        inputs = client._resolve_inputs()
        assert inputs.project_id == "proj-9"
        assert inputs.workspace_id == "ws-9"

    @staticmethod
    def test_workspace_lowercase_header(reset_model_service_ports, reset_common_utils_state):
        client = StudioModelClient.__new__(StudioModelClient)
        client.model_client_config = _FakeConfig()
        set_request_headers(lambda: {"x-workspace-id": "ws-low"})
        set_env_variables(lambda: {})

        inputs = client._resolve_inputs()
        assert inputs.workspace_id == "ws-low"

    @staticmethod
    def test_headers_none(reset_model_service_ports, reset_common_utils_state):
        client = StudioModelClient.__new__(StudioModelClient)
        client.model_client_config = _FakeConfig()
        set_request_headers(lambda: None)
        set_env_variables(lambda: {})

        inputs = client._resolve_inputs()
        assert inputs.project_id == "0"
        assert inputs.workspace_id == ""

    @staticmethod
    def test_env_variables_passthrough(reset_model_service_ports, reset_common_utils_state):
        client = StudioModelClient.__new__(StudioModelClient)
        client.model_client_config = _FakeConfig()
        set_request_headers(lambda: {})
        set_env_variables(lambda: {"plugin_url_params": {"A": "1"}})

        inputs = client._resolve_inputs()
        assert inputs.env_vars == {"plugin_url_params": {"A": "1"}}

    @staticmethod
    def test_refresh_false_string(reset_model_service_ports, reset_common_utils_state):
        client = StudioModelClient.__new__(StudioModelClient)
        client.model_client_config = _FakeConfig(refresh=False)
        set_request_headers(lambda: {})
        set_env_variables(lambda: {})

        assert client._resolve_inputs().refresh is False
