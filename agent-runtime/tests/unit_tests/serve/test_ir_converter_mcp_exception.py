# coding: utf-8
"""ir_converter._parse_exception_config 单元测试 — MCP 异常处理相关。

重点覆盖：
1. MCP 节点 outputs_schema 置空（Bug #4 修复）
2. Plugin / Code 等非 MCP 节点走正常 _convert_schema
3. 无 exceptionProcess 时返回 None
4. timeout / retryTimes 边界值

运行方式：
    cd agent-runtime
    pytest tests/unit_tests/serve/test_ir_converter_mcp_exception.py -v
"""

from jiuwen.serve.controllers.execution.ir_converter import _parse_exception_config


# ─── helpers ──────────────────────────────────────────────────────────


def _make_node(
    *,
    node_type="jiuwen.mcp",
    exception_process=None,
    outputs=None,
):
    """构造最小化 IR node dict。"""
    node = {"type": node_type, "configs": {}}
    if exception_process is not None:
        node["configs"]["exceptionProcess"] = exception_process
    if outputs is not None:
        node["outputs"] = outputs
    return node


def _make_ep(
    *,
    handle_type="interrupt",
    timeout=60,
    retry_times=0,
    default_outputs=None,
):
    """构造最小化 exceptionProcess dict。"""
    ep = {
        "handleType": handle_type,
        "timeout": timeout,
        "retryTimes": retry_times,
    }
    if default_outputs is not None:
        ep["defaultOutputs"] = default_outputs
    return ep


# ─── 无 exceptionProcess → None ─────────────────────────────────────


def test_no_configs():
    node = {"type": "jiuwen.mcp"}
    assert _parse_exception_config(node) is None


def test_configs_without_exception_process():
    node = {"type": "jiuwen.mcp", "configs": {"other_field": "value"}}
    assert _parse_exception_config(node) is None


def test_exception_process_is_none():
    node = _make_node(exception_process=None)
    assert _parse_exception_config(node) is None


def test_exception_process_is_empty_dict():
    """空 dict 视为 falsy → 返回 None。"""
    node = _make_node(exception_process={})
    assert _parse_exception_config(node) is None


# ─── MCP 节点 outputs_schema 置空（Bug #4 核心）─────────────────────


def test_mcp_node_outputs_schema_is_empty():
    """MCP 节点的 outputs_schema 必须置空，不使用 _convert_schema。"""
    node = _make_node(
        node_type="jiuwen.mcp",
        exception_process=_make_ep(handle_type="defaultOutputs"),
        outputs={"content": {"type": "array"}, "isError": {"type": "boolean"}},
    )
    config = _parse_exception_config(node)
    assert config is not None
    assert config.outputs_schema == {}


def test_flow_mcp_node_outputs_schema_is_empty():
    """jiuwen.flowMcp 同样置空。"""
    node = _make_node(
        node_type="jiuwen.flowMcp",
        exception_process=_make_ep(handle_type="errorbranch"),
        outputs={"result": "${node.userFields.result}"},
    )
    config = _parse_exception_config(node)
    assert config is not None
    assert config.outputs_schema == {}


def test_mcp_no_outputs_still_empty_schema():
    """MCP 节点没有 outputs 字段时，outputs_schema 仍然是 {}。"""
    node = _make_node(
        node_type="jiuwen.mcp",
        exception_process=_make_ep(),
    )
    config = _parse_exception_config(node)
    assert config.outputs_schema == {}


# ─── 非 MCP 节点走正常 _convert_schema ──────────────────────────────


def test_plugin_node_outputs_schema_not_empty():
    """Plugin 节点的 outputs_schema 不应为空（由 _convert_schema 生成）。"""
    node = _make_node(
        node_type="jiuwen.plugin",
        exception_process=_make_ep(handle_type="defaultOutputs"),
        outputs={"result": {"type": "string"}},
    )
    config = _parse_exception_config(node)
    assert config is not None
    assert config.outputs_schema != {}


def test_code_node_outputs_schema():
    node = _make_node(
        node_type="jiuwen.code",
        exception_process=_make_ep(),
        outputs={"output": {"type": "string"}},
    )
    config = _parse_exception_config(node)
    assert config is not None
    assert config.outputs_schema != {}


