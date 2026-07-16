# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import warnings
from copy import deepcopy
from typing import List

import ray
import vllm.entrypoints.openai.protocol
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from verl.workers.rollout.vllm_rollout.vllm_async_server import AsyncvLLMServer
from vllm.entrypoints.openai.protocol import ChatCompletionRequest, ErrorResponse
from vllm.entrypoints.openai.protocol import ChatCompletionResponse
from vllm.entrypoints.openai.serving_chat import OpenAIServingChat


class ChatCompletionResponsePatched(ChatCompletionResponse):
    """Extended response protocol with token IDs."""

    prompt_token_ids: List[int] | None = None
    response_token_ids: List[int] | None = None


original_chat_completion_full_generator = (
    OpenAIServingChat.chat_completion_full_generator
)


async def chat_completion_full_generator(
    self,
    request,
    result_generator,
    request_id: str,
    model_name: str,
    conversation,
    tokenizer,
    request_metadata,
):
    """Intercept generator to capture prompt and response token IDs."""
    prompt_token_ids: List[int] | None = None
    response_token_ids: List[List[int]] | None = None

    async def _generate_inceptor():
        nonlocal prompt_token_ids, response_token_ids
        async for res in result_generator:
            yield res
            prompt_token_ids = res.prompt_token_ids
            response_token_ids = [output.token_ids for output in res.outputs]

    response = await original_chat_completion_full_generator(
        self,
        request,
        _generate_inceptor(),
        request_id,
        model_name,
        conversation,
        tokenizer,
        request_metadata,
    )

    response = response.model_copy(
        update={
            "prompt_token_ids": prompt_token_ids,
            "response_token_ids": response_token_ids,
        }
    )

    return response


def instrument_vllm():
    """Patch vLLM protocols and methods to include token IDs."""
    if (
        vllm.entrypoints.openai.protocol.ChatCompletionResponse
        is ChatCompletionResponsePatched
    ):
        warnings.warn("vLLM is already instrumented. Skip the instrumentation.")
        return

    vllm.entrypoints.openai.protocol.ChatCompletionResponse = (
        ChatCompletionResponsePatched
    )
    OpenAIServingChat.chat_completion_full_generator = chat_completion_full_generator


def _unwrap_ray_remote(cls):
    """Extract original class from Ray actor wrapper."""
    if hasattr(cls, "__ray_actor_class__"):
        cls = cls.__ray_actor_class__
    return cls


@ray.remote(num_cpus=1)
class PatchedvLLMServer(_unwrap_ray_remote(AsyncvLLMServer)):
    """Enhanced vLLM server with custom response format and token IDs."""

    def __init__(self, *args, **kwargs):
        instrument_vllm()
        super().__init__(*args, **kwargs)

        self.config = deepcopy(self.config)
        self.config.rollout.multi_turn.tool_config_path = "/dev/null"

    async def chat_completion(self, raw_request: Request):
        """OpenAI-compatible HTTP endpoint for chat completions."""
        request_json = await raw_request.json()
        request = ChatCompletionRequest(**request_json)
        generator = await self.openai_serving_chat.create_chat_completion(
            request, raw_request
        )

        if isinstance(generator, ErrorResponse):
            return JSONResponse(
                content=generator.model_dump(), status_code=generator.code
            )
        if request.stream:
            return StreamingResponse(content=generator, media_type="text/event-stream")
        return JSONResponse(content=generator.model_dump())
