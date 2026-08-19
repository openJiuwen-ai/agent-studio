#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Dict, Any, List

import requests
from jiuwen.common.exception import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.orchestration import Invokable
from jiuwen.orchestration.callbacks.span import Span
from jiuwen.orchestration.flow.components.flow_agent.strategies.base import (
    AgentStrategy,
    AgentStrategyContext,
)
from jiuwen.orchestration.flow.components.interactive_base import InteractiveComponent
from jiuwen.orchestration.flow.constant import WORKFLOW_CHAT_HISTORY
from jiuwen.orchestration.flow.enum import ExecutionStatus
from jiuwen.orchestration.flow.model.workflow_data_class import WorkflowMetadata
from jiuwen.orchestration.flow.runtime_context import RuntimeContext
from jiuwen.orchestration.flow.state import State
from jiuwen.plugin import PluginManager
from jiuwen.plugin.common.utils.ir_utils import PluginIRConverter

DEFAULT_ERROR_INFO = {"message": "", "error_code": 0}

USER_FIELDS = "userFields"
USER_INPUTS = "inputs"
LLM_INPUTS = "llm_inputs"
LLM_OUTPUTS = "llm_outputs"

AGENT_STRATEGY = "agent_strategy"
STRATEGY_NAME = "name"
STRATEGY_PROVIDER = "provider"
MAX_ITERATION = "maxIteration"
STREAMING = "streaming"
PLUGINS_CONFIG = "plugins"
WITH_CHAT_HISTORY = "with_chat_history"
CHAT_HISTORY_MAX_TURN = "chatHistoryMaxTurn"
MODEL_CONFIG = "model"
MODEL_NAME = "modelName"
MODEL_TYPE = "modelType"
HYPER_PARA = "hyperParameters"
EXTENSION = "extension"
SYSTEM_PROMPT = "systemPrompt"


@dataclass
class AgentNodeConfig:
    """Agent节点静态配置 - 节点能力定义"""

    # 策略配置
    strategy_name: str = "ReAct"
    strategy_provider: str = "JiuWen"
    supported_strategies: List[str] = field(default_factory=list)

    # 执行配置
    max_iteration: int = 9
    streaming: bool = False
    with_chat_history: bool = True
    chat_history_max_turn: int = 0

    # 系统配置
    system_prompt: str = ""
    model_config: Dict[str, Any] = field(default_factory=dict)
    plugins: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AgentState(State):
    user_response: str = ""
    response_num: int = 0
    status: ExecutionStatus = ExecutionStatus.START
    tool_choose: str = ""
    extracted_key_fields: dict = None
    tool_result: list[dict] = None
    tool_result_summary: list[dict] = None
    cur_tool_name: str = ""


def convert_conf_to_agent_node_config(configs: dict) -> AgentNodeConfig:
    """convert IR config to AgentNodeConfig"""
    agent_strategy = configs.get(AGENT_STRATEGY, {})

    max_iteration = configs.get(MAX_ITERATION)
    if not isinstance(max_iteration, int) or max_iteration <= 0:
        raise JiuWenBaseException(
            message=StatusCode.AGENT_MAX_ITERATION_INVALID.errmsg,
            error_code=StatusCode.AGENT_MAX_ITERATION_INVALID.code,
        )

    return AgentNodeConfig(
        strategy_name=agent_strategy.get(STRATEGY_NAME),
        strategy_provider=agent_strategy.get(STRATEGY_PROVIDER),
        max_iteration=configs.get(MAX_ITERATION),
        streaming=configs.get(STREAMING),
        with_chat_history=configs.get(WITH_CHAT_HISTORY),
        chat_history_max_turn=configs.get(CHAT_HISTORY_MAX_TURN),
        system_prompt=configs.get(SYSTEM_PROMPT),
        model_config=configs.get(MODEL_CONFIG),
        plugins=configs.get(PLUGINS_CONFIG),
    )


