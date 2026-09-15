# -*- coding: UTF-8 -*-
"""Handoff 工具 —— 监督者 ReActAgent 调用的工具，把任务交给具体子 Agent。

子 Agent 是系统中已注册的 Agent，通过其已有 IR（OBS agent/ir/{agentId}/{agentId}.json）
加载，不重新上传、不生成新 IR。

HandoffTool 是无状态工具（D0-2/D0-8）：不绑定会话、不绑定模型；子 Agent 的模型来自其
自身 IR 的 modelConfig.modelName，会话为每次调用一次性创建。
"""

import uuid

from openjiuwen.core.foundation.tool import Tool, ToolCard
from openjiuwen.core.session.agent import create_agent_session
from openjiuwen.core.single_agent.agents.react_agent import ReActAgent
from openjiuwen.core.single_agent.schema.agent_card import AgentCard

from agent_runtime.runner.react_agent_runner import ReActAgentRunner
from agent_runtime.supervisor.common.constants import OutputSchemaType
from agent_runtime.supervisor.config import build_react_config
from agent_runtime.supervisor.event.adapt import StreamCtx, adapt_stream_chunk, build_sub_done, build_sub_start
from agent_runtime.supervisor.event.adapt import build_tool_call, build_tool_result
from agent_runtime.supervisor.event.channel import EventChannel, get_channel
from jiuwen.serve.controllers.execution.open_utils import async_ir_load

# 轻量工具装载器实例：复用平台 flow agent 同款 IR→工具 注册逻辑（构造只读 env、无副作用，
# 参照 orchestration.py 惰性单例先例）。子 Agent 工具装载只依赖 (ir_json, agent, agent_id)，与 runner 实例状态无关。
_runner = ReActAgentRunner()


