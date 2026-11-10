# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
CustomPluginTool -- 自定义插件工具实现。

将 ``PluginBase`` 子类包装为 ``Tool``，注册到
``Runner.resource_mgr``，使智能体和工作流能像调用 RESTful API 一样
调用自定义插件。

核心组件：
1. CustomPluginCard: 自定义插件 Card，携带 component_type 等元信息
2. CustomPluginTool: 继承 Tool，委托 PluginBase 实例执行
3. convert_ir_to_custom_card: IR 配置 → CustomPluginCard
4. create_plugin_tool: 统一入口，按 callMode 分流 custom / http_api
"""

import json
from typing import Any, AsyncIterator, Dict, List, Optional

from pydantic import Field

from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.insight.manager import TraceManager
from jiuwen.insight.utils import get_instance_info
from jiuwen.orchestration.flow.component_class_pool import component_class_pool
from jiuwen.plugin.models.param import Param
from openjiuwen.core.foundation.tool import Tool
from openjiuwen.core.foundation.tool.base import ToolCard

# 自定义插件执行错误码（105001，落在插件错误码区间 105000-105999）
_CUSTOM_PLUGIN_ERROR_CODE = 105001


async def _emit_plugin_event(trace_manager, method_name: str, *args):
    """安全发射插件遥测事件：manager 为 None 时跳过，handler 异常只告警。

    对齐 stream_post_utils.emit_trace_event 的隔离语义——insight 层
    _trace_event 直接调用 handler 并传播异常，遥测事件若与业务逻辑共用
    try 块，任一 handler 抛错会把成功的插件调用误判进业务失败分支；
    此处统一兜底，遥测失败不改变调用方业务语义。
    """
    if trace_manager is None:
        return
    try:
        await getattr(trace_manager, method_name)(*args)
    except Exception as e:
        logger.warning(
            "CustomPlugin trace event %s failed: %s: %s",
            method_name,
            type(e).__name__,
            e,
        )


class CustomPluginCard(ToolCard):
    """自定义插件 Card。

    由 ``convert_ir_to_custom_card`` 从 IR 配置创建，用于初始化
    ``CustomPluginTool``。

    Attributes:
        params: 输入参数定义列表（由 IR arguments 反序列化）。
        component_type: 组件类型标识，用于在 ``ComponentClassPool`` 中
            查找插件类。
        response: 输出参数定义列表。
        plugin_name: 插件名称。
        plugin_desc: 插件描述。
        related_info: 相关信息（如 logo）。
        input_parameters: 输入参数映射。
    """

    model_config = {"arbitrary_types_allowed": True}

    params: List[Param] = Field(default_factory=list, description="输入参数列表")
    component_type: str = Field(default="", description="组件类型标识")
    response: List[Param] = Field(default_factory=list, description="输出参数列表")
    plugin_name: str = Field(default="", description="插件名称")
    plugin_desc: str = Field(default="", description="插件描述")
    related_info: Optional[Dict[str, Any]] = Field(
        default=None, description="相关信息"
    )
    input_parameters: Dict[str, str] = Field(
        default_factory=dict, description="输入参数映射"
    )


class CustomPluginTool(Tool):
    """自定义插件工具。

    继承 ``Tool``，在初始化时通过 ``ComponentClassPool`` 创建插件
    实例，并将 ``invoke`` / ``stream`` 委托给该实例。

    输出格式与 ``RestfulApiToolNew`` 对齐：
    ``{"data": <result>, "errCode": 0, "errMessage": ""}``，
    使 ``FlowCustomApi._format_api_outputs`` 可复用 HTTP 插件输出解析逻辑。
    """

    def __init__(self, card: CustomPluginCard):
        super().__init__(card)
        self._card: CustomPluginCard = card
        self._name: str = card.name
        self._description: str = card.description
        self._id: str = card.id
        self._params: List[Param] = card.params
        self._component_type: str = card.component_type
        self._response: List[Param] = card.response

        if not self._component_type:
            raise ValueError(
                "CustomPluginTool requires a non-empty component_type in card"
            )

        self._plugin_instance = component_class_pool.create_component_instance(
            self._component_type, params=self._params
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def id(self) -> str:
        return self._id

    @property
    def params(self) -> List[Param]:
        return self._params

    @property
    def component_type(self) -> str:
        return self._component_type

    @property
    def response(self) -> List[Param]:
        return self._response

    async def invoke(self, inputs: dict, **kwargs) -> dict:
        """Tool 接口：非流式调用（委托 ainvoke）"""
        return await self.ainvoke(inputs, **kwargs)

    async def ainvoke(self, inputs: dict, **kwargs) -> dict:
        """非流式执行：委托 PluginBase.invoke，包装为统一输出格式"""
        # 与 RestfulApiToolNew/MCP 包装器同构：规划/工具模式下 ainvoke 收到
        # runtime_data 透传的 trace_handlers 时经 TraceManager 发射插件事件。
        # 遥测与业务隔离（对齐 plan_execute_mode StepExecute 的 safely/emit
        # 范式，见 stream_post_utils.create_trace_manager_safely /
        # emit_trace_event）：manager 构造失败或任一 handler 抛错只告警，
        # 不影响插件调用与返回值；业务失败（非 0 errCode）按 REST 包装器
        # 口径发 on_plugin_error 而非 on_plugin_end。trace_handlers 在此
        # 弹出，不泄入插件实现入参。
        trace_handlers = kwargs.pop("trace_handlers", None)
        trace_manager = self._create_tracer_manager(trace_handlers)
        try:
            await _emit_plugin_event(trace_manager, "on_plugin_start", inputs)
            result = await self._plugin_instance.invoke(inputs, **kwargs)
            if isinstance(result, dict) and "errCode" in result:
                exec_result = result
            else:
                exec_result = {"data": result, "errCode": 0, "errMessage": ""}
            if exec_result.get("errCode", 0) != 0:
                await _emit_plugin_event(
                    trace_manager,
                    "on_plugin_error",
                    Exception(exec_result.get("errMessage") or "plugin error"),
                )
            else:
                await _emit_plugin_event(trace_manager, "on_plugin_end", exec_result)
            return exec_result
        except Exception as e:
            await _emit_plugin_event(trace_manager, "on_plugin_error", e)
            logger.error(
                "CustomPlugin[%s] invoke error: %s: %s",
                self._component_type,
                type(e).__name__,
                e,
            )
            return {
                "data": None,
                "errCode": _CUSTOM_PLUGIN_ERROR_CODE,
                "errMessage": f"Custom plugin execution failed: {type(e).__name__}",
            }

    def _create_tracer_manager(self, trace_handlers):
        """创建追踪管理器（与 mcp_tool_wrapper 同构）。

        构造失败只告警并返回 None（遥测停用），异常不外传——对齐
        create_trace_manager_safely 的语义，遥测故障不变业务故障。
        instance_info 显式排除对象值成员（插件实例 / 卡片）——
        get_instance_info 逐键整拷 __dict__，黑名单只按顶层键精确
        匹配，放行 _plugin_instance 会把插件内部状态整对象带进遥测。
        """
        try:
            return TraceManager.generate_manager(
                trace_handlers,
                get_instance_info(
                    self, blacklist=["auth", "headers", "_plugin_instance", "_card"]
                ),
            )
        except Exception as e:
            logger.warning(
                "CustomPlugin[%s] tracer manager init failed: %s: %s",
                self._component_type,
                type(e).__name__,
                e,
            )
            return None

    def stream(self, inputs: dict, **kwargs) -> AsyncIterator[str]:
        """Tool 接口：流式调用（委托 astream）"""
        return self.astream(inputs, **kwargs)

    async def astream(self, inputs: dict, **kwargs) -> AsyncIterator[str]:
        """流式执行：委托 PluginBase.stream，逐条 yield"""
        try:
            async for chunk in self._plugin_instance.stream(inputs, **kwargs):
                if isinstance(chunk, str):
                    yield chunk
                else:
                    yield json.dumps(chunk, ensure_ascii=False)
        except Exception as e:
            logger.error(
                "CustomPlugin[%s] stream error: %s: %s",
                self._component_type,
                type(e).__name__,
                e,
            )
            yield json.dumps(
                {
                    "data": None,
                    "errCode": _CUSTOM_PLUGIN_ERROR_CODE,
                    "errMessage": f"Custom plugin stream failed: {type(e).__name__}",
                },
                ensure_ascii=False,
            )


def convert_ir_to_custom_card(ir_data: dict) -> CustomPluginCard:
    """将 IR 配置转换为 CustomPluginCard。

    从 IR 中提取参数定义、组件类型等字段，构建 ``CustomPluginCard``。
    与 ``convert_ir_to_card`` 不同，不需要 HTTP 专属字段（url/method/headers/auth）。

    Args:
        ir_data: IR 原始配置（驼峰命名）。

    Returns:
        CustomPluginCard 实例。
    """
    from jiuwen.common.utils.utils import convert_camel_to_snake
    from jiuwen.extension.wrapper.restful_api_loader import (
        _build_input_params_schema,
        param_deserialization,
    )

    ir_data = convert_camel_to_snake(ir_data, skip_fields=["headers", "auth"])

    params = param_deserialization(
        ir_data.get("arguments", []), allow_schema_is_empty=True
    )
    response = param_deserialization(
        ir_data.get("response", []), allow_schema_is_empty=True
    )

    plugin_name = ir_data.get("name", "")
    component_type = ir_data.get("component_type", "")
    if not component_type:
        metadata = ir_data.get("metadata", {})
        if isinstance(metadata, dict):
            component_type = metadata.get("component_type", "")

    card = CustomPluginCard(
        id=plugin_name or ir_data.get("id", ""),
        name=plugin_name,
        description=ir_data.get("description", ""),
        params=params,
        input_params=_build_input_params_schema(params),
        component_type=component_type,
        response=response,
        plugin_name=plugin_name,
        plugin_desc=ir_data.get("description", ""),
        related_info={"logo": ir_data.get("logo", "")},
        input_parameters=ir_data.get("input_parameters", {}),
    )
    return card


def create_plugin_tool(ir_data: dict, tag: str | None = None) -> str:
    """统一入口：按 callMode 分流创建并注册插件工具。

    - ``callMode == "custom"`` → ``CustomPluginTool``
    - 其他（含缺省） → ``RestfulApiToolNew``（现有 HTTP 逻辑）

    Args:
        ir_data: IR 原始配置（驼峰命名）。
        tag: 标签，标识工具所属 agent。

    Returns:
        注册后的 tool_id。
    """
    call_mode = ir_data.get("callMode", "api")
    from openjiuwen.core.runner import Runner

    if call_mode == "custom":
        card = convert_ir_to_custom_card(ir_data)
        tool = CustomPluginTool(card)
    else:
        from jiuwen.extension.wrapper.restful_api_loader import (
            convert_ir_to_card,
        )
        from jiuwen.extension.wrapper.restful_api_new import RestfulApiToolNew

        card = convert_ir_to_card(ir_data)
        tool = RestfulApiToolNew(card)

    result = Runner.resource_mgr.add_tool(tool, tag=tag)
    if result.is_ok():
        return tool.id
    err = result.error()
    err_msg = str(err)
    if "resource already exist" in err_msg:
        return tool.id
    raise err
