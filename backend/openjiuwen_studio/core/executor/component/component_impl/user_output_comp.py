#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved

import re
from typing import Any, AsyncIterator, AsyncGenerator
import asyncio
import json

from openjiuwen.core.workflow import WorkflowComponent, Input, Output
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.session.node import Session
from openjiuwen.core.session.stream import OutputSchema
from openjiuwen.core.common.utils.dict_utils import extract_leaf_nodes, format_path
from openjiuwen.core.common.logging import logger
from openjiuwen.core.workflow.components.flow.end_comp import TemplateProcessor, TemplateBatchProcessor

from openjiuwen_studio.core.common.dsl import UserOutputConfig
from openjiuwen_studio.core.common.exceptions import JiuWenExecuteException
from openjiuwen_studio.core.common.status_code import StatusCode
# {
#     "id": "UserOutput1",
#     "version": "",
#     "name": "",
#     "description": "",
#     "type": "jiuwen.UserOutputComponent",
#     "typeVersion": "1.0.0",
#     "inputs": {
#         "input1": "${LLM1}",
#         "input2": "${LLM2}"
#       },
#     "outputs": {},
#     "configs": {
#       "streaming":True
#       #"output_message":"just do it!!"
#       "output_message":"{{input2}}wwwww"
#      },
# }

STREAM_TIMEOUT = 5.0


def has_double_braces(s: str) -> bool:
    # 模式解释：\{\{ 匹配 {{，.*? 匹配任意字符（非贪婪模式），\}\} 匹配 }}
    pattern = r'\{\{.*?\}\}'
    return bool(re.search(pattern, s))


def render_template(template: str, inputs: dict) -> str:
    pattern = re.compile(r'\{\{(\w+)}}')
    # 替换所有匹配的变量
    return pattern.sub(lambda match: str(inputs.get(match.group(1), match.group(0))), template)


class UserOutputComponent(WorkflowComponent):
    def __init__(self, node_id: str, conf: UserOutputConfig) -> None:
        super().__init__()
        self.conf = conf
        self.node_id = node_id
        self.template_processor = None
        # self.output_writer = None
        self._batch_template = None
        self._mix = False
        if self.conf.output_message != "":
            self.template_processor = TemplateProcessor(self.conf.output_message)

    def set_mix(self):
        self._mix = True

    async def _render(self, inputs: Input, session: Session):
        if self._batch_template is None:
            processor = TemplateBatchProcessor(self.template_processor, inputs)
            self._batch_template = processor
            if self._mix:
                async with self._batch_template.condition:
                    try:
                        await asyncio.wait_for(self._batch_template.condition.wait(),
                                               timeout=0.2)  # set timeout by config
                    except asyncio.TimeoutError as e:
                        logger.error(f"render template stream timeout, {e}")
                        return None
                self._batch_template = None
                return None
        answer = await self._batch_template.render(inputs)
        async with self._batch_template.condition:
            self._batch_template.condition.notify_all()
        self._batch_template = None
        await self.create_output_result(answer, session)
        return {
            "output": answer,
        }

    async def invoke(self, inputs: Input, session: Session, context: ModelContext) -> Output:
        logger.debug(f"user output component invoke method")
        output_message = self.conf.output_message
        if output_message:
            if has_double_braces(output_message):
                result = render_template(output_message, inputs)
            else:
                result = output_message
        else:
            result = inputs
        await self.create_output_result(result, session)
        return {
            "output": result
        }

    async def stream(self, inputs: Input, session: Session, context: ModelContext) -> AsyncIterator[Output]:
        logger.debug(f"user output component stream method")
        try:
            if self.template_processor is not None:
                generator = self.template_processor.render_stream(inputs, STREAM_TIMEOUT)
                async for frame in generator:
                    logger.debug(f"user output component stream, frame={frame}")
                    result = await self.create_output_result(frame, session)
                    yield result
            else:
                if inputs is None:
                    return
                for key, value in inputs.items():
                    result = await self.create_output_result({key: value}, session)
                    yield result

        except Exception as e:
            logger.error("stream output error: {}".format(e))
            raise JiuWenExecuteException(
                StatusCode.USER_OUTPUT_COMPONENT_INVOKE_ERROR.code,
                StatusCode.USER_OUTPUT_COMPONENT_INVOKE_ERROR.errmsg.format(msg=f"stream output error: {e}"),
                node_id=self.node_id
            ) from e

    async def transform(self, inputs: Input, session: Session, context: ModelContext) -> AsyncIterator[Output]:
        logger.debug(f"user output component transform method")
        if self.template_processor is not None:
            generator = self.template_processor.render_stream(inputs, STREAM_TIMEOUT)
            async for frame in generator:
                logger.debug(f"user output component transform, frame={frame}")
                result = await self.create_output_result(frame, session)
                yield result
        else:
            for (path, value) in extract_leaf_nodes(inputs):
                if isinstance(value, AsyncGenerator):
                    async for frame in value:
                        result = await self.create_output_result({format_path(path): frame}, session)
                        yield result
                else:
                    result = await self.create_output_result({format_path(path): value}, session)
                    yield result

    async def collect(self, inputs: Input, session: Session, context: ModelContext) -> Output:
        logger.debug(f"user output component collect method")
        if self.template_processor is not None:
            return await self._render(inputs, session)
        else:
            chunks = []
            for (path, value) in extract_leaf_nodes(inputs):
                if isinstance(value, AsyncGenerator):
                    async for frame in value:
                        chunks.append({format_path(path): frame})
                else:
                    chunks.append({format_path(path): value})
            await self.create_output_result(chunks, session)
            return {
                "output": chunks
            }

    async def create_output_result(self, output_content, session: Session):
        """创建统一的输出结果格式"""
        logger.debug(f"create_output_result output_content: {output_content}")
        if not isinstance(output_content, str):
            if output_content.get("data"):
                output_content = output_content["data"]
            else:
                if isinstance(output_content, dict):
                    result = ""
                    for key, value in output_content.items():
                        # 根据键名决定使用哪种冒号
                            result += f"{key}:{value} \n "
                    # 去掉末尾可能多余的空格和换行
                    output_content = result.strip()
        result = {
            "output": output_content,
            "result_type": "answer",
            "node_id":  self.node_id,
        }
        output_schema = OutputSchema(type="output", index=0, payload=result)
        logger.debug(f"create_output_result output_schema: {output_schema}")
        await session.write_stream(output_schema)
        return output_schema
