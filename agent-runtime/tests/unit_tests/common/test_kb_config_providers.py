# pylint: disable=protected-access  # 单元测试需直接验证内部方法行为
import json

from agent_runtime.common import kb_config_providers
from agent_runtime.common.kb_config_providers import (
    KBConnectionConfig,
    KBReferenceConfig,
    OBSKnowledgeBaseConfigProvider,
)
from agent_runtime.context.request_context import RequestContext, _request_ctx


def test_parse_connection_reads_knowledge_source():
    provider = OBSKnowledgeBaseConfigProvider()
    conn = provider._parse_connection(
        {
            "connectionId": "conn-1",
            "connectorId": "LakeSearchInside",
            "knowledgeSource": "CUSTOM",
            "params": [{"code": "endpoint", "value": "http://host"}],
        }
    )
    assert conn.knowledge_source == "CUSTOM"
    assert conn.connector_type == "LakeSearchInside"
    assert conn.endpoint == "http://host"


def test_parse_connection_defaults_knowledge_source_empty():
    provider = OBSKnowledgeBaseConfigProvider()
    conn = provider._parse_connection({"connectionId": "conn-1"})
    assert conn.knowledge_source == ""


def test_parse_connection_decrypts_secret_params(monkeypatch):
    """SECRET 类型参数在 _parse_connection 中通过 CryptTool().decrypt() 解密。"""
    def _fake_decrypt(v):
        return f"decrypted::{v}"

    class _FakeCryptTool:
        decrypt = staticmethod(_fake_decrypt)

    monkeypatch.setattr(kb_config_providers, "CryptTool", _FakeCryptTool)
    provider = OBSKnowledgeBaseConfigProvider()
    conn = provider._parse_connection(
        {
            "connectionId": "conn-1",
            "connectorId": "Ragflow",
            "params": [
                {"code": "APIKey", "value": "cipher-text"},
                {"code": "endpoint", "value": "http://host"},
            ],
        }
    )
    # SECRET 字段被解密，普通字段保持原样
    assert conn.extra_params["APIKey"] == "decrypted::cipher-text"
    assert conn.extra_params["endpoint"] == "http://host"


def test_parse_connection_builds_basic_auth_from_user_password(monkeypatch):
    """authorization 为空但有 user_name+password 时自动生成 Basic 凭证。"""
    class _FakeCryptTool:
        @staticmethod
        def decrypt(v):
            return v

    monkeypatch.setattr(kb_config_providers, "CryptTool", _FakeCryptTool)
    provider = OBSKnowledgeBaseConfigProvider()
    conn = provider._parse_connection(
        {
            "connectionId": "conn-1",
            "connectorId": "LakeSearchInside",
            "params": [
                {"code": "user_name", "value": "alice"},
                {"code": "password", "value": "secret"},
            ],
        }
    )
    # authorization 为空但有 user_name+password 时自动生成 Basic 凭证（base64(user:pass)）
    import base64

    assert conn.auth_mode == "BASIC"
    assert conn.authorization == base64.b64encode(b"alice:secret").decode()


# ---------------------------------------------------------------------------
# _merge_auth_headers 测试
# ---------------------------------------------------------------------------


def test_merge_auth_headers_lakesearch_fills_user_token():
    """LakeSearch 连接：authorization 为空时，用用户 token 兜底。"""
    provider = OBSKnowledgeBaseConfigProvider()
    conn = KBConnectionConfig(
        connection_id="conn-1",
        connector_type="LakeSearch",
        authorization="",
    )
    token = _request_ctx.set(
        RequestContext(headers={"X-Auth-Token": "user-login-token"})
    )
    try:
        provider._merge_auth_headers(conn)
        assert conn.authorization == "user-login-token"
        assert conn.auth_mode == "TOKEN"
    finally:
        _request_ctx.reset(token)


def test_merge_auth_headers_ragflow_skips_user_token():
    """RAGFlow 连接：不应该用用户 token 填充 authorization。"""
    provider = OBSKnowledgeBaseConfigProvider()
    conn = KBConnectionConfig(
        connection_id="conn-1",
        connector_type="RagFlow",
        authorization="",
    )
    token = _request_ctx.set(
        RequestContext(headers={"X-Auth-Token": "user-login-token"})
    )
    try:
        provider._merge_auth_headers(conn)
        assert conn.authorization == ""  # 不应被填充
    finally:
        _request_ctx.reset(token)


def test_merge_auth_headers_koosearch_skips_user_token():
    """KooSearch 连接：不应该用用户 token 填充 authorization。"""
    provider = OBSKnowledgeBaseConfigProvider()
    conn = KBConnectionConfig(
        connection_id="conn-1",
        connector_type="KooSearch",
        authorization="",
    )
    token = _request_ctx.set(
        RequestContext(headers={"X-Auth-Token": "user-login-token"})
    )
    try:
        provider._merge_auth_headers(conn)
        assert conn.authorization == ""  # 不应被填充
    finally:
        _request_ctx.reset(token)