def test_llm_node_outputs_schema():
    node = _make_node(
        node_type="jiuwen.llm",
        exception_process=_make_ep(),
        outputs={"text": {"type": "string"}},
    )
    config = _parse_exception_config(node)
    assert config is not None
    assert config.outputs_schema != {}


# ─── handleType 解析 ─────────────────────────────────────────────────


def test_handle_type_default_is_interrupt():
    """handleType 缺省时默认 interrupt。"""
    node = _make_node(
        exception_process={"timeout": 60, "retryTimes": 0},
    )
    config = _parse_exception_config(node)
    assert config.handle_type == "interrupt"


def test_handle_type_errorbranch_lowercased():
    node = _make_node(exception_process=_make_ep(handle_type="ErrorBranch"))
    config = _parse_exception_config(node)
    assert config.handle_type == "errorbranch"


def test_handle_type_default_outputs_lowercased():
    node = _make_node(exception_process=_make_ep(handle_type="DefaultOutputs"))
    config = _parse_exception_config(node)
    assert config.handle_type == "defaultoutputs"


# ─── timeout / retryTimes 边界值 ─────────────────────────────────────


def test_normal_timeout():
    node = _make_node(exception_process=_make_ep(timeout=300))
    config = _parse_exception_config(node)
    assert config.timeout == 300


def test_negative_timeout_falls_back_to_default():
    node = _make_node(exception_process=_make_ep(timeout=-1))
    config = _parse_exception_config(node)
    from jiuwen.orchestration.flow.constant import DEFAULT_EXECUTION_NODE_TIMEOUT
    assert config.timeout == DEFAULT_EXECUTION_NODE_TIMEOUT


def test_string_timeout_falls_back_to_default():
    node = _make_node(exception_process=_make_ep(timeout="abc"))
    config = _parse_exception_config(node)
    from jiuwen.orchestration.flow.constant import DEFAULT_EXECUTION_NODE_TIMEOUT
    assert config.timeout == DEFAULT_EXECUTION_NODE_TIMEOUT


def test_zero_timeout_is_valid():
    """timeout=0 是合法值（不触发 fallback）。"""
    node = _make_node(exception_process=_make_ep(timeout=0))
    config = _parse_exception_config(node)
    assert config.timeout == 0


def test_normal_retry():
    node = _make_node(exception_process=_make_ep(retry_times=3))
    config = _parse_exception_config(node)
    assert config.retry_times == 3


def test_negative_retry_falls_back_to_zero():
    node = _make_node(exception_process=_make_ep(retry_times=-1))
    config = _parse_exception_config(node)
    assert config.retry_times == 0


def test_string_retry_falls_back_to_zero():
    node = _make_node(exception_process=_make_ep(retry_times="two"))
    config = _parse_exception_config(node)
    assert config.retry_times == 0


# ─── defaultOutputs 传递 ─────────────────────────────────────────────


def test_default_outputs_passed_through():
    defaults = {"content": [{"type": "text", "text": "默认"}], "isError": True}
    node = _make_node(
        node_type="jiuwen.mcp",
        exception_process=_make_ep(
            handle_type="defaultOutputs",
            default_outputs=defaults,
        ),
    )
    config = _parse_exception_config(node)
    assert config.default_outputs == defaults


def test_missing_default_outputs_defaults_to_empty():
    node = _make_node(exception_process=_make_ep())
    config = _parse_exception_config(node)
    assert config.default_outputs == {}


# ─── _node_type 记录 ─────────────────────────────────────────────────


def test_node_type_recorded():
    """exception_config._node_type 记录节点类型，供 handler 判断。"""
    node = _make_node(
        node_type="jiuwen.mcp",
        exception_process=_make_ep(),
    )
    config = _parse_exception_config(node)
    assert getattr(config, "_node_type") == "jiuwen.mcp"


def test_plugin_node_type_recorded():
    node = _make_node(
        node_type="jiuwen.plugin",
        exception_process=_make_ep(),
    )
    config = _parse_exception_config(node)
    assert getattr(config, "_node_type") == "jiuwen.plugin"
