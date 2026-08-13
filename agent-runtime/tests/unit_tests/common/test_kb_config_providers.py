# pylint: disable=protected-access  # 单元测试需直接验证内部方法行为
import json

from agent_runtime.common import kb_config_providers
from agent_runtime.common.kb_config_providers import (
    KBConnectionConfig,
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
