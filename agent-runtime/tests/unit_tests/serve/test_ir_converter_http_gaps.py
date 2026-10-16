# coding: utf-8
"""ir_converter EI.http 缺口修复（G1–G5）单元测试。

覆盖：
1. _remap_http_inputs_schema：query→query_parameters 改名（G1）、userFields 平铺顶层（G2）、
   configs.auth 并入两货架（G4）、保留键避让、用户行优先于 auth、非 dict 透传
2. _pythonize_json_literals：裸 true/false/null 改写（G3）、引号串内内容不受影响、转义引号安全
3. _parse_exception_config：exceptionEnable/exceptionSuppression 合成 fallback（G5）、
   handleType 大小写归一（历史 .lower() 死路径修复）、HTTP outputs_schema 置空、
   默认输出 snake→camel 别名、非法 JSON 回退、未开启异常 → None
4. MR 检视意见轮（2026-09-17）：单引号串/{{占位符}}内裸词保护（#2）、
   query_parameters 合并不重置与幂等（#4）、异常合成仅限 EI.http（#5）

运行方式：
    cd agent-runtime
    pytest tests/unit_tests/serve/test_ir_converter_http_gaps.py -v
"""

# pylint: disable=protected-access  # 单测需直接访问 wrapper 内部成员 _exception_config/_recover_or_raise

import ast

import pytest

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
        "userFields": {"query_parameters": "evil", "query": "evil2", "uid": "1"},
    }
    out = _remap_http_inputs_schema(schema, {})
    assert out["query_parameters"] == {}  # 用户字段不得覆盖组件读取通道
    assert "query" not in out  # 检视意见 #4：query 同属保留键，告警跳过而非平铺
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


def test_synthesize_empty_suppression_string_still_synthesizes():
    # 默认输出编辑器直绑 exceptionSuppression：用户清空内容存 ''，语义是
    # "开启异常处理 + 空默认输出"，不得按未配置回退 interrupt
    cfg = _parse_exception_config(_http_node(suppression=""))
    assert cfg is not None
    assert cfg.handle_type == "defaultOutputs"
    assert cfg.default_outputs == {}


def test_synthesize_bad_json_falls_back_empty():
    cfg = _parse_exception_config(_http_node(suppression="{not json"))
    assert cfg is not None
    assert cfg.handle_type == "defaultOutputs"
    assert cfg.default_outputs == {}


@pytest.mark.parametrize("suppression", ['[1, 2]', '"text"', "123", "null"])
def test_synthesize_non_object_json_falls_back_empty(suppression):
    # 合法 JSON 但非对象：异常恢复按 dict 消费（_merge_dicts .items()），
    # 透传会 AttributeError 导致恢复失败，须回退空默认输出
    cfg = _parse_exception_config(_http_node(suppression=suppression))
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


# ─── MR 检视意见 #1：单组件调试路径同样需要 inputs 重排 ────────────────


@pytest.mark.asyncio
async def test_create_single_component_http_inputs_remapped(monkeypatch):
    """单节点调试路径返回的 inputs_schema 必须与注册路径一样重排。

    create_single_component 需要与 _add_component 注册路径一样经过
    _remap_http_inputs_schema（G1/G2/G4），否则单节点调试时 query/用户参数/
    鉴权全部无法按组件预期读取。
    """
    from jiuwen.serve.controllers.execution.ir_converter import IRConverter

    node = {
        "id": "node_http_1",
        "type": "EI.http",
        "name": "HTTP请求_1",
        "inputs": {
            "query": {"page": "1"},
            "headers": {"X-A": "1"},
            "userFields": {"uid": "42"},
        },
        "configs": {
            "auth": {
                "scope": "SERVICE",
                "headers": {"X-Api-Key": "secret123"},
                "query": {},
            },
        },
    }
    ir_data = {
        "workflowId": "wf_test",
        "workflowVersion": "0.6.0",
        "components": [node],
        "connections": [],
    }

    async def fake_create_component(n, global_model, **kwargs):
        return object(), "EI.http", n.get("configs") or {}

    monkeypatch.setattr(
        IRConverter, "_create_component", staticmethod(fake_create_component)
    )
    info = await IRConverter.create_single_component(ir_data, "node_http_1")
    schema = info.inputs_schema
    # G1：query → query_parameters
    assert schema["query_parameters"] == {"page": "1"}
    assert "query" not in schema
    # G2：userFields 平铺顶层
    assert schema["uid"] == "42"
    assert "userFields" not in schema
    # G4：auth 并入 headers 货架
    assert schema["headers"]["X-Api-Key"] == "secret123"


# ─── MR 检视意见（2026-09-20 轮）#3：单节点调试路径的异常处理合成 ────────


