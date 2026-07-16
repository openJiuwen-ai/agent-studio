#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
"""
LLM Service for Component
"""

import ast
import json
import os
import time
from typing import Iterator, List

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.common.logging.base import interface_logger, logger
from agent_builder.common.utils.utils import sanitize_input
from agent_builder.serve.common.ssl_ctx import set_ssl_cert
from agent_builder.adapter.exception_bridge import JiuWenBaseException
from websockets.exceptions import ConnectionClosedOK
from websockets.sync.client import connect

TEXT_STR = "text"
LLM_OPEN_TIMEOUT = "8.5"
LLM_MID_TIMEOUT = "4"
DESC_LITERAL = "desc"
MASK_STAR_NUM = 8

LLM_CONNECT_OPEN_TIMEOUT = ast.literal_eval(
    os.environ.get("JIUWEN_LLM_OPEN_TIMEOUT", LLM_OPEN_TIMEOUT)
)
LLM_CONNECT_MID_TIMEOUT = ast.literal_eval(
    os.environ.get("JIUWEN_LLM_MID_TIMEOUT", LLM_MID_TIMEOUT)
)


def mask_sensitive_text():
    """
    屏蔽敏感信息
    """
    return "*" * MASK_STAR_NUM


class WebsocketConnection:
    """Websocket connection class"""

    def __init__(
        self,
        url: str,
        model_name: str,
        api_key: str,
        device_info: dict = None,
        user_info: dict = None,
        session_id: str = None,
        ssl_verify: bool = True,
        ssl_certification_path: str = None,
        request_timeout=10,
        ssl_client_key_path: str = None,
        ssl_client_cert_path: str = None,
        ssl_encrypt_key: str = None,
    ):
        self.url = url
        self.model_name = model_name
        self.api_key = api_key
        self.device_info = device_info
        self.user_info = user_info
        self.session_id = session_id
        self.data = None
        self.websocket_open_information = "Websocket connection is opened."
        self.websocket_close_information = "Websocket connection is closed."
        self.service_start_time = None
        if ssl_verify:
            self.ssl_context = set_ssl_cert(
                ssl_client_cert_path,
                ssl_client_key_path,
                ssl_certification_path,
                ssl_encrypt_key,
                ssl_type="client",
            )
        else:
            self.ssl_context = None
        self.request_timeout = request_timeout
        logger.info(
            f"LLM service first timeout is: {sanitize_input(self.request_timeout)}"
        )
        logger.info(
            f"LLM service connect timeout is: {sanitize_input(LLM_CONNECT_OPEN_TIMEOUT)}, "
            f"middle token timeout is: {sanitize_input(LLM_CONNECT_MID_TIMEOUT)}"
        )

    @staticmethod
    def prepare_output(
        content: str,
        content_type: str,
        metadata: dict,
        llm_content: str = None,
        tool_calls: dict = None,
    ) -> dict:
        """prepare output for streaming output"""
        index_str = "index"
        id_str = "id"
        message = dict(role="assistant", content=content)
        if llm_content:
            message.update({"llm_content": llm_content})
        if tool_calls:
            new_tools = []
            old_tools = tool_calls
            for old_tool in old_tools:
                new_tools.append(
                    {"type": old_tool.get("type"), "function": old_tool.get("function")}
                )
                if old_tool.get(index_str) is not None:
                    new_tools[-1].update({index_str: old_tool.get(index_str)})
                if old_tool.get(id_str) is not None:
                    new_tools[-1].update({id_str: old_tool.get(id_str)})
            message.update({"tool_calls": new_tools})
        return dict(message=message, metadata=metadata, type=content_type)

    @staticmethod
    def construct_metadata(model_request_info: dict):
        """construct metadata from service outputs"""
        contentbean_str = "contentBean"
        input_tokens = model_request_info.get(contentbean_str).get("inputTokenNum")
        output_tokens = model_request_info.get(contentbean_str).get("generateTokenNum")
        model_time = model_request_info.get(contentbean_str).get("modelTime")
        model_name = model_request_info.get("modelName")
        llm_label = model_request_info.get("llmLabel")
        try:
            average_token_latency = "{:.2f}".format(float(model_time) / output_tokens)
        except Exception as error:
            logger.info(
                f"LLM service error parsing token latency due to: {sanitize_input(error)}"
            )
            average_token_latency = None
        metadata = {
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
            "modelTime": model_time,
            "modelName": model_name,
            "llmLabel": llm_label,
            "averageTokenLatency": average_token_latency,
            "totalTokens": input_tokens + output_tokens,
            "firstTokenLatency": int(
                model_request_info.get(contentbean_str).get("firstCostTime")
            ),
            "errorCode": model_request_info.get(contentbean_str).get("errorCode"),
        }
        return metadata

    def run(self, messages, tools=None):
        """run connection and get result generator"""
        body_str = "body"
        self.data = {
            "session": {"sessionId": mask_sensitive_text()},
            body_str: {
                "apiKey": mask_sensitive_text(),
                "modelName": self.model_name,
                "deviceInfo": mask_sensitive_text(),
                "userInfo": mask_sensitive_text(),
                "messages": messages,
            },
        }
        if tools:
            if isinstance(tools, str):
                tools = json.loads(tools)
            self.data.get(body_str).update({"tools": tools})
        logger.info("LLM Service request info (with sensitive info masked): ******")
        self.data["session"]["sessionId"] = self.session_id
        self.data[body_str]["apiKey"] = self.api_key
        self.data[body_str]["deviceInfo"] = self.device_info
        self.data[body_str]["userInfo"] = self.user_info
        return self.connection_thread()

    def print_interface_log(self, code):
        """print_interface_log"""
        log_service = "LLMService"
        log_position = ""
        log_version = "V1.0"
        log_type = "req"
        log_interface_name = "LLMService"
        log_source_id = ""
        log_response_time = int(1000 * (time.time() - self.service_start_time))
        log_flag = "T" if code == 0 else "F"
        log_return_code = code
        interface_logger.info(
            f"{log_service}|{log_position}|{log_version}|{log_type}|"
            f"{log_interface_name}|{log_source_id}|log_dest_id|{log_response_time}|{log_flag}|"
            f"{sanitize_input(log_return_code)}|log_translocation_id"
        )

    def connection_thread(self) -> Iterator[dict]:
        """thread for the connection run."""
        self.service_start_time = time.time()
        first_token_time = None
        try:
            with connect(
                self.url,
                ssl_context=self.ssl_context,
                open_timeout=LLM_CONNECT_OPEN_TIMEOUT,
            ) as websocket:
                websocket.send(json.dumps(self.data))
                fed_prompt = None
                previous_text_len = 0
                while True:
                    try:
                        if not fed_prompt:
                            recv_info = websocket.recv(timeout=self.request_timeout)
                        else:
                            recv_info = websocket.recv(timeout=LLM_CONNECT_MID_TIMEOUT)

                        if first_token_time is None:
                            first_token_time = int(time.time() * 1000)
                        msg_dict = json.loads(recv_info)
                        code = msg_dict.get("code")
                        if code != 0:
                            logger.error(
                                "LLM service returned false result due to: {error_msg}".format(
                                    error_msg=f"(Code {sanitize_input(code)}) msg_dict ******"
                                )
                            )
                            self.print_interface_log(code)
                            raise JiuWenBaseException(
                                StatusCode.LLM_FALSE_RESULT_ERROR.code,
                                StatusCode.LLM_FALSE_RESULT_ERROR.errmsg.format(
                                    error_msg=f"(Code {code}) msg_dict ******"
                                ),
                            )
                        if not fed_prompt:
                            fed_prompt = msg_dict.get("result", {}).get("prompt")
                        model_request_info = msg_dict.get("modelRequestInfo", {})
                        metadata = self.construct_metadata(model_request_info)
                        metadata["startTime"] = int(self.service_start_time * 1000)
                        metadata["firstTokenTime"] = int(first_token_time * 1000)
                        result = msg_dict.get("result")
                        text = result.get(TEXT_STR, "")[previous_text_len:]
                        previous_text_len = len(result.get(TEXT_STR, ""))
                        if len(text) > 0:
                            yield self.prepare_output(
                                content=text,
                                content_type="stream_token",
                                metadata=metadata,
                            )
                        if result.get("type") == "finalText":
                            logger.info(
                                sanitize_input(self.websocket_close_information)
                            )
                            self.print_interface_log(code)
                            metadata["endTime"] = int(time.time() * 1000)
                            yield self.prepare_output(
                                content=result.get(TEXT_STR),
                                llm_content=result.get("llmText"),
                                content_type="full_result",
                                metadata=metadata,
                                tool_calls=result.get("toolCalls"),
                            )
                            break
                        if result.get("type") == "toolEndText":
                            logger.info(
                                sanitize_input(self.websocket_close_information)
                            )
                            self.print_interface_log(code)
                            metadata["endTime"] = int(time.time() * 1000)
                            yield self.prepare_output(
                                content=result.get("text"),
                                llm_content=result.get("llmText"),
                                content_type="full_result",
                                metadata=metadata,
                                tool_calls=result.get("toolCalls"),
                            )
                            break
                    except ConnectionClosedOK:
                        self.print_interface_log(0)
                        logger.info(sanitize_input(self.websocket_close_information))
                        break
                    except TimeoutError as error:
                        self.print_interface_log(-1)
                        raise JiuWenBaseException(
                            StatusCode.LLM_CONNECTION_ERROR.code,
                            StatusCode.LLM_CONNECTION_ERROR.errmsg.format(
                                error_msg="llm service receive info timeout."
                            ),
                        ) from error
                    except Exception as error:
                        self.print_interface_log(-1)
                        raise JiuWenBaseException(
                            StatusCode.LLM_CONNECTION_ERROR.code,
                            StatusCode.LLM_CONNECTION_ERROR.errmsg.format(
                                error_msg=str(error)
                            ),
                        ) from error
        except Exception as error:
            self.print_interface_log(-1)
            if isinstance(error, JiuWenBaseException):
                raise error
            raise JiuWenBaseException(
                StatusCode.LLM_CONNECTION_ERROR.code,
                StatusCode.LLM_CONNECTION_ERROR.errmsg.format(error_msg=str(error)),
            ) from error


