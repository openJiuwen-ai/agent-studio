#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import json
import os
import uuid
from typing import Any, Callable, Dict, List

from fastapi import status
from openjiuwen.core.common.logging import logger
from packaging import version
from pydantic import ValidationError

from openjiuwen_studio.core.database import milliseconds
import openjiuwen_studio.core.manager.convertor.plugin as convert
from openjiuwen_studio.core.manager.convertor.components.plugin import param_type_mapping
from openjiuwen_studio.core.manager.internal.workflow import InputElem
from openjiuwen_studio.core.manager.login_manager.space import check_user_space
from openjiuwen_studio.core.manager.repositories.plugin_repository import plugin_repository
from openjiuwen_studio.core.manager.repositories.tool_repository import tool_repository
from openjiuwen_studio.core.utils.exception import log_exception
from openjiuwen_studio.models.plugin import PluginBaseDBPd, ToolBaseDB, PluginPublishDBPd
from openjiuwen_studio.schemas.plugin import (
    PluginCreate, PluginId, PluginInfo, PluginInfoResponse, PluginApiBase,
    PluginApiInfo, PluginApiInfoCreate, PluginToolId, PluginApiInfoResponse,
    PluginListTool, PluginList, PluginListResponse, PluginListPagination,
    PluginType, PluginToolParam, ToolId, PluginCodeBase, PluginCodeInfo,
    PluginCodeInfoResponse, PluginApiInfoDB, PluginCodeInfoDB, PluginPublish,
    PluginPublishResponse, PluginPublishInfo, PluginPublishListResponse,
    PluginPublishInfoResponse, ParamType
)
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.core.manager.reference_extractor import check_referenced_dependencies
from openjiuwen_studio.core.manager.repositories.reference_repository import reference_repository


def with_exception_handling(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            log_exception(e)
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message=type(e).__name__
            )
        except Exception as e:
            log_exception(e)
            return ResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=type(e).__name__
            )

    return wrapper


@with_exception_handling
def plugin_create(
        req: PluginCreate,
        current_user: dict
) -> ResponseModel:
    """创建新的插件"""
    _ = check_user_space(req.space_id, current_user)

    current_time = milliseconds()

    plugin_id = str(uuid.uuid4())

    plugin_dict = {
        "plugin_id": plugin_id,
        "name": req.name,
        "desc": req.desc,
        "desc_mk": req.desc_mk if hasattr(req, 'desc_mk') else "",
        "url": req.url,
        "icon_uri": req.icon_uri,
        "space_id": req.space_id,
        "plugin_type": req.plugin_type,
        "create_time": current_time,
        "update_time": current_time,
    }

    # 将 request_params 映射到数据库字段 inputs
    if hasattr(req, 'request_params') and req.request_params:
        plugin_dict["inputs"] = [param.model_dump() for param in req.request_params]

    plugin = PluginBaseDBPd(**plugin_dict)
    logger.info(f"create plugin info: {plugin}")

    res = plugin_repository.plugin_create(plugin.model_dump())
    create_result = ResponseModel(**res)
    logger.info(f"create plugin info into db result: {create_result}")
    if create_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=create_result.code,
            message=create_result.message,
        )

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="create plugin success",
        data=PluginId(
            plugin_id=plugin_id,
            space_id=req.space_id,
        )
    )


@with_exception_handling
def plugin_get(
        req: PluginId,
        current_user: dict
) -> ResponseModel:
    """获取插件信息"""
    _ = check_user_space(req.space_id, current_user)

    res, _ = plugin_repository.plugin_get(req.model_dump())
    canvas_result = ResponseModel(**res)
    logger.info(f"get plugin info from db result: {canvas_result}")
    if canvas_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=canvas_result.code,
            message=canvas_result.message,
        )
    # 使用字段映射方法将数据库的 inputs 映射为 request_params
    plugin_info = PluginInfo.from_db_with_mapping(canvas_result.data)
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="get plugin success",
        data=PluginInfoResponse(plugin_info=plugin_info)
    )


