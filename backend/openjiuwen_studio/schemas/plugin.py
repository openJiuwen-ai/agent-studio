#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from enum import IntEnum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from openjiuwen_studio.core.common.url_validator import validate_plugin_url


class PluginType(IntEnum):
    PLUGIN_TYPE_CLOUD_API = 1,
    PLUGIN_TYPE_CLOUD_CODE = 2,
    PLUGIN_TYPE_CLOUD_MCP = 3,


class ParamType(IntEnum):
    PARAM_TYPE_STRING = 1,
    PARAM_TYPE_INT = 2,
    PARAM_TYPE_FLOAT = 3,
    PARAM_TYPE_BOOL = 4,
    PARAM_TYPE_OBJECT = 5,
    PARAM_TYPE_ARRAY_STRING = 6,
    PARAM_TYPE_ARRAY_INT = 7,
    PARAM_TYPE_ARRAY_FLOAT = 8,
    PARAM_TYPE_ARRAY_BOOL = 9,


class ParamSendMethod(IntEnum):
    PARAM_SEND_METHOD_NONE = 0,
    PARAM_SEND_METHOD_HEADER = 1,
    PARAM_SEND_METHOD_QUERY = 2,
    PARAM_SEND_METHOD_BODY = 3,
    PARAM_SEND_METHOD_PATH = 4,


class Priority(IntEnum):
    PRIORITY_TOOL = 0,
    PRIORITY_PLUGIN = 1,


class PluginToolParam(BaseModel):
    name: str = Field(..., alias="name")
    desc: Optional[str] = Field("", alias="desc")
    type: ParamType = Field(..., alias="type")
    is_required: Optional[bool] = Field(False, alias="is_required")
    method: Optional[ParamSendMethod] = Field(ParamSendMethod.PARAM_SEND_METHOD_NONE, alias="method")
    is_runtime: Optional[bool] = Field(True, alias="is_runtime")
    value: Optional[str] = Field("", alias="value")
    priority: Optional[Priority] = Field(Priority.PRIORITY_TOOL, alias="priority")


