# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
"""
ReActAgent Workflow Adapter — 将 Workflow 适配为 ReActAgent 可调用的 Tool
"""

import uuid
from typing import List

from openjiuwen.core.foundation.tool import Tool, ToolCard
from openjiuwen.core.session.stream import BaseStreamMode
from datetime import datetime

from agent_runtime.context.request_context import _request_ctx


class ReactWorkflowAdapter(Tool):
    """包装工作流为 Tool，供 ReActAgent 调用"""

    def __init__(
        self,
        ir_data: dict,
        card_id: str,
        workflow_name: str,
        workflow_desc: str,
        input_params: dict,
        user_fields_keys: List[str],
    ):
        card = ToolCard(
            id=card_id,
            name=workflow_name,
            description=workflow_desc,
            input_params=input_params,
        )
        super().__init__(card=card)
        # R-02: 只存只读 IR,不存共享 workflow 实例;invoke 每次自建,消除并发竞写
        self._ir_data = ir_data
        self._user_fields_keys = user_fields_keys

    async def invoke(self, inputs: dict, **kwargs) -> dict:
        """调用工作流"""
        from openjiuwen.core.workflow import create_workflow_session
        from jiuwen.serve.controllers.execution.ir_converter import IRConverter

        # ability_manager 调用形如 tool.invoke(tool_args, session=session)，
        # 传入的是 AgentSession（其 session_id 即真实 conversation_id）。
        # 优先复用它派生 workflow session，保留血缘与稳定 session_id，
        # 避免每次新建随机孤儿 session。AgentSession.create_workflow_session()
        # 会以 inner session 为 parent、沿用真实 session_id，是框架约定的派生方式。
        agent_session = kwargs.get("session")
        if agent_session is not None and hasattr(agent_session, "create_workflow_session"):
            session = agent_session.create_workflow_session()
        else:
            session_id = kwargs.get("session_id") or str(uuid.uuid4())
            session = create_workflow_session(session_id=session_id)
        wf_inputs = self._convert_inputs(inputs)
        # R-02: per-call 新建 workflow 实例 → 各自独立 _session/_graph → 并发 stream() 不竞写
        wf_instance = await IRConverter.async_ir_to_workflow(self._ir_data)

        final_payload = None
        fallback_answer = None
        fallback_present = False

        async for chunk in wf_instance.stream(
            inputs=wf_inputs,
            session=session,
            stream_modes=[BaseStreamMode.OUTPUT, BaseStreamMode.CUSTOM],
        ):
            chunk_type = getattr(chunk, "type", None)
            payload = getattr(chunk, "payload", {}) or getattr(chunk, "data", {})
            if not isinstance(payload, dict):
                payload = {"answer": payload}

            if chunk_type == "workflow_final":
                # 保留整个 payload：结构化内容在 origin_answer，业务字段在 userFields，
                # 仅取 answer 会丢兄弟字段；origin_answer 见 end.get_output_data_with_metadata。
                final_payload = payload
            elif chunk_type == "message_end" and payload.get("node_type", "") != "jiuwen.end":
                # 用 "answer" in payload 区分"falsy 答案"与"未产出"，
                # 避免 0/False/空串/空集合被 truthiness 吞掉。
                if "answer" in payload:
                    fallback_answer = payload["answer"]
                    fallback_present = True

        # workflow_final 优先；缺失时用 message_end 兜底
        if final_payload is None:
            final_payload = {"answer": fallback_answer} if fallback_present else None

        if final_payload is None:
            return {}

        # 结构化内容优先 origin_answer（isStructMessage 时结构化输出在此），其次 answer。
        answer = final_payload.get("origin_answer")
        if answer is None:
            answer = final_payload.get("answer")

        # workflow_final 未给出可用 answer（键缺失或空串）时，回退到 message_end 的 answer，
        # 与原逻辑保持一致；但 0/False/[]/{} 是合法 falsy 值，不触发回退、也不被丢弃。
        if (answer is None or answer == "") and fallback_present:
            answer = fallback_answer

        result = {}
        if answer is not None:
            result["answer"] = answer
        user_fields = final_payload.get("userFields")
        if user_fields:
            result["userFields"] = user_fields
        return result

    async def stream(self, inputs: dict, **kwargs):
        """流式调用工作流（ReActAgent 不使用，但需实现抽象方法）"""
        result = await self.invoke(inputs, **kwargs)
        yield result

    def _convert_inputs(self, inputs: dict) -> dict:
        """将 agent 的输入直接传递给工作流（扁平格式）

        身份字段（conversationId/userId）必须取真实值（来源 _request_ctx，由
        RequestContextMiddleware 对每个请求设置），避免用随机 uuid/空串覆盖
        导致记忆检索失效、会话状态错位。
        """
        global_variables = inputs.setdefault("global_variables", {})
        # 上游已提供 sys 视为权威值，原样保留（不覆盖、不丢 environment 等兄弟字段）。
        if isinstance(global_variables, dict) and global_variables.get("sys"):
            return inputs

        # 真实运行时 LLM 工具参数只有 {query}，不带 sys：从请求上下文取真实身份补齐。
        conversation_id, user_id = self._resolve_identity()
        sys = dict(
            conversationHistory=[],
            conversationId=conversation_id,
            userId=user_id,
            dialogueCount=1,
            currentTime=datetime.now().strftime("%Y-%m-%d%H:%M:%S"))
        global_variables["sys"] = sys
        return inputs

    @staticmethod
    def _resolve_identity():
        """从请求级上下文解析真实 conversation_id / user_id。

        RequestContextMiddleware 会为每个 HTTP 请求设置 _request_ctx（从 body
        解析 userId/conversationId）。非 HTTP 场景（单测/脚本）下返回默认空值，
        不抛异常。
        """
        try:
            ctx = _request_ctx.get()
            return ctx.conversation_id, ctx.user_id
        except Exception:
            return "", ""