@with_exception_handling
def plugin_update(
        req: PluginInfo,
        current_user: dict
) -> ResponseModel:
    """获取插件信息"""
    _ = check_user_space(req.space_id, current_user)

    logger.info(f"update plugin: {req}")
    res, _ = plugin_repository.plugin_get(req.model_dump())
    get_result = ResponseModel(**res)
    logger.info(f"get plugin info from db result: {get_result}")
    if get_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=get_result.code,
            message=get_result.message,
        )
    # Handle both dict and Pydantic model types
    data = get_result.data
    if hasattr(data, 'model_dump'):
        data_dict = data.model_dump()
    elif hasattr(data, 'dict'):
        data_dict = data.dict()
    else:
        data_dict = data
    plugin = PluginBaseDBPd(**data_dict)
    update_dict = {
        "name": req.name,
        "desc": req.desc,
        "url": req.url,
        "icon_uri": req.icon_uri,
    }

    if hasattr(req, 'desc_mk') and req.desc_mk is not None:
        update_dict["desc_mk"] = req.desc_mk

    # 将 request_params 映射到数据库字段 inputs
    if hasattr(req, 'request_params') and req.request_params is not None:
        update_dict["inputs"] = [param.model_dump() for param in req.request_params]

    for key, value in update_dict.items():
        setattr(plugin, key, value)

    res = plugin_repository.plugin_save(plugin.model_dump())
    result = ResponseModel(**res)
    logger.info(f"update plugin info in db result: {result}")
    if result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=result.code,
            message=result.message,
        )

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="update plugin success",
    )


@with_exception_handling
def plugin_delete(
        req: PluginId,
        current_user: dict
) -> ResponseModel:
    """删除插件"""
    _ = check_user_space(req.space_id, current_user)

    logger.info(f"delete plugin: {req}")

    # 1. 检查该plugin是否被引用
    try:
        can_delete, message = check_referenced_dependencies(
            reference_repository, req.space_id, "PLUGIN", req.plugin_id
        )

        if not can_delete:
            logger.warning(f"plugin deletion blocked due to dependencies: {req.plugin_id} - {message}")
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message=message,
            )
    except Exception as e:
        logger.error(f"Plugin dependency check failed for {req.plugin_id}: {e}")
        # 依赖检查失败时，为安全起见阻止删除
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Unable to verify plugin dependencies, deletion blocked for safety",
        )

    # 2. 执行删除操作
    res = plugin_repository.plugin_delete(req.model_dump())
    delete_result = ResponseModel(**res)
    logger.info(f"delete plugin info in db result: {delete_result}")
    if delete_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=delete_result.code,
            message=delete_result.message,
        )

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="delete plugin success",
    )


@with_exception_handling
def plugin_list(
        req: PluginList,
        current_user: dict
) -> ResponseModel:
    """获取插件列表"""
    _ = check_user_space(req.space_id, current_user)

    res = plugin_repository.plugin_list(req.model_dump())
    list_result = ResponseModel(**res)
    logger.info(f"get plugin list from db result: {list_result}")
    if list_result.code != status.HTTP_200_OK and list_result.code != status.HTTP_404_NOT_FOUND:
        return ResponseModel(
            code=list_result.code,
            message=list_result.message,
        )

    # 处理返回数据
    if list_result.data is None:
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="get plugin success",
            data=PluginListResponse(
                plugin_infos=[],
                pagination={
                    "total": 0,
                    "total_pages": 1,
                    "page": req.page or 1,
                    "page_size": req.size or 10
                }
            )
        )
    
    # 转换插件信息
    infos: List[PluginInfo] = []
    plugin_data = list_result.data.get("plugin_infos", [])
    for info_dict in plugin_data:
        info = PluginInfo(**info_dict)
        infos.append(info)
    
    # 获取分页信息
    pagination_data = list_result.data.get("pagination", {})
    pagination = PluginListPagination(**pagination_data) if pagination_data else PluginListPagination(
        total=0,
        total_pages=1,
        page=req.page or 1,
        page_size=req.size or 10
    )
    
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="get plugin success",
        data=PluginListResponse(
            plugin_infos=infos,
            pagination=pagination
        )
    )


