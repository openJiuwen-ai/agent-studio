"""DebugStreamFormatter — 将 SingleComponentDebugWrapper 产出的 StreamData 转为前端 SSE 事件格式。"""

import time
from datetime import datetime, timezone

from jiuwen.orchestration.flow.stream.base import StreamCode, StreamData

_COMPONENT_TYPE_DISPLAY: dict[str, str] = {
    "jiuwen.llm": "LLM",
    "jiuwen.llm_chain": "LLM",
    "jiuwen.llmChain": "LLM",
    "jiuwen.LLMComponent": "LLM",
    "jiuwen.plugin": "Plugin",
    "jiuwen.api": "API",
    "jiuwen.flowApi": "API",
    "jiuwen.agent": "Agent",
    "jiuwen.flowAgent": "Agent",
    "jiuwen.code": "Code",
    "jiuwen.start": "Start",
    "jiuwen.end": "End",
    "jiuwen.message": "Message",
    "jiuwen.branch": "Branch",
    "jiuwen.setVariable": "SetVariable",
    "jiuwen.intentDetection": "IntentDetection",
    "jiuwen.questioner": "Questioner",
    "jiuwen.aggregate": "Aggregate",
    "jiuwen.flowAggregate": "Aggregate",
    "jiuwen.aggregation": "Aggregate",
    "jiuwen.card": "Card",
    "jiuwen.flowCard": "Card",
    "jiuwen.loop": "Loop",
    "jiuwen.exception": "Exception",
    "jiuwen.streamTransform": "StreamTransform",
    "jiuwen.subWorkflow": "SubWorkflow",
    "jiuwen.workflowComposite": "SubWorkflow",
    "jiuwen.input": "Input",
    "jiuwen.flowInput": "Input",
    "jiuwen.extractor": "Extractor",
    "jiuwen.infoExtraction": "Extractor",
    "jiuwen.mcp": "MCP",
    "jiuwen.flowMcp": "MCP",
}


