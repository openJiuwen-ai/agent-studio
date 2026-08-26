#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import List

from jiuwen.common.configs.env_constants import PLUGIN_SSL_API_CERT_KEY
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger, get_x_request_id, get_x_execution_id
from jiuwen.common.types import ValueTypeEnum
from jiuwen.orchestration.flow.constant import X_REQUEST_ID, X_EXECUTION_ID
from jiuwen.plugin.common import exception, constant
from jiuwen.plugin.handlers.handler_manager import HandlerManager
from jiuwen.plugin.models.api_utils import ApiUtils
from jiuwen.plugin.models.param import Param


class ParamLocation(Enum):
    """param location"""

    BODY = "Body"
    HEADERS = "Headers"
    QUERY = "Query"
    PATH = "Path"


FILE_PARAMS = "_file_params"


@dataclass
class RequestParams:
    ip_address_url: str = None
    api_cert = True
    query_params_in_inputs = None
    file_params = None
    headers = None
    request_arg: dict = field(default_factory=dict)
    param_wrapper = None


class RequestParamsCreator:
    """
    整合 RestfulApi 参数准备过程。
    """

    def __init__(
        self,
        api_name: str = "",
        api_headers: dict = None,
        api_input_params: list = None,
        api_url: str = "",
        api_auth: dict = None,
        api_from_ir: bool = False,
        api_cert=True,
        api_error_handler=None,
        ignore_default_not_exit: bool = True,
        **kwargs,
    ):
        self._api_name = api_name
        self._api_input_params = api_input_params or []
        self._api_url = api_url
        self._api_from_ir = api_from_ir
        self._api_auth = api_auth or {}
        self._api_cert = api_cert
        self._api_headers = api_headers or {}
        self._api_error_handler = api_error_handler or (lambda s: None)
        self._plugin_dependency: dict = kwargs.get("plugin_dependency", {})
        self._ignore_default_not_exit = ignore_default_not_exit
        self._file_handler = kwargs.get("file_handler", "")

    @staticmethod
    def _format_file_params(
        inputs, file_params_list_type: bool, file_handler: str = ""
    ):
        """
        将ir中的配置转为文件参数格式
        """
        files = []
        file_params = inputs.get(FILE_PARAMS)
        if not file_params:
            return files
        api_cert = os.environ.get(PLUGIN_SSL_API_CERT_KEY)
        for param_name, file_type_dict in file_params.items():
            file_path = inputs.get(param_name)
            if file_path and file_type_dict.get("file_type"):
                file_name = file_path.split("/")[-1].split("?")[0]
                handler = HandlerManager().get_handler(file_handler)
                files.append(
                    {
                        param_name: (
                            file_name,
                            handler.handle(file_path, api_cert=api_cert),
                        )
                    }
                )
        if file_params_list_type:
            results = []
            for file in files:
                for key, item in file.items():
                    results.append((key, item))
            return results
        return files

    def create(self, inputs, file_params_list_type: bool = True, **kwargs):
        """
        inputs补充必选参数的默认值
        """
        inputs_with_default = self._fill_default_value_for_required(
            self._api_input_params, inputs
        )
        request_params = RequestParams()
        # 获取file_params
        request_params.file_params = self._format_file_params(
            inputs_with_default, file_params_list_type, self._file_handler
        )
        request_params.ip_address_url = self._format_and_check_url(
            self._api_url, inputs_with_default
        )
        # 获取headers
        request_params.headers = self._format_headers(inputs_with_default)
        # 获取query_params
        request_params.query_params_in_inputs = self._format_query_params(
            inputs_with_default
        )
        # 向headers和query_params填充auth param
        self._add_auth_params(
            request_params.headers, request_params.query_params_in_inputs, **kwargs
        )
        # 获取param_wrapper
        request_params.param_wrapper = self._plugin_dependency.get("params_wrapper", {})

        # 获取request_arg
        request_params.request_arg = self._format_request_args(
            inputs_with_default, request_params.param_wrapper
        )

        # 获取api_cert
        request_params.api_cert = self._api_cert

        request_params.headers[X_REQUEST_ID] = get_x_request_id()
        request_params.headers[X_EXECUTION_ID] = get_x_execution_id()

        return request_params

    def _format_headers(self, inputs):
        headers = {}
        headers.update(self._api_headers)
        headers.update(self._get_params_from_input(inputs, ParamLocation.HEADERS.value))
        return headers

    def _format_query_params(self, inputs):
        return self._get_params_from_input(inputs, ParamLocation.QUERY.value)

    def _format_and_check_url(self, url, inputs):
        if not self._api_from_ir or url.find("{") == -1:
            formatted_url = url
        else:
            try:
                path_params = self._get_params_from_input(
                    inputs, ParamLocation.PATH.value
                )
                formatted_url = url.format(**path_params)
            except Exception as e:
                logger.error("format url failed")
                raise exception.PluginCommonException(
                    code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                    message=f"format url failed: {e}",
                )

        return formatted_url

    def _format_request_args(self, inputs, param_wrapper):
        body_params = self._get_params_from_input(inputs, ParamLocation.BODY.value)
        if "retrieval" in self._api_name:
            # query或者multi_queries字段改为str
            multi_queries = body_params.get("multi_queries")
            if multi_queries:
                for simple_input in multi_queries:
                    simple_input["query"] = str(simple_input.get("query", ""))
            else:
                body_params["query"] = str(body_params.get("query", ""))
        input_list = (
            isinstance(param_wrapper, dict)
            and param_wrapper.get("input_list", False) is True
        )
        return dict(json=body_params if not input_list else [body_params])

    def _add_auth_params(self, headers, query_params, **kwargs):
        auth_type = self._api_auth.get(constant.AUTH_SCOPE)
        if not auth_type:
            return
        auth_params = {}
        if auth_type == constant.AUTH_USER:
            runtime_auth = kwargs.get("runtime_auth", None)
            if not runtime_auth:  # 兼容历史版本的字段runtime_context
                runtime_context = kwargs.get("runtime_context")
                if runtime_context and hasattr(runtime_context, "api_config"):
                    runtime_auth = runtime_context.api_config
            if not runtime_auth or not isinstance(runtime_auth, dict):
                return
            auth_params = self._get_user_auth_params(runtime_auth)
        if auth_type == constant.AUTH_SERVICE:
            try:
                auth_params = ApiUtils.decrypt_service_auth(self._api_auth)
                if not auth_params.get("headers") and not auth_params.get("query"):
                    self._api_error_handler(
                        "service auth mode, but dont have headers or query auth data"
                    )
            except Exception:
                # Fallback: 使用 runtime_auth headers + _api_auth 中的原始加密值
                runtime_auth = kwargs.get("runtime_auth", None)
                if runtime_auth and isinstance(runtime_auth, dict):
                    auth_params = {
                        "headers": runtime_auth.get("headers", {}),
                        "query": {},
                    }
                # 同时合并 _api_auth 中的原始加密值
                auth_params["headers"].update(self._api_auth.get("headers", {}))

        headers.update(auth_params.get("headers", {}))
        query_params.update(auth_params.get("query", {}))

    def _get_user_auth_params(self, runtime_auth: dict):
        # 获取auth的domain, “headers"或者"query"
        target = self._api_auth.get("target", {})
        target_domain_key = target.get("domain") if isinstance(target, dict) else None
        if target_domain_key not in ["headers", "query"]:
            self._api_error_handler(
                f"target domain is {target_domain_key}, now only support headers and query"
            )
        source = self._api_auth.get("source")
        domain = (
            source.get("domain")
            if source and isinstance(source, dict)
            else target_domain_key
        )
        # 获取domain_data
        domain_data = runtime_auth.get(domain)
        if not domain_data:
            self._api_error_handler(
                f"there no {domain} in runtime context, unable to authenticate"
            )
        # 获取auth_key
        target_auth_keys = target.get("auth_keys")
        auth_keys = (
            source.get("auth_keys") if isinstance(source, dict) else target_auth_keys
        )
        if not auth_keys or not isinstance(auth_keys, list):
            self._api_error_handler("the auth_keys is not list or empty")
        # 基于domain_data, auth_key, 获取auth_key指定的secret data
        secret_datas = []
        if domain == "headers":
            # headers是不区分大小写的
            domain_data = {k.lower(): v for k, v in domain_data.items()}
            auth_keys = [k.lower() for k in auth_keys]
        for auth_key in auth_keys:
            secret_data = domain_data.get(auth_key)
            if not secret_data:
                self._api_error_handler(
                    f"there no {auth_key} to get, unable to authenticate"
                )
            secret_datas.append(secret_data)
        if len(secret_datas) != len(target_auth_keys):
            self._api_error_handler(
                "the lens of source_auth_keys != the lens of target_auth_keys"
            )
        return {target_domain_key: dict(zip(target_auth_keys, secret_datas))}

    def _get_params_from_input(self, inputs: dict, param_location: str):
        """从inputs获得指定location的param, 并将value转换成str"""
        result = {}
        for param in self._api_input_params:
            value = inputs.get(param.name, None)
            # value存在
            if param.method == param_location and value is not None:
                result[param.name] = (
                    str(value) if param_location != ParamLocation.BODY.value else value
                )
        return result

    def _fill_default_value_for_required(
        self, api_inputs_params: List[Param], inputs: dict
    ):
        """缺少的required参数填充默认值"""
        if isinstance(inputs, str):
            try:
                inputs = json.loads(inputs)
            except (ValueError, TypeError):
                raise exception.PluginCommonException(
                    code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                    message=f"参数值应为合法的JSON字符串，实际收到: {inputs[:100]}",
                )
        if not isinstance(inputs, dict):
            raise exception.PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message=f"参数值应为JSON对象(dict)，实际收到{type(inputs).__name__}类型，请检查输入是否为合法的JSON字符串",
            )
        if not inputs:
            inputs = {}
        for param in api_inputs_params:
            if not param.required:
                continue
            if param.actual_type and param.actual_type.startswith("file/"):
                # file type类型的param不填充默认值
                file_type = param.actual_type.split("/")[-1].strip()
                if FILE_PARAMS not in inputs:
                    inputs[FILE_PARAMS] = {param.name: {"file_type": file_type}}
                else:
                    inputs[FILE_PARAMS].update({param.name: {"file_type": file_type}})
                continue
            inputs_value = inputs.get(param.name)
            if inputs_value is not None:
                # inputs提供了这个param的值（这个值可能为False)，则不需要填充默认值
                if not ValueTypeEnum.is_object(param.type) or param.default_value:
                    # 如果是object类型，没有提供default_value, 需要到schema里面检查是否还需要填充默认值
                    continue
            if param.default_value or param.default_value is False:
                # 提供了default_value, 则使用default_value（默认值可能为False）
                inputs[param.name] = param.default_value
                continue
            if ValueTypeEnum.is_object(param.type):
                self._fill_object_default_value(inputs, param)
                continue
            if not self._ignore_default_not_exit:
                self._api_error_handler(
                    f"param {param.name} is not support default_value"
                )
        return inputs

    def _fill_object_default_value(self, inputs, param):
        inputs_value = inputs.get(param.name)
        if ValueTypeEnum.is_nested_array(param.type):
            if inputs_value:
                for i, _ in enumerate(inputs_value):
                    inputs_value[i] = self._fill_default_value_for_required(
                        param.schema, inputs_value[i]
                    )
            else:
                inputs[param.name] = [
                    self._fill_default_value_for_required(param.schema, {})
                ]
        else:
            # object类型参数
            default_schema_value = self._fill_default_value_for_required(
                param.schema, inputs.get(param.name, {})
            )
            inputs[param.name] = default_schema_value
