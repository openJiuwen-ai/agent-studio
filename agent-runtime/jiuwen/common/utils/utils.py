#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""util module"""

import base64
import io
import json
import os
import re
import socket
import time
from socket import inet_aton
from struct import unpack
from urllib.parse import urlparse, urlunparse

from jiuwen.common.configs.env_constants import (
    CLOSE_URL_JUDGE_SWITCH_KEY,
    PLUGIN_WHITE_URLS_KEY,
    URL_MAX_LEN_KEY,
)
from jiuwen.common.log.base import logger, performance_logger

MAX_UPLOAD_FILE_SIZE = 20 * 1024 * 1024
MAX_ENCODED_LENGTH = (
    MAX_UPLOAD_FILE_SIZE * 4 // 3
)  # base64编码后的内容长度是原始内容的4/3倍
# COM-08 §4.4: 删除模块级 LOG_VERBOSE_MODE——env 解析集中到
# DiagnosticPolicy.from_env()（jiuwen/common/log/diagnostics.py）。

# COM-08 §4.4: 无登记稳定 reason 时的通用安全阶段描述。
_GENERIC_SAFE_REASON = "internal error"


def safe_exception_reason(exception: Exception, reason: str | None = None) -> str:
    """COM-08 §4.4: 确定性安全异常原因。

    不读取 ``LOG_VERBOSE``，两种配置返回值完全相同；不返回 ``str(exception)``。

    - 有登记稳定 ``reason`` 时返回 ``reason``；
    - 无 ``reason`` 时返回通用安全阶段描述 ``_GENERIC_SAFE_REASON``；
    - 原始异常正文通过 cause chain / ``exc_info`` 保留，不进本返回值。
    """
    if reason is not None:
        return str(reason)
    return _GENERIC_SAFE_REASON


def format_exception_reason(exception: Exception, reason: str | None = None) -> str:
    """[Deprecated] COM-08 §4.4: 改用 :func:`safe_exception_reason`。

    保留为不读取环境变量的弃用兼容壳，行为等价于 ``safe_exception_reason``；
    不再随 ``LOG_VERBOSE`` 返回 ``str(exception)``。
    """
    return safe_exception_reason(exception, reason)


def safe_json_loads(json_string, default=None):
    """
    安全地将JSON字符串转换为Python对象。

    如果转换过程中出现任何异常，将返回默认值，并记录错误日志。

    Args:
        json_string (str): 要解析的JSON字符串。
        default (任何类型): 当解析失败时返回的默认值，默认为None。

    Returns:
        Python对象：解析后的JSON对象，或在解析失败时返回默认值。

    Raises:
        该函数不会抛出异常，所有异常都会被捕获并记录日志。
    """
    try:
        return json.loads(json_string)
    except json.JSONDecodeError as _:
        logger.error("JSON decode error")
        return default
    except TypeError as _:
        logger.error("Type error")
        return default
    except Exception as _:
        logger.error("Unexpected error")
        return default


def load_json(inputs):
    """将str 转成json"""
    try:
        return json.loads(inputs)
    except json.JSONDecodeError as e:
        raise ValueError("inputs decode to json error") from e


def safe_json_loads_raise_exception(json_string, parse_int=None):
    """
    安全地将JSON字符串转换为Python对象，并在出现异常时抛出。

    如果转换过程中出现任何异常，将记录错误日志，并抛出相应的ValueError异常。

    Args:
        json_string (str): 要解析的JSON字符串。
        parse_int (可选): 用于解析整数的函数，默认为None。

    Returns:
        Python对象：解析后的JSON对象。

    Raises:
        ValueError: 当JSON解码错误、类型错误或发生其他未预期错误时抛出。

    Notes:
        该函数旨在提供一个安全的JSON解析方法，确保在解析过程中出现异常时能够
        适当地处理并通知调用者。通过抛出异常，调用者可以捕获并处理这些异常。
    """
    try:
        return json.loads(json_string, parse_int=parse_int)
    except json.JSONDecodeError as e:
        logger.error("JSON decode error")
        raise ValueError("JSON decode error") from e
    except TypeError as e:
        logger.error("Type error")
        raise ValueError("Type error") from e
    except Exception as e:
        logger.error("Unexpected error")
        raise ValueError("Unexpected error") from e


def ip2long(ip_addr):
    """trans ip to long"""
    return unpack("!L", inet_aton(ip_addr))[0]


def is_inner_ipaddress(ip):
    """judge inner ip"""
    ip_long = ip2long(ip)
    is_inner_ip = (
        ip2long("10.0.0.0") <= ip_long <= ip2long("10.255.255.255")
        or ip2long("172.16.0.0") <= ip_long <= ip2long("172.31.255.255")
        or ip2long("192.168.0.0") <= ip_long <= ip2long("192.168.255.255")
        or ip2long("127.0.0.0") <= ip_long <= ip2long("127.255.255.255")
        or ip_long == ip2long("0.0.0.0")
    )
    return is_inner_ip