class HandoffTool(Tool):
    """Handoff 工具：invoke 时加载子 Agent IR → 构建子 ReActAgent → 跑 query → 返回回答。"""

    def __init__(
        self,
        agent_id: str,
        description: str,
    ):
        self.agent_id = agent_id
        # name 用 agentId 前 8 位（ASCII、短、唯一）：模型校验 function name 只接受 ^[a-zA-Z0-9_-]+$（中文被拒，实证 2026-08-11）；
        # id 保持 handoff_{agentId}（唯一标识，执行按 id 不受影响，D0-4）；路由判断靠 description（中文）
        tool_name = f"transfer_to_{agent_id[:8]}"
        super().__init__(
            card=ToolCard(
                id=f"handoff_{agent_id}",
                name=tool_name,
                description=description or f"将任务移交给子 Agent {agent_id} 处理",
                input_params={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "需要子 Agent 处理的用户问题",
                        }
                    },
                    "required": ["query"],
                },
            )
        )

    def _ir_path(self) -> str:
        return f"agent/ir/{self.agent_id}/{self.agent_id}.json"

    def _extract_query(self, inputs) -> str:
        if isinstance(inputs, dict):
            return str(inputs.get("query", ""))
        return str(getattr(inputs, "query", inputs))

    async def invoke(self, inputs, **kwargs):
        query = self._extract_query(inputs)
        return await self._run_sub_agent(query)

    async def stream(self, inputs, **kwargs):
        result = await self.invoke(inputs, **kwargs)
        yield result

    def _build_sub_agent(self, ir_data: dict) -> ReActAgent:
        """从子 Agent IR 构建子 ReActAgent（system prompt + model）。

        子 Agent 的模型只取自身 IR 的 modelConfig.modelName，缺失/无效显式报错，不拿监督者模型
        兜底（A6）。⚠️ IR 字段名 `modelName` 实际存的是**部署 id**（D0-8），由路由解析成真实
        模型名——故变量命名用 model_deployment_id，勿理解成模型名。
        """
        configs = ir_data.get("configs", {})
        model_config = configs.get("modelConfig", {})
        model_deployment_id = model_config.get("modelName")
        if not model_deployment_id or str(model_deployment_id).lower() == "null":
            raise RuntimeError(
                f"子 Agent {self.agent_id} 的 modelConfig.modelName 无效（{model_deployment_id}），"
                f"请检查该 Agent 是否已绑定有效模型部署"
            )
        system_prompt = configs.get("sysPromptTemplate") or ""

        agent = ReActAgent(
            card=AgentCard(
                id=f"sub_{self.agent_id}",
                name=self.agent_id,
                description="子 Agent",
            )
        )
        agent.configure(build_react_config(system_prompt, model_deployment_id))
        return agent

    async def _run_sub_agent(self, query: str):
        """加载子 Agent IR → 构建子 ReActAgent → 跑 query → 返回最终回答。

        子 Agent 会话为一次性 uuid4()，无 conversation 前缀（子 Agent 与会话无关，D0-2）。
        SSE 事件化（D0-5）：开始发 tool_call/sub_start，迭代 sub_agent.stream() 经
        adapt_stream_chunk 实时冒泡 message/reasoning/usage，结束发 sub_done/tool_result。
        事件经请求级 EventChannel（ContextVar 注入，D0-4 工具无状态保持）写入，
        并发 handoff 时靠 sub_execution_id 分组。
        """
        channel = get_channel()
        if channel is None:
            raise RuntimeError("事件通道未注入（子 Agent 只能在 run_supervisor 调用链内执行）")
        execution_id = channel.execution_id
        # sub_execution_id 随本次调用生命周期诞生/回收：入口创建，函数返回即结束；不落 self（无状态共享实例，并行防串）
        sub_execution_id = str(uuid.uuid4())
        # handoff 决策时刻即发 tool_call（IR 加载失败也可见、可入库——工具异常需记录错误文本）
        tool_call_id = str(uuid.uuid4())
        tool_name = f"transfer_to_{self.agent_id[:8]}"
        await channel.emit(build_tool_call(execution_id, tool_call_id, tool_name, arguments={"query": query}))
        try:
            ir_data = await async_ir_load(self._ir_path())
        except Exception as e:
            # IR 加载失败 → 补发 tool_result（错误文本），再上交监督者（ability_manager 转 ToolMessage 喂回 LLM）
            error_msg = f"子 Agent {self.agent_id} IR 加载失败（{self._ir_path()}）: {e}"
            await channel.emit(build_tool_result(
                execution_id, tool_call_id, tool_name,
                result=error_msg,
            ))
            raise RuntimeError(error_msg) from e

        sub_agent = self._build_sub_agent(ir_data)
        # 装载子 Agent IR 工具（Plugin/MCP/Workflow/Skill），复用平台 flow agent 同一套注册语义（D0-3）
        await _runner.register_agent_tools(ir_data, sub_agent, self.agent_id)
        # ⚠️ [F3 场景3 实证记录 2026-08-11] 子 Agent 内部工具事件隔离验证：
        # 如需不依赖真实插件 API 验证子 Agent 的 tool_call/tool_result 事件，可在此临时注册 mock 工具
        # （id=mock_weather_tool, name=query_weather_mock，返回固定数据），已实证可用；验证后须删除。
        # 真实插件问题见 _emit_tool_event 注释（天气 8dafdc64 的 Create_Document URL 非法）。
        # 监督者 handoff 是统一工具调用（tool_call 包着 sub_start/sub_done，不分主子；agentId 缺省=监督者）
        await channel.emit(build_sub_start(execution_id, sub_execution_id, self.agent_id))
        # 必须传 card：agent.stream 内部 pre_run → checkpointer 读 session._card.id，缺 card 则 None.id 崩溃
        session = create_agent_session(session_id=str(uuid.uuid4()), card=sub_agent.card)
        ctx = StreamCtx(execution_id=execution_id, agent_id=self.agent_id, sub_execution_id=sub_execution_id)
        try:
            async for chunk in sub_agent.stream({"query": query}, session):
                # tracer_agent 是子 Agent 内部工具调用（需解析 payload），其余 chunk 走统一转换
                if getattr(chunk, "type", "") == OutputSchemaType.TRACER_AGENT.value:
                    await self._emit_tool_event(channel, getattr(chunk, "payload", {}) or {}, sub_execution_id)
                    continue
                for ev in adapt_stream_chunk(chunk, ctx):
                    await channel.emit(ev)
        except Exception as e:
            # 工具异常 → 先补发 tool_result（错误文本，供入库/前端展示），再上交监督者（ability_manager 转 ToolMessage 喂回 LLM）
            error_msg = f"子 Agent {self.agent_id} 执行失败: {e}"
            await channel.emit(build_tool_result(
                execution_id, tool_call_id, tool_name,
                result=error_msg,
            ))
            raise RuntimeError(error_msg) from e

        # sub_done 完整文本：answer 权威，兜底累计 llm_output（ctx.final_text，保证与 message 增量一致）
        await channel.emit(build_sub_done(execution_id, sub_execution_id, self.agent_id, ctx.final_text))
        await channel.emit(build_tool_result(
            execution_id, tool_call_id, tool_name,
            result=f"[子Agent {self.agent_id}] {ctx.final_text}",
        ))
        return {"result": f"[子Agent {self.agent_id}] {ctx.final_text}"}

    async def _emit_tool_event(self, channel: EventChannel, payload: dict, sub_execution_id: str) -> None:
        """把子 Agent 的工具调用（tracer_agent payload）转成统一 tool_call/tool_result 事件冒泡。

        工具事件不分主子 agent（用户决策 2026-08-11）：带 agentId/subExecutionId 标明归属子执行，
        供 Java 侧路由到 t_conversation_sub_run。

        ⚠️ [F3 场景3 实证记录 2026-08-11] 已知插件问题（待修复，勿当事件代码 bug）：
        天气子 Agent（8dafdc64）的 Create_Document 插件调用失败，tool_result 透传
        "Plugin params check failed, root cause = plugin's url is illegal"（插件 params 校验阶段拦截）。
        事件机制本身正常（mock 工具成功返回时同样正确冒泡），问题在插件 restful API 的 URL 配置，
        后续需修复插件配置（Java/平台侧）。
        """
        invoke_type = payload.get("invokeType", "")
        if invoke_type != "plugin":
            return
        name = payload.get("name", "")
        status = payload.get("status", "")
        tool_call_id = payload.get("invokeId") or str(uuid.uuid4())
        execution_id = channel.execution_id
        if status == "start":
            inputs = payload.get("inputs", {}) or {}
            await channel.emit(build_tool_call(
                execution_id, tool_call_id, name,
                arguments=inputs.get("inputs") if isinstance(inputs, dict) else inputs,
                agent_id=self.agent_id,
                sub_execution_id=sub_execution_id,
            ))
        elif status == "finish":
            outputs = payload.get("outputs", {}) or {}
            result = outputs.get("outputs") if isinstance(outputs, dict) else outputs
            if isinstance(result, dict):
                result = result.get("data", str(result))
            await channel.emit(build_tool_result(
                execution_id, tool_call_id, name,
                result=str(result) if result else None,
                agent_id=self.agent_id,
                sub_execution_id=sub_execution_id,
            ))
