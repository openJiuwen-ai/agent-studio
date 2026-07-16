# 永久性覆盖重写九问agent_builder代码中DSL模型相关内容
# 增加了多个函数参数，将请求体的模型信息传入框架内的modelConfig实现模型配置运行时修改
#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
from agent_builder.nl_to_agent.adapter.output_adapter.transform_json_to_ir import (
    TransformJsonToIr,
)
from agent_builder.nl_to_agent.base import BaseOperator, OperatorInput
from agent_builder.nl_to_agent.workflow_agent.agent_constructor.generate_workflow import (
    GenerateJsonWorkflow,
)
from agent_builder.nl_to_agent.workflow_agent.progress_bar import (
    WORKFLOW_AGENT_DL,
    WORKFLOW_AGENT_IR,
    result_msg,
    HD4_VERIFY_DL,
    HD4_CREATE_DSL,
)

from .generate_workflow.generate_json_workflow.reflector import extract_json

RESPONSE_CONTENT = "workflow is being generated...\n"


class AgentConstructor(BaseOperator):
    def __init__(self, refine_mermaid, model, input_adapter, controller, **kwargs):
        super().__init__()
        self.refine_mermaid = refine_mermaid
        self.model = model
        self.input_adapter = input_adapter
        self.controller = controller
        self.context_manager = controller.context_manager
        self.task_id = controller.task_id
        self.workflow_name = kwargs.get("name", None)
        self.workflow_name_en = kwargs.get("name_en", None)
        self.workflow_description = kwargs.get("description", None)

    def invoke(self, inputs: OperatorInput):
        """agent_constructor invoke"""
        generate_json_workflow = GenerateJsonWorkflow(
            inputs, self.refine_mermaid, self.model, self.input_adapter, self.controller
        )
        transform_json_to_ir = TransformJsonToIr()
        generator, llm_messages = generate_json_workflow.generate()
        content = None
        flag = True
        yield RESPONSE_CONTENT
        for item in generator:
            if item.content:
                content = extract_json(item.content)
                reflect_generator = generate_json_workflow.reflect(
                    item.content, llm_messages
                )
                for reflect_item in reflect_generator:
                    flag = False
                    if reflect_item.content:
                        content = extract_json(reflect_item.content)
                        self.context_manager.add_assistant_message(
                            self.task_id, reflect_item.content, "分类1"
                        )
                if flag:
                    self.context_manager.add_assistant_message(
                        self.task_id, item.content, "分类1"
                    )
        content = generate_json_workflow.post_process(content)
        eicloud_dsl = transform_json_to_ir.transform_cloud_ir(
            content, self.controller.plugin_dict, self.controller.workflow_dict
        )
        agent_json = transform_json_to_ir.build_agent_json(
            self.workflow_name,
            self.workflow_name_en,
            self.workflow_description,
            eicloud_dsl,
        )
        self.controller.finish_workflow()
        yield content, WORKFLOW_AGENT_DL
        yield agent_json, WORKFLOW_AGENT_IR

    async def ainvoke(self, inputs: OperatorInput):
        """agent_constructor ainvoke"""
        generate_json_workflow = GenerateJsonWorkflow(
            inputs, self.refine_mermaid, self.model, self.input_adapter, self.controller
        )
        transform_json_to_ir = TransformJsonToIr()
        generator, llm_messages = await generate_json_workflow.generate_async()  #
        content = None
        flag = True
        # yield RESPONSE_CONTENT
        async for item in generator:
            if item.raw_content:
                yield item, "dl_flow"  # dl流式输出
            if item.content:
                yield HD4_VERIFY_DL
                content = extract_json(item.content)
                reflect_generator = generate_json_workflow.reflect_async(
                    item.content, llm_messages
                )
                async for reflect_item in reflect_generator:
                    flag = False
                    yield reflect_item  # 输出reflect错误内容
                    if hasattr(reflect_item, "content") and getattr(
                        reflect_item, "content"
                    ):
                        content = extract_json(reflect_item.content)
                        self.context_manager.add_assistant_message(
                            self.task_id, reflect_item.content, "分类1"
                        )
                if flag:
                    self.context_manager.add_assistant_message(
                        self.task_id, item.content, "分类1"
                    )
        content = generate_json_workflow.post_process(content)
        yield HD4_CREATE_DSL
        eicloud_dsl = transform_json_to_ir.transform_cloud_ir(
            content,
            self.controller.plugin_dict,
            self.controller.workflow_dict,
            self.model.model_info.headers,
        )
        agent_json = transform_json_to_ir.build_agent_json(
            self.workflow_name,
            self.workflow_name_en,
            self.workflow_description,
            eicloud_dsl,
        )
        await self.controller.async_finish_workflow()
        yield result_msg(content, WORKFLOW_AGENT_DL)
        yield result_msg(agent_json, WORKFLOW_AGENT_IR)