class ComponentLLMService:
    """LLM Service for component."""

    def __init__(
        self,
        url: str,
        model_name: str,
        api_key: str,
        device_info: dict = None,
        user_info: dict = None,
        session_id: str = None,
        ssl_verify: bool = True,
        ssl_certification_path: str = None,
        **kwargs,
    ):
        self.url = url
        self.model_name = model_name
        self.api_key = api_key
        self.device_info = device_info
        self.user_info = user_info
        self.session_id = session_id
        self.ssl_verify = ssl_verify
        self.ssl_certification_path = ssl_certification_path
        self.request_timeout = kwargs.get("request_timeout", 20)
        self.ssl_client_cert_path = kwargs.get("ssl_client_cert_path", "")
        self.ssl_client_key_path = kwargs.get("ssl_client_key_path", "")
        self.ssl_encrypt_key = kwargs.get("ssl_encrypt_key", "")

    @staticmethod
    def format_messages(messages: List[dict]) -> List[dict]:
        """convert standard messages into llm service format."""
        formatted_messages = []
        for message in messages:
            role = message["role"]
            if role == "assistant":
                if "llm_content" in message:
                    message["llmContent"] = message.pop("llm_content")
                if "tool_calls" in message:
                    message["toolCalls"] = message.pop("tool_calls")
            if role == "tool" and "tool_call_id" in message:
                message["toolCallId"] = message.pop("tool_call_id")
            formatted_messages.append(message)
        return formatted_messages

    @classmethod
    def from_config(cls, service_type, url, model_name, **kwargs):
        """create llm instance."""
        if service_type == "llm_service":
            return ComponentLLMService(url=url, model_name=model_name, **kwargs)
        raise JiuWenBaseException(
            StatusCode.LLM_SERVICE_TYPE_ERROR.code,
            StatusCode.LLM_SERVICE_TYPE_ERROR.errmsg.format(
                error_msg=str(service_type)
            ),
        )

    def stream_chat(
        self, messages: List[dict], tools: List[dict] = None, **kwargs
    ) -> Iterator[dict]:
        """input messages and get generator output."""
        connection = WebsocketConnection(
            url=self.url,
            model_name=self.model_name,
            api_key=self.api_key,
            session_id=self.session_id,
            device_info=self.device_info,
            user_info=self.user_info,
            ssl_verify=self.ssl_verify,
            ssl_certification_path=self.ssl_certification_path,
            request_timeout=self.request_timeout,
            ssl_client_cert_path=self.ssl_client_cert_path,
            ssl_client_key_path=self.ssl_client_key_path,
            ssl_encrypt_key=self.ssl_encrypt_key,
        )
        return connection.run(messages=self.format_messages(messages), tools=tools)
