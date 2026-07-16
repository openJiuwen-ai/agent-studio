import hashlib
import inspect
from typing import Any, AsyncGenerator, Generator, Iterator, Union, Literal, Optional, Dict

from agent_builder.nl_to_agent.adapter.utils import parse_adapter_info
from agent_builder.nl_to_agent.agent_creator.controller import Executor
from agent_builder.prompt.common.config import LLMModelInfo
from fastapi.requests import Request
from fastapi.responses import StreamingResponse
from agent_builder.adapter.exception_bridge import JiuWenBaseException
from agent_builder.adapter.jiuwen_bridge import AIMessage
from agent_builder.adapter.logger_bridge import logger
from agent_builder.adapter.jiuwen_bridge import request_json
from pydantic import ValidationError, BaseModel, Field, StrictStr

# Nl2 CONSTANT
USER_INSTRUCTION_LENGTH_LIMIT = 8000
MIN_CONVERSATION_ID_LENGTH = 1
NL2_FALLBACK_ERROR_MESSAGE = "We're sorry, the system has encountered an error! It was unable to successfully execute your request. Please try re-entering your input or starting the conversation again."
NL2_AGENT = "nl2_agentBuilder_model"
AGENT_TYPE_MAP = {"agents": "llm_agent", "workflows": "workflow"}


class N2LResource(BaseModel):
    plugins: Optional[Dict[str, Any]] = None
    workflows: Optional[Dict[str, Any]] = None
    knowledge_base: Optional[Dict[str, Any]] = None


class N2LModel(BaseModel):
    modelName: Optional[str] = None
    modelExplicitName: Optional[str] = None
    extension: Optional[Dict[str, Any]] = None
    modelType: Optional[str] = None
    modelInterfaceProtocol: Optional[str] = None


# 最终的请求体模型
class N2LRequestBody(BaseModel):
    query: str
    model: Optional[N2LModel] = None
    resource: Optional[N2LResource] = None
    conversationId: Optional[str] = None


class EiCloudNl2AgentInfo(BaseModel):
    """GenerateInfo"""

    conversationId: StrictStr = Field(min_length=MIN_CONVERSATION_ID_LENGTH)
    query: StrictStr
    agentType: Literal["llm_agent", "workflow"] = Field(...)
    modelInfo: LLMModelInfo = Field(...)


def _n2l_json_wapper(
    project_id: str, agent_type: str, cid: str, req_json: dict, request: Request
) -> dict:
    """将项目ID、会话ID和模型信息封装到请求 JSON 中。"""
    # conversationId 手动同步回上下文变量 保持日志一致性
    payload = request_json.get()
    payload["conversationId"] = cid
    request_json.set(payload)

    # 预先获取 headers 和 query_params 中的常用值，避免多次调用
    headers = request.headers
    query_params = request.query_params
    model = req_json.get("model")
    model_name = model.get("modelName")

    # 使用字典映射agent_type转换
    if agent_type in AGENT_TYPE_MAP:
        req_json["agentType"] = AGENT_TYPE_MAP[agent_type]

    # 更新基本信息
    req_json.update({"projectId": project_id, "conversationId": cid})

    # 构建 modelInfo 结构
    model_info_headers = {
        "agentBuilder_model_name": model_name,
        "workspace_id": query_params.get("workspace_id", ""),
        "project_id": project_id,
        "x_auth_token": headers.get("x-auth-token"),
        "auth_id": model.get("extension", {}).get("authId"),
        "deployment_id": model.get("extension", {}).get("deploymentId", ""),
        "model_explicit_name": model.get("modelExplicitName", ""),
        "nl2_model_type": model.get("modelType", ""),
        "model_interface_protocol": model.get("modelInterfaceProtocol", ""),
    }

    req_json["modelInfo"] = {
        "model": model_name,  # 模型实际请求名称
        "model_source": NL2_AGENT,
        "headers": model_info_headers,
    }

    return req_json


