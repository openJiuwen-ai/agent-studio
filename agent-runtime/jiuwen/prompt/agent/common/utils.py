#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
"""
utils for components
"""

import json
import re
from datetime import datetime, timezone, timedelta
from enum import Enum

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode

MASK_STAR_NUM = 8
STREAM_TEXT_LITERAL = "streamText"
TYPE_LITERAL = "type"
MESSAGE_LITERAL = "message"
METADATA_LITERAL = "metadata"
PARSED_DATA_LITERAL = "parsedData"
CONTENT_LITERAL = "content"
REASONING_CONTENT_LITERAL = "reasoning_content"
RESULT_LITERAL = "result"
STREAM_TYPE_LITERAL = "streamType"
TOOL_CALLS_LITERAL = "tool_calls"
CACHED_TOKENS_LITERAL = "cached_tokens"
STREAMING_TEXT_ID_LITERAL = "streaming_text_id"
CHAT_HISTORY_LITERAL = "chat_history"
TOOLS_LITERAL = "tools"
DESC_LITERAL = "desc"


class StreamType(Enum):
    """stream types"""

    START = "start"
    PARTIAL = "partial"
    FINAL = "final"


class LLMResponseType(Enum):
    """llm response types"""

    STREAM_TOKEN = "stream_token"
    FULL_RESULT = "full_result"


def mask_sensitive_text():
    """
    屏蔽敏感信息
    """
    return "*" * MASK_STAR_NUM


def camel_to_snake(camel_dict):
    """convert camel case to snake case"""
    snake_dict = {}
    for name, value in camel_dict.items():
        name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        name = re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()
        snake_dict[name] = value
    return snake_dict


def raise_invalid_params_error(error_msg=""):
    """raise_invalid_params_error"""
    raise JiuWenBaseException(
        StatusCode.PROMPT_JSON_SCHEMA_ERROR.code,
        StatusCode.PROMPT_JSON_SCHEMA_ERROR.errmsg.format(error_msg=error_msg),
    )


def format_prompt(
    history: list[dict], response_format: dict, outputs_config_list: list
) -> list[dict]:
    """Format the last user message with instructions based on response type (text, markdown, json).

    Args:
        history: Conversation history as list of {'role': str, 'content': str}.
        response_format: Dict with 'type' and optional 'markdownInstruction'/'jsonInstruction'.
        outputs_config_list: List of field configs for JSON schema generation.

    Returns:
        Updated history with formatted user message.
    """
    res_type = response_format.get("type")
    if res_type == "text":
        return history
    if res_type == "markdown":
        default_request = """Please return the answer in markdown format
        - For headings, use number signs (#).
        - For list items, start with dashes (-).
        - To emphasize text, wrap it with asterisks (*).
        - For code or commands, surround them with backticks ().
        - For quoted text, use greater than signs (>).
        - For links, wrap the text in square brackets [], followed by the URL in parentheses ().
        - For images, use square brackets [] for the alt text, followed by the image URL in parentheses ().
        The question is: ${query}.
        """
        output_request = response_format.get("markdownInstruction", default_request)
        if output_request is None or output_request == "":
            output_request = default_request
    elif res_type == "json":
        if not isinstance(outputs_config_list, list):
            raise_invalid_params_error(error_msg="outputs_config is not a list type")

        json_schema = convert_json_schema(outputs_config_list)
        default_request = """Carefully consider the user's question to ensure your answer is logical and makes sense.
         - Make sure your explanation is concise and easy to understand, not verbose.
         - Strictly return the answer in a valid json format only, and "DO NOT ADD ANY COMMENTS BEFORE OR AFTER IT" 
           to ensure it could be formatted as a JSON instance that conforms to the JSON schema below. Here is the
           JSON schema:${json_schema}.
         The question is: ${query}.
         """
        output_request = response_format.get("jsonInstruction", default_request)
        if output_request is None or output_request == "":
            output_request = default_request
        output_request = output_request.replace(
            "${json_schema}", json.dumps(json_schema, ensure_ascii=False)
        )
    else:
        raise_invalid_params_error(error_msg=f"'{res_type}' is not supported")

    last_index = None
    for index, data in enumerate(history):
        if data.get("role") == "user":
            last_index = index
    if last_index is not None:
        # NOTE: 不做 html.escape。此处 content 是渲染后的工作流模板,
        # 即模型文本 Prompt,HTML 转义会改变语义:其中合法包含 JSON
        # 示例引号("key": "value")与 "&" 连接符(如 "e5051&n消费卡");
        # html.escape 会把它们转义成 &quot; / &amp;,破坏格式指令。
        history[last_index]["content"] = output_request.replace(
            "${query}", history[last_index]["content"]
        )
    return history


def format_response(
    response_content: str,
    response_type: str,
    outputs_config: dict,
    outputs_config_list: list,
) -> dict:
    """Format the model response based on response type and schema constraints.

    Args:
        response_content: Raw response string from the model.
        response_type: Type of response ('text', 'markdown', or 'json').
        outputs_config: Mapping of output field names to their types or instructions.
        outputs_config_list: List of field configurations for JSON schema validation.

    Returns:
        Formatted output dictionary matching the expected structure.
    """
    if not isinstance(outputs_config, dict):
        raise_invalid_params_error(error_msg="outputs_config is not a dict type")

    if response_type in ["text", "markdown"]:
        output = {}
        if (
            len(outputs_config.items()) == 2
            and outputs_config.get(REASONING_CONTENT_LITERAL) is not None
        ):
            for k in list(outputs_config.keys()):
                if k != REASONING_CONTENT_LITERAL:
                    output[k] = response_content
                    break
        elif len(outputs_config.items()) != 1:
            raise_invalid_params_error(
                error_msg="outputs_config must contain only one element when response_type is 'text' or 'markdown'"
            )
        output[list(outputs_config.keys())[0]] = response_content
        return output
    if response_type == "json":
        return _format_json_response(
            outputs_config, outputs_config_list, response_content
        )
    raise_invalid_params_error(
        error_msg="response_type is not supported which should be text, markdown or json."
    )
    return {}


