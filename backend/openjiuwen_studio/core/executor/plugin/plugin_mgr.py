#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Any, Dict, Optional
from fastapi import status
from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.common.dsl import RestfulApiSchema as DlRestfulApiSchema
from openjiuwen_studio.core.common.dsl import Plugin as DlPlugin
from openjiuwen_studio.core.common.dsl import PluginCodeConfig as DlPluginCodeConfig
from openjiuwen_studio.core.common.dsl import PluginType
from openjiuwen_studio.core.executor.plugin.plugin_tools import CodeTool, ServiceTool
import openjiuwen_studio.core.manager.plugin as mgr
from openjiuwen_studio.schemas.plugin import ToolId, PluginId
from openjiuwen_studio.core.common.exceptions import JiuWenExecuteException
from openjiuwen_studio.core.common.status_code import StatusCode
from openjiuwen_studio.core.manager.convertor.components.plugin import plugin_type_mapping
from openjiuwen_studio.core.manager.convertor.plugin import plugin_tool_convert
from openjiuwen_studio.core.manager.plugin import plugin_tool_update_available


async def _fetch_plugin_dl(
        tool_id: str,
        space_id: str,
        plugin_id: str,
        version: str,
        current_user: Optional[Dict[str, Any]]
) -> Any:
    if not current_user:
        import os
        from openjiuwen_studio.core.utils.file import read_file_to_string
        path = os.path.dirname(__file__)
        file_path = os.path.join(path, '../../../tests/resources/plugin_dl.json')
        dl_str = read_file_to_string(file_path)
        plugin = DlPlugin.model_validate_json(dl_str)
        return plugin
    plugin_dl = None
    if version == "draft" or version == "":
        req = {"tool_id": tool_id, "space_id": space_id}
        res = mgr.plugin_convert(ToolId(**req), current_user)
        if res.code != status.HTTP_200_OK:
            raise JiuWenExecuteException(
                StatusCode.PLUGIN_DL_FETCH_FAILED.code,
                message=StatusCode.PLUGIN_DL_FETCH_FAILED.errmsg.format(msg=str(res.message)),
                node_id=tool_id
            )
        plugin_dl = res.data
    else:
        req = {"plugin_id": plugin_id, "space_id": space_id, "plugin_version": version}
        res = mgr.plugin_publish_get(PluginId(**req), current_user)
        plugin_publish_dsl = res.data
        if plugin_publish_dsl is None:
            raise JiuWenExecuteException(
                code=StatusCode.PLUGIN_DL_FETCH_FAILED.code,
                message=StatusCode.PLUGIN_DL_FETCH_FAILED.errmsg.format(
                    msg=str(f"fetch plugin failed with version: {version}")),
                node_id=tool_id
            )
        tools = plugin_publish_dsl.plugin_info.tools
        for tool in tools:
            if tool.get("tool_id") == tool_id:
                convert_tools = plugin_tool_convert(plugin_publish_dsl.plugin_info, tool)
                plugin_dl = DlPlugin(
                    plugin_id=plugin_id,
                    plugin_name=plugin_publish_dsl.plugin_info.name,
                    plugin_description=plugin_publish_dsl.plugin_info.desc,
                    plugin_type=plugin_type_mapping[plugin_publish_dsl.plugin_info.plugin_type],
                    tools=convert_tools,
                    plugin_version=plugin_publish_dsl.plugin_info.plugin_version,
                )
    if plugin_dl is None:
        raise JiuWenExecuteException(
            code=StatusCode.PLUGIN_DL_FETCH_FAILED.code,
            message=StatusCode.PLUGIN_DL_FETCH_FAILED.errmsg.format(msg=str("fetch plugin dl failed")),
            node_id=tool_id
        )
    logger.warning(f"fetch plugin dl: {plugin_dl.model_dump_json()}")
    return plugin_dl


