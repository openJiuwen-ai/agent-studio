# pylint: disable=protected-access  # 单元测试需直接验证内部方法行为
"""验证知识检索召回阈值 clamp 逻辑：大于 max 取 max，小于 min 取 min。

环境变量 KNOWLEDGE_RECALL_THRESHOLD_MIN / MAX 控制阈值范围，
M 侧和 R 侧各自独立读取但共用同一组环境变量，默认 0~1。
客户可配置为 -10~10，本测试覆盖默认范围和自定义范围两种场景。
"""
from unittest.mock import AsyncMock

import pytest

import agent_runtime.extension.workflow_node.kb_adapter.base as base_module
import agent_runtime.extension.workflow_node.flow_knowledge_retrieval as fkr_module
from agent_runtime.extension.workflow_node.flow_knowledge_retrieval import (
    FlowKnowledgeRetrieval,
)
from agent_runtime.extension.workflow_node.kb_adapter.base import KBSearchResult


pytestmark = pytest.mark.asyncio


# --------------------------------------------------------------------------
# clamp_threshold 纯函数测试（默认 0~1 范围）
# --------------------------------------------------------------------------

class TestClampThresholdDefault:
    """默认范围 0~1 下的 clamp 行为。"""

    def test_value_within_range_unchanged(self):
        assert base_module.clamp_threshold(0.5) == 0.5

    def test_value_above_max_clamped_to_max(self):
        assert base_module.clamp_threshold(1.5) == 1.0

    def test_value_below_min_clamped_to_min(self):
        assert base_module.clamp_threshold(-0.5) == 0.0

    def test_value_equal_to_max_unchanged(self):
        assert base_module.clamp_threshold(1.0) == 1.0

    def test_value_equal_to_min_unchanged(self):
        assert base_module.clamp_threshold(0.0) == 0.0

    def test_extreme_high_value_clamped(self):
        assert base_module.clamp_threshold(999.0) == 1.0

    def test_extreme_low_value_clamped(self):
        assert base_module.clamp_threshold(-999.0) == 0.0


# --------------------------------------------------------------------------
# clamp_threshold 自定义范围（模拟 -10~10）
# --------------------------------------------------------------------------

class TestClampThresholdCustomRange:
    """模拟客户配置 KNOWLEDGE_RECALL_THRESHOLD_MIN=-10 / MAX=10 的场景。"""

    def test_value_within_custom_range_unchanged(self, monkeypatch):
        monkeypatch.setattr(base_module, "THRESHOLD_MIN", -10.0)
        monkeypatch.setattr(base_module, "THRESHOLD_MAX", 10.0)
        assert base_module.clamp_threshold(5.0) == 5.0

    def test_value_above_custom_max_clamped(self, monkeypatch):
        monkeypatch.setattr(base_module, "THRESHOLD_MIN", -10.0)
        monkeypatch.setattr(base_module, "THRESHOLD_MAX", 10.0)
        assert base_module.clamp_threshold(15.0) == 10.0

    def test_value_below_custom_min_clamped(self, monkeypatch):
        monkeypatch.setattr(base_module, "THRESHOLD_MIN", -10.0)
        monkeypatch.setattr(base_module, "THRESHOLD_MAX", 10.0)
        assert base_module.clamp_threshold(-15.0) == -10.0

    def test_negative_value_within_custom_range_unchanged(self, monkeypatch):
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


class TestSearchKnowledgeRepoThresholdClamp:
    """验证 search_knowledge_repo 中 recallThreshold 超出范围时被 clamp。"""

    async def test_threshold_above_max_clamped_to_max(self, monkeypatch):
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

    async def test_threshold_below_min_clamped_to_min(self, monkeypatch):
        """recallThreshold=-99 低于默认 min=0，clamp 后应为 0.0，不过滤任何结果。"""
        component = _make_component()
        raw = [
            KBSearchResult(text="a", score=0.9),
            KBSearchResult(text="b", score=0.1),
        ]
        monkeypatch.setattr(component, "_search_with_faq_fallback", AsyncMock(return_value=raw))

        results = await component.search_knowledge_repo(
            adapter=_FakeAdapter(),
            query="q",
            connection_config={"connector_type": "LakeSearch"},
            knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ext-1"}],
            retrieval_params={"recallThreshold": -99.0, "topK": 10},
        )

        # clamp 到 min=0，所有 score>=0 的结果保留
        assert len(results) == 2

    async def test_threshold_equal_to_min_no_filtering(self, monkeypatch):
        """recallThreshold clamp 后等于 min，不触发过滤逻辑（if threshold > THRESHOLD_MIN）。"""
        component = _make_component()
        raw = [
            KBSearchResult(text="a", score=0.0),
            KBSearchResult(text="b", score=0.5),
        ]
        monkeypatch.setattr(component, "_search_with_faq_fallback", AsyncMock(return_value=raw))

        results = await component.search_knowledge_repo(
            adapter=_FakeAdapter(),
            query="q",
            connection_config={"connector_type": "LakeSearch"},
            knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ext-1"}],
            retrieval_params={"recallThreshold": -5.0, "topK": 10},  # clamp 到 0
        )

        # threshold == THRESHOLD_MIN(0) 时不过滤
        assert len(results) == 2

    async def test_custom_range_threshold_above_max_clamped(self, monkeypatch):
        """自定义范围 -10~10，recallThreshold=15 clamp 到 10，只保留 score>=10 的结果。"""
        # base_module 供 clamp_threshold 闭包读取，fkr_module 供 flow 层守卫判断
        monkeypatch.setattr(base_module, "THRESHOLD_MIN", -10.0)
        monkeypatch.setattr(base_module, "THRESHOLD_MAX", 10.0)
        monkeypatch.setattr(fkr_module, "THRESHOLD_MIN", -10.0)

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

    async def test_custom_range_threshold_below_min_clamped(self, monkeypatch):
        """自定义范围 -10~10，recallThreshold=-20 clamp 到 -10，保留 score>=-10 的结果。"""
        monkeypatch.setattr(base_module, "THRESHOLD_MIN", -10.0)
        monkeypatch.setattr(base_module, "THRESHOLD_MAX", 10.0)
        monkeypatch.setattr(fkr_module, "THRESHOLD_MIN", -10.0)

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
