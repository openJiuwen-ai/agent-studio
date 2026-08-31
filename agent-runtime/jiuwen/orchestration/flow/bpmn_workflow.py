#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""Workflow based on the bpmn specification."""

import asyncio
import copy
import datetime
import json
import os
import re
import time
import uuid
from collections.abc import AsyncIterable
from typing import Generator, Union, AsyncGenerator
from typing import Optional

from SpiffWorkflow.bpmn import workflow
from SpiffWorkflow.spiff.parser.process import SpiffBpmnParser

try:
    from SpiffWorkflow.task import TaskState, TaskStateNames
except ImportError:
    from SpiffWorkflow.task import TaskState

    TaskStateNames = {
        getattr(TaskState, name): name
        for name in getattr(TaskState, "_names", [])
        if hasattr(TaskState, name)
    }
from SpiffWorkflow.workflow import logger as spiff_logger
from pydantic import ValidationError

from jiuwen.common.configs.env_constants import (
    EXECUTION_NODE_TIMEOUT_KEY,
    WORKFLOW_MAX_PARALLEL_COMPONENT_NUM_KEY,
)
from jiuwen.common.exception import status_code
from jiuwen.common.exception.base import (
    JiuWenBaseException,
    InterruptException,
    WorkflowAbortException,
    InnerException,
    ErrorBody,
)
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.utils.utils import format_exception_reason
from jiuwen.orchestration.common.perf_log import wf_performance_buffer
from jiuwen.common.log.base import logger, performance_logger
from jiuwen.orchestration.callbacks.constants import TriggerEventName
from jiuwen.orchestration.callbacks.manager import CallbackHandlerManager
from jiuwen.orchestration.callbacks.tracer import Tracer, Span
from jiuwen.orchestration.common.exception import WorkflowExecuteException
from jiuwen.orchestration.flow.base_workflow import BaseWorkflow, Node, SwitchNode
from jiuwen.orchestration.flow.components.AsyncGeneratorBroadcaster import (
    AsyncGeneratorBroadcaster,
)
from jiuwen.orchestration.flow.components.flow_message import MESSAGE_RUNTIME_KEYWORD
from jiuwen.orchestration.flow.components.flow_card import CARD_RUNTIME_KEYWORD
from jiuwen.orchestration.flow.components.util import (
    format_interaction_res,
    format_node_info_with_metadata,
    split_condition_expressions,
    split_one_condition_expression,
    convert_to_old_type,
    validate_ref_recursive,
)
from jiuwen.orchestration.flow.constant import (
    SYSTEM_FIELDS,
    MAXIMUM_LENGTH_OF_A_REGULAR_STRING,
    LOOP_DEFAULT_LOOP_MAX_NUM,
    BPMN_COMPLETED_MESSAGE,
    DEFAULT_EXECUTION_NODE_TIMEOUT,
    EXECUTION_ID,
    INVOKE_ID,
    CONVERSATION_ID,
    EXCEPTION_OUTPUT_RESULT_SUCCESS,
    ENVIRONMENT_VARIABLES,
    MEMORY_VARIABLES,
    ENV_PREFIX,
    MEM_MAP,
    REQUEST_PREFIX,
    REQUEST_VARIABLES,
)
from jiuwen.orchestration.flow.constant import (
    WORKFLOW_CHAT_MANAGER,
    STRUCTURE_POSITION_INPUTS,
    STRUCTURE_POSITION_OUTPUTS,
    WORKFLOW_API_CONFIGS,
    WORKFLOW_EXECUTE_DEBUG_INFO,
    WORKFLOW_DEFAULT_LOOP_MAX_NUM,
    USER_FIELDS,
    BPMN_VARIABLE_POOL_SEPARATOR,
)
from jiuwen.orchestration.flow.enum import NodeType, StreamDataMsg, ExecutionStatus
from jiuwen.orchestration.flow.component_class_pool import component_class_pool
from jiuwen.orchestration.flow.exception_handler import rewrite_timeout
from jiuwen.orchestration.flow.model.workflow_data_class import WorkflowMetadata
from jiuwen.orchestration.flow.runtime_context import RuntimeContext
from jiuwen.orchestration.flow.stream.base import StreamCode, StreamData
from jiuwen.orchestration.flow.stream.workflow_streaming import (
    WorkflowStreamCallback,
    StreamWriter,
)
from jiuwen.orchestration.flow.nested_structure_utils import (
    get_value_from_nested_structure_by_path_list,
    set_value_to_nested_structure_by_path,
)
from jiuwen.orchestration.flow.string_utils import get_ref_str, split_string
from jiuwen.orchestration.flow.utils import (
    Json2BpmnXmlParser,
    pre_process_inputs,
    is_model_output_json,
    get_final_result_of_flow_generator,
    validate_workflow_json,
    get_streaming_finish_stream_data,
    send_stream_data_by_stream_callback,
    force_convert_component_by_schema_raise_exception,
    get_streaming_single_component_stream_data,
    dict_with_generators_replaced,
    verify_the_security_of_variables_for_spiffworkflow,
    get_final_result_of_flow_async_generator,
)
from jiuwen.orchestration.flow.state import WorkflowSpec, BpmnInstanceState
from jiuwen.plugin.common.constant import WORKFLOW_ID
from jiuwen.serve.controllers.execution.open_utils import (
    deserialize_object,
    serialize_object,
)
from jiuwen.orchestration.flow.constant import (
    EXCEPTION_HANDLE_INTERRUPT,
    EXCEPTION_HANDLE_DEFAULT_OUTPUTS,
    EXCEPTION_HANDLE_ERROR_BRANCH,
    EXCEPTION_OUTPUT_RESULT,
    EXCEPTION_OUTPUT_RESULT_FAILED,
)

# 设置spiffworkflow的logger级别，避免spiffworkflow的日志信息在框架内大量打印
spiff_logger.setLevel("WARNING")
del spiff_logger

MAX_PARALLEL_COMPONENT_NUM = int(
    os.environ.get(WORKFLOW_MAX_PARALLEL_COMPONENT_NUM_KEY, 20)
)

NOT_YET_COMPLETED = 40  # 此状态码 大于 STARTED，但小于 COMPLETED
TaskStateNames[NOT_YET_COMPLETED] = "NOT_YET_COMPLETED"

CONDITION_OP = {
    "==": "==",
    "!=": "!=",
    "in": "in",
    "not_in": "not in",
    "&&": "and",
    "||": "or",
}

"""
将新节点类型值映射到旧节点类型的字典。

此字典用于将NodeType枚举类的值转换为对应的旧节点类型名称。
"""

BJ_TZ = datetime.timezone(
    datetime.timedelta(hours=8),
    name="Asia/Beijing",
)

# workflow执行状态
EXECUTE_ERROR = 0  # 执行失败
EXECUTE_SUCCESS = 1  # 执行成功
EXECUTING = 2  # 执行中

NAME = "name"
ID = "id"
TYPE = "type"
_ANSWER = "answer"
DEFAULT_EXECUTION_ID = ""
INTERACT_COMPONENT_TYPES = [
    NodeType.QUESTIONER.value,
    NodeType.SUB_WORKFLOW.value,
    NodeType.INPUT.value,
    NodeType.AGENT.value,
]
NOT_SUPPORT_EXCEPTION_COMPONENT_TYPES = [NodeType.LOOP.value, NodeType.ERROR_END.value]

# 自定义节点多分支判断标志
CUSTOM_MULTI_BRANCH_SIGN = "@@"

LOG_VERBOSE_MODE = os.getenv("LOG_VERBOSE", "false").lower() == "true"
CLASSIFICATION_ID = "classificationId"
INVALID_CLASSIFICATION_ID = -1


