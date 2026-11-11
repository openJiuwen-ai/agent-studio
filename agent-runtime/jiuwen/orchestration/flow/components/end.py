#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""Workflow end node."""

from typing import Any, Generator

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.controller.common.task_type import TaskType
from jiuwen.orchestration import Invokable
from jiuwen.orchestration.callbacks.span import Span
from jiuwen.orchestration.flow.components.message_base import (
    MessageComponentBase,
    STRUCT_OUTPUT_TEMPLATE,
    ENABLE_STRUCT_MESSAGE,
)
from jiuwen.orchestration.flow.components.util import (
    process_generator_values_of_dict,
    pass_streaming_data_without_finish,
)
from jiuwen.orchestration.flow.constant import (
    CONSTANT_NODE_VARIABLE,
    WORKFLOW_EXECUTE_DEBUG_INFO,
)
from jiuwen.orchestration.flow.constant import MEM_MAP, MEMORY_VARIABLES
from jiuwen.orchestration.flow.constant import USER_FIELDS
from jiuwen.orchestration.flow.constant import WORKFLOW_CHAT_MANAGER
from jiuwen.orchestration.flow.enum import NodeType
from jiuwen.orchestration.flow.model.workflow_data_class import (
    WorkflowMetadata,
    WorkflowStreamingData,
)
from jiuwen.orchestration.flow.outputmode import OutputMode
from jiuwen.orchestration.flow.runtime_context import RuntimeContext
from jiuwen.plugin.common.constant import WORKFLOW_ID
from jiuwen.prompt import Prompt, Template
from pydantic import BaseModel, StrictStr, Field, ValidationError

OUTPUT_PREFIX = "#end_"


class EndComponentConfig(BaseModel):
    """
    结束组件 配置校验
    """

    response_template: StrictStr = Field(min_length=1)


async def process_generator_values_of_output(
    inputs: dict,
    out_to_in: dict,
    workflow_streaming_data: WorkflowStreamingData,
    metadata: WorkflowMetadata,
):
    """获取流式输出变量值"""
    if inputs is None or len(inputs) == 0:
        return inputs

    """
    输出变量中存在还没解析的流式变量，获取其变量
    """
    # 记录流式返回值，防止多次引用同一个流，导致第二次读流失败
    flow_record = {}
    for k, v in inputs.items():
        if not k.startswith(OUTPUT_PREFIX) or not isinstance(v, Generator):
            continue
        if k in out_to_in and not isinstance(inputs[out_to_in[k]], Generator):
            # 把输入中已经获取过的流式输出记录到输出中
            inputs[k] = inputs[out_to_in[k]]
        else:
            if v not in flow_record:
                inputs[k], _ = await pass_streaming_data_without_finish(
                    generator=inputs[k],
                    workflow_streaming_data=workflow_streaming_data,
                    metadata=metadata,
                )
                flow_record[v] = k
            else:
                inputs[k] = inputs.get(flow_record[v])
    return inputs


# 记录输出和输入使用相同流式输出的映射，防止流式被重复消费，获取不到数据
def build_output_to_input(inputs: dict):
    """获取输出变量和输入变量的映射关系"""
    if inputs is None or len(inputs) == 0:
        return {}

    gen_map = {}
    for k, v in inputs.items():
        if isinstance(v, Generator):
            gen_map.setdefault(v, []).append(k)

    gen_out_to_in = {}
    for _, v in gen_map.items():
        input_gen = next((x for x in v if not x.startswith(OUTPUT_PREFIX)), None)
        if input_gen:
            gen_out_to_in.update(
                {x: input_gen for x in v if x.startswith(OUTPUT_PREFIX)}
            )
    return gen_out_to_in


def _remove_output_data(inputs: dict):
    keys = [x for x in inputs.keys() if x.startswith(OUTPUT_PREFIX)]
    for x in keys:
        del inputs[x]


# 如果输入变量中存在没有被回复引用的流式变量时，需要关闭流，防止工作流卡死
def _close_generator(inputs: dict):
    for _, v in inputs.items():
        if isinstance(v, Generator):
            v.close()