@pytest.mark.asyncio
async def test_create_single_component_http_exception_process_synthesized(monkeypatch):
    """单节点调试返回的 configs 必须含合成的 exceptionProcess。

    调试 wrapper 只消费 configs.exceptionProcess（空则 _recover_or_raise 直接
    抛错），注册路径经 _parse_exception_config 从 exceptionEnable/
    exceptionSuppression 合成；不对齐则 HTTP 单节点调试开启异常处理不走
    defaultOutputs 恢复，与试运行行为不一致。
    """
    from jiuwen.serve.controllers.execution.ir_converter import IRConverter

    def _ir(configs):
        node = {
            "id": "node_http_1",
            "type": "EI.http",
            "name": "HTTP请求_1",
            "inputs": {},
            "configs": configs,
        }
        return {
            "workflowId": "wf_test",
            "workflowVersion": "0.6.0",
            "components": [node],
            "connections": [],
        }

    async def fake_create_component(n, global_model, **kwargs):
        return object(), "EI.http", n.get("configs") or {}

    monkeypatch.setattr(
        IRConverter, "_create_component", staticmethod(fake_create_component)
    )

    # 开启异常处理 → 合成 defaultOutputs（默认输出键走 snake→camel 别名）
    info = await IRConverter.create_single_component(
        _ir(
            {
                "exceptionEnable": True,
                "exceptionSuppression": '{"body":"fallback","status_code":0}',
            }
        ),
        "node_http_1",
    )
    ep = info.configs["exceptionProcess"]
    assert ep["handleType"] == "defaultOutputs"
    assert ep["defaultOutputs"] == {"body": "fallback", "statusCode": 0}

    # 未开启 → 不合成（wrapper 得 None，保持抛错语义）
    info = await IRConverter.create_single_component(
        _ir({"exceptionEnable": False}), "node_http_1"
    )
    assert "exceptionProcess" not in info.configs

    # configs 已有 exceptionProcess（API 直写形态）→ 不覆盖
    info = await IRConverter.create_single_component(
        _ir({"exceptionProcess": {"handleType": "errorbranch"}}), "node_http_1"
    )
    assert info.configs["exceptionProcess"] == {"handleType": "errorbranch"}


def test_wrapper_http_exception_config_outputs_schema_empty():
    """wrapper 异常配置对 EI.http 置空 outputs_schema，对齐注册路径。

    HTTP 输出扁平、与 inputs 货架无关；若拿重排后的 inputs_schema 当合并
    base，恢复输出会混入 query_parameters/headers 等货架键。
    """
    from jiuwen.extension.wrapper.single_component_debug_wrapper import (
        SingleComponentDebugWrapper,
    )
    from jiuwen.serve.controllers.execution.ir_converter import SingleComponentInfo

    def _wrapper(node_type, configs, inputs_schema):
        return SingleComponentDebugWrapper(
            SingleComponentInfo(
                component=object(),
                node_id="n1",
                node_type=node_type,
                configs=configs,
                inputs_schema=inputs_schema,
                node_name="测试",
            ),
            execution_id="exec_test",
        )

    configs = {
        "exceptionProcess": {
            "handleType": "defaultOutputs",
            "defaultOutputs": {"body": "fallback"},
        }
    }
    shelf = {"query_parameters": {"page": "1"}, "headers": {}}
    cfg = _wrapper("EI.http", configs, shelf)._exception_config
    assert cfg is not None
    assert cfg.outputs_schema == {}

    # 非 HTTP 节点保持既有行为（inputs_schema 作合并 base）
    cfg = _wrapper("jiuwen.code", configs, shelf)._exception_config
    assert cfg.outputs_schema == shelf


@pytest.mark.asyncio
async def test_wrapper_recover_dispatches_default_outputs():
    """_recover_or_raise 必须命中驼峰常量 "defaultOutputs"。

    历史 .lower() 把它变成 "defaultoutputs" 后与常量永不相等，默认输出恢复
    静默退化为 interrupt 抛错（errorbranch/interrupt 全小写不受影响，唯独
    defaultOutputs 被杀）——既有平台缺陷，HTTP 单节点调试接入异常合成后暴露。
    """
    from jiuwen.extension.wrapper.single_component_debug_wrapper import (
        SingleComponentDebugWrapper,
    )
    from jiuwen.serve.controllers.execution.ir_converter import SingleComponentInfo

    wrapper = SingleComponentDebugWrapper(
        SingleComponentInfo(
            component=object(),
            node_id="n1",
            node_type="EI.http",
            configs={
                "exceptionProcess": {
                    "handleType": "defaultOutputs",
                    "defaultOutputs": {"body": "fallback"},
                }
            },
            inputs_schema={"query_parameters": {}},
            node_name="测试",
        ),
        execution_id="exec_test",
    )
    events = [
        sd
        async for sd in wrapper._recover_or_raise(RuntimeError("boom"), "exec_test")
    ]
    assert len(events) == 1
    outputs = events[0].data["outputs"]
    assert outputs["isSuccess"] is False
    assert outputs["body"] == "fallback"
    # HTTP 恢复输出不得混入 inputs 货架键
    assert "query_parameters" not in outputs


