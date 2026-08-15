"""KB 适配器 search() 请求构建测试：用 fake aiohttp 捕获出站请求体/URL/headers。"""

import pytest

from agent_runtime.extension.workflow_node.kb_adapter import (
    lakesearch_adapter,
    koosearch_adapter,
    ragflow_adapter,
    general_kb_adapter,
)
from agent_runtime.extension.workflow_node.kb_adapter.lakesearch_adapter import (
    LakeSearchAdapter,
)
from agent_runtime.extension.workflow_node.kb_adapter.koosearch_adapter import (
    KooSearchAdapter,
)
from agent_runtime.extension.workflow_node.kb_adapter.ragflow_adapter import RagFlowAdapter
from agent_runtime.extension.workflow_node.kb_adapter.general_kb_adapter import (
    GeneralKBAdapter,
)

pytestmark = pytest.mark.asyncio


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload
        self.ok = True
        self.status = 200

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def text(self):
        import json as _json

        return _json.dumps(self._payload)

    async def json(self):
        return self._payload


class _FakeSession:
    """记录最后一次 post 的 kwargs，返回预置响应。"""

    last = {}

    def __init__(self, payload):
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    def post(self, url=None, json=None, headers=None, timeout=None, **kwargs):
        _FakeSession.last = {
            "url": url,
            "json": json,
            "headers": headers,
            "ssl": kwargs.get("ssl"),
        }
        return _FakeResp(self._payload)


def _patch_session(monkeypatch, module, payload):
    _FakeSession.last = {}
    monkeypatch.setattr(
        module.aiohttp, "ClientSession", lambda *a, **k: _FakeSession(payload)
    )


# --------------------------------------------------------------------------
# LakeSearch
# --------------------------------------------------------------------------


async def test_lakesearch_builds_request(monkeypatch):
    _patch_session(monkeypatch, lakesearch_adapter, {"doc_list": []})
    adapter = LakeSearchAdapter()
    await adapter.search(
        query="hello",
        connection_config={
            "endpoint": "http://host",
            "auth_mode": "BASIC",
            "authorization": "cred",
            "extra_params": {"project_id": "p1", "app_id": "a1"},
        },
        knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ext-1"}],
        retrieval_params={"topK": 3, "searchMode": "faq", "tags": ["t1", "t2"]},
    )
    sent = _FakeSession.last
    assert sent["url"] == "http://host/v1/p1/applications/a1/uni-search/experience/searchtext"
    assert sent["json"]["repo_id"] == "ext-1"
    assert sent["json"]["content"] == "hello"
    assert sent["json"]["page_num"] == 1
    assert sent["json"]["page_size"] == 3  # min(topK, 50)
    assert sent["json"]["scope"] == "faq"
    assert sent["json"]["filter_string"] == "tags:(t1 OR t2)"
    assert sent["headers"]["Authorization"] == "Basic cred"


async def test_lakesearch_page_size_capped_at_50(monkeypatch):
    _patch_session(monkeypatch, lakesearch_adapter, {"doc_list": []})
    adapter = LakeSearchAdapter()
    await adapter.search(
        query="q",
        connection_config={
            "endpoint": "http://host",
            "auth_mode": "TOKEN",
            "authorization": "tok",
            "extra_params": {"project_id": "p1", "app_id": "a1"},
        },
        knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ext-1"}],
        retrieval_params={"topK": 999},
    )
    assert _FakeSession.last["json"]["page_size"] == 50
    assert _FakeSession.last["headers"]["Authorization"] == "Bearer tok"


async def test_lakesearch_multi_kb_single_request_with_extra_repo_ids(monkeypatch):
    """多知识库检索：对齐 Java 端，单次 HTTP 请求，用 extra_repo_ids 传递所有知识库 ID。"""
    _patch_session(monkeypatch, lakesearch_adapter, {"doc_list": []})
    adapter = LakeSearchAdapter()
    await adapter.search(
        query="multi-kb query",
        connection_config={
            "endpoint": "http://host",
            "auth_mode": "BASIC",
            "authorization": "cred",
            "extra_params": {"project_id": "p1", "app_id": "a1"},
        },
        knowledge_bases=[
            {"knowledge_base_id": "kb-1", "external_id": "ext-1"},
            {"knowledge_base_id": "kb-2", "external_id": "ext-2"},
            {"knowledge_base_id": "kb-3", "external_id": "ext-3"},
        ],
        retrieval_params={"topK": 5},
    )
    sent = _FakeSession.last
    assert sent["json"]["repo_id"] == "ext-1"  # 第一个 KB 作为主 repo_id
    # 对齐 Java LakeSearchService：extra_repo_ids 排除主 repo（主 repo 已在 repo_id 中）
    assert sent["json"]["extra_repo_ids"] == ["ext-2", "ext-3"]
    assert sent["json"]["content"] == "multi-kb query"