def illegal_url(url):
    """illegal url"""
    if not url or len(url) > int(os.getenv(URL_MAX_LEN_KEY, 2048)):
        return True
    # 必须是http 和 https开头
    if not re.match(r"^https?://.*$", url):
        return True
    # 默认是打开内网屏蔽，设置CLOSE_URL_JUDGE_SWITCH关闭内网屏蔽
    if os.environ.get(CLOSE_URL_JUDGE_SWITCH_KEY) in ["True", "true"]:
        return False
    # 内网屏蔽开启时 判断是否在url白名单
    if shot_plugin_white_urls(url):
        return False
    hostname = urlparse(url).hostname
    try:
        ip_address = socket.getaddrinfo(hostname, "http")[0][4][0]
    except Exception:
        return True

    return is_inner_ipaddress(ip_address)


def shot_plugin_white_urls(url):
    """judge plugin url in whitelist"""
    if isinstance(os.environ.get(PLUGIN_WHITE_URLS_KEY), str):
        urls = os.environ.get(PLUGIN_WHITE_URLS_KEY).split(",")
        if url in urls:
            logger.info("plugin url is in whitelist")
            return True
    return False


def url_to_ip_with_protocol_and_port(url):
    """url to ip"""
    parsed_url = urlparse(url)
    scheme = parsed_url.scheme
    hostname = parsed_url.hostname
    port = parsed_url.port
    if not re.match(r"^https?://.*$", url):
        raise ValueError("illegal url protocol")
    try:
        ip_address = socket.gethostbyname(hostname)
    except socket.error as e:
        raise ValueError("resolving IP address failed") from e
    if (
        os.environ.get(CLOSE_URL_JUDGE_SWITCH_KEY) not in ["True", "true"]
        and is_inner_ipaddress(ip_address)
        and not shot_plugin_white_urls(ip_address)
    ):
        raise ValueError("illegal ip address")
    new_url = urlunparse(
        (
            scheme,
            f"{ip_address}:{port}" if port else ip_address,
            parsed_url.path,
            parsed_url.params,
            parsed_url.query,
            parsed_url.fragment,
        )
    )
    return new_url, hostname


def illegal_logo_type(agent_logo):
    """illegal_logo_type"""
    pattern = r"^data:image/([^;]{1,100});base64,"
    match = re.match(pattern, agent_logo)
    if match:
        match_result = match.group(1)
        support_type = ["jpeg", "jpg", "png", "gif"]
        if match_result not in support_type:
            return True
        return False
    return True


def illegal_agent_logo(agent_logo):
    """illegal agent_logo judge"""
    if "base64," not in agent_logo:
        return True
    if illegal_logo_type(agent_logo=agent_logo):
        return True
    try:
        base64_data = agent_logo.split("base64,")[1]
        if not base64_data or len(base64_data) > MAX_ENCODED_LENGTH:
            return True
        agent_logo_str = base64.b64decode(base64_data)
    except Exception:
        return True
    agent_logo_header = io.BytesIO(agent_logo_str).read(24)
    return len(agent_logo_str) > MAX_UPLOAD_FILE_SIZE or len(agent_logo_header) != 24


def convert_camel_to_snake(dict_value: dict, skip_fields=None):
    """
    递归地将字典中所有键从驼峰命名法转换为下划线命名法。
    如果键包含非英文字符，则不进行转换。
    """
    if not skip_fields:
        skip_fields = list()

    # Helper function to convert a single string from camelCase to snake_case
    def camel_to_snake(name):
        # 如果名字只包含字母和数字（英文字符），则进行转换
        if all(c.isalnum() or c.isspace() for c in name):
            return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower()
        return name  # 如果包含非英文字符，则不转换

    # 判断输入是字典还是列表，递归处理
    if isinstance(dict_value, dict):  # 如果是字典
        return {
            camel_to_snake(k) if k not in skip_fields else k: convert_camel_to_snake(
                v, skip_fields
            )
            if k not in skip_fields
            else v
            for k, v in dict_value.items()
        }
    if isinstance(dict_value, list):  # 如果是列表
        return [convert_camel_to_snake(i) for i in dict_value]
    return dict_value


async def timed_cache_op(op_name: str, coro, ir_path: str):
    """执行缓存操作并打印耗时日志"""
    start_time = time.perf_counter()
    result = await coro
    end_time = time.perf_counter()
    execution_time = (end_time - start_time) * 1000
    performance_logger.info(
        f"{op_name} completed: {ir_path}, Execution time: {execution_time:.2f} ms"
    )
    return result