class BpmnWorkflow(BaseWorkflow):
    """Workflow based on the bpmn specification."""

    inputs = None
    outputs = None
    status = EXECUTING
    workflow = None

    def __init__(self):
        self.runtime_context: RuntimeContext = None
        self.nodes = {}
        self.workflow_json = None
        self.bpmn_spec = None
        self.name: str = None
        self.id: str = None
        self.description: str = None
        self._chat_manager = None
        self._runtime_debug_info = None
        self.tracer = None
        self._loop_max_num = 0
        self._stream_callback = None
        # 存储循环组件，key为循环体组件id，value为loop_id
        self.loop_comp = {}
        self.stop_bpmn_flag = False  # 为True时，退出bpmn执行
        self._cur_node = (
            None  # 记录当前运行的组件，并行情况下会随着并行任务提交顺序变化
        )
        self.generator_data_path = []  # 记录全局变量池中生成器类型数据的路径，状态导出时需要展平这些路径所对应的值
        self.node_broadcasters = {}

    @staticmethod
    def parse_reference(value):
        """Parse reference."""
        parse_value = value

        # 判断是否为引用表达式，如果是则替换为在spiffworkflow中存储的真实变量名
        pattern = re.compile(r"\$\{([^{}]+)\}")
        if isinstance(value, str):
            match = pattern.search(value[:MAXIMUM_LENGTH_OF_A_REGULAR_STRING])
            if match:
                # 把形如 start.123 的字符串替换为 start_123
                parse_value = match.group(1).replace(".", BPMN_VARIABLE_POOL_SEPARATOR)
        return parse_value

    @staticmethod
    def assemble_condition_expression(left_value, mid_op, right_value) -> str:
        """Assemble condition expression."""
        verify_the_security_of_variables_for_spiffworkflow([left_value, right_value])
        return "({} {} {})".format(left_value, CONDITION_OP[mid_op], right_value)

    @staticmethod
    def _get_intent_detection_switch_node_key(intent_detection_id: str) -> str:
        """
        For component IntentDetection, its branch needs to be separately registered as a SwitchNode.
        This function returns the key value of the SwitchNode in the node set.

        The current construction rule is to add _llm to the original node id.
        Args:
            intent_detection_id: original node id
        return:
            processed key
        """
        return intent_detection_id + "_llm"

    @staticmethod
    def _try_parse_json(output):
        try:
            if isinstance(output, str):
                # 解析 JSON
                output = json.loads(output)
        except json.JSONDecodeError as e:
            logger.warning(
                "Action result is not valid JSON: %s",
                str(e),
                simple_log="Action result is not valid JSON",
            )
        return output

    @staticmethod
    def _parse_intent_detection_branch_config(
        intent_detection_config: dict, intent_detection_id: str
    ) -> Optional[list[dict]]:
        """
        Convert intent detection branch config to branch config.
        Intent detection config format is:
                "branches": [
                    {
                        "id": "branch_1",
                        "catalog": "吃饭"
                    },
                    {
                        "id": "branch_2",
                        "catalog": "睡觉"
                    }
                ]
        """
        if not intent_detection_config or not intent_detection_config.get("branches"):
            return None
        res = []
        for branch in intent_detection_config["branches"]:
            replaced_catlog = int(branch["id"].replace("branch_", ""))
            res.append(
                {
                    "id": f"{intent_detection_id}_{branch['id']}",
                    "boolExpression": f"{replaced_catlog} == ${{{intent_detection_id}['classificationId']}}",
                }
            )
        return res

    @staticmethod
    def _judge_values_contains_type_of_generator(origin_input: dict) -> bool:
        """
        判断一个dict中所有的值是否包含生成器类型
        """
        for cur_value in origin_input.values():
            if isinstance(cur_value, Generator):
                return True
        return False

    @staticmethod
    def _filter_empty_user_fields_entries(origin_inputs: dict):
        """
        去除origin_inputs中，userFields下值为空字符串的元素
        :param origin_inputs: 待清理的字典

        :return: None
        """
        keys_to_delete = []
        for name, value in origin_inputs.get(USER_FIELDS).items():
            if value == "":
                keys_to_delete.append(name)
        for name in keys_to_delete:
            del origin_inputs.get(USER_FIELDS)[name]

    @staticmethod
    def _process_exception(
        exception: Exception, invokable: Node
    ) -> JiuWenBaseException:
        """
        处理执行过程中发生的异常。将其封装为JiuWenBaseException
        :param exception: Exception: 原始异常
        :return: JiuWenBaseException: 格式化后的异常
        """
        # JiuWenBaseException说明是可知的报错，其他类型的报错为未预知的错误，需要封装为JiuWenBaseException后再抛出
        if isinstance(exception, JiuWenBaseException):
            err_msg = exception.message
        else:
            err_msg = StatusCode.WORKFLOW_COMPONENT_EXECUTE_ERROR.errmsg.format(
                invokable.type, getattr(exception, "message", None) or str(exception)
            )
        return JiuWenBaseException(
            message=err_msg,
            error_code=exception.error_code
            if isinstance(exception, JiuWenBaseException)
            else StatusCode.WORKFLOW_COMPONENT_EXECUTE_ERROR.code,
            node_id=exception.node_id
            if hasattr(exception, "node_id") and exception.node_id is not None
            else invokable.id,
            node_name=exception.node_name
            if hasattr(exception, "node_name") and exception.node_name is not None
            else invokable.name,
            node_type=exception.node_type
            if hasattr(exception, "node_type") and exception.node_type is not None
            else invokable.type,
        )

    # 自定义节点的多分支,将分支名中含有@@的branch_id转成bpmn格式
    @staticmethod
    def _get_custom_multi_branch(condition_node_type: str, branch_id: str):
        # 将分支的@@左右两侧分割
        branch_split_res = branch_id.split("@@")
        # 获取当前的自定义节点id
        branch_split_res_front = branch_split_res[0]
        # 获取当前自定义节点的分支名称
        branch_split_res_suffix = branch_split_res[1]
        # 从当前的分支名称中获取id，比如：当前分支名是branch_123,那么提取分支id=123
        branch_split_id = branch_split_res_suffix.split("_")[1]
        # 如果当前的自定义节点需要多分支，那么需要在节点的invoke或ainvoke中返回'result'
        # 如：return dict(result="123"）
        return "'{}' == {}['result']".format(branch_split_id, branch_split_res_front)

    # 判断当前的节点是否需要人机交互
    @staticmethod
    def _is_custom_hci(invokable):
        if invokable.action is None:
            return False
        if not hasattr(invokable.action, "node_state"):
            return False
        return True

    @staticmethod
    def _get_nodes_states_dict(nodes: dict):
        """
        获得nodes_states字典
        :return:
        """
        nodes_info = {}
        nodes_states = {}
        for node_id, node in nodes.items():
            # 跳过意图分类组件对应的SwitchNode组件
            if isinstance(node, SwitchNode) and not hasattr(node, "type"):
                continue
            # 跳过排他网关
            if (
                hasattr(node, "id")
                and Json2BpmnXmlParser.loop2gate_before(node.id) == node_id
            ):
                continue
            node_info = dict(
                id=node.id,
                type=node.type,
                name=node.name,
                configs=node.configs,
                inputs=node.inputs,
                outputs=node.outputs,
            )
            nodes_info[node_id] = node_info

            node_state = node.action.get_state()
            nodes_states[node_id] = node_state
        return nodes_info, nodes_states

    @staticmethod
    def _is_only_support_interrupt(invokable: Node) -> bool:
        """判断Node异常处理是否只支持中断
        llm组件且responseFormat为非json时为流式输出
        """

        if (invokable.type == NodeType.LLM.value) and invokable.configs.get(
            "responseFormat", {}
        ).get("type", "") != "json":
            return True
        return False

    @staticmethod
    def _is_support_error_branch(invokable: Node) -> bool:
        """判断Node是否支持异常分支
        MESSAGE和end不支持异常分支
        """
        if (
            invokable.type
            not in [NodeType.MESSAGE.value, NodeType.CARD.value, NodeType.END.value]
            and invokable.exception_config.handle_type == EXCEPTION_HANDLE_ERROR_BRANCH
        ):
            return True
        if invokable.exception_config.is_config and invokable.type in [
            NodeType.MESSAGE.value,
            NodeType.CARD.value,
            NodeType.END.value,
        ]:
            logger.warning(f"{invokable.type}_{invokable.id} not support error branch")
        return False

    @staticmethod
    def _is_inputs_contains_generator(invokable_input) -> bool:
        """递归判断是否包含生成器类型"""
        if isinstance(invokable_input, (Generator, AsyncGenerator)):
            return True
        if isinstance(invokable_input, dict):
            return any(
                BpmnWorkflow._is_inputs_contains_generator(v)
                for v in invokable_input.values()
            )
        if isinstance(invokable_input, list):
            return any(
                BpmnWorkflow._is_inputs_contains_generator(v) for v in invokable_input
            )
        return False

    @staticmethod
    def _template_replace(origin_data, replace_data):
        """将origin_data中的{{}}替换对应的值"""

        cur_invokable_node_inputs = origin_data or {}
        stack = [
            (cur_invokable_node_inputs, None, None)
        ]  # (current, parent, key/index)
        while stack:
            current, parent, key = stack.pop()

            if isinstance(current, dict):
                for k, v in current.items():
                    stack.append((v, current, k))
            elif isinstance(current, list):
                for i, item in enumerate(current):
                    stack.append((item, current, i))
            elif isinstance(current, str):
                match_str = get_ref_str(current)
                if match_str:
                    # 获取真实的值
                    new_value = get_value_from_nested_structure_by_path_list(
                        nested_structure=replace_data, path=match_str
                    )
                    parent[key] = new_value

        return cur_invokable_node_inputs

    @staticmethod
    def _merge_dicts(origin_output: dict, default_output: dict) -> dict:
        """将default_output中的值替换origin_output"""
        result = origin_output.copy()
        for key in default_output:
            if key in result:
                if isinstance(result[key], dict) and isinstance(
                    default_output[key], dict
                ):
                    result[key] = BpmnWorkflow._merge_dicts(
                        result[key], default_output[key]
                    )
                else:
                    result[key] = default_output[key]
        return result

    async def async_clean_up(self, running_tasks: dict):
        """清理task资源"""
        try:
            tasks = list(running_tasks.values())
            if tasks:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
            logger.debug("bpmn Workflow (id=%s) clean up done.", id(self))
        except Exception as e:
            logger.error(
                "bpmn_workflow资源清理失败，失败原因：{}".format(str(e)),
                simple_log="bpmn_workflow资源清理失败",
            )
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_CLEAR_RESOURCES_ERROR_AFTER_EXECUTION.code,
                message=StatusCode.WORKFLOW_CLEAR_RESOURCES_ERROR_AFTER_EXECUTION.errmsg,
            ) from e

    def instantiate(
        self,
        data: Union[dict, WorkflowSpec, BpmnInstanceState] = None,
        runtime_context: RuntimeContext = None,
        loop_max_num=WORKFLOW_DEFAULT_LOOP_MAX_NUM,
    ):
        """初始化bpmn_workflow"""
        self.runtime_context = runtime_context if runtime_context else RuntimeContext()
        if isinstance(data, WorkflowSpec):
            # 从 bpmn_spec 重建
            self._spec_to_workflow(data)
            self.workflow_json = data.ir
        elif isinstance(data, BpmnInstanceState):
            # 从state初始化
            self._load_state(data)
            self.workflow_json = data.workflow_json
        elif data is not None:
            # 从 IR 初始化
            self.workflow_json = data
            validate_workflow_json(data)
            self._json_to_workflow(data)
        else:
            self.workflow_json = {}
        self.name = self.workflow_json.get("workflowName", "")
        self.id = self.workflow_json.get("workflowId", "")
        self.description = self.workflow_json.get("description", "")
        self._chat_manager = self.runtime_context.get(WORKFLOW_CHAT_MANAGER, None)
        self._runtime_debug_info = self.runtime_context.get(
            WORKFLOW_EXECUTE_DEBUG_INFO, {}
        )
        if not self.tracer:
            self.tracer = Tracer(self.runtime_context)
        self._loop_max_num = loop_max_num

    def get_state(self) -> BpmnInstanceState:
        """
        Get workflow state and return an object of WorkflowState type.
        """
        # 1. 序列化bpmn workflow实例，获得workflow_binary
        # 额外处理final_output（可能包含generator对象）
        if self.workflow.data.get("final_output"):
            self.workflow.data.pop("final_output")

        workflow_binary = serialize_object(self.workflow)

        # 2. 遍历nodes字典，对其中每一个组件调用get_state导出NodeState，获得nodes_states字典
        nodes_info, nodes_states = self._get_nodes_states_dict(self.nodes)

        # 3. 拼接BpmnInstanceState对象
        return BpmnInstanceState(
            name=self.name,
            id=self.id,
            description=self.description,
            nodes_info=nodes_info,  # 除action外的其他组件属性-node_info字典，恢复组件时根据此重新实例化
            nodes_states=nodes_states,  # <node_id: NodeState>
            binary_workflow=workflow_binary,
            loop_comp=self.loop_comp,
            workflow_json=self.workflow_json,
            trace_state=self.tracer.get_state(),
        )

    def set_end_invoke_output(self, invokable: Node, invokable_input: dict):
        """
        当前框架只能传入input，为了减少修改，把output也放到input里
        """
        outputs = self._pre_process_inputs(invokable, False)
        if outputs is None or USER_FIELDS not in outputs:
            return
        invokable_input.setdefault(USER_FIELDS, {}).update(
            {"#end_" + k: v for k, v in outputs.get(USER_FIELDS, {}).items()}
        )

    async def timed_task(self, task, task_label="", timeout: Optional[int] = None):
        """
        Run the given function with a timeout control using asyncio.wait_for().

        timeout(int): Maximum allowed runtime in seconds
        """
        # 如果在指定超时时间内协程尚未完成，wait_for 会调用其内部任务的 cancel() 方法自动取消任务，并最终抛出 TimeoutError
        # （另外，不推荐去忽略 CancelledError，因为这会打破 asyncio 的取消约定，使得任务状态变得不确定
        #  对于特定不需要设置定时时长的任务，比如子工作流和循环组件的执行，不采取此封装就可以了）
        try:
            wait_time = timeout or int(
                os.environ.get(
                    EXECUTION_NODE_TIMEOUT_KEY, DEFAULT_EXECUTION_NODE_TIMEOUT
                )
            )
        except ValueError:
            wait_time = DEFAULT_EXECUTION_NODE_TIMEOUT
        try:
            return await asyncio.wait_for(task, timeout=wait_time)
        except asyncio.TimeoutError as e:
            if self._chat_manager.get_control_qsize():
                # 假如 asyncio.wait_for() timeout了，task会被直接cancel()，可能会导致_on_recv执行到一半，
                # 也就是 get_control 少了一次，需要在异常处理中补上
                await self._chat_manager.get_control()
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_COMPONENT_EXECUTE_TIMEOUT.code,
                message=StatusCode.WORKFLOW_COMPONENT_EXECUTE_TIMEOUT.errmsg.format(
                    task_label=task_label, timeout=wait_time
                ),
            ) from e

    async def ainvoke(self, inputs: dict):
        """bpmn_workflow 非流式接口"""
        self._stream_callback = None
        return await self._arun(inputs=inputs)

    async def astream(self, inputs: dict):
        """bpmn_workflow 流式接口"""
        self._stream_callback = WorkflowStreamCallback(
            StreamWriter(chat_manager=self._chat_manager)
        )
        return await self._arun(inputs=inputs)

    def _stop_execution(self):
        logger.info(
            " workflow 停止执行 "
            "| workflow_id: {} "
            "| execution_id: {} "
            "| conversation_id: {}".format(
                self._runtime_debug_info.get(WORKFLOW_ID, ""),
                self._runtime_debug_info.get(EXECUTION_ID, ""),
                self._runtime_debug_info.get(CONVERSATION_ID, ""),
            ),
            simple_log=" workflow 停止执行 ",
        )

        raise JiuWenBaseException(
            error_code=StatusCode.WORKFLOW_TERMINATION_OF_EXECUTION.code,
            message=StatusCode.WORKFLOW_TERMINATION_OF_EXECUTION.errmsg.format(
                exec_id=self._runtime_debug_info.get(EXECUTION_ID, "")
            ),
        )

    def _get_loop_cmp_max_cnt(self, node_id, loop_cmp, node_execution_counts: dict):
        """
        获取循环体内组件的最大循环次数
        :param node_id: 循环组件id
        :param loop_cmp: 记录组件id->循环组件映射
        :param node_execution_counts: 组件执行次数
        :return: 最大循环次数
        """
        cmp_ids = [key for key, item in loop_cmp.items() if item == node_id]
        max_cnt = 0
        if cmp_ids:
            max_cnt = max([node_execution_counts.get(cmp_id, 0) for cmp_id in cmp_ids])
        return max_cnt

    def _check_the_number_of_cycles(
        self, invokable: Node, node_execution_counts: dict, loop_max_num
    ):
        """
        Check the number of cycles. If the number of cycles is greater than self._loop_max_num, an exception is thrown.
        Args:
            invokable: the node that is being executed.
        """
        cur_running_node_id = invokable.id
        _loop_max_num = loop_max_num
        if invokable.type == NodeType.LOOP.value:
            # 将循环组件的循环次数置为循环体内组件的执行次数
            _loop_max_num = invokable.configs.get(
                "loopMaxNum", LOOP_DEFAULT_LOOP_MAX_NUM
            )
            node_execution_counts[cur_running_node_id] = self._get_loop_cmp_max_cnt(
                invokable.id, self.loop_comp, node_execution_counts
            )

        # 获取当前执行的node的执行次数，并进行更新
        origin_counts = node_execution_counts.get(cur_running_node_id, 0)

        # 判断当前的次数是否超出最大限制
        if cur_running_node_id not in self.loop_comp:
            if origin_counts > _loop_max_num:
                raise JiuWenBaseException(
                    error_code=StatusCode.WORKFLOW_LOOP_OUT_OF_LIMIT_ERROR.code,
                    message=StatusCode.WORKFLOW_LOOP_OUT_OF_LIMIT_ERROR.errmsg,
                )

        node_execution_counts.update({cur_running_node_id: origin_counts + 1})

    async def _arun(self, inputs: dict):
        """Invoke workflow."""
        self.stop_bpmn_flag = False
        self.runtime_context.update(dict(stream_callback=self._stream_callback))
        if self._chat_manager is None:
            raise JiuWenBaseException(
                message=StatusCode.WORKFLOW_EXECUTE_ERROR.errmsg.format("Init error"),
                error_code=StatusCode.WORKFLOW_EXECUTE_ERROR.code,
            )
        self.start_time = datetime.datetime.now(tz=BJ_TZ)

        # 执行workflow
        execute_completed = await self._do_execute_with_clean_up(inputs=inputs)

        if not execute_completed:
            self.status = EXECUTE_ERROR
            self.finish_time = datetime.datetime.now(tz=BJ_TZ)
            raise WorkflowExecuteException(
                error_code=status_code.StatusCode.WORKFLOW_RUN_FAILED.code,
                message=status_code.StatusCode.WORKFLOW_RUN_FAILED.errmsg,
            )

        final_output = self.workflow.data.get("final_output", {})
        self.finish_time = datetime.datetime.now(tz=BJ_TZ)

        if self._stream_callback:
            if self.runtime_context.get("single_node_inputs") is not None:
                component = list(self.nodes.values())[-1]
                component_type = component.type
                if (component_type == NodeType.LLM.value) or (
                    component_type == NodeType.API.value
                    and component.configs.get("streaming", False)
                ):
                    response_content_list = list(
                        list(final_output["userFields"].values())
                    )[-1]
                    # 如果是异步可迭代对象
                    if isinstance(response_content_list, AsyncIterable):
                        try:
                            async for response_content in response_content_list:
                                await send_stream_data_by_stream_callback(
                                    stream_callback=self._stream_callback,
                                    item=response_content,
                                )
                        except Exception as e:
                            formatted_exception = self._process_exception(
                                exception=e, invokable=component
                            )
                            await self._pass_exception_info(
                                formatted_exception=formatted_exception,
                                invokable=component,
                            )
                            await self._handle_task_exception(formatted_exception, [])

                else:
                    await send_stream_data_by_stream_callback(
                        stream_callback=self._stream_callback,
                        item=get_streaming_single_component_stream_data(
                            self.tracer.trace_id, final_output, component_type
                        ),
                    )
                if component_type == NodeType.LLM.value:
                    finish_stream_data = StreamData(
                        code=StreamCode.FINISH.value,
                        msg=StreamDataMsg.FINISH.value,
                        data=dict(node_id=component.id, node_type=component.type),
                        execution_id=self.tracer.trace_id,
                    )
                    await self._stream_callback.on_recv(finish_stream_data)
            else:
                await send_stream_data_by_stream_callback(
                    stream_callback=self._stream_callback,
                    item=get_streaming_finish_stream_data(
                        execution_id=self.tracer.trace_id,
                        node=self._cur_node,
                        answer=final_output.get("responseContent", ""),
                        user_fields=final_output.get(USER_FIELDS, {}),
                    ),
                )
        else:
            async_output_dict = format_interaction_res(
                result=final_output.get("responseContent", ""),
                user_fields=final_output.get(USER_FIELDS, {}),
                node_type=NodeType.END.value,
                message_outputs=self.runtime_context.get(MESSAGE_RUNTIME_KEYWORD, []),
                card_outputs=self.runtime_context.get(CARD_RUNTIME_KEYWORD, []),
            )
            await self._chat_manager.put_out(async_output_dict)

        # 可以执行且执行完毕后，设置状态位标识任务执行完毕
        if self.workflow.is_completed():
            if not self._stream_callback:
                # 非流式需要额外处理结束标识
                await self._chat_manager.put_out(BPMN_COMPLETED_MESSAGE)
            self._chat_manager.set_finish(True)
            self.status = EXECUTE_SUCCESS

        return final_output

    async def _do_execute_with_clean_up(self, inputs: dict):
        running_coroutine2task = {}
        try:
            return await self._do_execute(inputs, running_coroutine2task)
        finally:
            await self.async_clean_up(running_coroutine2task)

    async def _do_execute(self, inputs: dict, running_coroutine2task: dict) -> bool:
        """
        单线程异步多并发执行
        Whether the execution is successful
        Args:
            inputs(dict): User inputs
        return:
            whether the execution ends normally
        """
        node_execution_counts = {}

        def check_task_exception(tasks_done_):
            for item in tasks_done_:
                err = item.exception()
                if err is not None:
                    raise err

        if (
            self.workflow.is_completed()
        ):  # 循环中有子工作流场景，子工作流可能需要执行多遍。
            if self.bpmn_spec is not None:  # 优先使用 bpmn_spec 重置工作流
                self._construct_bpmn_from_spec()
            else:
                self._json_to_workflow(self.workflow_json)

        while not self.workflow.is_completed() and not self.stop_bpmn_flag:
            self.workflow.refresh_waiting_tasks()

            tasks = self.workflow.get_tasks(TaskState.READY) + self.workflow.get_tasks(
                NOT_YET_COMPLETED
            )
            tasks = [
                t for t in tasks if t.state in (NOT_YET_COMPLETED, TaskState.READY)
            ]
            logger.debug("tasks refreshed to run: %s", tasks)
            logger.debug("tasks running: %s", running_coroutine2task.keys())

            available_slots = MAX_PARALLEL_COMPONENT_NUM - len(running_coroutine2task)
            for task in tasks:
                if available_slots <= 0:
                    break
                available_slots -= 1
                task_label = f"{task.task_spec.bpmn_id}@@{str(uuid.uuid4())}"
                if task.state == TaskState.READY:
                    task.state = TaskState.STARTED

                future = asyncio.create_task(
                    self._run_task(
                        task,
                        inputs,
                        node_execution_counts,
                        running_coroutine2task,
                        task_label,
                    )
                )
                running_coroutine2task[task_label] = future

            if running_coroutine2task:
                done, pending = await asyncio.wait(
                    running_coroutine2task.values(), return_when=asyncio.FIRST_COMPLETED
                )
                for task in done:
                    exc = task.exception()
                    if exc is not None:
                        await self._handle_task_exception(exc, pending)
                        return False
            else:
                logger.error("Terminate workflow due to no running task")
                if self._stream_callback:
                    await self._stream_callback.on_recv(
                        StreamData(
                            code=StreamCode.WORKFLOW_EXCEPTION.value,
                            msg=StreamDataMsg.FAIL.value,
                            data=dict(
                                error_code=status_code.StatusCode.WORKFLOW_EXECUTE_ERROR.code,
                                message=status_code.StatusCode.WORKFLOW_EXECUTE_ERROR.errmsg.format(
                                    "may be due to circular dependency."
                                ),
                            ),
                            execution_id=self.tracer.trace_id,
                        )
                    )
                    await self._stream_callback.on_recv(
                        StreamData(
                            code=StreamCode.FINISH.value,
                            msg=StreamDataMsg.FINISH.value,
                            data=dict(),
                            execution_id=self.tracer.trace_id,
                        )
                    )
                return False

        if self.stop_bpmn_flag:
            done, _ = await asyncio.wait(
                running_coroutine2task.values(), return_when=asyncio.ALL_COMPLETED
            )
            check_task_exception(done)
            await self._consume_generator()

        return True

    async def _handle_task_exception(self, exc, pending):
        for rem_task in self.workflow.get_tasks(TaskState.NOT_FINISHED_MASK):
            rem_task.state = TaskState.COMPLETED
        for p in pending:
            p.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        if self._stream_callback:
            await self._stream_callback.on_recv(
                StreamData(
                    code=StreamCode.FINISH.value,
                    msg=StreamDataMsg.FINISH.value,
                    data=dict(
                        node_id=exc.node_id
                        if hasattr(exc, "node_id") and exc.node_id is not None
                        else "",
                        node_name=exc.node_name
                        if hasattr(exc, "node_name") and exc.node_name is not None
                        else "",
                        node_type=exc.node_type
                        if hasattr(exc, "node_type") and exc.node_type is not None
                        else "",
                    ),
                    execution_id=self.tracer.trace_id,
                )
            )
        self._chat_manager.set_finish(True)
        raise exc

    async def _consume_generator(self):
        # 将生成器执行完毕（主要是LLM组件的输出）
        for generator_path in self.generator_data_path:
            generator = get_value_from_nested_structure_by_path_list(
                nested_structure=self.workflow.data, path=generator_path
            )
            if isinstance(generator, Generator):
                gen_str = get_final_result_of_flow_generator(generator)
            elif isinstance(generator, AsyncGenerator):
                gen_str = await get_final_result_of_flow_async_generator(generator)
            else:
                gen_str = generator
            set_value_to_nested_structure_by_path(
                nested_structure=self.workflow.data,
                path=generator_path,
                new_value=gen_str,
            )

    async def _run_task(
        self,
        task,
        inputs: dict,
        node_execution_counts: dict,
        running_coroutine2task: dict,
        task_label: str,
    ):
        """执行一次 task"""
        logger.debug("node_execution_counts: %s", node_execution_counts)
        invokable: Node = self.nodes.get(task.task_spec.bpmn_id, None)
        logger.debug(
            "Task: %s (type: %s) starts.",
            task.task_spec.bpmn_id,
            invokable.type if invokable else None,
        )

        is_invokable_interrupted = False
        if invokable:
            # 提取初始化逻辑到辅助方法
            self._initialize_invokable_if_needed(invokable)

            # 获取span实例
            cur_span_instance = self._get_span_instance(invokable)
            self._cur_node = invokable

            try:
                start_time = time.perf_counter()
                # 在真正执行前，先判断一下该次执行有没有被取消
                cancel_flag = os.environ.get(
                    f"{self._runtime_debug_info.get(EXECUTION_ID)}_canceled"
                )
                if cancel_flag and str(cancel_flag).lower() == "true":
                    self._stop_execution()

                # 执行前输入前处理，主要是对于生成器对象的封装，确保生成器完成遍历后可以正确的被采集数据
                invokable_input = await self._pre_process(
                    invokable, inputs, cur_span_instance
                )

                # 检查节点循环执行的次数是否已经超出限制，超出会抛出JiuWenBaseException
                self._check_the_number_of_cycles(
                    invokable, node_execution_counts, self._loop_max_num
                )

                # 提取组件执行逻辑到辅助方法
                invokable_output = await self._execute_invokable(
                    invokable, invokable_input, cur_span_instance, task_label
                )

                # 对于生成器结果，因为无法立即获取到完整结果，所以对于post_process以及_post_execution_debug_info
                # 需要做额外处理，确保迭代完成后的最终结果被正确的处理以及采集。
                await self._post_process(
                    invokable_output=invokable_output,
                    invokable_input=invokable_input,
                    invokable=invokable,
                    span=cur_span_instance,
                )

                # 提取数据处理逻辑到辅助方法
                self._process_task_data(task, invokable)
                duration = round((time.perf_counter() - start_time) * 1000)
                performance_logger.info(
                    f"_execute_invokable<node={invokable.type}_{invokable.name}>|{duration}"
                )
                wf_performance_buffer.info("workflow_execution_components", duration)

                # 检查交互中断状态
                is_invokable_interrupted = await self._check_interactive_interruption(
                    invokable
                )

            except WorkflowAbortException as e:
                await self._pass_abort_exception_info(abort_exception=e)
                await self._handle_execution_error(invokable, e, cur_span_instance)

            except InterruptException as e:
                is_invokable_interrupted = True
                self.stop_bpmn_flag = True
                self._chat_manager.set_new_chat(False)
                await self._pass_exception_info(
                    formatted_exception=e, invokable=invokable
                )
            except Exception as e:
                await self._handle_execution_error(invokable, e, cur_span_instance)
                return

        if not is_invokable_interrupted:
            task.run()
            running_coroutine2task.pop(task_label)
            logger.debug(
                "Task: %s (type: %s) done.",
                task.task_spec.bpmn_id,
                invokable.type if invokable else None,
            )
        else:
            task.state = NOT_YET_COMPLETED
            logger.debug(
                "Task: %s (type: %s) need feedback.",
                task.task_spec.bpmn_id,
                invokable.type,
            )

    async def _pass_abort_exception_info(self, abort_exception: WorkflowAbortException):
        """
        处理abort_exception，发送流式数据
        """
        # 判断_from_subworkflow是否为TRUE，是True就跳过__abort__
        if (
            not getattr(abort_exception, "_from_subworkflow", False)
            and self.workflow.data.get("__abort__") is None
        ):
            self.workflow.data["__abort__"] = abort_exception.to_payload()
            error_stream_data = StreamData(
                code=StreamCode.WORKFLOW_EXCEPTION.value,
                msg=StreamDataMsg.FAIL.value,
                data=abort_exception.to_payload(),
                execution_id=self.tracer.trace_id,
            )
            error_stream_data.data["jiuwen_exception_node_id"] = (
                abort_exception.node_id if abort_exception.node_id is not None else ""
            )
            await self._stream_callback.on_recv(error_stream_data)

    def _initialize_invokable_if_needed(self, invokable):
        """初始化可调用节点（如果需要）"""
        if (
            invokable.type in component_class_pool.custom_component_hci
            or invokable.type
            in [
                NodeType.LLM.value,
                NodeType.QUESTIONER.value,
                NodeType.LOOP.value,
                NodeType.INPUT.value,
                NodeType.AGENT.value,
                NodeType.EXTRACTOR.value,
            ]
        ):
            invokable.init(
                invokable.configs, self.runtime_context, invokable.action.metadata
            )

    def _get_span_instance(self, invokable):
        """获取节点的span实例"""
        if (
            invokable.type == NodeType.LOOP.value
            and self.tracer.loop_span_dict.get(invokable.id, None) is not None
        ):
            return self.tracer.loop_span_dict.get(invokable.id, None)
        return self.tracer.start_span(
            span_id=self._runtime_debug_info.pop(INVOKE_ID, "")
        )

    def _format_inner_exception(self, e) -> InnerException:
        """format inner exception"""
        if isinstance(e, JiuWenBaseException):
            error_body = ErrorBody(error_message=e.message, error_code=e.error_code)
        else:
            error_body = ErrorBody(
                error_message=repr(e), error_code=StatusCode.ERROR.code
            )
        return InnerException(is_success=False, error_body=error_body)

    async def _do_invoke_retry(
        self, invokable, invokable_input, cur_span_instance, timeout, retry_time
    ):
        timeout = rewrite_timeout(self.runtime_context, invokable, timeout)
        """异常处理机制，超时重试"""
        last_exception = None
        for _ in range(0, retry_time + 1):
            last_exception = None
            invokable_input_new = copy.deepcopy(invokable_input)
            try:
                return await asyncio.wait_for(
                    self._do_invoke(
                        invokable=invokable,
                        invokable_input=invokable_input_new,
                        cur_span_instance=cur_span_instance,
                    ),
                    timeout=timeout,
                )
            except Exception as e:
                logger.info(
                    f"{invokable.type}_{invokable.id} invoke exception, reset and retry"
                )
                # 重试时，需要发送带有innerError异常的调测信息
                if retry_time > 0 and _ < retry_time:
                    await CallbackHandlerManager().trigger_event(
                        event_name=TriggerEventName.ON_INVOKE.value,
                        data={},
                        exception=self._format_inner_exception(e),
                        component_metadata=self._get_callback_data(invokable),
                        span_instance=cur_span_instance,
                        runtime_context=self.runtime_context,
                    )
                invokable.reset()
                last_exception = e
        if last_exception:
            raise last_exception

    async def _do_invoke_with_exception_handle(
        self, invokable, invokable_input, cur_span_instance
    ):
        try:
            # 不支持重试
            if (
                self._is_inputs_contains_generator(invokable_input)
                or invokable.type == NodeType.SUB_WORKFLOW.value
            ):
                if invokable.exception_config.retry_times > 0:
                    logger.warning(f"{invokable.type}_{invokable.id} not support retry")
                invokable_output = await asyncio.wait_for(
                    self._do_invoke(
                        invokable=invokable,
                        invokable_input=invokable_input,
                        cur_span_instance=cur_span_instance,
                    ),
                    timeout=invokable.exception_config.timeout,
                )
            else:
                invokable_output = await self._do_invoke_retry(
                    invokable,
                    invokable_input,
                    cur_span_instance,
                    invokable.exception_config.timeout,
                    invokable.exception_config.retry_times,
                )
            if invokable.exception_config.is_config:
                invokable_output.update(InnerException(is_success=True).to_alias_dict())
            if self._is_support_error_branch(invokable):
                invokable_output[EXCEPTION_OUTPUT_RESULT] = (
                    EXCEPTION_OUTPUT_RESULT_SUCCESS
                )
        except Exception as e:
            # 只中断
            if self._is_only_support_interrupt(invokable):
                if invokable.exception_config.handle_type != EXCEPTION_HANDLE_INTERRUPT:
                    logger.warning(
                        f"{invokable.type}_{invokable.id} only support interrupt"
                    )
                raise e

            invokable_output = copy.deepcopy(invokable.outputs)
            # 异常处理逻辑
            if (
                invokable.exception_config.handle_type
                == EXCEPTION_HANDLE_DEFAULT_OUTPUTS
            ):
                invokable_output = self._merge_dicts(
                    invokable_output, invokable.exception_config.default_outputs
                )
                self._template_replace(invokable_output, self.workflow.data)
                invokable_output.update(self._format_inner_exception(e).to_alias_dict())
                # 修改节点状态为end，表示正常结束，流程可以继续
                if (
                    invokable.type in component_class_pool.custom_component_hci
                    or invokable.type in INTERACT_COMPONENT_TYPES
                ):
                    invokable.error_to_output()
            elif self._is_support_error_branch(invokable):
                invokable_output = {}
                invokable_output[EXCEPTION_OUTPUT_RESULT] = (
                    EXCEPTION_OUTPUT_RESULT_FAILED
                )
                invokable_output[CLASSIFICATION_ID] = INVALID_CLASSIFICATION_ID
                invokable_output.update(self._format_inner_exception(e).to_alias_dict())
                # 修改节点状态为end，表示正常结束，流程可以继续
                if (
                    invokable.type in component_class_pool.custom_component_hci
                    or invokable.type in INTERACT_COMPONENT_TYPES
                ):
                    invokable.error_to_output()
            else:
                raise e

        return invokable_output

    async def _execute_invokable(
        self, invokable, invokable_input, cur_span_instance, task_label
    ):
        """执行组件并获取结果"""
        if invokable.type in NOT_SUPPORT_EXCEPTION_COMPONENT_TYPES:
            if invokable.exception_config.is_config:
                logger.warning(
                    f"{invokable.type}_{invokable.id} not support exception handle"
                )
            return await self._do_invoke(
                invokable=invokable,
                invokable_input=invokable_input,
                cur_span_instance=cur_span_instance,
            )
        return await self._do_invoke_with_exception_handle(
            invokable=invokable,
            invokable_input=invokable_input,
            cur_span_instance=cur_span_instance,
        )

    def _process_task_data(self, task, invokable):
        """处理任务数据流"""
        if (
            invokable.type == NodeType.LOOP.value
        ):  # Loop 条件判断，数据需要传给 task 才可用
            task.set_data(**{invokable.id: self.workflow.data.get(invokable.id, {})})

        if (
            id(task.workflow) != id(self.workflow)
            and invokable.id in self.workflow.data
        ):
            # SubProcess 内如有条件判断，只能使用 SubProcess 自己对应的 workflow.data
            task.workflow.data[invokable.id] = self.workflow.data[invokable.id]

    async def _check_interactive_interruption(self, invokable):
        """检查交互组件是否中断"""
        if (
            invokable.type in component_class_pool.custom_component_hci
            or invokable.type in INTERACT_COMPONENT_TYPES
        ):
            node_state = invokable.action.get_state()
            if (
                hasattr(node_state, "status")
                and node_state.status != ExecutionStatus.END
            ):
                # 交互中断时需要主动退出bpmn执行，不执行task.run()，并标记ChatManager为非新对话
                self.stop_bpmn_flag = True
                self._chat_manager.set_new_chat(False)
                await invokable.action.post_interact_process(
                    runtime_context=self.runtime_context,
                    component_metadata=self._get_callback_data(invokable),
                )
                return True
        return False

    async def _handle_execution_error(self, invokable, error, cur_span_instance):
        """处理执行错误"""
        self.status = EXECUTE_ERROR
        self.finish_time = datetime.datetime.now(tz=BJ_TZ)
        try:
            await self._on_execution_error_debug_info(
                invokable=invokable, error=error, cur_span=cur_span_instance
            )
        except JiuWenBaseException:
            logger.error("Failed to collect exception info when the callback occurred")
        finally:
            formatted_exception = self._process_exception(
                exception=error, invokable=invokable
            )
            await self._pass_exception_info(
                formatted_exception=formatted_exception, invokable=invokable
            )
            raise formatted_exception from error

    async def _do_invoke(
        self, invokable: Node, invokable_input, cur_span_instance: Span
    ):
        """
        组件invoke的判断逻辑，主要区分异步执行、流式执行、其他执行方式。
        """

        if (
            invokable.type in component_class_pool.custom_component_hci
            or invokable.type
            in [
                NodeType.TASK.value,
                NodeType.QUESTIONER.value,
                NodeType.SUB_WORKFLOW.value,
                NodeType.INPUT.value,
                NodeType.AGENT.value,
            ]
        ):
            # 有中间交互能力的组件，调用其异步执行方法
            invokable_output = await invokable.ainvoke(
                inputs=invokable_input,
                span=cur_span_instance,
                component_metadata=self._get_callback_data(invokable),
                runtime_context=self.runtime_context,
                stream_callback=self._stream_callback,
                runtime_auth_headers=self.runtime_context.get(WORKFLOW_API_CONFIGS),
            )
        elif invokable.type in [NodeType.LLM.value] and self._stream_callback:
            # 带有流式能力的组件，并且stream_callback不为空，表示调用流式执行
            invokable_output = await invokable.astream(
                inputs=invokable_input,
                span=cur_span_instance,
                stream_callback=self._stream_callback,
            )
        elif (
            invokable.type
            in [
                NodeType.MESSAGE.value,
                NodeType.CARD.value,
                NodeType.END.value,
                NodeType.MCP.value,
                NodeType.STREAM_TRANSFORM.value,
            ]
            and self._stream_callback
        ):
            # 在流式场景，消息节点、卡片节点与结束节点有特殊处理逻辑
            invokable_output = await invokable.ainvoke(
                inputs=invokable_input,
                stream_callback=self._stream_callback,
                span=cur_span_instance,
                ref=invokable.inputs,
            )
        elif invokable.type in [NodeType.API.value, NodeType.EXTRACTOR.value]:
            api_configs = self.runtime_context.get(WORKFLOW_API_CONFIGS)
            if invokable.configs.get("streaming", False) and self._stream_callback:
                # 插件流式调用
                invokable_output = await invokable.astream(
                    inputs=invokable_input,
                    span=cur_span_instance,
                    runtime_auth_headers=api_configs,
                )
            else:
                # 插件异步调用
                invokable_output = await invokable.ainvoke(
                    inputs=invokable_input,
                    span=cur_span_instance,
                    runtime_auth_headers=api_configs,
                )
        elif invokable.type in [
            NodeType.START.value,
            NodeType.CODE.value,
            NodeType.INTENT_DETECTION.value,
        ]:
            invokable_output = await invokable.ainvoke(
                inputs=invokable_input,
                runtime_auth_headers=self.runtime_context.get(WORKFLOW_API_CONFIGS),
                runtime_context=self.runtime_context,
                span=cur_span_instance,
            )
        elif invokable.type in [NodeType.SET_VARIABLE.value]:
            invokable_output = await invokable.ainvoke(
                inputs=invokable_input,
                runtime_auth_headers=self.runtime_context.get(WORKFLOW_API_CONFIGS),
                span=cur_span_instance,
            )
        else:
            invokable_output = await invokable.ainvoke(
                inputs=invokable_input,
                runtime_auth_headers=self.runtime_context.get(WORKFLOW_API_CONFIGS),
                span=cur_span_instance,
            )
            if invokable.type == NodeType.LOOP.value:
                invokable.state = invokable.action.metadata.node_state
                self.tracer.loop_span_dict[invokable.id] = cur_span_instance
        return invokable_output

    async def _gen_stream_output_with_specific_event(
        self, event_code: StreamCode, data: Optional[dict] = None
    ):
        """
        根据事件码，生成不带数据的流式数据。
        :param event_code: 区分流式数据的事件码
        :return None
        """
        if not self._stream_callback:
            return
        if data is None:
            data = {}
        start_stream_data = StreamData(
            code=event_code.value,
            msg=StreamDataMsg.SUCCESS.value,
            data=data,
            execution_id=self.tracer.trace_id,
        )
        await self._stream_callback.on_recv(start_stream_data)

    async def _pre_process(self, invokable: Node, inputs: dict, span: Span):
        """
        预处理输入，主要包括输入变量赋值、调试信息采集。
        返回处理后的输入。
        """
        if (
            invokable.type in component_class_pool.custom_component_hci
            or invokable.type
            in [
                NodeType.LOOP.value,
                NodeType.QUESTIONER.value,
                NodeType.INPUT.value,
                NodeType.AGENT.value,
            ]
        ) and invokable.get_node_status() not in [
            ExecutionStatus.START,
            ExecutionStatus.LOOP_RECOVER,
        ]:
            return {}

        if self.runtime_context.get("single_node_inputs") is not None:
            if invokable.type == "jiuwen.intentDetection":
                param_field = ""
            elif invokable.type == "jiuwen.workflowComposite":
                param_field = "systemFields"
            else:
                param_field = "userFields"
            inputs = self._pre_process_single_component_inputs(invokable, param_field)

            await self._pre_execution_debug_info(
                invokable=invokable, inputs=inputs, cur_span=span
            )
            return force_convert_component_by_schema_raise_exception(
                inputs=inputs,
                node_configs=invokable.configs,
                node_info=WorkflowMetadata(
                    node_id=invokable.id,
                    node_type=invokable.type,
                    node_name=invokable.name,
                ),
                structure_pos=STRUCTURE_POSITION_INPUTS,
            )
        # 开始组件的输入就是workflow的输入
        if invokable.type == NodeType.START.value:
            # 开始组件中的引用需要转化为真实值
            invokable_input = self._pre_process_inputs(invokable).get(USER_FIELDS, {})
            invokable_input.update(inputs)
            await self._gen_stream_output_with_specific_event(
                event_code=StreamCode.WORKFLOW_START, data={"workflow_id": self.id}
            )
        else:
            # 对输入进行前处理，完成输入引用变量替换为真实值
            invokable_input = self._pre_process_inputs(invokable)

        if invokable.type not in [
            NodeType.END.value,
            NodeType.MESSAGE.value,
            NodeType.CARD.value,
        ]:
            # 对于可能存在的迭代器结果，结束与消息的迭代器输入需要特殊处理，其余组件可以统一先进行处理
            invokable_input = await pre_process_inputs(invokable_input)

        if invokable.type == NodeType.SUB_WORKFLOW.value:
            # 将设置记忆变量在打印debug信息之前，方便打印记忆变量数据
            self._set_mem_map(invokable, invokable_input)

        await self._pre_execution_debug_info(
            invokable=invokable,
            inputs=dict_with_generators_replaced(invokable_input),
            cur_span=span,
        )
        if invokable.type == NodeType.END.value:
            self.set_end_invoke_output(invokable, invokable_input)

        return invokable_input

    def _set_mem_map(self, invokable: Node, inputs: dict):
        """
        设置记忆变量及映射关系
        """
        workflow_id = self.id
        reference_id = invokable.configs["reference"]["id"]

        memory_variables = self.runtime_context.get(MEMORY_VARIABLES, {})
        mem_map = self.runtime_context.get(MEM_MAP, {})

        if invokable.inputs and "memory" in invokable.inputs:
            for target_key, source_path in invokable.inputs["memory"].items():
                # 解析 ${node_start.memory.test_mem} 这样的路径
                if source_path.startswith("${") and source_path.endswith("}"):
                    source_expr = source_path[2:-1]  # 去掉 ${ 和 }
                    source_key = f"{workflow_id}.{source_expr}"
                    target_mapped_key = f"{reference_id}.memory.{target_key}"
                    mem_map[target_mapped_key] = (
                        source_key  # 父子映射关系对调位置，应对多工作流
                    )
                    value = inputs.get("memory", {}).get(target_key, "")
                    memory_variables[source_key] = value

    async def _process_generator(
        self,
        generator: Generator,
        origin_input: dict,
        cur_invokable: Node,
        cur_span: Span,
        origin_key: str,
        **kwargs,
    ):
        ref_str = get_ref_str(kwargs.get("ref_str"))
        # 迭代完生成器后，再调用前置数据采集逻辑
        for stream_item in generator:
            if stream_item.code in [StreamCode.FINISH.value, StreamCode.ERROR.value]:
                origin_input[origin_key] = get_value_from_nested_structure_by_path_list(
                    nested_structure=self.workflow.data, path=ref_str
                )
            # 输入数据中的数据类型均不是生成器时，表示迭代已经完成，可以进行数据采集动作
            if (
                not self._judge_values_contains_type_of_generator(origin_input)
                and cur_invokable.action
            ):
                await self._pre_execution_debug_info(
                    invokable=cur_invokable, inputs=origin_input, cur_span=cur_span
                )
            yield stream_item

    def _pre_process_single_component_inputs(
        self, invokable_node: Node, params_field: str
    ):
        """Preprocess before single component invoke"""
        if not params_field:
            return self.runtime_context.get("single_node_inputs")
        # 获取invokable中的inputs
        invokable_inputs = invokable_node.inputs.get(params_field, {})
        # 获取用户输入中的inputs
        request_inputs = self.runtime_context.get("single_node_inputs")
        # 用于存储处理后的inputs
        processed_inputs = {}

        for item in invokable_node.configs.get(params_field, {}).get("inputs", []):
            key = item["id"]
            source_type = item.get("sourceType", "")
            if key in request_inputs:
                processed_inputs[key] = request_inputs[key]
            else:
                if source_type == "input":
                    # 如果sourceType为input且request的inputs中不存在该key，取默认值
                    processed_inputs[key] = invokable_inputs[key]
                else:
                    raise JiuWenBaseException(
                        error_code=StatusCode.COMPONENT_STEP_DEBUG_ERROR.code,
                        message=StatusCode.COMPONENT_STEP_DEBUG_ERROR.errmsg.format(
                            reason=f"Input key '{key}' with sourceType 'ref' is missing in the request inputs."
                        ),
                    )

        return {params_field: processed_inputs}

    def _missing_invokable(self, node: Node, is_input: bool) -> bool:
        """判定节点或 输入/输出 是否缺失。"""
        if not node:
            return True
        if is_input and not node.inputs:
            return True
        if not is_input and not node.outputs:
            return True
        return False

    def _filter_ref_inputs(self, invoke_node: Node, node_inputs):
        user_inputs = node_inputs.get(USER_FIELDS, {})
        result = {}
        for key, value in user_inputs.items():
            if invoke_node.is_ref_input(key):
                result[key] = value
        node_inputs[USER_FIELDS] = result

    def _handle_streaming_api_reference(self, match_str, data_source, parent, key):
        """处理流式API节点的引用"""
        node_id = split_string(match_str)[0]
        node = self.nodes.get(node_id)

        is_data_source_valid = data_source == self.workflow.data
        is_streaming_api_node = (
            node
            and node.type == NodeType.API.value
            and node.configs.get("streaming") is True
        )

        if is_data_source_valid and is_streaming_api_node:
            if validate_ref_recursive(split_string(match_str), node.outputs):
                parent[key] = self._generator(split_string(match_str), data_source)
            else:
                parent[key] = None
            return True
        return False

    def _dereference_inputs_variables(self, invokable_node: Node, is_input: bool):
        """dereference inputs variables like ${path.to.value} to the real value referenced"""
        cur_invokable_node_inputs = (
            copy.deepcopy(invokable_node.inputs if is_input else invokable_node.outputs)
            or {}
        )

        if invokable_node.type == NodeType.START.value and is_input:
            self._filter_ref_inputs(invokable_node, cur_invokable_node_inputs)

        stack = [
            (cur_invokable_node_inputs, None, None)
        ]  # (current, parent, key/index)
        while stack:
            current, parent, key = stack.pop()

            if isinstance(current, dict):
                for k, v in current.items():
                    stack.append((v, current, k))
            elif isinstance(current, list):
                for i, item in enumerate(current):
                    stack.append((item, current, i))
            elif isinstance(current, str):
                if invokable_node.type == NodeType.BRANCH.value:
                    current = key
                match_str = get_ref_str(current)
                if match_str:
                    if match_str.startswith(ENV_PREFIX):
                        data_source = self.runtime_context.get(ENVIRONMENT_VARIABLES)
                        match_str = match_str[len(ENV_PREFIX) :]
                    elif match_str.startswith(REQUEST_PREFIX):
                        data_source = self.runtime_context.get(REQUEST_VARIABLES)
                        match_str = match_str[len(REQUEST_PREFIX) :]
                    else:
                        data_source = self.workflow.data
                    # 获取真实的值
                    if self._handle_streaming_api_reference(
                        match_str, data_source, parent, key
                    ):
                        continue
                    new_value = get_value_from_nested_structure_by_path_list(
                        nested_structure=data_source, path=match_str
                    )
                    if isinstance(new_value, Generator) and is_model_output_json(
                        self.nodes.get(match_str.split(BPMN_VARIABLE_POOL_SEPARATOR)[0])
                    ):
                        get_final_result_of_flow_generator(new_value)
                        parent[key] = get_value_from_nested_structure_by_path_list(
                            nested_structure=data_source, path=match_str
                        )
                    if isinstance(new_value, AsyncGenerator) and is_model_output_json(
                        self.nodes.get(match_str.split(BPMN_VARIABLE_POOL_SEPARATOR)[0])
                    ):
                        get_final_result_of_flow_async_generator(new_value)
                        parent[key] = get_value_from_nested_structure_by_path_list(
                            nested_structure=data_source, path=match_str
                        )
                    else:
                        parent[key] = new_value
                    if invokable_node.type == NodeType.LOOP.value:
                        parent[key] = copy.deepcopy(new_value)
                else:
                    parent[key] = current

        return cur_invokable_node_inputs

    def _pre_process_inputs(self, invokable_node: Node, is_input: bool = True):
        """Preprocess before invoke."""
        # 初始化变量
        # 判断：节点不存在，或输入缺失，或输出缺失
        if self._missing_invokable(invokable_node, is_input):
            return {}

        cur_invokable_node_inputs = self._dereference_inputs_variables(
            invokable_node, is_input
        )

        # 对于插件组件，去除输入中类型为直接输入且为空值的输出
        if invokable_node.type == NodeType.API.value:
            self._filter_empty_user_fields_entries(cur_invokable_node_inputs)

        # 强转 cur_invokable_node_inputs 使其符合其类型定义
        if invokable_node.type in [NodeType.START.value, NodeType.EXTRACTOR.value]:
            return cur_invokable_node_inputs
        return force_convert_component_by_schema_raise_exception(
            inputs=cur_invokable_node_inputs,
            node_configs=invokable_node.configs,
            node_info=WorkflowMetadata(
                node_id=invokable_node.id,
                node_type=invokable_node.type,
                node_name=invokable_node.name,
            ),
            structure_pos=STRUCTURE_POSITION_INPUTS
            if is_input
            else STRUCTURE_POSITION_OUTPUTS,
        )

    async def _pre_execution_debug_info(
        self, invokable: Node, inputs: dict, cur_span: Span
    ):
        logger.debug(
            "The node starts to execute. "
            "| flow_id: %s | node type: %s | node name: %s",
            self._runtime_debug_info.get(WORKFLOW_ID, ""),
            invokable.type,
            invokable.name,
        )
        if invokable.action:
            try:
                await invokable.action.pre_process(
                    node_input=inputs,
                    runtime_context=self.runtime_context,
                    component_metadata=self._get_callback_data(invokable),
                    span_instance=cur_span,
                )
                if invokable.type == NodeType.LLM.value:
                    # 模型组件会有一个开始，两个结束：
                    # 第一个结束是空的，只是为了保证链路完整；第二个结束是真实值，迭代器里消费到FINISH事件触发
                    await self._post_execution_debug_info(
                        invokable=invokable, outputs="", cur_span=cur_span
                    )
            except Exception as e:
                if isinstance(e, JiuWenBaseException):
                    raise
                raise JiuWenBaseException(
                    error_code=StatusCode.WORKFLOW_COLLECT_PRE_CALLBACK_INFO_ERROR.code,
                    message=StatusCode.WORKFLOW_COLLECT_PRE_CALLBACK_INFO_ERROR.errmsg,
                ) from e

    def _update_loop_node(self, invokable: Node, processed_outputs):
        # 更新循环节点组件里的值
        if invokable.id in self.loop_comp:
            id_loop = invokable.id + "_loop"
            if id_loop not in self.workflow.data:
                self.workflow.data[id_loop] = [processed_outputs]
            else:
                self.workflow.data[id_loop].append(processed_outputs)

    # 循环体里的generator需要提前解析
    async def _get_generator_in_loop(self, processed_outputs):
        res = {"userFields": {}}
        for key, value in processed_outputs["userFields"].items():
            if isinstance(value, Generator):
                processed_value = get_final_result_of_flow_generator(value)
                res["userFields"].update({key: processed_value})
            elif isinstance(value, AsyncGenerator):
                processed_value = await get_final_result_of_flow_async_generator(value)
                res["userFields"].update({key: processed_value})
            else:
                res["userFields"].update({key: value})

        return res

    async def _post_process(
        self, invokable_output, invokable_input, invokable: Node, span: Span
    ):
        """
        处理执行后的原始输出：
        对于生成器结果，需要对其增加一层封装，确保遍历完成后正确进行数据采集与变量池数据更新。
        对于非生成器结果，直接进行数据采集与变量池结果更新。
        """
        if invokable.type == NodeType.LOOP.value:
            for loop_comp_id in invokable.configs.get("loopBody", []):
                self.loop_comp.update({loop_comp_id: invokable.id})
        processed_outputs, has_generator = await self._recursive_process_output(
            invokable_output, invokable, span, path=invokable.id
        )
        if invokable.id in self.loop_comp and has_generator:
            processed_outputs = await self._get_generator_in_loop(processed_outputs)

        if (
            invokable.type in component_class_pool.custom_component_hci
            or invokable.type
            in [
                NodeType.QUESTIONER.value,
                NodeType.INPUT.value,
                NodeType.SUB_WORKFLOW.value,
                NodeType.AGENT.value,
            ]
        ):
            # 交互组件只有结束状态才获取值
            if invokable.action.node_state.status == ExecutionStatus.END:
                self.workflow.data[invokable.id] = processed_outputs
                self.workflow.data["final_output"] = processed_outputs
                self._update_loop_node(invokable, processed_outputs)
        else:
            self.workflow.data[invokable.id] = processed_outputs
            self.workflow.data["final_output"] = processed_outputs
            self._update_loop_node(invokable, processed_outputs)

        if (
            invokable.type in component_class_pool.custom_component_hci
            or invokable.type
            in [
                NodeType.LOOP.value,
                NodeType.QUESTIONER.value,
                NodeType.INPUT.value,
                NodeType.AGENT.value,
            ]
        ) and invokable.get_node_status() != ExecutionStatus.END:
            return
        self._post_process_outputs(
            action_result=invokable_output, invokable_node=invokable
        )
        if not has_generator:
            await self._post_execution_debug_info(
                invokable=invokable,
                outputs=invokable_output,
                inputs=dict_with_generators_replaced(invokable_input),
                cur_span=span,
            )

        if invokable.type == NodeType.SUB_WORKFLOW.value:
            self._parse_mem_map(invokable.configs.get("reference", {}).get("id"))

    def _parse_mem_map(self, sub_workflow_id: str):
        """
        根据mem_map和memory_variables，将子工作流的修改结果回溯到父工作流
        """
        mem_map = self.runtime_context.get(MEM_MAP, {})
        memory_variables = self.runtime_context.get(MEMORY_VARIABLES, {})
        keys_to_delete = []
        source_keys_to_check = set()  # 多工作流引用同一个数据，避免提前删除

        for target_key, source_key in mem_map.items():
            # 如果目标键在memory_variables中有值（被子工作流修改过）
            if (
                target_key.split(".")[0] == sub_workflow_id
                and target_key in memory_variables
            ):
                target_value = memory_variables[target_key]

                # 将值设置回源键
                memory_variables[source_key] = target_value
                parts = source_key.split(".")
                if parts[0] == self.id:
                    current = self.workflow.data
                    for part in parts[1:-1]:
                        current = current[part]
                    current[parts[-1]] = target_value
                keys_to_delete.append(target_key)
                source_keys_to_check.add(source_key)

        for key in keys_to_delete:
            if key in memory_variables:
                del memory_variables[key]
            if key in mem_map:
                del mem_map[key]

        for source_key in source_keys_to_check:
            # 检查mem_map中是否还有映射到这个source_key的键值对
            has_other_mapping = any(source == source_key for source in mem_map.values())
            if not has_other_mapping and source_key in memory_variables:
                del memory_variables[source_key]

    async def _recursive_process_output(
        self, invokable_output, invokable: Node, span: Span, path=""
    ):
        """递归处理原始输出，如果有迭代器类型输出，进行封装"""
        has_generator = False
        if isinstance(invokable_output, dict):
            for k, v in invokable_output.items():
                # 更新路径
                current_path = ".".join([path, k])
                invokable_output[k], flag = await self._recursive_process_output(
                    v, invokable, span, current_path
                )
                has_generator = True if flag else has_generator
            return invokable_output, has_generator
        if isinstance(invokable_output, Generator):
            # 将生成器类型数据的路径记录下来
            self.generator_data_path.append(path)
            return self._post_process_output_of_generator(
                invokable_output, invokable, span
            ), True
        if isinstance(invokable_output, AsyncGenerator):
            # 将生成器类型数据的路径记录下来
            self.generator_data_path.append(path)
            return self._post_process_output_of_async_generator(
                invokable_output, invokable, span
            ), True
        return invokable_output, False

    def _post_process_outputs(self, action_result, invokable_node: Node):
        """Postprocess after invoke."""
        if action_result is None:
            return
        if invokable_node.outputs is None:
            return
        # 检查 action_result 是否能被解析为 JSON 格式
        action_json_result = self._try_parse_json(action_result)

        # 校验 action_result 是否符合其类型定义
        force_convert_component_by_schema_raise_exception(
            inputs=action_json_result,
            node_configs=invokable_node.configs,
            node_info=WorkflowMetadata(
                node_id=invokable_node.id,
                node_type=invokable_node.type,
                node_name=invokable_node.name,
            ),
            structure_pos=STRUCTURE_POSITION_OUTPUTS,
        )

    async def _process_streaming_error(self, error, invokable, span):
        if isinstance(error, JiuWenBaseException):
            # 此处主要为了捕获未以item.code=-1的形式表达的异常，已经处理过的异常直接抛出
            await self._on_execution_error_debug_info(
                invokable=invokable, error=error, cur_span=span
            )
            raise error
        err = JiuWenBaseException(
            error_code=StatusCode.WORKFLOW_LLM_STREAMING_OUTPUT_ERROR.code,
            message=StatusCode.WORKFLOW_LLM_STREAMING_OUTPUT_ERROR.errmsg.format(
                msg=f"Unknown error, Please check the log. Details: {format_exception_reason(error)}"
            ),
        )
        await self._on_execution_error_debug_info(
            invokable=invokable, error=err, cur_span=span
        )
        raise err from error

    async def _post_process_output_of_generator(
        self, origin_output: Generator, invokable: Node, span: Span
    ) -> Generator:
        """
        后处理时，若结果为迭代器，表示无法实时获取到节点的完整输出。
        通过对生成器进行一层额外封装，使迭代完成后的最终结果可以被正确处理与采集。
        :param origin_output: 原始迭代器输出。
        :param invokable: 节点实例。
        :param span: trace实例。
        :return: 封装处理后的迭代器。
        """
        try:
            for item in origin_output:
                await self._post_process_single_output(item, invokable, span)
                yield item
        except Exception as e:
            await self._process_streaming_error(e, invokable, span)

    async def _post_process_single_output(self, item, invokable, span):
        if item.code == StreamCode.FINISH.value:
            if (
                invokable.id in self.workflow.data
                and invokable.id not in self.loop_comp
            ):
                self.workflow.data[invokable.id].update(
                    self._try_parse_json(item.data.get(_ANSWER))
                )
            else:
                self.workflow.data[invokable.id] = self._try_parse_json(
                    item.data.get(_ANSWER)
                )
            await self._post_execution_debug_info(
                invokable=invokable,
                outputs=item.data.get(_ANSWER),
                cur_span=span,
            )
        if item.code == StreamCode.ERROR.value:
            err = JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_LLM_STREAMING_OUTPUT_ERROR.code,
                message=StatusCode.WORKFLOW_LLM_STREAMING_OUTPUT_ERROR.errmsg.format(
                    msg=item.data.get(_ANSWER, "")
                ),
            )
            # 此处调用采集是为了确保采集报错信息时，当前的节点时模型节点，而不是引用模型的节点
            await self._on_execution_error_debug_info(
                invokable=invokable, error=err, cur_span=span
            )
            raise err

    async def _post_process_output_of_async_generator(
        self, origin_output: AsyncGenerator, invokable: Node, span: Span
    ) -> AsyncGenerator:
        """
        后处理时，若结果为迭代器，表示无法实时获取到节点的完整输出。
        通过对生成器进行一层额外封装，使迭代完成后的最终结果可以被正确处理与采集。
        :param origin_output: 原始迭代器输出。
        :param invokable: 节点实例。
        :param span: trace实例。
        :return: 封装处理后的迭代器。
        """
        try:
            async for item in origin_output:
                await self._post_process_single_output(item, invokable, span)
                yield item
        except Exception as e:
            await self._process_streaming_error(e, invokable, span)

    async def _post_execution_debug_info(
        self,
        invokable: Node,
        outputs: Union[dict, str],
        cur_span: Span,
        inputs: Union[dict, str] = None,
    ):
        logger.debug(
            "Node execution is complete. "
            "| flow_id: %s | node type: %s | node name: %s",
            self._runtime_debug_info.get(WORKFLOW_ID, ""),
            invokable.type,
            invokable.name,
        )
        if invokable.action:
            try:
                await invokable.action.post_process(
                    node_output=outputs,
                    node_input=inputs,
                    runtime_context=self.runtime_context,
                    component_metadata=self._get_callback_data(invokable),
                    span_instance=cur_span,
                )
            except Exception as e:
                if isinstance(e, JiuWenBaseException):
                    raise
                raise JiuWenBaseException(
                    error_code=StatusCode.WORKFLOW_COLLECT_POST_CALLBACK_INFO_ERROR.code,
                    message=StatusCode.WORKFLOW_COLLECT_POST_CALLBACK_INFO_ERROR.errmsg,
                ) from e

    async def _pass_exception_info(
        self, formatted_exception: JiuWenBaseException, invokable: Node
    ):
        """
        如果是流式调用：
        需将报错信息封装为一个流式信息返回。
        如果是非流式调用：
        直接通过异步消息队列传递信息即可。
        :param formatted_exception: JiuWenBaseException: 格式化后的异常信息
        :param invokable: Node: 报错的节点
        :return: None
        """
        if self._stream_callback:
            if isinstance(formatted_exception, InterruptException):
                interrupt_stream_data = StreamData(
                    code=StreamCode.MESSAGE_END.value,
                    msg=StreamDataMsg.FAIL.value,
                    data=dict(
                        code=formatted_exception.error_code,
                        message=formatted_exception.message,
                        node_id=invokable.id,
                        node_name=invokable.name,
                        node_type=invokable.type,
                    ),
                    execution_id=self.tracer.trace_id,
                )
                await self._stream_callback.on_recv(interrupt_stream_data)
            else:
                error_stream_data = StreamData(
                    code=StreamCode.ERROR.value,
                    msg=StreamDataMsg.FAIL.value,
                    data=dict(
                        code=formatted_exception.error_code,
                        message=formatted_exception.message,
                        node_id=formatted_exception.node_id
                        if hasattr(formatted_exception, "node_id")
                        and formatted_exception.node_id is not None
                        else invokable.id,
                        node_name=formatted_exception.node_name
                        if hasattr(formatted_exception, "node_name")
                        and formatted_exception.node_name is not None
                        else invokable.name,
                        node_type=formatted_exception.node_type
                        if hasattr(formatted_exception, "node_type")
                        and formatted_exception.node_type is not None
                        else invokable.type,
                    ),
                    execution_id=self.tracer.trace_id,
                )
                await self._stream_callback.on_recv(error_stream_data)

    async def _on_execution_error_debug_info(
        self, invokable: Node, error: Exception, cur_span: Span
    ):
        logger.error(
            "Node execution error. "
            "| flow_id: {} | node type: {} | node name: {} "
            "| origin error code: {} | origin error message: {}".format(
                self._runtime_debug_info.get(WORKFLOW_ID, ""),
                invokable.type,
                invokable.name,
                error.error_code
                if isinstance(error, JiuWenBaseException)
                else "Unknown Error",
                error.message
                if isinstance(error, JiuWenBaseException)
                else "Unknown Error",
            )
        )
        try:
            await CallbackHandlerManager().trigger_event(
                event_name=TriggerEventName.ON_INVOKE.value,
                data=error.to_payload()
                if isinstance(error, WorkflowAbortException)
                else {},
                exception=error,
                component_metadata=self._get_callback_data(invokable),
                span_instance=cur_span,
                runtime_context=self.runtime_context,
            )
        except Exception as e:
            if isinstance(e, JiuWenBaseException):
                raise
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_COLLECT_ON_INVOKE_EXCEPTION_CALLBACK_INFO_ERROR.code,
                message=StatusCode.WORKFLOW_COLLECT_ON_INVOKE_EXCEPTION_CALLBACK_INFO_ERROR.errmsg,
            ) from e

    # 获取循环节点的中间执行结果
    def _get_loop_invoke_data(self, invokable: Node):
        if invokable.id in self.loop_comp:
            loop_index = len(self.workflow.data.get(invokable.id + "_loop", [])) + 1
            invoke_data = {
                "loop_node_id": self.loop_comp.get(invokable.id),
                "loop_index": loop_index,
            }
            return invoke_data

        return {}

    def _get_callback_data(self, invokable: Node):
        ori = dict(
            execution_id=self._runtime_debug_info.get(EXECUTION_ID)
            or DEFAULT_EXECUTION_ID,
            conversation_id=self._runtime_debug_info.get(CONVERSATION_ID) or "",
            current_time=datetime.datetime.now(tz=BJ_TZ),
            on_invoke_data=[],  # 用于记录当前组件执行时的中间过程信息
            # 元数据信息
            agent_id=self._runtime_debug_info.get(WORKFLOW_ID, ""),
            component_id=invokable.id if invokable else "",
            component_name=invokable.name if invokable else "",
            component_type=convert_to_old_type.get(invokable.type, invokable.type)
            if invokable
            else "",
            # 备注：这边实现组件类型从"jiuwen.start"转换成为"Start"。对于自定义组件来说不需要做这个转换，直接使用IR中自定义组件的type。
            component_config=invokable.configs if invokable else {},
        )
        # 循环体内的组件需要增加
        loop_invoke_data = self._get_loop_invoke_data(invokable)
        if loop_invoke_data:
            ori.update(loop_invoke_data)
        return ori

    def _get_condition_content(self, condition_node: SwitchNode, condition_id: str):
        """Get branch condition content."""
        if (
            hasattr(condition_node, "type")
            and condition_node.type == NodeType.BRANCH.value
        ):
            verify_the_security_of_variables_for_spiffworkflow(
                [condition_id, condition_node.id]
            )
            return f"({condition_node.id}['{SYSTEM_FIELDS}']['result'] == '{condition_id}')"
        branch = condition_node.branches[condition_id]
        exp_list = []
        # split expression use && or ||
        sub_expressions = split_condition_expressions(branch)
        for exp in sub_expressions:
            if exp in ["&&", "||"]:
                exp_list.append(CONDITION_OP.get(exp))
                continue
            exp = exp.lstrip("(").strip(")")
            left_value, mid_op, right_value = split_one_condition_expression(exp)
            left_value = self.parse_reference(left_value)
            right_value = self.parse_reference(right_value)
            assembled_exp = self.assemble_condition_expression(
                left_value, mid_op, right_value
            )
            exp_list.append(assembled_exp)
        return " ".join(exp_list)

    def _json_to_workflow_node(self, node: dict):
        """Get workflow node from json."""
        if node[TYPE] == NodeType.BRANCH.value:
            wf_node = SwitchNode(node, self.runtime_context)
        elif node[TYPE] == NodeType.INTENT_DETECTION.value:
            # 意图分类中有具体的执行逻辑，所以需要实例化为Node
            wf_node = self._initialize_node(node)
            branch_config = self._parse_intent_detection_branch_config(
                node.get("configs"), node.get("id")
            )
            branch_config = dict(
                type=node.get(TYPE),
                name=node.get(NAME),
                configs=dict(branches=branch_config),
            )
            self.nodes[self._get_intent_detection_switch_node_key(node[ID])] = (
                SwitchNode(branch_config, self.runtime_context)
            )
        else:
            wf_node = self._initialize_node(node)
        self.nodes[node[ID]] = wf_node

    def _initialize_node(self, node: dict):
        try:
            return Node(node, self.runtime_context)
        except JiuWenBaseException:
            raise
        except ValidationError as e:
            metadata = WorkflowMetadata(
                node_name=node.get(NAME), node_id=node.get(ID), node_type=node.get(TYPE)
            )
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_COMPONENT_INIT_FAILED.code,
                message=StatusCode.WORKFLOW_COMPONENT_INIT_FAILED.errmsg.format(
                    comp=format_node_info_with_metadata(metadata),
                    reason=f"{type(e).__name__}",
                ),
            ) from e

    def _json_to_workflow(self, workflow_json: dict):
        """Get workflow from json."""

        def binding_node_maker(node_config: dict):
            """实例化 Node 的封装"""
            self._json_to_workflow_node(node_config)
            if node_config[TYPE] == NodeType.LOOP.value:
                gate_check_loop_condition = Json2BpmnXmlParser.loop2gate_before(
                    node_config[ID]
                )
                self.nodes[gate_check_loop_condition] = self.nodes.get(node_config[ID])

        def get_condition_of_branch(node_id: str, branch_id: str) -> str:
            """获取分支节点对应判断条件的封装"""
            condition_node = self.nodes.get(node_id)
            if (
                condition_node.type == NodeType.INTENT_DETECTION.value
                and CUSTOM_MULTI_BRANCH_SIGN not in branch_id
            ):
                # 此条件为意图分类的条件，条件被注册进nodes中使用的key为 node_id + "_llm"
                condition_node = self.nodes.get(
                    self._get_intent_detection_switch_node_key(node_id)
                )
            if CUSTOM_MULTI_BRANCH_SIGN in branch_id:
                return self._get_custom_multi_branch(condition_node.type, branch_id)
            return self._get_condition_content(condition_node, branch_id)

        try:
            ir2bpmn_converter = Json2BpmnXmlParser(
                workflow_json, binding_node_maker, get_condition_of_branch
            )
            root = ir2bpmn_converter.parsed()
            parser = SpiffBpmnParser()
            parser.add_bpmn_xml(root)
            self.bpmn_spec = parser.find_all_specs()
            self._construct_bpmn_from_spec()
        except Exception as e:
            logger.error(
                f"Failed to parse IR as BPMNWorkflow, details: {e}",
                simple_log="Failed to parse IR as BPMNWorkflow.",
            )
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_IR_VALIDATION_ERROR.code,
                message=StatusCode.WORKFLOW_IR_VALIDATION_ERROR.errmsg.format(
                    reason=str(e) if LOG_VERBOSE_MODE else str(type(e).__name__)
                ),
            ) from e

        self.runtime_context.update(dict(node_variable=self.workflow.data))

    def _spec_to_workflow(self, workflow_spec: WorkflowSpec):
        """Get workflow from WorkflowSpec."""
        self.bpmn_spec = workflow_spec.bpmn_spec
        self._construct_bpmn_from_spec()
        loop_gates = set()
        for node_id, node_spec in workflow_spec.node_spec.items():
            if node_spec.node_type == "Node":
                if node_id.startswith("xor_gate_before_"):
                    loop_gates.add(node_id)
                else:
                    self.nodes[node_id] = Node.construct_from_spec(
                        node_spec=node_spec, runtime_context=self.runtime_context
                    )
            elif node_spec.node_type == "SwitchNode":
                self.nodes[node_id] = SwitchNode.construct_from_spec(
                    node_spec=node_spec, runtime_context=self.runtime_context
                )

        for node_id in loop_gates:
            loop_node_id = node_id[len("xor_gate_before_") :]
            self.nodes[node_id] = self.nodes.get(loop_node_id)
        self.workflow_json = workflow_spec.ir
        self.runtime_context.update(dict(node_variable=self.workflow.data))

    def _construct_bpmn_from_spec(self):
        """
        使用（可复用 的） BpmnProcessSpec 实例构建 （SpiffWorkflow 的） BpmnWorkflow 实例。
        """
        self.workflow = workflow.BpmnWorkflow(
            self.bpmn_spec.get("process_node"), self.bpmn_spec
        )
        self.runtime_context.update(dict(node_variable=self.workflow.data))

    def _generator(self, path_list, data_source):
        """
        根据路径列表返回对应的生成器
        """
        if not path_list or len(path_list) < 3:
            logger.error(f"无效的path_list: {path_list}")
            return None
        node_id = path_list[0]
        field_name = path_list[-1]
        target_value = None
        for i in range(len(path_list) - 1, 0, -1):
            current_field = path_list[i]
            current_value = data_source[node_id]["userFields"].get(current_field, {})
            if current_value != {}:
                target_value = current_value
                break
        if target_value == {} or isinstance(target_value, AsyncGenerator):
            if node_id not in self.node_broadcasters:
                self.node_broadcasters[node_id] = AsyncGeneratorBroadcaster(
                    target_value
                )
            broadcaster = self.node_broadcasters[node_id]
            return broadcaster.get_generator_by_id(field_name)
        return target_value

    def _load_state(self, bpmn_workflow_state: BpmnInstanceState):
        # recover basic information
        self.name = bpmn_workflow_state.name
        self.id = bpmn_workflow_state.id
        self.description = bpmn_workflow_state.description
        self.loop_comp = bpmn_workflow_state.loop_comp
        self.workflow_json = bpmn_workflow_state.workflow_json
        self.workflow = deserialize_object(bpmn_workflow_state.binary_workflow)
        # recover nodes by node state
        for node_id, node_info in bpmn_workflow_state.nodes_info.items():
            node = Node(node_info, self.runtime_context)
            node.action.load_state(bpmn_workflow_state.nodes_states.get(node_id))
            self.nodes[node_id] = node
            if node.type == NodeType.LOOP.value:
                self.nodes[Json2BpmnXmlParser.loop2gate_before(node.id)] = node
        self.runtime_context.set("node_variable", self.workflow.data)
        self.tracer = Tracer(self.runtime_context, bpmn_workflow_state.trace_state)