class End(Invokable, MessageComponentBase):
    """End node."""

    def __init__(
        self, conf: dict, runtime_context: RuntimeContext, metadata: WorkflowMetadata
    ):
        self.conf = conf
        raw_mode = conf.get("outputMode")
        self.output_mode = OutputMode.from_str(raw_mode)
        self.origin_template_conf = (
            conf["responseTemplate"]
            if "responseTemplate" in conf and len(conf["responseTemplate"]) > 0
            else None
        )
        self._validate_configs()
        self.template = (
            Prompt(
                template=Template(
                    name="flow_output_template", content=self.origin_template_conf
                )
            )
            if self.origin_template_conf is not None
            else None
        )
        self.node_type = NodeType.END.value
        self.runtime_context = runtime_context
        self.chat_manager = runtime_context.get(WORKFLOW_CHAT_MANAGER)
        self.metadata = metadata
        self.end_interrupt = False
        self.event = conf.get("event", {})
        self.struct_output_template = conf.get(STRUCT_OUTPUT_TEMPLATE, "")
        self.enable_struct_message = conf.get(ENABLE_STRUCT_MESSAGE, False)
        if self.event and self.event.get("type", "") == TaskType.TASK_COMPLETION:
            self.end_interrupt = True

    async def invoke(self, inputs: dict[str, Any], **kwargs):
        """Invoke to assemble final answer."""
        try:
            answer = (
                await self.template.ainvoke(inputs.get(USER_FIELDS)) if self.template else ""
            )
            output = {
                k[len(OUTPUT_PREFIX) :]: v
                for k, v in inputs.get(USER_FIELDS, {}).items()
                if k.startswith(OUTPUT_PREFIX) and v is not None
            }
        except JiuWenBaseException:
            raise
        except Exception as e:
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_END_TEMPLATE_ASSEMBLE_ERROR.code,
                message=StatusCode.WORKFLOW_END_TEMPLATE_ASSEMBLE_ERROR.errmsg,
            ) from e
        return dict(responseContent=answer, userFields=output)

    async def ainvoke(self, inputs: dict, **kwargs):
        """Asynchronous invoke to assemble end outputs."""
        stream_callback = kwargs.get("stream_callback")
        if stream_callback is None:
            return self.invoke(inputs, **kwargs)

        # USER_FIELDS 缺失时不得把 None 传给 build_output_to_input（`x in None`）
        raw_inputs = inputs if isinstance(inputs, dict) else {}
        inputs = raw_inputs.get(USER_FIELDS) or {}
        if not isinstance(inputs, dict):
            inputs = {}
        gen_out_to_in = build_output_to_input(inputs)

        span: Span = kwargs.get("span")
        ref = kwargs.get("ref", {})
        stream_related_info = WorkflowStreamingData(
            stream_callback=stream_callback, execution_id=span.trace_id
        )
        # 处理消息以及结束节点的执行回复模板
        try:
            output_mode_val = self.output_mode.value if self.output_mode else None
            inputs = await process_generator_values_of_dict(
                origin_template=self.origin_template_conf,
                inputs=inputs,
                workflow_streaming_data=stream_related_info,
                metadata=self.metadata,
                output_mode=output_mode_val,
                ref=ref,
            )
            inputs = await process_generator_values_of_output(
                inputs=inputs,
                out_to_in=gen_out_to_in,
                workflow_streaming_data=stream_related_info,
                metadata=self.metadata,
            )
        except JiuWenBaseException:
            raise
        except Exception as e:
            raise JiuWenBaseException(
                message=StatusCode.WORKFLOW_END_STREAM_ERROR.errmsg,
                error_code=StatusCode.WORKFLOW_END_STREAM_ERROR.code,
            ) from e

        _close_generator(inputs)
        outputs = {
            k[len(OUTPUT_PREFIX) :]: v
            for k, v in inputs.items()
            if k.startswith(OUTPUT_PREFIX) and v is not None
        }
        _remove_output_data(inputs)

        # 模板拼接
        try:
            final_output = await self.template.ainvoke(inputs) if self.template else ""
        except Exception as e:
            raise JiuWenBaseException(
                message=StatusCode.WORKFLOW_END_TEMPLATE_ASSEMBLE_ERROR.errmsg,
                error_code=StatusCode.WORKFLOW_END_TEMPLATE_ASSEMBLE_ERROR.code,
            ) from e

        # 结束节点最后返回的finish事件，带有完整的workflow输出信息
        struct_answer_item = (
            dict(
                struct_output_template=self.struct_output_template,
                variables={**inputs, **outputs},
            )
            if self.enable_struct_message and self.struct_output_template
            else {}
        )
        try:
            output_mode_val = self.output_mode.value if self.output_mode else None
            await self.format_workflow_end_output(
                origin_output=final_output,
                struct_answer_item=struct_answer_item,
                metadata=self.metadata,
                stream_data=stream_related_info,
                outputs=outputs,
                output_mode=output_mode_val,
            )
            self._update_parent_memory_from_sub_workflow()  # 在结束节点结束前，若该工作流为子工作流，则其将与父工作流关联的记忆变量写入runtime_context
            return dict(
                responseContent=final_output,
                userFields=outputs,
                output_mode=output_mode_val,
            )
        except Exception as e:
            raise JiuWenBaseException(
                message=StatusCode.WORKFLOW_END_STREAM_ERROR.errmsg,
                error_code=StatusCode.WORKFLOW_END_STREAM_ERROR.code,
            ) from e

    def _validate_configs(self):
        if self.origin_template_conf is None:
            return
        try:
            EndComponentConfig.model_validate(
                dict(response_template=self.origin_template_conf)
            )
        except ValidationError as e:
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_END_INIT_ERROR.code,
                message=StatusCode.WORKFLOW_END_INIT_ERROR.errmsg,
            ) from e

    def _update_parent_memory_from_sub_workflow(self) -> None:
        """
        Update the memory_variables of the parent
        workflow in place according to the memory and
        memory mapping of the sub workflow.
        """
        workflow_id = self.runtime_context.get(WORKFLOW_EXECUTE_DEBUG_INFO, {}).get(
            WORKFLOW_ID
        )  # 当前工作流id
        mem_map = self.runtime_context.get(MEM_MAP, {})  # 记忆变量映射
        memory_variables = self.runtime_context.get(
            MEMORY_VARIABLES, {}
        )  # 记忆变量值存放池

        # memory_dict 是子工作流结束时, 'node_start' 节点中 'memory' 的最终值
        memory_dict = (
            self.runtime_context.get(CONSTANT_NODE_VARIABLE, {})
            .get("node_start", {})
            .get("memory", {})
        )

        filtered_mem_map = {
            key: value
            for key, value in mem_map.items()
            if isinstance(key, str) and key.startswith(workflow_id)
        }

        if not filtered_mem_map:
            # 该工作流无父节点 或 无需回传全局变量
            return

        # 构造子工作流内存键的前缀，格式为: {sub_workflow_id}.memory.
        prefix = f"{workflow_id}.memory."

        # 循环将当前工作流的记忆变量写入runtime_context变量池
        for sub_workflow_key_full, parent_map_key in filtered_mem_map.items():
            # 检查映射的 "key" (子工作流路径) 是否符合预期的格式
            if not sub_workflow_key_full.startswith(prefix):
                logger.warning(
                    f"Mapping key '{sub_workflow_key_full}' (mapped to '{parent_map_key}') "
                    f"does not match prefix '{prefix}'. Skipping."
                )
                continue  # 使用 continue 减少嵌套

            # 提取在 memory_dict 中对应的简单键名
            # 例如: 从 "workflow_id_123.memory.my_var" 提取 "my_var"
            simple_key = sub_workflow_key_full[len(prefix) :]

            # 检查这个简单键是否存在于子工作流的本地内存 (memory_dict) 中
            if simple_key not in memory_dict:
                logger.warning(
                    f"Key '{simple_key}' (from mapping {sub_workflow_key_full}) "
                    f"not found in sub-workflow memory (memory_dict). Skipping."
                )
                continue

            # 获取对应的值
            value_to_write = memory_dict[simple_key]

            # 按照映射要求，将值写入 memory_variables
            try:
                logger.info(
                    f"Writing back memory variable: Updating '{sub_workflow_key_full}' "
                    f" with value: {value_to_write})"
                )
                memory_variables[sub_workflow_key_full] = value_to_write
            except Exception as e:
                logger.error(
                    f"Error writing back memory variable: {e} "
                    f"(Child key: {sub_workflow_key_full}, "
                    f"Parent key: {parent_map_key})"
                )
        return
