"""ControllerRunner — HierarchicalAgentGroup execution with full SSE event flow."""

from __future__ import annotations

import json
import os
import time
import uuid
from collections.abc import Mapping
from typing import AsyncGenerator, Any

from agent_runtime.observability import setup_otel_tracer
from agent_runtime.runner.controller_stream_data_adapter import (
    ControllerStreamDataAdapter,
)
from agent_runtime.schemas.orchestration_mgr import ExecutionRequest
from agent_runtime.runner.memory_extraction_context import MemoryExtractionContext
from jiuwen.serve.controllers.execution.enum import IRType
from jiuwen.serve.controllers.execution.ir_converter import IRConverter
from jiuwen.serve.controllers.execution.open_utils import async_ir_load
from jiuwen.serve.controllers.execution.manager import AsyncStateManager
from jiuwen.serve.controllers.execution.types import ExecutionData
from jiuwen.serve.controllers.execution.utils import (
    build_agent_input,
    post_process_agent_group_streaming_output,
)
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.common.logging import performance_logger
from openjiuwen.core.session.agent import Session, create_agent_session


def _parse_controller_stream_chunk(chunk) -> dict | None:
    """把 run_streaming 的 chunk 规范化为 dict。

    Controller 正常流产出 SSE bytes("data: {...}\\n\\n");错误流(adapt_error)产出 dict。
    严格 UTF-8 解码——本进程自生成流,坏帧应抛错由调用方逐帧记录,不静默丢字节。
    """
    if isinstance(chunk, (bytes, bytearray)):
        chunk = bytes(chunk).decode("utf-8")
    if isinstance(chunk, str):
        if not chunk.startswith("data: "):
            return None
        try:
            chunk = json.loads(chunk[6:].strip())
        except json.JSONDecodeError:
            return None
    if not isinstance(chunk, Mapping):
        return None
    return dict(chunk)


