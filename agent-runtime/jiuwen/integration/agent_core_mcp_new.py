"""Agent-core MCP layer with jiuwen-compatible southbound interface."""

import asyncio
import inspect
from dataclasses import dataclass, field
from typing import Any

from jiuwen.orchestration import Invokable


@dataclass
class McpCallContext:
    """Normalized MCP call context passed across the layer boundary."""

    inputs: dict[str, Any]
    tool_id: str
    agent_id: str
    session_id: str
    context: Any = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentCoreMcpLayerOptions:
    """Optional MCP tool metadata when constructing AgentCoreMcpLayer without mcp_api."""

    name: str = ""
    description: str = ""
    parameters: dict[str, Any] | None = None
    headers: dict[str, Any] | None = None
    auth: dict[str, Any] | None = None
    plugin_dependency: dict[str, Any] | None = None
    server_name: str = ""
    server_url: str = ""
    transport_type: str = ""
    params: list[Any] | None = None


class _FallbackMcpAPIState:
    """Lightweight metadata holder when legacy MCP dependencies are unavailable."""

    def __init__(
        self,
        *,
        server_url: str,
        name: str,
        parameters: dict[str, Any],
        headers: dict[str, Any],
        server_name: str,
        transport_type: str,
        plugin_dependency: dict[str, Any] | None = None,
        auth: dict[str, Any] | None = None,
        description: str = "",
        params: list[Any] | None = None,
    ) -> None:
        self.server_url = server_url
        self.name = name
        self.parameters = parameters or {}
        self.params = params or []
        self.headers = headers or {}
        self.description = description
        self.server_name = server_name
        self.transport_type = transport_type
        self.is_mcp = True
        self.auth = auth or {}
        self.plugin_dependency = plugin_dependency or {}


