# coding: utf-8

"""FlowKnowledgeRetrieval.trace_metadata 契约：喂给工作流 retrieval span 的静态事实。

tracer_otel 侧的读取契约（handler._apply_component_metadata）：
- top_k 必须是 int（isinstance 判断，非 int 直接丢弃）
- data_source_ids 必须是非空 list
"""

from agent_runtime.extension.workflow_node.flow_knowledge_retrieval import (
    FlowKnowledgeRetrieval,
)


def test_trace_metadata_exports_topk_and_data_source_ids():
    comp = FlowKnowledgeRetrieval(
        {
            "connectionId": "conn-1",
            "knowledgeBaseIds": ["kb-1", "kb-2"],
            "retrievalConfig": {"topK": 5},
        }
    )
    assert comp.trace_metadata() == {
        "top_k": 5,
        "data_source_ids": ["kb-1", "kb-2"],
    }


def test_trace_metadata_topk_is_int_even_from_string_ir():
    # IR 里 topK 可能是字符串；handler 只接受 int，这里负责收敛
    comp = FlowKnowledgeRetrieval(
        {
            "connectionId": "conn-1",
            "knowledgeBaseIds": ["kb-1"],
            "retrievalConfig": {"topK": "3"},
        }
    )
    metadata = comp.trace_metadata()
    assert metadata["top_k"] == 3
    assert isinstance(metadata["top_k"], int)


def test_trace_metadata_missing_or_invalid_topk_omits_key():
    comp = FlowKnowledgeRetrieval(
        {
            "connectionId": "conn-1",
            "knowledgeBaseIds": [],
            "retrievalConfig": {},
        }
    )
    assert comp.trace_metadata() == {"data_source_ids": []}

    comp_missing = FlowKnowledgeRetrieval(
        {
            "connectionId": "conn-1",
            "knowledgeBaseIds": [],
            "retrievalConfig": {"topK": "not-a-number"},
        }
    )
    assert comp_missing.trace_metadata() == {"data_source_ids": []}


def test_trace_metadata_without_conf_returns_none():
    # 遗留两阶段初始化路径：init 之前 conf 为空
    assert FlowKnowledgeRetrieval(None).trace_metadata() is None


def test_trace_metadata_prefers_loaded_kb_retrieval_params(monkeypatch):
    # 首次执行前 _kb_config 未加载，用 IR retrievalConfig；
    # 已加载后 OBS retrieval_params 是实际生效值，优先
    comp = FlowKnowledgeRetrieval(
        {
            "connectionId": "conn-1",
            "knowledgeBaseIds": ["kb-1"],
            "retrievalConfig": {"topK": 5},
        }
    )
    monkeypatch.setattr(comp, "_kb_config", {"retrieval_params": {"topK": 7}})
    assert comp.trace_metadata()["top_k"] == 7
