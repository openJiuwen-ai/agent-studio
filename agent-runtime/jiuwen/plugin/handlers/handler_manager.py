#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
import re
import threading
from abc import ABC, abstractmethod
from typing import Dict, Type

import requests
from jiuwen.common.exception import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.common.utils.utils import (
    pinned_https_resolution,
    safe_json_loads,
    validate_and_keep_https_url,
)

# 错误报文中的 URL 脱敏：查询串可能携带 OBS 预签名 AccessKeyId/Signature 等凭据。
# 两种形态（requests 异常报文实测）：
# 1. 带 scheme 的完整 URL —— HTTPError: "... for url: https://host/path?query"
# 2. 相对路径形态（无 scheme）—— SSLError/ConnectionError:
#    "... Max retries exceeded with url: /bucket/key?query"
_URL_QUERY_PATTERN = re.compile(r"(https?://[^\s?'\"]+)(\?[^\s'\"]*)?")
_BARE_PATH_QUERY_PATTERN = re.compile(r"(/[^\s?'\"]*)(\?[^\s'\"]+)")


def _redact_urls(text: str) -> str:
    """错误报文脱敏：URL/路径仅保留主体，查询串（可能含预签名凭据）替换为 ?***。

    先脱敏完整 URL，再兜底脱敏"裸路径+查询串"形态（requests 的
    SSLError/ConnectionError 报文不含 scheme，仅输出 url: /path?query）。
    对已脱敏文本二次匹配是幂等的（路径主体保留、?*** 原样）。
    """
    redacted = _URL_QUERY_PATTERN.sub(
        lambda m: m.group(1) + ("?***" if m.group(2) else ""), text
    )
    return _BARE_PATH_QUERY_PATTERN.sub(
        lambda m: m.group(1) + "?***", redacted
    )


class AbstractFileHandler(ABC):
    @abstractmethod
    def handle(self, file_path: str, **kwargs):
        """
        文件处理的抽象接口类
        """
        raise NotImplementedError()


class FileHandler(AbstractFileHandler):
    @staticmethod
    def _get_valid_api_cert(api_cert_env):
        """get valid api_cert"""
        if api_cert_env is None:
            return True

        api_cert = safe_json_loads(api_cert_env, None)
        if api_cert is None:
            return True

        if not isinstance(api_cert, str) and not isinstance(api_cert, bool):
            return True

        return api_cert

    @classmethod
    def handle(cls, file_path: str, **kwargs):
        # 远程方式
        # 默认校验证书
        try:
            api_cert_env = kwargs.get("api_cert")
            verify = cls._get_valid_api_cert(api_cert_env=api_cert_env)
            # FEAT-073: https 保留原主机名（IP 重写丢 SNI 导致证书校验失败），
            # SSRF 校验（内网 IP 拦截/白名单）不变；https 用 pinned_https_resolution
            # 钉死 DNS 解析（requests 二次解析与校验之间存在 rebinding TOCTOU）
            valid_url, hostname = validate_and_keep_https_url(file_path)
            is_https = valid_url.startswith("https://")
            if is_https:
                with pinned_https_resolution(hostname):
                    return cls._download(valid_url, verify)
            return cls._download(valid_url, verify)
        except ValueError as val_error:
            raise JiuWenBaseException(
                error_code=StatusCode.REQUEST_GET_METHOD_ERROR.code,
                message=StatusCode.REQUEST_GET_METHOD_ERROR.errmsg.format(
                    reason=_redact_urls(f"url is invalid: {val_error}")
                ),
            ) from val_error
        except Exception as e:
            raise JiuWenBaseException(
                error_code=StatusCode.REQUEST_GET_METHOD_ERROR.code,
                # 先脱敏后截断：截断在前会把查询串凭据截半泄漏
                message=StatusCode.REQUEST_GET_METHOD_ERROR.errmsg.format(
                    reason=f"{type(e).__name__}: {_redact_urls(str(e))[:200]}"
                ),
            ) from e

    @classmethod
    def _download(cls, valid_url: str, verify):
        with requests.get(
            valid_url, stream=True, verify=verify, allow_redirects=False, timeout=60
        ) as response:
            response.raise_for_status()

            content = bytearray()
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    content.extend(chunk)
            return bytes(content)


class HandlerManager:
    _instance_lock = threading.Lock()
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_inited"):
            return
        self.file_handler_map: Dict[str, AbstractFileHandler] = dict()
        self.default_file_handler = FileHandler
        self._inited = True

    def register(
        self, handler_type_value: str, handler_class: Type[AbstractFileHandler]
    ):
        """对外接口，用于注册不同类型文件的处理handler逻辑"""
        if not isinstance(handler_type_value, str):
            logger.error("FileHandler register failed")
            return
        if not isinstance(handler_class, type) or not issubclass(
            handler_class, AbstractFileHandler
        ):
            logger.error("FileHandler register failed")
            return
        self.file_handler_map.update({handler_type_value: handler_class})
        logger.info("FileHandler register success")

    def get_handler(self, handler_type: str) -> AbstractFileHandler:
        """引用接口，用于引用已注册的handler逻辑"""
        return self.file_handler_map.get(handler_type, self.default_file_handler)()
