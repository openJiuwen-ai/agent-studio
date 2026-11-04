from types import SimpleNamespace

import pytest

from agent_runtime.extension.tool import knowledge_retrieval_tool as krt
from agent_runtime.extension.tool.knowledge_retrieval_tool import (
    _to_agent_output,
    _format_output,
    _run_retrieval,
)
from agent_runtime.extension.workflow_node.kb_adapter.base import KBSearchResult
from jiuwen.plugin.common import constant


def test_to_agent_output_maps_all_fields():
    r = KBSearchResult(
        text="body",
        score=0.7,
        source="src",
        knowledge_base_id="kb-1",
        knowledge_base_type="INTERNAL",
        file_id="f-1",
        document_name="doc.pdf",
        subtitle="sub",
        serial_number=2,
        retrieval_id="rid",
        type="faq",
        metadata={"k": "v"},
    )
    out = _to_agent_output(r)
    assert out["content"] == "body"
    assert out["text"] == "body"
    assert out["score"] == 0.7
    assert out["knowledge_base_id"] == "kb-1"
    assert out["knowledge_base_type"] == "INTERNAL"
    assert out["file_id"] == "f-1"
    assert out["document_name"] == "doc.pdf"
    assert out["serial_number"] == 2
    assert out["retrieval_id"] == "rid"
    assert out["type"] == "faq"
    assert out["metadata"] == {"k": "v"}


def test_format_output_structure():
    out = _format_output([{"x": 1}])
    assert out[constant.ERR_CODE] == 0
    assert out[constant.ERR_MESSAGE] == "success"
    assert out[constant.RESTFUL_DATA] == {"output_list": [{"x": 1}]}


@pytest.mark.asyncio
async def test_run_retrieval_empty_query_short_circuits():
    # 空 query 直接返回空 output_list，不触发任何检索
    out = await _run_retrieval(
        query="   ",
        connection_id="conn-1",
        knowledge_base_ids=["kb-1"],
        retrieval_config={},
        tag_overrides={},
    )
    assert out[constant.RESTFUL_DATA] == {"output_list": []}


@pytest.mark.asyncio
async def test_run_retrieval_custom_source_skips_normalization(monkeypatch):
    """CUSTOM 知识源：_run_retrieval 不调用 normalize_results_like_java。"""
    from agent_runtime.extension.workflow_node import flow_knowledge_retrieval as fkr

    sample = [KBSearchResult(text="t", score=0.9, knowledge_base_id="kb-1")]

    async def fake_ensure(self):
        return {
            "connection": {"connector_type": "LakeSearch", "knowledge_source": "CUSTOM"},
            "knowledge_bases": [{"knowledge_base_id": "kb-1", "external_id": "ext-1"}],
            "retrieval_params": {},
        }

    async def fake_search(self, **kwargs):
        return sample

    normalize_called = {"v": False}

    async def fake_normalize(self, results, kbs, params):
        normalize_called["v"] = True
        return results

    monkeypatch.setattr(fkr.FlowKnowledgeRetrieval, "ensure_kb_config", fake_ensure)
    monkeypatch.setattr(fkr.FlowKnowledgeRetrieval, "search_knowledge_repo", fake_search)
    monkeypatch.setattr(
        fkr.FlowKnowledgeRetrieval, "normalize_results_like_java", fake_normalize
    )
    # 避免真实构造适配器
    monkeypatch.setattr(krt.KBAdapterFactory, "create", lambda *a, **k: object())

    out = await _run_retrieval(
        query="hello",
        connection_id="conn-1",
        knowledge_base_ids=["kb-1"],
        retrieval_config={},
        tag_overrides={},
    )

    assert normalize_called["v"] is False  # CUSTOM 跳过归一化
    assert len(out[constant.RESTFUL_DATA]["output_list"]) == 1


# --------------------------------------------------------------------------
# retriever span 发射（_run_retrieval 遥测，镜像 APIEmbedding 范式）
# --------------------------------------------------------------------------


class _StubSpanManager:
    def __init__(self):
        self.created = 0
        self.popped = []

    def create_agent_span(self):
        self.created += 1
        return SimpleNamespace(invoke_id=f"inv-{self.created}")

    def pop_span(self, invoke_id):
        self.popped.append(invoke_id)


class _StubTracer:
    def __init__(self, fail_trigger=False, fail_events=None):
        self.span_manager = _StubSpanManager()
        self.events = []
        self.fail_trigger = fail_trigger
        self.fail_events = fail_events or set()

    @property
    def tracer_agent_span_manager(self):
        return self.span_manager

    @staticmethod
    def agent_handler_valid():
        return True

    async def trigger(self, handler, event_name, span=None, **payload):
        if self.fail_trigger or event_name in self.fail_events:
            raise RuntimeError("otel exporter down")
        self.events.append((handler, event_name, span, payload))


