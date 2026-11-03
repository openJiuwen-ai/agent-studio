# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
FlowCustomApi - 自定义插件工作流组件。

与 ``FlowApi`` 对应，但底层使用 ``CustomPluginTool`` 而非
``RestfulApiToolNew``。复用 ``FlowApi`` 的参数校验、类型转换、
流式输出等逻辑，省去 HTTP 专属的 header/auth 处理。

设计说明:
- 继承 WorkflowComponent（openjiuwen 标准组件基类）
- 有 apiId 时通过 Runner.resource_mgr.get_tool() 获取已注册 Tool
- 无 apiId 时根据 IR 配置构建 CustomPluginTool 实例
- invoke/stream 调用 self._api.ainvoke / self._api.astream
"""

import json
import time
from typing import AsyncIterator, List, Optional

from jiuwen.common.exception import JiuWenBaseException as CommonJiuWenBaseException
from jiuwen.extension.workflow_node.flow_api import (
    EXCEPTIONENABLE,
    EXCEPTIONSUPPRESSION,
    FlowApiStatusCode,
    OLD_IR_PLUGIN_RESPONSE,
    USER_FIELDS,
    MessageSubType,
    _build_flow_api_error,
    _err_ignore,
    _inner_error_text,
    _load_json,
)
from jiuwen.extension.workflow_node.utils import (
    JiuWenBaseException,
    WorkflowMetadata,
)
from jiuwen.extension.wrapper.custom_plugin_tool import (
    CustomPluginTool,
    convert_ir_to_custom_card,
)
from jiuwen.plugin.models.param import Param
from jiuwen.plugin.models.api_utils import transform_type
from openjiuwen.core.common.logging import LogEventType, workflow_logger
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.runner import Runner
from openjiuwen.core.session.node import Session
from openjiuwen.core.session.stream.base import OutputSchema
from openjiuwen.core.workflow.components.component import WorkflowComponent


class FlowCustomApi(WorkflowComponent):
    """自定义插件工作流组件。

    封装自定义插件的调用过程，支持非流式和流式两种执行方式。

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
        self._api: Optional[CustomPluginTool] = None
        self._outputs: List[dict] = []
        self._user_fields: Optional[dict] = None
        self._final_stream_output: Optional[dict] = None

        if conf:
            self.init(conf)

    def init(self, conf: dict, **kwargs):
        """初始化组件配置"""
        self._workflow_metadata = kwargs.get("metadata")
        self._init_from_conf(conf)

    def _init_from_conf(self, conf: dict):
        """从配置字典初始化组件"""
        self._conf = conf
        self._enable_validate = self._conf.get("needValidate", False)
        self._enable_confirm = self._conf.get("needConfirm", False)
        self._streaming = self._conf.get("streaming", False)
        self._outputs = self._conf.get("userFields", {}).get("outputs") or []
        self._user_fields = conf.get("userFields")
        self._init_api()

    def _init_api(self):
        """初始化插件实例

        有 apiId 时通过 Runner.resource_mgr.get_tool() 获取已注册 Tool，
        无 apiId 时根据 IR 配置构建 CustomPluginTool 实例。
        """
        self._api_id = self._conf.get("apiId")
        if not self._api_id:
            self._api_id = self._conf.get("id")
            self._api = self._build_api_from_ir()
        else:
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

    def _build_api_from_ir(self) -> CustomPluginTool:
        """从 IR 配置构建 CustomPluginTool 实例"""
        try:
            card = convert_ir_to_custom_card(self._conf)
            return CustomPluginTool(card)
        except Exception as e:
            raise _build_flow_api_error(
                FlowApiStatusCode.WORKFLOW_API_INIT_ERROR,
                error_msg=f"Failed to build custom plugin from IR config: {_inner_error_text(e)}",
            ) from e

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        """非流式调用自定义插件"""
        start_time = time.perf_counter()
        workflow_logger.info(
            "FlowCustomApi invoke started",
            event_type=LogEventType.WORKFLOW_COMPONENT_START,
            component_type_str="FlowCustomApi",
            metadata={"api_id": self._api_id},
        )
        await session.trace(
            data={"performance_metric": {"api_invoke_enter": True, "api_id": self._api_id}}
        )

        try:
            validated = inputs.get("validated", False)
            confirmed = inputs.get("confirmed", False)
            inputs_data = inputs.get("userFields")

            formatted_inputs = await self._format_api_inputs(
                inputs_data,
                session=session,
                need_validate=self._enable_validate and not validated,
                need_confirm=self._enable_confirm and not confirmed,
            )

            api_outputs = await self._api.ainvoke(formatted_inputs)
            outputs = {"userFields": self._format_api_outputs(api_outputs)}

            duration = round((time.perf_counter() - start_time) * 1000)
            workflow_logger.info(
                "FlowCustomApi invoke completed",
                event_type=LogEventType.WORKFLOW_COMPONENT_END,
                component_type_str="FlowCustomApi",
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

        except CommonJiuWenBaseException as e:
            if _err_ignore(self._conf):
                return {"userFields": _load_json(self._conf.get(EXCEPTIONSUPPRESSION))}
            raise JiuWenBaseException(
                error_code=e.error_code,
                message=e.message,
                node_id=e.node_id,
                node_name=e.node_name,
                node_type=e.node_type,
            ) from e
        except JiuWenBaseException:
            if _err_ignore(self._conf):
                return {"userFields": _load_json(self._conf.get(EXCEPTIONSUPPRESSION))}
            raise
        except Exception as e:
            workflow_logger.error(
                "FlowCustomApi invoke error: %s: %s",
                type(e).__name__,
                e,
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                component_type_str="FlowCustomApi",
                metadata={"api_id": self._api_id},
            )
            if _err_ignore(self._conf):
                return {"userFields": _load_json(self._conf.get(EXCEPTIONSUPPRESSION))}
            raise _build_flow_api_error(
                FlowApiStatusCode.WORKFLOW_API_EXECUTE_ERROR,
                cause=e,
            ) from e

    async def stream(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> AsyncIterator[Output]:
        """流式调用自定义插件"""
        start_time = time.perf_counter()
        workflow_logger.info(
            "FlowCustomApi stream started",
            event_type=LogEventType.WORKFLOW_COMPONENT_START,
            component_type_str="FlowCustomApi",
            metadata={"api_id": self._api_id},
        )
        await session.trace(
            data={"performance_metric": {"api_invoke_enter": True, "api_id": self._api_id}}
        )

        try:
            inputs_data = inputs.get("userFields", {}) or {}
            api_inputs = await self._format_api_inputs(inputs_data, session=session)

            api_outputs = self._api.astream(api_inputs)
            async for schema in self._transform_async_stream_data(api_outputs, session):
                yield schema

            duration = round((time.perf_counter() - start_time) * 1000)
            workflow_logger.info(
                "FlowCustomApi stream completed",
                event_type=LogEventType.WORKFLOW_COMPONENT_END,
                component_type_str="FlowCustomApi",
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

        except CommonJiuWenBaseException as e:
            if _err_ignore(self._conf):
                yield OutputSchema(
                    type="error",
                    index=0,
                    payload={
                        "userFields": _load_json(self._conf.get(EXCEPTIONSUPPRESSION))
                    },
                )
            raise JiuWenBaseException(
                error_code=e.error_code,
                message=e.message,
                node_id=e.node_id,
                node_name=e.node_name,
                node_type=e.node_type,
            ) from e
        except JiuWenBaseException:
            if _err_ignore(self._conf):
                yield OutputSchema(
                    type="error",
                    index=0,
                    payload={
                        "userFields": _load_json(self._conf.get(EXCEPTIONSUPPRESSION))
                    },
                )
            raise
        except Exception as e:
            workflow_logger.error(
                "FlowCustomApi stream error: %s: %s",
                type(e).__name__,
                e,
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                component_type_str="FlowCustomApi",
                metadata={"api_id": self._api_id},
            )
            if _err_ignore(self._conf):
                yield OutputSchema(
                    type="error",
                    index=0,
                    payload={
                        "userFields": _load_json(self._conf.get(EXCEPTIONSUPPRESSION))
                    },
                )
            raise _build_flow_api_error(
                FlowApiStatusCode.WORKFLOW_API_EXECUTE_ERROR,
                cause=e,
            ) from e

    # ------------------------------------------------------------------
    # 以下方法复用 FlowApi 的实现逻辑（参数校验、类型转换、流式输出）
    # ------------------------------------------------------------------

    async def _format_api_inputs(
        self,
        inputs: dict,
        session: Session = None,
        need_validate: bool = False,
        need_confirm: bool = False,
    ) -> dict:
        """格式化输入参数（复用 FlowApi 逻辑）"""
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
                    "FlowCustomApi _format_api_inputs error: param not found",
                    event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                    component_type_str="FlowCustomApi",
                    metadata={"param_name": "unknown"},
                )
                raise _build_flow_api_error(
                    FlowApiStatusCode.WORKFLOW_API_INPUTS_ERROR,
                    error_msg="param is not api params",
                )
        return api_inputs

    def _format_api_outputs(self, outputs: dict, **kwargs) -> dict:
        """格式化输出结果（复用 FlowApi 逻辑）"""
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
                    "FlowCustomApi _format_api_outputs error: data is not dict",
                    event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                    component_type_str="FlowCustomApi",
                )
                raise _build_flow_api_error(
                    FlowApiStatusCode.WORKFLOW_API_OUTPUTS_ERROR
                )
            return outputs.get("data")
        return outputs

    async def _wait_for_required_params(
        self, inputs: dict, required_params: List[Param], session: Session
    ):
        """校验必选参数，如有缺失则请求补充"""
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
        """等待用户确认参数"""
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
        """从 user_fields 的 outputs 中构建必需字段的字典"""
        if not self._user_fields:
            return {}
        return {
            field.get("id"): field.get("required")
            for field in self._user_fields.get("outputs", [])
            if field.get("id") is not None
        }

    def _process_and_filter_answer(self, data: dict, required_fields: dict) -> dict:
        """解析并过滤单个流式数据中的 answer 字段"""
        answer = data.get("answer")
        streaming_response_dict = None

        if isinstance(answer, dict):
            streaming_response_dict = answer
        elif isinstance(answer, str):
            try:
                parsed_json = json.loads(answer)
                if isinstance(parsed_json, dict):
                    streaming_response_dict = parsed_json
            except (ValueError, TypeError):
                pass

        if OLD_IR_PLUGIN_RESPONSE in required_fields and len(required_fields) == 1:
            data["answer"] = answer
            return data

        if streaming_response_dict is None:
            workflow_logger.warning(
                "FlowCustomApi: the response returned by the plugin is invalid",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                component_type_str="FlowCustomApi",
            )
            data["answer"] = {OLD_IR_PLUGIN_RESPONSE: str(answer)}
            return data

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
        """生成单个流式数据项"""
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
        """获取流式输出的节点元信息"""
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
        """流进流出核心：逐条 yield 处理后的流式数据，流结束后 yield 聚合结果"""
        required_user_fields_param = self._get_required_output_fields()
        final_output_dict = {"final_output": ""}
        execution_id = session.get_session_id() if session else ""
        output_definition_list = self._get_outputs_list_from_conf()

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
                            "userFields": formatted_res,
                            "__stream_metadata__": streaming_meta,
                        }
                    else:
                        yield {
                            "userFields": answer,
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
        self._final_stream_output = formatted_res
        yield {"userFields": formatted_res, "__stream_metadata__": finish_meta}

    def _get_outputs_list_from_conf(self) -> List[dict]:
        """获取 conf 中定义的组件输出列表"""
        return self._conf.get("userFields", {}).get("outputs") or []

    def get_stream_output(self) -> Optional[dict]:
        """流式结束后将最终输出写入 io_state，供非流式下游节点引用。"""
        if self._final_stream_output is None:
            return None
        return {"userFields": self._final_stream_output}

    def get_auth_token(self) -> dict | None:
        """自定义插件不支持 HTTP 认证透传"""
        return None
