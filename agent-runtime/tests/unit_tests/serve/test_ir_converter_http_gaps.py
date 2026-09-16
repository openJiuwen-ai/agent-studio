# coding: utf-8
"""ir_converter EI.http 缺口修复（G1–G5）单元测试。

覆盖：
1. _remap_http_inputs_schema：query→query_parameters 改名（G1）、userFields 平铺顶层（G2）、
   configs.auth 并入两货架（G4）、保留键避让、用户行优先于 auth、非 dict 透传
2. _pythonize_json_literals：裸 true/false/null 改写（G3）、引号串内内容不受影响、转义引号安全
3. _parse_exception_config：exceptionEnable/exceptionSuppression 合成 fallback（G5）、
   handleType 大小写归一（历史 .lower() 死路径修复）、HTTP outputs_schema 置空、
   默认输出 snake→camel 别名、非法 JSON 回退、未开启异常 → None

运行方式：
    cd agent-runtime
    pytest tests/unit_tests/serve/test_ir_converter_http_gaps.py -v
"""

import ast

from jiuwen.serve.controllers.execution.ir_converter import (
    _parse_exception_config,
    _pythonize_json_literals,
    _remap_http_inputs_schema,
)


# ─── G1/G2/G4：inputs 货架重排 ────────────────────────────────────────


def test_remap_query_renamed_and_userfields_flattened():
    schema = {
        "query": {"page": "1", "city": "${node_start.userFields.city}"},
        "headers": {"X-A": "1"},
        "userFields": {"uid": "42", "token": "${node_start.userFields.token}"},
    }
    out = _remap_http_inputs_schema(schema, {})
    assert out["query_parameters"] == {"page": "1", "city": "${node_start.userFields.city}"}
    assert "query" not in out
    assert out["headers"] == {"X-A": "1"}
    # G2：用户字段平铺到顶层，组件 {{}} 替换才能查到
    assert out["uid"] == "42"
    assert out["token"] == "${node_start.userFields.token}"
    assert "userFields" not in out


def test_remap_auth_merged_into_shelves():
    schema = {"query": {}, "headers": {}, "userFields": {}}
    configs = {
        "auth": {
            "scope": "SERVICE",
            "headers": {"X-API-Key": "secret123"},
            "query": {},
        }
    }
    out = _remap_http_inputs_schema(schema, configs)
    assert out["headers"]["X-API-Key"] == "secret123"
    assert out["query_parameters"] == {}

    configs_query = {
        "auth": {"scope": "SERVICE", "headers": {}, "query": {"api_key": "secret123"}}
    }
    out = _remap_http_inputs_schema(schema, configs_query)
    assert out["query_parameters"]["api_key"] == "secret123"


def test_remap_user_row_wins_over_auth():
    schema = {"query": {}, "headers": {"X-API-Key": "user-value"}, "userFields": {}}
    configs = {"auth": {"headers": {"X-API-Key": "auth-value"}, "query": {}}}
    out = _remap_http_inputs_schema(schema, configs)
    assert out["headers"]["X-API-Key"] == "user-value"


def test_remap_reserved_key_skipped():
    schema = {
        "query": {},
        "headers": {},
        "userFields": {"query_parameters": "evil", "uid": "1"},
    }
    out = _remap_http_inputs_schema(schema, {})
    assert out["query_parameters"] == {}  # 用户字段不得覆盖组件读取通道
    assert out["uid"] == "1"


def test_remap_non_dict_passthrough_and_extra_keys_kept():
    assert _remap_http_inputs_schema(None, {}) is None
    schema = {"query": {}, "headers": {}, "userFields": {}, "systemFields": {"a": 1}}
    out = _remap_http_inputs_schema(schema, {})
    assert out["systemFields"] == {"a": 1}


# ─── G3：body 模板字面量预处理 ────────────────────────────────────────


def test_pythonize_bare_literals():
    out = _pythonize_json_literals(
        '{"enabled": true, "deleted": false, "note": null, "n": 1}'
    )
    assert out == '{"enabled": True, "deleted": False, "note": None, "n": 1}'
    # 预处理后必须能过组件的 ast.literal_eval 门
    assert ast.literal_eval(out) == {
        "enabled": True,
        "deleted": False,
        "note": None,
        "n": 1,
    }


def test_pythonize_protects_quoted_content():
    # 串内单词与带引号的字符串值都不得改写
    out = _pythonize_json_literals('{"msg": "true story", "v": "true", "k": "null"}')
    assert out == '{"msg": "true story", "v": "true", "k": "null"}'


def test_pythonize_protects_escaped_quote_content():
    tmpl = '{"msg": "he said \\"hi\\" true null", "ok": true}'
    out = _pythonize_json_literals(tmpl)
    assert '"he said \\"hi\\" true null"' in out
    assert out.endswith('"ok": True}')


def test_pythonize_non_string_passthrough():
    assert _pythonize_json_literals(None) is None
    assert _pythonize_json_literals(42) == 42


# ─── G5：异常配置合成与归一 ───────────────────────────────────────────


def _http_node(*, enable=True, suppression='{"body":"fallback","status_code":0}'):
    configs = {"exceptionEnable": enable}
    if suppression is not None:
        configs["exceptionSuppression"] = suppression
    return {"type": "EI.http", "id": "n1", "configs": configs}


def test_synthesize_from_enable_suppression():
    cfg = _parse_exception_config(_http_node())
    assert cfg is not None
    # 归一后必须是驼峰规范值，下游 bpmn 才认
    assert cfg.handle_type == "defaultOutputs"
    assert cfg.default_outputs == {"body": "fallback", "statusCode": 0}
    # HTTP 输出扁平，outputs_schema 置空让兜底键原样通过（MCP 同款先例）
    assert cfg.outputs_schema == {}


def test_synthesize_disabled_returns_none():
    assert _parse_exception_config(_http_node(enable=False)) is None


def test_synthesize_missing_suppression_returns_none():
    assert _parse_exception_config(_http_node(suppression=None)) is None


def test_synthesize_bad_json_falls_back_empty():
    cfg = _parse_exception_config(_http_node(suppression="{not json"))
    assert cfg is not None
    assert cfg.handle_type == "defaultOutputs"
    assert cfg.default_outputs == {}


def test_handletype_case_normalization():
    def _ep_node(handle_type):
        return {
            "type": "jiuwen.code",
            "configs": {"exceptionProcess": {"handleType": handle_type}},
        }

    assert _parse_exception_config(_ep_node("defaultOutputs")).handle_type == "defaultOutputs"
    assert _parse_exception_config(_ep_node("default_outputs")).handle_type == "defaultOutputs"
    # 历史 .lower() 存出的小写形态现在也能归一回驼峰
    assert _parse_exception_config(_ep_node("defaultoutputs")).handle_type == "defaultOutputs"
    assert _parse_exception_config(_ep_node("nonsense")).handle_type == "interrupt"


def test_mcp_outputs_schema_still_empty_regression():
    node = {
        "type": "jiuwen.mcp",
        "configs": {"exceptionProcess": {"handleType": "interrupt"}},
        "outputs": {"result": {"type": "array"}},
    }
    cfg = _parse_exception_config(node)
    assert cfg.outputs_schema == {}


def test_non_http_outputs_schema_still_converted():
    node = {
        "type": "jiuwen.code",
        "configs": {"exceptionProcess": {"handleType": "interrupt"}},
        "outputs": {"result": "plain"},
    }
    cfg = _parse_exception_config(node)
    assert cfg.outputs_schema == {"result": "plain"}