def _format_json_response(
    outputs_config: dict, outputs_config_list: list, response_content: str
):
    output = {}
    if len(outputs_config.items()) < 1:
        raise_invalid_params_error(
            error_msg="outputs_config must contain more than one element when response_type is 'json'"
        )
    try:
        # 处理存在前缀的json格式
        response_content = response_content.strip()
        if response_content.startswith("```") and response_content.endswith("```"):
            response_content = response_content.lstrip("```json").rstrip("```")
        res = json.loads(response_content)
    except Exception as e:
        raise JiuWenBaseException(
            StatusCode.PROMPT_JSON_SCHEMA_ERROR.code,
            StatusCode.PROMPT_JSON_SCHEMA_ERROR.errmsg.format(
                error_msg="response_content is not a valid json."
            ),
        ) from e
    json_schema = convert_json_schema(outputs_config_list)
    try:
        validate(instance=res, schema=json_schema)
    except JiuWenBaseException as e:
        raise e
    except Exception as e:
        raise JiuWenBaseException(
            StatusCode.PROMPT_JSON_SCHEMA_ERROR.code,
            StatusCode.PROMPT_JSON_SCHEMA_ERROR.errmsg.format(
                error_msg="response_content json schema validation error."
            ),
        ) from e

    for k, value in outputs_config.items():
        if k == REASONING_CONTENT_LITERAL:
            continue
        if res.get(k) is None:
            if value.get("required"):
                raise_invalid_params_error(error_msg=f"No key {k} in response_content")
        else:
            output[k] = res[k]
    return output


def convert_json_schema(schema_data: list):
    """
    Convert custom schema format to standard JSON Schema format.
    """

    def convert_type(type_str):
        """Convert custom type names to JSON Schema types."""
        type_mapping = {
            "String": "string",
            "Int": "integer",
            "Map": "object",
            "List": "array",
            "Float": "number",
            "Boolean": "boolean",
        }
        return type_mapping.get(type_str, type_str.lower())

    def process_schema_item(item):
        """Process a single schema item recursively."""
        if not isinstance(item, dict):
            return {"type": convert_type(item)}

        result = {}

        if "type" in item:
            schema_type = convert_type(item["type"])
            result["type"] = schema_type

            if "description" in item:
                result["description"] = item["description"]

            if schema_type == "object" and "schema" in item:
                result["properties"] = {}
                result["required"] = []

                for prop in item["schema"]:
                    prop_name = prop["id"]
                    result["properties"][prop_name] = process_schema_item(prop)
                    if prop.get("required", False):
                        result["required"].append(prop_name)

            elif schema_type == "array" and "schema" in item:
                result["items"] = process_schema_item(item["schema"])
            # Note: 'required' field should only exist at object type level as an array,
            # not in basic type schemas (string, integer, number, boolean, array items)

        return result

    root_schema = {"type": "object", "properties": {}, "required": []}

    for item in schema_data:
        prop_name = item["id"]
        if prop_name == REASONING_CONTENT_LITERAL:
            continue
        root_schema["properties"][prop_name] = process_schema_item(item)
        if item.get("required", False):
            root_schema["required"].append(prop_name)

    return root_schema


def validate_type(instance, expected_type):
    """校验schema json实例类型: object, array, string, integer, boolean, and number types."""
    if expected_type == "object" and not isinstance(instance, dict):
        raise_invalid_params_error(
            "instance validate error: Expected object, got {type(instance).__name__}"
        )
    elif expected_type == "array" and not isinstance(instance, list):
        raise_invalid_params_error(
            "instance validate error: Expected array, got {type(instance).__name__}"
        )
    elif expected_type == "string" and not isinstance(instance, str):
        raise_invalid_params_error(
            "instance validate error: Expected string, got {type(instance).__name__}"
        )
    elif expected_type == "integer" and not isinstance(instance, int):
        raise_invalid_params_error(
            "instance validate error: Expected integer, got {type(instance).__name__}"
        )
    elif expected_type == "boolean" and not isinstance(instance, bool):
        raise_invalid_params_error(
            "instance validate error: Expected boolean, got {type(instance).__name__}"
        )
    elif expected_type == "number" and not isinstance(instance, (int, float)):
        raise_invalid_params_error(
            "instance validate error: Expected number, got {type(instance).__name__}"
        )


def validate(instance, schema):
    """
    对json schema实例进行schema校验type类型和缺失.
    """
    validate_type(instance, schema["type"])

    if schema["type"] == "object" and "properties" in schema:
        # Check required properties from top-level required array (standard JSON Schema format)
        required_props = schema.get("required", [])

        for prop_name, prop_schema in schema["properties"].items():
            # Check if property is required (standard JSON Schema: in required array)
            if prop_name in required_props and prop_name not in instance:
                raise_invalid_params_error("Missing required property.")

            if prop_name in instance:
                validate(instance[prop_name], prop_schema)

    elif schema["type"] == "array" and "items" in schema:
        for _, item in enumerate(instance):
            validate(item, schema["items"])


def get_current_time():
    """get current time"""
    now = datetime.now(tz=timezone.utc)
    local_time = now + timedelta(hours=8)
    weekdays = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    weekday = weekdays[local_time.weekday()]
    return (
        f"It is {local_time.year}/{local_time.month:02d}/{local_time.day:02d} {local_time.hour:02d}"
        f":{local_time.minute:02d}:{local_time.second:02d} {weekday} now."
    )
