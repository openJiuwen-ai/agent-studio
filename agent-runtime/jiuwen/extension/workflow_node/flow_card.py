# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.

"""
FlowCard - 卡片节点组件

迁移自商用版本 flow_card.py，适配开源版本 openjiuwen Studio 框架。

功能特性:
- 模板渲染，返回格式化的卡片输出
- 支持流式/非流式输出模式
- 支持结构化输出 (struct_output_template)
- 输出模式控制
- 卡片输出收集与时间戳记录

设计说明:
- 直接继承 WorkflowComponent（单一继承）
- 通过 Session 管理状态（替代 runtime_context）
- 使用 TemplateProcessor 或简单字符串替换进行模板处理

迁移差异:
| 商用版本 | 开源版本 |
|---------|---------|
| 多重继承 Invokable + MessageComponentBase | 单一继承 WorkflowComponent |
| runtime_context 全局引用 | Session 状态管理 |
| jiuwen.prompt.Prompt/Template | TemplateProcessor 或简单替换 |
| JiuWenBaseException 异常 | workflow_logger 日志记录 |
"""

from __future__ import annotations

import datetime
from datetime import timezone, timedelta
from enum import Enum
from typing import Any, AsyncGenerator, AsyncIterator, Dict, Optional

from openjiuwen.core.common.logging import workflow_logger, LogEventType
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session.stream import OutputSchema
from openjiuwen.core.session.stream.base import CustomSchema
from openjiuwen.core.workflow import WorkflowComponent
from openjiuwen.core.workflow.components import Session
from openjiuwen.core.workflow.components.flow.end_comp import (
    TemplateProcessor,
    TemplateUtils,
)
from pydantic import BaseModel, Field, StrictStr

# =============================================================================
# 常量定义
# =============================================================================

# 卡片节点类型
JIUWEN_CARD_TYPE = "jiuwen.card"

# 配置字段名
CONFIG_TEMPLATE_KEYWORD = "template"

# 卡片输出存储键
CARD_OUTPUTS_KEY = "card_outputs"
PARTIAL_CONTENT = "partial_content"
MESSAGE_NODE_END = "message_end"
# 用户字段键
USER_FIELDS = "userFields"

# 北京时区
BJ_TZ = timezone(timedelta(hours=8), name="Asia/Beijing")


# =============================================================================
# 枚举定义
# =============================================================================


class OutputMode(Enum):
    """前端气泡展示方式枚举

    - SEPARATE: 独立展示
    - APPEND: 追加到上一个气泡
    - REPLACE: 替换上一个气泡
    """

    SEPARATE = "separate"
    APPEND = "append"
    REPLACE = "replace"

    @classmethod
    def from_str(cls, mode_str: Optional[str]) -> Optional["OutputMode"]:
        """从字符串创建枚举实例

        Args:
            mode_str: 输出模式字符串

        Returns:
            OutputMode 枚举实例，无效输入返回 None
        """
        if mode_str is None:
            return None
        try:
            return cls(mode_str.lower())
        except ValueError:
            workflow_logger.warning(
                f"Invalid output mode string: {mode_str}, using None",
            )
            return None


# =============================================================================
# 配置类
# =============================================================================


class FlowCardConfig(BaseModel):
    """FlowCard 组件配置

    对应商用版本 FlowCardComponentConfig，扩展了更多配置项。

    Attributes:
        template: 卡片模板内容（必填）
        output_mode: 输出模式
        event: 事件配置
        struct_output_template: 结构化输出模板
        enable_struct_message: 是否启用结构化消息
    """

    template: StrictStr = Field(
        ..., min_length=1, description="卡片模板内容，支持 {{variable}} 语法"
    )
    name: str = Field(default="卡片", min_length=1, description="节点名称")
    output_mode: Optional[str] = Field(
        default=None,
        alias="outputMode",
        description="输出模式: separate/append/replace",
    )
    event: Dict[str, Any] = Field(default_factory=dict, description="事件配置")
    struct_output_template: str = Field(
        default="", alias="structOutputTemplate", description="结构化输出模板"
    )
    enable_struct_message: bool = Field(
        default=False, alias="isStructMessage", description="是否启用结构化消息"
    )

    class Config:
        """Pydantic 配置"""

        populate_by_name = True


