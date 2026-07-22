import asyncio
import inspect
import re
from enum import Enum
from typing import Any, Optional, Union, AsyncGenerator

from agent_runtime.common.session_state_access import get_state_info
from jiuwen.extension.workflow_node.utils import get_workflow_param
from openjiuwen.core.common.logging import workflow_logger, LogEventType
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session.node import Session
from openjiuwen.core.session.stream import OutputSchema
from openjiuwen.core.session.stream.base import CustomSchema
from openjiuwen.core.workflow.components.flow.end_comp import (
    End as BaseEnd,
    EndConfig as BaseEndConfig,
    TemplateUtils,
)

_TEMPLATE_SPLIT_PATTERN = re.compile(r"(\{\{[^{}]*?\}\})")

# 父-子工作流记忆传递相关常量
MEM_MAP = "mem_map"
MEMORY_VARIABLES = "memory_variables"
CONSTANT_NODE_VARIABLE = "node_variable"
WORKFLOW_ID = "workflow_id"
WORKFLOW_EXECUTE_DEBUG_INFO = "workflow_debug_info"

# 流式输出常量
OUTPUT_PREFIX = "#end_"
STRUCT_OUTPUT_TEMPLATE = "struct_output_template"
ENABLE_STRUCT_MESSAGE = "isStructMessage"
USER_FIELDS = "userFields"
ORIGIN_ANSWER = "origin_answer"

# 类型强转常量（与旧框架 force_convert → _convert_simple 行为对齐）
STRING_TYPE = "string"
INTEGER_TYPE = "integer"
NUMBER_TYPE = "number"
BOOLEAN_TYPE = "boolean"
ARRAY_TYPE = "array"
OBJECT_TYPE = "object"

_SIMPLE_TYPE_CONVERT = {
    STRING_TYPE: str,
    INTEGER_TYPE: int,
    NUMBER_TYPE: float,
    BOOLEAN_TYPE: bool,
}

_TYPE_DEFAULT_VALUE = {
    STRING_TYPE: "",
    INTEGER_TYPE: None,
    NUMBER_TYPE: None,
    BOOLEAN_TYPE: None,
}


def _has_response_payload(output: Any) -> bool:
    """判断 output 是否为携带 response 字段的 OutputSchema 类型输出（G.CTL.03：抽取多条件判断）。"""
    return (
        hasattr(output, "type")
        and hasattr(output, "payload")
        and isinstance(output.payload, dict)
        and "response" in output.payload
    )


async def process_generator_values_of_output(
    inputs: dict, out_to_in: dict, workflow_streaming_data
):
    """获取流式输出变量值"""
    if inputs is None or len(inputs) == 0:
        return inputs

    # 记录流式返回值，防止多次引用同一个流，导致第二次读流失败
    flow_record = {}
    # 保存 reasoning_content
    reasoning_content = ""

    for k, v in inputs.items():
        # 直接检查是否有 reasoning_content 字段
        if k == "reasoning_content" and isinstance(v, str):
            reasoning_content = v
        if not k.startswith(OUTPUT_PREFIX) or not isinstance(v, AsyncGenerator):
            continue
        if k in out_to_in and not isinstance(inputs[out_to_in[k]], AsyncGenerator):
            # 把输入中已经获取过的流式输出记录到输出中
            inputs[k] = inputs[out_to_in[k]]
        else:
            if v not in flow_record:
                # 处理流式数据
                data_list = []
                async for data in v:
                    data_list.append(data)
                    if workflow_streaming_data:
                        await workflow_streaming_data.stream_callback(data)
                inputs[k] = "".join(data_list)
                flow_record[v] = k
            else:
                inputs[k] = inputs.get(flow_record[v])

    # 如果有 reasoning_content，记录到 inputs 中供后续使用
    if reasoning_content:
        inputs["_reasoning_content"] = reasoning_content
    return inputs


# 记录输出和输入使用相同流式输出的映射，防止流式被重复消费，获取不到数据
def build_output_to_input(inputs: dict):
    """获取输出变量和输入变量的映射关系"""
    if inputs is None or len(inputs) == 0:
        return {}

    gen_map = {}
    for k, v in inputs.items():
        if isinstance(v, AsyncGenerator):
            gen_map.setdefault(v, []).append(k)

    gen_out_to_in = {}
    for _, v in gen_map.items():
        if len(v) == 1:
            # 只有一个生成器，无需映射
            continue
        # 找到第一个非 #end_ 前缀的键作为主键
        input_gen = next((x for x in v if not x.startswith(OUTPUT_PREFIX)), v[0])
        if input_gen:
            # 将所有 #end_ 前缀的键映射到主键
            gen_out_to_in.update(
                {x: input_gen for x in v if x.startswith(OUTPUT_PREFIX)}
            )
    return gen_out_to_in


async def _skip_last_generator(gen: AsyncGenerator, meta_count: int) -> AsyncGenerator:
    """消费生成器全部帧后，仅当帧数 == meta_count 时丢弃最后一帧（聚合帧），其余原样回放。

    保留 AsyncGenerator 类型，使下游 super().transform() 仍能逐帧流式处理。
    """
    buf: list = []
    async for item in gen:
        buf.append(item)
    if len(buf) == meta_count and len(buf) > 1:
        buf = buf[:-1]
    for item in buf:
        yield item


async def _interruptible_generator(
    gen: AsyncGenerator,
    session: Session,
    is_interrupted_fn,
    on_complete=None,
) -> AsyncGenerator:
    """包装输入生成器，在每次迭代产出后检查中断状态，若中断则提前终止。

    Args:
        gen: 原始 AsyncGenerator
        session: 会话对象，用于中断检测
        is_interrupted_fn: 中断检测回调函数
        on_complete: 可选回调，生成器结束（含中断）时调用，参数为收集帧的拼接结果
    """
    frames: list = []
    try:
        async for item in gen:
            frames.append(item)
            yield item
            if is_interrupted_fn(session):
                break
    finally:
        if on_complete is not None:
            result = "".join(str(f) for f in frames)
            on_complete(result)


def _remove_output_data(inputs: dict):
    keys = [x for x in inputs.keys() if x.startswith(OUTPUT_PREFIX)]
    for x in keys:
        del inputs[x]


SPLIT_DELIMITER = "\001"


