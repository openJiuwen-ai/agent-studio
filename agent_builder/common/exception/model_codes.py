# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""agent_builder 模型服务 facade 的 ``MD_*`` 错误码本地登记表。

共享包 ``packages.model_service`` 定义了 ``ModelServiceError``（``code`` 为字符串，复用
Java ``StudioError`` 名串），但**不登记** ``openjiuwen.*`` 全码 / i18n 文案 / 响应封包
形状——这些是 agent_builder 的响应契约层关注点。整改前 Java agent-service 经
``GlobalExceptionHandler`` + i18n ``studio-messages_zh_CN.properties`` 统一产出
``ErrorRsp``；facade 迁移后该契约下沉到此文件。

约定：
- ``MD_*`` 字面量集中在模块级常量（``INVOKE_MODEL_SERVICE_FAIL`` 等），raise 点与
  ``_error_response`` 都从本表取，避免字面量散落在 ``model_service_api.py`` 各处。
- ``MODEL_ERROR_SPECS`` 登记每个 code 的 ``openjiuwen`` 全码 + 三段 i18n 文案 +
  HTTP status + 是否透传上游 status + 是否带 ``details``（上游原始 body）。
- i18n 文案与 Java ``studio-messages_zh_CN.properties`` 对齐（当前硬编码，后续如需
  多语言再抽 i18n 层）。
- 未知 code（如共享包抛出的 ``MD_OBS_READ_ERROR`` 等）走 ``DEFAULT_MODEL_ERROR_SPEC``
  兜底：``{error:{code,message}}`` + 400。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# ---- MD_* code 字面量（单一来源；raise 点引用这些常量，禁止裸写字符串）----

INVOKE_MODEL_SERVICE_FAIL = "MD_INVOKE_MODEL_SERVICE_FAIL"
MODEL_SERVICE_NOT_PUBLISH = "MD_MODEL_SERVICE_NOT_PUBLISH"


@dataclass
class ModelErrorSpec:
    """单个 ``MD_*`` 错误码的响应契约。

    - ``full_code`` 非空 → 构造旧 Java ``ErrorRsp`` 形状
      ``{error_code, error_msg, error_reason, error_suggestion, details?}``；
      为空 → 通用兜底 ``{error:{code, message}}``。
    - ``use_upstream_status`` → HTTP status 透传 ``exc.upstream_status``（缺失退回
      ``http_status``）；用于上游模型调用失败时还原上游真实码（如 401）。
    - ``with_details`` → 将 ``exc.upstream_body`` 放进 ``details[0].error_msg``。
    """

    full_code: Optional[str] = None
    error_msg: str = ""
    error_reason: str = ""
    error_suggestion: str = ""
    http_status: int = 400
    use_upstream_status: bool = False
    with_details: bool = False

    def __post_init__(self):
        if not self.error_reason:
            self.error_reason = self.error_msg
        if not self.error_suggestion:
            self.error_suggestion = self.error_msg


# ---- 登记表（code → 响应契约）----

MODEL_ERROR_SPECS: dict[str, ModelErrorSpec] = {
    INVOKE_MODEL_SERVICE_FAIL: ModelErrorSpec(
        full_code="openjiuwen.02501049",
        error_msg="调用第三方模型服务失败,请查看请求响应查询详细原因",
        error_reason="调用第三方模型服务失败,请查看请求响应查询详细原因",
        error_suggestion="请查看请求响应查询详细原因",
        http_status=400,
        use_upstream_status=True,
        with_details=True,
    ),
    MODEL_SERVICE_NOT_PUBLISH: ModelErrorSpec(
        full_code=None,           # 通用兜底 {error:{code,message}}
        http_status=404,
    ),
}

# 未知 MD_* code（共享包抛出的 MD_OBS_READ_ERROR / MD_MODEL_ROUTER_INVALID 等）兜底。
DEFAULT_MODEL_ERROR_SPEC = ModelErrorSpec(full_code=None, http_status=400)


def get_model_error_spec(code: str) -> ModelErrorSpec:
    """按 code 取响应契约；未登记返回通用兜底。"""
    return MODEL_ERROR_SPECS.get(code, DEFAULT_MODEL_ERROR_SPEC)
