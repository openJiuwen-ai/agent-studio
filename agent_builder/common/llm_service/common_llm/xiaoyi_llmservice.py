#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
"""
xiaoyi llm service
"""

import json
import os
import secrets
from typing import List, Iterator

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.prompt.common.config import LLMModelInfo
from agent_builder.adapter.exception_bridge import JiuWenBaseException

TRUE_LITERAL = "true"


class XiaoyiLLM:
    """Class representing xiaoyi llm request"""

    def __init__(self, model_info: LLMModelInfo, **kwargs):
        self.url = os.environ.get("PROMPT_MODEL_URL", "")
        self.api_key = os.environ.get("PROMPT_MODEL_API_KEY", "")

        self.model_name = model_info.model

        if self.url == "" or self.model_name == "" or self.api_key == "":
            raise JiuWenBaseException(
                StatusCode.LLM_CONFIG_MISS_ERROR.code,
                StatusCode.LLM_CONFIG_MISS_ERROR.errmsg.format(
                    error_msg="please check url, model, apikey"
                ),
            )
        self.session_id = model_info.headers.get(
            "session_id", str(secrets.token_hex(24))
        )
        self.device_info = model_info.headers.get("device_info", None)
        self.user_info = model_info.headers.get("user_info", None)
        from agent_builder.prompt.agent.common.llm_service import ComponentLLMService

        ssl_verify = os.environ.get("PROMPT_MODEL_SSL_VERIFY", TRUE_LITERAL)
        ssl_certification_path = os.environ.get(
            "PROMPT_MODEL_SSL_CERTIFICATION_PATH", ""
        )
        ssl_client_cert_path = os.environ.get("PROMPT_MODEL_SSL_CLIENT_CERT_PATH", "")
        ssl_client_key_path = os.environ.get("PROMPT_MODEL_SSL_CLIENT_KEY_PATH", "")
        ssl_encrypt_key = os.environ.get("PROMPT_MODEL_SSL_ENCRYPT_KEY", "")
        self.llm = ComponentLLMService(
            url=self.url,
            model_name=self.model_name,
            api_key=self.api_key,
            session_id=self.session_id,
            ssl_verify=ssl_verify == TRUE_LITERAL,
            ssl_certification_path=ssl_certification_path,
            ssl_client_cert_path=ssl_client_cert_path,
            ssl_client_key_path=ssl_client_key_path,
            ssl_encrypt_key=ssl_encrypt_key,
            device_info=self.device_info,
            user_info=self.user_info,
        )

    def stream_chat(self, messages: List[dict], **kwargs) -> Iterator[dict]:
        """Function representing llm stream result"""
        type_str = "type"
        metadata_str = "metadata"
        message_str = "message"
        model_str = "modelName"
        content_str = "content"

        for item in self.llm.stream_chat(messages=messages):
            if (
                type_str not in item.keys()
                or metadata_str not in item.keys()
                or message_str not in item.keys()
            ):
                raise JiuWenBaseException(
                    StatusCode.LLM_FORMAT_ERROR.code,
                    StatusCode.LLM_FORMAT_ERROR.errmsg.format(
                        error_msg="source llm returned message."
                    ),
                )

            if model_str not in item.get(metadata_str) or content_str not in item.get(
                message_str
            ):
                raise JiuWenBaseException(
                    StatusCode.LLM_FORMAT_ERROR.code,
                    StatusCode.LLM_FORMAT_ERROR.errmsg.format(
                        error_msg="source llm returned message."
                    ),
                )

            if item.get(type_str, "") == "stream_token":
                finish_reason = "null"
                err_code = 0
            else:
                finish_reason = "stop"
                err_code = 200
            result = {
                "errCode": err_code,
                "errMessage": "成功",
                "result": {
                    "id": item.get(metadata_str, {}).get(model_str, ""),
                    "object": "chat.completion",
                    "model": item.get(metadata_str, {}).get(model_str, ""),
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": finish_reason,
                            message_str: {
                                "role": "assistant",
                                content_str: item.get(message_str, {}).get(
                                    content_str, ""
                                ),
                                "latency": 0,
                                "function_call": None,
                            },
                        }
                    ],
                },
            }
            yield "data:" + json.dumps(result, ensure_ascii=False)
