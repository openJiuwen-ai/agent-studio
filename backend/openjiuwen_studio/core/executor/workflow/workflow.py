#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Union

from openjiuwen.core.common.logging import logger
from openjiuwen.core.component.base import WorkflowComponent
from openjiuwen.core.component.branch_comp import BranchComponent
from openjiuwen.core.component.break_comp import BreakComponent
from openjiuwen.core.component.condition.condition import AlwaysTrue
from openjiuwen.core.component.end_comp import End
from openjiuwen.core.component.loop_comp import LoopComponent, LoopGroup
from openjiuwen.core.component.set_variable_comp import SetVariableComponent
from openjiuwen.core.component.start_comp import Start
from openjiuwen.core.component.tool_comp import ToolComponentConfig, ToolComponent
from openjiuwen.core.component.workflow_comp import SubWorkflowComponent
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.runtime.base import ComponentExecutable
from openjiuwen.core.runtime.runtime import BaseRuntime
from openjiuwen.core.workflow.base import Workflow as InvokableWorkflow
from openjiuwen.core.workflow.base import WorkflowConfig
from openjiuwen.core.workflow.workflow_config import WorkflowMetadata, WorkflowInputsSchema

from openjiuwen_studio.core.common.dsl import PluginCodeConfig as DlPluginCodeConfig
from openjiuwen_studio.core.common.dsl import PluginType
from openjiuwen_studio.core.common.dsl import RestfulApiSchema as DlRestfulApiSchema
from openjiuwen_studio.core.common.dsl import ToolCompConfig, LoopConfig, ExecSubWfConfig, SetVariableConfig, \
    BaseFlow
from openjiuwen_studio.core.common.dsl import Workflow as DlWorkflow, Component, EndConfig, ComponentType
from openjiuwen_studio.core.executor.component.compile.intent_detection_comp_compiler import IntentDetectionCompCompiler
from openjiuwen_studio.core.executor.component.compile.llm_comp_compiler import LLMCompCompiler
from openjiuwen_studio.core.executor.component.compile.questioner_comp_compiler import QuestionerCompCompiler
from openjiuwen_studio.core.executor.component.compile.branch_comp_compiler import BranchCompCompiler
from openjiuwen_studio.core.executor.component.compile.code_comp_compiler import CodeCompCompiler
from openjiuwen_studio.core.executor.component.component_impl.empty_comp import EmptyComponent
from openjiuwen_studio.core.executor.component.compile.text_editor_comp_compiler import TextEditorCompCompiler
from openjiuwen_studio.core.executor.component.compile.user_input_comp_compiler import UserInputCompCompiler
from openjiuwen_studio.core.executor.component.compile.user_output_comp_compiler import UserOutputCompCompiler, \
    find_llm_to_stream_out, change_stream_input
from openjiuwen_studio.core.executor.component.compile.variable_merge_comp_compiler import VariableMergeCompCompiler
from openjiuwen_studio.core.executor.plugin.plugin_tools import ServiceTool, CodeTool
from openjiuwen_studio.core.executor.workflow.context import Context
from openjiuwen_studio.core.executor.workflow.pregel_graph_adapter import PregelGraphAdapter
from openjiuwen.core.workflow.workflow_config import ComponentAbility
from openjiuwen.core.graph.executable import Executable
from openjiuwen_studio.core.executor.component.component_impl.user_output_comp import UserOutputComponent


class IWorkflowLoader(ABC):
    @abstractmethod
    async def get_compiled_workflow(self, context: Context, id: str, version: str, space_id,
                                    current_user) -> InvokableWorkflow:
        pass


