#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from jiuwen.common.intent_detection.config import MultiLayerIntentDetectionConfig
from jiuwen.context.base import ContextConfig
from jiuwen.context.memory_engine.config.memory_ir_config import MemoryIrConfig
from jiuwen.controller.common.constants import DEFAULT_USER_PROMPT
from jiuwen.controller.common.enum import (
    HandlerType,
    ActionAfterCompletionType,
    IntentIdentificationMethod,
)
from jiuwen.prompt import Template
from pydantic import BaseModel, Field


@dataclass
class IntentConfig:
    """意图配置类"""

    name: Optional[str] = None
    intent_id: Optional[str] = None
    description: Optional[str] = None
    handler_type: HandlerType = None
    handler: Any = None
    termination: bool = False
    action_after_completion: ActionAfterCompletionType = (
        ActionAfterCompletionType.WAITING_USER_INPUT
    )


@dataclass
class BasePlanConfig:
    """基础规划配置类，包含共同字段"""

    task_id: str
    # 规划模式
    plan_mode: Optional[str] = None
    # 最大迭代次数
    max_iterations: int = 20
    # 模型
    model: Optional[Any] = None
    # 最大对话轮次
    chat_history_max_turn: int = 20


@dataclass
class ConstrainConfig:
    """配置规划约束参数"""

    max_iteration: int = 10


@dataclass
class OperatorConfig:
    """配置规划操作符参数"""

    prompt_template_name: Optional[str] = None
    is_chat: bool = False
    reserved_max_chat_rounds: int = 10
    operator_name: Optional[str] = None


def parse_config(input_dict: Dict[str, Any]):
    """从配置字典构建ReactConfig实例

    Args:
        input_dict (Dict[str, Any]): 配置字典，包含任务ID、规划模式、工作流、插件、模型等配置

    Returns:
        tuple: (base_config, propose_next_config, constrain_config) 配置元组
    """
    base_config = {}
    base_config["task_id"] = input_dict["task_id"]
    if "plan_mode" in input_dict:
        base_config["plan_mode"] = input_dict["plan_mode"]
    if "workflows" in input_dict:
        base_config["workflows"] = input_dict["workflows"]
    if "plugins" in input_dict:
        base_config["plugins"] = input_dict["plugins"]
    if "model" in input_dict:
        base_config["model"] = input_dict["model"]

    constrain_config = None
    if "constrain" in input_dict:
        constrain_value = input_dict["constrain"]
        constrain_config = ConstrainConfig(**constrain_value)
        if "max_iteration" in constrain_value:
            base_config["max_iterations"] = constrain_value["max_iteration"]

    propose_next_config = None
    if "propose_next" in input_dict:
        propose_next_config = OperatorConfig(**input_dict["propose_next"])

    return base_config, propose_next_config, constrain_config


@dataclass
class ReactConfig(BasePlanConfig):
    """反应式规划引擎的配置类，封装规划引擎初始化参数"""

    # 下一步配置
    propose_next_config: Optional[OperatorConfig] = None
    # 约束配置
    constrain_config: ConstrainConfig = field(default_factory=ConstrainConfig)
    # 是否启用工作流切换
    workflow_switch_enable: Optional[bool] = None
    # 输入变量
    input_variables: List[dict] = field(default_factory=list)

    @classmethod
    def from_config_dict(cls, input_dict: Dict[str, Any]):
        """从配置字典构建ReactConfig实例

        Args:
            input_dict (Dict[str, Any]): 配置字典

        Returns:
            ReactConfig: 反应式规划引擎配置实例
        """
        base_config, propose_next_config, constrain_config = parse_config(input_dict)
        workflow_switch_enable = input_dict.get("workflow_switch_enable")
        return cls(
            **base_config,
            propose_next_config=propose_next_config,
            constrain_config=constrain_config,
            workflow_switch_enable=workflow_switch_enable,
        )