class DebugStreamFormatter:
    """将 SingleComponentDebugWrapper.astream() 产出的 StreamData 转为前端期望的 SSE 事件字典。

    事件注入顺序（对齐交接文档的 response 格式）：
    1. start 事件
    2. workflow_node_message (status=start)
    3. workflow_node_message (status=running) — 首次收到 PARTIAL_CONTENT 时
    4. N 个 message 事件 — 来自 PARTIAL_CONTENT 的 answer
    5. workflow_node_message (status=running, outputs=...) — 收到 FINISH 时
    6. workflow_node_message (status=finish, outputs=...) — 收到 FINISH 时
    7. done 事件 — 包含最终 answer + node_id/node_name/node_type
    """

    def __init__(
        self,
        execution_id: str,
        component_id: str,
        component_name: str,
        component_type: str,
        agent_id: str,
        inputs: dict,
    ):
        self._execution_id = execution_id
        self._component_id = component_id
        self._component_name = component_name
        self._component_type = _COMPONENT_TYPE_DISPLAY.get(
            component_type, component_type
        )
        self._raw_component_type = component_type
        self._agent_id = agent_id
        self._inputs = inputs
        self._started = False
        self._node_started = False
        self._node_running = False
        self._start_time = datetime.now(timezone.utc).isoformat()
        self._message_index = 0
        self._done_emitted = False
        self._is_questioner = component_type == "jiuwen.questioner"

    def _finish_status(self, data: dict) -> str:
        """Questioner 节点 FINISH 时状态为 running，其他节点为 finish"""
        if self._is_questioner:
            if data.get("answer", {}).get("should_interrupt", False):
                return "running"
        return "finish"

    def format(self, stream_data: StreamData) -> list[dict]:
        """将单个 StreamData 转为 SSE 事件字典列表。"""
        events: list[dict] = []

        # 清除提问器标识
        if self._is_questioner:
            self._inputs.pop("__single_debug_recovery__", None)

        # 首次收到数据时注入 start + node_message(start)
        if not self._started:
            self._started = True
            events.append(self._build_start_event())
            events.append(self._build_node_message("start"))
            self._node_started = True

        code = stream_data.code

        # FINISH → node_message(结束状态) + done
        if code == StreamCode.FINISH.value:
            data = stream_data.data if isinstance(stream_data.data, dict) else {}
            # 异常恢复时 data 顶层带 innerError（isSuccess:false + errorBody），
            # 提到 node_message 顶层供 Java JiuwenEventProcessor 识别为失败。
            inner_error = data.get("innerError") if isinstance(data, dict) else None
            # 异常恢复时 data.outputs 为扁平恢复结果（对齐参考版本）；正常时 outputs=data
            outputs = data.get("outputs", data) if isinstance(data, dict) else data
            # 提问器增加历史
            invoke_data = []
            if self._is_questioner:
                invoke_data = [
                    {"user": self._inputs.get("query", "")},
                    {"assistant": data.get("answer", {}).get("answer", "")},
                ]
            # node_message(结束状态) 带 outputs
            # 异常恢复（innerError 存在）时状态为 error，否则为 finish
            node_status = "error" if inner_error else self._finish_status(data)
            events.append(
                self._build_node_message(
                    node_status,
                    outputs=outputs,
                    invoke_data=invoke_data,
                    inner_error=inner_error,
                )
            )
            # done 事件
            events.append(self._build_done_event(data))
            self._done_emitted = True
            return events

        # PARTIAL_CONTENT → message 事件
        if code == StreamCode.PARTIAL_CONTENT.value:
            if not self._node_running:
                self._node_running = True
                events.append(self._build_node_message("running"))

            answer = ""
            if isinstance(stream_data.data, dict):
                answer = stream_data.data.get("answer", "")
            else:
                answer = str(stream_data.data) if stream_data.data is not None else ""

            events.append(
                {
                    "event": "message",
                    "data": {
                        "answer": answer,
                        "node_id": self._component_id,
                        "node_name": self._component_name,
                        "node_type": self._raw_component_type,
                        "should_interrupt": False,
                    },
                    "createdTime": int(time.time() * 1000),
                    "executionId": self._execution_id,
                    "index": self._message_index,
                    "isStructMessage": False,
                }
            )
            self._message_index += 1
            return events

        # ERROR → node_message(error) + error 事件
        if code == StreamCode.ERROR.value:
            data = stream_data.data if isinstance(stream_data.data, dict) else {}
            events.append(self._build_node_message("error", error=data))
            events.append(
                {
                    "event": "error",
                    "data": data,
                    "executionId": self._execution_id,
                    "index": 0,
                    "createdTime": int(time.time() * 1000),
                }
            )
            self._done_emitted = True
            return events

        # MESSAGE_END — 跳过 LLM 类型的（已被 SingleComponentDebugWrapper 转为 FINISH）
        # 但对于 Questioner 等组件，需要输出 message_end 事件
        if code == StreamCode.MESSAGE_END.value:
            # 构建 message_end 事件
            answer = ""
            if isinstance(stream_data.data, dict):
                answer = stream_data.data.get("answer", "")
            events.append(
                {
                    "event": "message_end",
                    "data": {
                        "answer": answer,
                        "node_id": self._component_id,
                        "node_name": self._component_name,
                        "node_type": self._raw_component_type,
                        "should_interrupt": False,
                    },
                    "createdTime": int(time.time() * 1000),
                    "executionId": self._execution_id,
                    "index": self._message_index,
                    "isStructMessage": False,
                }
            )
            self._message_index += 1
            return events

        # 其他 code 兜底透传
        events.append(
            {
                "event": "message",
                "data": stream_data.data
                if isinstance(stream_data.data, dict)
                else {"answer": str(stream_data.data)},
                "executionId": self._execution_id,
                "index": self._message_index,
                "createdTime": int(time.time() * 1000),
                "isStructMessage": False,
            }
        )
        self._message_index += 1
        return events

    def finalize(self) -> list[dict]:
        """流结束后产出遗漏的事件（如未收到任何 StreamData 时）。"""
        if not self._started:
            return [
                {
                    "event": "error",
                    "data": {"message": "No output from component"},
                    "executionId": self._execution_id,
                    "index": 0,
                    "createdTime": int(time.time() * 1000),
                }
            ]
        if not self._done_emitted:
            # 流正常结束但未收到 FINISH，补发 done
            events = [self._build_node_message(self._finish_status())]
            events.append(self._build_done_event({}))
            return events
        return []

    def _build_start_event(self) -> dict:
        return {
            "event": "start",
            "data": {},
            "createdTime": int(time.time() * 1000),
            "executionId": self._execution_id,
            "index": 0,
            "isStructMessage": False,
        }

    def _build_node_message(
        self,
        status: str,
        outputs: dict | None = None,
        error: dict | None = None,
        invoke_data: list | None = None,
        inner_error: dict | None = None,
    ) -> dict:
        if invoke_data is None:
            invoke_data = []

        now = datetime.now(timezone.utc).isoformat()
        data = {
            "executionId": self._execution_id,
            "conversationId": "",
            "startTime": self._start_time,
            "endTime": now if status in ("finish", "running", "error") else None,
            "onInvokeData": invoke_data,
            "agentId": self._agent_id,
            "componentId": self._component_id,
            "componentName": self._component_name,
            "componentType": self._component_type,
            "agentParentInvokeId": "",
            "inputs": {"userFields": self._inputs},
            "outputs": outputs,
            "error": error,
            "metaData": None,
            "invokeId": "",
            "parentInvokeId": "",
            "traceId": self._execution_id,
            "loopNodeId": None,
            "loopIndex": None,
            "innerError": inner_error,
            "status": status,
        }
        return {
            "event": "workflow_node_message",
            "data": data,
            "executionId": self._execution_id,
            "index": 0,
            "createdTime": int(time.time() * 1000),
            "isStructMessage": False,
        }

    def _build_done_event(self, finish_data: dict) -> dict:
        answer = finish_data.get("answer", {})
        return {
            "event": "done",
            "data": {
                "answer": answer,
                "node_id": self._component_id,
                "node_name": self._component_name,
                "node_type": self._raw_component_type,
                "should_interrupt": False,
            },
            "executionId": self._execution_id,
            "index": 0,
            "createdTime": int(time.time() * 1000),
            "isStructMessage": False,
        }