@with_exception_handling
def plugin_convert(
        req: ToolId,
        current_user: dict
) -> ResponseModel:
    """转换插件"""
    _ = check_user_space(req.space_id, current_user)

    get_res, plugin_dict = tool_repository.tool_get(req.model_dump())
    get_result = ResponseModel(**get_res)
    if get_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=get_result.code,
            message=get_result.message,
        )
    tool_info = get_result.data
    plugin = convert.plugin_convert(PluginBaseDBPd(**plugin_dict), tool_info.model_dump())
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="convert plugin success",
        data=plugin
    )


@with_exception_handling
def plugin_create_api(
        req: PluginApiInfoCreate,
        current_user: dict
) -> ResponseModel:
    """创建插件API"""
    _ = check_user_space(req.space_id, current_user)

    logger.info(f"create plugin api info: {req}")

    api_info = PluginApiInfo(
        space_id=req.space_id,
        plugin_id=req.plugin_id,
        plugin_type=PluginType.PLUGIN_TYPE_CLOUD_API,
        tool_id=str(uuid.uuid4()),
        name=req.name,
        desc=req.desc,
        path=req.path,
        method=req.method,
        available=False,
        request_params=req.request_params if hasattr(req, 'request_params') else [],
        response_params=req.response_params if hasattr(req, 'response_params') else [],
        headers=req.headers if hasattr(req, 'headers') else [],
    )

    res = tool_repository.tool_create(api_info.model_dump())
    result = ResponseModel(**res)
    logger.info(f"create plugin api info in db result: {result}")
    if result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=result.code,
            message=result.message,
        )

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="create plugin api success",
        data={"tool_id": api_info.tool_id},
    )


def _plugin_input_output_parameters(params: List[PluginToolParam]) -> List[Dict[str, Any]]:
    input_output_params: List[Dict[str, Any]] = []
    for param in params:
        input = InputElem(
            name=param.name,
            type=param_type_mapping.get(param.type),
            description=param.desc,
            required=param.is_required,
            method=param.method
        )
        param_dict = input.model_dump()
        param_dict['runtime'] = param.is_runtime if hasattr(param, 'is_runtime') else True
        param_dict['value'] = param.value if hasattr(param, 'value') else ""
        param_dict['priority'] = param.priority if hasattr(param, 'priority') else 0
        input_output_params.append(param_dict)

    return input_output_params


def _input_parameters_to_request_params(input_parameters: List[Dict[str, Any]]) -> List[PluginToolParam]:
    """Convert input_parameters from database to request_params for API response"""
    if not input_parameters:
        return []

    request_params = []
    for param in input_parameters:
        param_type = ParamType.PARAM_TYPE_STRING
        for key, value in param_type_mapping.items():
            if value == param.get('type'):
                param_type = key
                break

        request_param = PluginToolParam(
            name=param.get('name', ''),
            desc=param.get('description', ''),
            type=param_type,
            is_required=param.get('required', False),
            is_runtime=param.get('runtime', True),
            value=param.get('value', ''),
            method=param.get('method', 0),
            priority=param.get('priority', 0),
        )
        request_params.append(request_param)

    return request_params


def _plugin_update_tool(
        plugin_id: str,
        req: Dict[str, Any]
) -> ResponseModel:
    get_res, _ = tool_repository.tool_get(req)
    get_result = ResponseModel(**get_res)
    if get_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=get_result.code,
            message=get_result.message,
        )

    tool = get_result.data
    # tool is already a dict from database, not a Pydantic model
    tool_plugin_id = tool.get('plugin_id') if isinstance(tool, dict) else tool.plugin_id
    tool_version = tool.get('plugin_version') if isinstance(tool, dict) else tool.plugin_version

    if tool_plugin_id != plugin_id:
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="plugin id is not match",
        )

    # 确保 req 中包含 plugin_version，因为唯一约束是 (tool_id, plugin_version)
    # 从已获取的 tool 对象中获取 plugin_version，确保更新时能正确找到记录
    if 'plugin_version' not in req or not req.get('plugin_version'):
        req['plugin_version'] = tool_version if tool_version else ToolBaseDB.__version_none__

    res = tool_repository.tool_save(req)
    result = ResponseModel(**res)
    logger.info(f"update plugin tool info in db result: {result}")
    if result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=result.code,
            message=result.message,
        )

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="update plugin tool success",
    )


