# -*- coding: utf-8 -*-
"""apiUrl 环境变量占位符解析。

跨环境迁移的模型其 ``api_url`` 用 ``${_env.plugin_url_params.VAR}`` 字面占位符替代具体
host/path，运行期由 ``resolver.resolve_strategy`` 在解析 OBS 元数据后用当前请求加载的
env_vars 替换为真实值。占位符语法与管理侧校验（Java ``UrlCheckUtils.validateEnvVarPlaceholders``）
及脱敏正则（``agent_runtime/common/logging_context.py``）严格同源。

- ``has_env_placeholder``：快速判定 api_url 是否含占位符。无占位符时 ``resolve_strategy``
  跳过解析，保持现有 verbatim 行为完全不变（向后兼容）。
- ``resolve_env_placeholders``：逐个替换占位符；缺变量时 fail-fast 抛
  ``MD_ENV_VAR_UNRESOLVED``（对应 Java ``StudioError.MODEL_ENV_VAR_UNRESOLVED`` / 1083），
  与管理侧校验、IR 模板字段 ``get_by_schema`` 缺值行为对齐——让缺失显式失败，避免
  httpx 打到含 ``${...}`` 的非法 URL 后才暴露。

env_vars 结构（``load_environment_variables`` 产出）：
    {"plugin_url_params": {name: value, ...}, "_secretEnvKeys": [...]}
"""

from __future__ import annotations

import re
from typing import Optional

# 与 agent_runtime/common/logging_context.py:47 的 _ENV_REF_PATTERN 同源。
# 占位符语法：${_env.plugin_url_params.<name>}，<name> 为环境变量名。
ENV_PLACEHOLDER_PATTERN = re.compile(r"\$\{_env\.plugin_url_params\.([^}]+)\}")

# env_vars dict 中存放可替换变量的子键（load_environment_variables 的产出约定）。
_PLUGIN_URL_PARAMS_KEY = "plugin_url_params"


def has_env_placeholder(url: str) -> bool:
    """``api_url`` 是否含 ``${_env.plugin_url_params.VAR}`` 占位符。

    用于在 ``resolve_strategy`` 调用链中做快速短路：无占位符时完全跳过 env_vars 解析，
    既保持现有 verbatim 行为不变，也避免对无环境变量的普通模型引入额外开销。
    """
    return ENV_PLACEHOLDER_PATTERN.search(url or "") is not None


def resolve_env_placeholders(
    url: str,
    env_vars: Optional[dict],
    *,
    fail_fast: bool = True,
) -> str:
    """用 ``env_vars`` 替换 ``api_url`` 中的环境变量占位符。

    Args:
        url: 原始 api_url（可能含 ``${_env.plugin_url_params.VAR}``）。
        env_vars: ``load_environment_variables`` 产出的 dict
            (``{"plugin_url_params": {...}, "_secretEnvKeys": [...]}``)。
            为 ``None`` / 空 / 不含 ``plugin_url_params`` 时，无占位符原样返回，
            有占位符按 ``fail_fast`` 处置。
        fail_fast: ``True``（默认）时缺变量抛
            ``ModelServiceError(MD_ENV_VAR_UNRESOLVED)``；``False`` 时保留原占位符字面量返回。

    Returns:
        解析后的 api_url；无占位符时与入参相同（新字符串，原入参不变）。
    """
    if not url or not has_env_placeholder(url):
        return url

    params = (env_vars or {}).get(_PLUGIN_URL_PARAMS_KEY) or {}

    def _replace(match: re.Match) -> str:
        name = match.group(1)
        if name in params:
            value = params[name]
            return str(value) if value is not None else ""
        if fail_fast:
            # 延迟导入避免与 resolver 的循环依赖（resolver 顶部 import 本模块）。
            from .resolver import ModelServiceError
            raise ModelServiceError(
                "MD_ENV_VAR_UNRESOLVED",
                f"environment variable not resolved: {name} (api_url={url})",
            )
        return match.group(0)

    return ENV_PLACEHOLDER_PATTERN.sub(_replace, url)
