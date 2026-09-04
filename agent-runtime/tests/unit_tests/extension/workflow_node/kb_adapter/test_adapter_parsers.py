import pytest

from agent_runtime.extension.workflow_node.kb_adapter.koosearch_adapter import (
    KooSearchAdapter,
)
from agent_runtime.extension.workflow_node.kb_adapter.ragflow_adapter import RagFlowAdapter
from agent_runtime.extension.workflow_node.kb_adapter.general_kb_adapter import (
    GeneralKBAdapter,
)


# --------------------------------------------------------------------------
# KooSearch._parse_response
# --------------------------------------------------------------------------


def test_koosearch_parse_response_maps_fields():
    resp = {
        "doc_list": [
            {
                "content": "txt",
                "score": 0.8,
                "repo_id": "ext-1",
                "title": "doc.pdf",
                "file_id": "f-1",
                "doc_type": "faq",
                "extra": "kept-in-metadata",
            }
        ]
    }
    results = KooSearchAdapter.parse_response(resp)
    assert len(results) == 1
    r = results[0]
    assert r.text == "txt"
    assert r.score == 0.8
    assert r.source == "ext-1"
    assert r.knowledge_base_id == "ext-1"
    assert r.document_name == "doc.pdf"
    assert r.file_id == "f-1"
    assert r.type == "faq"
    assert r.metadata.get("extra") == "kept-in-metadata"


def test_koosearch_parse_response_skips_empty_content():
    resp = {"doc_list": [{"content": "", "score": 0.9}, {"score": 0.5}]}
    assert KooSearchAdapter.parse_response(resp) == []


def test_koosearch_parse_response_empty_doc_list():
    assert KooSearchAdapter.parse_response({"doc_list": []}) == []


# --------------------------------------------------------------------------
# RagFlow._parse_response
# --------------------------------------------------------------------------


def test_ragflow_parse_response_nonzero_code_raises_error():
    with pytest.raises(RuntimeError, match="non-zero code"):
        RagFlowAdapter.parse_response({"code": 1, "message": "err"})


def test_ragflow_parse_response_maps_chunks_and_faq_by_score():
    resp = {
        "code": 0,
        "data": {
            "chunks": [
                {"content": "high", "similarity": 0.95, "dataset_id": "d-1"},
                {"content": "low", "similarity": 0.4, "dataset_id": "d-1"},
            ]
        },
    }
    results = RagFlowAdapter.parse_response(resp)
    assert [r.text for r in results] == ["high", "low"]
    # similarity 映射到 score；>0.9 判为 faq，否则 doc
    assert results[0].score == 0.95 and results[0].type == "faq"
    assert results[1].type == "doc"
    assert results[0].knowledge_base_id == "d-1"


def test_ragflow_parse_response_maps_document_keyword():
    """RAGFlow v1 retrieval API 返回 document_keyword 作为文档名称。"""
    resp = {
        "code": 0,
        "data": {
            "chunks": [
                {
                    "content": "some text",
                    "similarity": 0.8,
                    "dataset_id": "d-1",
                    "document_keyword": "report.pdf",
                    "document_id": "doc-1",
                },
            ]
        },
    }
    results = RagFlowAdapter.parse_response(resp)
    assert len(results) == 1
    r = results[0]
    assert r.document_name == "report.pdf"
    assert r.subtitle == "report.pdf"
    assert r.file_id == "doc-1"


def test_ragflow_parse_response_maps_docnm_kwd_legacy():
    """RAGFlow 旧版 API 返回 docnm_kwd 作为文档名称。"""
    resp = {
        "code": 0,
        "data": {
            "chunks": [
                {
                    "content": "legacy text",
                    "similarity": 0.7,
                    "dataset_id": "d-1",
                    "docnm_kwd": "legacy.pdf",
                    "doc_id": "doc-2",
                },
            ]
        },
    }
    results = RagFlowAdapter.parse_response(resp)
    assert len(results) == 1
    assert results[0].document_name == "legacy.pdf"
    assert results[0].file_id == "doc-2"


def test_ragflow_parse_response_document_keyword_priority():
    """document_keyword 优先于 docnm_kwd 和 title。"""
    resp = {
        "code": 0,
        "data": {
            "chunks": [
                {
                    "content": "priority text",
                    "similarity": 0.8,
                    "dataset_id": "d-1",
                    "document_keyword": "from_keyword.pdf",
                    "docnm_kwd": "from_docnm.pdf",
                    "title": "from_title",
                },
            ]
        },
    }
    results = RagFlowAdapter.parse_response(resp)
    assert results[0].document_name == "from_keyword.pdf"


def test_ragflow_parse_response_empty_chunks():
    assert RagFlowAdapter.parse_response({"code": 0, "data": {"chunks": []}}) == []


def test_ragflow_parse_response_faq_mode_marks_results_as_faq():
    """显式 searchMode=faq 时，即使 similarity 不高于 0.9，结果类型也标记为 faq。"""
    resp = {
        "code": 0,
        "data": {
            "chunks": [
                {"content": "faq answer", "similarity": 0.4, "dataset_id": "d-1"},
            ]
        },
    }
    results = RagFlowAdapter.parse_response(resp, search_mode="faq")
    assert len(results) == 1
    assert results[0].type == "faq"


# --------------------------------------------------------------------------
# General._parse_response
# --------------------------------------------------------------------------


def test_general_parse_response_maps_fields():
    resp = {
        "search_result_list": [
            {
                "content": "txt",
                "score": 0.6,
                "knowledge_base_id": "kb-1",
                "file_id": "f-1",
                "title": "t.md",
                "type": "doc",
            }
        ]
    }
    results = GeneralKBAdapter.parse_response(resp)
    assert len(results) == 1
    r = results[0]
    assert r.text == "txt"
    assert r.score == 0.6
    assert r.knowledge_base_id == "kb-1"
    assert r.file_id == "f-1"
    assert r.document_name == "t.md"


def test_general_parse_response_empty_list():
    assert GeneralKBAdapter.parse_response({"search_result_list": []}) == []
    assert GeneralKBAdapter.parse_response({}) == []


def test_general_parse_response_faq_mode_without_type_field():
    """响应缺少 type/doc_type 时，searchMode=faq 的结果类型回退为 faq。"""
    resp = {
        "search_result_list": [
            {
                "content": "faq answer",
                "score": 0.6,
                "knowledge_base_id": "kb-1",
            }
        ]
    }
    results = GeneralKBAdapter.parse_response(resp, search_mode="faq")
    assert len(results) == 1
    assert results[0].type == "faq"
