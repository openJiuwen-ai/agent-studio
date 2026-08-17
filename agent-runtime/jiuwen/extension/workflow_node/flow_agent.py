# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.

"""
FlowAgent - Agent节点组件

迁移自商用版本 FlowAgent，适配开源版本框架。

功能特性:
- 多策略执行（当前支持 ReAct）
- 插件工具调用
- 多轮对话历史管理
- 流式/非流式输出
- 状态管理与中断恢复

设计说明:
- 直接继承 WorkflowComponen
- 通过组合方式持有 ReActAgent 实例
"""

from __future__ import annotations

import ast
import traceback
from typing import Any, AsyncIterator, Dict, List, Optional

from agent_runtime.common.config import settings
from openjiuwen.core.common.logging import logger, workflow_logger
from openjiuwen.core.common.logging.events import LogEventType
from openjiuwen.core.context_engine import ContextEngineConfig
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.foundation.llm.schema.config import (
    ModelClientConfig,
    ModelRequestConfig,
)
from openjiuwen.core.foundation.tool import Tool
from openjiuwen.core.graph.base import Graph
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session.node import Session
from openjiuwen.core.single_agent.agents.react_agent import ReActAgent
from openjiuwen.core.single_agent.agents.react_agent import ReActAgentConfig
from openjiuwen.core.single_agent.schema.agent_card import AgentCard
from openjiuwen.core.workflow.components.component import WorkflowComponent
from pydantic import BaseModel, Field


# =============================================================================
# 配置类
# =============================================================================


class FlowAgentConfig(BaseModel):
    """Agent组件配置 - 对应商用版 AgentNodeConfig

    Attributes:
        strategy_name: 策略名称（当前仅支持 ReAct）
        strategy_provider: 策略提供者（当前仅支持 JiuWen）
        max_iteration: 最大工具调用轮次
        streaming: 是否流式输出
        with_chat_history: 是否启用对话历史
        chat_history_max_turn: 对话历史轮次（0表示不限制）
        system_prompt: 系统提示词
        model_config: 模型配置
        plugins: 插件配置列表
    """

    strategy_name: str = Field(default="ReAct", description="策略名称")
    strategy_provider: str = Field(default="JiuWen", description="策略提供者")
    max_iteration: int = Field(default=9, ge=1, le=100, description="最大工具调用轮次")
    streaming: bool = Field(default=False, description="是否流式输出")
    with_chat_history: bool = Field(default=True, description="是否启用对话历史")
    chat_history_max_turn: int = Field(default=0, ge=0, description="对话历史轮次")
    system_prompt: str = Field(default="", description="系统提示词")
    llm_config: Dict[str, Any] = Field(default_factory=dict, description="模型配置")
    plugins: List[Dict[str, Any]] = Field(
        default_factory=list, description="插件配置列表"
    )

    def validate_config(self) -> None:
        """验证配置有效性"""
        # 验证策略名称
        if self.strategy_name not in ("ReAct",):
            workflow_logger.error(
                "End component stream failed",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                exception=f"unsupported strategy: {self.strategy_name}，only ReAct is supported",
            )
            raise ValueError(
                f"Unsupported strategy: {self.strategy_name}, only ReAct is supported"
            )

        # 验证策略提供者
        if self.strategy_provider not in ("JiuWen",):
            workflow_logger.error(
                "End component stream failed",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                exception=f"unsupported strategy provider: {self.strategy_provider}，only JiuWen is supported",
            )
            raise ValueError(
                f"Unsupported strategy provider: {self.strategy_provider}, only JiuWen is supported"
            )

        # 验证最大工具调用轮次
        if self.max_iteration < 1:
            workflow_logger.error(
                "End component stream failed",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                exception=f"invalid max_iteration: {self.max_iteration}，must be >= 1",
            )
            raise ValueError(
                f"Invalid max_iteration: {self.max_iteration}, must be >= 1"
            )


# =============================================================================
# 组件类 - 直接继承 WorkflowComponent
# =============================================================================