class PluginManager:
    def __init__(self) -> None:
        pass

    async def get_tool(
            self,
            tool_id: str,
            space_id: str,
            plugin_id: str,
            version: str,
            current_user: Optional[Dict[str, Any]]
    ) -> Any:
        logger.warning(f"get_tool: tool_id={tool_id}")
        plugin = await _fetch_plugin_dl(tool_id, space_id, plugin_id, version, current_user)
        tool = None
        for tool_dl in plugin.tools:
            logger.warning(f"tool_dl: {tool_dl}, type: {type(tool_dl)}")
            if tool_dl["tool_id"] == tool_id:
                if plugin.plugin_type == PluginType.SERVICE:
                    tool = ServiceTool(DlRestfulApiSchema.model_validate(tool_dl))
                else:
                    tool = CodeTool(DlPluginCodeConfig.model_validate(tool_dl))
                break
        return tool

    async def get_compiled_tool(
            self,
            plugin_id: str,
            tool_id: str,
            space_id: str,
            version: str,
            current_user: Optional[Dict[str, Any]]
    ) -> Any:
        logger.warning(f"get_compiled_tool: plugin_id={plugin_id} tool_id={tool_id}")
        tool = await self.get_tool(tool_id, space_id, plugin_id, version, current_user)
        if not tool:
            raise JiuWenExecuteException(
                code=StatusCode.PLUGIN_COMPILE_FAILED.code,
                message=StatusCode.PLUGIN_COMPILE_FAILED.errmsg.format(
                    msg=str(f"can not find tool with plugin_id={plugin_id} tool_id={tool_id}")),
                node_id=tool_id
            )
        compiled_tool = tool.compile()
        return compiled_tool

    async def run(
            self,
            plugin_id: str,
            tool_id: str,
            inputs: Any,
            space_id: str,
            version: str,
            current_user: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        tool = await self.get_compiled_tool(plugin_id, tool_id, space_id, version, current_user)
        data = await tool.invoke(inputs, raise_for_status=False)
        # 记录 HTTP 调用结果
        http_code = data.get("code")
        if http_code != status.HTTP_200_OK and http_code != 0:
            logger.error(
                f"Plugin tool HTTP request failed: "
                f"plugin_id={plugin_id}, tool_id={tool_id}, "
                f"http_code={http_code}, reason={data.get('reason')}, "
                f"url={data.get('url')}, "
                f"response={data.get('data')}"
            )
        else:
            logger.info(
                f"Plugin tool HTTP request succeeded: "
                f"plugin_id={plugin_id}, tool_id={tool_id}, "
                f"http_code={http_code}"
            )

        available = True
        if http_code != status.HTTP_200_OK and http_code != 0:
            available = False
        available_res = plugin_tool_update_available(tool_id, space_id, available, version)

        # 永不覆盖原始 HTTP 状态码
        if available_res.code != status.HTTP_200_OK:
            # 记录可用性更新失败
            logger.warning(
                f"Failed to update plugin availability status: "
                f"tool_id={tool_id}, space_id={space_id}, version={version}, "
                f"error_code={available_res.code}, error_message={available_res.message}"
            )
            # 将可用性更新错误作为附加信息，不覆盖主错误码
            if "metadata" not in data:
                data["metadata"] = {}
            data["metadata"]["availability_update_failed"] = {
                "code": available_res.code,
                "message": available_res.message
            }

        # 如果原始调用成功，但可用性更新失败，添加警告但不改变成功状态
        if (http_code == status.HTTP_200_OK or http_code == 0) and available_res.code != status.HTTP_200_OK:
            data["warning"] = f"Tool executed successfully but availability update failed: {available_res.message}"

        return PluginManager.result_convert(data)

    @staticmethod
    def result_convert(data: Any) -> Dict[str, Any]:
        from openjiuwen_studio.core.common.message import ExecuteResponseType, ExecuteResponse

        # 提取用户友好的错误消息
        error_message = data.get("message", "success")
        response_data = data.get("data")

        # 如果响应数据中包含更详细的错误信息，优先使用
        if response_data and isinstance(response_data, dict):
            # 检查是否有 OpenAI 格式的错误响应
            if "error" in response_data and isinstance(response_data["error"], dict):
                error_info = response_data["error"]
                # 优先使用 error.message，其次 error.type
                if "message" in error_info:
                    error_message = error_info["message"]
                elif "type" in error_info:
                    error_message = error_info["type"]

        payload = {
            "error_code": data.get("code"),
            "error_message": error_message,
            "output": response_data,
        }

        # 透传HTTP响应详细信息，便于前端调试
        if "url" in data:
            payload["url"] = data.get("url")
        if "headers" in data:
            payload["headers"] = data.get("headers")
        if "reason" in data:
            payload["reason"] = data.get("reason")

        return ExecuteResponse(
            type=ExecuteResponseType.Plugin,
            payload=payload
        ).model_dump()


plugin_mgr = PluginManager()
