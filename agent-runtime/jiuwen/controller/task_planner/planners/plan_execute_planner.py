#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""
PlanExecute 规划器

职责：
- 继承 TaskPlanner，实现 plan() 和 stream() 方法
- 协调场景匹配、任务规划、计划跟踪三个子模块
- 管理执行计划的生成和步骤推进
"""

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import List, Optional

from jiuwen.common.log.base import logger
from jiuwen.controller.common.config import SceneConfig, PlanExecuteConfig
from jiuwen.controller.common.message import Message
from jiuwen.controller.common.message_type import MessageType
from jiuwen.controller.task_planner.planning_modules.plan_tracker import (
    PlanTracker,
    HintBuilder,
    ExecutionPlan,
)
from jiuwen.controller.task_planner.planning_modules.scene_match_module import (
    SceneMatchModule,
)
from jiuwen.controller.task_planner.planning_modules.task_plan_module import (
    TaskPlanModule,
)
from jiuwen.controller.task_planner.task_planner import TaskPlanner
from jiuwen.controller.task_planner.task_queue import TaskQueue


@dataclass
class SceneMatchEvent:
    """场景匹配事件"""

    matched_scene: Optional[SceneConfig]
    confidence: float


@dataclass
class PlanEndEvent:
    """任务规划完成事件"""

    plan: ExecutionPlan


@dataclass
class PlanExecuteState:
    """PlanExecute 状态（用于持久化与恢复）"""

    plan: Optional[ExecutionPlan] = None
    current_step_idx: int = 1


class PlanExecutePlanner(TaskPlanner):
    """
    PlanExecute 规划器

    协调场景匹配、任务规划、计划跟踪模块，实现动态规划逻辑
    """

    def __init__(
        self,
        plan_config: PlanExecuteConfig,
        llm,
        plugins,
        workflows,
        context_manager,
        task_id,
    ):
        """
        初始化 PlanExecute 规划器

        Args:
            plan_config: PlanExecute 配置
            llm: 语言模型
            plugins: 插件列表
            workflows: 工作流列表
            context_manager: 上下文管理器
            task_id: 任务ID
        """
        super().__init__(plan_config, llm, plugins, workflows, context_manager, task_id)

        # 初始化子模块
        self.scene_match_module = SceneMatchModule(
            llm=llm, context_manager=context_manager
        )
        self.task_plan_module = TaskPlanModule(llm=llm, context_manager=context_manager)
        self.plan_tracker = PlanTracker()
        self.hint_builder = HintBuilder()
        self.task_queue = TaskQueue()

        # 保存配置
        self.pe_config: PlanExecuteConfig = plan_config
        from jiuwen.controller.common.config import SkillInjectionContext

        self.skill_context: SkillInjectionContext = SkillInjectionContext.empty()

    def plan(self, message: Message) -> None:
        """
        同步规划任务（不推荐使用，PlanExecute 模式建议使用流式）

        Args:
            message: 输入消息

        Note:
            PlanExecute 模式不支持同步规划，请使用 stream() 方法
        """
        logger.warning("PlanExecute mode should use stream() instead of plan()")

    async def stream(self, message: Message) -> AsyncGenerator:
        """
        流式规划任务

        Args:
            message: 输入消息

        Yields:
            流式输出：SceneMatchEvent, PlanEndEvent, Task 等
        """
        # 1. 处理用户输入消息
        if message.message_type == MessageType.USER_INPUT:
            self.context_manager.add_user_message(message.content)
            query = message.content
        else:
            query = self.context_manager.get_latest_user_content()

        # 获取对话历史
        chat_history = []

        # 2. 场景匹配
        logger.info(
            f"task_id: {self.task_id}| Starting scene matching",
            simple_log=f"task_id: {self.task_id}| Starting scene matching",
        )
        matched_scene, confidence = await self.scene_match_module.match(
            query=query,
            chat_history=chat_history,
            scenes=self.pe_config.scenes,
            task_id=self.task_id,
        )

        # yield 场景匹配事件
        yield SceneMatchEvent(matched_scene=matched_scene, confidence=confidence)

        # 3. 工具过滤（plugins + workflows）
        filtered_tools = self._filter_tools_by_scene(matched_scene)
        filtered_workflows = self._filter_workflows_by_scene(matched_scene)

        # 转换工具格式
        tools_for_planning = []
        for tool in filtered_tools:
            if hasattr(tool, "name"):
                tools_for_planning.append(
                    {"name": tool.name, "description": getattr(tool, "description", "")}
                )
        for ctx in (filtered_workflows or {}).values():
            tools_for_planning.append(
                {
                    "name": ctx.workflow_name,
                    "description": getattr(ctx, "description", ""),
                }
            )

        # 4. 任务规划
        logger.info(
            f"task_id: {self.task_id}| Starting task planning",
            simple_log=f"task_id: {self.task_id}| Starting task planning",
        )
        execution_plan = await self.task_plan_module.plan(
            query=query,
            chat_history=chat_history,
            matched_scene=matched_scene,
            filtered_tools=tools_for_planning,
            task_id=self.task_id,
        )

        # 初始化计划跟踪
        self.plan_tracker.init_plan(execution_plan)

        # yield 任务规划完成事件
        yield PlanEndEvent(plan=execution_plan)

        # 5. 后续步骤执行由 PlanExecuteMode 控制
        # 这里只负责规划，不负责执行
        logger.info(
            f"task_id: {self.task_id}| Planning completed, total steps: {len(execution_plan.steps)}",
            simple_log=f"task_id: {self.task_id}| Planning completed, total steps: {len(execution_plan.steps)}",
        )

    def get_state(self) -> Optional[PlanExecuteState]:
        """获取当前Planner状态（用于向后兼容）

        Returns:
            Optional[PlanExecuteState]: 规划器状态，如果没有计划则返回 None
        """
        if not self.plan_tracker.plan:
            return None
        return PlanExecuteState(
            plan=self.plan_tracker.plan,
            current_step_idx=self.plan_tracker.current_step_idx,
        )

    def load_state(self, state: Optional["ControllerState"]) -> None:
        """加载当前PlanExecutePlanner的状态

        Args:
            state: 状态对象，包含 plan_execute_state 属性
        """
        if not state or not hasattr(state, "plan_execute_state"):
            return
        pe_state = state.plan_execute_state
        if not pe_state or not pe_state.plan:
            return
        if pe_state.current_step_idx:
            pe_state.plan.current_step_idx = pe_state.current_step_idx
        self.plan_tracker.init_plan(pe_state.plan)
        if pe_state.current_step_idx:
            self.plan_tracker.current_step_idx = pe_state.current_step_idx
            if self.plan_tracker.plan:
                self.plan_tracker.plan.current_step_idx = pe_state.current_step_idx

    def _filter_tools_by_scene(self, matched_scene: Optional[SceneConfig]) -> List:
        """
        根据匹配的场景过滤工具

        Args:
            matched_scene: 匹配的场景

        Returns:
            过滤后的工具列表
        """
        plugins = list(self.plugins) if self.plugins else []

        if matched_scene is None:
            # 不排除skill注入的工具，让规划器能看到所有可用工具（包括read_file等skill工具）
            # 这样规划器可以根据用户请求中提到的skill生成合理的执行计划
            filtered = plugins
            logger.info(
                f"task_id: {self.task_id}| No scene match: {len(filtered)} plugin entries for task planning"
            )
            return filtered

        # 获取场景中的工具名称集合（场景级 + 指南级聚合）
        scene_tool_names = set(matched_scene.tools) if matched_scene.tools else set()
        # 如果场景级工具为空，从指南中聚合所有工具名
        if not scene_tool_names and matched_scene.guidelines:
            for guideline in matched_scene.guidelines:
                if guideline.tools:
                    scene_tool_names.update(guideline.tools)
            logger.info(
                f"task_id: {self.task_id}| Aggregated tools from guidelines: {scene_tool_names}"
            )

        # 过滤插件 — plugin.name 格式为 "{plugin_name}{operation_id}"（如 zhinenghuiyizhushoucreate_meeting）
        # scene_tool_names 中存的是完整 operation 名（前端保存 plugin_display_name + tool_display_name）
        filtered_tools = []
        for plugin in plugins:
            pname = getattr(plugin, "name", "")
            if pname in scene_tool_names:
                filtered_tools.append(plugin)

        scene_name = matched_scene.name if matched_scene else "None"
        logger.info(
            f"task_id: {self.task_id}| Filtered {len(filtered_tools)} tools from scene: {scene_name}, "
            f"scene_tool_names={scene_tool_names}"
        )
        return filtered_tools

    def _filter_workflows_by_scene(self, matched_scene) -> dict:
        """根据场景过滤工作流，逻辑与 PlanExecuteMode._filter_workflows_by_scene 对齐"""
        all_workflows = (
            getattr(self.context_manager, "workflow_contexts", None)
            if self.context_manager
            else None
        )
        if not all_workflows:
            return {}

        if matched_scene is None:
            logger.info(
                f"task_id: {self.task_id}| No scene match: {len(all_workflows)} workflow(s) for task planning"
            )
            return all_workflows

        scene_tool_names = set(matched_scene.tools) if matched_scene.tools else set()
        # 如果场景级工具为空，从指南中聚合所有工具名
        if not scene_tool_names and matched_scene.guidelines:
            for guideline in matched_scene.guidelines:
                if guideline.tools:
                    scene_tool_names.update(guideline.tools)
        filtered = {}
        for k, ctx in all_workflows.items():
            if ctx.workflow_name in scene_tool_names:
                filtered[k] = ctx
        logger.info(
            f"task_id: {self.task_id}| Filtered {len(filtered)} workflow(s) by scene for task planning"
        )
        return filtered