async def test_lakesearch_single_kb_no_extra_repo_ids(monkeypatch):
    """单知识库检索：不设置 extra_repo_ids。"""
    _patch_session(monkeypatch, lakesearch_adapter, {"doc_list": []})
    adapter = LakeSearchAdapter()
    await adapter.search(
        query="q",
        connection_config={
            "endpoint": "http://host",
            "auth_mode": "BASIC",
            "authorization": "cred",
            "extra_params": {"project_id": "p1", "app_id": "a1"},
        },
        knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ext-1"}],
        retrieval_params={"topK": 5},
    )
    sent = _FakeSession.last
    assert sent["json"]["repo_id"] == "ext-1"
    assert "extra_repo_ids" not in sent["json"]  # 单 KB 不需要 extra_repo_ids


async def test_lakesearch_ssl_disabled_by_default(monkeypatch):
    """KB_SSL_VERIFY 默认 false：对齐旧版，POST 传 ssl=False 跳过证书校验。"""
    monkeypatch.setattr(lakesearch_adapter.settings.kb, "ssl_verify", False)
    _patch_session(monkeypatch, lakesearch_adapter, {"doc_list": []})
    adapter = LakeSearchAdapter()
    await adapter.search(
        query="q",
        connection_config={
            "endpoint": "http://host",
            "auth_mode": "BASIC",
            "authorization": "cred",
            "extra_params": {"project_id": "p1", "app_id": "a1"},
        },
        knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ext-1"}],
        retrieval_params={"topK": 3},
    )
    assert _FakeSession.last["ssl"] is False


async def test_lakesearch_ssl_enabled_when_verify_true(monkeypatch):
    """KB_SSL_VERIFY=true：恢复证书校验，POST 传 ssl=None 走 aiohttp 默认。"""
    monkeypatch.setattr(lakesearch_adapter.settings.kb, "ssl_verify", True)
    _patch_session(monkeypatch, lakesearch_adapter, {"doc_list": []})
    adapter = LakeSearchAdapter()
    await adapter.search(
        query="q",
        connection_config={
            "endpoint": "http://host",
            "auth_mode": "BASIC",
            "authorization": "cred",
            "extra_params": {"project_id": "p1", "app_id": "a1"},
        },
        knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ext-1"}],
        retrieval_params={"topK": 3},
    )
    assert _FakeSession.last["ssl"] is None


# --------------------------------------------------------------------------
# KooSearch
# --------------------------------------------------------------------------


async def test_koosearch_builds_request_with_extra_repo_ids(monkeypatch):
    _patch_session(monkeypatch, koosearch_adapter, {"doc_list": []})
    adapter = KooSearchAdapter()
    await adapter.search(
        query="q",
        connection_config={
            "endpoint": "http://koo",
            "authorization": "appcode-1",
            "extra_params": {"project_id": "p1", "application_id": "app1"},
        },
        knowledge_bases=[
            {"knowledge_base_id": "kb-1", "external_id": "ext-1"},
            {"knowledge_base_id": "kb-2", "external_id": "ext-2"},
        ],
        retrieval_params={"topK": 5, "searchMode": "mix"},
    )
    sent = _FakeSession.last
    assert sent["json"]["repo_id"] == "ext-1"
    # 对齐 Java CssUniSearchService：extra_repo_ids 排除主 repo（主 repo 已在 repo_id 中）
    assert sent["json"]["extra_repo_ids"] == ["ext-2"]
    assert sent["json"]["scope"] == "mix"
    assert sent["headers"]["X-Apig-AppCode"] == "appcode-1"


