import asyncio
import copy
import json
from unittest.mock import AsyncMock, patch

from agent_runtime.extension.tool.knowledge_retrieval_tool import (
    _ModelFacingRetrievalResult,
    build_knowledge_retrieval_openjiuwen_tool,
)

from agent_runtime.extension.tool.knowledge_retrieval_tool import (
    is_knowledge_retrieval_ir,
    _resolve_retrieval_params,
    _resolve_connection_id,
    _merge_tags,
)


# --------------------------------------------------------------------------
# is_knowledge_retrieval_ir
# --------------------------------------------------------------------------


def test_is_knowledge_retrieval_ir_true():
    ir = {"name": "retrieval", "arguments": [{"name": "knowledge_bases"}, {"name": "query"}]}
    assert is_knowledge_retrieval_ir(ir) is True


def test_is_knowledge_retrieval_ir_wrong_name():
    ir = {"name": "other", "arguments": [{"name": "knowledge_bases"}]}
    assert is_knowledge_retrieval_ir(ir) is False


def test_is_knowledge_retrieval_ir_missing_knowledge_bases_arg():
    ir = {"name": "retrieval", "arguments": [{"name": "query"}]}
    assert is_knowledge_retrieval_ir(ir) is False


def test_is_knowledge_retrieval_ir_not_dict():
    assert is_knowledge_retrieval_ir(None) is False
    assert is_knowledge_retrieval_ir("retrieval") is False


# --------------------------------------------------------------------------
# _resolve_connection_id
# --------------------------------------------------------------------------


def test_resolve_connection_id_from_first_kb():
    kbs = [{"id": "kb-1"}, {"id": "kb-2", "connection_id": "conn-2"}]
    assert _resolve_connection_id(kbs) == "conn-2"


def test_resolve_connection_id_none_returns_empty():
    assert _resolve_connection_id([{"id": "kb-1"}]) == ""


# --------------------------------------------------------------------------
# _merge_tags
# --------------------------------------------------------------------------


def test_merge_tags_applies_override_by_kb_id():
    loaded = [{"knowledge_base_id": "kb-1"}, {"knowledge_base_id": "kb-2"}]
    merged = _merge_tags(loaded, {"kb-1": ["t1", "t2"]})
    assert merged[0]["tags"] == ["t1", "t2"]
    assert "tags" not in merged[1]  # kb-2 无 override


def test_merge_tags_non_list_override_becomes_empty():
    loaded = [{"knowledge_base_id": "kb-1"}]
    merged = _merge_tags(loaded, {"kb-1": "not-a-list"})
    assert merged[0]["tags"] == []


# --------------------------------------------------------------------------
# _resolve_retrieval_params: 新形态 knowledgeConfig 优先于旧 knowledge_bases
# --------------------------------------------------------------------------


def test_resolve_retrieval_params_prefers_knowledge_config():
    ir = {
        "name": "retrieval",
        "knowledgeConfig": {
            "connectionId": "conn-new",
            "knowledgeBaseIds": ["kb-new"],
            "retrievalConfig": {},
        },
        "arguments": [
            {
                "name": "knowledge_bases",
                "default_value": [{"id": "kb-old", "connection_id": "conn-old", "tags": ["t"]}],
            }
        ],
    }
    resolved = _resolve_retrieval_params(ir)
    assert resolved["connection_id"] == "conn-new"
    assert resolved["knowledge_base_ids"] == ["kb-new"]
    # tag_overrides 仍来自旧 knowledge_bases（按 kb id 索引）
    assert resolved["tag_overrides"] == {"kb-old": ["t"]}


def test_resolve_retrieval_params_falls_back_to_knowledge_bases():
    ir = {
        "name": "retrieval",
        "arguments": [
            {
                "name": "knowledge_bases",
                "default_value": [{"id": "kb-1", "connection_id": "conn-1"}],
            }
        ],
    }
    resolved = _resolve_retrieval_params(ir)
    # 无 knowledgeConfig 时回退到 knowledge_bases
    assert resolved["connection_id"] == "conn-1"
    assert resolved["knowledge_base_ids"] == ["kb-1"]


# --------------------------------------------------------------------------
# Single-agent model view: deduplicate without changing raw retrieval output
# --------------------------------------------------------------------------


def test_model_facing_result_deduplicates_without_mutating_raw_output():
    marker = "SYNTHETIC_BODY_MARKER_7F29"
    raw = {
        "errCode": 0,
        "errMessage": "success",
        "data": {"output_list": [{
            "content": marker,
            "text": marker,
            "file_id": "fake-file",
            "retrieval_id": "fake-retrieval",
            "metadata": {"section": "fake-section"},
        }]},
    }
    snapshot = copy.deepcopy(raw)
    result = _ModelFacingRetrievalResult(raw)

    message = result.data["content"]
    row = json.loads(message)["data"]["output_list"][0]

    assert message.count(marker) == 1
    assert "text" not in row
    assert row["file_id"] == "fake-file"
    assert row["retrieval_id"] == "fake-retrieval"
    assert row["metadata"] == {"section": "fake-section"}
    assert isinstance(result, dict)
    assert result == snapshot
    assert raw == snapshot
    assert json.dumps(result, ensure_ascii=False) == json.dumps(
        snapshot, ensure_ascii=False
    )
    assert copy.deepcopy(result) == snapshot


def test_model_facing_result_preserves_nonduplicate_and_edge_cases():
    cases = [
        {"data": {"output_list": []}},
        {"data": {"output_list": [{"content": "A", "text": "B"}]}},
        {"data": {"output_list": [{"text": "ONLY_TEXT"}]}},
        {"data": {"output_list": ["NON_DICT_ROW"]}},
        {"data": {"output_list": None}},
        {"data": None},
        {"errCode": 1, "errMessage": "synthetic error"},
    ]
    for raw in cases:
        snapshot = copy.deepcopy(raw)
        result = _ModelFacingRetrievalResult(raw)
        assert json.loads(result.data["content"]) == snapshot
        assert result == snapshot
        assert raw == snapshot


def test_knowledge_retrieval_invoke_and_stream_wrap_raw_output():
    raw = {
        "errCode": 0,
        "data": {"output_list": [{"content": "BODY", "text": "BODY"}]},
    }
    snapshot = copy.deepcopy(raw)
    tool = build_knowledge_retrieval_openjiuwen_tool({
        "name": "retrieval",
        "knowledgeConfig": {
            "connectionId": "fake-connection",
            "knowledgeBaseIds": ["fake-kb"],
            "retrievalConfig": {"topK": 3},
        },
        "arguments": [],
    })
    mocked = AsyncMock(return_value=raw)

    async def exercise():
        result = await tool.invoke({"query": "fake-query"})
        assert isinstance(result, _ModelFacingRetrievalResult)
        assert result == snapshot
        rows = json.loads(result.data["content"])["data"]["output_list"]
        assert rows == [{"content": "BODY"}]

        streamed = [
            item async for item in tool.stream({"query": "fake-query"})
        ]
        assert len(streamed) == 1
        assert isinstance(streamed[0], _ModelFacingRetrievalResult)
        assert streamed[0] == snapshot

    with patch(
        "agent_runtime.extension.tool.knowledge_retrieval_tool._run_retrieval",
        mocked,
    ):
        asyncio.run(exercise())

    assert mocked.await_count == 2
    for awaited in mocked.await_args_list:
        assert awaited.kwargs == {
            "query": "fake-query",
            "connection_id": "fake-connection",
            "knowledge_base_ids": ["fake-kb"],
            "retrieval_config": {"topK": 3},
            "tag_overrides": {},
        }
    assert raw == snapshot
