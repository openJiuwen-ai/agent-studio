"""COM-03 §5: Runtime HTTP 错误响应构建器。

只负责序列化：接受 ErrorDescriptor + locale，一次产生 HTTP 响应规格。
不重新读取入站 Header，不调用 UUID，不从 exception message 推断状态/文案，
不序列化 cause/downstream_*，不自行记录第二条错误日志。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from agent_runtime.error_contract.descriptor import ErrorDescriptor


@dataclass(frozen=True)
class HttpResponseSpec:
    """HTTP 响应规格——供 FastAPI/Flask 调用方包装为实际 Response。"""

    status: int
    headers: dict[str, str]
    body: dict[str, Any]


class I18nResolver:
    """从 .properties 文件按全串 key 解析三段安全文案。

    Manifest i18n_key 是单一治理根键；message_key = i18n_key，
    reason_key = i18n_key + ".reason"，suggestion_key = i18n_key + ".suggestion"。
    """

    def __init__(self, properties_dir: str, locale_files: dict[str, str]):
        self._locales: dict[str, dict[str, str]] = {}
        for locale, filename in locale_files.items():
            filepath = os.path.join(properties_dir, filename)
            self._locales[locale] = self._parse_properties(filepath)

    @staticmethod
    def _parse_properties(filepath: str) -> dict[str, str]:
        result: dict[str, str] = {}
        if not os.path.exists(filepath):
            return result
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if "=" in stripped:
                    key, _, value = stripped.partition("=")
                    result[key.strip()] = value
        return result

    def resolve(self, locale: str, key: str) -> tuple[str, str, str]:
        """返回 (message, reason, suggestion)。

        COM-03 §4: fail-closed——locale 缺失回退到 zh_cn；但若回退后
        message/reason/suggestion 任一为空，立即 raise ValueError，
        不返回空字段。调用方应捕获并提供硬编码安全 fallback（非空）。
        """
        props = self._locales.get(locale) or self._locales.get("zh_cn", {})
        message = props.get(key, "")
        reason = props.get(f"{key}.reason", "")
        suggestion = props.get(f"{key}.suggestion", "")
        if not message or not message.strip():
            raise ValueError(f"i18n message empty for key={key} locale={locale}")
        if not reason or not reason.strip():
            raise ValueError(f"i18n reason empty for key={key} locale={locale}")
        if not suggestion or not suggestion.strip():
            raise ValueError(f"i18n suggestion empty for key={key} locale={locale}")
        return message, reason, suggestion


def build_http_response(
    descriptor: ErrorDescriptor,
    locale: str,
    resolver: I18nResolver,
) -> HttpResponseSpec:
    """从 ErrorDescriptor + locale 一次产生 HTTP 响应规格。"""
    message, reason, suggestion = resolver.resolve(locale, descriptor.message_key)

    body: dict[str, Any] = {
        "error_code": descriptor.error_code,
        "error_msg": message,
        "error_reason": reason,
        "error_suggestion": suggestion,
        "request_id": descriptor.request_id,
    }

    if descriptor.safe_details is not None:
        body["details"] = [
            {"error_code": d.error_code, "error_msg": d.error_msg}
            for d in descriptor.safe_details
        ]

    headers = {
        "Content-Type": "application/json",
        "X-Request-Id": descriptor.request_id,
    }

    return HttpResponseSpec(
        status=descriptor.http_status,
        headers=headers,
        body=body,
    )
