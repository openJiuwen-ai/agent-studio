#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

"""
This module contains the FlowApi class, which is a subclass of Invokable.
FlowApi is responsible for invoking a specific API based on the configuration provided.
"""

import json
import os
import time
from typing import Generator, AsyncIterator, List

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import performance_logger, logger
from jiuwen.controller.common.message_type import MessageSubType
from jiuwen.orchestration import Invokable
from jiuwen.orchestration.callbacks.span import Span
from jiuwen.orchestration.flow.components.util import (
    get_data_of_streaming_with_metadata,
    get_data_of_streaming_with_metadata_api,
    _load_json,
    _err_ignore,
)
from jiuwen.orchestration.flow.constant import USER_FIELDS, EXCEPTIONSUPPRESSION
from jiuwen.orchestration.flow.enum import StreamDataMsg
from jiuwen.orchestration.flow.stream.base import StreamData, StreamCode
from jiuwen.orchestration.utils import Input, Output
from jiuwen.plugin import PluginManager, Param
from jiuwen.plugin.common.utils.ir_utils import PluginIRConverter
from jiuwen.plugin.models.api_utils import transform_type

TAG = " === FLOW_API === "
OLD_IR_PLUGIN_RESPONSE = "raw_output"


class FlowApi(Invokable):
    """
    This class is used to encapsulate the API invoking process, making API invoking more convenient and concise.
    """

    def __init__(self):
        super().__init__()
        self._conf = None
        self._workflow_metadata = None
        self._enable_validate = False
        self._enable_confirm = False
        self._streaming = False
        self._api_id: str = None
        self._api = None
        self._outputs = None

    def init(self, conf: dict, **kwargs):
        self._conf = conf
        self._workflow_metadata = kwargs.get("metadata")
        self._enable_validate = self._conf.get("needValidate", False)
        self._enable_confirm = self._conf.get("needConfirm", False)
        self._streaming = self._conf.get("streaming", False)
        self._outputs = self._conf.get(USER_FIELDS, {}).get("outputs") or []
        self._user_fields = conf.get("userFields")
        self._init_api()

    def invoke(self, inputs: Input, **kwargs) -> Output:
        logger.info("flow api not support invoke, please use ainvoke instead")
        pass

    async def ainvoke(self, inputs: Input, **kwargs) -> Output:
        """
        异步调用插件
        """
        try:
            start_time = time.perf_counter()
            performance_logger.info(
                f"[invoke] Entered function for API ID: {self._api_id}"
            )
            validated = inputs.get("validated", False)
            confirmed = inputs.get("confirmed", False)
            inputs = inputs.get(USER_FIELDS)
            formatted_inputs = self._format_api_inputs(
                inputs,
                need_validate=self._enable_validate and not validated,
                need_confirm=self._enable_confirm and not confirmed,
            )
            cur_headers = self._format_api_header(**kwargs)
            api_outputs = await self._api.ainvoke(
                formatted_inputs, runtime_auth={"headers": cur_headers}
            )
            outputs = {USER_FIELDS: self._format_api_outputs(api_outputs, **kwargs)}
            duration = round((time.perf_counter() - start_time) * 1000)
            performance_logger.info(
                f"[invoke] Exiting function for API ID: {self._api_id}, duration: {duration:.3f}ms"
            )
            return outputs
        except JiuWenBaseException:
            if _err_ignore(self._conf):
                return {USER_FIELDS: _load_json(self._conf.get(EXCEPTIONSUPPRESSION))}
            raise
        except Exception as e:
            if _err_ignore(self._conf):
                return {USER_FIELDS: _load_json(self._conf.get(EXCEPTIONSUPPRESSION))}
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_API_EXECUTE_ERROR.code,
                message="Flow API executed failed",
            ) from e

    def stream(self, inputs: Input, **kwargs):
        logger.info("flow api not support invoke, please use astream instead")
        pass

    async def astream(self, inputs: Input, **kwargs):
        """
        异步流式调用插件
        """
        try:
            start_time = time.perf_counter()
            performance_logger.info(
                f"[invoke] Entered async function for API ID: {self._api_id}"
            )
            inputs = inputs.get(USER_FIELDS)
            api_inputs = self._format_api_inputs(inputs)
            cur_headers = self._format_api_header(**kwargs)
            api_outputs = self._api.astream(
                api_inputs, runtime_auth={"headers": cur_headers}
            )
            async_generator_res = self._transform_async_stream_data(
                api_outputs, kwargs.get("span")
            )
            outputs = {
                output.get("id"): async_generator_res for output in self._outputs
            }
            duration = round((time.perf_counter() - start_time) * 1000)
            performance_logger.info(
                f"[invoke] Exiting async function for API ID: {self._api_id}, duration: {duration:.3f}ms"
            )
            return {USER_FIELDS: outputs}
        except JiuWenBaseException:
            if _err_ignore(self._conf):
                return {USER_FIELDS: _load_json(self._conf.get(EXCEPTIONSUPPRESSION))}
            raise
        except Exception as e:
            if _err_ignore(self._conf):
                return {USER_FIELDS: _load_json(self._conf.get(EXCEPTIONSUPPRESSION))}
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_API_EXECUTE_ERROR.code,
                message="Flow API executed failed",
            ) from e

    def _init_api(self):
        self._api_id = self._conf.get("apiId")
        if not self._api_id:
            # 通过ir解析得到api
            self._api_id = self._conf.get("id")
            self._api = PluginIRConverter.ir_to_plugin(self._conf)
        else:
            # 指定id获取api_list, 首选第一个
            try:
                res = PluginManager().get_plugin_by_id(int(self._api_id))
            except ValueError as e:
                raise JiuWenBaseException(
                    error_code=StatusCode.WORKFLOW_API_INIT_ERROR.code,
                    message=StatusCode.WORKFLOW_API_INIT_ERROR.errmsg.format(
                        msg="The apiId must be of the int type"
                    ),
                ) from e

            plugin_list = res.get("body")
            if not plugin_list or not plugin_list[0]:
                raise JiuWenBaseException(
                    message=StatusCode.WORKFLOW_API_INIT_ERROR.errmsg.format(
                        msg=f"cannot find apiId[{self._api_id}]"
                    ),
                    error_code=StatusCode.WORKFLOW_API_INIT_ERROR.code,
                )
            self._api = plugin_list[0]

    def _format_api_header(self, **kwargs):
        """
        获取请求头, 优先选择self._api_id指定的header，否则用默认
        """
        all_headers = kwargs.get("runtime_auth_headers") or {}
        return all_headers.get(str(self._api_id)) or all_headers.get("default", {})

    def _format_api_inputs(self, inputs, **kwargs):
        if kwargs.get("validated", False):
            self._wait_for_required_params(inputs, self._api.params)
        if kwargs.get("confirmed", False):
            self._wait_for_user_confirmation(inputs, self._api.params)
        # 基于数据type定义，对inputs数据做强转, 若inputs提供了不在api范围内，则报错
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
                logger.error("%s _prepare_inputs ERR", TAG)
                raise JiuWenBaseException(
                    error_code=StatusCode.WORKFLOW_API_INPUTS_ERROR.code,
                    message=f"{StatusCode.WORKFLOW_API_INPUTS_ERROR.errmsg}, "
                    "param is not api params",
                )
        return api_inputs

    def _format_api_outputs(self, outputs: dict, **kwargs):
        # 插件invoke的结果统一为data, errCode, errMessage，需要的字段都在data里头，需要额外做一层解析
        error_code = outputs.get("errCode", StatusCode.WORKFLOW_API_EXECUTE_ERROR.code)
        if error_code != StatusCode.SUCCESS.code:
            error_msg = outputs.get(
                "errMessage",
                "plugin execution error, and no error information is specified",
            )
            if isinstance(error_code, int) and (
                error_code < 105000 or error_code > 105999
            ):
                # 如果error code 不是内部插件的错误返回码，就统一一个错误码，并把原来的code和msg合并
                error_msg = f"plugin flow execute inner failed, errCode={error_code}, errMessage={error_msg}"
                error_code = StatusCode.WORKFLOW_API_EXECUTE_ERROR.code
            raise JiuWenBaseException(error_code=error_code, message=error_msg)
        if self._api.response:
            # 插件invoke的结果统一为data, errCode, errMessage，需要的字段都在data里头，需要额外做一层解析
            if not isinstance(outputs.get("data"), dict):
                logger.error("%s _transform_type string ERR", TAG)
                raise JiuWenBaseException(
                    error_code=StatusCode.WORKFLOW_API_OUTPUTS_ERROR.code,
                    message=StatusCode.WORKFLOW_API_OUTPUTS_ERROR.errmsg,
                )
            return outputs.get("data")
        # 如果没有定义插件返回参数，则使用"data"作为出参名字
        return outputs

    def _format_stream_api_outputs(self, stream_outputs, **kwargs):
        generator_res = self._transform_stream_data(stream_outputs, kwargs.get("span"))
        return {output.get("id"): generator_res for output in self._outputs}

    def _wait_for_required_params(self, inputs, required_params):
        """
        校验必选参数，如有缺失则请求补充

        Args:
            inputs: 用户请求
            required_params: 必选参数列表
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
            self.interrupt(interrupt_message)

    def _wait_for_user_confirmation(self, inputs, required_params):
        """
        等待用户确认参数

        Args:
            inputs: 用户请求
            required_params: 必选参数列表
        """
        # 构建需要确认的参数字典
        input_params_dict = {}
        for param in required_params:
            if param.name in inputs:
                input_params_dict[param.name] = inputs[param.name]

        # 请求用户确认
        interrupt_message = {
            "type": MessageSubType.PLUGIN_CALL_CONFIRM.value,
            "tool_name": self._api.name,
            "parameter_dict": input_params_dict,
        }
        self.interrupt(interrupt_message)

    def _get_item_stream_data_generator(self, item, execution_id, final_output_dict):
        if hasattr(item, "content") and item.content:
            yield StreamData(
                code=StreamCode.PARTIAL_CONTENT.value,
                msg=StreamDataMsg.SUCCESS.value,
                data=get_data_of_streaming_with_metadata_api(
                    answer=item, metadata=self._workflow_metadata
                ),
                execution_id=execution_id,
            )
            final_output_dict["final_output"] += str(item.content)
        else:
            # 透传
            yield StreamData(
                code=StreamCode.PARTIAL_CONTENT.value,
                msg=StreamDataMsg.SUCCESS.value,
                data=get_data_of_streaming_with_metadata(
                    answer=item, metadata=self._workflow_metadata
                ),
                execution_id=execution_id,
            )
            final_output_dict["final_output"] += str(item)

    def _get_required_output_fields(self) -> dict:
        """
        辅助方法 1: 从 user_fields 的 outputs 中构建必需字段的字典。
        """
        return {
            field.get("id"): field.get("required")
            for field in self._user_fields.get("outputs", [])
            if field.get("id") is not None
        }

    def _process_and_filter_answer(
        self, data: "StreamData", required_fields: dict
    ) -> StreamData:
        """
        辅助方法 2: 解析并过滤单个 stream data 中的 'answer' 字段。
        如果解析失败或 answer 无效，则返回 None。

        Args:
            data: 包含流式数据的 StreamData 对象
            required_fields: 需要过滤的字段字典，键为字段名，值为布尔值表示是否需要

        Returns:
            如果解析成功且 answer 有效，则返回处理后的 StreamData 对象，否则返回 {'raw_output':str{answer}}。
        """
        answer = data.data.get("answer")
        streaming_response_dict = None
        if isinstance(answer, dict):
            streaming_response_dict = answer
        elif isinstance(answer, str):
            try:
                parsed_json = json.loads(answer)
                if isinstance(parsed_json, dict):
                    streaming_response_dict = parsed_json
            except (json.JSONDecodeError, TypeError):
                # 不是合法的JSON字符串, streaming_response_dict 保持为 None
                pass

        # 如果只有一个raw_output键（即老IR，未配置响应参数），那么直接输出
        if OLD_IR_PLUGIN_RESPONSE in required_fields and len(required_fields) == 1:
            data.data["answer"] = answer
            return data

        # answer 无法被解析为一个字典，则直接返回原始值
        if streaming_response_dict is None:
            logger.warning("The response returned by the plugin is invalid.")
            data.data["answer"] = {OLD_IR_PLUGIN_RESPONSE: str(answer)}
            return data

        # 动态过滤字段
        filtered_data = {
            key: value
            for key, value in streaming_response_dict.items()
            if required_fields.get(key) is True
        }

        # 将修改后的过滤字段赋值回原始数据
        data.data["answer"] = filtered_data
        return data

    async def _transform_async_stream_data(self, res: AsyncIterator, span: "Span"):
        """
        异步流式传输数据过滤与转化

        Args:
            res: 异步迭代器，包含流式数据
            span: 跟踪上下文对象，用于获取 trace_id

        Returns:
            生成器，逐个返回处理后的 StreamData 对象
        """
        required_user_fields_param = self._get_required_output_fields()
        final_output_dict = {"final_output": ""}
        execution_id = span.trace_id if span else ""

        async for item in res:
            for data in self._get_item_stream_data_generator(
                item, execution_id, final_output_dict
            ):
                processed_data = self._process_and_filter_answer(
                    data, required_user_fields_param
                )
                if processed_data:
                    yield processed_data

        formatted_res = {
            output.get("id"): final_output_dict["final_output"]
            for output in self._outputs
        }
        yield StreamData(
            code=StreamCode.FINISH.value,
            msg=StreamDataMsg.FINISH.value,
            data=get_data_of_streaming_with_metadata(
                answer={"USER_FIELDS": formatted_res}, metadata=self._workflow_metadata
            ),
            execution_id=execution_id,
        )

    def _transform_stream_data(self, res: Generator, span: "Span"):
        """
        同步流式传输数据过滤与转化

        Args:
            res: 生成器，包含流式数据
            span: 跟踪上下文对象，用于获取 trace_id

        Returns:
            生成器，逐个返回处理后的 StreamData 对象
        """
        required_user_fields_param = self._get_required_output_fields()
        final_output_dict = {"final_output": ""}
        execution_id = span.trace_id if span else ""

        for item in res:
            for data in self._get_item_stream_data_generator(
                item, execution_id, final_output_dict
            ):
                processed_data = self._process_and_filter_answer(
                    data, required_user_fields_param
                )
                if processed_data:
                    yield processed_data

        output_definition_list = self._get_outputs_list_from_conf()
        formatted_res = {
            output.get("id"): final_output_dict["final_output"]
            for output in output_definition_list
        }
        yield StreamData(
            code=StreamCode.FINISH.value,
            msg=StreamDataMsg.FINISH.value,
            data=get_data_of_streaming_with_metadata(
                answer={"USER_FIELDS": formatted_res}, metadata=self._workflow_metadata
            ),
            execution_id=execution_id,
        )

    def _get_outputs_list_from_conf(self) -> List[dict]:
        """获取conf中定义的组件输出列表"""
        return self._conf.get(USER_FIELDS, {}).get("outputs") or []
