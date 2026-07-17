#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""OBSModelConfigProvider / model_service.resolver 集成测试 — 使用本地 modelcase JSON 文件验证解析逻辑"""

import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from agent_runtime.common.model_providers import OBSModelConfigProvider


MODELCASE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "modelcase"
)


def _make_ir_node(model_name: str = "7a2558ae-4fbd-44aa-b9ee-1cb64e03ed69"):
    return {
        "id": "node_llm",
        "type": "jiuwen.LLMComponent",
        "configs": {
            "model": {
                "modelName": model_name,
                "hyperParameters": {
                    "temperature": 0.5,
                    "top_p": 0.5,
                },
                "extension": {},
            },
        },
    }


class TestOBSModelConfigProviderLocal:
    """使用本地 modelcase JSON 文件验证解析逻辑"""

    @staticmethod
    def _run(coro):
        return asyncio.run(coro)

    @staticmethod
    def test_parse_model_service_json():
        """验证 model-service JSON 解析正确"""
        json_path = os.path.join(MODELCASE_DIR, "7a2558ae-4fbd-44aa-b9ee-1cb64e03ed69.json")
        if not os.path.exists(json_path):
            pytest.skip(f"modelcase file not found: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        model_info = data.get("data", data)
        assert model_info["api_url"] == "http://100.102.173.98:8090/v1/chat/completions"
        assert model_info["model_name"] == "MiniMax-M2.7"
        assert model_info["interface_protocol"] == "openai"
        assert model_info["provider_id"] == "58fbdd7f-f5db-4a35-bcbc-3dcd0531ffd0"
        assert model_info["auth_metadata_id"] == "58c28342-0a25-4228-9356-d1fb20a78289"
        assert model_info["project_id"] == "0"

    @staticmethod
    def test_parse_model_auth_json():
        """验证 model-auth JSON 解析正确"""
        json_path = os.path.join(MODELCASE_DIR, "ee4b1d91-8ddb-47ba-bfa1-b9522988b45e.json")
        if not os.path.exists(json_path):
            pytest.skip(f"modelcase file not found: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["auth_type"] == "API_KEY"
        auth_info = json.loads(data["auth_info"])
        assert "API Key" in auth_info
        assert auth_info["API Key"].startswith("ah-")

    def test_full_flow_with_local_files(self):
        """端到端：``resolver.resolve_strategy`` 从 modelcase 读 OBS → 解析出真实 model/auth。

        厚解析已下沉到 ``model_service.resolver``（provider 现为薄配置：
        ``client_provider="studio"`` + extra={model_service_id, auth_id, refresh}）。此处验证
        resolver 而非薄 provider——薄 provider 只塞解析输入，真实 api_base / api_key / model_name
        在此解析。
        """
        from storage import LocalStorageProvider
        from model_service.resolver import StrategyType, resolve_strategy

        modelcase_dir = os.path.abspath(MODELCASE_DIR)
        if not os.path.exists(modelcase_dir):
            pytest.skip(f"modelcase directory not found: {modelcase_dir}")

        class ModelCaseStorageProvider(LocalStorageProvider):
            """Map OBS paths to modelcase/ flat files"""

            _AUTH_FILE_MAP = {
                "58c28342-0a25-4228-9356-d1fb20a78289": "ee4b1d91-8ddb-47ba-bfa1-b9522988b45e.json",
            }

            async def get_content(self, object_key: str) -> str:
                if object_key.startswith("model-service/ir/"):
                    filename = object_key.split("/")[-1]
                elif object_key.startswith("model-auth/auth/"):
                    parts = object_key.split("/")
                    auth_metadata_id = parts[-1].replace(".json", "")
                    filename = self._AUTH_FILE_MAP.get(auth_metadata_id, parts[-1])
                else:
                    filename = object_key

                local_path = os.path.join(modelcase_dir, filename)
                with open(local_path, "r", encoding="utf-8") as f:
                    return f.read()

        # cache miss → 读 OBS（modelcase）；aput no-op
        with patch("jiuwen.serve.controllers.execution.open_utils.cache_model_service_queue") as mock_svc, \
             patch("jiuwen.serve.controllers.execution.open_utils.cache_model_auth_queue") as mock_auth, \
             patch("storage.get_storage_provider", return_value=ModelCaseStorageProvider()):
            mock_svc.aget_with_source = AsyncMock(return_value=(None, ""))
            mock_svc.aput = AsyncMock()
            mock_auth.aget_with_source = AsyncMock(return_value=(None, ""))
            mock_auth.aput = AsyncMock()

            strat = self._run(resolve_strategy(
                "7a2558ae-4fbd-44aa-b9ee-1cb64e03ed69", "0", "w",
                "58c28342-0a25-4228-9356-d1fb20a78289"))

        assert strat.type == StrategyType.MODEL
        d = strat.models[0]
        assert d.model.api_url == "http://100.102.173.98:8090/v1/chat/completions"
        assert d.model.model_name == "MiniMax-M2.7"
        assert d.model.provider_id == "58fbdd7f-f5db-4a35-bcbc-3dcd0531ffd0"
        assert d.auth.auth_type == "API_KEY"
        assert d.auth.auth_info["api_key"].startswith("ah-")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