def test_merge_auth_headers_no_override_existing():
    """已有 authorization 时不覆盖。"""
    provider = OBSKnowledgeBaseConfigProvider()
    conn = KBConnectionConfig(
        connection_id="conn-1",
        connector_type="LakeSearch",
        authorization="existing-cred",
    )
    token = _request_ctx.set(
        RequestContext(headers={"X-Auth-Token": "user-login-token"})
    )
    try:
        provider._merge_auth_headers(conn)
        assert conn.authorization == "existing-cred"  # 保持原值
    finally:
        _request_ctx.reset(token)


def test_merge_auth_headers_empty_connector_type_fills_user_token():
    """connector_type 为空（未知/兼容旧数据）时仍用用户 token 兜底。"""
    provider = OBSKnowledgeBaseConfigProvider()
    conn = KBConnectionConfig(
        connection_id="conn-1",
        connector_type="",
        authorization="",
    )
    token = _request_ctx.set(
        RequestContext(headers={"X-Auth-Token": "user-login-token"})
    )
    try:
        provider._merge_auth_headers(conn)
        assert conn.authorization == "user-login-token"
    finally:
        _request_ctx.reset(token)


def test_merge_auth_headers_lakesearch_inside_fills_user_token():
    """LakeSearchInside 连接：底层是 LakeSearchAdapter，应用户 token 兜底。"""
    provider = OBSKnowledgeBaseConfigProvider()
    conn = KBConnectionConfig(
        connection_id="conn-1",
        connector_type="LakeSearchInside",
        authorization="",
    )
    token = _request_ctx.set(
        RequestContext(headers={"X-Auth-Token": "user-login-token"})
    )
    try:
        provider._merge_auth_headers(conn)
        assert conn.authorization == "user-login-token"
    finally:
        _request_ctx.reset(token)


def test_merge_auth_headers_custom_fills_user_token():
    """Custom 连接：底层是 LakeSearchAdapter，应用户 token 兜底。"""
    provider = OBSKnowledgeBaseConfigProvider()
    conn = KBConnectionConfig(
        connection_id="conn-1",
        connector_type="Custom",
        authorization="",
    )
    token = _request_ctx.set(
        RequestContext(headers={"X-Auth-Token": "user-login-token"})
    )
    try:
        provider._merge_auth_headers(conn)
        assert conn.authorization == "user-login-token"
    finally:
        _request_ctx.reset(token)


# ---------------------------------------------------------------------------
# model_config / reranker_config 解析测试
# ---------------------------------------------------------------------------


def test_parse_connection_extracts_model_config():
    """openjiuwen 连接文件中 model_config 以 JSON 字符串存储在 params 里。"""
    provider = OBSKnowledgeBaseConfigProvider()
    model_cfg = {"model_service_id": "svc-123", "workspace_id": "ws-1"}
    conn = provider._parse_connection(
        {
            "connectionId": "conn-1",
            "connectorId": "OpenJiuwen",
            "params": [
                {"code": "model_config", "value": json.dumps(model_cfg)},
            ],
        }
    )
    assert conn.model_config == model_cfg
    assert conn.connector_type == "OpenJiuwen"


def test_parse_connection_extracts_reranker_config():
    """reranker_config 以 JSON 字符串存储在 params 里。"""
    provider = OBSKnowledgeBaseConfigProvider()
    reranker_cfg = {"model_service_id": "rerank-456", "workspace_id": "ws-1"}
    conn = provider._parse_connection(
        {
            "connectionId": "conn-1",
            "connectorId": "OpenJiuwen",
            "params": [
                {"code": "model_config", "value": json.dumps({"model_service_id": "svc-123"})},
                {"code": "reranker_config", "value": json.dumps(reranker_cfg)},
            ],
        }
    )
    assert conn.reranker_config == reranker_cfg


def test_parse_connection_reranker_config_empty_when_absent():
    """没有 reranker_config param 时，reranker_config 为空 dict。"""
    provider = OBSKnowledgeBaseConfigProvider()
    conn = provider._parse_connection(
        {
            "connectionId": "conn-1",
            "connectorId": "OpenJiuwen",
            "params": [
                {"code": "model_config", "value": json.dumps({"model_service_id": "svc-123"})},
            ],
        }
    )
    assert conn.reranker_config == {}


def test_parse_connection_invalid_reranker_config_json_falls_back_to_empty():
    """reranker_config JSON 解析失败时，reranker_config 为空 dict（不抛异常）。"""
    provider = OBSKnowledgeBaseConfigProvider()
    conn = provider._parse_connection(
        {
            "connectionId": "conn-1",
            "connectorId": "OpenJiuwen",
            "params": [
                {"code": "model_config", "value": json.dumps({"model_service_id": "svc-123"})},
                {"code": "reranker_config", "value": "not-valid-json"},
            ],
        }
    )
    assert conn.reranker_config == {}


