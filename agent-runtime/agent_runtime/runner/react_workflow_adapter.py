# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
"""
ReActAgent Workflow Adapter — 将 Workflow 适配为 ReActAgent 可调用的 Tool
"""

import uuid
from typing import List

from openjiuwen.core.foundation.tool import Tool, ToolCard
from openjiuwen.core.session.stream import BaseStreamMode
from datetime import datetime


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

        session_id = kwargs.get("session_id", str(uuid.uuid4()))
        session = create_workflow_session(session_id=session_id)
        wf_inputs = self._convert_inputs(inputs)
        # R-02: per-call 新建 workflow 实例 → 各自独立 _session/_graph → 并发 stream() 不竞写
        wf_instance = await IRConverter.async_ir_to_workflow(self._ir_data)

        final_answer = None
        fallback_result = None

        async for chunk in wf_instance.stream(
            inputs=wf_inputs,
            session=session,
            stream_modes=[BaseStreamMode.OUTPUT, BaseStreamMode.CUSTOM],
        ):
            chunk_type = getattr(chunk, "type", None)
            payload = getattr(chunk, "payload", {}) or getattr(chunk, "data", {})

            if chunk_type == "workflow_final":
                final_answer = payload.get("answer", "")
            elif chunk_type == "message_end" and payload.get("node_type", "") != "jiuwen.end":
                message_result = payload.get("answer", "")
                if message_result:
                    fallback_result = message_result

        if not final_answer and fallback_result:
            final_answer = fallback_result

        return {"answer": final_answer} if final_answer else {}

    async def stream(self, inputs: dict, **kwargs):
        """流式调用工作流（ReActAgent 不使用，但需实现抽象方法）"""
        result = await self.invoke(inputs, **kwargs)
        yield result

    def _convert_inputs(self, inputs: dict) -> dict:
        """将 agent 的输入直接传递给工作流（扁平格式）"""
        if "sys" not in inputs:
            sys = dict(
                conversationHistory=[],
                conversationId=str(uuid.uuid4()),
                userId="",
                dialogueCount=1,
                currentTime=datetime.now().strftime("%Y-%m-%d%H:%M:%S"))
            inputs["global_variables"] = {"sys": sys}
        return inputs