async def _chat(req_json: dict) -> StreamingResponse:
    """
    处理NL2的核心逻辑
    """
    task_id = req_json.get("conversationId")

    try:
        input_info = EiCloudNl2AgentInfo.model_validate(req_json)

        if not task_id:
            task_id = _generate_optimize_task_job_id(req_json)

        logger.info("========== Starting Chat Task, task_id: %s ==========", task_id)

        schema_config_dict = parse_adapter_info()

        initial_state = {
            "query": input_info.query,
            "task_id": task_id,
            "agent_type": input_info.agentType,
        }

        executor = Executor(
            initial_state,
            input_info.modelInfo,
            schema_config_dict,
            req_json.get("resource"),
        )

        yield_answer = executor.ainvoke(input_info.query)

        if not isinstance(yield_answer, (Generator, Iterator, AsyncGenerator)):
            # 如果 executor.invoke 还是返回的 coroutine，说明内部没 await 好
            # 这里增加一个保护判断
            if inspect.iscoroutine(yield_answer):
                logger.warning("yield_answer is a coroutine, awaiting it...")
                yield_answer = await yield_answer
            else:
                raise JiuWenBaseException(
                    f"Unexpected type: {type(yield_answer).__name__}"
                )

        return StreamingResponse(
            _generate(yield_answer, task_id), media_type="text/event-stream"
        )

    except ValidationError as e:
        # 专门捕获 Pydantic 校验错误
        logger.warning(f"Request validation failed: {e}")
        return StreamingResponse(
            _error_sse_generator(
                ValueError(f"Invalid Request: {e}"), task_id or "unknown"
            ),
            media_type="text/event-stream",
        )

    except Exception as e:
        # 捕获所有运行时异常
        logger.exception(f"Internal error processing task {task_id}")
        return StreamingResponse(
            _error_sse_generator(e, task_id or "unknown"),
            media_type="text/event-stream",
        )


class MessagePayload(BaseModel):
    answer: str | list | dict
    message_type: str = "message"


class ErrorPayload(BaseModel):
    code: str
    message: str


class SSEEvent(BaseModel):
    data: Union[str, MessagePayload, ErrorPayload, dict]
    event: str
    conversation_id: str = Field(..., serialization_alias="conversationId")

    def to_sse_string(self) -> str:
        """序列化为 SSE 格式字符串"""
        # 使用 model_dump 获取字典，by_alias=True 确保输出 conversationId
        json_str = json.dumps(self.model_dump(by_alias=True), ensure_ascii=False)
        return f"data: {json_str}\n\n"


import asyncio
import json
import time


