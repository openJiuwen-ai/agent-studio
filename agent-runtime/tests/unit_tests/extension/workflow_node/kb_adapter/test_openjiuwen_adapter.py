# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""OpenJiuwenKBAdapter 单元测试 — 检索模式映射、score 过滤、reranker_config 传递。"""

from unittest.mock import AsyncMock, patch

import pytest

from agent_runtime.extension.workflow_node.kb_adapter.openjiuwen_adapter import (
    OpenJiuwenKBAdapter,
)

pytestmark = pytest.mark.asyncio


def _mock_manager(search_results):
    """创建 mock OpenJiuwenKBManager，search 返回指定结果。"""
    mock = AsyncMock()
    mock.search = AsyncMock(return_value=search_results)
    return mock


_VALID_MODEL_CONFIG = {"model_service_id": "svc-1"}


def _get_opts(mock_cls):
    """从 mock search 调用中提取 KBSearchOptions。"""
    return mock_cls.return_value.search.call_args.kwargs["options"]


async def test_search_mode_doc_maps_to_vector():
    """searchMode=doc 映射到 index_type=vector。"""
    adapter = OpenJiuwenKBAdapter()
    mock_results = [{"text": "hello", "score": 0.9, "metadata": {}}]
    with patch(
        "agent_runtime.extension.workflow_node.kb_adapter.openjiuwen_adapter.OpenJiuwenKBManager",
        return_value=_mock_manager(mock_results),
    ) as mock_cls:
        results = await adapter.search(
            query="q",
            connection_config={"model_config": _VALID_MODEL_CONFIG},
            knowledge_bases=[{"external_id": "kb-1"}],
            retrieval_params={"searchMode": "doc", "topK": 5},
        )
        assert _get_opts(mock_cls).index_type == "vector"
        assert len(results) == 1
        assert results[0].text == "hello"


async def test_search_mode_keyword_maps_to_bm25():
    """searchMode=keyword 映射到 index_type=bm25。"""
    adapter = OpenJiuwenKBAdapter()
    with patch(
        "agent_runtime.extension.workflow_node.kb_adapter.openjiuwen_adapter.OpenJiuwenKBManager",
        return_value=_mock_manager([]),
    ) as mock_cls:
        await adapter.search(
            query="q",
            connection_config={"model_config": _VALID_MODEL_CONFIG},
            knowledge_bases=[{"external_id": "kb-1"}],
            retrieval_params={"searchMode": "keyword"},
        )
        assert _get_opts(mock_cls).index_type == "bm25"


async def test_search_mode_mix_maps_to_hybrid():
    """searchMode=mix 映射到 index_type=hybrid。"""
    adapter = OpenJiuwenKBAdapter()
    with patch(
        "agent_runtime.extension.workflow_node.kb_adapter.openjiuwen_adapter.OpenJiuwenKBManager",
        return_value=_mock_manager([]),
    ) as mock_cls:
        await adapter.search(
            query="q",
            connection_config={"model_config": _VALID_MODEL_CONFIG},
            knowledge_bases=[{"external_id": "kb-1"}],
            retrieval_params={"searchMode": "mix"},
        )
        assert _get_opts(mock_cls).index_type == "hybrid"


async def test_search_fallback_to_index_type():
    """searchMode 未传时，fallback 到 retrieval_params 中的 indexType。"""
    adapter = OpenJiuwenKBAdapter()
    with patch(
        "agent_runtime.extension.workflow_node.kb_adapter.openjiuwen_adapter.OpenJiuwenKBManager",
        return_value=_mock_manager([]),
    ) as mock_cls:
        await adapter.search(
            query="q",
            connection_config={"model_config": _VALID_MODEL_CONFIG},
            knowledge_bases=[{"external_id": "kb-1"}],
            retrieval_params={"indexType": "bm25"},
        )
        assert _get_opts(mock_cls).index_type == "bm25"


async def test_search_fallback_to_vector():
    """searchMode 和 indexType 都未传时，fallback 到 vector。"""
    adapter = OpenJiuwenKBAdapter()
    with patch(
        "agent_runtime.extension.workflow_node.kb_adapter.openjiuwen_adapter.OpenJiuwenKBManager",
        return_value=_mock_manager([]),
    ) as mock_cls:
        await adapter.search(
            query="q",
            connection_config={"model_config": _VALID_MODEL_CONFIG},
            knowledge_bases=[{"external_id": "kb-1"}],
            retrieval_params={},
        )
        assert _get_opts(mock_cls).index_type == "vector"


async def test_search_unsupported_index_type_falls_back_to_vector():
    """不支持的 indexType 回退到 vector。"""
    adapter = OpenJiuwenKBAdapter()
    with patch(
        "agent_runtime.extension.workflow_node.kb_adapter.openjiuwen_adapter.OpenJiuwenKBManager",
        return_value=_mock_manager([]),
    ) as mock_cls:
        await adapter.search(
            query="q",
            connection_config={"model_config": _VALID_MODEL_CONFIG},
            knowledge_bases=[{"external_id": "kb-1"}],
            retrieval_params={"indexType": "unknown"},
        )
        assert _get_opts(mock_cls).index_type == "vector"