async def test_koosearch_appcode_takes_priority_over_authorization(monkeypatch):
    """AppCode 优先于 authorization — _merge_auth_headers 可能填入用户 token。"""
    _patch_session(monkeypatch, koosearch_adapter, {"doc_list": []})
    adapter = KooSearchAdapter()
    await adapter.search(
        query="q",
        connection_config={
            "endpoint": "http://koo",
            "authorization": "user-login-token",
            "extra_params": {"AppCode": "real-app-code", "project_id": "p1", "application_id": "app1"},
        },
        knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ext-1"}],
        retrieval_params={},
    )
    assert _FakeSession.last["headers"]["X-Apig-AppCode"] == "real-app-code"


async def test_koosearch_fallback_to_authorization(monkeypatch):
    """当 extra_params 中没有 AppCode 时，回退使用 authorization。"""
    _patch_session(monkeypatch, koosearch_adapter, {"doc_list": []})
    adapter = KooSearchAdapter()
    await adapter.search(
        query="q",
        connection_config={
            "endpoint": "http://koo",
            "authorization": "appcode-from-auth",
            "extra_params": {"project_id": "p1", "application_id": "app1"},
        },
        knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ext-1"}],
        retrieval_params={},
    )
    assert _FakeSession.last["headers"]["X-Apig-AppCode"] == "appcode-from-auth"


async def test_koosearch_raises_when_no_appcode(monkeypatch):
    """AppCode 和 authorization 都为空时，抛出 RuntimeError。"""
    _patch_session(monkeypatch, koosearch_adapter, {"doc_list": []})
    adapter = KooSearchAdapter()
    with pytest.raises(RuntimeError, match="AppCode"):
        await adapter.search(
            query="q",
            connection_config={"endpoint": "http://koo", "extra_params": {}},
            knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ext-1"}],
            retrieval_params={},
        )


async def test_koosearch_raises_when_no_endpoint():
    """endpoint 为空时，抛出 RuntimeError。"""
    adapter = KooSearchAdapter()
    with pytest.raises(RuntimeError, match="endpoint"):
        await adapter.search(
            query="q",
            connection_config={"endpoint": "", "extra_params": {"AppCode": "code"}},
            knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ext-1"}],
            retrieval_params={},
        )


# --------------------------------------------------------------------------
# RAGFlow
# --------------------------------------------------------------------------


async def test_ragflow_builds_request(monkeypatch):
    _patch_session(monkeypatch, ragflow_adapter, {"code": 0, "data": {"chunks": []}})
    adapter = RagFlowAdapter()
    await adapter.search(
        query="q",
        connection_config={"endpoint": "http://rag", "authorization": "key-1"},
        knowledge_bases=[
            {"knowledge_base_id": "kb-1", "external_id": "ds-1"},
            {"knowledge_base_id": "kb-2", "external_id": "ds-2"},
        ],
        retrieval_params={"topK": 4, "scoreThreshold": 0.6},
    )
    sent = _FakeSession.last
    assert sent["url"] == "http://rag/api/v1/retrieval"
    assert sent["json"]["question"] == "q"
    assert sent["json"]["dataset_ids"] == ["ds-1", "ds-2"]
    assert sent["json"]["page_size"] == 4
    assert sent["json"]["similarity_threshold"] == 0.6
    assert sent["headers"]["Authorization"] == "Bearer key-1"


async def test_ragflow_apikey_takes_priority_over_authorization(monkeypatch):
    """APIKey 优先于 authorization — _merge_auth_headers 可能填入用户 token，不可用作 RAGFlow 鉴权。"""
    _patch_session(monkeypatch, ragflow_adapter, {"code": 0, "data": {"chunks": []}})
    adapter = RagFlowAdapter()
    await adapter.search(
        query="q",
        connection_config={
            "endpoint": "http://rag",
            "authorization": "user-login-token",  # 被 _merge_auth_headers 填入的用户 token
            "extra_params": {"APIKey": "ragflow-api-key"},  # RAGFlow 真正的 API Key
        },
        knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ds-1"}],
        retrieval_params={},
    )
    assert _FakeSession.last["headers"]["Authorization"] == "Bearer ragflow-api-key"


async def test_ragflow_apikey_fallback_to_authorization(monkeypatch):
    """当 extra_params 中没有 APIKey 时，回退使用 authorization。"""
    _patch_session(monkeypatch, ragflow_adapter, {"code": 0, "data": {"chunks": []}})
    adapter = RagFlowAdapter()
    await adapter.search(
        query="q",
        connection_config={
            "endpoint": "http://rag",
            "authorization": "key-from-auth",
            "extra_params": {},  # 没有 APIKey
        },
        knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ds-1"}],
        retrieval_params={},
    )
    assert _FakeSession.last["headers"]["Authorization"] == "Bearer key-from-auth"


