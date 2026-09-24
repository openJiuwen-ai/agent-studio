# pylint: disable=protected-access,missing-class-docstring  # 单元测试需直接验证内部方法行为
"""验证知识检索召回阈值 clamp 逻辑：大于 max 取 max，小于 min 取 min。

环境变量 KNOWLEDGE_RECALL_THRESHOLD_MIN / MAX 控制阈值范围，
M 侧和 R 侧各自独立读取但共用同一组环境变量，默认 0~1。
客户可配置为 -10~10，本测试覆盖默认范围和自定义范围两种场景。

过滤职责：适配器（adapter）不做本地分数过滤，所有过滤统一在 flow 层
search_knowledge_repo 中执行。adapter 仅透传阈值给后端 API（如
search_threshold / similarity_threshold）。
"""
from unittest.mock import AsyncMock

import pytest

import agent_runtime.extension.workflow_node.kb_adapter.base as base_module
from agent_runtime.extension.workflow_node.flow_knowledge_retrieval import (
    FlowKnowledgeRetrieval,
)
from agent_runtime.extension.workflow_node.kb_adapter.base import KBSearchResult


pytestmark = pytest.mark.asyncio


# --------------------------------------------------------------------------
# clamp_threshold 纯函数测试（默认 0~1 范围）
# --------------------------------------------------------------------------

def test_clamp_value_within_range_unchanged():
    assert base_module.clamp_threshold(0.5) == 0.5


def test_clamp_value_above_max_clamped_to_max():
    assert base_module.clamp_threshold(1.5) == 1.0


def test_clamp_value_below_min_clamped_to_min():
    assert base_module.clamp_threshold(-0.5) == 0.0


def test_clamp_value_equal_to_max_unchanged():
    assert base_module.clamp_threshold(1.0) == 1.0


def test_clamp_value_equal_to_min_unchanged():
    assert base_module.clamp_threshold(0.0) == 0.0


def test_clamp_extreme_high_value_clamped():
    assert base_module.clamp_threshold(999.0) == 1.0


def test_clamp_extreme_low_value_clamped():
    assert base_module.clamp_threshold(-999.0) == 0.0


# --------------------------------------------------------------------------
# clamp_threshold 自定义范围（模拟 -10~10）
# --------------------------------------------------------------------------


def test_clamp_custom_range_value_within_range_unchanged(monkeypatch):
    monkeypatch.setattr(base_module, "THRESHOLD_MIN", -10.0)
    monkeypatch.setattr(base_module, "THRESHOLD_MAX", 10.0)
    assert base_module.clamp_threshold(5.0) == 5.0


def test_clamp_custom_range_value_above_max_clamped(monkeypatch):
    monkeypatch.setattr(base_module, "THRESHOLD_MIN", -10.0)
    monkeypatch.setattr(base_module, "THRESHOLD_MAX", 10.0)
    assert base_module.clamp_threshold(15.0) == 10.0


def test_clamp_custom_range_value_below_min_clamped(monkeypatch):
    monkeypatch.setattr(base_module, "THRESHOLD_MIN", -10.0)
    monkeypatch.setattr(base_module, "THRESHOLD_MAX", 10.0)
    assert base_module.clamp_threshold(-15.0) == -10.0


def test_clamp_custom_range_negative_value_within_range_unchanged(monkeypatch):
    monkeypatch.setattr(base_module, "THRESHOLD_MIN", -10.0)
    monkeypatch.setattr(base_module, "THRESHOLD_MAX", 10.0)
    assert base_module.clamp_threshold(-5.0) == -5.0


# --------------------------------------------------------------------------
# search_knowledge_repo 集成验证：阈值超出范围时 clamp 后过滤
# --------------------------------------------------------------------------


