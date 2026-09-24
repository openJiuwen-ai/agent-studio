"""COM-03 §4.1: Runtime 服务内不可变错误 descriptor。

内部模型，不是对外 DTO。HTTP/SSE 构建器只提取安全字段序列化；
``cause``、``downstream_service``、``downstream_error_code`` 不参与
序列化、``__eq__``、``__hash__`` 和 ``__repr__``。

构造时 ``__post_init__`` 立即校验不变量：
- 六个必填字段非空非 blank；
- http_status 为 4xx/5xx；
- downstream_service 与 downstream_error_code 成对出现；
- safe_details 非空时逐项校验子错误码和子消息非空。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


_VALID_DOWNSTREAM = ("runtime", "builder", "external")


@dataclass(frozen=True)
class ErrorDetail:
    """COM-03 §4.1 safe_details 元素：只允许 error_code + error_msg。"""

    error_code: str
    error_msg: str

    def __post_init__(self) -> None:
        if not self.error_code or not self.error_code.strip():
            raise ValueError("ErrorDetail.error_code must not be blank")
        if not self.error_msg or not self.error_msg.strip():
            raise ValueError("ErrorDetail.error_msg must not be blank")


@dataclass(frozen=True)
class ErrorDescriptor:
    error_code: str
    http_status: int
    message_key: str
    reason_key: str
    suggestion_key: str
    request_id: str
    safe_details: Optional[list[ErrorDetail]] = None
    downstream_service: Optional[str] = field(default=None, compare=False, repr=False)
    downstream_error_code: Optional[str] = field(default=None, compare=False, repr=False)
    cause: Optional[BaseException] = field(default=None, compare=False, repr=False)

    def __post_init__(self) -> None:
        for name, val in (
            ("error_code", self.error_code),
            ("message_key", self.message_key),
            ("reason_key", self.reason_key),
            ("suggestion_key", self.suggestion_key),
            ("request_id", self.request_id),
        ):
            if not val or not val.strip():
                raise ValueError(f"ErrorDescriptor.{name} must not be blank")

        if not (400 <= self.http_status <= 599):
            raise ValueError(
                f"httpStatus must be 4xx/5xx, got {self.http_status}"
            )

        self._validate_downstream_pairing()
        self._validate_safe_details()

    def _validate_downstream_pairing(self) -> None:
        # 基础契约 §3/§5：单向约束——downstream_error_code 出现时必须同时有
        # downstream_service；传输失败等无原码场景允许只记录 downstream_service。
        has_service = self.downstream_service is not None
        has_code = self.downstream_error_code is not None and self.downstream_error_code.strip()
        if has_code and not has_service:
            raise ValueError(
                "downstream_error_code set but downstream_service is None"
            )
        if has_service and self.downstream_service not in _VALID_DOWNSTREAM:
            raise ValueError(
                f"downstream_service must be one of {_VALID_DOWNSTREAM}, "
                f"got {self.downstream_service!r}"
            )

    def _validate_safe_details(self) -> None:
        if self.safe_details is None:
            return
        for i, detail in enumerate(self.safe_details):
            if detail is None:
                raise ValueError(f"safe_details[{i}] is None")
            if not isinstance(detail, ErrorDetail):
                raise ValueError(
                    f"safe_details[{i}] must be ErrorDetail, got {type(detail).__name__}"
                )
        # COM-03 §3.7：深度不可变——冻结为 tuple，防止外部原列表修改
        object.__setattr__(self, "safe_details", tuple(self.safe_details))

    def to_safe_dict(self) -> dict[str, Any]:
        """提取安全字段供 HTTP/SSE 构建器使用。不包含 cause/downstream_*。"""
        result: dict[str, Any] = {
            "error_code": self.error_code,
            "http_status": self.http_status,
            "message_key": self.message_key,
            "reason_key": self.reason_key,
            "suggestion_key": self.suggestion_key,
            "request_id": self.request_id,
        }
        if self.safe_details is not None:
            result["safe_details"] = [
                {"error_code": d.error_code, "error_msg": d.error_msg}
                for d in self.safe_details
            ]
        return result