async def test_ragflow_empty_authorization_raises_error(monkeypatch):
    """APIKey 和 authorization 都为空时，抛出 RuntimeError。"""
    _patch_session(monkeypatch, ragflow_adapter, {"code": 0, "data": {"chunks": []}})
    adapter = RagFlowAdapter()
    with pytest.raises(RuntimeError, match="authorization"):
        await adapter.search(
            query="q",
            connection_config={
                "endpoint": "http://rag",
                "authorization": "",
                "extra_params": {"APIKey": ""},
            },
            knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ds-1"}],
            retrieval_params={},
        )


async def test_ragflow_empty_endpoint_raises_error():
    """endpoint 为空时，抛出 RuntimeError。"""
    adapter = RagFlowAdapter()
    with pytest.raises(RuntimeError, match="endpoint"):
        await adapter.search(
            query="q",
            connection_config={"endpoint": "", "authorization": "key"},
            knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ds-1"}],
            retrieval_params={},
        )


# --------------------------------------------------------------------------
# General
# --------------------------------------------------------------------------


async def test_general_builds_request(monkeypatch):
    _patch_session(monkeypatch, general_kb_adapter, {"search_result_list": []})
    adapter = GeneralKBAdapter()
    await adapter.search(
        query="q",
        connection_config={
            "endpoint": "http://gen",
            "authorization": "api-1",
            "extra_params": {},
        },
        knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ext-1"}],
        retrieval_params={"topK": 7, "searchMode": "keyword", "scoreThreshold": 0.5},
    )
    sent = _FakeSession.last
    assert sent["url"] == "http://gen/knowledge-bases/retrieve"
    assert sent["json"]["knowledge_base_ids"] == ["ext-1"]
    assert sent["json"]["method"] == "keyword"
    assert sent["json"]["limit"] == 7
    assert sent["json"]["top_k"] == 7
    assert sent["json"]["search_threshold"] == 0.5
    assert sent["headers"]["Authorization"] == "Bearer api-1"


async def test_general_apikey_takes_priority_over_authorization(monkeypatch):
    """apiKey 优先于 authorization — _merge_auth_headers 可能填入用户 token。"""
    _patch_session(monkeypatch, general_kb_adapter, {"search_result_list": []})
    adapter = GeneralKBAdapter()
    await adapter.search(
        query="q",
        connection_config={
            "endpoint": "http://gen",
            "authorization": "user-login-token",
            "extra_params": {"apiKey": "real-api-key"},
        },
        knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ext-1"}],
        retrieval_params={},
    )
    assert _FakeSession.last["headers"]["Authorization"] == "Bearer real-api-key"


async def test_general_fallback_to_authorization(monkeypatch):
    """当 extra_params 中没有 apiKey 时，回退使用 authorization。"""
    _patch_session(monkeypatch, general_kb_adapter, {"search_result_list": []})
    adapter = GeneralKBAdapter()
    await adapter.search(
        query="q",
        connection_config={
            "endpoint": "http://gen",
            "authorization": "key-from-auth",
            "extra_params": {},
        },
        knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ext-1"}],
        retrieval_params={},
    )
    assert _FakeSession.last["headers"]["Authorization"] == "Bearer key-from-auth"


async def test_general_raises_when_no_apikey(monkeypatch):
    """apiKey 和 authorization 都为空时，抛出 RuntimeError。"""
    _patch_session(monkeypatch, general_kb_adapter, {"search_result_list": []})
    adapter = GeneralKBAdapter()
    with pytest.raises(RuntimeError, match="apiKey"):
        await adapter.search(
            query="q",
            connection_config={
                "endpoint": "http://gen",
                "authorization": "",
                "extra_params": {"apiKey": ""},
            },
            knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ext-1"}],
            retrieval_params={},
        )


async def test_general_raises_when_no_endpoint():
    """endpoint 为空时，抛出 RuntimeError。"""
    adapter = GeneralKBAdapter()
    with pytest.raises(RuntimeError, match="endpoint"):
        await adapter.search(
            query="q",
            connection_config={"endpoint": "", "authorization": "key", "extra_params": {}},
            knowledge_bases=[{"knowledge_base_id": "kb-1", "external_id": "ext-1"}],
            retrieval_params={},
        )