class FlowAgent(Invokable, InteractiveComponent):
    """Agent node."""

    def __init__(
        self, runtime_context: RuntimeContext = None, metadata: WorkflowMetadata = None
    ):
        super().__init__()
        self.conf = None
        self.metadata = metadata
        self.runtime_context = runtime_context
        self.agent_node_config = AgentNodeConfig()

        self.node_state = AgentState()
        self.component_config = None
        self.plugins = []
        self.plugins_dict = dict()
        self.language = ""
        self.language_config = dict()

        self.strategy_registry = None
        self.strategy_name = None
        self.strategy_provider = None
        self.strategy = None

    @staticmethod
    def _get_plugin_list_from_config(conf):
        plugin_conf_list = conf.get("plugins") or []
        plugin_instance_list = []
        plugin_ids = []
        for plugin_conf in plugin_conf_list:
            if "url" in plugin_conf:
                url = plugin_conf.get("url")
                r = requests.options(url, timeout=10)
                if r.status_code == 404:
                    raise JiuWenBaseException(
                        message=StatusCode.PLUGIN_RESPONSE_HTTP_CODE_ERROR.errmsg,
                        error_code=StatusCode.PLUGIN_RESPONSE_HTTP_CODE_ERROR.code,
                    )
                # 有url表示此plugin_conf为完整的插件IR信息
                plugin_instance_list.append(PluginIRConverter.ir_to_plugin(plugin_conf))
            else:
                plugin_ids.append(plugin_conf.get("id"))

        try:
            plugin_ids = [int(plugin_id) for plugin_id in plugin_ids]
        except Exception as e:
            raise JiuWenBaseException(
                message=StatusCode.PLUGIN_VALID.errmsg,
                error_code=StatusCode.PLUGIN_VALID.code,
            ) from e
        if plugin_ids:
            try:
                plugin_manager = PluginManager()

                res = plugin_manager.get_plugin_by_id(plugin_ids)
                if "body" in res:
                    plugin_instance_list.extend(res.get("body"))
                else:
                    raise JiuWenBaseException(
                        message=StatusCode.PLUGIN_VALID.errmsg,
                        error_code=StatusCode.PLUGIN_VALID.code,
                    )
            except JiuWenBaseException:
                raise
            except Exception as e:
                raise JiuWenBaseException(
                    message=StatusCode.PLUGIN_VALID.errmsg,
                    error_code=StatusCode.PLUGIN_VALID.code,
                ) from e

        return plugin_instance_list

    def init(self, conf: dict, **kwargs):
        self.conf = conf
        runtime_context = kwargs.get("runtime_context")
        self.runtime_context = runtime_context

        metadata = kwargs.get("metadata")
        self.metadata = metadata

        # 初始化node config
        self.agent_node_config = convert_conf_to_agent_node_config(self.conf)
        # 加载可调用的插件
        self.plugins = self._get_plugin_list_from_config(self.conf)
        self.plugins_dict = {
            item.name: item for item in self.plugins
        }  # 插件名称 -> 实例映射
        self.node_state = AgentState()
        self.strategy_name = self.agent_node_config.strategy_name
        self.strategy_provider = self.agent_node_config.strategy_provider
        self.strategy = self._create_strategy()

    def should_interrupt(self) -> bool:
        """
        check if should be interrupted

        Returns:
            bool: The result of the interruption.
        """
        return self.node_state.status == ExecutionStatus.USER_INTERACT

    def get_state(self):
        """
        get input state
        """
        return self.node_state

    def load_state(self, state):
        """
        load input state from input state
        """
        self.node_state = deepcopy(state)

    def get_node_status(self):
        """
        返回节点状态
        :return:
        """
        return self.node_state.status

    async def ainvoke(self, inputs: Dict[str, Any], **kwargs):
        debug_info = dict(
            component_metadata=kwargs.get("component_metadata", {}),
            runtime_context=kwargs.get("runtime_context", {}),
            span=kwargs.get("span"),
        )
        strategy_context = self._create_strategy_context(
            inputs, span=debug_info.get("span")
        )

        return await self.strategy.ainvoke(strategy_context)

    def invoke(self, inputs: Dict[str, Any], **kwargs):
        """Invoke to assemble final answer."""
        pass

    def stream(self, inputs: Dict[str, Any], **kwargs):
        """Default implementation, subclass should override if they support stream."""
        pass

    async def astream(self, inputs: Dict[str, Any], **kwargs):
        """Default implementation, subclass should override if they support asynchronous stream."""
        pass

    def _create_strategy(self) -> AgentStrategy:
        from jiuwen.orchestration.flow.agent_strategy_registry import (
            AgentStrategyRegistry,
        )

        strategy_class = AgentStrategyRegistry.get_strategy(
            self.strategy_provider, self.strategy_name
        )

        # 实例化类，并调用初始化方法
        strategy_instance = strategy_class()
        strategy_instance.init(
            self.agent_node_config
        )  # 调用 ReActStrategy 的 init 方法初始化

        return strategy_instance  # 返回实例，而非类

    def _create_strategy_context(self, inputs, span: Span):
        return AgentStrategyContext(
            model_config=self.agent_node_config.model_config,
            plugins=self.plugins,
            max_iteration=self.agent_node_config.max_iteration,
            with_chat_history=self.agent_node_config.with_chat_history,
            chat_history_max_turn=self.agent_node_config.chat_history_max_turn,
            user_inputs=inputs,
            chat_history=self.runtime_context.get(WORKFLOW_CHAT_HISTORY),
            execution_id=span.trace_id,
            system_prompt=self.agent_node_config.system_prompt,
        )