async def test_search_raises_when_model_config_missing():
    """缺少 model_config 时抛 ValueError。"""
    adapter = OpenJiuwenKBAdapter()
    with pytest.raises(ValueError, match="model_config"):
        await adapter.search(
            query="q",
            connection_config={},
            knowledge_bases=[{"external_id": "kb-1"}],
            retrieval_params={},
        )


async def test_search_raises_when_model_service_id_missing():
    """model_config 缺少 model_service_id 时抛 ValueError。"""
    adapter = OpenJiuwenKBAdapter()
    with pytest.raises(ValueError, match="model_config"):
        await adapter.search(
            query="q",
            connection_config={"model_config": {}},
            knowledge_bases=[{"external_id": "kb-1"}],
            retrieval_params={},
        )


async def test_search_score_threshold_filters_low_scores():
    """score_threshold 过滤低分结果。"""
    adapter = OpenJiuwenKBAdapter()
    mock_results = [
        {"text": "high", "score": 0.9, "metadata": {}},
        {"text": "low", "score": 0.3, "metadata": {}},
    ]
    with patch(
        "agent_runtime.extension.workflow_node.kb_adapter.openjiuwen_adapter.OpenJiuwenKBManager",
        return_value=_mock_manager(mock_results),
    ):
        results = await adapter.search(
            query="q",
            connection_config={"model_config": _VALID_MODEL_CONFIG},
            knowledge_bases=[{"external_id": "kb-1"}],
            retrieval_params={"scoreThreshold": 0.5, "topK": 5},
        )
        assert len(results) == 1
        assert results[0].text == "high"


async def test_search_top_k_limits_results():
    """topK 限制返回结果数量。"""
    adapter = OpenJiuwenKBAdapter()
    mock_results = [
        {"text": "doc1", "score": 0.9, "metadata": {}},
        {"text": "doc2", "score": 0.8, "metadata": {}},
        {"text": "doc3", "score": 0.7, "metadata": {}},
    ]
    with patch(
        "agent_runtime.extension.workflow_node.kb_adapter.openjiuwen_adapter.OpenJiuwenKBManager",
        return_value=_mock_manager(mock_results),
    ):
        results = await adapter.search(
            query="q",
            connection_config={"model_config": _VALID_MODEL_CONFIG},
            knowledge_bases=[{"external_id": "kb-1"}],
            retrieval_params={"topK": 2},
        )
        assert len(results) == 2


async def test_search_passes_reranker_config():
    """reranker_config 从 connection_config 传递到 options.reranker_config。"""
    adapter = OpenJiuwenKBAdapter()
    reranker_cfg = {"model_service_id": "rerank-1"}
    with patch(
        "agent_runtime.extension.workflow_node.kb_adapter.openjiuwen_adapter.OpenJiuwenKBManager",
        return_value=_mock_manager([]),
    ) as mock_cls:
        await adapter.search(
            query="q",
            connection_config={
                "model_config": _VALID_MODEL_CONFIG,
                "reranker_config": reranker_cfg,
            },
            knowledge_bases=[{"external_id": "kb-1"}],
            retrieval_params={},
        )
        assert _get_opts(mock_cls).reranker_config == reranker_cfg


async def test_search_skips_kb_without_id():
    """没有 external_id/knowledge_base_id/id 的 KB 被跳过。"""
    adapter = OpenJiuwenKBAdapter()
    with patch(
        "agent_runtime.extension.workflow_node.kb_adapter.openjiuwen_adapter.OpenJiuwenKBManager",
        return_value=_mock_manager([]),
    ) as mock_cls:
        await adapter.search(
            query="q",
            connection_config={"model_config": _VALID_MODEL_CONFIG},
            knowledge_bases=[{"external_id": ""}, {"external_id": "kb-1"}],
            retrieval_params={},
        )
        assert mock_cls.return_value.search.call_count == 1
        assert mock_cls.return_value.search.call_args.kwargs["kb_id"] == "kb-1"


async def test_search_results_sorted_by_score_desc():
    """结果按 score 降序排列。"""
    adapter = OpenJiuwenKBAdapter()
    mock_results = [
        {"text": "low", "score": 0.3, "metadata": {}},
        {"text": "high", "score": 0.9, "metadata": {}},
        {"text": "mid", "score": 0.6, "metadata": {}},
    ]
    with patch(
        "agent_runtime.extension.workflow_node.kb_adapter.openjiuwen_adapter.OpenJiuwenKBManager",
        return_value=_mock_manager(mock_results),
    ):
        results = await adapter.search(
            query="q",
            connection_config={"model_config": _VALID_MODEL_CONFIG},
            knowledge_bases=[{"external_id": "kb-1"}],
            retrieval_params={"topK": 5},
        )
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)
