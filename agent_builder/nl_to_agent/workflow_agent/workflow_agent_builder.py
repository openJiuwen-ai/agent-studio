# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
import json
import random
import re
import time
from typing import Generator, Dict, Any

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.nl_to_agent.base import OperatorInput
from agent_builder.nl_to_agent.workflow_agent.agent_constructor.agent_constructor import (
    AgentConstructor,
)
from agent_builder.nl_to_agent.workflow_agent.progress_bar import (
    HD0_SOP_JUDGE,
    HD0_INIT,
    HD0_TRANSFORM_SOP,
    SOP_CHUNK,
    MESSAGE_TYPE,
    ANSWER,
    HD0_CREATE_SOP,
    HD1_DESIGN_SOP,
    HD2_DESIGN_MERMAID,
    HD3_MODIFY_MERMAID,
    HD4_CREATE_DL,
    progress_msg,
    result_msg,
    QUESTION_WITHOUT_OPTION,
)
from agent_builder.adapter.exception_bridge import JiuWenBaseException
from agent_builder.adapter.jiuwen_bridge import SystemMessage
from agent_builder.adapter.logger_bridge import logger

from .agent_designer.agent_designer import (
    AgentDesigner,
    NAME_CONTENT,
    NAME_EN_CONTENT,
    DESCRIPTION_CONTENT,
    RESPONSE_CONTENT,
)
from .agent_refiner.agent_refiner import AgentRefiner
from .intention_prompt import REFINE_INTENTION_PROMPT, PLAN_INTENTION_PROMPT
from .sop_generator.sop_generator import SopGenerator, SopMode

WORKFLOW_RESPONSE_CONTENT = "请描述工作流的流程，如果不清楚可回复不清楚\n"


class IntentionOperator:
    """意图操作器。

    该类用于基于用户对话历史，结合大语言模型来识别用户意图，
    判断是否需要对需求进行细化（refine）以及是否提供了完整的流程描述。
    内部包含输入清理与提示词构造逻辑。

    Attributes:
        model: 底层大语言模型实例，用于处理对话与意图识别。
    """

    def __init__(self, model):
        """初始化意图操作器。

        Args:
            model: 底层大语言模型实例。
        """
        self.model = model

    @staticmethod
    def clean_intent(input_text):
        """使用正则表达式从输入文本中提取意图。

        优先提取输入中以 Markdown 格式包裹的 JSON 片段（```json ... ```），
        如果未找到，则返回原始输入文本。

        Args:
            input_text (str): 输入文本，可能包含 JSON 形式的意图信息。

        Returns:
            str: 提取出的 JSON 字符串或原始文本。
        """
        json_pattern = r"```json\n(.*?)```"
        # 查找 Mermaid 部分
        json_match = re.search(json_pattern, input_text, re.DOTALL)
        # 提取匹配的文本
        result = json_match.group(1) if json_match else input_text
        return result

    def operate(self, dig_history, mermaid_code=None):
        """根据对话历史和可选 Mermaid 信息，判断用户意图。

        将用户对话历史格式化为字符串，并结合是否提供了 Mermaid 代码，
        构造相应的提示词交给模型进行处理，识别是否需要 refine，
        以及是否提供了流程描述。

        Args:
            dig_history (str): 对话历史。
            mermaid_code (str, optional): 可选的 Mermaid 流程代码。

        Returns:
            str: 模型输出的意图信息（经过清理）。

        Raises:
            JiuWenException: 当模型服务出错时抛出异常。
        """
        prompt = (
            REFINE_INTENTION_PROMPT.replace("{{mermaid_code}}", mermaid_code).replace(
                "{{dig_history}}", dig_history
            )
            if mermaid_code
            else PLAN_INTENTION_PROMPT.replace("{{dig_history}}", dig_history)
        )
        for item in self.model.chat(
            [SystemMessage(content=prompt)], method="stream", add_prefix=False
        ):
            if item.content:
                return self.clean_intent(item.content)
        raise JiuWenBaseException(
            StatusCode.NL2AGENT_LLM_SERVICE_ERROR.code,
            StatusCode.NL2AGENT_LLM_SERVICE_ERROR.errmsg.format(
                error_msg="大模型服务请求失败"
            ),
        )

    async def aoperate(self, dig_history, mermaid_code=None):
        """根据对话历史和可选 Mermaid 信息，判断用户意图。

        将用户对话历史格式化为字符串，并结合是否提供了 Mermaid 代码，
        构造相应的提示词交给模型进行处理，识别是否需要 refine，
        以及是否提供了流程描述。

        Args:
            dig_history (str): 对话历史。
            mermaid_code (str, optional): 可选的 Mermaid 流程代码。

        Returns:
            collections. AsyncIterable : 模型输出的意图信息（经过清理）。

        Raises:
            JiuWenException: 当模型服务出错时抛出异常。
        """
        prompt = (
            REFINE_INTENTION_PROMPT.replace("{{mermaid_code}}", mermaid_code).replace(
                "{{dig_history}}", dig_history
            )
            if mermaid_code
            else PLAN_INTENTION_PROMPT.replace("{{dig_history}}", dig_history)
        )
        async for item in self.model.achat(
            [SystemMessage(content=prompt)], method="stream", add_prefix=False
        ):
            yield item.raw_content
            if item.content:
                yield self.clean_intent(item.content)
                return
        raise JiuWenBaseException(
            StatusCode.NL2AGENT_LLM_SERVICE_ERROR.code,
            StatusCode.NL2AGENT_LLM_SERVICE_ERROR.errmsg.format(
                error_msg="大模型服务请求失败"
            ),
        )