@dataclass
class ToolUseConfig(BasePlanConfig):
    """规划执行引擎的配置类，封装规划执行引擎初始化参数"""

    execute_config: ReactConfig = None
    execute_type: str = "ToolUse"
    propose_next_config: Optional[OperatorConfig] = None
    constrain_config: ConstrainConfig = field(default_factory=ConstrainConfig)

    @classmethod
    def from_config_dict(cls, input_dict: Dict[str, Any]):
        """从配置字典构建ToolUseConfig实例

        Args:
            input_dict (Dict[str, Any]): 配置字典

        Returns:
            ToolUseConfig: 规划执行引擎配置实例
        """
        base_config, propose_next_config, constrain_config = parse_config(input_dict)
        return cls(
            **base_config,
            propose_next_config=propose_next_config,
            constrain_config=constrain_config,
        )


class IntentDetectionConfig(BaseModel):
    """config of Intent Detection Component"""

    category_info: str = Field(default="")
    category_list: list[str] = Field(default_factory=list)
    intent_detection_template: Template
    user_prompt: str = Field(default=DEFAULT_USER_PROMPT)
    chat_history_max_turn: int = Field(default=100)
    default_class: str = Field(default="分类0")
    enable_history: bool = Field(default=False)
    enable_input: bool = Field(default=True)
    example_content: list[str] = Field(default_factory=list)


@dataclass
class IntentIdentificationConfig:
    """意图识别配置主结构"""

    method: IntentIdentificationMethod = None
    id: Optional[str] = None
    threshold: float = Field(default=0.0)
    # 多级意图配置
    enable_multi_layer_detection: bool = Field(default=False)
    multi_layer_id_cfg: Optional[MultiLayerIntentDetectionConfig] = None


@dataclass
class ControllerConfig(BasePlanConfig):
    """控制器配置类，封装控制器初始化参数"""

    # 开始工作流
    start_workflow: Optional[Any] = None
    # 结束工作流
    end_workflow: Optional[Any] = None
    # 全局意图
    global_intents: List[Any] = field(default_factory=list)
    # 全局变量
    global_variables: List[dict] = field(default_factory=list)
    # 输入变量
    input_variables: List[dict] = field(default_factory=list)
    # 全局workflow实例
    global_workflows: List[Any] = field(default_factory=list)
    # 默认workflow实例
    default_workflow: Optional[Any] = None
    # 是否指定工作流顺序
    specify_workflow_order: bool = False
    # user_prompt
    user_prompt: str = Field(default=DEFAULT_USER_PROMPT)
    # 意图识别方式
    intent_identification: Optional[IntentIdentificationConfig] = None
    metadata: Any = None
    parent_agent_metadata: Optional[Any] = None
    child_agents_metadata: List[Any] = None


@dataclass
class ControlModeConfig:
    """控制器配置类，封装控制器初始化参数"""

    task_id: str = None
    # 上下文管理器
    context_manager: Optional[Any] = None
    # 开始工作流
    start_workflow: Optional[Any] = None
    # 结束工作流
    end_workflow: Optional[Any] = None
    # workflow 实例
    workflows: List = field(default_factory=list)
    global_workflows: List[Any] = field(default_factory=list)
    # 全局意图
    global_intents: List[Any] = field(default_factory=list)
    # 全局变量
    global_variables: List[dict] = field(default_factory=list)
    # 输入变量
    input_variables: List[dict] = field(default_factory=list)
    # 各种插件类型
    plugins: Any = None
    # BaseModel
    model: Any = None
    # ReActConfig | ControllerConfig
    plan_config: Any = None


@dataclass
class WorkflowConfig:
    workflow_ir: dict = field(default_factory=dict)
    action_after_completion: ActionAfterCompletionType = None
    config_name: str = None
    config_description: str = None
    intent_name: str = None
    intent_description: str = None
    arguments: List[Any] = field(default_factory=list)
    input_parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentMetaData:
    id: str = None
    name: str = None
    description: str = None
    intent_name: str = None
    intent_description: str = None
    ir_path: str = None
    mode: str = "Controller"