class _StubSession:
    def __init__(self, tracer):
        self._tracer = tracer

    def tracer(self):
        return self._tracer


def _patch_traced_session(monkeypatch, tracer):
    session = _StubSession(tracer)
    # get_current_session 已下沉为 _resolve_retrieval_tracer 内惰性导入，
    # patch 源模块属性（导入发生在调用时，取到的是补丁值）
    import openjiuwen.core.session as core_session

    monkeypatch.setattr(core_session, "get_current_session", lambda: session)


def _patch_lake_search_flow(monkeypatch, sample, normalize=None):
    """LakeSearch 非 CUSTOM 知识源：search 返回 sample，normalize 可定制。"""
    from agent_runtime.extension.workflow_node import flow_knowledge_retrieval as fkr

    async def fake_ensure(self):
        return {
            "connection": {"connector_type": "LakeSearch"},
            "knowledge_bases": [{"knowledge_base_id": "kb-1"}],
            "retrieval_params": {},
        }

    async def fake_search(self, **kwargs):
        return list(sample)

    async def fake_normalize(self, results, kbs, params):
        return normalize(results) if normalize else results

    monkeypatch.setattr(fkr.FlowKnowledgeRetrieval, "ensure_kb_config", fake_ensure)
    monkeypatch.setattr(fkr.FlowKnowledgeRetrieval, "search_knowledge_repo", fake_search)
    monkeypatch.setattr(
        fkr.FlowKnowledgeRetrieval, "normalize_results_like_java", fake_normalize
    )
    monkeypatch.setattr(krt.KBAdapterFactory, "create", lambda *a, **k: object())


@pytest.mark.asyncio
async def test_run_retrieval_emits_retriever_span(monkeypatch):
    """有会话 tracer 时：start（query/top_k/知识库）→ end（归一化后条数）。"""
    tracer = _StubTracer()
    _patch_traced_session(monkeypatch, tracer)
    sample = [
        KBSearchResult(text="t1", score=0.9, knowledge_base_id="kb-1"),
        KBSearchResult(text="t2", score=0.8, knowledge_base_id="kb-1"),
    ]
    # 归一化丢弃一条，document_count 应为归一化后的真实条数
    _patch_lake_search_flow(monkeypatch, sample, normalize=lambda rs: rs[:1])

    out = await _run_retrieval(
        query="hello",
        connection_id="conn-1",
        knowledge_base_ids=["kb-1"],
        retrieval_config={"topK": 5},
        tag_overrides={},
    )

    assert len(out[constant.RESTFUL_DATA]["output_list"]) == 1
    assert tracer.span_manager.created == 1  # 一次检索恰一个 span
    names = [e[1] for e in tracer.events]
    assert names == ["on_retriever_start", "on_retriever_end"]
    handler, _, span, payload = tracer.events[0]
    assert handler == "tracer_agent"
    assert span is not None
    assert payload["inputs"] == {"query": "hello", "top_k": 5, "knowledge_base_ids": ["kb-1"]}
    assert payload["instance_info"] == {"class_name": "knowledge_retrieval_tool"}
    assert tracer.events[1][3]["outputs"] == {"document_count": 1}


@pytest.mark.asyncio
async def test_run_retrieval_no_session_skips_events(monkeypatch):
    """无会话 tracer：不发事件，业务结果不受影响。"""
    import openjiuwen.core.session as core_session

    monkeypatch.setattr(core_session, "get_current_session", lambda: None)
    sample = [KBSearchResult(text="t", score=0.9, knowledge_base_id="kb-1")]
    _patch_lake_search_flow(monkeypatch, sample)

    out = await _run_retrieval(
        query="hello",
        connection_id="conn-1",
        knowledge_base_ids=["kb-1"],
        retrieval_config={},
        tag_overrides={},
    )

    assert len(out[constant.RESTFUL_DATA]["output_list"]) == 1


@pytest.mark.asyncio
async def test_run_retrieval_error_emits_retriever_error(monkeypatch):
    """检索抛错：发 on_retriever_error 后原样上抛。"""
    from agent_runtime.extension.workflow_node import flow_knowledge_retrieval as fkr

    tracer = _StubTracer()
    _patch_traced_session(monkeypatch, tracer)
    _patch_lake_search_flow(monkeypatch, [])

    async def boom(self, **kwargs):
        raise RuntimeError("search failed")

    monkeypatch.setattr(fkr.FlowKnowledgeRetrieval, "search_knowledge_repo", boom)

    with pytest.raises(RuntimeError, match="search failed"):
        await _run_retrieval(
            query="hello",
            connection_id="conn-1",
            knowledge_base_ids=["kb-1"],
            retrieval_config={},
            tag_overrides={},
        )

    assert [e[1] for e in tracer.events] == ["on_retriever_start", "on_retriever_error"]
    assert isinstance(tracer.events[1][3]["error"], RuntimeError)