def set_comp_with_stream(
        self: InvokableWorkflow,
        comp_id: str,
        component: Union[Executable, WorkflowComponent],
        inputs_schema: dict = None,
        outputs_schema: dict = None,
        stream_inputs_schema: dict = None,
        stream_outputs_schema: dict = None,
        response_mode: str = None,
        wait_for_all: bool = None
) -> InvokableWorkflow:
    """Workflow添加支持流式处理的组件添加方法"""

    # 实现逻辑与方式1相同
    if wait_for_all is None:
        wait_for_all = False
    comp_ability = []
    if response_mode is not None and "streaming" == response_mode:
        if inputs_schema:
            comp_ability = [ComponentAbility.STREAM]
        self._is_streaming = True
        if stream_inputs_schema:
            comp_ability.append(ComponentAbility.TRANSFORM)
            if isinstance(component, End):
                component.set_mix()
            wait_for_all = True
    else:
        if inputs_schema:
            comp_ability = [ComponentAbility.INVOKE]
        if stream_inputs_schema:
            comp_ability.append(ComponentAbility.COLLECT)
            if isinstance(component, UserOutputComponent):
                component.set_mix()
            wait_for_all = True

    self.add_workflow_comp(
        comp_id,
        component,
        wait_for_all=wait_for_all,
        inputs_schema=inputs_schema,
        comp_ability=comp_ability,
        outputs_schema=outputs_schema,
        stream_inputs_schema=stream_inputs_schema,
        stream_outputs_schema=stream_outputs_schema,
    )
    logger.debug(f"comp set comp_ability: {comp_ability}")
    return self


InvokableWorkflow.set_comp_with_stream = set_comp_with_stream