def test_parse_connection_invalid_model_config_json_falls_back_to_empty():
    """model_config JSON 解析失败时，model_config 为空 dict（不抛异常）。"""
    provider = OBSKnowledgeBaseConfigProvider()
    conn = provider._parse_connection(
        {
            "connectionId": "conn-1",
            "connectorId": "OpenJiuwen",
            "params": [
                {"code": "model_config", "value": "broken"},
            ],
        }
    )
    assert conn.model_config == {}


# ---------------------------------------------------------------------------
# get_kb_config — CUSTOM 模式 KB reference 回退测试
# ---------------------------------------------------------------------------


def _make_ir_node(connection_id="conn-1", kb_ids=None):
    """构造最小化 ir_node dict。"""
    return {
        "configs": {
            "connectionId": connection_id,
            "knowledgeBaseIds": kb_ids or [],
        }
    }


def test_custom_mode_kb_fallback_uses_kb_id_as_external_id(monkeypatch):
    """CUSTOM 模式下 OBS 无 reference 文件时，用 kb_id 作为 external_id。"""
    import asyncio

    provider = OBSKnowledgeBaseConfigProvider()

    async def fake_load_connection(cid):
        return KBConnectionConfig(
            connection_id=cid,
            connector_type="LakeSearchInside",
            knowledge_source="CUSTOM",
            endpoint="http://lakesearch",
        )

    async def fake_load_kb_reference(kb_id):
        return None  # OBS 无 reference 文件

    monkeypatch.setattr(provider, "_load_connection_config", fake_load_connection)
    monkeypatch.setattr(provider, "_load_kb_reference", fake_load_kb_reference)
    monkeypatch.setattr(provider, "_merge_auth_headers", lambda conn: None)

    ir_node = _make_ir_node(kb_ids=["kb-001", "kb-002"])
    result = asyncio.run(provider.get_kb_config(ir_node))

    kbs = result["knowledge_bases"]
    assert len(kbs) == 2
    assert kbs[0]["knowledge_base_id"] == "kb-001"
    assert kbs[0]["external_id"] == "kb-001"
    assert kbs[0]["connection_id"] == "conn-1"
    assert kbs[1]["knowledge_base_id"] == "kb-002"
    assert kbs[1]["external_id"] == "kb-002"


def test_non_custom_mode_kb_missing_no_fallback(monkeypatch):
    """非 CUSTOM 模式下 OBS 无 reference 文件时，不生成 KB reference（保持原行为）。"""
    import asyncio

    provider = OBSKnowledgeBaseConfigProvider()

    async def fake_load_connection(cid):
        return KBConnectionConfig(
            connection_id=cid,
            connector_type="LakeSearch",
            knowledge_source="LakeSearch",  # 非 CUSTOM
        )

    async def fake_load_kb_reference(kb_id):
        return None

    monkeypatch.setattr(provider, "_load_connection_config", fake_load_connection)
    monkeypatch.setattr(provider, "_load_kb_reference", fake_load_kb_reference)
    monkeypatch.setattr(provider, "_merge_auth_headers", lambda conn: None)

    ir_node = _make_ir_node(kb_ids=["kb-001"])
    result = asyncio.run(provider.get_kb_config(ir_node))

    assert len(result["knowledge_bases"]) == 0


def test_custom_mode_kb_ref_exists_uses_ref(monkeypatch):
    """CUSTOM 模式下 OBS 有 reference 文件时，使用 reference 而非回退逻辑。"""
    import asyncio

    provider = OBSKnowledgeBaseConfigProvider()

    async def fake_load_connection(cid):
        return KBConnectionConfig(
            connection_id=cid,
            connector_type="LakeSearchInside",
            knowledge_source="CUSTOM",
        )

    async def fake_load_kb_reference(kb_id):
        return KBReferenceConfig(
            knowledge_base_id=kb_id,
            external_id="obs-external-id-123",
            connection_id="conn-1",
            knowledge_base_name="MyKB",
        )

    monkeypatch.setattr(provider, "_load_connection_config", fake_load_connection)
    monkeypatch.setattr(provider, "_load_kb_reference", fake_load_kb_reference)
    monkeypatch.setattr(provider, "_merge_auth_headers", lambda conn: None)

    ir_node = _make_ir_node(kb_ids=["kb-001"])
    result = asyncio.run(provider.get_kb_config(ir_node))

    kbs = result["knowledge_bases"]
    assert len(kbs) == 1
    # 使用 OBS reference 中的 external_id，而非 kb_id
    assert kbs[0]["external_id"] == "obs-external-id-123"
    assert kbs[0]["knowledge_base_name"] == "MyKB"