@with_exception_handling
def plugin_update_api(
        req: PluginApiInfo,
        current_user: dict
) -> ResponseModel:
    """更新插件API"""
    _ = check_user_space(req.space_id, current_user)

    logger.info("update plugin api info")
    update_api = PluginApiInfoDB(**(req.model_dump()))
    update_api.input_parameters = _plugin_input_output_parameters(req.request_params)
    update_api.output_parameters = _plugin_input_output_parameters(req.response_params)
    return _plugin_update_tool(req.plugin_id, update_api.model_dump())


@with_exception_handling
def plugin_delete_tool(
        req: PluginToolId,
        current_user: dict
) -> ResponseModel:
    """删除插件工具"""
    _ = check_user_space(req.space_id, current_user)

    logger.info("delete plugin tool")
    get_res, _ = tool_repository.tool_get(req.model_dump())
    get_result = ResponseModel(**get_res)
    if get_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=get_result.code,
            message=get_result.message,
        )

    tool = get_result.data
    if tool.plugin_id != req.plugin_id:
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="plugin id is not match",
        )

    # 检查tool是否被其他资源引用
    can_delete, message = check_referenced_dependencies(
        reference_repository, req.space_id, "TOOL", req.tool_id
    )
    if not can_delete:
        return ResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message=message,
        )

    res = tool_repository.tool_delete(req.model_dump())
    result = ResponseModel(**res)
    logger.info(f"delete plugin tool info in db result: {result}")
    if result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=result.code,
            message=result.message,
        )

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="delete plugin tool success",
    )


@with_exception_handling
def plugin_get_api(
        req: PluginToolId,
        current_user: dict
) -> ResponseModel:
    """获取插件API"""
    _ = check_user_space(req.space_id, current_user)

    logger.info("get plugin api")
    get_res, _ = tool_repository.tool_get(req.model_dump())
    get_result = ResponseModel(**get_res)
    if get_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=get_result.code,
            message=get_result.message,
        )

    tool = get_result.data
    if tool.plugin_id != req.plugin_id:
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="plugin id is not match",
        )

    # tool is already a dict from database, not a Pydantic model
    api_dict = tool if isinstance(tool, dict) else tool.model_dump()
    if 'available' not in api_dict or api_dict.get('available') is None:
        api_dict['available'] = True

    # Convert input_parameters to request_params with runtime and value
    if 'input_parameters' in api_dict and api_dict['input_parameters']:
        request_params = _input_parameters_to_request_params(api_dict['input_parameters'])
        api_dict['request_params'] = [param.model_dump() for param in request_params]

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="get plugin api success",
        data=PluginApiInfoResponse(
            api_info=[PluginApiInfo(**api_dict)],
            total=1,
        )
    )


@with_exception_handling
def plugin_list_api(
        req: PluginListTool,
        current_user: dict
) -> ResponseModel:
    """获取插件API列表"""
    _ = check_user_space(req.space_id, current_user)

    logger.info("list plugin api")
    list_res, tool_list = plugin_repository.plugin_get(req.model_dump())
    list_result = ResponseModel(**list_res)
    if list_result.code != status.HTTP_200_OK and list_result.code != status.HTTP_404_NOT_FOUND:
        return ResponseModel(
            code=list_result.code,
            message=list_result.message,
        )

    api_infos: List[PluginApiInfo] = []
    for info_dict in tool_list:
        logger.info(f"tool: {info_dict}")
        if 'available' not in info_dict or info_dict.get('available') is None:
            info_dict['available'] = True

        # Convert input_parameters to request_params with runtime and value
        if 'input_parameters' in info_dict and info_dict['input_parameters']:
            request_params = _input_parameters_to_request_params(info_dict['input_parameters'])
            info_dict['request_params'] = [param.model_dump() for param in request_params]

        info = PluginApiInfo(**info_dict)
        if info.plugin_id == req.plugin_id:
            api_infos.append(info)

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="list plugin api success",
        data=PluginApiInfoResponse(
            api_info=api_infos,
            total=len(api_infos),
        )
    )


