# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

import ast
import asyncio
import random

from agent_builder.common.logging.base import logger
from agent_builder.nl_to_agent.adapter.input_adapter import InputAdapter
from agent_builder.nl_to_agent.adapter.output_adapter.transform_llm_agent import (
    transform_to_cloud,
)
from agent_builder.nl_to_agent.base import OperatorInput
from agent_builder.nl_to_agent.llm_agent.utils import AGENT_MSG
from agent_builder.nl_to_agent.workflow_agent.progress_bar import (
    LLM_AGENT_IR,
    QUESTION,
    result_msg,
    LLM_AGENT_IR_CHUNK,
    content_msg,
    status_msg,
    AGENT_HD4,
)

from .clarifier.base import AgentClarifier
from .constructor.base import AgentConstructor
from .designer.base import AgentDesigner


class LlmAgentBuilder:
    """LLM Agent 构建器。

    该类负责管理基于大语言模型（LLM）的 Agent 构建流程，
    包含用户意图澄清、Agent 设计、Agent 构造等步骤。
    在执行过程中，它会维护全局对话历史和可用资源列表，
    并根据用户输入动态更新和生成最终的 Agent 定义。

    Attributes:
        controller (Controller): 对应任务的对话控制器。
        model: 底层大语言模型实例。
        agent_clarifier (AgentClarifier): 用于意图澄清的子模块。
        agent_designer (AgentDesigner): 用于生成 Agent 初始提示词的子模块。
        agent_constructor (AgentConstructor): 用于构建最终 Agent 提示词的子模块。
        agent_constructor_output (str): 上一次 Agent 构造输出的缓存，用于后续迭代。
        use_designer (bool): 是否启用 AgentDesigner 阶段。
        input_adapter (InputAdapter): 输入适配器，用于外部资源检索与输入预处理。
        dialogue_history (list): 全局对话历史，存储用户与模型的交互信息。
        plugin_list (list): 当前适合 Agent 使用的插件信息列表。
        knowledge_list (list): 当前适合 Agent 使用的知识信息列表。
        sub_workflow_list (list): 当前适合 Agent 使用的子工作流信息列表。
    """

    def __init__(self, model, input_adapter: InputAdapter, controller):
        """初始化 LLM Agent 构建器。

        Args:
            model: 底层大语言模型实例。
            input_adapter (InputAdapter): 输入适配器实例。
            controller (Controller): 对话控制器。
        """
        self.model = model
        self.controller = controller
        self.agent_clarifier = AgentClarifier(self.model, controller)
        self.agent_designer = AgentDesigner(self.model, controller)
        self.agent_constructor = AgentConstructor(self.model, controller)
        self.use_designer = False
        self.input_adapter = input_adapter
        self.plugin_list = []  # 维护适合Agent的插件信息
        self.knowledge_list = []
        self.sub_workflow_list = []

    @staticmethod
    def eval_and_parse_query(query):
        """解析用户输入。

        如果输入是一个列表格式的字符串（包含 question/answer 字段），
        则将其格式化为带序号的问答文本；否则原样返回。

        Args:
            query (str): 用户输入字符串。

        Returns:
            str: 解析后的用户输入文本。
        """
        try:
            qa_list = ast.literal_eval(query)
            return "".join(
                f"{i + 1}.{qa['question']}：{qa['answer']}\n"
                for i, qa in enumerate(qa_list)
                if qa["answer"]
            )
        except (ValueError, SyntaxError):
            return query

    @staticmethod
    def add_batch_unique(existing_list, new_dicts_list, unique_key="resource_id"):
        """批量添加外部资源时基于唯一键去重。

        Args:
            existing_list (list): 已有的资源列表。
            new_dicts_list (list): 新增的资源字典列表。
            unique_key (str, optional): 用于去重的唯一键，默认为 'resource_id'。

        Returns:
            list: 去重后的资源列表。
        """
        if not new_dicts_list:
            return existing_list
        existing_keys = {d[unique_key] for d in existing_list if unique_key in d}
        for d in new_dicts_list:
            if d.get(unique_key) not in existing_keys:
                existing_list.append(d)
                existing_keys.add(d[unique_key])
        return existing_list

    def update_resources(self, query: str, inputs: OperatorInput):
        """更新可用的外部资源信息。

        根据用户查询调用输入适配器，检索插件、知识和子工作流资源，
        并将结果与已有资源合并去重，更新到输入对象中。

        Args:
            query (str): 用户输入的查询内容。
            inputs (OperatorInput): 输入数据对象，将被更新为最新资源列表。
        """
        retrieved_resource = self.input_adapter.retriever_adapter(
            query, res_num=500, filtered=True
        )
        self.controller.resource_config["plugin"] = self.add_batch_unique(
            self.controller.resource_config["plugin"], retrieved_resource.plugin_info
        )
        self.controller.resource_config["knowledge"] = self.add_batch_unique(
            self.controller.resource_config["knowledge"],
            retrieved_resource.knowledge_info,
        )
        self.controller.resource_config["workflow"] = self.add_batch_unique(
            self.controller.resource_config["workflow"],
            retrieved_resource.sub_workflow_info,
        )

        inputs.plugin_info = self.controller.resource_config["plugin"]
        inputs.knowledge_info = self.controller.resource_config["knowledge"]
        inputs.sub_workflow_info = self.controller.resource_config["workflow"]

    def invoke(self, inputs: OperatorInput, for_workflow=False):
        """执行 LLM Agent 的构建过程。

        包括以下步骤：
        1. 根据用户输入解析 query，并维护对话历史。
        2. 调用输入适配器检索可用外部资源并更新。
        3. 执行意图澄清阶段（AgentClarifier）。
            - 如果需要澄清，则返回澄清问题。
            - 如果已澄清，则继续后续阶段。
        4. （可选）执行 Agent 设计阶段（AgentDesigner）。
        5. 执行 Agent 构造阶段（AgentConstructor），生成最终的 Agent 定义。

        Args:
            inputs (OperatorInput): 输入数据对象。
            for_workflow (bool, optional): 是否在工作流场景下调用，默认为 False。

        Yields:
            tuple: (输出内容, 输出类型)，可能为澄清问题、消息片段或最终的 Agent 定义。
        """
        query = self.eval_and_parse_query(inputs.query)
        # 1. 根据用户query检索外部资源，更新可用外部资源
        self.update_resources(query, inputs)

        # 2. 意图澄清
        clarifier_output = self.agent_clarifier.run(inputs, for_workflow=for_workflow)
        # 如果是需要进行需求澄清
        if self.agent_clarifier.need_clarification:
            yield clarifier_output, "question"
        # 否则是已经完成了需求澄清，得到了应得信息
        else:
            if for_workflow:
                yield clarifier_output, False
            # 3. Agent designer设计初始提示词
            if self.use_designer:
                response = self.agent_designer.run(inputs)
                _ = "".join(str(item) for item in response)

            # 4. Agent constructor构建最终提示词
            response = self.agent_constructor.invoke(inputs)
            for item in response:
                if AGENT_MSG in item:
                    yield (
                        transform_to_cloud(
                            item[AGENT_MSG], self.controller.resource_config
                        ),
                        LLM_AGENT_IR,
                    )
                else:
                    yield item["cache_token"], "message"
            logger.info("\n LLM Agent Configuration Construction Finished")

    async def ainvoke(self, inputs: OperatorInput, for_workflow=False):
        """执行 LLM Agent 的构建过程。

        包括以下步骤：
        1. 根据用户输入解析 query，并维护对话历史。
        2. 调用输入适配器检索可用外部资源并更新。
        3. 执行意图澄清阶段（AgentClarifier）。
            - 如果需要澄清，则返回澄清问题。
            - 如果已澄清，则继续后续阶段。
        4. （可选）执行 Agent 设计阶段（AgentDesigner）。
        5. 执行 Agent 构造阶段（AgentConstructor），生成最终的 Agent 定义。

        Args:
            inputs (OperatorInput): 输入数据对象。
            for_workflow (bool, optional): 是否在工作流场景下调用，默认为 False。

        Yields:
            tuple: (输出内容, 输出类型)，可能为澄清问题、消息片段或最终的 Agent 定义。
        """
        query = self.eval_and_parse_query(inputs.query)
        # 1. 根据用户query检索外部资源，更新可用外部资源
        self.update_resources(query, inputs)
        # 2. 意图澄清
        clarifier_output = await self.agent_clarifier.arun(
            inputs, for_workflow=for_workflow
        )
        # 如果是需要进行需求澄清
        if self.agent_clarifier.need_clarification:
            yield result_msg(clarifier_output, QUESTION)
        # 否则是已经完成了需求澄清，得到了应得信息
        else:
            if for_workflow:
                yield clarifier_output, False
            # 3. Agent designer设计初始提示词
            status_steps = [
                ("正在规划思考", "PLANNING"),
                ("正在生成提示词", "PROMPT_GENERATING"),
                ("正在查询插件", "TOOL_CALLING"),
                ("正在查询知识库", "KNOWLEDGE_RETRIEVAL"),
            ]
            for status in status_steps:
                yield status_msg(status[0], AGENT_HD4, status[1])
                delay = random.uniform(0.5, 1.2)
                await asyncio.sleep(delay)
            if self.use_designer:
                response = self.agent_designer.arun(inputs)
                _ = "".join(str(item) for item in response)

            buffer = ""
            has_stopped_yielding = False
            # 4. Agent constructor构建最终提示词
            async for item in self.agent_constructor.ainvoke(inputs):
                if AGENT_MSG in item:
                    result = transform_to_cloud(
                        item[AGENT_MSG], self.controller.resource_config, self.model.model_info.headers
                    )
                    yield result_msg(result, LLM_AGENT_IR)
                else:
                    if has_stopped_yielding:
                        continue  # 彻底不返回给前端了，只等它生成完毕

                    chunk = item["cache_token"]
                    buffer += chunk

                    # 只要遇到包含 "<选择的" 的前置标志，直接截断
                    if "<选择的" in buffer:
                        has_stopped_yielding = True
                        # 将 "<选择的" 之前的内容最后发送一次
                        safe_text = buffer.split("<选择的")[0]
                        if safe_text:
                            yield content_msg(safe_text, LLM_AGENT_IR_CHUNK)
                    else:
                        # 防御性保留最后 4 个字符（防止把 "<选择" 给截断）
                        if len(buffer) > 4:
                            yield content_msg(buffer[:-4], LLM_AGENT_IR_CHUNK)
                            buffer = buffer[-4:]

            yield status_msg("完成对话体验配置", AGENT_HD4, "FINISHED")
            logger.info("\n LLM Agent Configuration Construction Finished")