class AgentCoreMcpLayer(Invokable[dict[str, Any], dict[str, Any]]):
    """Adapt agent-core MCP runtime to jiuwen's historical McpAPI-like contract."""

    # 旧版关键字参数（经 **legacy_tool_meta 接收，保持对外兼容且避免形参过多）
    _LEGACY_OPTION_KEYS = frozenset(
        {
            "name",
            "description",
            "parameters",
            "headers",
            "auth",
            "plugin_dependency",
            "server_name",
            "server_url",
            "transport_type",
            "params",
        }
    )

    def __init__(
        self,
        runtime: Any | None = None,
        *,
        mcp_api: Any | None = None,
        tool_id: str = "",
        agent_id: str = "",
        session_id: str = "",
        options: AgentCoreMcpLayerOptions | None = None,
        **legacy_tool_meta: Any,
    ) -> None:
        """Initialize a compatibility layer for a single MCP tool runtime.

        Prefer ``options=AgentCoreMcpLayerOptions(...)``. Legacy keyword args
        (``name`` / ``description`` / ``parameters`` / ...) remain accepted and
        merge into options for backward compatibility.
        """
        super().__init__()
        unknown = set(legacy_tool_meta) - self._LEGACY_OPTION_KEYS
        if unknown:
            raise TypeError(
                "AgentCoreMcpLayer.__init__() got unexpected keyword argument(s): "
                f"{sorted(unknown)}"
            )
        opts = self._merge_options(options, legacy_tool_meta)
        self.runtime = runtime or self._create_runtime(
            tool_id=tool_id,
            agent_id=agent_id,
            session_id=session_id,
        )
        self._tool_id = tool_id or str(getattr(self.runtime, "_tool_id", "") or "")
        self._agent_id = agent_id or str(getattr(self.runtime, "_agent_id", "") or "")
        self._session_id = session_id or str(
            getattr(self.runtime, "_session_id", "") or ""
        )
        self.mcp_api = mcp_api or self._create_mcp_api(
            server_url=opts.server_url
            or str(getattr(self.runtime, "server_url", "") or ""),
            name=opts.name or str(getattr(self.runtime, "name", "") or self._tool_id),
            parameters=opts.parameters
            or dict(getattr(self.runtime, "parameters", {}) or {}),
            headers=opts.headers or dict(getattr(self.runtime, "headers", {}) or {}),
            server_name=opts.server_name
            or str(getattr(self.runtime, "server_name", "") or ""),
            transport_type=opts.transport_type
            or str(getattr(self.runtime, "transport_type", "") or ""),
            plugin_dependency=opts.plugin_dependency
            or dict(getattr(self.runtime, "plugin_dependency", {}) or {}),
            auth=opts.auth or dict(getattr(self.runtime, "auth", {}) or {}),
            description=opts.description
            or str(getattr(self.runtime, "description", "") or ""),
            params=opts.params
            if opts.params is not None
            else list(getattr(self.runtime, "params", []) or []),
        )

    @staticmethod
    def _merge_options(
        options: AgentCoreMcpLayerOptions | None,
        legacy_tool_meta: dict[str, Any],
    ) -> AgentCoreMcpLayerOptions:
        """Merge options dataclass with legacy kwargs; explicit legacy wins."""
        base = options or AgentCoreMcpLayerOptions()
        if not legacy_tool_meta:
            return base
        merged = {
            "name": base.name,
            "description": base.description,
            "parameters": base.parameters,
            "headers": base.headers,
            "auth": base.auth,
            "plugin_dependency": base.plugin_dependency,
            "server_name": base.server_name,
            "server_url": base.server_url,
            "transport_type": base.transport_type,
            "params": base.params,
        }
        merged.update(legacy_tool_meta)
        return AgentCoreMcpLayerOptions(**merged)

    @staticmethod
    def _create_runtime(*, tool_id: str, agent_id: str, session_id: str) -> Any:
        """Create the default MCP runtime lazily to avoid importing optional deps on load."""
        from jiuwen.extension.wrapper import ToolType, ToolWrapper

        return ToolWrapper(
            tool_id=tool_id,
            agent_id=agent_id,
            session_id=session_id,
            tool_type=ToolType.MCP,
        )

    @staticmethod
    def _create_mcp_api(**kwargs: Any) -> Any:
        """Build a legacy-style McpAPI object, or a metadata-only fallback when deps are absent."""
        try:
            from jiuwen.plugin.models.mcpapi import McpAPI

            return McpAPI(**kwargs)
        except Exception:
            return _FallbackMcpAPIState(**kwargs)

    @property
    def tool_id(self):
        return self._tool_id

    @property
    def agent_id(self):
        return self._agent_id

    @property
    def session_id(self):
        return self._session_id

    @property
    def name(self) -> str:
        """Return the callable MCP tool name."""
        return self.mcp_api.name

    @name.setter
    def name(self, value: str) -> None:
        """Keep assignment-compatible behavior for legacy callers."""
        self.mcp_api.name = value or ""

    @property
    def description(self) -> str:
        """Return the MCP tool description."""
        return self.mcp_api.description

    @description.setter
    def description(self, value: str) -> None:
        """Keep assignment-compatible behavior for legacy callers."""
        self.mcp_api.description = value or ""

    @property
    def parameters(self) -> dict[str, Any]:
        """Return MCP parameter schema."""
        return self.mcp_api.parameters

    @parameters.setter
    def parameters(self, value: dict[str, Any] | None) -> None:
        """Keep assignment-compatible behavior for legacy callers."""
        self.mcp_api.parameters = value or {}

    @property
    def headers(self) -> dict[str, Any]:
        """Return MCP headers metadata."""
        return self.mcp_api.headers

    @headers.setter
    def headers(self, value: dict[str, Any] | None) -> None:
        """Keep assignment-compatible behavior for legacy callers."""
        self.mcp_api.headers = value or {}

    @property
    def auth(self) -> dict[str, Any]:
        """Return MCP auth metadata."""
        return self.mcp_api.auth

    @auth.setter
    def auth(self, value: dict[str, Any] | None) -> None:
        """Keep assignment-compatible behavior for legacy callers."""
        self.mcp_api.auth = value or {}

    @property
    def plugin_dependency(self) -> dict[str, Any]:
        """Return plugin dependency metadata."""
        return self.mcp_api.plugin_dependency

    @plugin_dependency.setter
    def plugin_dependency(self, value: dict[str, Any] | None) -> None:
        """Keep assignment-compatible behavior for legacy callers."""
        self.mcp_api.plugin_dependency = value or {}

    @property
    def server_name(self) -> str:
        """Return MCP server display name."""
        return self.mcp_api.server_name

    @server_name.setter
    def server_name(self, value: str) -> None:
        """Keep assignment-compatible behavior for legacy callers."""
        self.mcp_api.server_name = value or ""

    @property
    def server_url(self) -> str:
        """Return MCP server URL."""
        return self.mcp_api.server_url

    @server_url.setter
    def server_url(self, value: str) -> None:
        """Keep assignment-compatible behavior for legacy callers."""
        self.mcp_api.server_url = value or ""

    @property
    def transport_type(self) -> str:
        """Return MCP transport type."""
        return self.mcp_api.transport_type

    @transport_type.setter
    def transport_type(self, value: str) -> None:
        """Keep assignment-compatible behavior for legacy callers."""
        self.mcp_api.transport_type = value or ""

    @property
    def params(self) -> list[Any]:
        """Return original parameter descriptors when present."""
        return self.mcp_api.params

    @params.setter
    def params(self, value: list[Any] | None) -> None:
        """Keep assignment-compatible behavior for legacy callers."""
        self.mcp_api.params = value or []

    @property
    def is_mcp(self) -> bool:
        """Return MCP identity flag used by legacy code paths."""
        return self.mcp_api.is_mcp

    @is_mcp.setter
    def is_mcp(self, value: bool) -> None:
        """Keep assignment-compatible behavior for legacy callers."""
        self.mcp_api.is_mcp = bool(value)

    def invoke(
        self,
        inputs: dict[str, Any],
        tool_id: str = "",
        agent_id: str = "",
        session_id: str = "",
        context: Any = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Invoke MCP runtime synchronously for compatibility with Invokable checks."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                self.ainvoke(
                    inputs=inputs,
                    tool_id=tool_id,
                    agent_id=agent_id,
                    session_id=session_id,
                    context=context,
                    **kwargs,
                )
            )
        raise RuntimeError(
            "AgentCoreMcpLayer.invoke is not supported inside a running event loop. Use ainvoke()."
        )

    async def ainvoke(
        self,
        inputs: dict[str, Any],
        tool_id: str = "",
        agent_id: str = "",
        session_id: str = "",
        context: Any = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Invoke MCP runtime through a jiuwen-compatible async interface."""
        call = self._normalize_call(
            inputs=inputs,
            tool_id=tool_id,
            agent_id=agent_id,
            session_id=session_id,
            context=context,
            extra=kwargs,
        )
        result = self.runtime.ainvoke(
            call.inputs,
            tool_id=call.tool_id,
            agent_id=call.agent_id,
            session_id=call.session_id,
            context=call.context,
            **call.extra,
        )
        if inspect.isawaitable(result):
            return await result
        return result

    def _normalize_call(
        self,
        *,
        inputs: dict[str, Any],
        tool_id: str,
        agent_id: str,
        session_id: str,
        context: Any,
        extra: dict[str, Any],
    ) -> McpCallContext:
        """Normalize legacy-call and envelope-call shapes into one runtime call."""
        normalized_inputs = inputs
        normalized_tool_id = tool_id
        normalized_agent_id = agent_id
        normalized_session_id = session_id
        normalized_context = context
        normalized_extra = dict(extra)

        if isinstance(inputs, dict) and "inputs" in inputs:
            normalized_inputs = inputs.get("inputs") or {}
            normalized_tool_id = normalized_tool_id or self._get_first_value(
                inputs, "tool_id", "toolId"
            )
            normalized_agent_id = normalized_agent_id or self._get_first_value(
                inputs, "agent_id", "agentId"
            )
            normalized_session_id = normalized_session_id or self._get_first_value(
                inputs, "session_id", "sessionId"
            )
            if normalized_context is None:
                normalized_context = self._get_first_value(inputs, "context")
            for key, value in inputs.items():
                if key not in {
                    "inputs",
                    "tool_id",
                    "toolId",
                    "agent_id",
                    "agentId",
                    "session_id",
                    "sessionId",
                    "context",
                }:
                    normalized_extra.setdefault(key, value)

        return McpCallContext(
            inputs=normalized_inputs or {},
            tool_id=normalized_tool_id or self._tool_id,
            agent_id=normalized_agent_id or self._agent_id,
            session_id=normalized_session_id or self._session_id,
            context=normalized_context,
            extra=normalized_extra,
        )

    @staticmethod
    def _get_first_value(source: dict[str, Any], *keys: str) -> Any:
        """Return the first truthy value found by key lookup."""
        for key in keys:
            value = source.get(key)
            if value is not None and value != "":
                return value
        return None