def get_output_data_with_metadata(
    answer: Any,
    node_id: str = "",
    node_name: str = "",
    node_type: str = "end",
    should_interrupt: bool = False,
    think: str = "",
    outputs: dict = None,
    output_mode: Optional[str] = None,
    struct_answer: str = "",
) -> dict:
    """
    封装流式输出的结果，包括原始输出、节点ID、节点类型

    Args:
        answer: 原始输出内容
        node_id: 节点ID
        node_name: 节点名称
        node_type: 节点类型
        should_interrupt: 是否中断
        think: 思考内容
        outputs: 用户字段输出
        output_mode: 输出模式
        struct_answer: 结构化输出

    Returns:
        封装后的输出字典
    """
    if isinstance(answer, dict):
        answer_value = (
            answer if "response" not in answer else answer.get("response", "")
        )
    else:
        answer_value = answer

    # 处理 answer 中包含 think 的情况（通过 SPLIT_DELIMITER 分割）
    final_think = think
    final_answer = answer_value
    if isinstance(final_answer, str) and SPLIT_DELIMITER in final_answer:
        parts = final_answer.split(SPLIT_DELIMITER)
        final_answer = parts[0]
        if len(parts) > 1 and not final_think:
            final_think = parts[1]

    base = dict(
        answer=final_answer,
        node_id=node_id,
        node_name=node_name,
        node_type=node_type,
        should_interrupt=should_interrupt,
    )
    if struct_answer:
        base[ORIGIN_ANSWER] = struct_answer
    if final_think:
        base["think"] = final_think
    if output_mode is not None:
        base["output_mode"] = output_mode
    return base | ({USER_FIELDS: outputs} if outputs else {})


class OutputMode(Enum):
    """
    前端气泡展示方式枚举。
    """

    SEPARATE = "separate"
    APPEND = "append"
    REPLACE = "replace"

    @classmethod
    def from_str(cls, s: Optional[str]) -> Optional["OutputMode"]:
        """将字符串（大小写不敏感）解析为 OutputMode 枚举值。"""
        if s is None:
            return None
        try:
            return cls(s)
        except ValueError:
            return None


class EndConfig(BaseEndConfig):
    """扩展的 End 组件配置，继承基础配置"""

    pass