# ─── MR 检视意见 #2/#4/#5（2026-09-17 轮）─────────────────────────────


def test_pythonize_protects_single_quoted_content():
    # #2：body 允许 Python 字面量形态（组件走 ast.literal_eval），单引号串内不得改写
    out = _pythonize_json_literals("{'msg': 'true story', 'ok': true}")
    assert out == "{'msg': 'true story', 'ok': True}"
    assert ast.literal_eval(out) == {"msg": "true story", "ok": True}


def test_pythonize_protects_placeholder_bare_words():
    # #2：{{true}}/{{null}} 内裸词是变量名，改写成 {{True}} 后无法按原始 key
    # 解析 → body 解析失败被组件静默丢弃
    tmpl = '{"a": {{true}}, "b": {{null}}, "c": "x{{false}}y"}'
    assert _pythonize_json_literals(tmpl) == tmpl


def test_remap_merges_existing_query_parameters():
    # #4：schema 已含 query_parameters 时合并而非重置；同名键 query（IR 原生）优先
    schema = {
        "query": {"page": "1", "k": "new"},
        "query_parameters": {"legacy": "v", "k": "old"},
        "headers": {},
        "userFields": {},
    }
    out = _remap_http_inputs_schema(schema, {})
    assert out["query_parameters"] == {"legacy": "v", "page": "1", "k": "new"}


def test_remap_idempotent():
    # #4：函数被重复调用不得丢货架值
    schema = {"query": {"page": "1"}, "headers": {"X-A": "1"}, "userFields": {"uid": "42"}}
    configs = {
        "auth": {
            "scope": "SERVICE",
            "headers": {"X-Api-Key": "s"},
            "query": {"api_key": "k"},
        }
    }
    once = _remap_http_inputs_schema(schema, configs)
    twice = _remap_http_inputs_schema(once, configs)
    assert twice == once


def test_synthesize_skipped_for_non_http_node():
    # #5：非 HTTP 节点缺 exceptionProcess 时保持既有语义（不合成默认输出），
    # 迁移不改变 HTTP 以外节点的异常行为
    node = {
        "type": "jiuwen.code",
        "id": "n2",
        "configs": {
            "exceptionEnable": True,
            "exceptionSuppression": '{"result": "x"}',
        },
    }
    assert _parse_exception_config(node) is None


# ─── MR 检视意见（2026-09-20 第七轮）：auth 子字段形态甄别 / dict suppression 保留 ───


def test_remap_auth_non_dict_subfields_skipped():
    """auth.headers/auth.query 真值非 dict 不得 AttributeError 打断 IR 转换。

    API 直写/导入 DSL 可能带入字符串、列表等畸形形态：`or {}` 只挡 falsy，
    真值非 dict 直接 .items() 抛 AttributeError 使注册与单节点调试整体崩溃。
    修复后仅跳过畸形子字段合并并告警。
    """
    schema = {"query": {"page": "1"}, "headers": {"X-A": "1"}, "userFields": {}}
    configs = {
        "auth": {"scope": "SERVICE", "headers": "X-Api-Key: secret", "query": ["k=v"]}
    }
    out = _remap_http_inputs_schema(schema, configs)
    # 畸形子字段被跳过，用户货架原样保留
    assert out["headers"] == {"X-A": "1"}
    assert out["query_parameters"] == {"page": "1"}

    # 混合形态：headers 畸形不影响 query 正常合并
    configs_mixed = {"auth": {"headers": "broken", "query": {"api_key": "k"}}}
    out = _remap_http_inputs_schema(schema, configs_mixed)
    assert out["query_parameters"] == {"page": "1", "api_key": "k"}
    assert out["headers"] == {"X-A": "1"}


def test_synthesize_dict_suppression_preserved():
    """API 直写形态：exceptionSuppression 已是 dict 时不得清空。

    json.loads(dict) 抛 TypeError 被历史 except 捕获后回退空默认输出，
    用户已配置的兜底值被静默丢弃且告警文案误报"非合法 JSON"。
    """
    node = {
        "type": "EI.http",
        "id": "n1",
        "configs": {
            "exceptionEnable": True,
            "exceptionSuppression": {"body": "fallback", "status_code": 0},
        },
    }
    cfg = _parse_exception_config(node)
    assert cfg is not None
    assert cfg.handle_type == "defaultOutputs"
    # snake→camel 别名归一对 dict 形态同样生效
    assert cfg.default_outputs == {"body": "fallback", "statusCode": 0}
