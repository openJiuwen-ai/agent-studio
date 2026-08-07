# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
FlowApi - API 调用组件

迁移自商用版本 jiuwen/orchestration/flow/components/flow_api.py，
适配开源版本 openjiuwen 框架。

功能特性:
- 封装 RESTful API 调用过程
- 支持非流式 (invoke) 和流式 (stream) 两种执行方式
- 支持参数校验 (needValidate) 和用户确认 (needConfirm) 交互中断
- 支持异常抑制 (exceptionEnable/exceptionSuppression)
- 支持流式输出字段过滤
- 使用 RestfulApiToolNew 作为底层 plugin 实现

设计说明:
- 继承 WorkflowComponent（openjiuwen 标准组件基类）
- 有 apiId 时通过 Runner.resource_mgr.get_tool() 获取已注册 Tool
- 无 apiId 时根据 IR 配置构建 RestfulApiToolNew 实例
- 使用 Session.interact() 实现参数补充/用户确认中断
- 使用 OutputSchema 构造流式输出
"""

import json
import os
import time
from enum import Enum
from typing import AsyncIterator, List, Optional

from jiuwen.extension.workflow_node.utils import (
    JiuWenBaseException,
    WorkflowMetadata,
    get_workflow_param,
)
from jiuwen.extension.wrapper.restful_api_loader import convert_ir_to_card
from jiuwen.extension.wrapper.restful_api_new import RestfulApiToolNew
from jiuwen.plugin.models.api_utils import transform_type
from jiuwen.plugin.models.param import Param
from openjiuwen.core.common.logging import workflow_logger, LogEventType
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.runner import Runner
from openjiuwen.core.session.node import Session
from openjiuwen.core.session.stream.base import OutputSchema
from openjiuwen.core.workflow.components.component import WorkflowComponent

USER_FIELDS = "userFields"
EXCEPTIONENABLE = "exceptionEnable"
EXCEPTIONSUPPRESSION = "exceptionSuppression"
OLD_IR_PLUGIN_RESPONSE = "raw_output"

LOG_VERBOSE_MODE = os.getenv("LOG_VERBOSE", "false").lower() == "true"


class FlowApiStatusCode(Enum):
    """FlowApi 组件专用错误码"""

    SUCCESS = (0, "success")
    WORKFLOW_API_INIT_ERROR = (101741, "Api component init error. msg={msg}")
    WORKFLOW_API_EXECUTE_ERROR = (101745, "Plugin flow components execute error")
    WORKFLOW_API_INPUTS_ERROR = (101743, "Plugin flow components input not defined, {msg}")
    WORKFLOW_API_OUTPUTS_ERROR = (101744, "Plugin flow components output is error")
    WORKFLOW_API_PARAMS_CHECK_ERROR = (101742, "Plugin flow components params check error")


def _build_flow_api_error(
    status: FlowApiStatusCode,
    error_msg: str = "",
    cause: Optional[Exception] = None,
    **kwargs,
) -> JiuWenBaseException:
    """构建 FlowApi 组件异常

    Args:
        status: 错误状态码枚举
        error_msg: 错误信息
        cause: 原始异常
        **kwargs: 额外的消息格式化参数

    Returns:
        JiuWenBaseException 实例
    """
    format_kwargs = {"msg": error_msg, **kwargs}
    return JiuWenBaseException(
        error_code=status.value[0],
        message=status.value[1].format(**format_kwargs),
    )


def _err_ignore(conf: dict) -> bool:
    """判断当前是否需要忽略异常返回默认值"""
    exception_enable = conf.get(EXCEPTIONENABLE)
    return exception_enable is not None and exception_enable


def _load_json(input_data) -> dict:
    """解析 json"""
    if isinstance(input_data, dict):
        return input_data
    if not isinstance(input_data, str):
        return {}
    try:
        return json.loads(input_data)
    except json.JSONDecodeError:
        return {}


class MessageSubType(str, Enum):
    """消息子类型"""

    PLUGIN_PARAM_MISS = "plugin_param_miss"
    PLUGIN_CALL_CONFIRM = "plugin_call_confirm"


class FlowApi(WorkflowComponent):
    """API 调用组件

    封装 RESTful API 的调用过程，支持非流式和流式两种执行方式。

    Args:
        conf: 组件配置字典
    """

    def __init__(self, conf: dict = None):
        super().__init__()
        self._conf = conf or {}
        self._workflow_metadata: Optional[WorkflowMetadata] = None
        self._enable_validate = False
        self._enable_confirm = False
        self._streaming = False
        self._api_id: Optional[str] = None
        self._api: Optional[RestfulApiToolNew] = None
        self._outputs: List[dict] = []
        self._user_fields: Optional[dict] = None
        # 缓存流式末帧输出，供 get_stream_output 写入 io_state
        self._final_stream_output: Optional[dict] = None

        # 如果构造时提供了 conf，直接初始化
        if conf:
            self.init(conf)

    def init(self, conf: dict, **kwargs):
        """初始化组件配置

        Args:
            conf: 组件配置字典
            **kwargs: 可选参数，支持 metadata、session 等
        """
        self._workflow_metadata = kwargs.get("metadata")
        self._init_from_conf(conf)

    def _init_from_conf(self, conf: dict):
        """从配置字典初始化组件

        Args:
            conf: 组件配置字典
        """
        self._conf = conf
        self._enable_validate = self._conf.get("needValidate", False)
        self._enable_confirm = self._conf.get("needConfirm", False)
        self._streaming = self._conf.get("streaming", False)
        self._outputs = self._conf.get(USER_FIELDS, {}).get("outputs") or []
        self._user_fields = conf.get("userFields")
        self._init_api()

    def _init_api(self):
        """初始化 API 实例

        有 apiId 时通过 Runner.resource_mgr.get_tool() 获取已注册 Tool，
        无 apiId 时根据 IR 配置构建 RestfulApiToolNew 实例。
        """
        self._api_id = self._conf.get("apiId")
        if not self._api_id:
            # 通过 IR 解析得到 api
            self._api_id = self._conf.get("id")
            self._api = self._build_api_from_ir()
        else:
            # 指定 id 从 Runner 获取已注册 tool
            try:
                tool = Runner.resource_mgr.get_tool(str(self._api_id))
            except Exception as e:
                raise _build_flow_api_error(
                    FlowApiStatusCode.WORKFLOW_API_INIT_ERROR,
                    error_msg=f"The apiId must be a valid tool id: {e}",
                ) from e

            if not tool:
                raise _build_flow_api_error(
                    FlowApiStatusCode.WORKFLOW_API_INIT_ERROR,
                    error_msg=f"cannot find apiId[{self._api_id}]",
                )
            self._api = tool

    def _build_api_from_ir(self) -> RestfulApiToolNew:
        """从 IR 配置构建 RestfulApiToolNew 实例

        Returns:
            RestfulApiToolNew 实例
        """
        try:
            card = convert_ir_to_card(self._conf)
            return RestfulApiToolNew(card)
        except Exception as e:
            raise _build_flow_api_error(
                FlowApiStatusCode.WORKFLOW_API_INIT_ERROR,
                error_msg=f"Failed to build API from IR config: {e}",
            ) from e

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        """非流式调用 API 插件

        Args:
            inputs: 输入数据，格式: {"userFields": {...}, "validated": bool, "confirmed": bool}
            session: 工作流会话
            context: 模型上下文

        Returns:
            Output: 输出数据，格式: {"userFields": {...}}
        """
        start_time = time.perf_counter()
        workflow_logger.info(
            "FlowApi invoke started",
            event_type=LogEventType.WORKFLOW_COMPONENT_START,
            component_type_str="FlowApi",
            metadata={"api_id": self._api_id},
        )
        await session.trace(
            data={"performance_metric": {"api_invoke_enter": True, "api_id": self._api_id}}
        )

        try:
            validated = inputs.get("validated", False)
            confirmed = inputs.get("confirmed", False)
            inputs_data = inputs.get(USER_FIELDS)

            formatted_inputs = await self._format_api_inputs(
                inputs_data,
                session=session,
                need_validate=self._enable_validate and not validated,
                need_confirm=self._enable_confirm and not confirmed,
            )
            cur_headers = self._format_api_header(session)

            tmp_header = self.get_auth_token()
            if tmp_header:
                cur_headers.update(tmp_header)

            api_outputs = await self._api.ainvoke(
                formatted_inputs, runtime_auth={"headers": cur_headers}
            )
            outputs = {USER_FIELDS: self._format_api_outputs(api_outputs)}

            duration = round((time.perf_counter() - start_time) * 1000)
            workflow_logger.info(
                "FlowApi invoke completed",
                event_type=LogEventType.WORKFLOW_COMPONENT_END,
                component_type_str="FlowApi",
                metadata={"api_id": self._api_id, "duration_ms": duration},
            )
            await session.trace(
                data={
                    "performance_metric": {
                        "api_invoke_duration": duration,
                        "api_id": self._api_id,
                    }
                }
            )
            return outputs

        except JiuWenBaseException:
            if _err_ignore(self._conf):
                return {USER_FIELDS: _load_json(self._conf.get(EXCEPTIONSUPPRESSION))}
            raise
        except Exception as e:
            if _err_ignore(self._conf):
                return {USER_FIELDS: _load_json(self._conf.get(EXCEPTIONSUPPRESSION))}
            raise _build_flow_api_error(
                FlowApiStatusCode.WORKFLOW_API_EXECUTE_ERROR,
                cause=e,
            ) from e

    async def stream(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> AsyncIterator[Output]:
        """流式调用 API 插件

        直接 yield OutputSchema，由工作流引擎逐个消费并分发到下游节点。

        Args:
            inputs: 输入数据，格式: {"userFields": {...}}
            session: 工作流会话
            context: 模型上下文

        Yields:
            OutputSchema: 流式输出数据
        """
        start_time = time.perf_counter()
        workflow_logger.info(
            "FlowApi stream started",
            event_type=LogEventType.WORKFLOW_COMPONENT_START,
            component_type_str="FlowApi",
            metadata={"api_id": self._api_id},
        )
        await session.trace(
            data={"performance_metric": {"api_invoke_enter": True, "api_id": self._api_id}}
        )

        try:
            inputs_data = inputs.get(USER_FIELDS, {}) or {}
            api_inputs = await self._format_api_inputs(inputs_data, session=session)
            cur_headers = self._format_api_header(session)

            tmp_header = self.get_auth_token()
            if tmp_header:
                cur_headers.update(tmp_header)

            api_outputs = self._api.astream(
                api_inputs, runtime_auth={"headers": cur_headers}
            )
            async for schema in self._transform_async_stream_data(api_outputs, session):
                yield schema

            duration = round((time.perf_counter() - start_time) * 1000)
            workflow_logger.info(
                "FlowApi stream completed",
                event_type=LogEventType.WORKFLOW_COMPONENT_END,
                component_type_str="FlowApi",
                metadata={"api_id": self._api_id, "duration_ms": duration},
            )
            await session.trace(
                data={
                    "performance_metric": {
                        "api_invoke_duration": duration,
                        "api_id": self._api_id,
                    }
                }
            )

        except JiuWenBaseException:
            if _err_ignore(self._conf):
                yield OutputSchema(
                    type="error",
                    index=0,
                    payload={
                        USER_FIELDS: _load_json(self._conf.get(EXCEPTIONSUPPRESSION))
                    },
                )
            raise
        except Exception as e:
            if _err_ignore(self._conf):
                yield OutputSchema(
                    type="error",
                    index=0,
                    payload={
                        USER_FIELDS: _load_json(self._conf.get(EXCEPTIONSUPPRESSION))
                    },
                )
            raise _build_flow_api_error(
                FlowApiStatusCode.WORKFLOW_API_EXECUTE_ERROR,
                cause=e,
            ) from e

    def _format_api_header(self, session) -> dict:
        """获取请求头，优先选择 self._api_id 指定的 header，否则用默认

        Args:
            session: 工作流会话，从中获取全局状态中的 headers

        Returns:
            dict: 请求头字典
        """
        all_headers = get_workflow_param(session, "runtime_auth_headers") or {}
        return all_headers.get(str(self._api_id)) or all_headers.get("default", {})

    async def _format_api_inputs(
        self,
        inputs: dict,
        session: Session = None,
        need_validate: bool = False,
        need_confirm: bool = False,
    ) -> dict:
        """格式化 API 输入参数

        基于数据 type 定义对 inputs 数据做强转，若 inputs 提供了不在 api 范围内的参数则报错。

        Args:
            inputs: 用户请求参数
            session: 工作流会话（用于交互中断）
            need_validate: 是否需要参数校验
            need_confirm: 是否需要用户确认

        Returns:
            dict: 格式化后的 API 输入参数
        """
        if need_validate and session:
            await self._wait_for_required_params(inputs, self._api.params, session)
        if need_confirm and session:
            await self._wait_for_user_confirmation(inputs, self._api.params, session)

        api_params_dict = {param.name: param for param in self._api.params}
        api_inputs = {}
        for name, value in inputs.items():
            param: Param = api_params_dict.get(name)
            if value is None:
                continue
            if param:
                expected_type = param.type
                api_inputs[param.name] = transform_type(value, expected_type, name)
            else:
                workflow_logger.error(
                    "FlowApi _format_api_inputs error: param not found",
                    event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                    component_type_str="FlowApi",
                    metadata={"param_name": name if LOG_VERBOSE_MODE else "unknown"},
                )
                raise _build_flow_api_error(
                    FlowApiStatusCode.WORKFLOW_API_INPUTS_ERROR,
                    error_msg=(
                        f"param is {name if LOG_VERBOSE_MODE else 'not api params'}"
                    ),
                )
        return api_inputs

    def _format_api_outputs(self, outputs: dict, **kwargs) -> dict:
        """格式化 API 输出结果

        插件 invoke 的结果统一为 data, errCode, errMessage，需要的字段都在 data 里头，
        需要额外做一层解析。

        Args:
            outputs: API 原始输出

        Returns:
            dict: 格式化后的输出数据
        """
        error_code = outputs.get(
            "errCode", FlowApiStatusCode.WORKFLOW_API_EXECUTE_ERROR.value[0]
        )
        if error_code != FlowApiStatusCode.SUCCESS.value[0]:
            error_msg = outputs.get(
                "errMessage",
                "plugin execution error, and no error information is specified",
            )
            if isinstance(error_code, int) and (
                error_code < 105000 or error_code > 105999
            ):
                error_msg = (
                    f"plugin flow execute inner failed, "
                    f"errCode={error_code}, errMessage={error_msg}"
                )
                error_code = FlowApiStatusCode.WORKFLOW_API_EXECUTE_ERROR.value[0]
            raise JiuWenBaseException(
                error_code=error_code,
                message=error_msg,
            )

        if self._api.response:
            if not isinstance(outputs.get("data"), dict):
                workflow_logger.error(
                    "FlowApi _format_api_outputs error: data is not dict",
                    event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                    component_type_str="FlowApi",
                )
                raise _build_flow_api_error(
                    FlowApiStatusCode.WORKFLOW_API_OUTPUTS_ERROR
                )
            return outputs.get("data")
        return outputs

    async def _wait_for_required_params(
        self, inputs: dict, required_params: List[Param], session: Session
    ):
        """校验必选参数，如有缺失则请求补充

        Args:
            inputs: 用户请求参数
            required_params: 必选参数列表
            session: 工作流会话
        """
        params_dict = {param.name: param.description for param in required_params}
        missing_params = [param for param in params_dict if param not in inputs]
        if missing_params:
            missing_params_dict = {
                param: params_dict[param] for param in missing_params
            }
            interrupt_message = {
                "type": MessageSubType.PLUGIN_PARAM_MISS.value,
                "tool_name": self._api.name,
                "missing_params": missing_params_dict,
            }
            await session.interact(interrupt_message)

    async def _wait_for_user_confirmation(
        self, inputs: dict, required_params: List[Param], session: Session
    ):
        """等待用户确认参数

        Args:
            inputs: 用户请求参数
            required_params: 必选参数列表
            session: 工作流会话
        """
        input_params_dict = {}
        for param in required_params:
            if param.name in inputs:
                input_params_dict[param.name] = inputs[param.name]

        interrupt_message = {
            "type": MessageSubType.PLUGIN_CALL_CONFIRM.value,
            "tool_name": self._api.name,
            "parameter_dict": input_params_dict,
        }
        await session.interact(interrupt_message)

    def _get_required_output_fields(self) -> dict:
        """从 user_fields 的 outputs 中构建必需字段的字典

        Returns:
            dict: {field_id: required_bool}
        """
        if not self._user_fields:
            return {}
        return {
            field.get("id"): field.get("required")
            for field in self._user_fields.get("outputs", [])
            if field.get("id") is not None
        }

    def _process_and_filter_answer(self, data: dict, required_fields: dict) -> dict:
        """解析并过滤单个流式数据中的 answer 字段

        Args:
            data: 包含流式数据的字典（answer 字段）
            required_fields: 需要过滤的字段字典，键为字段名，值为布尔值表示是否需要

        Returns:
            dict: 处理后的数据字典，answer 字段已过滤。若解析失败返回原始值。
        """
        answer = data.get("answer")
        streaming_response_dict = None

        if isinstance(answer, dict):
            streaming_response_dict = answer
        elif isinstance(answer, str):
            try:
                parsed_json = json.loads(answer)
                if isinstance(parsed_json, dict):
                    streaming_response_dict = parsed_json
            except (json.JSONDecodeError, TypeError):
                pass

        # 如果只有一个 raw_output 键（即老 IR，未配置响应参数），直接输出
        if OLD_IR_PLUGIN_RESPONSE in required_fields and len(required_fields) == 1:
            data["answer"] = answer
            return data

        # answer 无法被解析为一个字典，直接返回原始值
        if streaming_response_dict is None:
            workflow_logger.warning(
                "FlowApi: the response returned by the plugin is invalid",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                component_type_str="FlowApi",
            )
            data["answer"] = {OLD_IR_PLUGIN_RESPONSE: str(answer)}
            return data

        # 动态过滤字段
        filtered_data = {
            key: value
            for key, value in streaming_response_dict.items()
            if required_fields.get(key) is True
        }

        data["answer"] = filtered_data
        return data

    async def _get_item_stream_data_generator(
        self, item, execution_id: str, final_output_dict: dict
    ) -> AsyncIterator[dict]:
        """生成单个流式数据项

        Args:
            item: 流式数据项
            execution_id: 执行 ID
            final_output_dict: 最终输出字典（用于累积输出）

        Yields:
            dict: 包含 answer 和 metadata 的数据字典
        """
        if hasattr(item, "content") and item.content:
            yield {
                "answer": item.content,
                **self._get_stream_metadata(),
            }
            final_output_dict["final_output"] += str(item.content)
        else:
            yield {
                "answer": item,
                **self._get_stream_metadata(),
            }
            final_output_dict["final_output"] += str(item)

    def _get_stream_metadata(self) -> dict:
        """获取流式输出的节点元信息

        Returns:
            dict: 包含 node_id, node_name, node_type 的字典
        """
        if self._workflow_metadata:
            return {
                "node_id": self._workflow_metadata.node_id,
                "node_name": self._workflow_metadata.node_name,
                "node_type": self._workflow_metadata.node_type,
            }
        return {}

    async def _transform_async_stream_data(
        self, res: AsyncIterator, session: Session
    ) -> AsyncIterator[dict]:
        """流进流出核心：逐条 yield 处理后的流式数据，流结束后 yield 聚合结果

        Args:
            res: 异步迭代器，包含流式数据
            session: 工作流会话

        Yields:
            dict: 格式化后的流式数据，格式为:
                  {USER_FIELDS: {output_id: value}, "__stream_metadata__": {...}}
                  最后一帧 messages_type="finish"，供下游 End 组件判断。
        """
        required_user_fields_param = self._get_required_output_fields()
        final_output_dict = {"final_output": ""}
        execution_id = session.get_session_id() if session else ""
        output_definition_list = self._get_outputs_list_from_conf()

        # 从 session 中获取当前节点信息，构建流式 metadata
        inner_session = getattr(session, "_inner", None)
        stream_node_id = (
            getattr(inner_session.state(), "_node_id", None) if inner_session else None
        )
        stream_node_type = (
            getattr(inner_session.state(), "_node_type", None)
            if inner_session
            else None
        )
        streaming_meta = {
            "node_id": stream_node_id,
            "node_type": stream_node_type,
            "messages_type": "streaming",
        }

        async for item in res:
            async for data in self._get_item_stream_data_generator(
                item, execution_id, final_output_dict
            ):
                processed_data = self._process_and_filter_answer(
                    data, required_user_fields_param
                )
                if processed_data:
                    answer = processed_data.get("answer", {})
                    if (
                        isinstance(answer, dict)
                        and OLD_IR_PLUGIN_RESPONSE not in answer
                    ):
                        formatted_res = {
                            output.get("id"): answer.get(output.get("id"))
                            for output in output_definition_list
                        }
                        yield {
                            USER_FIELDS: formatted_res,
                            "__stream_metadata__": streaming_meta,
                        }
                    else:
                        yield {
                            USER_FIELDS: answer,
                            "__stream_metadata__": streaming_meta,
                        }

        finish_meta = {
            "node_id": stream_node_id,
            "node_type": stream_node_type,
            "messages_type": "finish",
        }
        formatted_res = {
            output.get("id"): final_output_dict["final_output"]
            for output in output_definition_list
        }
        # 缓存末帧输出，供 get_stream_output 写入 io_state
        self._final_stream_output = formatted_res
        yield {USER_FIELDS: formatted_res, "__stream_metadata__": finish_meta}

    def _get_outputs_list_from_conf(self) -> List[dict]:
        """获取 conf 中定义的组件输出列表

        Returns:
            List[dict]: 输出定义列表
        """
        return self._conf.get(USER_FIELDS, {}).get("outputs") or []

    def get_stream_output(self) -> Optional[dict]:
        """流式结束后将最终输出写入 io_state，供非流式下游节点引用。

        Vertex._post_stream 流结束后会检查组件是否有此方法，
        有则把返回值通过 set_outputs 写入 io_state。

        Returns:
            dict: {USER_FIELDS: {output_id: value}}，或 None
        """
        if self._final_stream_output is None:
            return None
        return {USER_FIELDS: self._final_stream_output}

    # 插件节点中自定义认证header相关的逻辑需要修改
    def get_auth_token(self) -> dict | None:
        auth = self._conf.get("auth") or {}
        if not auth:
            return None
        if auth.get("scope") != "USER":
            return None
        target = auth.get("target") or {}

        if not target:
            return None

        if target.get("domain") != "headers":
            return None

        auth_keys = target.get("auth_keys") or []
        if not auth_keys:
            return None

        if "X-Auth-Token" not in auth_keys:
            return None

        return {"X-Auth-Token": "defaultUser|0"}