class End(BaseEnd):
    """
    扩展的 End 组件，支持增强的流式输出。

    继承自 openjiuwen 的基础 End 组件，新增:
    - 增强的流式输出处理
    - 结构化输出支持
    """

    def __init__(self, conf: Union[EndConfig, dict] = None):
        super().__init__(conf)
        # 从配置中提取结构化输出相关参数
        conf_dict = conf if isinstance(conf, dict) else {}
        raw_mode = conf_dict.get("outputMode")
        self.output_mode = OutputMode.from_str(raw_mode)
        self.node_type = "jiuwen.end"
        self.node_name = conf_dict.get("name", "")
        self.end_interrupt = False
        self.event = conf_dict.get("event", {})
        if self.event and self.event.get("type", "") == "task_completion":
            self.end_interrupt = True
        self.struct_output_template = conf_dict.get(STRUCT_OUTPUT_TEMPLATE, "")
        self.enable_struct_message = conf_dict.get(ENABLE_STRUCT_MESSAGE, False)
        self._stream_output: Optional[dict] = None
        # 回复模板，用于判断流式起始/结束空 chunk 的发送条件
        self._response_template: str = conf_dict.get("responseTemplate", "") or ""
        # 预计算模板 split 结果，用于判断起始/结束是否需要空 chunk
        self._template_parts: list[str] = (
            _TEMPLATE_SPLIT_PATTERN.split(self._response_template)
            if self._response_template
            else []
        )

        # 获取 userFields.inputs schema，用于输入值的类型强转
        _user_fields_conf = conf_dict.get("userFields", {}) or {}
        self._user_fields_inputs: list[dict] = _user_fields_conf.get("inputs", []) or []

        # mix 模式协调：batch 路径只注入数据不渲染（防止 engine pickle 失败），
        # stream 路径负责 merge + render + signal
        # None 表示兼容 openjiuwen 默认行为；IR converter 会显式标记纯流式/混合场景。
        self._expect_mix: Optional[bool] = None
        self._mix_condition = None  # asyncio.Condition，lazy init
        self._mix_data = {}  # {'batch': {inputs, outputs}, 'stream': {inputs, outputs}}
        self._mix_push_count = 0  # 已 push 的路径数 (0/1/2)
        self._mix_render_complete = False
        self._mix_batch_pushed = False  # batch 路径已 push 数据，stream 可以开始渲染

        # Pregel 引擎在 wait_for_all=False 时，每条入边分别触发 End 节点，
        # 导致 stream()/invoke() 被多次调用。用各自独立的标志保证幂等，
        # 同时不影响 mix 模式下 batch(invoke/stream) 与 stream(collect/transform) 两路的协调。
        self._invoke_executed = False
        self._stream_executed = False
        self._collect_executed = False
        self._transform_executed = False

    @staticmethod
    def _is_workflow_interrupted(session: Session) -> bool:
        """检查工作流是否处于中断状态，通过 workflow_state 中的 __interrupted 标志判断。"""
        try:
            workflow_state = get_state_info(session, "workflow_state")
            if not isinstance(workflow_state, dict):
                return False
            return workflow_state.get("workflow", {}).get("__interrupted") is True
        except Exception:
            return False

    def _should_emit_start_marker(self) -> bool:
        """
        判断是否需要发送流式起始空 chunk。

        旧框架 process_specified_reply 使用 re.split 切分 responseTemplate，
        当模板以 {{...}} 开头时，split 结果的首元素为空字符串，
        该空字符串会作为 PARTIAL_CONTENT(answer="") 发送，充当流式起始标记。
        """
        if not self._template_parts:
            return False
        return self._template_parts[0] == ""

    def _should_emit_end_marker(self) -> bool:
        """
        判断是否需要发送流式结束空 chunk。

        与起始标记同理：当模板以 {{...}} 结尾时，split 结果的末元素为空字符串，
        该空字符串作为 PARTIAL_CONTENT(answer="") 发送，充当流式结束标记。
        """
        if not self._template_parts:
            return False
        return self._template_parts[-1] == ""

    def _apply_type_conversion(self, inputs: dict) -> None:
        """按照 userFields.inputs schema 对输入值做类型强转，与旧框架 force_convert → _convert_simple 对齐。"""
        if not self._user_fields_inputs or not isinstance(inputs, dict):
            return
        for definition in self._user_fields_inputs:
            field_id = definition.get("id", "")
            if field_id not in inputs:
                continue
            expected_type = definition.get("type", STRING_TYPE)
            inputs[field_id] = self._convert_simple(inputs[field_id], expected_type)

    @staticmethod
    def _convert_simple(actual_value, expected_type: str):
        """对单个值做简单类型强转，逻辑与旧框架 _convert_simple 一致。"""
        import inspect as _inspect

        # 流式数据不做强转
        if (
            isinstance(actual_value, AsyncGenerator)
            or _inspect.isasyncgen(actual_value)
            or hasattr(actual_value, "__aiter__")
        ):
            return actual_value
        if actual_value is None:
            return _TYPE_DEFAULT_VALUE.get(expected_type)
        if expected_type == ARRAY_TYPE and isinstance(actual_value, list):
            return "" if not actual_value else str(actual_value)
        if expected_type == OBJECT_TYPE and isinstance(actual_value, dict):
            return "" if not actual_value else str(actual_value)
        convert_action = _SIMPLE_TYPE_CONVERT.get(expected_type, str)
        # bool 是特殊的 int，需额外判断
        if not isinstance(actual_value, convert_action) or (
            isinstance(actual_value, bool) and expected_type == INTEGER_TYPE
        ):
            try:
                return convert_action(actual_value)
            except (ValueError, TypeError):
                return None
        return actual_value

    def set_expect_mix(self, expect_mix: bool) -> None:
        self._expect_mix = expect_mix

    def set_mix(self):
        if self._expect_mix is False:
            return
        super().set_mix()

    def _reset_stream_output(self) -> None:
        self._stream_output = None

    def _build_final_output(
        self,
        *,
        answer: str,
        node_id: Optional[str] = None,
        struct_answer: Any = None,
        user_fields: Optional[dict] = None,
    ) -> dict:
        result = {
            "answer": answer,
            "node_id": node_id,
            "node_type": self.node_type,
        }
        if struct_answer:
            result[ORIGIN_ANSWER] = struct_answer
        if self.output_mode is not None:
            result["output_mode"] = self.output_mode.value
        result["user_fields"] = user_fields
        return result

    async def _mix_coordinate(
        self,
        key: str,
        inputs: dict,
        outputs: dict,
    ) -> tuple[dict, dict, bool]:
        """mix 协调：push 数据到 _mix_data，等待另一条路径。

        第二条路径（后 push 的）负责合并数据并消费 generator，
        第一条路径在收到完成信号后跳过。

        Args:
            key: 'batch'（批输入路径: invoke/stream）或 'stream'（流输入路径: collect/transform）
            inputs: 当前路径的输入
            outputs: 当前路径的输出

        Returns:
            (merged_inputs, merged_outputs, is_renderer)
            - is_renderer=True：调用方继续执行渲染
            - is_renderer=False：另一方已完成渲染，调用方应 return/return None
        """
        if not self._mix:
            return inputs, outputs, True

        if self._mix_condition is None:
            self._mix_condition = asyncio.Condition()

        async with self._mix_condition:
            self._mix_data[key] = {"inputs": inputs, "outputs": outputs}
            self._mix_push_count += 1
            if key == "batch":
                self._mix_batch_pushed = True
            self._mix_condition.notify_all()
            i_am_last = self._mix_push_count == 2

        # ——— 批路径：只注入数据，等待流路径渲染 ———
        if key == "batch":
            async with self._mix_condition:
                if not self._mix_render_complete:
                    try:
                        await asyncio.wait_for(self._mix_condition.wait(), timeout=3.0)
                    except asyncio.TimeoutError:
                        pass
            if self._mix_render_complete:
                return inputs, outputs, False
            # 超时回退：流路径未到达，批路径自己渲染
            merged_inputs, merged_outputs = self._merge_mix_data()
            async with self._mix_condition:
                self._mix_render_complete = True
                self._mix_condition.notify_all()
            self._mix = False
            if self._template:
                self._template._data_source_count = 1
            merged_inputs = await self._wrap_generators_for_replay(merged_inputs, key)
            return merged_inputs, merged_outputs, True

        # ——— 流路径：负责渲染 ———
        if i_am_last:
            # 批路径已 push，直接合并渲染
            pass  # 跳到下面的渲染逻辑
        else:
            # 等待批路径 push
            async with self._mix_condition:
                if not self._mix_batch_pushed:
                    try:
                        await asyncio.wait_for(self._mix_condition.wait(), timeout=3.0)
                    except asyncio.TimeoutError:
                        pass
            if not self._mix_batch_pushed:
                # 超时：批路径未到达，流路径独自渲染
                pass  # 跳到下面的渲染逻辑

        # 流路径渲染
        merged_inputs, merged_outputs = self._merge_mix_data()
        async with self._mix_condition:
            self._mix_render_complete = True
            self._mix_condition.notify_all()
        self._mix = False
        if self._template:
            self._template._data_source_count = 1
        merged_inputs = await self._wrap_generators_for_replay(merged_inputs, key)
        return merged_inputs, merged_outputs, True

    async def _wrap_generators_for_replay(self, inputs: dict, key: str) -> dict:
        """消费原始 AsyncGenerator，根据路径类型替换。

        批路径（key='batch'）：替换为字符串（引擎会序列化批路径输入，generator 无法 pickle）
        流路径（key='stream'）：替换为逐帧回放式 generator（保留流式输出）
        """
        for k, v in list(inputs.items()):
            if isinstance(v, AsyncGenerator):
                frames = []
                async for item in v:
                    frames.append(item)

                if key == "batch":
                    inputs[k] = "".join(frames)
                else:

                    def _make_replay(captured_frames):
                        async def _replay():
                            for item in captured_frames:
                                yield item

                        return _replay

                    inputs[k] = _make_replay(frames)()
        return inputs

    def _merge_mix_data(self) -> tuple[dict, dict]:
        """合并两路数据，batch 侧数据优先级高于 stream 侧（与原始逻辑一致）。"""
        stream_inputs = self._mix_data.get("stream", {}).get("inputs", {})
        batch_inputs = self._mix_data.get("batch", {}).get("inputs", {})
        stream_outputs = self._mix_data.get("stream", {}).get("outputs", {})
        batch_outputs = self._mix_data.get("batch", {}).get("outputs", {})
        return {**stream_inputs, **batch_inputs}, {**stream_outputs, **batch_outputs}

    def get_stream_output(self):
        return self._stream_output

    def _format_struct_answer(
        self, origin_output: str, struct_template: str, variables: dict[str, Any]
    ) -> str:
        """渲染结构化输出模板，返回 JSON 字符串"""
        if not struct_template:
            return ""
        vars_copy = dict(variables)
        vars_copy["_NODE_OUTPUT"] = (
            origin_output.get("answer", "")
            if isinstance(origin_output, dict)
            else origin_output
        )
        try:
            return TemplateUtils.render_template(struct_template, vars_copy)
        except Exception as e:
            workflow_logger.warning(
                "End struct template render failed: %s",
                str(e),
            )
            return ""

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        """
        执行 End 组件逻辑，在返回前处理父-子工作流记忆变量传递。

        增强功能包括：
        - 处理输入中的生成器值
        - 支持结构化输出
        """
        # 幂等保护：End 节点在 wait_for_all=False 时可能被 Pregel 引擎多次触发
        if self._invoke_executed:
            return {}
        self._invoke_executed = True

        # 处理输入中的生成器值
        outputs = {}
        if inputs and isinstance(inputs, dict):
            # 构建输出到输入的映射，防止重复消费流式数据
            if inputs.get(USER_FIELDS):
                inputs = inputs[USER_FIELDS]
            gen_out_to_in = build_output_to_input(inputs)

            # 按照 userFields.inputs schema 对输入值做类型强转
            self._apply_type_conversion(inputs)

            # 处理生成器值
            inputs = await process_generator_values_of_output(
                inputs=inputs,
                out_to_in=gen_out_to_in,
                workflow_streaming_data=None,  # 非流式调用，不需要回调
            )

            outputs = {
                k[len(OUTPUT_PREFIX) :]: v
                for k, v in inputs.items()
                if k.startswith(OUTPUT_PREFIX) and v is not None
            }

            # 移除输出数据标记
            _remove_output_data(inputs)

        # mix 模式协调
        inputs, outputs, _mix_i_am_renderer = await self._mix_coordinate(
            "batch", inputs, outputs
        )
        if not _mix_i_am_renderer:
            return None

        # 调用父类的invoke方法获取结果
        response = await super().invoke(inputs, session, context)

        # 提取原始文本输出
        final_output = (
            str(response)
            if not isinstance(response, dict)
            else response.get("response", "")
        )

        # 处理结构化输出：渲染模板得到 JSON 字符串
        struct_answer_str = ""
        if self.enable_struct_message and self.struct_output_template:
            struct_answer_str = self._format_struct_answer(
                final_output,
                self.struct_output_template,
                {**inputs, **response.get("output", {})},
            )
            # 将结构化输出添加到结果中
            if "output" not in response:
                response["output"] = {}
            response["output"]["struct_answer"] = struct_answer_str

        # 从 inputs 中提取 reasoning_content（think）
        think_content = inputs.get("_reasoning_content", "")
        if not think_content:
            # 检查 outputs 中是否有 reasoning_content
            for k, v in outputs.items():
                if k == "reasoning_content" and isinstance(v, str):
                    think_content = v
                    break

        # 构建最终输出结果
        inner_session = getattr(session, "_inner", None)
        node_id = getattr(inner_session.state(), "_node_id", None)
        query = session.get_global_state("query") or ""
        # outputs 来自 IR 中 outputs.userFields（#end_ 前缀映射），代表 End 节点最终输出，
        # 优先级高于 inputs（IR 的 inputs.userFields，仅作为兜底/原始引用）。
        user_fields = {**inputs, **outputs, **{"query": query}}

        # 构建带有 think 的 result（用于 message_end）
        result_with_think = get_output_data_with_metadata(
            answer=struct_answer_str if struct_answer_str else final_output,
            node_id=node_id,
            node_name=self.node_name,
            node_type=self.node_type,
            should_interrupt=self.end_interrupt,
            think=think_content,
            outputs=user_fields,
            output_mode=self.output_mode.value if self.output_mode else None,
            struct_answer=final_output,
        )

        # 构建不带 think 的 result（用于 workflow_end）
        result_without_think = get_output_data_with_metadata(
            answer=struct_answer_str if struct_answer_str else final_output,
            node_id=node_id,
            node_name=self.node_name,
            node_type=self.node_type,
            should_interrupt=self.end_interrupt,
            think="",
            outputs=user_fields,
            output_mode=self.output_mode.value if self.output_mode else None,
            struct_answer=final_output,
        )

        # 写入 CustomSchema 以产出与 stream() 等价的流式事件
        # 当 End 使用 INVOKE 能力时，需要通过 CustomSchema 输出 message_end 和 workflow_end
        # 否则下游（如 WorkflowWrapper）无法收到这些流式事件
        # 批处理模式不应有 PARTIAL_CONTENT
        await session.write_custom_stream(
            CustomSchema(type="message_end", index=1, data=result_with_think)
        )
        await session.write_custom_stream(
            CustomSchema(type="workflow_end", index=2, data=result_without_think)
        )

        # 写入最终输出到缓存
        self._stream_output = self._build_final_output(
            answer=struct_answer_str if struct_answer_str else final_output,
            node_id=node_id,
            struct_answer=final_output,
            user_fields=user_fields,
        )

        # mix 模式：通知另一方渲染已完成
        if _mix_i_am_renderer and self._mix_condition is not None:
            async with self._mix_condition:
                self._mix_render_complete = True
                self._mix_condition.notify_all()

        return result_with_think

    async def stream(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> AsyncGenerator[Output, None]:
        """
        增强的流式输出处理，支持生成器值和结构化输出。
        """
        # 幂等保护：End 节点在 wait_for_all=False 时可能被 Pregel 引擎多次触发
        if self._stream_executed:
            return
        self._stream_executed = True

        # 处理输入中的生成器值
        outputs = {}
        if inputs and isinstance(inputs, dict):
            # 构建输出到输入的映射，防止重复消费流式数据
            if inputs.get(USER_FIELDS):
                inputs = inputs[USER_FIELDS]
            gen_out_to_in = build_output_to_input(inputs)

            # 按照 userFields.inputs schema 对输入值做类型强转
            self._apply_type_conversion(inputs)

            # 处理生成器值
            inputs = await process_generator_values_of_output(
                inputs=inputs, out_to_in=gen_out_to_in, workflow_streaming_data=None
            )

            outputs = {
                k[len(OUTPUT_PREFIX) :]: v
                for k, v in inputs.items()
                if k.startswith(OUTPUT_PREFIX) and v is not None
            }
            # 移除输出数据标记
            _remove_output_data(inputs)

        # mix 模式协调
        inputs, outputs, _mix_i_am_renderer = await self._mix_coordinate(
            "batch", inputs, outputs
        )
        if not _mix_i_am_renderer:
            return

        # 调用父类的stream方法获取结果，并保存响应内容
        response_parts = []
        inner_session = getattr(session, "_inner", None)
        node_id = (
            getattr(inner_session.state(), "_node_id", None) if inner_session else None
        )
        query = session.get_global_state("query") or ""
        user_fields = {**inputs, **outputs, **{"query": query}}
        last_end_node_stream = None
        first_end_node_stream = True
        async for output in super().stream(inputs, session, context):
            # 保存响应内容
            last_end_node_stream = output
            # 处理 OutputSchema 类型输出（有 type 和 index 属性）
            if (
                hasattr(output, "type")
                and hasattr(output, "payload")
                and "response" in output.payload
            ):
                response_parts.append(output.payload["response"])
                # 构建输出结果
                result = get_output_data_with_metadata(
                    answer=output.payload["response"],
                    node_id=node_id,
                    node_name=self.node_name or node_id,
                    node_type=self.node_type,
                    should_interrupt=self.end_interrupt,
                    outputs=user_fields,
                    output_mode=self.output_mode.value if self.output_mode else None,
                    struct_answer="",
                )
                if first_end_node_stream:
                    # 当模板以 {{...}} 开头时，旧框架 split 首元素为空字符串，
                    # 会作为 PARTIAL_CONTENT(answer="") 发送，充当流式起始标记
                    if self._should_emit_start_marker():
                        empty_result = get_output_data_with_metadata(
                            answer="",
                            node_id=node_id,
                            node_name=self.node_name,
                            node_type=self.node_type,
                            should_interrupt=self.end_interrupt,
                            outputs=user_fields,
                            output_mode=self.output_mode.value
                            if self.output_mode
                            else None,
                            struct_answer="",
                        )
                        yield OutputSchema(
                            type="end node stream", index=0, payload=empty_result
                        )
                    first_end_node_stream = False
                yield OutputSchema(
                    type=output.type, index=output.index + 1, payload=result
                )
            else:
                yield OutputSchema(
                    type=output.get("type", "end node stream"),
                    index=output.get("index", 0) + 1,
                    payload=output,
                )
        if last_end_node_stream:
            # 当模板以 {{...}} 结尾时，旧框架 split 末元素为空字符串，
            # 会作为 PARTIAL_CONTENT(answer="") 发送，充当流式结束标记
            if self._should_emit_end_marker():
                empty_result = get_output_data_with_metadata(
                    answer="",
                    node_id=node_id,
                    node_name=self.node_name,
                    node_type=self.node_type,
                    should_interrupt=self.end_interrupt,
                    outputs=user_fields,
                    output_mode=self.output_mode.value if self.output_mode else None,
                    struct_answer="",
                )
                yield OutputSchema(
                    type="end node stream",
                    index=last_end_node_stream.index + 2,
                    payload=empty_result,
                )

        # 添加结束节点最后的finish事件，带有完整的workflow输出信息
        if len(response_parts) == 1 and not isinstance(response_parts[0], str):
            response_value = response_parts[0]
        else:
            response_value = "".join(str(p) for p in response_parts)

        # 处理结构化输出：渲染模板得到 JSON 字符串
        struct_answer_str = ""
        if self.enable_struct_message and self.struct_output_template:
            struct_answer_str = self._format_struct_answer(
                response_value,
                self.struct_output_template,
                inputs if isinstance(inputs, dict) else {},
            )

        workflow_output = {
            "response": response_value,
            "struct_answer": struct_answer_str
            if (self.enable_struct_message and self.struct_output_template)
            else None,
        }

        # 从 inputs 中提取 reasoning_content（think）
        think_content = inputs.get("_reasoning_content", "")
        if not think_content:
            # 检查 outputs 中是否有 reasoning_content
            for k, v in outputs.items():
                if k == "reasoning_content" and isinstance(v, str):
                    think_content = v
                    break

        # 构建最终输出结果
        inner_session = getattr(session, "_inner", None)
        node_id = (
            getattr(inner_session.state(), "_node_id", None) if inner_session else None
        )
        query = session.get_global_state("query") or ""
        user_fields = {**inputs, **outputs, **{"query": query}}

        # 构建带有 think 的 result（用于 message_end）
        result_with_think = get_output_data_with_metadata(
            answer=struct_answer_str
            if struct_answer_str
            else workflow_output["response"],
            node_id=node_id,
            node_name=self.node_name,
            node_type=self.node_type,
            should_interrupt=self.end_interrupt,
            think=think_content,
            outputs=user_fields,
            output_mode=self.output_mode.value if self.output_mode else None,
            struct_answer=workflow_output["response"],
        )

        # 构建不带 think 的 result（用于 workflow_end）
        result_without_think = get_output_data_with_metadata(
            answer=struct_answer_str
            if struct_answer_str
            else workflow_output["response"],
            node_id=node_id,
            node_name=self.node_name,
            node_type=self.node_type,
            should_interrupt=self.end_interrupt,
            think="",
            outputs=user_fields,
            output_mode=self.output_mode.value if self.output_mode else None,
            struct_answer=workflow_output["response"],
        )

        # 发送事件 - message_end 带有 think，workflow_end 不带 think
        yield OutputSchema(type="message_end", index=0, payload=result_with_think)
        yield OutputSchema(type="workflow_end", index=1, payload=result_without_think)

        # 写入最终输出到缓存
        self._stream_output = self._build_final_output(
            answer=struct_answer_str
            if struct_answer_str
            else workflow_output["response"],
            node_id=node_id,
            struct_answer=workflow_output["response"],
            user_fields=user_fields,
        )

        # mix 模式：通知另一方渲染已完成
        if _mix_i_am_renderer and self._mix_condition is not None:
            async with self._mix_condition:
                self._mix_render_complete = True
                self._mix_condition.notify_all()

    async def collect(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        """
        流式输入聚合为批量输出（与 invoke 模式一致）。
        """
        # 幂等保护：End 节点在 wait_for_all=False 时可能被 Pregel 引擎多次触发
        if self._collect_executed:
            return None
        self._collect_executed = True
        # 聚合流式输入
        collected_inputs = []
        outputs = {}
        if inputs and isinstance(inputs, dict):
            if inputs.get(USER_FIELDS):
                inputs = inputs[USER_FIELDS]
        if hasattr(inputs, "__aiter__"):
            async for input_chunk in inputs:
                collected_inputs.append(input_chunk)
            if len(collected_inputs) == 1:
                final_inputs = collected_inputs[0]
            elif len(collected_inputs) > 1:
                final_inputs = collected_inputs[-1]
            else:
                final_inputs = {}
        else:
            final_inputs = inputs

        # 处理输入中的生成器值（与 invoke 一致）
        if final_inputs and isinstance(final_inputs, dict):
            gen_out_to_in = build_output_to_input(final_inputs)
            final_inputs = await process_generator_values_of_output(
                inputs=final_inputs,
                out_to_in=gen_out_to_in,
                workflow_streaming_data=None,
            )
            outputs = {
                k[len(OUTPUT_PREFIX) :]: v
                for k, v in final_inputs.items()
                if k.startswith(OUTPUT_PREFIX) and v is not None
            }
            _remove_output_data(final_inputs)

        # mix 模式协调
        final_inputs, outputs, _mix_i_am_renderer = await self._mix_coordinate(
            "stream", final_inputs, outputs
        )
        if not _mix_i_am_renderer:
            return None

        # 调用父类的collect方法获取结果（与 invoke 一致）
        response = await super().collect(final_inputs, session, context)

        # 提取原始文本输出
        final_output = (
            str(response)
            if not isinstance(response, dict)
            else response.get("response", "")
        )

        # 处理结构化输出：渲染模板得到 JSON 字符串
        struct_answer_str = ""
        if self.enable_struct_message and self.struct_output_template:
            struct_answer_str = self._format_struct_answer(
                final_output,
                self.struct_output_template,
                {**final_inputs, **response.get("output", {})},
            )
            if "output" not in response:
                response["output"] = {}
            response["output"]["struct_answer"] = struct_answer_str

        # 从 inputs 中提取 reasoning_content（think）
        think_content = final_inputs.get("_reasoning_content", "")
        if not think_content:
            # 检查 outputs 中是否有 reasoning_content
            for k, v in outputs.items():
                if k == "reasoning_content" and isinstance(v, str):
                    think_content = v
                    break

        # 构建最终输出结果
        inner_session = getattr(session, "_inner", None)
        node_id = getattr(inner_session.state(), "_node_id", None)
        query = session.get_global_state("query") or ""
        user_fields = {**final_inputs, **outputs, **{"query": query}}

        # 构建带有 think 的 result（用于 message_end）
        result_with_think = get_output_data_with_metadata(
            answer=struct_answer_str if struct_answer_str else final_output,
            node_id=node_id,
            node_name=self.node_name,
            node_type=self.node_type,
            should_interrupt=self.end_interrupt,
            think=think_content,
            outputs=user_fields,
            output_mode=self.output_mode.value if self.output_mode else None,
            struct_answer=final_output,
        )

        # 构建不带 think 的 result（用于 workflow_end）
        result_without_think = get_output_data_with_metadata(
            answer=struct_answer_str if struct_answer_str else final_output,
            node_id=node_id,
            node_name=self.node_name,
            node_type=self.node_type,
            should_interrupt=self.end_interrupt,
            think="",
            outputs=user_fields,
            output_mode=self.output_mode.value if self.output_mode else None,
            struct_answer=final_output,
        )

        # 写入 CustomSchema 以产出流式事件（与 invoke 一致）
        await session.write_custom_stream(
            CustomSchema(type="message_end", index=1, data=result_with_think)
        )
        await session.write_custom_stream(
            CustomSchema(type="workflow_end", index=2, data=result_without_think)
        )

        # 写入最终输出到缓存
        self._stream_output = self._build_final_output(
            answer=struct_answer_str if struct_answer_str else final_output,
            node_id=node_id,
            struct_answer=final_output,
            user_fields=user_fields,
        )

        # mix 模式：通知另一方渲染已完成
        if _mix_i_am_renderer and self._mix_condition is not None:
            async with self._mix_condition:
                self._mix_render_complete = True
                self._mix_condition.notify_all()

        return result_with_think

    @staticmethod
    async def _wrap_async_generator(gen, var_name: str, fill_count: int = 0):
        """将 async generator 每条 yield 值用 {var_name: value} 包裹；若生成器为空则补 fill_count 个 None"""
        has_value = False
        async for item in gen:
            has_value = True
            yield {var_name: item}
        if not has_value and fill_count > 0:
            for _ in range(fill_count):
                yield {var_name: None}

    def _wrap_template_variable_values(self, inputs: dict, fill_count: int = 0) -> None:
        """将模板变量的值用 {var_name: value} 格式包裹，使流式输出 answer 携带变量名"""
        if self._template is None or not isinstance(inputs, dict):
            return
        for i in self._template._variables_positions:
            var_name = self._template._segments[i]
            if var_name not in inputs:
                continue
            value = inputs[var_name]
            if inspect.isasyncgen(value) or hasattr(value, "__aiter__"):
                inputs[var_name] = self._wrap_async_generator(
                    value, var_name, fill_count
                )
            else:
                inputs[var_name] = {var_name: value}

    async def transform(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> AsyncGenerator[Output, None]:
        """
        流式输入输出转换（真流式实现）。
        流式输入通过 super().transform() 逐帧处理，普通内容帧即时 yield；
        每帧后检查中断状态，若中断则立即停止，不发送 message_end/workflow_end 等结束帧。
        """
        # 幂等保护：End 节点在 wait_for_all=False 时可能被 Pregel 引擎多次触发
        if self._transform_executed:
            return
        self._transform_executed = True

        # 开始时清空缓存
        self._reset_stream_output()

        # 提取上游节点的流式 metadata（由 FlowApi/FlowMcp 在 yield 中附带）
        # 流式连接下 __stream_metadata__ 会被引擎包装为 AsyncGenerator，需消费取最后一帧
        stream_metadata = None
        _meta_count = 0
        if inputs and isinstance(inputs, dict):
            if inputs.get(USER_FIELDS):
                inputs = inputs[USER_FIELDS]
        _raw_meta = inputs.pop("__stream_metadata__", None) if isinstance(inputs, dict) else None
        if isinstance(_raw_meta, AsyncGenerator):
            _last_meta = None
            async for _meta_item in _raw_meta:
                _last_meta = _meta_item
                _meta_count += 1
            stream_metadata = _last_meta
        else:
            stream_metadata = _raw_meta

        # finish 模式：上游最后一帧是聚合结果，消费生成器并按帧数决定是否丢弃最后一帧
        # 只有帧数 == metadata 帧数的生成器才包含聚合帧（引擎对部分嵌套字段路由不到聚合帧）
        _is_finish = (
            isinstance(stream_metadata, dict)
            and stream_metadata.get("messages_type") == "finish"
        )
        if _is_finish and inputs and isinstance(inputs, dict):
            for k, v in list(inputs.items()):
                if isinstance(v, AsyncGenerator):
                    inputs[k] = _skip_last_generator(v, _meta_count)

        # 处理输入中的生成器值：包装为可中断的流式生成器（真流式，不预消费）
        outputs = {}
        _resolved_generators = {}
        # 声明为输出（#end_ 前缀）且由生成器喂入的字段名（去除前缀），
        # 消费后需用解析值回填 outputs。引擎可能把 X 与 #end_X 路由成同一生成器，
        # 也可能路由成两个独立生成器，故回填时两处都要查。
        _declared_output_names = []
        _reasoning_content = ""
        _reasoning_ref = {"value": _reasoning_content}
        if inputs and isinstance(inputs, dict):
            self._apply_type_conversion(inputs)

            # 按生成器 id 分组：同一 AsyncGenerator 可能被多个键引用（answer/#end_answer）
            gen_to_keys = {}
            for k, v in inputs.items():
                if k == "reasoning_content" and isinstance(v, str):
                    _reasoning_content = v
                    _reasoning_ref["value"] = v
                if isinstance(v, AsyncGenerator):
                    gen_to_keys.setdefault(id(v), []).append(k)

            # 将所有 AsyncGenerator 包装为可中断生成器，多键引用共享同一包装实例
            for gen_id, keys in gen_to_keys.items():
                primary_key = next((x for x in keys if not x.startswith(OUTPUT_PREFIX)), keys[0])
                end_keys = [x for x in keys if x.startswith(OUTPUT_PREFIX)]
                gen = inputs[primary_key]

                def make_callback(primary_key, end_keys, is_reasoning):
                    def _cb(result):
                        _resolved_generators[primary_key] = result
                        for ek in end_keys:
                            _resolved_generators[ek] = result
                        if is_reasoning:
                            _reasoning_ref["value"] = result
                    return _cb

                is_reasoning = primary_key == "reasoning_content" or any("reasoning_content" in ek for ek in end_keys)
                _on_complete = make_callback(primary_key, end_keys, is_reasoning)
                wrapped = _interruptible_generator(
                    gen, session, self._is_workflow_interrupted,
                    on_complete=_on_complete,
                )
                inputs[primary_key] = wrapped
                for ek in end_keys:
                    inputs[ek] = wrapped

            # 提取 outputs 中的非生成器值（输出字段以 #end_ 前缀标识）
            outputs = {
                k[len(OUTPUT_PREFIX) :]: v
                for k, v in inputs.items()
                if k.startswith(OUTPUT_PREFIX) and v is not None and not isinstance(v, AsyncGenerator)
            }
            _gen_output_keys = [
                x for x in inputs.keys()
                if x.startswith(OUTPUT_PREFIX) and isinstance(inputs[x], AsyncGenerator)
            ]
            for k in _gen_output_keys:
                outputs[k[len(OUTPUT_PREFIX):]] = ""
            _declared_output_names = [k[len(OUTPUT_PREFIX):] for k in _gen_output_keys]
            _remove_output_data(inputs)

        # mix 模式协调
        inputs, outputs, _mix_i_am_renderer = await self._mix_coordinate(
            "stream", inputs, outputs
        )
        if not _mix_i_am_renderer:
            return

        # 从 __stream_metadata__ 中判断上游节点类型，决定是否需要 wrap answer
        _should_wrap = (
            isinstance(stream_metadata, dict)
            and stream_metadata.get("node_id") == "node_plugin"
        )

        # 仅当上游 node_id 为 node_plugin 时，包裹模板变量值使流式 answer 携带变量名
        if _should_wrap and isinstance(inputs, dict):
            self._wrap_template_variable_values(inputs, max(_meta_count - 1, 0))

        # 在 _wrap 之后保存干净的输入值（排除 AsyncGenerator，用于构建 user_fields）
        if isinstance(inputs, dict):
            clean_input_values = {
                k: v for k, v in inputs.items()
                if not inspect.isasyncgen(v) and not hasattr(v, "__aiter__")
            }
        else:
            clean_input_values = {}
        response_parts = []
        inner_session = getattr(session, "_inner", None)
        node_id = (
            getattr(inner_session.state(), "_node_id", None) if inner_session else None
        )
        query = session.get_global_state("query") or ""
        user_fields = {**clean_input_values, **outputs, **{"query": query}}

        first_end_node_stream = True
        last_output_index = 0
        interrupted = False
        last_stream_output = None

        # 逐帧消费父类输出，即时 yield（真流式），每帧后检查中断状态
        async for output in super().transform(inputs, session, context):
            # 每帧检查中断状态，若中断立即停止
            if self._is_workflow_interrupted(session):
                interrupted = True
                break

            # 处理 OutputSchema 类型输出（有 type 和 payload 属性，包含 response 字段）
            if _has_response_payload(output):
                response_parts.append(output.payload["response"])
                result = get_output_data_with_metadata(
                    answer=output.payload["response"],
                    node_id=node_id,
                    node_name=self.node_name,
                    node_type=self.node_type,
                    should_interrupt=self.end_interrupt,
                    outputs=user_fields,
                    output_mode=self.output_mode.value if self.output_mode else None,
                    struct_answer="",
                )
                if first_end_node_stream:
                    first_end_node_stream = False
                    # 当模板以 {{...}} 开头时，旧框架 split 首元素为空字符串，
                    # 会作为 PARTIAL_CONTENT(answer="") 发送，充当流式起始标记
                    if self._should_emit_start_marker():
                        empty_result = get_output_data_with_metadata(
                            answer="",
                            node_id=node_id,
                            node_name=self.node_name,
                            node_type=self.node_type,
                            should_interrupt=self.end_interrupt,
                            outputs=user_fields,
                            output_mode=self.output_mode.value
                            if self.output_mode
                            else None,
                            struct_answer="",
                        )
                        yield OutputSchema(
                            type="end node stream", index=0, payload=empty_result
                        )
                out_schema = OutputSchema(
                    type=output.type, index=output.index + 1, payload=result
                )
                last_output_index = output.index + 1
                last_stream_output = out_schema
                yield out_schema
            # 处理 dict 类型输出（父类无模板时返回的格式）
            elif isinstance(output, dict):
                # 提取 output 中的值作为响应内容
                if "output" in output:
                    output_data = output["output"]
                    if isinstance(output_data, dict):
                        for value in output_data.values():
                            response_parts.append(str(value))
                    else:
                        response_parts.append(str(output_data))
                output_index = output.get("index", 0)
                dict_schema = OutputSchema(
                    type="end node stream", index=output_index + 1, payload=output
                )
                last_output_index = output_index + 1
                last_stream_output = dict_schema
                yield dict_schema
            # 其他类型输出（兜底处理）
            else:
                other_type = getattr(output, "type", "end node stream")
                other_index = getattr(output, "index", 0)
                other_schema = OutputSchema(
                    type=other_type, index=other_index + 1, payload=output
                )
                last_output_index = other_index + 1
                last_stream_output = other_schema
                yield other_schema

        # 流式数据消费完毕后，检查中断状态，碰到中断时不执行 end 的流程
        if interrupted or self._is_workflow_interrupted(session):
            workflow_logger.info(
                "End transform skipped due to workflow interrupt (true streaming)",
                event_type=LogEventType.WORKFLOW_COMPONENT_END,
                component_id=session.get_component_id(),
                component_type_str="End",
                session_id=session.get_session_id(),
            )
            # mix 模式：通知另一方渲染已完成（即使中断也要通知，避免另一方死锁）
            if _mix_i_am_renderer and self._mix_condition is not None:
                async with self._mix_condition:
                    self._mix_render_complete = True
                    self._mix_condition.notify_all()
            return

        # 生成器消费完成后获取 reasoning_content 最终值
        _reasoning_content = _reasoning_ref["value"]

        # 将回调收集的生成器解析值合并回 outputs。
        # 回调故意只写入稳定的 _resolved_generators（不直接写 outputs）：outputs 之后会被
        # 重绑定（非生成器值字典推导）或在 mix 模式被 _mix_coordinate 替换为合并 dict，
        # 直接让回调写 outputs 会丢失这些值。这里在消费完成后显式合并到当前 outputs。
        # 引擎可能把输出变量 X 与 #end_X 路由为同一生成器（回调写入 #end_X），
        # 也可能路由为两个独立生成器（#end_X 的那个会被 _remove_output_data 移除而不消费，
        # 解析值落在主键 X 上），因此对每个声明输出两处都查。
        for _out_name in _declared_output_names:
            _resolved = _resolved_generators.get(OUTPUT_PREFIX + _out_name)
            if _resolved is None:
                _resolved = _resolved_generators.get(_out_name)
            if _resolved is not None:
                outputs[_out_name] = _resolved

        # 当模板以 {{...}} 结尾时，旧框架 split 末元素为空字符串，
        # 会作为 PARTIAL_CONTENT(answer="") 发送，充当流式结束标记
        if last_stream_output is not None and self._should_emit_end_marker():
            empty_result = get_output_data_with_metadata(
                answer="",
                node_id=node_id,
                node_name=self.node_name,
                node_type=self.node_type,
                should_interrupt=self.end_interrupt,
                outputs=user_fields,
                output_mode=self.output_mode.value if self.output_mode else None,
                struct_answer="",
            )
            yield OutputSchema(
                type="end node stream",
                index=last_output_index + 1,
                payload=empty_result,
            )

        # 将 reasoning_content 放回 inputs 供后续 think 字段构建使用
        if _reasoning_content and isinstance(inputs, dict):
            inputs["_reasoning_content"] = _reasoning_content

        # 拼接最终响应内容
        if len(response_parts) == 1 and not isinstance(response_parts[0], str):
            response_value = response_parts[0]
        else:
            response_value = "".join(str(p) for p in response_parts)

        # 处理结构化输出：从模板中提取变量名，然后用可用的数据填充
        template_vars = set()
        if self.struct_output_template:
            for match in _TEMPLATE_SPLIT_PATTERN.finditer(self.struct_output_template):
                var_name = match.group(1)[2:-2]  # 提取 {{var}} 中的 var
                if var_name:
                    template_vars.add(var_name)

        # 构建 inputs_for_struct：先添加非生成器的 inputs 值，再添加 user_fields，
        # 最后用 response_value 填充模板中引用但 inputs 和 user_fields 中不存在的变量
        inputs_for_struct = {}
        if isinstance(inputs, dict):
            for k, v in inputs.items():
                if not isinstance(v, AsyncGenerator):
                    inputs_for_struct[k] = v
        inputs_for_struct.update({**clean_input_values, **outputs})
        for var_name in template_vars:
            if var_name not in inputs_for_struct or inputs_for_struct.get(var_name) is None:
                inputs_for_struct[var_name] = response_value

        # 处理结构化输出
        struct_answer_str = ""
        if self.enable_struct_message and self.struct_output_template:
            struct_answer = {
                "struct_output_template": self.struct_output_template,
                "variables": inputs_for_struct,
            }
            yield OutputSchema(type="struct_output", index=0, payload=struct_answer)
            # 渲染结构化模板得到 JSON 字符串
            struct_answer_str = self._format_struct_answer(
                response_value,
                self.struct_output_template,
                inputs_for_struct,
            )

        workflow_output = {
            "response": response_value,
            "struct_answer": struct_answer_str if struct_answer_str else None,
        }

        # 从 inputs/outputs 中提取 reasoning_content（think 字段）
        think_content = ""
        if isinstance(inputs, dict):
            think_content = inputs.get("_reasoning_content", "")
        if not think_content:
            # 检查 outputs 中是否有 reasoning_content
            for k, v in outputs.items():
                if k == "reasoning_content" and isinstance(v, str):
                    think_content = v
                    break

        # 构建最终输出结果
        inner_session = getattr(session, "_inner", None)
        node_id = (
            getattr(inner_session.state(), "_node_id", None) if inner_session else None
        )
        query = session.get_global_state("query") or ""
        user_fields = {**clean_input_values, **outputs, **{"query": query}}

        # 构建带有 think 的 result（用于 message_end）
        result_with_think = get_output_data_with_metadata(
            answer=struct_answer_str
            if struct_answer_str
            else workflow_output["response"],
            node_id=node_id,
            node_name=self.node_name,
            node_type=self.node_type,
            should_interrupt=self.end_interrupt,
            think=think_content,
            outputs=user_fields,
            output_mode=self.output_mode.value if self.output_mode else None,
            struct_answer=workflow_output["response"],
        )

        # 构建不带 think 的 result（用于 workflow_end）
        result_without_think = get_output_data_with_metadata(
            answer=struct_answer_str
            if struct_answer_str
            else workflow_output["response"],
            node_id=node_id,
            node_name=self.node_name,
            node_type=self.node_type,
            should_interrupt=self.end_interrupt,
            think="",
            outputs=user_fields,
            output_mode=self.output_mode.value if self.output_mode else None,
            struct_answer=workflow_output["response"],
        )

        # 防御性检查：发送最终结束帧前再次确认未中断
        if self._is_workflow_interrupted(session):
            if _mix_i_am_renderer and self._mix_condition is not None:
                async with self._mix_condition:
                    self._mix_render_complete = True
                    self._mix_condition.notify_all()
            return

        yield OutputSchema(type="message_end", index=0, payload=result_with_think)
        yield OutputSchema(type="workflow_end", index=1, payload=result_without_think)

        # 写入最终输出到缓存
        self._stream_output = self._build_final_output(
            answer=struct_answer_str
            if struct_answer_str
            else workflow_output["response"],
            node_id=node_id,
            struct_answer=workflow_output["response"],
            user_fields=user_fields,
        )

        # mix 模式：通知另一方渲染已完成
        if _mix_i_am_renderer and self._mix_condition is not None:
            async with self._mix_condition:
                self._mix_render_complete = True
                self._mix_condition.notify_all()
