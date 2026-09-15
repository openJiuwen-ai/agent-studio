# -*- coding: UTF-8 -*-
"""监督者运行器 —— run_supervisor 事件生成器（每次请求执行）。

与 builder.py（组装）职责分离：run 负责跑监督者一轮并产出 SSE 事件流。
对齐平台 XxxRunner 命名惯例（react_agent_runner / workflow_runner / controller_runner）。
当前为无状态 async 生成器（channel/ctx/index 均为调用局部），不强类化；
后续若需跨调用状态（多轮历史/会话恢复）再升级为 SupervisorRunner 类。
"""

import asyncio
import sys

from openjiuwen.core.session.agent import create_agent_session
from openjiuwen.core.single_agent.agents.react_agent import ReActAgent

from agent_runtime.supervisor.common.constants import TeamEventField
from agent_runtime.supervisor.event.adapt import StreamCtx, adapt_stream_chunk, build_error, build_run_done
from agent_runtime.supervisor.event.channel import EventChannel, reset_channel, set_channel
from agent_runtime.supervisor.skill_context import bind_agent_skill_context, reset_skill_context

# 监督者 stream 消费任务结束哨兵
_STOP = object()


async def _finish_supervisor_task(
    task: asyncio.Task | None,
) -> tuple[BaseException | None, asyncio.CancelledError | None, bool]:
    """Cancel and await a copied-Context task, even when our caller is cancelled again."""
    if task is None:
        return None, None, False
    cleanup_task = asyncio.current_task()
    cancellation_baseline = cleanup_task.cancelling() if cleanup_task is not None else 0
    cleanup_requested_cancel = False
    if not task.done():
        cleanup_requested_cancel = task.cancel()

    caller_cancellation: asyncio.CancelledError | None = None
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError as error:
            current_cancellations = cleanup_task.cancelling() if cleanup_task is not None else 0
            if current_cancellations > cancellation_baseline:
                caller_cancellation = error
                cancellation_baseline = current_cancellations
            if not task.done():
                task.cancel()
        except BaseException:
            break

    try:
        task.result()
    except BaseException as error:
        return error, caller_cancellation, cleanup_requested_cancel
    return None, caller_cancellation, cleanup_requested_cancel


async def run_supervisor(agent: ReActAgent, query: str, conversation_id: str, execution_id: str):
    """事件生成器：跑监督者一轮，产出 SSE 事件 dict（message/reasoning/usage/run_done/error）。

    双任务模式：
    - 任务 A（supervisor_stream_task）：消费监督者 stream 的 OutputSchema → put 事件通道；
      工具（handoff）在该任务内被 await，子 Agent 增量经同一通道冒泡。
    - 主生成器（本协程）：从通道取事件 → yield（工具执行期间仍实时输出）。

    Args:
        agent: 监督者 ReActAgent
        query: 用户问题
        conversation_id: 业务会话 ID（作监督者执行 session_id，非事件 ID）
        execution_id: 本轮唯一标识（全量 uuid4）

    Yields:
        事件 dict（无 done，流结束即正常终止；异常发 error）
    """
    # 请求级事件通道对象（execution_id + 队列）：经 ContextVar 注入，工具/子 Agent 经 channel.emit 冒泡
    skill_token = bind_agent_skill_context(agent)
    channel_token = None
    task: asyncio.Task | None = None
    try:
        channel = EventChannel(execution_id)
        channel_token = set_channel(channel)
        # 必须传 card：agent.stream 内部 pre_run → checkpointer 读 session._card.id，缺 card 则 None.id 崩溃
        session = create_agent_session(session_id=conversation_id, card=agent.card)
        index = 0
        ctx = StreamCtx(execution_id=execution_id)
        error_sent = False

        async def supervisor_stream_task():
            # 监督者与子 Agent 同路径：stream 消费 → adapt_stream_chunk 提前转事件 dict → channel.emit
            try:
                async for chunk in agent.stream({"query": query}, session):
                    for ev in adapt_stream_chunk(chunk, ctx):
                        await channel.emit(ev)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                await channel.emit(e)
            finally:
                await channel.emit(_STOP)

        task = asyncio.create_task(supervisor_stream_task())
        while True:
            item = await channel.get()
            if item is _STOP:
                if task is not None:
                    task.result()
                break
            if isinstance(item, Exception):
                yield build_error(execution_id, code="supervisor_error", message=str(item), index=index)
                index += 1
                error_sent = True
                break
            # channel 中 item 必然是事件 dict（监督者提前转 + 子 Agent emit 冒泡），直接透传
            item[TeamEventField.INDEX] = index
            index += 1
            yield item

        # 边界收尾：run_done 用 answer 的权威完整文本（ctx.final_text）；异常已发 error 则不补 run_done
        if not error_sent:
            yield build_run_done(execution_id, ctx.final_text, index=index)
    finally:
        primary_error = sys.exception()
        task_error, caller_cancellation, cleanup_requested_cancel = await _finish_supervisor_task(task)
        channel_error: BaseException | None = None
        skill_error: BaseException | None = None
        try:
            if channel_token is not None:
                reset_channel(channel_token)
        except BaseException as error:
            channel_error = error
        finally:
            try:
                reset_skill_context(skill_token)
            except BaseException as error:
                skill_error = error

        expected_cleanup_cancellation = (
            cleanup_requested_cancel and isinstance(task_error, asyncio.CancelledError)
        )
        if caller_cancellation is not None:
            raise caller_cancellation
        if task_error is not None and not expected_cleanup_cancellation:
            raise task_error
        if primary_error is None:
            for error in (channel_error, skill_error):
                if error is not None:
                    raise error