class _FakeAdapter:
    """记录 search() 收到的参数，并返回预置结果。"""

    def __init__(self, results=None):
        self._results = results or []
        self.calls = []

    async def search(self, query, *, connection_config, knowledge_bases, retrieval_params):
        self.calls.append(
            {
                "query": query,
                "connection_config": connection_config,
                "knowledge_bases": knowledge_bases,
                "retrieval_params": dict(retrieval_params),
            }
        )
        return list(self._results)


def _make_component():
    return FlowKnowledgeRetrieval(
        {"connectionId": "conn-1", "knowledgeBaseIds": ["kb-1"], "retrievalConfig": {}}
    )


async def test_threshold_above_max_clamped_to_max(monkeypatch):
    """recallThreshold=99 超过默认 max=1，clamp 后应为 1.0，只保留 score>=1.0 的结果。"""
    component = _make_component()
    raw = [
        KBSearchResult(text="perfect", score=1.0),
        KBSearchResult(text="good", score=0.8),
        KBSearchResult(text="low", score=0.3),
    ]
    monkeypatch.setattr(component, "_search_with_faq_fallback", AsyncMock(return_value=raw))

    results = await component.search_knowledge_repo(
        adapter=_FakeAdapter(),
        query="q",
        connection_config={"connector_type": "LakeSearch"},
        knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ext-1"}],
        retrieval_params={"recallThreshold": 99.0, "topK": 10},
    )

    assert len(results) == 1
    assert results[0].score == 1.0


async def test_threshold_below_min_clamped_and_filters(monkeypatch):
    """recallThreshold=-99 低于默认 min=0，clamp 后为 0.0，执行 score>=0 过滤。"""
    component = _make_component()
    raw = [
        KBSearchResult(text="a", score=0.9),
        KBSearchResult(text="b", score=0.1),
        KBSearchResult(text="neg", score=-0.5),
    ]
    monkeypatch.setattr(component, "_search_with_faq_fallback", AsyncMock(return_value=raw))

    results = await component.search_knowledge_repo(
        adapter=_FakeAdapter(),
        query="q",
        connection_config={"connector_type": "LakeSearch"},
        knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ext-1"}],
        retrieval_params={"recallThreshold": -99.0, "topK": 10},
    )

    # clamp 到 min=0，过滤掉 score<0 的结果
    assert len(results) == 2
    assert all(r.score >= 0.0 for r in results)


async def test_threshold_clamped_to_min_still_filters(monkeypatch):
    """recallThreshold clamp 后等于 min，仍然执行过滤（score >= min）。"""
    component = _make_component()
    raw = [
        KBSearchResult(text="a", score=0.0),
        KBSearchResult(text="b", score=0.5),
        KBSearchResult(text="neg", score=-1.0),
    ]
    monkeypatch.setattr(component, "_search_with_faq_fallback", AsyncMock(return_value=raw))

    results = await component.search_knowledge_repo(
        adapter=_FakeAdapter(),
        query="q",
        connection_config={"connector_type": "LakeSearch"},
        knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ext-1"}],
        retrieval_params={"recallThreshold": -5.0, "topK": 10},  # clamp 到 0
    )

    # 显式传入了阈值，clamp 到 0 后仍执行 score >= 0 过滤，负分结果被丢弃
    assert len(results) == 2
    assert all(r.score >= 0.0 for r in results)


async def test_no_threshold_no_filtering(monkeypatch):
    """未传入 recallThreshold/scoreThreshold 时，不过滤任何结果。"""
    component = _make_component()
    raw = [
        KBSearchResult(text="a", score=0.9),
        KBSearchResult(text="b", score=-0.5),
    ]
    monkeypatch.setattr(component, "_search_with_faq_fallback", AsyncMock(return_value=raw))

    results = await component.search_knowledge_repo(
        adapter=_FakeAdapter(),
        query="q",
        connection_config={"connector_type": "LakeSearch"},
        knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ext-1"}],
        retrieval_params={"topK": 10},  # 不含 recallThreshold / scoreThreshold
    )

    # 未传入阈值 → 不过滤，负分结果保留
    assert len(results) == 2