@with_exception_handling
def plugin_create_code(
        req: PluginCodeBase,
        current_user: dict
) -> ResponseModel:
    """创建插件code工具"""
    _ = check_user_space(req.space_id, current_user)

    logger.info("create plugin code info")

    code_info = PluginCodeInfo(
        space_id=req.space_id,
        plugin_id=req.plugin_id,
        plugin_type=PluginType.PLUGIN_TYPE_CLOUD_CODE,
        tool_id=str(uuid.uuid4()),
        name=req.name,
        desc=req.desc,
        language=req.language,
        code=req.code,
        available=False,
    )

    res = tool_repository.tool_create(code_info.model_dump())
    result = ResponseModel(**res)
    logger.info(f"create plugin code info in db result: {result}")
    if result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=result.code,
            message=result.message,
        )

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="create plugin code success",
        data={"tool_id": code_info.tool_id},
    )


@with_exception_handling
def plugin_update_code(
        req: PluginCodeInfo,
        current_user: dict
) -> ResponseModel:
    """更新插件code工具"""
    _ = check_user_space(req.space_id, current_user)

    logger.info("update plugin code info")
    update_code = PluginCodeInfoDB(**(req.model_dump()))
    update_code.input_parameters = _plugin_input_output_parameters(req.request_params)
    update_code.output_parameters = _plugin_input_output_parameters(req.response_params)
    return _plugin_update_tool(req.plugin_id, update_code.model_dump())


@with_exception_handling
def plugin_get_code(
        req: PluginToolId,
        current_user: dict
) -> ResponseModel:
    """获取插件code工具信息"""
    _ = check_user_space(req.space_id, current_user)

    logger.info("get plugin code")
    get_res, _ = tool_repository.tool_get(req.model_dump())
    get_result = ResponseModel(**get_res)
    if get_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=get_result.code,
            message=get_result.message,
        )

    tool = get_result.data
    # tool is already a dict from database, not a Pydantic model
    tool_plugin_id = tool.get('plugin_id') if isinstance(tool, dict) else tool.plugin_id

    if tool_plugin_id != req.plugin_id:
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="plugin id is not match",
        )

    # tool is already a dict from database, not a Pydantic model
    tool_dict = tool if isinstance(tool, dict) else tool.model_dump()

    # Convert input_parameters to request_params with runtime and value
    if 'input_parameters' in tool_dict and tool_dict['input_parameters']:
        request_params = _input_parameters_to_request_params(tool_dict['input_parameters'])
        tool_dict['request_params'] = [param.model_dump() for param in request_params]

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="get plugin code success",
        data=PluginCodeInfoResponse(
            code_info=[PluginCodeInfo(**tool_dict)],
            total=1,
        )
    )


@with_exception_handling
def plugin_list_code(
        req: PluginListTool,
        current_user: dict
) -> ResponseModel:
    """获取插件code工具列表"""
    _ = check_user_space(req.space_id, current_user)

    logger.info("list plugin code")
    list_res, tool_list = plugin_repository.plugin_get(req.model_dump())
    list_result = ResponseModel(**list_res)
    if list_result.code != status.HTTP_200_OK and list_result.code != status.HTTP_404_NOT_FOUND:
        return ResponseModel(
            code=list_result.code,
            message=list_result.message,
        )

    code_infos: List[PluginCodeInfo] = []
    for info_dict in tool_list:
        info = PluginCodeInfo(**info_dict)
        if info.plugin_id == req.plugin_id:
            code_infos.append(info)

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="list plugin code success",
        data=PluginCodeInfoResponse(
            code_info=code_infos,
            total=len(code_infos),
        )
    )


def _compare_versions(ver1, ver2):
    v1 = version.parse(ver1)
    v2 = version.parse(ver2)

    if v1 < v2:
        return True
    return False