async def _generate(yield_answer, task_id):
    """
    纯异步 SSE 生成器：打通从模型到前端的流式管道。
    """
    heartbeat_interval = 30  # 心跳间隔

    # 辅助函数：封装 SSE 格式
    def to_sse(event: str, data: Any) -> bytes:
        payload = {
            "data": data.model_dump() if hasattr(data, "model_dump") else data,
            "event": event,
            "conversationId": task_id,
        }
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")

    def to_error_sse(exc) -> bytes:
        # 默认Error，增加容错
        code = getattr(exc, "code", "500")
        msg = str(exc)
        if isinstance(exc, JiuWenBaseException):
            code = exc.error_code
            msg = exc.message
        return to_sse("error", {"code": code, "message": msg})

    try:
        # 1. 发送 START
        yield to_sse("START", "")

        # 2. 准备迭代器
        # 如果 yield_answer 是 coroutine，先 await 它拿到真正的 generator
        if asyncio.iscoroutine(yield_answer):
            yield_answer = await yield_answer

        async_iter = yield_answer.__aiter__()

        # 使用 task 包装，防止超时取消导致的数据丢失
        data_task = asyncio.create_task(async_iter.__anext__())

        while True:
            # 3. 等待数据或超时心跳
            done, pending = await asyncio.wait(
                [data_task],
                timeout=heartbeat_interval,
                return_when=asyncio.FIRST_COMPLETED,
            )

            if data_task in done:
                try:
                    item = await data_task  # 获取结果

                    # --- 类型处理逻辑 ---
                    if isinstance(item, str):
                        content = {"answer": item} if isinstance(item, str) else item
                        yield to_sse("MESSAGE", content)
                    elif isinstance(item, bytes):
                        yield b"data: " + item + b"\n\n"
                    elif isinstance(item, tuple):
                        yield to_sse(
                            "MESSAGE", {"answer": item[0], "message_type": item[1]}
                        )
                    elif isinstance(item, Exception):
                        yield to_error_sse(item)
                    if isinstance(item, dict):
                        content = item if isinstance(item, str) else item
                        yield to_sse("MESSAGE", content)
                    elif isinstance(item, AIMessage):
                        yield to_sse(
                            "MESSAGE",
                            {
                                "answer": item.raw_content,
                                "message_type": item.usage_metadata.type,
                            },
                        )
                    # ------------------

                    # 开启下一个取数任务
                    data_task = asyncio.create_task(async_iter.__anext__())
                except StopAsyncIteration:
                    break
            else:
                # 4. 触发心跳
                yield to_sse("MESSAGE", {"answer": "", "message_type": "heartbeat"})

        # 5. 发送 END
        yield to_sse("END", "")
    except JiuWenBaseException as e:
        logger.error("Streaming processing failed")
        yield to_error_sse(e)
    except Exception as e:
        logger.error("Streaming processing failed")
        yield to_error_sse(e)
    finally:
        if not data_task.done():
            data_task.cancel()


def _generate_optimize_task_job_id(
    json_data: dict,
    mode: str = "JNT",
):
    """
    Generates a job ID based on the request data and timestamp, with a prefix based on 'is_joint' parameter
    """
    json_data = json.dumps(json_data, sort_keys=True)
    timestamp = int(time.time() * 1000)
    sign_str = f"{json_data}|{timestamp}"
    return f"{mode}_{hashlib.sha256(sign_str.encode()).hexdigest()}"


def _error_sse_generator(e: Exception, task_id: str):
    """
    An error response data stream is generated when an error
    occurs during the NL2AGENT intent recognition phase.
    """

    start_payload = {"data": "", "event": "START", "conversationId": task_id}
    # 将整个字典转换为 JSON 字符串，并添加 'data: ' 前缀和换行符
    start_json = json.dumps(start_payload, ensure_ascii=False)
    yield f"data: {start_json}\n\n"

    # 尝试安全地获取错误代码和消息
    try:
        error_code = getattr(e, "error_code", "500")
        error_message = getattr(e, "message", str(e))
    except Exception:
        error_code = "500"
        error_message = str(e)
    if (
        error_code == 100029
        and error_message
        and "Model response error" in error_message
    ):
        error_message = "The model failed to identify the user's intent. Please switch to another model and try again. It is recommended to use the DeepSeek-V3 model."
    else:
        error_message = f"{NL2_FALLBACK_ERROR_MESSAGE}([{error_code}], {error_message})"
    error_payload = {
        "data": {"code": str(error_code), "message": str(error_message)},
        "event": "error",
        "conversationId": task_id,
    }
    error_json = json.dumps(error_payload, ensure_ascii=False)
    yield f"data: {error_json}\n\n"

    end_payload = {"data": "", "event": "END", "conversationId": task_id}
    end_json = json.dumps(end_payload, ensure_ascii=False)
    yield f"data: {end_json}\n\n"


def _nl2_get_error(error_item):
    """Attempt to safely retrieve error codes and messages"""
    try:
        error_code = getattr(error_item, "error_code", "500")
        error_message = getattr(error_item, "message", str(error_item))
    except Exception:
        error_code = "500"
        error_message = str(error_item)

    return error_code, error_message
