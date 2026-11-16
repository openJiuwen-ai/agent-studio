# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""FEAT-093 插件动态鉴权：restful wrapper {{inputs.*}}/{{memory.*}} 绑定解析测试。

机制：react 执行器把请求级全局变量/记忆变量写入 RequestContext；插件
工具的动态鉴权头（Headers 位置参数）绑定模板（inputParameters，
react 链路只认请求级映射，不回退 card 自身配置——card 进程级共享、
配置可能来自首个注册者即别的 agent）解析出值并入 inputs，经
RequestParamsCreator 的 Headers 路由注入出站请求头。工作流链路不写
请求上下文，互不重叠。绑定值对 inputs 已有同名值（LLM 工具调用参数，
可能为编造值）强制覆盖——与环境变量通道同语义。
"""
# pylint: disable=protected-access  # 单测需注入/调用内部属性与方法（仓库既有惯例）

from types import SimpleNamespace

from jiuwen.extension.wrapper.restful_api_new import RestfulApiToolNew


def _create_wrapper(param_specs):
    """构造跳过 __init__ 的 wrapper（只设 _merge_dynamic_credential_parameters 依赖的属性）。"""
    wrapper = RestfulApiToolNew.__new__(RestfulApiToolNew)
    wrapper._id = "plugin-1"
    wrapper._name = "插件一"
    wrapper._input_parameters = {}
    wrapper._params = [
        SimpleNamespace(name=name, method=method)
        for name, method in param_specs
    ]
    return wrapper


def _bind(global_variables=None, memory_variables=None, request_templates=None):
    from agent_runtime.context import request_context as rc

    original_globals = rc._request_ctx.get().global_variables
    original_memory = rc._request_ctx.get().memory_variables
    original_templates = rc._request_ctx.get().mcp_input_parameters
    rc._request_ctx.get().global_variables = global_variables or {}
    rc._request_ctx.get().memory_variables = memory_variables or {}
    rc._request_ctx.get().mcp_input_parameters = request_templates or {}

    def restore():
        rc._request_ctx.get().global_variables = original_globals
        rc._request_ctx.get().memory_variables = original_memory
        rc._request_ctx.get().mcp_input_parameters = original_templates

    return restore


class TestPluginDynamicCredentialMerge:

    @staticmethod
    def test_inputs_template_resolved_to_headers_param():
        """{{inputs.*}} 绑定 → Headers 位置参数值并入 inputs。"""
        wrapper = _create_wrapper([("Authorization", "Headers"), ("query", "Body")])
        restore = _bind(
            global_variables={"userToken": "Bearer plugin-tok"},
            request_templates={"plugin-1": {"Authorization": "{{inputs.userToken}}"}},
        )
        try:
            inputs = {"query": "hi"}
            wrapper._merge_input_parameters(inputs)
        finally:
            restore()
        assert inputs.get("Authorization") == "Bearer plugin-tok"

    @staticmethod
    def test_memory_template_resolved():
        """{{memory.*}} 绑定 → 记忆变量值并入 Headers 参数。"""
        wrapper = _create_wrapper([("Authorization", "Headers")])
        restore = _bind(
            global_variables={"any": "source"},
            memory_variables={"memToken": "123"},
            request_templates={"plugin-1": {"Authorization": "{{memory.memToken}}"}},
        )
        try:
            inputs = {}
            wrapper._merge_input_parameters(inputs)
        finally:
            restore()
        assert inputs.get("Authorization") == "123"

    @staticmethod
    def test_non_headers_param_not_injected():
        """非 Headers 位置参数的 {{inputs.*}} 引用不注入（维持环境变量通道语义）。"""
        wrapper = _create_wrapper([("query", "Body")])
        restore = _bind(
            global_variables={"userToken": "tok"},
            request_templates={"plugin-1": {"query": "{{inputs.userToken}}"}},
        )
        try:
            inputs = {}
            wrapper._merge_input_parameters(inputs)
        finally:
            restore()
        assert "query" not in inputs or inputs.get("query") != "tok"

    @staticmethod
    def test_bound_value_overwrites_llm_given():
        """绑定值强制覆盖 inputs 已有同名值（LLM 编造值必须被覆盖）。

        Java 侧 IrAdapter 把动态头 target_name 下发进工具 schema，LLM
        工具调用可能编造同名参数值；与环境变量通道（LLM 可能生成推测值，
        必须被覆盖）同语义——绑定模板解析成功即覆盖。
        """
        wrapper = _create_wrapper([("Authorization", "Headers")])
        restore = _bind(
            global_variables={"userToken": "bound"},
            request_templates={"plugin-1": {"Authorization": "{{inputs.userToken}}"}},
        )
        try:
            inputs = {"Authorization": "llm-given"}
            wrapper._merge_input_parameters(inputs)
        finally:
            restore()
        assert inputs.get("Authorization") == "bound"

    @staticmethod
    def test_request_level_template_wins():
        """请求级模板优先（跨 agent 共享 card 防污染；id 命中）。"""
        wrapper = _create_wrapper([("Authorization", "Headers")])
        wrapper._input_parameters = {"Authorization": "{{inputs.otherVar}}"}
        restore = _bind(
            global_variables={"userToken": "request-level"},
            request_templates={"plugin-1": {"Authorization": "{{inputs.userToken}}"}},
        )
        try:
            inputs = {}
            wrapper._merge_input_parameters(inputs)
        finally:
            restore()
        assert inputs.get("Authorization") == "request-level"

    @staticmethod
    def test_request_level_template_by_name_wins():
        """请求级模板按 name 命中（card.id 优先 name 的另一形态）。"""
        wrapper = _create_wrapper([("Authorization", "Headers")])
        restore = _bind(
            global_variables={"userToken": "by-name"},
            request_templates={"插件一": {"Authorization": "{{inputs.userToken}}"}},
        )
        try:
            inputs = {}
            wrapper._merge_input_parameters(inputs)
        finally:
            restore()
        assert inputs.get("Authorization") == "by-name"

    @staticmethod
    def test_invalid_value_rejected():
        """非法头值（中文/控制字符）WARNING 后不注入。"""
        for bad in ("Bearer 中文", "tok\r\nen"):
            wrapper = _create_wrapper([("Authorization", "Headers")])
            restore = _bind(
                global_variables={"userToken": bad},
                request_templates={"plugin-1": {"Authorization": "{{inputs.userToken}}"}},
            )
            try:
                inputs = {}
                wrapper._merge_input_parameters(inputs)
            finally:
                restore()
            assert "Authorization" not in inputs, bad

    @staticmethod
    def test_client_template_not_applied_in_react_chain():
        """react 链路（请求级值源存在）映射无本插件条目 → 不回退 card 自身
        input_parameters（跨 agent 凭证污染防护）。

        card（插件工具实例）进程级共享且首个注册者的配置生效——card 的
        input_parameters 可能来自别的 agent 的 IR；本次 agent 未配置该
        插件的绑定（映射无条目）时套用旧模板会把本次请求的变量按他
        agent 的绑定注入出站头。
        """
        wrapper = _create_wrapper([("Authorization", "Headers")])
        wrapper._input_parameters = {"Authorization": "{{inputs.userToken}}"}
        restore = _bind(global_variables={"userToken": "client-level-tok"})
        try:
            inputs = {}
            wrapper._merge_input_parameters(inputs)
        finally:
            restore()
        assert "Authorization" not in inputs

    @staticmethod
    def test_workflow_path_untouched_without_ctx():
        """工作流链路（请求上下文未写）零合并。"""
        wrapper = _create_wrapper([("Authorization", "Headers")])
        wrapper._input_parameters = {"Authorization": "{{inputs.userToken}}"}
        restore = _bind()
        try:
            inputs = {}
            wrapper._merge_input_parameters(inputs)
        finally:
            restore()
        assert "Authorization" not in inputs
