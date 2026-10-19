#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""util module"""

import base64
import contextlib
import io
import json
import os
import re
import socket
import threading
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
    """judge inner ip

    内网段与 Java 侧 urlCheckUtils.isInternalIp 对齐：
    isSiteLocalAddress（10/8、172.16/12、192.168/16）+ loopback（127/8）
    + anyLocal（0.0.0.0）+ isLinkLocalAddress（169.254/16，含云元数据
    169.254.169.254——此前 Python 侧未拦截，SSRF 口径与 Java 不一致）。
    """
    ip_long = ip2long(ip)
    is_inner_ip = (
        ip2long("10.0.0.0") <= ip_long <= ip2long("10.255.255.255")
        or ip2long("172.16.0.0") <= ip_long <= ip2long("172.31.255.255")
        or ip2long("192.168.0.0") <= ip_long <= ip2long("192.168.255.255")
        or ip2long("127.0.0.0") <= ip_long <= ip2long("127.255.255.255")
        or ip2long("169.254.0.0") <= ip_long <= ip2long("169.254.255.255")
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


def _is_inner_ipaddr_strict(ip: str) -> bool:
    """FEAT-073 新校验路径的内网判定（IPv4+IPv6 统一走 ipaddress，fail-safe）。

    比 is_inner_ipaddress（旧 http 路径，Java isInternalIp 对齐口径）更严：
    额外覆盖组播 224/4、保留 240/4、0.0.0.0/8 全段与文档段（is_private）；
    CGNAT 100.64/10 两口径均放行（Java/Python 一致）。FEAT-073 把用户
    任意 URL 变成一等输入，validate_and_keep_https_url/pinned_https_resolution
    走本口径；旧路径（illegal_url/url_to_ip_with_protocol_and_port）维持
    Java 对齐口径不动，避免影响既有插件集成。
    """
    import ipaddress

    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True  # 不可解析按内网处理（fail-safe）
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        # IPv4 映射 IPv6（::ffff:a.b.c.d）按其映射的 IPv4 判定——
        # 169.254/16 等内网段的映射形态与 IPv4 口径一致拦截，
        # 不依赖各 Python 版本 is_private 对映射段分类的差异
        return _is_inner_ipaddr_strict(addr.ipv4_mapped.exploded)
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def validate_and_keep_https_url(url):
    """文件下载 URL 校验（FEAT-073）。

    https：校验通过后返回**原始 URL**（IP 重写会丢失 SNI，导致证书
    主机名校验失败——OBS 预签名等 https 文件地址全部 SSLError）。
    校验走 getaddrinfo 双栈（IPv4+IPv6）——不可经
    url_to_ip_with_protocol_and_port：其 gethostbyname 仅解析 A 记录，
    纯 IPv6 主机名/IPv6 字面量会在进入钉死解析前就误报
    resolving IP address failed，IPv6 文件 URL 无法下载。
    内网判定统一走 _is_inner_ipaddr_strict（ipaddress 全家桶，
    严于旧 http 路径的 Java 对齐口径）。

    http：维持 url_to_ip_with_protocol_and_port 的 IP 重写（防
    DNS rebinding；其 IPv4-only 限制为既有行为，不在本函数范围）。

    https 返回原始 URL 意味着 requests.get 会再次解析 DNS——校验与
    连接之间存在 TOCTOU（DNS rebinding 可校验时解析公网、连接时解析
    内网）。调用方须以 pinned_https_resolution(hostname) 包裹实际请求
    以钉死解析（见 handler_manager.FileHandler.handle）。
    """
    if not re.match(r"^https?://.*$", url):
        raise ValueError("illegal url protocol")
    if urlparse(url).scheme == "https":
        hostname = urlparse(url).hostname
        try:
            infos = socket.getaddrinfo(hostname, None)
        except socket.error as e:
            raise ValueError("resolving IP address failed") from e
        if os.environ.get(CLOSE_URL_JUDGE_SWITCH_KEY) not in ["True", "true"]:
            for info in infos:
                ip = info[4][0]
                if not shot_plugin_white_urls(ip) and _is_inner_ipaddr_strict(ip):
                    raise ValueError("illegal ip address")
        return url, hostname
    valid_url, hostname = url_to_ip_with_protocol_and_port(url)
    return valid_url, hostname


# https 文件下载的 DNS 解析钉死（消除校验/连接 TOCTOU）。
# getaddrinfo 补丁按 hostname 精确匹配，未钉死的主机名走原解析；
# 补丁装卸按全局引用计数，钉死记录按 hostname 引用计数——同一主机名
# 并发下载时先退出的线程不会移除其他线程仍在使用的记录。
_pinned_resolution_lock = threading.Lock()
_pinned_resolution_depth = 0
_pinned_entries = {}  # hostname -> [(family, sockaddr)] 校验时全部解析地址（IPv6 sockaddr 为四元组）
_pinned_refcounts = {}  # hostname -> 并发使用计数
_orig_getaddrinfo = socket.getaddrinfo


def _pinned_getaddrinfo(host, port, *args, **kwargs):
    entries = _pinned_entries.get(host)
    if entries is None:
        return _orig_getaddrinfo(host, port, *args, **kwargs)
    req_family = (args[0] if len(args) > 0 else kwargs.get("family", 0)) or 0
    req_type = (args[1] if len(args) > 1 else kwargs.get("type", 0)) or 0
    req_proto = (args[2] if len(args) > 2 else kwargs.get("proto", 0)) or 0
    # 仅接管 TCP 解析（受保护的下载连接）。UDP（SOCK_DGRAM）等查询不是
    # 本钉死保护的连接，回退原解析
    if req_type not in (0, socket.SOCK_STREAM):
        return _orig_getaddrinfo(host, port, *args, **kwargs)
    # 家族过滤：AF_UNSPEC（0）返回全部钉死地址（保留多地址回退——双栈
    # 主机首个地址不可达时连接层可逐个尝试，与原 getaddrinfo 行为一致）；
    # 显式 AF_INET/AF_INET6 仅返回同族钉死地址。钉死记录无同族地址时
    # 抛 gaierror（fail-closed）——若回退原解析，DNS rebinding 可在钉死
    # 窗口内经家族切换返回未校验地址，破坏 TOCTOU 防护
    if req_family not in (0, socket.AF_UNSPEC):
        entries = [entry for entry in entries if entry[0] == req_family]
    if not entries:
        raise socket.gaierror(
            socket.EAI_NONAME, "pinned resolution has no address of the requested family"
        )
    port_num = port if isinstance(port, int) else 0
    out_type = req_type or socket.SOCK_STREAM
    out_proto = req_proto or socket.IPPROTO_TCP
    results = []
    for family, sockaddr in entries:
        if family == socket.AF_INET6:
            # AF_INET6 sockaddr 约定为四元组 (host, port, flowinfo, scope_id)
            results.append(
                (family, out_type, out_proto, "", (sockaddr[0], port_num, sockaddr[2], sockaddr[3]))
            )
        else:
            results.append((family, out_type, out_proto, "", (sockaddr[0], port_num)))
    return results


@contextlib.contextmanager
def pinned_https_resolution(hostname):
    """连接期间把 hostname 的 DNS 解析钉死为校验时通过的地址。

    进入时重新解析并同口径复校验（拦截校验后才 rebinding 到内网的
    场景；统一走 _is_inner_ipaddr_strict——ipaddress 全家桶，IPv4/IPv6
    同口径且严于旧 http 路径）。**全部**解析
    地址逐一校验并整体钉死（不只首个——双栈主机首个地址不可达时连接层
    保留多地址回退能力）；期间 urllib3 对该主机名的 TCP 解析返回全部
    钉死地址（SNI/证书校验仍按主机名，不受影响），TOCTOU 完全消除；
    退出时按 hostname 引用计数还原（同一主机名并发下载时，先退出的
    线程不会移除其他线程仍在使用的记录）。
    """
    global _pinned_resolution_depth
    infos = socket.getaddrinfo(hostname, None)
    # 按 (family, ip) 去重保序——glibc 对字面量的 port=None 解析会返回
    # STREAM/DGRAM/RAW 多条同 IP 形态（Windows 仅 1 条），不去重会让
    # 连接期解析返回重复条目
    pinned = []
    seen = set()
    for info in infos:
        family, sockaddr = info[0], info[4]
        key = (family, sockaddr[0])
        if key in seen:
            continue
        seen.add(key)
        pinned.append((family, sockaddr))
    if os.environ.get(CLOSE_URL_JUDGE_SWITCH_KEY) not in ["True", "true"]:
        for _, sockaddr in pinned:
            ip = sockaddr[0]
            if not shot_plugin_white_urls(ip) and _is_inner_ipaddr_strict(ip):
                raise ValueError("illegal ip address")
    with _pinned_resolution_lock:
        _pinned_refcounts[hostname] = _pinned_refcounts.get(hostname, 0) + 1
        _pinned_entries[hostname] = pinned
        if _pinned_resolution_depth == 0:
            socket.getaddrinfo = _pinned_getaddrinfo
        _pinned_resolution_depth += 1
    try:
        yield
    finally:
        with _pinned_resolution_lock:
            _pinned_resolution_depth -= 1
            remaining = _pinned_refcounts.get(hostname, 0) - 1
            if remaining > 0:
                _pinned_refcounts[hostname] = remaining
            else:
                _pinned_refcounts.pop(hostname, None)
                _pinned_entries.pop(hostname, None)
            if _pinned_resolution_depth == 0:
                socket.getaddrinfo = _orig_getaddrinfo


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