@pytest.mark.asyncio
async def test_run_retrieval_trigger_failure_degrades(monkeypatch):
    """tracer.trigger 抛错：事件被吞掉，检索结果不受影响。"""
    tracer = _StubTracer(fail_trigger=True)
    _patch_traced_session(monkeypatch, tracer)
    sample = [KBSearchResult(text="t", score=0.9, knowledge_base_id="kb-1")]
    _patch_lake_search_flow(monkeypatch, sample)

    out = await _run_retrieval(
        query="hello",
        connection_id="conn-1",
        knowledge_base_ids=["kb-1"],
        retrieval_config={},
        tag_overrides={},
    )

    assert len(out[constant.RESTFUL_DATA]["output_list"]) == 1  # 遥测失败不阻断业务


@pytest.mark.asyncio
async def test_run_retrieval_invalid_handler_skips_events(monkeypatch):
    """agent_handler_valid 为 False（OTel 未注册）：不发事件。"""
    tracer = _StubTracer()

    def invalid():
        return False

    tracer.agent_handler_valid = invalid
    _patch_traced_session(monkeypatch, tracer)
    sample = [KBSearchResult(text="t", score=0.9, knowledge_base_id="kb-1")]
    _patch_lake_search_flow(monkeypatch, sample)

    out = await _run_retrieval(
        query="hello",
        connection_id="conn-1",
        knowledge_base_ids=["kb-1"],
        retrieval_config={},
        tag_overrides={},
    )

    assert tracer.events == []
    assert tracer.span_manager.created == 0
    assert len(out[constant.RESTFUL_DATA]["output_list"]) == 1


@pytest.mark.asyncio
async def test_run_retrieval_handler_valid_raising_skips_events(monkeypatch):
    """agent_handler_valid 自身抛错：按无 handler 处理，检索不受影响。"""

    def boom():
        raise RuntimeError("handler registry corrupted")

    tracer = _StubTracer()
    tracer.agent_handler_valid = boom
    _patch_traced_session(monkeypatch, tracer)
    sample = [KBSearchResult(text="t", score=0.9, knowledge_base_id="kb-1")]
    _patch_lake_search_flow(monkeypatch, sample)

    out = await _run_retrieval(
        query="hello",
        connection_id="conn-1",
        knowledge_base_ids=["kb-1"],
        retrieval_config={},
        tag_overrides={},
    )

    assert tracer.events == []
    assert tracer.span_manager.created == 0
    assert len(out[constant.RESTFUL_DATA]["output_list"]) == 1


@pytest.mark.asyncio
async def test_run_retrieval_span_start_failure_degrades(monkeypatch):
    """create_agent_span 抛错：开 span 被吞掉，检索照常返回。"""
    tracer = _StubTracer()

    class _BrokenSpanManager:
        @staticmethod
        def create_agent_span():
            raise RuntimeError("span manager down")

    tracer.span_manager = _BrokenSpanManager()
    _patch_traced_session(monkeypatch, tracer)
    sample = [KBSearchResult(text="t", score=0.9, knowledge_base_id="kb-1")]
    _patch_lake_search_flow(monkeypatch, sample)

    out = await _run_retrieval(
        query="hello",
        connection_id="conn-1",
        knowledge_base_ids=["kb-1"],
        retrieval_config={},
        tag_overrides={},
    )

    assert tracer.events == []  # start 失败后 end 也不再发
    assert len(out[constant.RESTFUL_DATA]["output_list"]) == 1  # 业务不受影响


@pytest.mark.asyncio
async def test_run_retrieval_start_event_failure_skips_end(monkeypatch):
    """on_retriever_start 触发失败：span 判死（None），不再发 end——无半开 span。"""
    tracer = _StubTracer(fail_events={"on_retriever_start"})
    _patch_traced_session(monkeypatch, tracer)
    sample = [KBSearchResult(text="t", score=0.9, knowledge_base_id="kb-1")]
    _patch_lake_search_flow(monkeypatch, sample)

    out = await _run_retrieval(
        query="hello",
        connection_id="conn-1",
        knowledge_base_ids=["kb-1"],
        retrieval_config={},
        tag_overrides={},
    )

    # start 未送达：end 事件不补发（span 已判死），业务照常
    assert tracer.events == []
    assert len(out[constant.RESTFUL_DATA]["output_list"]) == 1
    # 判死的同时注销登记：span manager 不留永不 start/end 的悬空记录
    assert tracer.span_manager.popped == ["inv-1"]