class Workflow:
    # 组件编译器映射表
    COMPILER_HANDLERS = {
        ComponentType.COMPONENT_TYPE_LLM: '_compile_llm_component',
        ComponentType.COMPONENT_TYPE_QUESTION: '_compile_question_component',
        ComponentType.COMPONENT_TYPE_INTENT: '_compile_intent_component',
        ComponentType.COMPONENT_TYPE_INPUT: '_compile_input_component',
        ComponentType.COMPONENT_TYPE_OUTPUT: '_compile_output_component',
        ComponentType.COMPONENT_TYPE_TEXT_EDITOR: '_compile_text_editor_component',
        ComponentType.COMPONENT_TYPE_VARIABLE_MERGE: '_compile_variable_merge_component',
        ComponentType.COMPONENT_TYPE_CODE: '_compile_code_component',
    }

    # 特殊组件类型（需要异步处理或特殊参数）
    SPECIAL_COMPONENT_TYPES = {
        ComponentType.COMPONENT_TYPE_IF,
        ComponentType.COMPONENT_TYPE_SUB_WORKFLOW,
        ComponentType.COMPONENT_TYPE_LOOP,
        ComponentType.COMPONENT_TYPE_PLUGIN,
    }

    # 空组件类型
    EMPTY_COMPONENT_TYPES = {
        ComponentType.COMPONENT_TYPE_EMPTY,
        ComponentType.COMPONENT_TYPE_CONTINUE,
        ComponentType.COMPONENT_TYPE_EMPTY_START,
        ComponentType.COMPONENT_TYPE_EMPTY_END,
    }

    def __init__(
            self,
            dl_workflow: DlWorkflow,
            space_id: str,
            current_user: Dict[str, Any]
    ) -> None:
        logger.info(f"first dsl: {dl_workflow.model_dump_json()}")
        for component in dl_workflow.components:
            if component.type == ComponentType.COMPONENT_TYPE_LOOP:
                loop_config = LoopConfig.model_validate(component.configs)
                loop_graph_adapter = PregelGraphAdapter(loop_config.loop_body)
                loop_config.loop_body = loop_graph_adapter.convert()
                component.configs = loop_config.model_dump()
        self.id = dl_workflow.id
        self.version = dl_workflow.version
        self.name = dl_workflow.name
        self.inputs = dl_workflow.inputs
        graph_adapter = PregelGraphAdapter(dl_workflow)
        self.dl_workflow = graph_adapter.convert()
        logger.info(f"second dsl: {self.dl_workflow.model_dump_json()}")
        self.space_id = space_id
        self.current_user = current_user
        self.need_stream_output_comp = {}

    async def process_components(
            self,
            context: Context,
            flow: Any,
            workflow_dl: BaseFlow,
            loader: Optional[IWorkflowLoader] = None
    ) -> None:
        dl_wf_components = workflow_dl.components
        for comp in dl_wf_components:
            if comp.id in self.dl_workflow.start_id:
                compiled_comp = Start({})
                flow.set_start_comp(comp.id, compiled_comp, comp.inputs)
            elif comp.id in self.dl_workflow.end_id:
                stream_inputs_schema = None
                batch_inputs_schema = None
                response_mode = None
                if comp.configs:
                    end_config = EndConfig.model_validate(comp.configs)
                    template: str = ""
                    if end_config.response_template:
                        template = end_config.response_template
                    compiled_comp = End({"responseTemplate": template})
                    # 打开流式输出开关
                    if end_config.stream_output:
                        find_llm_to_stream_out(comp.id, comp.inputs, self.need_stream_output_comp)
                        stream_inputs_schema, batch_inputs_schema = change_stream_input(comp.inputs)
                        if stream_inputs_schema:
                            response_mode = "streaming"
                    else:
                        # 非流式输出模式下，直接使用原始输入
                        batch_inputs_schema = comp.inputs

                else:
                    compiled_comp = End()
                    # 没有配置时，直接使用原始输入
                    batch_inputs_schema = comp.inputs
                logger.debug(f"set_end_comp inputs_schema: {batch_inputs_schema}, "
                             f"stream_inputs_schema: {stream_inputs_schema}, "
                             f"response_mode: {response_mode}")
                flow.set_end_comp(comp.id, compiled_comp, inputs_schema=batch_inputs_schema,
                                  stream_inputs_schema=stream_inputs_schema, response_mode=response_mode)
            else:
                compiled_comp = await self.compile_component(context, workflow_dl, comp, loader)
                if compiled_comp is None:
                    continue
                if comp.type == ComponentType.COMPONENT_TYPE_OUTPUT:
                    if any(
                            (isinstance(value, str) and comp.id == value) or
                            (isinstance(value, list) and comp.id in value)
                            for value in self.need_stream_output_comp.values()
                    ):
                        stream_inputs, new_inputs = change_stream_input(comp.inputs)
                        if stream_inputs:
                            response_mode = "streaming"
                        else:
                            response_mode = None
                        logger.debug(f"set_comp_with_stream stream_inputs: {stream_inputs}, new_inputs: {new_inputs}")
                        flow.set_comp_with_stream(comp.id, compiled_comp, inputs_schema=new_inputs,
                                                  stream_inputs_schema=stream_inputs, response_mode=response_mode)
                        continue
                flow.add_workflow_comp(comp.id, compiled_comp, inputs_schema=comp.inputs)
        return flow

    async def compile(
            self,
            context: Context,
            loader: Optional[IWorkflowLoader] = None
    ) -> InvokableWorkflow:
        flow = InvokableWorkflow(WorkflowConfig(metadata=WorkflowMetadata(
            id=self.id,
            version=self.version,
            name=self.name,
        ), workflow_inputs_schema=WorkflowInputsSchema.model_validate(self.inputs)))

        flow = await self.process_components(context, flow, self.dl_workflow, loader)
        flow = await self.process_stream_connections(flow)
        flow = await self.process_connections(flow, self.dl_workflow.connections)
        return flow

    async def compile_component(
            self,
            context: Context,
            workflow_dl: BaseFlow,
            comp: Component,
            loader: Optional[IWorkflowLoader] = None
    ) -> Any:
        """使用简单注册机制编译组件"""

        # 1. 处理空组件
        if comp.type in self.EMPTY_COMPONENT_TYPES:
            return EmptyComponent()

        # 2. 处理BREAK组件
        if comp.type == ComponentType.COMPONENT_TYPE_BREAK:
            return BreakComponent()

        # 3. 处理特殊组件（保持原有逻辑）
        if comp.type in self.SPECIAL_COMPONENT_TYPES:
            return await self._compile_special_component(context, workflow_dl, comp, loader)

        # 4. 使用注册表编译标准组件
        handler_name = self.COMPILER_HANDLERS.get(comp.type)
        if handler_name:
            handler = getattr(self, handler_name)
            return await handler(comp, workflow_dl)
        else:
            logger.warning(f"Unsupported component type: {comp.type}")
            return None

    # 各个组件的编译方法
    async def _compile_llm_component(self, comp: Component, workflow_dl: BaseFlow):
        """编译LLM组件"""
        llm_compiler = LLMCompCompiler(comp.configs)
        return llm_compiler.compile()

    async def _compile_question_component(self, comp: Component, workflow_dl: BaseFlow):
        """编译提问者组件"""
        questioner_compiler = QuestionerCompCompiler(comp.configs)
        return questioner_compiler.compile()

    async def _compile_intent_component(self, comp: Component, workflow_dl: BaseFlow):
        """编译意图检测组件"""
        compiler = IntentDetectionCompCompiler(comp, workflow_dl.connections)
        return compiler.compile()

    async def _compile_input_component(self, comp: Component, workflow_dl: BaseFlow):
        """编译用户输入组件"""
        userinput_compiler = UserInputCompCompiler(comp.configs, comp.id)
        return userinput_compiler.compile()

    async def _compile_output_component(self, comp: Component, workflow_dl: BaseFlow):
        """编译用户输出组件"""
        useroutput_compiler = UserOutputCompCompiler(comp.id, comp.configs, comp.inputs, self.need_stream_output_comp)
        output_component, self.need_stream_output_comp = useroutput_compiler.compile()
        return output_component

    async def _compile_text_editor_component(self, comp: Component, workflow_dl: BaseFlow):
        """编译文本编辑器组件"""
        texteditor_compiler = TextEditorCompCompiler(comp.id, comp.configs, comp.outputs)
        return texteditor_compiler.compile()

    async def _compile_variable_merge_component(self, comp: Component, workflow_dl: BaseFlow):
        """编译变量合并组件"""
        varimerge_compiler = VariableMergeCompCompiler(comp.configs, comp.id)
        return varimerge_compiler.compile()

    async def _compile_code_component(self, comp: Component, workflow_dl: BaseFlow):
        """编译代码组件"""
        code_compiler = CodeCompCompiler(comp.id, comp.configs, workflow_dl.connections)
        return code_compiler.compile()

    async def _compile_special_component(self, context: Context, workflow_dl: BaseFlow, comp: Component, loader):
        """处理特殊组件（保持原有逻辑）"""
        if comp.type == ComponentType.COMPONENT_TYPE_IF:
            branch_compiler = BranchCompCompiler(comp.id, comp.branches, workflow_dl.connections)
            return branch_compiler.compile()

        elif comp.type == ComponentType.COMPONENT_TYPE_SUB_WORKFLOW:
            return await self._create_exec_sub_workflow_component(context, comp.configs, loader)

        elif comp.type == ComponentType.COMPONENT_TYPE_LOOP:
            return await self._create_loop_component(context, comp.configs, comp.outputs, loader)

        elif comp.type == ComponentType.COMPONENT_TYPE_PLUGIN:
            return await self._compile_plugin_component(comp)

        return None

    async def _compile_plugin_component(self, comp: Component):
        """编译插件组件"""
        tool_config = ToolCompConfig.model_validate(comp.configs)
        if tool_config.type == PluginType.SERVICE:
            plugin_tool = ServiceTool(DlRestfulApiSchema.model_validate(tool_config.tool)).compile()
        else:
            plugin_tool = CodeTool(DlPluginCodeConfig.model_validate(tool_config.tool)).compile()
        tool_config = ToolComponentConfig()
        return ToolComponent(tool_config).bind_tool(plugin_tool)

    async def process_stream_connections(self,
                                         flow: Any) -> Any:
        if not self.need_stream_output_comp:
            return flow
        for source_id, target_id in self.need_stream_output_comp.items():

            if isinstance(target_id, list):
                for tid in target_id:
                    logger.debug(f"add_stream_connection source_id: {source_id}, target_id: {tid}")
                    flow.add_stream_connection(source_id, tid)
            else:
                logger.debug(f"add_stream_connection source_id: {source_id}, target_id: {target_id}")
                flow.add_stream_connection(source_id, target_id)

        return flow

    async def do_add_connection(self, flow, source, target):
        skip_connection = False
        for source_id, target_id in self.need_stream_output_comp.items():
            if (source == source_id) and (target == target_id or target in target_id):
                skip_connection = True
                break
        if not skip_connection:
            logger.debug(f"add_connection source: {source}, target: {target}")
            flow.add_connection(source, target)
        return flow

    async def process_connections(
            self,
            flow: Any,
            dl_wf_connections: List[Any]
    ) -> Any:
        for conn in dl_wf_connections:
            # 跳过分支连接，因为分支连接由组件内部的add_branch方法处理
            # 只有非分支连接需要被添加到flow中
            if conn.branch_id:
                continue
            # 检查 conn.source 是否包含 self.need_stream_output_comp 中的任何 key
            source_list = conn.source if isinstance(conn.source, list) else [conn.source]
            need_stream_sources = set(self.need_stream_output_comp.keys())
            has_stream_source = bool(set(source_list) & need_stream_sources)

            if has_stream_source:
                # 如果 source 在 need_stream_output_comp 中，需要遍历出没有加过add_stream_connection的连接
                if isinstance(conn.source, list):
                    for sid in conn.source:
                        flow = await self.do_add_connection(flow, sid, conn.target)
                else:
                    flow = await self.do_add_connection(flow, conn.source, conn.target)
            else:
                # 如果 source 不在 need_stream_output_comp 中，直接添加连接
                logger.debug(f"add_connection source: {conn.source}, target: {conn.target}")
                flow.add_connection(conn.source, conn.target)
        return flow

    async def _create_exec_sub_workflow_component(
            self,
            context: Context,
            configs: Any,
            loader: Optional[IWorkflowLoader]
    ) -> Any:
        ref_ir = ExecSubWfConfig.model_validate(configs).reference_ir
        sub_id = ref_ir.id
        sub_version = ref_ir.version
        sub_workflow = await loader.get_compiled_workflow(Context(context),
                                                          sub_id, sub_version, self.space_id, self.current_user)
        return SubWorkflowComponent(sub_workflow)

    async def _create_loop_component(
            self,
            context: Context,
            comp_configs: Any,
            comp_outputs: Any,
            loader: Optional[IWorkflowLoader] = None

    ) -> Any:
        # create loop component
        loop_group = LoopGroup()
        loop_config = LoopConfig.model_validate(comp_configs)
        loop_body = loop_config.loop_body
        loop_group.start_nodes(loop_body.start_id)
        loop_group.end_nodes(loop_body.end_id)
        loop_group = await self.process_components(context, loop_group, loop_body, loader)
        loop_group = await self.process_connections(loop_group, loop_body.connections)

        # 添加SetVariable组件
        for comp in loop_body.components:
            if comp.type == ComponentType.COMPONENT_TYPE_SET_VARIABLE:
                set_variable_config = SetVariableConfig.model_validate(comp.configs)
                set_variable_comp = SetVariableComponent(set_variable_config.inter_variable)
                loop_group.add_workflow_comp(comp.id, set_variable_comp)

        return LoopComponent(loop_group, comp_outputs)