class WorkflowAgentBuilder:
    """Workflow Agent 构建器。

    该类用于基于用户输入、上下文和外部资源，动态构建工作流类型的智能体（Workflow Agent）。
    它封装了需求澄清、意图识别、设计、细化与构造等完整流程，
    并与控制器（controller_instance）交互以实现异步的用户输入/输出。

    Attributes:
        model: 底层大语言模型实例。
        intention_operator (IntentionOperator): 意图识别与处理的操作器。
        controller (Controller): 当前任务的对话控制器。
        input_adapter (InputAdapter): 输入适配器，用于外部资源检索与数据预处理。
    """

    def __init__(self, model, input_adapter, controller):
        """初始化工作流 Agent 构建器。

        Args:
            model: 底层大语言模型实例。
            input_adapter (InputAdapter): 输入适配器实例。
            controller (Controller): 当前任务的对话控制器。
        """
        self.model = model
        self.intention_operator = IntentionOperator(self.model)
        self.controller = controller
        self.input_adapter = input_adapter
        self.state_handlers = {
            0: self._handle_state_0,
            1: self._handle_state_1,
            2: self._handle_state_2,
            3: self._handle_state_3,
            4: self._handle_state_4,
        }
        self.state_handlers_async = {
            0: self._handle_state_0_async,
            1: self._handle_state_1_async,
            2: self._handle_state_2_async,
            3: self._handle_state_3_async,
            4: self._handle_state_4_async,
        }
        self.state_exception_info = {
            0: (StatusCode.NL2AGENT_PREPROCESS_ERROR, "工作流初始阶段失败："),
            1: (StatusCode.NL2AGENT_PREPROCESS_ERROR, "工作流流程判断阶段失败："),
            2: (StatusCode.NL2AGENT_DESIGN_ERROR, "工作流设计阶段失败："),
            3: (StatusCode.NL2AGENT_DESIGN_ERROR, "工作流完善阶段失败："),
            4: (
                StatusCode.NL2AGENT_TRANSFORM_IR_TO_EICLOUD_ERROR,
                "工作流构造阶段失败：",
            ),
        }

    @staticmethod
    def transform_to_generator(string):
        """将字符串转换为生成器形式。

        用于统一输出格式，支持返回“澄清问题”或普通字符串。

        Args:
            string (str): 待转换的字符串。

        Yields:
            tuple 或 str: 如果是工作流固定响应内容，返回(question 类型)；
                          否则直接返回字符串。
        """
        if string == WORKFLOW_RESPONSE_CONTENT:
            yield json.dumps([{"question": string}], ensure_ascii=False), "question"
        else:
            yield string

    @staticmethod
    async def atransform_to_generator(string):
        """将字符串转换为生成器形式。

        用于统一输出格式，支持返回“澄清问题”或普通字符串。

        Args:
            string (str): 待转换的字符串。

        Yields:
            tuple 或 str: 如果是工作流固定响应内容，返回(question 类型)；
                          否则直接返回字符串。
        """
        if string == WORKFLOW_RESPONSE_CONTENT:
            yield result_msg(
                json.dumps([{"question": string}], ensure_ascii=False),
                QUESTION_WITHOUT_OPTION,
            )
        else:
            yield result_msg(string, QUESTION_WITHOUT_OPTION)

    @staticmethod
    def get_uml(content):
        """从模型输出中提取 UML 代码。

        Args:
            content (str): 模型输出内容。
        Returns:
            str: 提取出的 UML 代码。
        """
        return content.split(RESPONSE_CONTENT)[1]

    @staticmethod
    def _inputs_info_preprocess(inputs):
        """输入信息预处理。

        将插件、知识和子工作流信息序列化为 JSON 字符串，
        以便传递给 LLM 进行处理。

        Args:
            inputs (OperatorInput): 输入数据对象。

        Returns:
            OperatorInput: 预处理后的输入数据对象。
        """
        inputs.plugin_info = (
            json.dumps(inputs.plugin_info, ensure_ascii=False, indent=2)
            if isinstance(inputs.plugin_info, (list, dict))
            else inputs.plugin_info
        )
        inputs.knowledge_info = (
            json.dumps(inputs.knowledge_info, ensure_ascii=False, indent=2)
            if isinstance(inputs.knowledge_info, (list, dict))
            else inputs.knowledge_info
        )
        inputs.sub_workflow_info = (
            json.dumps(inputs.sub_workflow_info, ensure_ascii=False, indent=2)
            if isinstance(inputs.sub_workflow_info, (list, dict))
            else inputs.sub_workflow_info
        )
        return inputs

    def invoke(self, inputs: OperatorInput):
        """工作流 Agent 构建流程。

        包含以下主要步骤：
        1. 检索外部资源并预处理输入。
        2. 根据工作流状态进入对应阶段：初始阶段(0)、流程判断(1)、流程设计(2)、流程修改(3)、工作流生成(4)。

        Args:
            inputs (OperatorInput): 用户输入数据对象。

        Returns:
            generator: AgentConstructor 的输出生成器。
        """
        if self.controller.workflow_state in self.state_handlers:
            try:
                return self.state_handlers[self.controller.workflow_state](inputs)
            except Exception as e:
                status, msg_prefix = self.state_exception_info[
                    self.controller.workflow_state
                ]
                raise JiuWenBaseException(
                    status.code,
                    status.errmsg.format(error_msg=f"{msg_prefix}{str(e)}"),
                ) from e
        raise JiuWenBaseException(
            StatusCode.NL2AGENT_WORKFLOW_STATE_ERROR.code,
            StatusCode.NL2AGENT_WORKFLOW_STATE_ERROR.errmsg.format(
                error_msg="Workflow状态超出定义范围"
            ),
        )

    def _handle_state_0(self, inputs):
        task_id = self.controller.task_id
        context_manager = self.controller.context_manager
        formatted_history = context_manager.get_formatted_history(
            session_id=task_id, intent="分类1"
        )
        provide_process = json.loads(
            self.intention_operator.operate(formatted_history)
        ).get("provide_process")
        if provide_process:
            sop_content = SopGenerator(
                self.model, self.controller, SopMode.TRANSFORM
            ).invoke(inputs)
            inputs.query = sop_content
            return self._handle_state_2(inputs)
        context_manager.add_assistant_message(
            task_id, WORKFLOW_RESPONSE_CONTENT, "分类1"
        )
        self.controller.start_workflow()
        return self.transform_to_generator(WORKFLOW_RESPONSE_CONTENT)

    def _handle_state_1(self, inputs):
        task_id = self.controller.task_id
        context_manager = self.controller.context_manager
        formatted_history = context_manager.get_formatted_history(
            session_id=task_id, intent="分类1"
        )
        provide_process = json.loads(
            self.intention_operator.operate(formatted_history)
        ).get("provide_process")
        if provide_process:
            inputs.query = formatted_history
            sop_content = SopGenerator(
                self.model, self.controller, SopMode.TRANSFORM
            ).invoke(inputs)
        else:
            sop_content = SopGenerator(
                self.model, self.controller, SopMode.GENERATE
            ).invoke(inputs)
        inputs.query = sop_content
        return self._handle_state_2(inputs)

    def _handle_state_2(self, inputs):
        self.controller.design_workflow()
        inputs, plugin_dict, workflow_dict = (
            self.input_adapter.workflow_retrieve_adapter(inputs.query)
        )
        self.controller.resource_config["plugin"] = inputs.plugin_info
        self.controller.resource_config["knowledge"] = inputs.knowledge_info
        self.controller.resource_config["workflow"] = inputs.sub_workflow_info
        self.controller.plugin_dict = plugin_dict
        self.controller.workflow_dict = workflow_dict
        inputs = self._inputs_info_preprocess(inputs)
        return AgentDesigner(
            self.model, self.input_adapter.detail_config, self.controller
        ).invoke(inputs)

    def _handle_state_3(self, inputs):
        task_id = self.controller.task_id
        context_manager = self.controller.context_manager
        self.controller.refine_workflow()
        history = context_manager.get_formatted_history(
            session_id=task_id, intent="分类1"
        )
        mermaid_code = history.split(RESPONSE_CONTENT)[-1].split("用户: ")[0].strip()
        if json.loads(self.intention_operator.operate(history, mermaid_code)).get(
            "need_refined"
        ):
            return AgentRefiner(self.model, self.input_adapter, self.controller).invoke(
                inputs
            )
        return self._handle_state_4(inputs)

    def _handle_state_4(self, inputs):
        task_id = self.controller.task_id
        context_manager = self.controller.context_manager
        self.controller.construct_workflow()
        history = context_manager.get_filtered_messages(
            session_id=task_id, intent="分类1"
        )
        mermaid_code = history[-2]["content"].split(RESPONSE_CONTENT)[1].strip()
        name = history[-2]["content"].split("\n")[0].split(NAME_CONTENT)[1].strip()
        name_en = (
            history[-2]["content"].split("\n")[1].split(NAME_EN_CONTENT)[1].strip()
        )
        description = (
            history[-2]["content"].split("\n")[2].split(DESCRIPTION_CONTENT)[1].strip()
        )
        sop_content = ""
        modify_query = ""
        for idx, tmp in enumerate(history):
            if "工作流SOP：" in tmp["content"] and tmp["role"] == "assistant":
                sop_content = tmp["content"].split("工作流SOP：")[-1].strip()
                modify_query = ";".join(
                    [
                        tmp.get("content")
                        for tmp in history[idx:-1]
                        if tmp.get("role") == "user"
                    ]
                )
                break
        inputs.query = f"# 原始工作流创建指令：\n{sop_content}\n\n# 用户修改意见汇总：{modify_query}"
        agent_construct_generator = AgentConstructor(
            mermaid_code,
            self.model,
            self.input_adapter,
            self.controller,
            name=name,
            name_en=name_en,
            description=description,
        ).invoke(inputs)
        return agent_construct_generator

    async def ainvoke(self, inputs: OperatorInput):
        """工作流 Agent 构建流程。

        包含以下主要步骤：
        1. 检索外部资源并预处理输入。
        2. 根据工作流状态进入对应阶段：初始阶段(0)、流程判断(1)、流程设计(2)、流程修改(3)、工作流生成(4)。

        Args:
            inputs (OperatorInput): 用户输入数据对象。

        Returns:
            generator: AgentConstructor 的输出生成器。
        """
        if self.controller.workflow_state not in self.state_handlers:
            raise JiuWenBaseException(
                StatusCode.NL2AGENT_WORKFLOW_STATE_ERROR.code,
                StatusCode.NL2AGENT_WORKFLOW_STATE_ERROR.errmsg.format(
                    error_msg="Workflow状态超出定义范围"
                ),
            )
        try:
            handler = self.state_handlers_async[self.controller.workflow_state]
            async for chunk in handler(inputs):
                yield chunk
        except JiuWenBaseException as e:
            raise e
        except Exception as e:
            status, msg_prefix = self.state_exception_info[
                self.controller.workflow_state
            ]
            raise JiuWenBaseException(
                status.code,
                status.errmsg.format(error_msg=f"{msg_prefix}{str(e)}"),
            ) from e

    async def _handle_state_0_async(self, inputs):
        yield HD0_INIT
        task_id = self.controller.task_id
        context_manager = self.controller.context_manager
        formatted_history = context_manager.get_formatted_history(
            session_id=task_id, intent="分类1"
        )
        sop_content = ""
        last_item = None
        yield HD0_SOP_JUDGE
        async for item in self.intention_operator.aoperate(formatted_history):
            last_item = item
        provide_process = json.loads(last_item).get("provide_process")
        if provide_process:
            yield HD0_TRANSFORM_SOP
            async for chunk in SopGenerator(
                self.model, self.controller, SopMode.TRANSFORM
            ).ainvoke(inputs):
                if SOP_CHUNK not in chunk.get(MESSAGE_TYPE):
                    sop_content = chunk.get(ANSWER)
                yield chunk  # SOP信息
            inputs.query = sop_content
            async for item in self._handle_state_2_async(inputs):
                yield item
        else:
            yield HD0_CREATE_SOP
            context_manager.add_assistant_message(
                task_id, WORKFLOW_RESPONSE_CONTENT, "分类1"
            )
            await self.controller.async_start_workflow()
            async for item in self.atransform_to_generator(WORKFLOW_RESPONSE_CONTENT):
                yield item

    async def _handle_state_1_async(self, inputs):
        yield HD1_DESIGN_SOP
        task_id = self.controller.task_id
        context_manager = self.controller.context_manager
        formatted_history = context_manager.get_formatted_history(
            session_id=task_id, intent="分类1"
        )
        last_item = None
        async for item in self.intention_operator.aoperate(formatted_history):
            last_item = item
        provide_process = json.loads(last_item).get("provide_process")
        sop_content = ""
        if provide_process:
            async for chunk in SopGenerator(
                self.model, self.controller, SopMode.TRANSFORM
            ).ainvoke(inputs):
                if SOP_CHUNK not in chunk.get(MESSAGE_TYPE):
                    sop_content = chunk.get(ANSWER)
                yield chunk  # SOP信息
        else:
            async for chunk in SopGenerator(
                self.model, self.controller, SopMode.GENERATE
            ).ainvoke(inputs):
                if SOP_CHUNK not in chunk.get(MESSAGE_TYPE):
                    sop_content = chunk.get(ANSWER)
                yield chunk  # SOP信息
        inputs.query = sop_content
        async for chunk in self._handle_state_2_async(inputs):
            yield chunk

    async def _handle_state_2_async(self, inputs):
        yield HD2_DESIGN_MERMAID
        await self.controller.async_design_workflow()
        inputs, plugin_dict, workflow_dict = (
            self.input_adapter.workflow_retrieve_adapter(inputs.query)
        )
        self.controller.resource_config["plugin"] = inputs.plugin_info
        self.controller.resource_config["knowledge"] = inputs.knowledge_info
        self.controller.resource_config["workflow"] = inputs.sub_workflow_info
        self.controller.plugin_dict = plugin_dict
        self.controller.workflow_dict = workflow_dict
        inputs = self._inputs_info_preprocess(inputs)
        designer = AgentDesigner(
            self.model, self.input_adapter.detail_config, self.controller
        )
        async for chunk in designer.ainvoke(inputs):
            yield chunk

    async def _handle_state_3_async(self, inputs):
        task_id = self.controller.task_id
        context_manager = self.controller.context_manager
        await self.controller.async_refine_workflow()
        history = context_manager.get_formatted_history(
            session_id=task_id, intent="分类1"
        )
        mermaid_code = history.split(RESPONSE_CONTENT)[-1].split("用户: ")[0].strip()
        last_item = None
        async for item in self.intention_operator.aoperate(history, mermaid_code):
            last_item = item
        need_refined = json.loads(last_item).get("need_refined")
        if need_refined:
            yield HD3_MODIFY_MERMAID
            refiner = AgentRefiner(self.model, self.input_adapter, self.controller)
            async for item in refiner.ainvoke(inputs):
                yield item
        else:
            async for item in self._handle_state_4_async(inputs):
                yield item

    async def _handle_state_4_async(self, inputs):
        yield HD4_CREATE_DL
        task_id = self.controller.task_id
        context_manager = self.controller.context_manager
        await self.controller.async_construct_workflow()
        history = context_manager.get_filtered_messages(
            session_id=task_id, intent="分类1"
        )
        mermaid_code = history[-2]["content"].split(RESPONSE_CONTENT)[1].strip()
        name = history[-2]["content"].split("\n")[0].split(NAME_CONTENT)[1].strip()
        name_en = (
            history[-2]["content"].split("\n")[1].split(NAME_EN_CONTENT)[1].strip()
        )
        description = (
            history[-2]["content"].split("\n")[2].split(DESCRIPTION_CONTENT)[1].strip()
        )
        sop_content = ""
        modify_query = ""
        for idx, tmp in enumerate(history):
            if "工作流SOP：" in tmp["content"] and tmp["role"] == "assistant":
                sop_content = tmp["content"].split("工作流SOP：")[-1].strip()
                modify_query = ";".join(
                    [
                        tmp.get("content")
                        for tmp in history[idx:-1]
                        if tmp.get("role") == "user"
                    ]
                )
                break
        inputs.query = f"# 原始工作流创建指令：\n{sop_content}\n\n# 用户修改意见汇总：{modify_query}"
        agent_construct_generator = AgentConstructor(
            mermaid_code,
            self.model,
            self.input_adapter,
            self.controller,
            name=name,
            name_en=name_en,
            description=description,
        )

        parser = StreamNodeParser()
        tracker = PDDProgressTracker(agent_construct_generator.refine_mermaid)
        start_time = time.time()
        async for chunk in agent_construct_generator.ainvoke(inputs):
            partial_json = ""
            # 处理你的特定数据结构 (Tuple with raw_content)
            if isinstance(chunk, tuple) and hasattr(chunk[0], "raw_content"):
                partial_json = chunk[0].raw_content
            # --- 核心逻辑：解析并计算进度 ---
            if partial_json:
                # 将碎片喂给解析器，如果拼出了完整节点，这里会有产出
                for node in parser.process_chunk(partial_json):
                    # A. 获取节点信息
                    node_id = node.get("id", "unknown_node")
                    node_type = node.get("type", "Processing")

                    # B. 计算 PDD 进度
                    progress_value = tracker.update(node_type)

                    # C. Yield 目标格式 (节点名, 进度值)
                    # 例如: ('node_start', 8.5)
                    current_elapsed = int(time.time() - start_time)
                    yield progress_msg(
                        node,
                        tracker.node_count,
                        tracker.total_estimated,
                        current_elapsed,
                        progress_value,
                    )
                    if progress_value == 100:
                        parser = StreamNodeParser()
                        tracker = PDDProgressTracker(
                            agent_construct_generator.refine_mermaid
                        )
                        start_time = time.time()
            else:
                yield chunk