class FlowAgent(WorkflowComponent):
    """Agent节点组件 - 迁移自商用版 FlowAgent

    直接继承 WorkflowComponent，不依赖 ComponentComposable 中间层。
    通过组合方式持有 ReActAgent 实例。

    功能:
    - 多策略执行（当前支持 ReAct）
    - 插件工具调用
    - 多轮对话历史管理
    - 流式/非流式输出

    使用示例:
        config = FlowAgentConfig(
            strategy_name="ReAct",
            max_iteration=9,
            streaming=True,
            llm_config={"model_name": "gpt-4", ...}
        )
        agent = FlowAgent(config)
        agent.add_component(graph, "agent_node")
    """

    def __init__(
        self,
        config: FlowAgentConfig,
        tools: Optional[List[Tool]] = None,
        model: Any = None,
    ):
        """初始化 FlowAgent

        Args:
            config: Agent 配置
            tools: 工具列表（可选）
            model: 已构造好的 SDK Model 实例（由 ir_converter 通过 provider 加载后传入）；
                   为 None 时回退到 _build_react_config 自拼逻辑（兼容旧调用方）。
        """
        super().__init__()  # WorkflowComponent 初始化
        self._config = config
        self._tools: List[Tool] = tools or []
        self._model = model
        self._react_agent = None  # 组合持有 ReActAgent，非继承
        self._initialized = False

    # =========================================================================
    # 初始化与 Agent 创建
    # =========================================================================

    async def _ensure_initialized(self) -> None:
        """确保 Agent 已初始化（async：register_rail 需要 await）。"""
        if self._initialized:
            return

        # 验证配置
        self._config.validate_config()

        # 创建 ReAct Agent
        self._create_react_agent()

        # 注入 model（若上游传入，对齐 llm_chain 范式，保留 model_service 延迟解析）
        if self._model is not None:
            self._react_agent.set_llm(self._model)
            logger.info("FlowAgent injected model via set_llm")

        # 注册工具
        self._register_tools()

        # max_iteration 表示工具调用轮次，而不是包含最终回答在内的模型调用次数。
        from agent_runtime.extension.workflow_node.tool_call_limit_rail import ToolCallLimitRail
        await self._react_agent.register_rail(
            ToolCallLimitRail(self._config.max_iteration)
        )

        self._initialized = True
        logger.info(f"FlowAgent initialized with {len(self._tools)} tools")

    def _create_react_agent(self) -> None:
        """创建 ReAct Agent 实例（组合持有）"""

        # 构建 ReActAgentConfig
        react_config = self._build_react_config()

        # 创建 Agent（组合方式持有）
        self._react_agent = ReActAgent(
            card=AgentCard(
                id="flow_agent_workflow",
                name="FlowAgent Workflow Component",
                description="FlowAgent for workflow execution with plugin tools",
            )
        )

        # 配置 Agent
        self._react_agent.configure(react_config)
        logger.info("ReActAgent created and configured")

    def _build_react_config(self):
        """构建 ReActAgent 配置"""

        model_cfg = self._config.llm_config or {}

        # 构建模型客户端配置
        model_client_config = None
        if model_cfg.get("model_client_config"):
            mc = model_cfg["model_client_config"]
            model_client_config = ModelClientConfig(
                client_provider=mc.get("client_provider", "openai"),
                api_key=mc.get("api_key", ""),
                api_base=mc.get("api_base", ""),
                timeout=mc.get("timeout", settings.llm.timeout),
            )

        # 构建模型请求配置
        model_request_config = None
        if model_cfg.get("request_config"):
            rc = model_cfg["request_config"]
            model_request_config = ModelRequestConfig(
                model_name=rc.get("model_name", ""),
                temperature=rc.get("temperature", 0.7),
                top_p=rc.get("top_p", 1.0),
                stream=self._config.streaming,
            )

        # 构建上下文引擎配置
        context_engine_config = ContextEngineConfig(
            max_context_message_num=200,
            default_window_round_num=self._config.chat_history_max_turn
            if self._config.chat_history_max_turn > 0
            else 10,
        )

        return ReActAgentConfig(
            model_name=model_cfg.get("model_name", ""),
            model_provider=model_cfg.get("model_provider", "openai"),
            api_key=model_cfg.get("api_key", ""),
            api_base=model_cfg.get("api_base", ""),
            # 最多 X 轮工具调用后，还需保留一次模型调用来生成最终回答。
            max_iterations=self._config.max_iteration + 1,
            prompt_template=[{"role": "system", "content": self._config.system_prompt}]
            if self._config.system_prompt
            else [],
            model_client_config=model_client_config,
            model_config_obj=model_request_config,
            context_engine_config=context_engine_config,
        )

    def _register_tools(self) -> None:
        """注册工具到 Agent"""
        if not self._tools:
            return

        for tool in self._tools:
            try:
                tool_name = tool.card.name if hasattr(tool, "card") and tool.card else "unknown"

                # 1. 添加工具卡片到 ability_manager（公开 API，带去重）
                if hasattr(tool, "card") and tool.card:
                    result = self._react_agent.ability_manager.add(tool.card)
                    added = getattr(result, "added", True)
                    if added:
                        logger.debug(f"Added tool card to ability_manager: {tool_name}")
                    else:
                        logger.debug(f"Tool already in ability_manager, skipped: {tool_name}")

                # 2. 注册工具实例到 Runner.resource_mgr
                from openjiuwen.core.runner import Runner

                Runner.resource_mgr.add_tool(tool)
                logger.debug(f"Registered tool with Runner.resource_mgr: {tool_name}")

            except Exception as e:
                logger.error(f"Failed to register tool: {e}")

    # =========================================================================
    # 输入映射
    # =========================================================================

    @staticmethod
    def _map_inputs_to_query(inputs: Any) -> Any:
        """映射输入到 query 字段

        ReActAgent 期望输入包含 'query' 键，此方法将第一个输入值映射到 'query'
        """
        if isinstance(inputs, dict) and "query" not in inputs and len(inputs) > 0:
            first_key = next(iter(inputs.keys()))
            return {"query": inputs[first_key]}
        elif isinstance(inputs, dict) and len(inputs) == 0:
            return {"query": ""}
        return inputs

    # =========================================================================
    # WorkflowComponent 执行方法实现
    # =========================================================================

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        """同步执行入口

        Args:
            inputs: 输入数据
            session: 工作流会话
            context: 模型上下文

        Returns:
            执行结果
        """
        await self._ensure_initialized()

        try:
            mapped_inputs = self._map_inputs_to_query(inputs)
            result = await self._react_agent.invoke(mapped_inputs, session)
            output = result.get("output", {})
            if isinstance(output, str):
                try:
                    output = ast.literal_eval(output)
                except (ValueError, SyntaxError) as e:
                    workflow_logger.warning(
                        f"FlowAgent literal_eval failed: {e}",
                        event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                    )
            normalized_output = (
                output
                if isinstance(output, str)
                else output.get("data", {}).get("result", "")
            )
            return {
                "userFields": {
                    "output": normalized_output,
                    "result_type": result.get("result_type", "answer"),
                }
            }
        except Exception as e:
            logger.error(f"FlowAgent invoke error: {e}\n{traceback.format_exc()}")
            return {
                "output": f"Error in FlowAgent execution: {str(e)}",
                "result_type": "error",
            }

    async def stream(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> AsyncIterator[Output]:
        """流式执行入口

        Args:
            inputs: 输入数据
            session: 工作流会话
            context: 模型上下文

        Yields:
            流式输出块
        """
        await self._ensure_initialized()

        try:
            mapped_inputs = self._map_inputs_to_query(inputs)
            async for chunk in self._react_agent.stream(mapped_inputs, session):
                yield chunk
        except Exception as e:
            logger.error(f"FlowAgent stream error: {e}")
            yield {
                "type": "error",
                "payload": {
                    "output": f"Error in FlowAgent streaming: {str(e)}",
                    "result_type": "error",
                },
            }

    async def collect(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        """流式输入聚合为批量输出

        Args:
            inputs: 流式输入数据
            session: 工作流会话
            context: 模型上下文

        Returns:
            聚合后的结果
        """
        await self._ensure_initialized()

        try:
            # 收集流式输入
            if hasattr(inputs, "__aiter__"):
                collected_inputs = []
                async for input_chunk in inputs:
                    collected_inputs.append(input_chunk)

                if len(collected_inputs) == 1:
                    final_inputs = collected_inputs[0]
                else:
                    final_inputs = collected_inputs[-1]
            else:
                final_inputs = inputs

            mapped_inputs = self._map_inputs_to_query(final_inputs)
            result = await self._react_agent.invoke(mapped_inputs, session)
            return result
        except Exception as e:
            logger.error(f"FlowAgent collect error: {e}")
            return {
                "output": f"Error in FlowAgent collect: {str(e)}",
                "result_type": "error",
            }

    async def transform(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> AsyncIterator[Output]:
        """流式输入输出转换

        Args:
            inputs: 流式输入数据
            session: 工作流会话
            context: 模型上下文

        Yields:
            转换后的流式输出
        """
        await self._ensure_initialized()

        try:
            async for input_chunk in inputs:
                mapped_inputs = self._map_inputs_to_query(input_chunk)
                result = await self._react_agent.invoke(mapped_inputs, session)
                yield result
        except Exception as e:
            logger.error(f"FlowAgent transform error: {e}")
            yield {
                "type": "error",
                "payload": {
                    "output": f"Error in FlowAgent transform: {str(e)}",
                    "result_type": "error",
                },
            }

    # =========================================================================
    # 图构建方法（继承自 WorkflowComponent，可覆盖）
    # =========================================================================

    def add_component(
        self, graph: Graph, node_id: str, wait_for_all: bool = False
    ) -> None:
        """添加组件到工作流图

        Args:
            graph: 工作流图
            node_id: 节点ID
            wait_for_all: 是否等待所有前置节点完成
        """
        # WorkflowComponent 本身就是 Executable，直接添加 self
        graph.add_node(node_id, self, wait_for_all=wait_for_all)

    def to_executable(self) -> "FlowAgent":
        """转换为可执行实例

        由于 FlowAgent 直接继承 WorkflowComponent，本身就是可执行的。

        Returns:
            self
        """
        return self

    # =========================================================================
    # 工具管理方法
    # =========================================================================

    def add_tool(self, tool: Tool) -> "FlowAgent":
        """添加工具（支持链式调用）

        Args:
            tool: 工具实例

        Returns:
            self
        """
        self._tools.append(tool)
        return self

    def add_tools(self, tools: List[Tool]) -> "FlowAgent":
        """添加多个工具（支持链式调用）

        Args:
            tools: 工具列表

        Returns:
            self
        """
        self._tools.extend(tools)
        return self

    @property
    def tools(self) -> List[Tool]:
        """获取工具列表"""
        return self._tools

    @property
    def config(self) -> FlowAgentConfig:
        """获取配置"""
        return self._config


# =============================================================================
# 工具加载器
# =============================================================================


class FlowAgentToolLoader:
    """FlowAgent 工具加载器

    负责从插件配置加载工具实例
    """

    @staticmethod
    async def load_tools_from_plugins(
        plugin_configs: List[Dict[str, Any]],
    ) -> List[Tool]:
        """从插件配置加载工具

        Args:
            plugin_configs: 插件配置列表
        Returns:
            工具实例列表
        """
        tools = []

        for plugin_cfg in plugin_configs:
            try:
                tool = await FlowAgentToolLoader._load_single_plugin(plugin_cfg)
                if tool:
                    tools.append(tool)
            except Exception as e:
                logger.error(
                    f"Failed to load plugin {plugin_cfg.get('plugin_id', 'unknown')}: {e}"
                )

        return tools

    @staticmethod
    async def _load_single_plugin(plugin_cfg: Dict[str, Any]) -> Optional[Tool]:
        """加载单个插件

        Args:
            plugin_cfg: 插件配置

        Returns:
            工具实例或 None
        """
        from openjiuwen.core.runner import Runner

        plugin_id = plugin_cfg.get("plugin_id", "")
        if not plugin_id:
            logger.warning("Plugin config missing plugin_id")
            return None

        # 尝试从 Runner.resource_mgr 获取工具
        tool = Runner.resource_mgr.get_tool(plugin_id)
        if tool:
            return tool

        # 从插件管理器加载工具的逻辑待实现
        logger.warning(f"Tool not found for plugin_id: {plugin_id}")
        return None
