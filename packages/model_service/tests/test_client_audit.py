# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for StudioModelClient audit helpers (_new_audit / _apply_audit_detail)."""

# pylint: disable=protected-access  # 白盒单测：需直接调用 _new_audit / _apply_audit_detail

import pytest

from model_service.client import StudioModelClient, _ResolveInputs
from model_service.policy import AuditLog
from model_service.resolver import (
    InterfaceProtocol,
    ModelServiceBase,
    ModelServiceDetail,
    ModelStrategy,
    ProviderAuth,
    StrategyType,
)


def _model(mid="m1", name="model-1"):
    return ModelServiceBase(
        id=mid, model_name=name, api_url="http://x/v1", provider_id="prov",
        interface_protocol=InterfaceProtocol.OPENAI, project_id="p",
        workspace_id="w", auth_id="a",
    )


def _detail(mid="m1", name="model-1", auth_id="a1"):
    auth = ProviderAuth(auth_id=auth_id, auth_type="API_KEY", auth_info={"api_key": "k"})
    return ModelServiceDetail(
        model=_model(mid, name), auth=auth, available=True, is_free_model=False,
    )


def _strategy(models):
    return ModelStrategy(type=StrategyType.MODEL, name="s", models=models)


def _inputs():
    return _ResolveInputs(
        model_service_id="ms", auth_id="a", workspace_id="w",
        project_id="p", refresh=False, env_vars={},
    )


class TestNewAudit:
    @staticmethod
    def test_new_audit_non_stream():
        client = StudioModelClient.__new__(StudioModelClient)
        audit = client._new_audit(_strategy([_detail()]), _inputs(), stream=False)
        assert isinstance(audit, AuditLog)
        assert audit.model_id == "m1"
        assert audit.model_name == "model-1"
        assert audit.stream is False
        assert audit.status == "fail"
        assert audit.project_id == "p"
        assert audit.workspace_id == "w"
        assert audit.auth_id == "a1"
        assert audit.provider_id == "prov"

    @staticmethod
    def test_new_audit_stream():
        client = StudioModelClient.__new__(StudioModelClient)
        audit = client._new_audit(_strategy([_detail()]), _inputs(), stream=True)
        assert audit.stream is True

    @staticmethod
    def test_new_audit_auth_none():
        auth = None
        detail = ModelServiceDetail(
            model=_model(), auth=auth, available=False, is_free_model=False,
        )
        client = StudioModelClient.__new__(StudioModelClient)
        audit = client._new_audit(_strategy([detail]), _inputs(), stream=False)
        assert audit.auth_id == ""


class TestApplyAuditDetail:
    @staticmethod
    def test_apply_updates_fields():
        client = StudioModelClient.__new__(StudioModelClient)
        audit = AuditLog(
            model_id="old", model_name="old", api_url="http://old", stream=False,
            status="fail", duration_ms=0, project_id="p", workspace_id="w",
            auth_id="old", provider_id="old",
        )
        client._apply_audit_detail(audit, _detail("m2", "model-2", auth_id="a2"))
        assert audit.model_id == "m2"
        assert audit.model_name == "model-2"
        assert audit.api_url == "http://x/v1"
        assert audit.provider_id == "prov"
        assert audit.auth_id == "a2"

    @staticmethod
    def test_apply_auth_none_keeps_id():
        client = StudioModelClient.__new__(StudioModelClient)
        audit = AuditLog(
            model_id="old", model_name="old", api_url="http://old", stream=False,
            status="fail", duration_ms=0, project_id="p", workspace_id="w",
            auth_id="keep", provider_id="old",
        )
        detail = ModelServiceDetail(
            model=_model("m2", "model-2"), auth=None, available=False, is_free_model=False,
        )
        client._apply_audit_detail(audit, detail)
        # auth 为空时不覆盖 auth_id。
        assert audit.auth_id == "keep"
        assert audit.model_id == "m2"