class ControllerRunner:
    """Execute IRType.Agent (Controller mode) via HierarchicalAgentGroup path.

    Produces full SSE event flow matching commercial JiuWen:
    start → task_start → intent → workflow_start → message(s) → workflow_end → done → task_end
    """

    def __init__(self, api_key: str | None = None, api_base: str | None = None):
        self._api_key = api_key or os.environ.get("API_KEY", "")
        self._api_base = api_base or os.environ.get(
            "API_BASE", "https://api.deepseek.com"
        )
        if self._api_key:
            os.environ["IR_LLM_API_KEY"] = self._api_key
        if self._api_base:
            os.environ["IR_LLM_API_BASE"] = self._api_base

    async def run_streaming(
        self,
        req: ExecutionRequest,
        execution_id: str | None = None,
    ) -> AsyncGenerator[Any]:
        """Execute Controller mode IR and yield SSE bytes.

        Args:
            req: Execution request with conversation_id, query, ir_path, params, headers
            execution_id: Request-level execution ID for SSE event tracking

        Yields:
            SSE event dictionaries in the format expected by the API
        """
        session_id = req.conversation_id
        exec_id = execution_id or session_id or str(uuid.uuid4())
        adapter = ControllerStreamDataAdapter(execution_id=exec_id)

        # 1. Load IR from storage
        try:
            ir_json = await async_ir_load(req.ir_path)
        except Exception as e:
            workflow_logger.error(
                f"Failed to load IR from {req.ir_path}: {e}", exc_info=True
            )
            yield adapter.adapt_error(
                f"Failed to load workflow configuration: {e}", exec_id
            )
            return

        # 2. Build PlanRuntimeContext (reuse commercial logic)
        try:
            t_build_input = time.perf_counter()
            insight_client, runtime_context, tracer = await build_agent_input(req)
            performance_logger.info(f"build_agent_input|{round((time.perf_counter() - t_build_input) * 1000)}")

            # Inject the multi-agent's memory_repo_id and user_id into the
            # runtime_context's workflow_req_params so that sub-workflows use
            # the multi-agent's memory repo (not the sub-workflow's own) for
            # memory retrieval, and can resolve the user_id needed to query it.
            # This ensures memory extraction and retrieval share the same repo.
            controller_memory_repo_id = (
                (ir_json.get("configs") or {}).get("memory") or {}
            ).get("memory_repo_id", "")
            if controller_memory_repo_id:
                from jiuwen.controller.common.constants import WorkflowConstants
                req_params = runtime_context.agent_workflow_context.get(
                    WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY, {}
                )
                req_params["memory_repo_id"] = controller_memory_repo_id
                # Ensure user_id reaches sub-workflow global_variables; the
                # multi-agent request's global_variables.userId is often empty
                # even though req.user_id is set (e.g. "testUser").
                if req.user_id:
                    gv = dict(req_params.get("global_variables") or {})
                    if not gv.get("userId"):
                        gv["userId"] = req.user_id
                    req_params["global_variables"] = gv
                runtime_context.agent_workflow_context[
                    WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY
                ] = req_params
        except Exception as e:
            workflow_logger.error(f"Failed to build agent input: {e}", exc_info=True)
            yield adapter.adapt_error(f"Failed to build runtime context: {e}", exec_id)
            return

        # 3. Create Agent Group instance
        try:
            t_agent_group = time.perf_counter()
            agent_group = await IRConverter.ir_to_agent_group(ir_json, session_id)
            performance_logger.info(f"ir_to_agent_group|{round((time.perf_counter() - t_agent_group) * 1000)}")
        except Exception as e:
            workflow_logger.error(
                f"Failed to create agent group from IR: {e}", exc_info=True
            )
            yield adapter.adapt_error(f"Failed to create agent group: {e}", exec_id)
            return

        # 4. Setup insight queue for debug mode
        is_debug = (
            os.environ.get("INSIGHT_EI_DEBUG_INFO_ENABLE", "true").lower() == "true"
        )
        insight_queue = insight_client.data_queue if is_debug else None

        # 5. Create ExecutionData for post_process_agent_group_streaming_output
        execution_data = ExecutionData(
            instance=agent_group,
            instance_type=IRType.Agent,
            updated_time=int(time.time() * 1000),
            collector=None,
        )

        # 6. Execute agent group streaming using post_process_agent_group_streaming_output
        # Collect assistant response for memory extraction
        memory_response_parts: list[str] = []
        session: Session | None = None
        try:
            t_stream_start = time.perf_counter()
            workflow_logger.info(f"Starting agent_group.astream for query: {req.query}")

            session_id = req.conversation_id or "default_session"
            session_inputs = {
                "query": req.query or "",
                "conversation_id": req.conversation_id,
                "user_id": req.user_id,
            }
            setup_otel_tracer()
            session = create_agent_session(session_id=session_id, card=agent_group.card)
            await session.pre_run(inputs=session_inputs)

            streaming_output = agent_group.astream(
                req.query,
                stream=True,
                runtime_context=runtime_context,
                tool_switch_dict=getattr(req.params, "tool_switch_dict", None),
                trace_handlers=tracer,
                session=session,
            )

            async for chunk in post_process_agent_group_streaming_output(
                conversation_id=session_id,
                origin_output=streaming_output,
                execution_data=execution_data,
                insight_queue=insight_queue,
                is_debug=is_debug,
            ):
                # Collect response text for memory extraction
                try:
                    chunk_str = chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
                    if chunk_str.startswith("data: "):
                        import json as _json
                        evt_data = _json.loads(chunk_str[6:])
                        evt_type = evt_data.get("event", "")
                        if evt_type in ("message", "done"):
                            answer = evt_data.get("data", {}).get("answer", "")
                            if answer:
                                memory_response_parts.append(str(answer))
                except Exception as _e:
                    # Non-critical: SSE chunk parsing failure must not break the stream.
                    # Logged at debug level since this is best-effort collection for
                    # memory extraction, not essential for the response flow.
                    workflow_logger.debug(
                        "Failed to parse SSE chunk for memory extraction: %s", _e
                    )
                yield adapter.adapt_execution_id(chunk)

            performance_logger.info(f"agent_group_stream|{round((time.perf_counter() - t_stream_start) * 1000)}")

            # Trigger memory extraction after successful agent group execution
            await self._trigger_memory_extraction(
                MemoryExtractionContext(
                    ir_json=ir_json,
                    user_id=req.user_id,
                    conversation_id=req.conversation_id,
                    user_query=req.query or "",
                    assistant_response="".join(memory_response_parts),
                    enable_memory_extract=bool(req.params.enable_memory_extract),
                )
            )
        except Exception as e:
            workflow_logger.error(
                f"Agent group streaming failed with exception: {e}", exc_info=True
            )
            import traceback

            tb_str = traceback.format_exc()
            workflow_logger.error(f"Exception traceback: {tb_str}")
            yield adapter.adapt_error(f"Agent execution failed: {e}\n{tb_str}", exec_id)
            await AsyncStateManager().delete_state(session_id)
            return
        finally:
            if session is not None:
                await session.post_run()

    async def _trigger_memory_extraction(
        self,
        ctx: MemoryExtractionContext,
    ) -> None:
        """Trigger memory extraction after agent group execution if memory is configured.

        Checks if the IR has memory config with memory_repo_id,
        and if so, calls the UserProfileMemoryExtractor to cache the conversation
        turn for later extraction (based on conversation_round / time_span triggers).

        Skipped when ``ctx.enable_memory_extract`` is False (the "对话中存储记忆"
        switch is off).
        """
        try:
            if not ctx.enable_memory_extract:
                return

            configs = ctx.ir_json.get("configs") or {}
            memory_config = configs.get("memory") or {}
            memory_repo_id = memory_config.get("memory_repo_id")

            if not memory_repo_id:
                return

            if not ctx.user_query and not ctx.assistant_response:
                return

            from openjiuwen.core.foundation.llm import UserMessage, AssistantMessage
            from agent_runtime.memory.storage.memory_extractor import get_instance

            messages = []
            if ctx.user_query:
                messages.append(UserMessage(content=ctx.user_query))
            if ctx.assistant_response:
                messages.append(AssistantMessage(content=ctx.assistant_response))

            if not messages:
                return

            extractor = get_instance()
            await extractor.async_add_chat_turn(
                user_id=ctx.user_id,
                memory_repo_id=memory_repo_id,
                conversation_id=ctx.conversation_id,
                ir_data=ctx.ir_json,
                messages=messages,
            )
            workflow_logger.info(
                "Memory extraction triggered for repo=%s, user=%s, conversation=%s",
                memory_repo_id,
                ctx.user_id,
                ctx.conversation_id,
            )
        except Exception as e:
            workflow_logger.warning(
                "Failed to trigger memory extraction: %s", e, exc_info=True
            )

    async def run_blocking(self, req: ExecutionRequest) -> str:
        """Execute Controller mode IR and return complete result.

        run_streaming 正常流产 SSE bytes、错误流产 dict;_parse_controller_stream_chunk
        统一成 dict。裁决:完整终态(workflow_end/message_end)优先,delta(message)仅兜底,
        保证答案恰好一份(不重复、不空)。
        """
        message_parts: list[str] = []
        message_end_answer = ""
        workflow_end_answer = ""
        async for chunk in self.run_streaming(req):
            if chunk is None:
                continue
            try:
                payload = _parse_controller_stream_chunk(chunk)
                if payload is None:
                    continue
                event = payload.get("event", "")
                data = payload.get("data") or {}
                answer = data.get("answer", "") or data.get("output", "")
                if not answer:
                    continue
                if event == "message":
                    message_parts.append(str(answer))
                elif event == "message_end":
                    message_end_answer = str(answer)
                elif event == "workflow_end":
                    workflow_end_answer = str(answer)
                # done / 其他事件:忽略
            except Exception as e:
                workflow_logger.error(
                    f"Agent group blocking failed with exception: {e}", exc_info=True
                )
        return workflow_end_answer or message_end_answer or "".join(message_parts)
