# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
"""LLMAgent Component for Workflow Integration"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, AsyncIterator, List

from openjiuwen.core.common.exception.errors import build_error
from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.workflow.components.base import ComponentConfig
from openjiuwen.core.workflow.components.component import WorkflowComponent
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session.node import Session
from openjiuwen.core.foundation.llm import ModelConfig
from openjiuwen.core.foundation.prompt import PromptTemplate
from openjiuwen.core.foundation.tool import Tool
from openjiuwen.core.application.llm_agent.llm_agent import LLMAgent, create_llm_agent, create_llm_agent_config
from openjiuwen.core.single_agent.legacy import LegacyReActAgentConfig as ReActAgentConfig, WorkflowSchema, PluginSchema
from openjiuwen.core.common.constants.enums import ControllerType


@dataclass
class LLMAgentConfig(ComponentConfig):
    """Configuration for LLMAgent Component"""
    agent_id: str = field(default="llm_agent")
    agent_version: str = field(default="1.0.0")
    description: str = field(default="LLM Agent Component")
    model_config: Optional[ModelConfig] = field(default=None)
    prompt_template: List[Dict] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    workflows: List[WorkflowSchema] = field(default_factory=list)
    plugins: List[PluginSchema] = field(default_factory=list)
    memory_scope_id: Optional[str] = field(default=None)
    enable_memory: bool = field(default=False)


class LLMAgentExecutable(WorkflowComponent):
    """LLMAgent Component Executable Implementation"""
    
    def __init__(self, config: LLMAgentConfig):
        super().__init__()
        self._config = config
        self._agent: Optional[LLMAgent] = None
        self._initialized: bool = False
    
    @property
    def config(self) -> LLMAgentConfig:
        return self._config
    
    async def _initialize_if_needed(self):
        """Initialize the LLMAgent if not already initialized."""
        if not self._initialized:
            try:
                # Create agent configuration
                agent_config = create_llm_agent_config(
                    agent_id=self._config.agent_id,
                    agent_version=self._config.agent_version,
                    description=self._config.description,
                    workflows=self._config.workflows,
                    plugins=self._config.plugins,
                    model=self._config.model_config,
                    prompt_template=self._config.prompt_template,
                    tools=self._config.tools
                )
                
                # Create the agent
                self._agent = create_llm_agent(agent_config)
                
                # Configure memory if enabled
                if self._config.memory_scope_id:
                    # This would need to be handled differently depending on the actual implementation
                    # For now, we'll just note that memory is enabled
                    pass
                
                self._initialized = True
            except Exception as e:
                raise build_error(
                    StatusCode.WORKFLOW_COMPONENT_INIT_ERROR,
                    error_msg=f"Failed to initialize LLMAgent component: {str(e)}",
                    cause=e
                ) from e
    
    async def invoke(self, inputs: Input, session: Session, context: ModelContext) -> Output:
        """Execute the LLMAgent component synchronously."""
        await self._initialize_if_needed()
        
        if not self._agent:
            raise build_error(
                StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
                error_msg="LLMAgent component not properly initialized"
            )
        
        # Prepare inputs for the agent
        # Extract query from inputs, defaulting to empty string if not present
        query = inputs.get("query", "")
        conversation_id = inputs.get("conversation_id", session.get_executable_id())
        user_id = inputs.get("user_id", "default_user")
        
        # Prepare agent inputs
        agent_inputs = {
            "query": query,
            "conversation_id": conversation_id,
            "user_id": user_id
        }
        
        # Add any additional context from the workflow
        if context:
            # Add any context-specific data if needed
            pass
        
        try:
            # Execute the agent
            result = await self._agent.invoke(agent_inputs, session)
            return result
        except Exception as e:
            raise build_error(
                StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
                error_msg=f"Failed to execute LLMAgent component: {str(e)}",
                cause=e
            ) from e
    
    async def stream(self, inputs: Input, session: Session, context: ModelContext) -> AsyncIterator[Output]:
        """Execute the LLMAgent component with streaming output."""
        await self._initialize_if_needed()
        
        if not self._agent:
            raise build_error(
                StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
                error_msg="LLMAgent component not properly initialized"
            )
        
        # Prepare inputs for the agent
        query = inputs.get("query", "")
        conversation_id = inputs.get("conversation_id", session.get_executable_id())
        user_id = inputs.get("user_id", "default_user")
        
        # Prepare agent inputs
        agent_inputs = {
            "query": query,
            "conversation_id": conversation_id,
            "user_id": user_id
        }
        
        try:
            # Stream the agent execution
            async for chunk in self._agent.stream(agent_inputs, session):
                yield chunk
        except Exception as e:
            raise build_error(
                StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
                error_msg=f"Failed to stream LLMAgent component: {str(e)}",
                cause=e
            ) from e
    
    async def collect(self, inputs: Input, session: Session, context: ModelContext) -> Output:
        """Collect streaming input and return batch output."""
        # For LLMAgent, collect would aggregate the streaming results
        result_parts = []
        async for chunk in self.stream(inputs, session, context):
            result_parts.append(chunk)
        
        # Return aggregated result - this depends on the specific output format
        # For now, returning the list of chunks
        return result_parts
    
    async def transform(self, inputs: Input, session: Session, context: ModelContext) -> AsyncIterator[Output]:
        """Transform streaming input to streaming output."""
        # For LLMAgent, transform would process streaming input data
        # Since LLMAgent typically takes a single query, we'll just stream the result
        async for chunk in self.stream(inputs, session, context):
            yield chunk
    
    def add_component(self, graph, node_id: str, wait_for_all: bool = False):
        """Add this component to a workflow graph."""
        graph.add_node(node_id, self, wait_for_all=wait_for_all)


class LLMAgentComponent:
    """LLMAgent Component Factory"""
    
    def __init__(self, config: LLMAgentConfig):
        self._config = config
        self._executable = None
    
    @property
    def executable(self) -> LLMAgentExecutable:
        if self._executable is None:
            self._executable = self.to_executable()
        return self._executable
    
    def to_executable(self) -> LLMAgentExecutable:
        return LLMAgentExecutable(self._config)
    
    def add_component(self, graph, node_id: str, wait_for_all: bool = False):
        """Add this component to a workflow graph."""
        executable = self.to_executable()
        executable.add_component(graph, node_id, wait_for_all)