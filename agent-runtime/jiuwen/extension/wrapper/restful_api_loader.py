# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
Restful API Loader -- IR 解析 + 工具注册。

从 IR 配置创建并注册 RestfulApiToolNew 工具。

核心功能：
1. load_restful_api_from_ir: 从 IR 配置创建并注册工具
2. convert_ir_to_card: 将 IR 配置转换为 RestfulApiCardNew
3. 参数反序列化、校验等辅助函数
"""

import copy
import os
from typing import List

from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.utils.utils import convert_camel_to_snake, format_exception_reason
from jiuwen.extension.wrapper.restful_api_new import (
    RestfulApiCardNew,
    RestfulApiToolNew,
)
from jiuwen.plugin import Param
from jiuwen.plugin.common.constant import (
    PLUGIN_DEFAULT_MAX_TIME_OUT,
    PLUGIN_DEFAULT_PERIOD_ROUND,
    PLUGIN_MAX_PERIOD_ROUND,
    PLUGIN_MAX_TIME_OUT,
    REQUEST_TIME_OUT,
)
from jiuwen.plugin.common.exception import PluginCommonException
from jiuwen.plugin.common.utils.ir_utils import RestfulPluginInputValidate

HEADERS = "headers"
AUTH = "auth"


def load_restful_api_from_ir(ir_data: dict, tag: str | None = None) -> str:
    """
    从 IR 配置创建并注册 RestfulApi 工具

    Args:
        ir_data: IR 原始配置字典（驼峰命名），包含：
            - name,
            - description,
            - url,
            - method,
            - headers,
            - auth,
            - arguments,
            - response
            - principle, logo, pluginDependency
            - id, asyncInvoke, inputParameters
            - fileHandler
        tag: 标签，用于标识工具属于那个agent

    Returns:
        注册后的 tool_id
    """
    card = convert_ir_to_card(ir_data)

    tool = RestfulApiToolNew(card)

    from openjiuwen.core.runner import Runner

    result = Runner.resource_mgr.add_tool(tool, tag=tag)

    if result.is_ok():
        return tool.id
    err = result.error()
    err_msg = str(err)
    if "resource already exist" in err_msg:
        return tool.id
    raise err


def convert_ir_to_card(ir_data: dict) -> RestfulApiCardNew:
    """
    将 IR 配置转换为 RestfulApiCardNew

    参考 PluginIRConverter.ir_to_plugin 实现

    Args:
        ir_data: IR 原始配置（驼峰命名），包含：
            - name, description, url, method
            - headers, auth, arguments, response
            - principle, logo, pluginDependency
            - id, asyncInvoke, inputParameters
            - fileHandler

    Returns:
        (RestfulApiCardNew 实例, tag)
    """
    if not isinstance(ir_data, dict):
        raise PluginCommonException(
            code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
            message="plugin ir info is not dict type",
        )

    ir_data = convert_camel_to_snake(ir_data, skip_fields=[HEADERS, AUTH])

    try:
        RestfulPluginInputValidate(**ir_data)
        params = param_deserialization(
            ir_data.get("arguments", []), allow_schema_is_empty=True
        )
        response = param_deserialization(
            ir_data.get("response", []), allow_schema_is_empty=True
        )
    except PluginCommonException as e:
        raise e
    except Exception as e:
        raise PluginCommonException(
            code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
            message=format_exception_reason(
                e, reason="Plugin parameter validation failed"
            ),
        ) from e

    url = ir_data.get("url", "")
    headers = copy.deepcopy(ir_data.get(HEADERS, {}))

    auth = ir_data.get(AUTH, {})
    auth = extend_auth(auth, ir_data)

    plugin_reade_buffer_size = int(
        os.environ.get("STREAM_PLUGIN_BUFSIZE_KEY", 64 * 1024)
    )

    cert = os.environ.get("PLUGIN_SSL_API_CERT_KEY")

    timeout = float(os.getenv("PLUGIN_REQUEST_TIMEOUT_KEY", REQUEST_TIME_OUT))

    # 优先使用 name 作为 id，避免同一插件组下不同接口 id 重复导致注册被覆盖
    plugin_name = ir_data.get("name", "")
    card = RestfulApiCardNew(
        id=plugin_name or ir_data.get("id", ""),
        name=plugin_name,
        description=ir_data.get("description", ""),
        params=params,
        path=url,
        headers=headers,
        method=ir_data.get("method", "POST"),
        response=response,
        plugin_name=ir_data.get("name", ""),
        plugin_desc=ir_data.get("description", ""),
        auth=auth,
        label=ir_data.get("label", ""),
        related_info={"logo": ir_data.get("logo", "")},
        status=ir_data.get("status"),
        principle=ir_data.get("principle", ""),
        query_params=ir_data.get("query_params", {}),
        user_id=ir_data.get("user_id", ""),
        plugin_dependency=ir_data.get("plugin_dependency", {}),
        async_conf=ir_data.get("async_invoke", {}),
        async_switch=ir_data.get("async_invoke", {}).get("async_switch", False),
        is_from_ir=True,
        input_parameters=ir_data.get("input_parameters", {}),
        file_handler=ir_data.get("file_handler", ""),
        plugin_reade_buffer_size=plugin_reade_buffer_size,
        cert=cert,
        timeout=timeout,
    )

    check_valid_value(card)
    check_async_conf(card)

    return card


def param_deserialization(
    arguments: list, allow_schema_is_empty: bool = False
) -> List[Param]:
    """
    参数反序列化

    参考 Plugin.param_deserialization 实现

    Args:
        arguments: 参数列表
        allow_schema_is_empty: 是否允许 schema 为空

    Returns:
        List[Param]
    """
    params = []
    level_key = "level"
    for p in arguments:
        if "name" not in p or "description" not in p:
            raise PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message="name and description needed",
            )
        if isinstance(p.get(level_key), str) and p.get(level_key).isdigit():
            p[level_key] = int(p.get(level_key))
        params.append(
            Param(
                name=p.get("name", ""),
                description=p.get("description", ""),
                default_value=p.get("default_value"),
                param_type=p.get("type", ""),
                required=p.get("required", False),
                visible=p.get("visible", True),
                level=p.get(level_key, 0),
                method=p.get("method", "Body"),
                schema=p.get("schema", []),
                actual_type=p.get("actual_type", ""),
                allow_schema_is_empty=allow_schema_is_empty,
            )
        )
    return params


def check_valid_value(card: RestfulApiCardNew):
    """
    校验参数有效性

    参考 Plugin.check_valid_value 实现

    Args:
        card: RestfulApiCardNew 实例
    """
    param_locations = ["Body", "Headers", "Query", "Path"]
    param_locations_str = " ".join(param_locations)

    for param in card.params:
        if param.method not in param_locations:
            raise PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message=f"parameter's request type only supports {param_locations_str}",
            )

    if card.method.lower() not in ["post", "get"]:
        raise PluginCommonException(
            code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
            message="request method only supports post and get",
        )


def check_async_conf(card: RestfulApiCardNew):
    """
    校验异步配置

    参考 Plugin.check_async_conf 实现

    Args:
        card: RestfulApiCardNew 实例
    """
    async_conf = card.async_conf
    if not isinstance(async_conf, dict):
        if not async_conf:
            return
        raise PluginCommonException(
            code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
            message="async_conf should be dict",
        )

    async_switch = async_conf.get("async_switch", False)
    if async_switch is False:
        return

    if not isinstance(async_switch, bool):
        raise PluginCommonException(
            code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
            message="async switch should be bool",
        )

    call_back_url = async_conf.get("callback_url")
    if not call_back_url or not isinstance(call_back_url, str):
        raise PluginCommonException(
            code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
            message="async url should be str",
        )

    max_time_out = async_conf.get("max_timeout", PLUGIN_DEFAULT_MAX_TIME_OUT)
    if not max_time_out or not isinstance(max_time_out, int):
        raise PluginCommonException(
            code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
            message="max_time_out should be int",
        )
    if max_time_out <= 0 or max_time_out > PLUGIN_MAX_TIME_OUT:
        raise PluginCommonException(
            code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
            message=f"max_round_count should between [0, {PLUGIN_MAX_TIME_OUT}]",
        )

    period_of_round = async_conf.get("period_of_round", PLUGIN_DEFAULT_PERIOD_ROUND)
    if not period_of_round or not isinstance(period_of_round, int):
        raise PluginCommonException(
            code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
            message="period_of_round should be int",
        )
    if period_of_round <= 0 or period_of_round > PLUGIN_MAX_PERIOD_ROUND:
        raise PluginCommonException(
            code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
            message=f"period_of_round should between [0, {PLUGIN_MAX_PERIOD_ROUND}]",
        )


def extend_auth(auth: dict, ir_data: dict) -> dict:
    """
    auth 扩展点

    参考 PluginIRConverter.extend_auth 实现

    Args:
        auth: 原始 auth 配置
        ir_data: IR 数据

    Returns:
        扩展后的 auth 配置
    """
    return auth
