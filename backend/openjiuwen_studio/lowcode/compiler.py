#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Agent编译器 - Runtime SDK的主要入口
"""

from typing import Any, Dict, Optional, Union
from pathlib import Path
import logging

from openjiuwen_studio.lowcode.loader import LowCodeAgentLoader
from openjiuwen_studio.lowcode.schemas import ModelOverride
from openjiuwen_studio.lowcode.config_adapter import ConfigAdapter

logger = logging.getLogger(__name__)

try:
    from openjiuwen.core.single_agent.base import BaseAgent as InvokableAgent
    HAS_INVOKABLE_AGENT = True
except ImportError:
    InvokableAgent = None
    HAS_INVOKABLE_AGENT = False


class AgentCompiler:
    """
    Agent编译器 - Runtime SDK的主要入口

    使用示例:
        # 方式一：直接编译为可执行的Agent实例
        from openjiuwen_studio.lowcode import AgentCompiler

        compiler = AgentCompiler()
        agent = await compiler.compile(
            config=agent_config,
            current_user={"user_id": "system"}
        )
        # agent 是可执行的 InvokableAgent 实例

        # 方式二：仅编译配置（不创建实例）
        result = await compiler.compile_config(
            config=agent_config,
            current_user={"user_id": "system"}
        )
        # result 包含 config, workflows, plugins, knowledge_bases, agent_config
    """

    def __init__(
        self,
        workflow_runner: Optional[Any] = None,
        plugin_manager: Optional[Any] = None
    ):
        """
        初始化Agent编译器

        Args:
            workflow_runner: 工作流运行器
            plugin_manager: 插件管理器
        """
        self.loader = LowCodeAgentLoader(
            workflow_runner=workflow_runner,
            plugin_manager=plugin_manager
        )
        logger.info("AgentCompiler initialized")

    async def compile(
        self,
        config: Dict[str, Any],
        current_user: Optional[Dict] = None,
        space_id: Optional[str] = None
    ) -> "InvokableAgent":
        """
        将Agent配置编译为可执行的Agent实例

        Args:
            config: Agent配置（AgentExportData格式）
            current_user: 当前用户信息
            space_id: 工作空间ID，默认为 "default"

        Returns:
            InvokableAgent: 可执行的Agent实例

        Raises:
            ValueError: 如果配置无效
            RuntimeError: 如果编译失败
            ImportError: 如果无法导入必要的Agent运行时组件
        """
        if not HAS_INVOKABLE_AGENT:
            raise ImportError(
                "Cannot import InvokableAgent from openjiuwen.core.single_agent.base. "
                "Please ensure openjiuwen is installed correctly."
            )

        try:
            logger.info("Starting agent compilation to InvokableAgent")

            compiled_result = await self.compile_config(
                config=config,
                current_user=current_user
            )

            from openjiuwen_studio.core.executor.agent.agent_runner import AgentRunner

            agent_runner = AgentRunner(
                flow_mgr=self.loader.dep_processor.workflow_runner,
                plugin_mgr=self.loader.dep_processor.plugin_manager
            )

            agent_config = compiled_result['agent_config']
            adapted_config = ConfigAdapter.adapt(agent_config)

            actual_space_id = space_id or (current_user.get("space_id") if current_user else "default")
            actual_user = current_user or {"user_id": "system"}

            invokable_agent = await agent_runner.create_new_agent(
                agent_config=adapted_config,
                space_id=actual_space_id,
                current_user=actual_user
            )

            logger.info("Agent compilation to InvokableAgent completed successfully")
            return invokable_agent

        except ValueError as e:
            logger.error(f"Invalid configuration: {e}")
            raise
        except Exception as e:
            logger.error(f"Compilation failed: {e}")
            raise RuntimeError(f"Failed to compile agent: {e}") from e

    async def compile_config(
        self,
        config: Dict[str, Any],
        current_user: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        将Agent配置编译为配置字典（不创建Agent实例）

        Args:
            config: Agent配置（AgentExportData格式）
            current_user: 当前用户信息

        Returns:
            包含配置的字典:
            {
                "config": AgentDLConfig,
                "workflows": List[Workflow],
                "plugins": List[Tool],
                "knowledge_bases": List[Dict],
                "agent_config": Dict
            }

        Raises:
            ValueError: 如果配置无效
            RuntimeError: 如果编译失败
        """
        try:
            logger.info("Starting agent configuration compilation")

            result = await self.loader.load_from_export_data(
                export_data=config,
                current_user=current_user
            )

            logger.info("Agent configuration compilation completed successfully")
            return result

        except ValueError as e:
            logger.error(f"Invalid configuration: {e}")
            raise
        except Exception as e:
            logger.error(f"Compilation failed: {e}")
            raise RuntimeError(f"Failed to compile agent configuration: {e}") from e

    async def compile_from_file(
        self,
        config_path: Union[str, Path],
        current_user: Optional[Dict] = None,
        space_id: Optional[str] = None
    ) -> "InvokableAgent":
        """
        从配置文件编译Agent实例

        Args:
            config_path: 配置文件路径（JSON或ZIP）
            current_user: 当前用户信息
            space_id: 工作空间ID，默认为 "default"

        Returns:
            InvokableAgent: 可执行的Agent实例

        Raises:
            FileNotFoundError: 如果文件不存在
            ValueError: 如果配置无效
            RuntimeError: 如果编译失败
        """
        if not HAS_INVOKABLE_AGENT:
            raise ImportError(
                "Cannot import InvokableAgent from openjiuwen.core.single_agent.base. "
                "Please ensure openjiuwen is installed correctly."
            )

        try:
            logger.info(f"Compiling agent from file to InvokableAgent: {config_path}")

            compiled_result = await self.compile_from_file_config(
                config_path=config_path,
                current_user=current_user
            )

            from openjiuwen_studio.core.executor.agent.agent_runner import AgentRunner

            agent_runner = AgentRunner(
                flow_mgr=self.loader.dep_processor.workflow_runner,
                plugin_mgr=self.loader.dep_processor.plugin_manager
            )

            agent_config = compiled_result['agent_config']
            adapted_config = ConfigAdapter.adapt(agent_config)

            actual_space_id = space_id or (current_user.get("space_id") if current_user else "default")
            actual_user = current_user or {"user_id": "system"}

            invokable_agent = await agent_runner.create_new_agent(
                agent_config=adapted_config,
                space_id=actual_space_id,
                current_user=actual_user
            )

            logger.info("Agent compilation from file to InvokableAgent completed successfully")
            return invokable_agent

        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to compile from file: {e}")
            raise RuntimeError(f"Failed to compile agent from file: {e}") from e

    async def compile_from_file_config(
        self,
        config_path: Union[str, Path],
        current_user: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        从配置文件编译Agent配置（不创建实例）

        Args:
            config_path: 配置文件路径（JSON或ZIP）
            current_user: 当前用户信息

        Returns:
            包含配置的字典

        Raises:
            FileNotFoundError: 如果文件不存在
            ValueError: 如果配置无效
            RuntimeError: 如果编译失败
        """
        try:
            logger.info(f"Compiling agent configuration from file: {config_path}")

            result = await self.loader.load_from_config_file(
                config_path=config_path,
                current_user=current_user
            )

            logger.info("Agent configuration compilation from file completed successfully")
            return result

        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to compile configuration from file: {e}")
            raise RuntimeError(f"Failed to compile agent configuration from file: {e}") from e

    async def compile_with_overrides(
        self,
        config: Dict[str, Any],
        model_overrides: Dict[str, ModelOverride],
        current_user: Optional[Dict] = None,
        space_id: Optional[str] = None
    ) -> "InvokableAgent":
        """
        使用模型覆盖配置编译Agent实例

        Args:
            config: Agent配置
            model_overrides: 模型覆盖配置（如API Key）
            current_user: 当前用户信息
            space_id: 工作空间ID，默认为 "default"

        Returns:
            InvokableAgent: 可执行的Agent实例
        """
        if not HAS_INVOKABLE_AGENT:
            raise ImportError(
                "Cannot import InvokableAgent from openjiuwen.core.single_agent.base. "
                "Please ensure openjiuwen is installed correctly."
            )

        try:
            logger.info("Starting agent compilation with model overrides to InvokableAgent")

            compiled_result = await self.compile_with_overrides_config(
                config=config,
                model_overrides=model_overrides,
                current_user=current_user
            )

            from openjiuwen_studio.core.executor.agent.agent_runner import AgentRunner

            agent_runner = AgentRunner(
                flow_mgr=self.loader.dep_processor.workflow_runner,
                plugin_mgr=self.loader.dep_processor.plugin_manager
            )

            agent_config = compiled_result['agent_config']
            adapted_config = ConfigAdapter.adapt(agent_config)

            actual_space_id = space_id or (current_user.get("space_id") if current_user else "default")
            actual_user = current_user or {"user_id": "system"}

            invokable_agent = await agent_runner.create_new_agent(
                agent_config=adapted_config,
                space_id=actual_space_id,
                current_user=actual_user
            )

            logger.info("Agent compilation with overrides to InvokableAgent completed successfully")
            return invokable_agent

        except Exception as e:
            logger.error(f"Compilation with overrides failed: {e}")
            raise RuntimeError(f"Failed to compile agent with overrides: {e}") from e

    async def compile_with_overrides_config(
        self,
        config: Dict[str, Any],
        model_overrides: Dict[str, ModelOverride],
        current_user: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        使用模型覆盖配置编译Agent配置（不创建实例）

        Args:
            config: Agent配置
            model_overrides: 模型覆盖配置（如API Key）
            current_user: 当前用户信息

        Returns:
            包含配置的字典
        """
        try:
            logger.info("Starting agent configuration compilation with model overrides")

            result = await self.loader.load_from_export_data(
                export_data=config,
                model_overrides=model_overrides,
                current_user=current_user
            )

            logger.info("Agent configuration compilation with overrides completed successfully")
            return result

        except Exception as e:
            logger.error(f"Configuration compilation with overrides failed: {e}")
            raise RuntimeError(f"Failed to compile agent configuration with overrides: {e}") from e

    async def validate(
        self,
        config: Dict[str, Any],
        model_overrides: Optional[Dict[str, ModelOverride]] = None
    ) -> Dict[str, Any]:
        """
        验证Agent配置

        Args:
            config: Agent配置
            model_overrides: 模型覆盖配置

        Returns:
            验证结果
        """
        try:
            logger.info("Validating agent configuration")

            result = await self.loader.validate_export_data(
                export_data=config,
                model_overrides=model_overrides
            )

            return {
                "valid": result.valid,
                "checks": result.checks,
                "errors": [
                    {
                        "field": e.field,
                        "message": e.message,
                        "severity": e.severity
                    }
                    for e in result.errors
                ]
            }

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {
                "valid": False,
                "checks": {},
                "errors": [
                    {
                        "field": "general",
                        "message": str(e),
                        "severity": "error"
                    }
                ]
            }

    async def compile_for_runtime(
        self,
        config: Dict[str, Any],
        model_overrides: Optional[Dict[str, ModelOverride]] = None,
        current_user: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        编译配置用于 Runtime 环境（不依赖数据库）

        此方法专为 Runtime 环境设计，返回可直接用于创建 Agent 实例的配置。
        不依赖 AgentRunner，因此不需要数据库配置。

        Args:
            config: Agent配置（AgentExportData格式）
            model_overrides: 模型覆盖配置（如API Key）
            current_user: 当前用户信息

        Returns:
            Dict 包含:
            {
                "agent_card": AgentCard,
                "runtime_config": ReActAgentConfig,
                "agent_config": Dict
            }

        使用示例:
            from openjiuwen.core.single_agent.agents.react_agent import ReActAgent
            from openjiuwen_studio.lowcode import AgentCompiler

            compiler = AgentCompiler()
            result = await compiler.compile_for_runtime(
                config=export_data,
                model_overrides={"147": ModelOverride(...)}
            )

            agent = ReActAgent(card=result["agent_card"])
            agent.configure(result["runtime_config"])
        """
        try:
            from openjiuwen.core.single_agent.schema.agent_card import AgentCard
            logger.info("Starting agent compilation for runtime environment")

            compiled_result = await self.compile_with_overrides_config(
                config=config,
                model_overrides=model_overrides or {},
                current_user=current_user
            )

            agent_config = compiled_result['agent_config']

            agent_card = AgentCard(
                id=agent_config.get("agent_id", ""),
                name=agent_config.get("agent_name", "Agent"),
                description=agent_config.get("description", ""),
                version=agent_config.get("agent_version", "draft"),
            )

            runtime_config = ConfigAdapter.adapt_to_runtime_config(agent_config)

            logger.info("Agent compilation for runtime completed successfully")

            return {
                "agent_card": agent_card,
                "runtime_config": runtime_config,
                "agent_config": agent_config,
            }

        except Exception as e:
            logger.error(f"Runtime compilation failed: {e}")
            raise RuntimeError(f"Failed to compile agent for runtime: {e}") from e