@with_exception_handling
def plugin_publish(
        req: PluginPublish,
        current_user: dict
) -> ResponseModel:
    """
    发布插件

    Args:
        req: 插件发布请求
        current_user: 当前用户信息

    Returns:
        ResponseModel: 发布结果
    """
    # 1. 校验Space_id是否有权限
    _ = check_user_space(req.space_id, current_user)

    plugin_query = {
        "plugin_id": req.plugin_id,
        "space_id": req.space_id
    }

    # 2. 获取最新版本信息
    res = plugin_repository.plugin_publish_get(plugin_query)
    get_version_result = ResponseModel(**res)
    logger.info(f"get version plugin info: {get_version_result}")

    if get_version_result.code == status.HTTP_404_NOT_FOUND:
        latest_version = "0.0.0"  # 初始版本
    elif get_version_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=get_version_result.code,
            message=f"Get versioned plugin with id {req.plugin_id} failed, error: {get_version_result.message}",
            data=None
        )
    else:
        latest_version_data = PluginPublishDBPd(**get_version_result.data)
        latest_version = latest_version_data.plugin_version

    # 3. 检查版本格式和递增性（除非强制发布）
    if not req.force:
        is_valid = _compare_versions(latest_version, req.plugin_version)
        if not is_valid:
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message=f"Version check failed",
                data=None
            )

    # 4. 获取插件草稿内容
    plugin_draft_query = {
        "plugin_id": req.plugin_id,
        "space_id": req.space_id,
    }

    draft_result, tool_list = plugin_repository.plugin_get(plugin_draft_query)
    draft_response = ResponseModel(**draft_result)

    if draft_response.code != status.HTTP_200_OK:
        return ResponseModel(
            code=draft_response.code,
            message=f"Get plugin draft failed: {draft_response.message}",
            data=None
        )

    plugin_data = draft_response.data
    plugin_info = PluginBaseDBPd(**(plugin_data.model_dump()))

    # 5. 创建发布版本
    publish_data = {
        "plugin_id": req.plugin_id,
        "name": plugin_info.name,
        "desc": plugin_info.desc,
        "desc_mk": plugin_info.desc_mk,
        "plugin_version": req.plugin_version,
        "version_desc": req.version_desc,
        "url": plugin_info.url,
        "icon_uri": plugin_info.icon_uri,
        "plugin_type": plugin_info.plugin_type,
        "space_id": req.space_id,
        "inputs": plugin_info.inputs,
        "tools": tool_list,
        "create_time": milliseconds(),
        "update_time": milliseconds()
    }

    # 6. 保存发布版本
    publish_result = plugin_repository.plugin_publish_create(publish_data)
    publish_response = ResponseModel(**publish_result)

    if publish_response.code != status.HTTP_200_OK:
        return ResponseModel(
            code=publish_response.code,
            message=f"Create plugin publish version failed: {publish_response.message}",
            data=None
        )

    # 7. 返回发布结果
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="Plugin published successfully",
        data=PluginPublishResponse(
            plugin_id=req.plugin_id,
            version=req.plugin_version,
            published_at=str(milliseconds())
        )
    )


@with_exception_handling
def plugin_publish_list(
        req: PluginId,
        current_user: dict
) -> ResponseModel:
    """
    发布插件

    Args:
        req: 插件发布列表请求
        current_user: 当前用户信息

    Returns:
        ResponseModel: 发布列表查询结果
    """
    # 1. 校验Space_id是否有权限
    _ = check_user_space(req.space_id, current_user)

    res = plugin_repository.plugin_publish_list(req.model_dump())
    list_result = ResponseModel(**res)
    logger.info(f"get plugin list from db result: {list_result}")
    if list_result.code != status.HTTP_200_OK and list_result.code != status.HTTP_404_NOT_FOUND:
        return ResponseModel(
            code=list_result.code,
            message=list_result.message,
        )

    infos: List[PluginPublishInfo] = []
    if list_result.data is not None:
        for info_dict in list_result.data:
            # 使用 from_db_with_mapping 将 inputs 映射为 request_params
            info = PluginPublishInfo.from_db_with_mapping(info_dict)
            infos.append(info)
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="plugin publish list success",
        data=PluginPublishListResponse(plugin_infos=infos)
    )