@dataclass
class AgentConfig:
    """Agent配置类，用于封装Agent初始化参数"""

    model: Any = None  # BaseModel
    task_id: str = None
    agent_id: str = None
    plan_config: Any = None  # ReActConfig | ControllerConfig
    plugins: Any = None  # 各种插件类型
    # workflow 实例
    workflows: List = field(default_factory=list)
    # 开始工作流
    start_workflow: Optional[Any] = None
    # 结束工作流
    end_workflow: Optional[Any] = None
    # 默认工作流
    default_workflow: Optional[Any] = None
    # 全局工作流
    global_workflows: List[Any] = field(default_factory=list)
    # 用户提示词
    user_prompt: str = None
    # 意图识别方式
    intent_identification: Optional[IntentIdentificationConfig] = None
    # 意图识别方式
    intent_workflows: List[Any] = None
    metadata: AgentMetaData = field(default_factory=AgentMetaData)
    parent_agent_metadata: Optional[AgentMetaData] = None
    child_agents_metadata: List[AgentMetaData] = field(default_factory=list)
    # ir_path，用于agent示例缓存
    ir_path: str = None
    # is_published，记录agent是否已发布
    is_published: bool = False
    # context engine config
    context: ContextConfig = None
    # memory engine config
    memory_config: MemoryIrConfig = None
    # Skill 本地目录（相对路径）
    skill_dir: str = ""
    # Skill 信息列表，每一项包含 name、description、skill_path
    skill_info: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SkillInjectionContext:
    """Skill 动态注入上下文，封装 Agent.astream 注入的 skill 相关参数"""

    prompt_suffix: str = ""
    tool_names: Set[str] = field(default_factory=set)
    tool_refs: Set[int] = field(default_factory=set)
    work_dir: str = ""

    @staticmethod
    def empty() -> "SkillInjectionContext":
        """Create an empty SkillInjectionContext with default values."""
        return SkillInjectionContext()


@dataclass
class StreamRequest:
    """流式请求参数封装"""

    query: str
    prompt_info: dict = None
    plugins: list = None
    workflows: list = None
    trace_handlers: list = None
    session: Any = None
    runtime_context: Any = None
    contexts: dict = None
    multimodal_image: Any = None
    request_params: Any = None
    mcps: list = None
    skill_context: SkillInjectionContext = field(default_factory=SkillInjectionContext)
    # 请求级执行 ID：Controller 内嵌 workflow 的 OTel handler 按它隔离状态
    execution_id: str = ""


@dataclass
class InvokeRequest:
    """同步调用请求参数封装"""

    query: str
    prompt_info: dict
    plugins: list = None
    workflows: list = None
    trace_handlers: list = None
    session: Any = None
    contexts: dict = None
    runtime_context: Any = None


# ============= PlanExecute 模式配置类 =============


@dataclass
class GuidelineConfig:
    """指南配置"""

    id: int
    condition: str
    action: str
    tools: List[str] = field(default_factory=list)


@dataclass
class RelationConfig:
    """指南依赖关系配置"""

    type: str  # "dependency"
    src: int
    tgt: int


@dataclass
class SceneConfig:
    """场景配置"""

    id: str
    name: str
    description: str
    tools: List[str] = field(default_factory=list)
    guidelines: List[GuidelineConfig] = field(default_factory=list)
    relations: List[RelationConfig] = field(default_factory=list)


@dataclass
class PlanningConfig:
    """规划配置"""

    max_steps: int = 10
    allow_replanning: bool = False


@dataclass
class PlanExecuteConfig(BasePlanConfig):
    """动态规划模式配置"""

    scenes: List[SceneConfig] = field(default_factory=list)
    planning: PlanningConfig = field(default_factory=PlanningConfig)
    sys_prompt_template: Optional[str] = None