async def test_custom_range_threshold_above_max_clamped(monkeypatch):
    """自定义范围 -10~10，recallThreshold=15 clamp 到 10，只保留 score>=10 的结果。"""
    monkeypatch.setattr(base_module, "THRESHOLD_MIN", -10.0)
    monkeypatch.setattr(base_module, "THRESHOLD_MAX", 10.0)

    component = _make_component()
    raw = [
        KBSearchResult(text="perfect", score=10.0),
        KBSearchResult(text="good", score=5.0),
        KBSearchResult(text="low", score=-5.0),
    ]
    monkeypatch.setattr(component, "_search_with_faq_fallback", AsyncMock(return_value=raw))

    results = await component.search_knowledge_repo(
        adapter=_FakeAdapter(),
        query="q",
        connection_config={"connector_type": "LakeSearch"},
        knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ext-1"}],
        retrieval_params={"recallThreshold": 15.0, "topK": 10},
    )

    assert len(results) == 1
    assert results[0].score == 10.0


async def test_custom_range_threshold_below_min_clamped(monkeypatch):
    """自定义范围 -10~10，recallThreshold=-20 clamp 到 -10，保留 score>=-10 的结果。"""
    monkeypatch.setattr(base_module, "THRESHOLD_MIN", -10.0)
    monkeypatch.setattr(base_module, "THRESHOLD_MAX", 10.0)

    component = _make_component()
    raw = [
        KBSearchResult(text="a", score=5.0),
        KBSearchResult(text="b", score=-5.0),
    ]
    monkeypatch.setattr(component, "_search_with_faq_fallback", AsyncMock(return_value=raw))

    results = await component.search_knowledge_repo(
        adapter=_FakeAdapter(),
        query="q",
        connection_config={"connector_type": "LakeSearch"},
        knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ext-1"}],
        retrieval_params={"recallThreshold": -20.0, "topK": 10},
    )

    # clamp 到 -10，所有 score>=-10 保留
    assert len(results) == 2


async def test_custom_range_no_threshold_negative_score_preserved(monkeypatch):
    """自定义范围 -10~10，未传入阈值时负分结果不被丢弃。"""
    monkeypatch.setattr(base_module, "THRESHOLD_MIN", -10.0)
    monkeypatch.setattr(base_module, "THRESHOLD_MAX", 10.0)

    component = _make_component()
    raw = [
        KBSearchResult(text="a", score=5.0),
        KBSearchResult(text="b", score=-5.0),
    ]
    monkeypatch.setattr(component, "_search_with_faq_fallback", AsyncMock(return_value=raw))

    results = await component.search_knowledge_repo(
        adapter=_FakeAdapter(),
        query="q",
        connection_config={"connector_type": "LakeSearch"},
        knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ext-1"}],
        retrieval_params={"topK": 10},  # 不含阈值
    )

    # 未传入阈值 → 不过滤，负分结果保留
    assert len(results) == 2


async def test_score_threshold_zero_does_not_filter_negative_scores(monkeypatch):
    """adapter 不做本地过滤，score>=0 过滤统一由 flow 层执行。"""
    component = _make_component()
    raw = [
        KBSearchResult(text="a", score=0.9),
        KBSearchResult(text="b", score=-0.5),
    ]
    monkeypatch.setattr(component, "_search_with_faq_fallback", AsyncMock(return_value=raw))

    results = await component.search_knowledge_repo(
        adapter=_FakeAdapter(),
        query="q",
        connection_config={"connector_type": "LakeSearch"},
        knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ext-1"}],
        retrieval_params={"recallThreshold": 0.0, "scoreThreshold": 0.0, "topK": 10},
    )

    # flow 层 clamp(0)=0，执行 score>=0 过滤，负分结果被丢弃
    assert len(results) == 1
    assert results[0].score >= 0.0