@with_exception_handling
def plugin_publish_get(
        req: PluginId,
        current_user: dict
) -> ResponseModel:
    """获取发布插件信息"""
    _ = check_user_space(req.space_id, current_user)

    res = plugin_repository.plugin_publish_get(req.model_dump())
    canvas_result = ResponseModel(**res)
    logger.info(f"get publish plugin info from db result: {canvas_result}")
    if canvas_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=canvas_result.code,
            message=canvas_result.message,
        )
    # 使用 from_db_with_mapping 将 inputs 映射为 request_params
    plugin_info = PluginPublishInfo.from_db_with_mapping(canvas_result.data)
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="get publish plugin success",
        data=PluginPublishInfoResponse(plugin_info=plugin_info)
    )


@with_exception_handling
def plugin_publish_delete(
        req: PluginId,
        current_user: dict
) -> ResponseModel:
    """删除已发布的插件"""
    _ = check_user_space(req.space_id, current_user)

    logger.info(f"delete publish plugin: {req}")
    res = plugin_repository.plugin_publish_delete(req.model_dump())
    delete_result = ResponseModel(**res)
    logger.info(f"delete publish plugin info in db result: {delete_result}")
    if delete_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=delete_result.code,
            message=delete_result.message,
        )

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="delete publish plugin success",
    )


@with_exception_handling
def plugin_read_market_json(
    req: PluginList,
    current_user: dict
) -> ResponseModel:
    """
    读取backend目录下的config.json文件内容并以JSON字符串形式返回

    Args:
        req: 用户空间
        current_user: 当前用户信息

    Returns:
        ResponseModel: 包含JSON文件内容的响应模型
    """
    # 1. 校验Space_id是否有权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 构造config.json文件路径
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../conf/"))
    config_file_path = os.path.join(base_dir, "config.json")
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            json_content = json.load(f)
        json_content["VITE_PLUGIN_SERVICE_URL"] = os.getenv("VITE_PLUGIN_SERVICE_URL", "")
        json_string = json.dumps(json_content, ensure_ascii=False, indent=2)

        return ResponseModel(
            code=status.HTTP_200_OK,
            message="JSON file read successfully",
            data=json_string
        )
    except FileNotFoundError:
        logger.error(f"JSON file not found: {config_file_path}")
        return ResponseModel(
            code=status.HTTP_404_NOT_FOUND,
            message=f"JSON file not found: {config_file_path}",
            data=""
        )
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format in file: {config_file_path}, error: {str(e)}")
        return ResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message=f"Invalid JSON format in file: {config_file_path}",
            data=""
        )
    except Exception as e:
        logger.error(f"Error reading JSON file: {str(e)}")
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Error reading JSON file: {str(e)}",
            data=""
        )


@with_exception_handling
def plugin_tool_update_available(
    tool_id: str,
    space_id: str,
    available: bool,
    plugin_version: str = None
) -> ResponseModel:
    """
    更新工具的可用状态（供运行面调用）

    当工具执行成功时，调用此方法将工具的 available 字段设置为 True
    当工具执行失败时，调用此方法将工具的 available 字段设置为 False

    Args:
        tool_id: 工具ID
        space_id: 空间ID
        available: 工具是否可用（True=可用，False=不可用）
        plugin_version: 插件版本（可选，默认使用 __version_none__）

    Returns:
        ResponseModel: 更新结果

    Example:
        # 工具执行成功后调用
        plugin_tool_update_available("tool_123", "space_456", True)

        # 工具执行失败后调用
        plugin_tool_update_available("tool_123", "space_456", False)
    """
    result = tool_repository.tool_update_available(
        tool_id=tool_id,
        space_id=space_id,
        available=available,
        plugin_version=plugin_version
    )

    if result.get("code") == status.HTTP_200_OK:
        logger.info(
            f"Tool available status updated: tool_id={tool_id}, "
            f"space_id={space_id}, available={available}"
        )
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="Tool available status updated successfully",
            data=result
        )
    else:
        logger.error(
            f"Failed to update tool available status: tool_id={tool_id}, "
            f"space_id={space_id}, error={result.get('message')}"
        )
        return ResponseModel(
            code=result.get("code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            message=result.get("message", "Failed to update tool available status"),
            data=result
        )