class PluginCreate(BaseModel):
    name: str = Field(..., alias="name")
    desc: str = Field(..., alias="desc")
    desc_mk: Optional[str] = Field("", alias="desc_mk")
    space_id: str = Field(alias="space_id")
    plugin_type: PluginType = Field(..., alias="plugin_type")
    url: Optional[str] = Field("", alias="url")
    icon_uri: Optional[str] = Field("", alias="icon_uri")
    auth: Optional[Any] = Field(None, alias="auth")
    request_params: Optional[List[PluginToolParam]] = Field([], alias="request_params")
    header_configuration: Optional[Any] = Field(None, alias="header_configuration")
    mcp_transport: Optional[int] = Field(None, alias="mcp_transport")
    external_plugin_type: Optional[str] = Field(None, alias="external_plugin_type")
    category: Optional[str] = Field(None, alias="category")
    category_name: Optional[str] = Field(None, alias="category_name")
    market_source: Optional[str] = Field(None, alias="market_source")
    original_market_plugin_id: Optional[str] = Field(None, alias="original_market_plugin_id")
    # stdio transport fields
    command: Optional[str] = Field("", alias="command")
    args: Optional[List[str]] = Field(default_factory=list, alias="args")
    env: Optional[Dict[str, str]] = Field(None, alias="env")

    @staticmethod
    def _is_local_file_path(value: str) -> bool:
        """Return True if *value* looks like a local filesystem path rather than a URL."""
        if value.startswith("/") or value.startswith("./") or value.startswith("../"):
            return True
        if value.startswith("~/"):
            return True
        return len(value) > 2 and value[1] == ":"  # Windows drive letter, e.g. C:\

    @field_validator("url", mode="after")
    @classmethod
    def check_url_ssrf(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        # Allow file paths (absolute or relative) for local files
        # Examples: /Users/..., ./file.yaml, ~/file.yaml, C:\path\file.yaml
        if isinstance(v, str) and cls._is_local_file_path(v):
            return v
        return validate_plugin_url(v)

    def model_post_init(self, __context) -> None:
        """Validate MCP plugin requirements after model initialization"""
        # Constants matching PluginMcpTransport enum (defined later in this file)
        openapi = 4
        sse = 2
        streamable_http = 3

        # For MCP plugins with OPENAPI transport, URL/path is required
        if self.plugin_type == PluginType.PLUGIN_TYPE_CLOUD_MCP and self.mcp_transport == openapi:
            if not self.url:
                raise ValueError(
                    "For MCP plugins with OPENAPI transport (external_plugin_type='openai'), "
                    "a URL or file path is required. Provide either:\n"
                    "  - URL: 'https://api.openai.com/v1'\n"
                    "  - Local file: '/path/to/openapi.yaml' or './openapi.yaml'"
                )

        # For MCP plugins with SSE/HTTP transports, URL is required (not local file)
        if (self.plugin_type == PluginType.PLUGIN_TYPE_CLOUD_MCP and
            self.mcp_transport in [sse, streamable_http]):
            if not self.url:
                raise ValueError(
                    f"For MCP plugins with transport type {self.mcp_transport}, "
                    "a valid URL is required."
                )
            # SSE/HTTP transports require URL (not local file path)
            if isinstance(self.url, str) and not self.url.startswith("http"):
                raise ValueError(
                    f"For MCP plugins with transport type {self.mcp_transport}, "
                    "a URL with http/https scheme is required (local file paths are not supported). "
                    f"Received: {self.url}"
                )


class PluginId(BaseModel):
    space_id: str = Field(alias="space_id")
    plugin_id: str = Field(alias="plugin_id")
    plugin_version: Optional[str] = Field("", alias="plugin_version")


class PluginBase(PluginId):
    plugin_type: Optional[PluginType] = Field(PluginType.PLUGIN_TYPE_CLOUD_API, alias="plugin_type")


class PluginList(BaseModel):
    space_id: str = Field(alias="space_id")
    page: Optional[int] = Field(1, ge=1, alias="page")
    size: Optional[int] = Field(10, ge=1, le=100, alias="size")
    market_source: Optional[str] = Field("local", alias="market_source")


class PluginMarketDetailRequest(BaseModel):
    space_id: str = Field(alias="space_id")
    plugin_id: str = Field(alias="plugin_id")
    plugin_version: Optional[str] = Field("", alias="plugin_version")
    market_source: Optional[str] = Field("local", alias="market_source")
    include_contract: Optional[bool] = Field(False, alias="include_contract")


class PluginMarketInstallRequest(BaseModel):
    space_id: str = Field(alias="space_id")
    plugin_id: str = Field(alias="plugin_id")
    plugin_version: Optional[str] = Field("", alias="plugin_version")
    market_source: Optional[str] = Field("local", alias="market_source")


class PluginPublish(PluginId):
    version_desc: Optional[str] = Field("", alias="version_desc")
    force: Optional[bool] = Field(False, alias="force")


class PluginApiHeader(BaseModel):
    name: str = Field(..., alias="name")
    value: str = Field("", alias="value")
    description: Optional[str] = Field("", alias="description")


class PluginInfo(PluginBase):
    name: str = Field(..., alias="name")
    desc: str = Field(..., alias="desc")
    desc_mk: Optional[str] = Field("", alias="desc_mk")
    published: bool = Field(False, alias="published")
    url: Optional[str] = Field("", alias="url")
    icon_uri: Optional[str] = Field("", alias="icon_uri")
    auth: Optional[Any] = Field(None, alias="auth")
    request_params: Optional[List[PluginToolParam]] = Field([], alias="request_params")
    header_configuration: Optional[Any] = Field(None, alias="header_configuration")
    mcp_transport: Optional[int] = Field(None, alias="mcp_transport")
    external_plugin_type: Optional[str] = Field(None, alias="external_plugin_type")
    original_market_plugin_id: Optional[str] = Field(None, alias="original_market_plugin_id")
    category: Optional[str] = Field(None, alias="category")
    category_name: Optional[str] = Field(None, alias="category_name")
    category_icon: Optional[str] = Field(None, alias="category_icon")
    market_source: Optional[str] = Field(None, alias="market_source")
    ready: Optional[bool] = Field(None, alias="ready")
    tags: Optional[List[str]] = Field(None, alias="tags")
    status: Optional[str] = Field(None, alias="status")
    config: Optional[Dict[str, Any]] = Field(None, alias="config")
    original_data: Optional[Dict[str, Any]] = Field(None, alias="original_data")
    market_detail_snapshot: Optional[Dict[str, Any]] = Field(None, alias="market_detail_snapshot")
    author: Optional[str] = Field(None, alias="author")
    detail_desc: Optional[str] = Field(None, alias="detail_desc")
    plugin_version: Optional[str] = Field("", alias="plugin_version")
    space_id: Optional[str] = Field(None, alias="space_id")
    plugin_id: Optional[str] = Field(None, alias="plugin_id")

    @field_validator("url")
    @classmethod
    def check_url_ssrf(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        if isinstance(v, str) and v.startswith("/"):
            return v
        return validate_plugin_url(v)

    class Config:
        populate_by_name = True

    @classmethod
    def from_db_with_mapping(cls, data: Dict[str, Any]) -> "PluginInfo":
        """从数据库数据创建对象，将 inputs 字段映射为 request_params"""
        # 如果数据是 Pydantic 模型对象，先转换为字典
        if hasattr(data, 'model_dump'):
            data_dict = data.model_dump()
        elif hasattr(data, 'dict'):
            data_dict = data.dict()
        else:
            data_dict = data

        # 如果数据中有 inputs 字段，映射到 request_params
        if "inputs" in data_dict and data_dict["inputs"] is not None:
            data_dict["request_params"] = data_dict.pop("inputs")

        # Extract extra metadata from _rest_ if present
        rest = data_dict.get("_rest_")
        if isinstance(rest, dict) and isinstance(rest.get("_rest_"), dict):
            rest = rest.get("_rest_")
            data_dict["_rest_"] = rest
        if isinstance(rest, dict):
            if "mcp_transport" in rest:
                data_dict["mcp_transport"] = rest["mcp_transport"]
            for key in (
                "auth",
                "external_plugin_type",
                "original_market_plugin_id",
                "category",
                "category_name",
                "category_icon",
                "market_source",
                "ready",
                "tags",
                "status",
                "config",
                "original_data",
                "market_detail_snapshot",
                "author",
                "detail_desc",
            ):
                if key not in rest:
                    continue
                current_value = data_dict.get(key)
                if current_value in (None, "", [], {}):
                    data_dict[key] = rest[key]

            data_market_detail_snapshot = data_dict.get("market_detail_snapshot") or {}
            data_market_detail_config = data_market_detail_snapshot.get("config") or {}
            data_config = data_dict.get("config") or {}
            original_data = data_dict.get("original_data") or {}
            original_market_detail_snapshot = original_data.get("market_detail_snapshot") or {}
            original_market_detail_config = original_market_detail_snapshot.get("config") or {}
            original_config = original_data.get("config") or {}
            rest_market_detail_snapshot = rest.get("market_detail_snapshot") or {}
            rest_market_detail_config = rest_market_detail_snapshot.get("config") or {}
            rest_config = rest.get("config") or {}
            header_config_candidates = (
                data_market_detail_snapshot.get("header_configuration"),
                data_market_detail_config.get("header_configuration"),
                data_config.get("header_configuration"),
                original_market_detail_snapshot.get("header_configuration"),
                original_market_detail_config.get("header_configuration"),
                original_config.get("header_configuration"),
                rest.get("header_configuration"),
                rest_market_detail_snapshot.get("header_configuration"),
                rest_market_detail_config.get("header_configuration"),
                rest_config.get("header_configuration"),
            )
            header_configuration = next(
                (candidate for candidate in header_config_candidates if candidate),
                None,
            )
            if header_configuration:
                data_dict["header_configuration"] = header_configuration

            if not data_dict.get("auth"):
                auth_candidates = (
                    data_market_detail_snapshot.get("auth"),
                    data_market_detail_config.get("auth"),
                    data_config.get("auth"),
                    original_market_detail_snapshot.get("auth"),
                    original_market_detail_config.get("auth"),
                    original_config.get("auth"),
                    rest.get("auth"),
                    rest_market_detail_snapshot.get("auth"),
                    rest_market_detail_config.get("auth"),
                    rest_config.get("auth"),
                )
                auth_data = next((candidate for candidate in auth_candidates if candidate), None)
                if auth_data:
                    data_dict["auth"] = auth_data

        return cls(**data_dict)


class PluginInfoResponse(BaseModel):
    plugin_info: PluginInfo = Field(..., alias="plugin_info")


class PluginListPagination(BaseModel):
    total: int = Field(..., ge=0, alias="total")
    total_pages: int = Field(..., ge=0, alias="total_pages")
    page: int = Field(..., ge=1, alias="page")
    page_size: int = Field(..., ge=1, alias="page_size")


class PluginListResponse(BaseModel):
    plugin_infos: List[PluginInfo] = Field(..., alias="plugin_infos")
    pagination: PluginListPagination = Field(..., alias="pagination")


class PluginToolId(PluginId):
    tool_id: str = Field(..., alias="tool_id")


class ToolId(BaseModel):
    space_id: str = Field(alias="space_id")
    tool_id: str = Field(..., alias="tool_id")


class PluginApiMethod(IntEnum):
    PLUGIN_API_METHOD_GET = 1,
    PLUGIN_API_METHOD_POST = 2,
    PLUGIN_API_METHOD_PUT = 3,
    PLUGIN_API_METHOD_DELETE = 4,
    PLUGIN_API_METHOD_PATCH = 5,


class PluginMcpTransport(IntEnum):
    PLUGIN_MCP_TRANSPORT_STDIO = 1,
    PLUGIN_MCP_TRANSPORT_SSE = 2,
    PLUGIN_MCP_TRANSPORT_STREAMABLE_HTTP = 3,
    PLUGIN_MCP_TRANSPORT_OPENAPI = 4,
    PLUGIN_MCP_TRANSPORT_PLAYWRIGHT = 5,


class PluginApiBase(PluginBase):
    name: str = Field(..., alias="name")
    desc: str = Field(..., alias="desc")
    path: str = Field(..., alias="path")
    method: PluginApiMethod = Field(..., alias="method")


class PluginListTool(PluginId):
    page: Optional[int] = Field(0, alias="page")
    size: Optional[int] = Field(0, alias="size")


class PluginApiInfo(PluginApiBase):
    tool_id: str = Field(..., alias="tool_id")
    request_params: Optional[List[PluginToolParam]] = Field([], alias="request_params")
    response_params: Optional[List[PluginToolParam]] = Field([], alias="response_params")
    headers: Optional[List[PluginApiHeader]] = Field([], alias="headers")
    available: Optional[bool] = Field(False, alias="available")


class PluginApiInfoCreate(PluginApiBase):
    request_params: Optional[List[PluginToolParam]] = Field([], alias="request_params")
    response_params: Optional[List[PluginToolParam]] = Field([], alias="response_params")
    headers: Optional[List[PluginApiHeader]] = Field([], alias="headers")
    available: Optional[bool] = Field(False, alias="available")


class PluginApiInfoDB(PluginApiInfo):
    input_parameters: Optional[List[Dict[str, Any]]] = Field([], alias="input_parameters")
    output_parameters: Optional[List[Dict[str, Any]]] = Field([], alias="output_parameters")


class PluginApiInfoResponse(BaseModel):
    api_info: List[PluginApiInfo] = Field(..., alias="api_info")
    total: int = Field(..., alias="total")


class PluginCodeBase(PluginBase):
    name: str = Field(..., alias="name")
    desc: str = Field(..., alias="desc")
    language: str = Field(..., alias="language")
    code: str = Field(..., alias="code")


class PluginCodeInfo(PluginCodeBase):
    tool_id: str = Field(..., alias="tool_id")
    request_params: Optional[List[PluginToolParam]] = Field([], alias="request_params")
    response_params: Optional[List[PluginToolParam]] = Field([], alias="response_params")
    available: Optional[bool] = Field(False, alias="available")


class PluginCodeInfoDB(PluginCodeInfo):
    input_parameters: Optional[List[Dict[str, Any]]] = Field([], alias="input_parameters")
    output_parameters: Optional[List[Dict[str, Any]]] = Field([], alias="output_parameters")


class PluginCodeInfoResponse(BaseModel):
    code_info: List[PluginCodeInfo] = Field(..., alias="code_info")
    total: int = Field(..., alias="total")


class PluginMcpBase(PluginBase):
    name: str = Field(..., alias="name")
    desc: str = Field(..., alias="desc")
    transport: PluginMcpTransport = Field(PluginMcpTransport.PLUGIN_MCP_TRANSPORT_STDIO, alias="transport")
    command: Optional[str] = Field("", alias="command")
    args: Optional[List[str]] = Field(default_factory=list, alias="args")
    env: Optional[Dict[str, str]] = Field(None, alias="env")
    url: Optional[str] = Field("", alias="url")
    headers: Optional[Dict[str, str]] = Field(None, alias="headers")
    mcp_tool_name: str = Field("", alias="mcp_tool_name")


class PluginMcpInfo(PluginMcpBase):
    tool_id: str = Field(..., alias="tool_id")
    request_params: Optional[List[PluginToolParam]] = Field([], alias="request_params")
    response_params: Optional[List[PluginToolParam]] = Field([], alias="response_params")
    available: Optional[bool] = Field(False, alias="available")


class PluginMcpInfoDB(PluginMcpInfo):
    input_parameters: Optional[List[Dict[str, Any]]] = Field([], alias="input_parameters")
    output_parameters: Optional[List[Dict[str, Any]]] = Field([], alias="output_parameters")


class PluginMcpInfoResponse(BaseModel):
    mcp_info: List[PluginMcpInfo] = Field(..., alias="mcp_info")
    total: int = Field(..., alias="total")


class PluginPublishResponse(BaseModel):
    """Plugin publish response model"""
    plugin_id: str = Field(..., alias="plugin_id")
    version: str = Field(..., alias="version")
    published_at: str = Field(..., alias="published_at")


class PluginPublishInfo(PluginInfo):
    version_desc: Optional[str] = Field("", alias="version_desc")
    tools: List[Dict] = Field(..., alias="tools")
    headers: Optional[List[PluginApiHeader]] = Field([], alias="headers")

    @classmethod
    def from_db_with_mapping(cls, data: Dict[str, Any]) -> "PluginPublishInfo":
        """从数据库数据创建对象，将 inputs 字段映射为 request_params"""
        # 如果数据是 Pydantic 模型对象，先转换为字典
        if hasattr(data, 'model_dump'):
            data_dict = data.model_dump()
        elif hasattr(data, 'dict'):
            data_dict = data.dict()
        else:
            data_dict = data

        # 如果数据中有 inputs 字段，映射到 request_params
        if "inputs" in data_dict and data_dict["inputs"] is not None:
            data_dict["request_params"] = data_dict.pop("inputs")
        return cls(**data_dict)


class PluginPublishInfoResponse(BaseModel):
    plugin_info: PluginPublishInfo = Field(..., alias="plugin_info")


class PluginPublishListResponse(BaseModel):
    plugin_infos: List[PluginPublishInfo] = Field(..., alias="plugin_infos")
