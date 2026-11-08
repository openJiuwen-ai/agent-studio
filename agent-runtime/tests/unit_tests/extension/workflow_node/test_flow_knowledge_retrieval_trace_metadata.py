# pylint: disable=protected-access  # 单元测试需直接验证内部方法行为
"""FlowKnowledgeRetrieval.trace_metadata 检索事实导出契约。

core 引擎经 getattr 钩子拾取返回值并入组件 metadata，tracer_otel handler
按 isinstance 门控消费（top_k 必须 int、data_source_ids 非空 list）。
"""
from agent_runtime.extension.workflow_node.flow_knowledge_retrieval import (
    FlowKnowledgeRetrieval,
    FlowKnowledgeRetrievalConfig,
)


def test_trace_metadata_full_conf():
    component = FlowKnowledgeRetrieval(
        {
            "connectionId": "conn-1",
            "knowledgeBaseIds": ["kb-1", "kb-2"],
            "retrievalConfig": {"topK": 5},
        }
    )

    metadata = component.trace_metadata()

    assert metadata == {"top_k": 5, "data_source_ids": ["kb-1", "kb-2"]}


def test_trace_metadata_defaults_align_with_search_behavior():
    """空检索配置时 top_k 取执行口径默认值 10，无库则不产 data_source_ids。"""
    component = FlowKnowledgeRetrieval(
        {"connectionId": "conn-1", "knowledgeBaseIds": [], "retrievalConfig": {}}
    )

    metadata = component.trace_metadata()

    assert metadata == {"top_k": 10}


def test_trace_metadata_non_numeric_top_k_omitted():
    """topK 非数值时丢 top_k 键（handler isinstance 门控跳过），其余照出。"""
    component = FlowKnowledgeRetrieval(
        {
            "connectionId": "conn-1",
            "knowledgeBaseIds": ["kb-1"],
            "retrievalConfig": {"topK": "many"},
        }
    )

    metadata = component.trace_metadata()

    assert metadata == {"data_source_ids": ["kb-1"]}


def test_trace_metadata_without_conf_returns_none():
    """无配置组件保持基类语义（None，不添事实）。"""
    component = FlowKnowledgeRetrieval()

    assert component.trace_metadata() is None


def test_trace_metadata_dataclass_conf_and_copy():
    """dataclass 配置路径同样生效；返回列表为拷贝，不回写组件配置。"""
    component = FlowKnowledgeRetrieval(
        FlowKnowledgeRetrievalConfig(
            connection_id="conn-1",
            knowledge_base_ids=["kb-1"],
            retrieval_config={"topK": "3"},
        )
    )

    metadata = component.trace_metadata()

    assert metadata == {"top_k": 3, "data_source_ids": ["kb-1"]}
    metadata["data_source_ids"].append("kb-extra")
    assert component.config.knowledge_base_ids == ["kb-1"]
