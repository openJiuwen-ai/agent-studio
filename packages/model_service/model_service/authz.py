# -*- coding: utf-8 -*-
"""projectId 可信源与平台鉴权钩子。

``X-Owner-Project-Id`` 由上游信任层（API 网关 / 鉴权服务）在校验 ``X-Auth-Token`` 后按身份注入，
调用方无法自行设置，因此 projectId 可信，跨项目读取 auth 的风险由上游关闭。约束：projectId
永不由调用方原始提供，一律取自该请求头。
"""

from __future__ import annotations

from typing import Optional

PROJECT_ID_HEADER = "X-Owner-Project-Id"


def extract_project_id(headers: Optional[dict], *, fallback: str = "0") -> str:
    """从 ``X-Owner-Project-Id`` 请求头提取 projectId。

    Args:
        headers: 请求头字典。
        fallback: 头缺失时的兜底值，默认 "0"。

    Returns:
        projectId 字符串。
    """
    if not headers:
        return fallback
    return (
        headers.get(PROJECT_ID_HEADER)
        or headers.get("x-owner-project-id")
        or fallback
    )


def assert_project_id_trusted(project_id: str, *, source: str) -> None:
    """声明 projectId 必须来自可信源（上游注入的请求头）。

    运行时信任上游，不做额外校验；保留此函数用于显式标注信任边界。
    """
    return None


async def check_authz(
    caller_identity: str,
    project_id: str,
    model_service_id: str,
    auth_id: str,
) -> None:
    """平台鉴权钩子（预留）。

    信任根为平台鉴权服务（签发 / 校验 ``X-Auth-Token``、绑定 ``authId``），不属于本包职责，
    当前为 no-op，后续接入时在此实现。
    """
    return None