# =============================================================================
# 主组件类
# =============================================================================
class FlowCard(WorkflowComponent):
    """工作流卡片节点组件

    迁移自商用版本 FlowCard，适配开源版本框架。

    职责:
    1. 模板渲染，生成卡片内容
    2. 支持流式/批量输出模式
    3. 支持结构化输出
    4. 卡片输出收集与时间戳记录

    使用示例:
        config = FlowCardConfig(
            template="Hello, {{name}}! Your order #{{order_id}} is ready.",
            output_mode="separate"
        )
        flow_card = FlowCard(config)

        # 执行
        result = await flow_card.invoke(
            {"name": "Alice", "order_id": "12345"},
            session,
            context
        )

    状态管理:
    - 卡片输出存储在 Session 状态中，键为 "card_outputs"
    - 每次执行会将输出追加到该列表
    """

    # 节点类型标识
    NODE_TYPE = "card"

    def __init__(self, conf: FlowCardConfig):
        """初始化 FlowCard 组件

        Args:
            conf: 组件配置
        """
        super().__init__()
        self._config = conf

        # 解析输出模式
        self._output_mode = OutputMode.from_str(conf.output_mode)

        # 初始化模板处理器
        self._template_processor = self._init_template_processor(conf.template)

        # 检查是否为结束中断节点
        self._end_interrupt = self._check_end_interrupt(conf.event)

    # =========================================================================
    # 初始化辅助方法
    # =========================================================================

    def _init_template_processor(self, template_content: str):
        """初始化模板处理器

        优先使用 TemplateProcessor，如果不可用则降级为简单字符串替换。

        Args:
            template_content: 模板内容

        Returns:
            TemplateProcessor 实例或 None
        """
        try:
            return TemplateProcessor(template_content)
        except ImportError:
            workflow_logger.warning(
                "TemplateProcessor not available, fallback to simple string replacement",
            )
            return None
        except Exception as e:
            workflow_logger.warning(
                "Template processor init failed, fallback to simple replacement",
                exception=e,
            )
            return None

    def _check_end_interrupt(self, event: Dict[str, Any]) -> bool:
        """检查是否为结束中断节点

        Args:
            event: 事件配置

        Returns:
            是否为结束中断节点
        """
        if not event:
            return False

        event_type = event.get("type", "")
        # 商用版本中 TaskType.TASK_COMPLETION 会触发中断
        return event_type == "task_completion"

    # =========================================================================
    # 核心执行方法
    # =========================================================================

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        """批量输入输出模式

        执行流程:
        1. 提取用户字段
        2. 渲染模板
        3. 收集卡片输出到 Session
        4. 返回结果

        Args:
            inputs: 输入数据
            session: 工作流会话
            context: 模型上下文

        Returns:
            包含渲染结果的输出字典
        """
        try:
            # 1. 提取用户字段
            user_fields = self._extract_user_fields(inputs)

            # 2. 渲染模板
            rendered_output = self._render_template(user_fields)

            # 3. 收集卡片输出到 Session
            self._collect_card_output(rendered_output, session)

            # 4. 返回结果
            return {"result": rendered_output}

        except Exception as e:
            workflow_logger.error(
                "FlowCard invoke failed",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                component_id=session.get_component_id() if session else "",
                component_type_str=self.NODE_TYPE,
                session_id=session.get_session_id() if session else "",
                exception=e,
            )
            # 返回原始模板作为降级
            return {"result": self._config.template}

    async def stream(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> AsyncIterator[Output]:
        """批量输入，流式输出模式

        执行流程:
        1. 提取用户字段
        2. 渲染模板
        3. 处理结构化输出
        4. 流式返回结果
        5. 收集卡片输出

        Args:
            inputs: 输入数据
            session: 工作流会话
            context: 模型上下文

        Yields:
            流式输出块
        """
        try:
            # 1. 提取用户字段
            user_fields = self._extract_user_fields(inputs)

            # 2. 渲染模板
            rendered_output = self._render_template(user_fields)

            # 3. 处理结构化输出
            final_output = self._format_structured_output(rendered_output, user_fields)

            # 4. 流式返回结果
            if self._template_processor and hasattr(
                self._template_processor, "render_stream"
            ):
                # 使用模板处理器的流式渲染
                try:
                    timeout = self._get_stream_timeout(session)
                    generator = self._template_processor.render_stream(
                        user_fields, session, timeout=timeout
                    )
                    node_id = session.get_component_id()
                    node_name = self._config.name or node_id
                    async for frame in generator:
                        custom_data = {
                            "answer": frame.get("data", ""),
                            "result": frame.get("data", ""),
                            "node_id": node_id,
                            "node_name": node_name,
                            "node_type": JIUWEN_CARD_TYPE,
                            "should_interrupt": False,
                        }
                        yield OutputSchema(
                            type=self.NODE_TYPE,
                            index=frame.get("index"),
                            payload={"response": frame.get("data")},
                        )
                        await session.write_custom_stream(
                            CustomSchema(
                                type=PARTIAL_CONTENT, index=0, data=custom_data
                            )
                        )
                except Exception as stream_error:
                    workflow_logger.warning(
                        "Stream rendering failed, fallback to chunked output",
                        exception=stream_error,
                    )
                    # 降级为分块输出
                    async for chunk in self._chunked_stream(final_output):
                        yield chunk
            else:
                # 简单分块流式输出
                async for chunk in self._chunked_stream(final_output):
                    yield chunk

            # 5. 收集卡片输出
            self._collect_card_output(rendered_output, session)
            node_id = session.get_component_id()
            node_name = self._config.node_name or node_id
            custom_data = {
                "answer": rendered_output,
                "result": rendered_output,
                "node_id": node_id,
                "node_name": node_name,
                "node_type": JIUWEN_CARD_TYPE,
                "should_interrupt": False,
            }
            await session.write_custom_stream(
                CustomSchema(type=PARTIAL_CONTENT, index=0, data=custom_data)
            )
            await session.write_custom_stream(
                CustomSchema(type=MESSAGE_NODE_END, index=0, data=custom_data)
            )
        except Exception as e:
            workflow_logger.error(
                "FlowCard stream failed",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                component_id=session.get_component_id() if session else "",
                component_type_str=self.NODE_TYPE,
                session_id=session.get_session_id() if session else "",
                exception=e,
            )
            yield OutputSchema(
                type=self.NODE_TYPE,
                index=0,
                payload={"response": self._config.template},
            )

    # =========================================================================
    # 模板处理方法
    # =========================================================================

    def _render_template(self, variables: Dict[str, Any]) -> str:
        """渲染模板

        优先使用 TemplateProcessor，否则使用简单字符串替换。

        Args:
            variables: 模板变量

        Returns:
            渲染后的字符串
        """
        if not variables:
            variables = {}

        try:
            if self._template_processor:
                return self._template_processor.render(variables)
            else:
                # 简单模板替换降级方案
                return self._simple_template_replace(variables)
        except Exception as e:
            workflow_logger.error(
                "Card template rendering failed",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                exception=e,
            )
            # 降级返回原始模板
            return self._config.template

    def _simple_template_replace(self, variables: Dict[str, Any]) -> str:
        """简单模板替换

        支持 {{variable}} 语法。

        Args:
            variables: 模板变量

        Returns:
            替换后的字符串
        """
        result = self._config.template
        for key, value in variables.items():
            if value is not None:
                result = result.replace(f"{{{{{key}}}}}", str(value))
        return result

    # =========================================================================
    # 结构化输出处理
    # =========================================================================

    def _format_structured_output(
        self, origin_output: str, variables: Dict[str, Any]
    ) -> str:
        """格式化结构化输出

        Args:
            origin_output: 原始输出内容
            variables: 模板变量

        Returns:
            格式化后的结构化输出
        """
        if (
            not self._config.enable_struct_message
            or not self._config.struct_output_template
        ):
            return origin_output

        try:
            # 合并变量，添加默认占位符
            all_vars = {**(variables or {}), "_NODE_OUTPUT": origin_output}

            # 渲染结构化模板
            if self._template_processor and hasattr(
                self._template_processor, "render_with_template"
            ):
                return self._template_processor.render_with_template(
                    self._config.struct_output_template, all_vars
                )
            else:
                # 使用 TemplateUtils
                try:
                    return TemplateUtils.render_template(
                        self._config.struct_output_template, all_vars
                    )
                except ImportError:
                    # 简单替换
                    result = self._config.struct_output_template
                    for key, value in all_vars.items():
                        if value is not None:
                            result = result.replace(f"{{{{{key}}}}}", str(value))
                    return result

        except Exception as e:
            workflow_logger.warning(
                "Structured output rendering failed, using original output",
                exception=e,
            )
            return origin_output

    # =========================================================================
    # 卡片输出收集
    # =========================================================================

    def _collect_card_output(self, output: str, session: Session) -> None:
        """收集卡片输出到 Session 状态

        Args:
            output: 渲染后的输出内容
            session: 工作流会话
        """
        try:
            # 获取现有卡片输出列表
            card_outputs = session.get_global_state(CARD_OUTPUTS_KEY)
            if card_outputs is None or not isinstance(card_outputs, list):
                card_outputs = []

            # 追加新的卡片输出
            card_outputs.append(self._format_card_output(output))

            # 更新 Session 状态
            inner_session = getattr(session, "_inner", None)
            if not inner_session:
                return
            node_id = getattr(inner_session.state(), "_node_id", None)
            io_state = getattr(inner_session.state(), "_io_state")
            io_state.update_by_id(node_id, {CARD_OUTPUTS_KEY: card_outputs})
            inner_session.state().commit()

        except Exception as e:
            workflow_logger.error(
                "Failed to collect card output to session",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                exception=e,
            )

    def _format_card_output(self, output: str) -> Dict[str, Any]:
        """格式化卡片输出

        Args:
            output: 输出内容

        Returns:
            包含节点类型、输出内容和时间戳的字典
        """
        return {
            "node_type": self.NODE_TYPE,
            "output": output,
            "time_stamp": datetime.datetime.now(tz=BJ_TZ).isoformat(),
        }

    # =========================================================================
    # 辅助方法
    # =========================================================================

    def _extract_user_fields(self, inputs: Input) -> Dict[str, Any]:
        """从输入中提取用户字段

        Args:
            inputs: 输入数据

        Returns:
            用户字段字典
        """
        if inputs is None:
            return {}

        if isinstance(inputs, dict):
            # 如果有 userFields 键，提取它
            if USER_FIELDS in inputs:
                user_fields = inputs[USER_FIELDS]
                return user_fields if isinstance(user_fields, dict) else {}
            return inputs

        return {}

    def _get_stream_timeout(self, session: Session) -> float:
        """获取流式渲染超时配置

        Args:
            session: 工作流会话

        Returns:
            超时时间（秒）
        """
        try:
            return session.get_env("END_COMP_TEMPLATE_RENDER_POSITION_TIMEOUT_KEY", 0.2)
        except Exception:
            return 0.2

    async def _chunked_stream(self, content: str) -> AsyncIterator[OutputSchema]:
        """将内容分块流式输出

        Args:
            content: 要输出的内容

        Yields:
            流式输出块
        """
        # 按字符分块输出
        for i, char in enumerate(content):
            yield OutputSchema(type=self.NODE_TYPE, index=i, payload={"response": char})

    # =========================================================================
    # 属性访问器
    # =========================================================================

    @property
    def output_mode(self) -> Optional[OutputMode]:
        """获取输出模式"""
        return self._output_mode

    @property
    def end_interrupt(self) -> bool:
        """获取是否为结束中断节点"""
        return self._end_interrupt

    @property
    def resolved_node_type(self) -> str:
        """获取节点类型（与 NODE_TYPE 常量区分，避免静态分析字段/方法同名冲突）"""
        return self.NODE_TYPE

    @property
    def node_type(self) -> str:
        """兼容旧属性名；新代码请使用 resolved_node_type。"""
        return self.resolved_node_type

    @property
    def config(self) -> FlowCardConfig:
        """获取配置"""
        return self._config

    # =========================================================================
    # 流式输入方法（collect / transform）
    # =========================================================================

    async def collect(
        self,
        inputs: Input,
        session: Session,
        context: ModelContext,
    ) -> Output:
        """
        流式输入聚合为批量输出。

        旧框架中 Card 在 _pre_process 被豁免生成器预解析（与 End、Message 同组），
        直接接收上游组件（如 LLM）的 AsyncGenerator 输出。
        此方法将流式输入聚合后委托给 invoke() 进行模板渲染。
        """
        resolved = await self._resolve_stream_inputs(inputs)
        return await self.invoke(resolved, session, context)

    async def transform(
        self,
        inputs: Input,
        session: Session,
        context: ModelContext,
    ) -> AsyncIterator[Output]:
        """
        流式输入转换为流式输出。

        当 Card 同时作为流式接收端和流式发送端时
        （如 LLM → Card → End(isStreamOut)），
        auto_complete_abilities 授予 TRANSFORM 能力。
        此方法聚合流式输入后委托给 stream() 产出流式输出。
        """
        resolved = await self._resolve_stream_inputs(inputs)
        async for output in self.stream(resolved, session, context):
            yield output

    @staticmethod
    async def _resolve_stream_inputs(inputs: Input) -> Dict[str, Any]:
        """
        将 inputs 中的 AsyncGenerator 值解析为最终内容。

        当上游组件（如 LLM）通过流式连接输出时，inputs 中对应的变量值
        是 AsyncGenerator 对象。此方法迭代所有 AsyncGenerator 并聚合为最终文本。
        """
        if inputs is None:
            return {}
        if not isinstance(inputs, dict):
            if hasattr(inputs, "__aiter__"):
                collected = []
                async for chunk in inputs:
                    if isinstance(chunk, dict):
                        collected.append(chunk)
                if not collected:
                    return {}
                return collected[-1] if len(collected) > 1 else collected[0]
            return {}
        resolved = {}
        for key, value in inputs.items():
            if isinstance(value, AsyncGenerator):
                chunks = []
                async for frame in value:
                    if isinstance(frame, str):
                        chunks.append(frame)
                    elif isinstance(frame, dict):
                        resp = frame.get("response", frame.get("answer", ""))
                        if resp:
                            chunks.append(str(resp))
                    else:
                        chunks.append(str(frame))
                resolved[key] = "".join(chunks)
            else:
                resolved[key] = value
        return resolved


# =============================================================================
# 兼容性适配器（可选）
# =============================================================================


class FlowCardRuntimeContextAdapter:
    """RuntimeContext 适配器

    用于兼容旧代码中通过 runtime_context 访问卡片输出的场景。
    新代码应直接使用 Session 状态管理。

    使用示例:
        adapter = FlowCardRuntimeContextAdapter(session)
        card_outputs = adapter.get("card_outputs")
    """

    def __init__(self, session: Session):
        """初始化适配器

        Args:
            session: 工作流会话
        """
        self._session = session

    def get(self, key: str) -> Any:
        """获取状态值

        Args:
            key: 状态键

        Returns:
            状态值
        """
        return self._session.get_global_state(key)

    def set(self, key: str, value: Any) -> None:
        """设置状态值

        Args:
            key: 状态键
            value: 状态值
        """
        inner_session = getattr(self._session, "_inner", None)
        if not inner_session:
            return
        node_id = getattr(inner_session.state(), "_node_id", None)
        io_state = getattr(inner_session.state(), "_io_state")
        io_state.update_by_id(node_id, {key: value})
        inner_session.state().commit()


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    # 主类
    "FlowCard",
    "FlowCardConfig",
    # 枚举
    "OutputMode",
    # 适配器
    "FlowCardRuntimeContextAdapter",
    # 常量
    "CARD_OUTPUTS_KEY",
    "USER_FIELDS",
    "BJ_TZ",
]