class StreamNodeParser:
    """流式 JSON 解析器：负责把碎片拼成完整的 Node"""

    def __init__(self):
        self.buffer = ""
        self.brace_depth = 0
        self.in_node = False

    def process_chunk(self, chunk: str) -> Generator[Dict[str, Any], None, None]:
        """
        处理输入的JSON数据块，生成完整的JSON节点。

        param chunk: 输入的JSON数据块字符串
        return: 生成器，返回完整的JSON节点字典
        """
        for char in chunk:
            if not self.in_node:
                # 过滤列表外层字符
                if char in ["[", "]", ",", "\n", " ", "\t"]:
                    continue
                if char == "{":
                    self.in_node = True
                    self.buffer += char
                    self.brace_depth = 1
                continue

            if self.in_node:
                self.buffer += char
                if char == "{":
                    self.brace_depth += 1
                elif char == "}":
                    self.brace_depth -= 1
                if self.brace_depth == 0:
                    try:
                        yield json.loads(self.buffer)
                    except Exception:
                        logger.warning(
                            "NL2: Failed to parse streaming LLM output as JSON. Error: {e}"
                        )
                        continue
                    finally:
                        self.buffer = ""
                        self.in_node = False


class PDDProgressTracker:
    """PDD 风格进度计算器：自动适应流程长短，生成那种“快到了但就是不到”的进度

    Param:
        mermaid_text (str, 可选): Mermaid 图文本，用于自动计算节点总数。默认为 None。

    Attributes:
        current_progress (float): 当前进度百分比。
        node_count (int): 已处理的节点数量。
        total_estimated (int): 预估的总节点数。
    """

    def __init__(self, mermaid_text=None):
        self.current_progress = 0.0
        self.node_count = 0

        # 自动计算总数
        if mermaid_text:
            self.total_estimated, _ = self.parse_mermaid_node_count(mermaid_text)
            # 安全兜底：如果解析出来是 0 或 1，强制设为 10 避免除以零或步子太大
            self.total_estimated = max(self.total_estimated, 3)
        else:
            self.total_estimated = 10

    def update(self, node_type: str) -> float:
        # 2. 结束信号：直接拉满
        self.node_count += 1
        if node_type == "End":
            self.current_progress = 100.0

            return 100.0

        # 3. 计算基准步长 (平均每一步该走多少)
        # 例如 20 个节点，平均每步 5%；50 个节点，平均每步 2%
        base_step = 100.0 / self.total_estimated

        # 计算当前完成度比例
        completion_ratio = self.node_count / self.total_estimated

        increment = 0.0

        # --- 核心算法优化 ---

        if completion_ratio < 0.4:
            # 【诱导期】前 40%：
            # 策略：基准步长的 1.2 ~ 2.0 倍
            increment = base_step * random.uniform(1.2, 2.0)

        elif completion_ratio < 0.8:
            # 【平稳期】40% - 80%：
            # 策略：基准步长的 0.5 ~ 1.0 倍
            increment = base_step * random.uniform(0.5, 1.0)

        else:
            # 【灵魂期】80% 以后，或者节点数超过了预估值：
            # 策略：(100 - 当前进度) * 衰减系数
            remaining_space = 99.99 - self.current_progress

            # decay 加重。模拟只差 0.01
            decay = random.uniform(0.05, 0.15)
            increment = remaining_space * decay

            # 保证最小颗粒度，避免彻底不动 (至少动 0.01)
            increment = max(0.01, increment)

        # 4. 应用增量
        self.current_progress += increment

        # 5. 绝对钳位：在收到 End 之前，死都不让它到 100
        if self.current_progress >= 99.99:
            self.current_progress = 99.99

        return round(self.current_progress, 2)

    def parse_mermaid_node_count(self, mermaid_text: str):
        """
        从 Mermaid 文本中解析出唯一的节点数量和 ID 列表
        """
        # 移除头部声明 (flowchart TD/LR graph...)
        clean_text = re.sub(
            r"^\s*(flowchart|graph)\s+\w+.*$", "", mermaid_text, flags=re.MULTILINE
        )

        # 移除引号内的内容把 ["提问器..."] 中的中文去掉
        clean_text = re.sub(r'["\'].*?["\']', "", clean_text)

        # 移除连接线上的标签例如 C --> |label| D 中的 |label|
        clean_text = re.sub(r"\|.*?\|", "", clean_text)

        # 移除注释
        clean_text = re.sub(r"%%.*", "", clean_text)

        # 提取剩下的 字母/数字/下划线 组合
        raw_tokens = re.findall(r"\b[a-zA-Z0-9_]+\b", clean_text)

        # 过滤关键字并去重
        keywords = {"subgraph", "end", "click", "style", "classDef", "linkStyle"}
        unique_nodes = set(token for token in raw_tokens if token not in keywords)

        return len(unique_nodes), unique_nodes
