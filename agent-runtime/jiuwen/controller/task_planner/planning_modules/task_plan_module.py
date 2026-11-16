#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""
任务规划模块

职责：
- 根据用户查询、匹配的场景、场景指南和依赖关系生成执行计划
- 如果没有匹配场景，直接让大模型规划
"""

import json
import uuid
from typing import List, Dict, Optional

from jiuwen.common.llm_service.messages import HumanMessage, SystemMessage
from jiuwen.common.log.base import logger
from jiuwen.controller.common.config import SceneConfig
from jiuwen.controller.task_planner.planning_modules.plan_tracker import (
    ExecutionPlan,
    PlanStep,
    StepStatus,
)
from jiuwen.prompt.template.template_manager import TemplateManager


class TaskPlanModule:
    """
    任务规划模块

    使用 LLM 根据场景、指南和依赖关系生成执行计划
    """

    def __init__(self, llm, context_manager):
        """
        初始化任务规划模块

        Args:
            llm: 语言模型实例
            context_manager: 上下文管理器
        """
        self.llm = llm
        self.context_manager = context_manager
        self.template_manager = TemplateManager()

    @staticmethod
    def _format_tools_text(filtered_tools: List[Dict]) -> str:
        """
        格式化工具列表文本

        Args:
            filtered_tools: 过滤后的工具列表

        Returns:
            格式化后的工具列表文本
        """
        tools_text = "## 可用工具列表\n\n"
        for tool in filtered_tools:
            tools_text += f"- {tool.get('name', '')}: {tool.get('description', '')}\n"
        tools_text += "\n"
        return tools_text

    @staticmethod
    def _format_scene_text(matched_scene: Optional[SceneConfig]) -> str:
        """
        格式化场景信息文本

        Args:
            matched_scene: 匹配的场景

        Returns:
            格式化后的场景信息文本
        """
        if not matched_scene:
            return ""

        scene_text = f"""## 当前场景信息

场景名称: {matched_scene.name}
场景描述: {matched_scene.description}

## 场景指南

"""
        for guideline in matched_scene.guidelines:
            tools_str = ", ".join(guideline.tools)
            scene_text += (
                f"- 指南{guideline.id}: 条件「{guideline.condition}」"
                f"→ 动作「{guideline.action}」，工具: [{tools_str}]\n"
            )

        scene_text += "\n## 指南依赖关系\n\n"
        for relation in matched_scene.relations:
            scene_text += f"- 指南{relation.tgt} 依赖 指南{relation.src}\n"
        scene_text += "\n"
        return scene_text

    @staticmethod
    def _parse_plan_result(content: str, task_id: str = "") -> Dict:
        """
        解析 LLM 返回的计划结果

        Args:
            content: LLM 返回的内容
            task_id: 任务ID，用于日志追踪

        Returns:
            解析后的计划字典
        """
        try:
            plan_dict = json.loads(content)
            return plan_dict
        except json.JSONDecodeError:
            logger.warning(
                f"task_id: {task_id}| Failed to parse plan result as JSON: {content[:100]}",
                simple_log=f"task_id: {task_id}| Failed to parse plan result as JSON",
            )
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                json_str = content[start:end].strip()
                try:
                    plan_dict = json.loads(json_str)
                    return plan_dict
                except json.JSONDecodeError:
                    pass
            return {"steps": []}

    @staticmethod
    def _build_execution_plan(
        plan_dict: Dict, matched_scene: Optional[SceneConfig]
    ) -> ExecutionPlan:
        """
        构建执行计划对象

        Args:
            plan_dict: 解析后的计划字典
            matched_scene: 匹配的场景

        Returns:
            ExecutionPlan: 执行计划对象
        """
        steps_data = plan_dict.get("steps", [])
        steps = []
        for step_data in steps_data:
            step = PlanStep(
                step_idx=step_data.get("step_idx", len(steps) + 1),
                step_name=step_data.get("step_name", "未命名步骤"),
                description=step_data.get("description", ""),
                status=StepStatus.PENDING,
                result=None,
            )
            steps.append(step)

        execution_plan = ExecutionPlan(
            plan_id=f"plan_{uuid.uuid4().hex[:8]}",
            steps=steps,
            current_step_idx=1,
            matched_scene=matched_scene,
        )
        return execution_plan

    async def plan(
        self,
        query: str,
        chat_history: List[Dict],
        matched_scene: Optional[SceneConfig],
        filtered_tools: List[Dict],
        task_id: str = "",
    ) -> ExecutionPlan:
        """
        生成任务执行计划

        Args:
            query: 用户查询
            chat_history: 对话历史
            matched_scene: 匹配的场景（可能为 None）
            filtered_tools: 过滤后的可用工具列表
            task_id: 任务ID，用于日志追踪

        Returns:
            ExecutionPlan: 执行计划对象
        """
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(query, matched_scene, filtered_tools)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        llm_input = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        }
        logger.info(
            f"task_id: {task_id}| [TaskPlan] <LLM Input> {llm_input}",
            simple_log=f"task_id: {task_id}| [TaskPlan] <LLM Input>",
        )

        try:
            result = await self.llm.ainvoke(messages)

            logger.info(
                f"task_id: {task_id}| [TaskPlan] <LLM Output> {result.content}",
                simple_log=f"task_id: {task_id}| [TaskPlan] <LLM Output>",
            )

            plan_dict = self._parse_plan_result(result.content, task_id)
            execution_plan = self._build_execution_plan(plan_dict, matched_scene)

            step_count = len(execution_plan.steps)
            logger.info(
                f"task_id: {task_id}| Task planning completed, total steps: {step_count}",
                simple_log=f"task_id: {task_id}| Task planning completed",
            )
            return execution_plan

        except Exception as e:
            logger.error(
                f"task_id: {task_id}| Error during task planning: {e}",
                simple_log=f"task_id: {task_id}| Error during task planning",
            )
            raise

    def _build_system_prompt(self) -> str:
        """
        构建系统提示词

        Returns:
            系统提示词字符串
        """
        template = self.template_manager.get("plan_execute_task_plan")
        for msg in template.content:
            if msg.get("role") == "system":
                return msg.get("content", "")
        return ""

    def _build_user_prompt(
        self,
        query: str,
        matched_scene: Optional[SceneConfig],
        filtered_tools: List[Dict],
    ) -> str:
        """
        构建用户提示词

        Args:
            query: 用户查询
            matched_scene: 匹配的场景
            filtered_tools: 过滤后的工具列表

        Returns:
            用户提示词字符串
        """
        tools_text = self._format_tools_text(filtered_tools)
        scene_text = self._format_scene_text(matched_scene)

        template = self.template_manager.get("plan_execute_task_plan")
        user_prompt_template = ""
        for msg in template.content:
            if msg.get("role") == "user":
                user_prompt_template = msg.get("content", "")
                break

        user_prompt = user_prompt_template.replace("{{tools_text}}", tools_text)
        user_prompt = user_prompt.replace("{{scene_text}}", scene_text)
        user_prompt = user_prompt.replace("{{query}}", query)
        return user_prompt
