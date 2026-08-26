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
            # 用户友好：占位符显示为 {ali} 而非后端格式 ${_env.plugin_url_params.ali}
            user_friendly_url = ENV_PLACEHOLDER_PATTERN.sub(
                lambda m: "{" + m.group(1) + "}", url
            )
            raise ModelServiceError(
                "MD_ENV_VAR_UNRESOLVED",
                f"模型服务API地址配置有误：当前配置的环境下未配置环境变量 {name}（api_url={user_friendly_url}）",
            )
        return match.group(0)

    return ENV_PLACEHOLDER_PATTERN.sub(_replace, url)


# 异常 __str__ 的前导错误码前缀，形如 ``[181001]``（agent-core ``ModelError``）或
# ``[MD_ENV_VAR_UNRESOLVED]``（``JiuWenBaseException``）。错误码已由外层 ``data["code"]``
# 单独传递，这里剥离前缀避免其在「错误信息」正文中重复出现，仅保留可读消息。
_LEADING_CODE_PREFIX = re.compile(r"^\[\w+\]\s*")


def friendly_message(exc: BaseException) -> str:
    """将异常转为面向用户的错误信息，统一所有 LLM 节点的异常格式化。

    - ``ModelServiceError``（占位符未解析 / 模型服务不可用 / OBS 读取失败等）的
      ``str`` 为 ``"[code] msg"``，``[code]`` 是内部错误码对用户无意义，取
      ``.msg`` 得到干净消息（如「模型服务API地址配置有误：...未配置环境变量 ali」）。
    - 其他异常的 ``str`` 可能带前导错误码前缀（agent-core ``ModelError`` 的
      ``"[181001] Model invoke failed: ..."`` 或 ``JiuWenBaseException`` 的
      ``"[code]msg\\t"``）。剥离该前缀与尾随 ``MAGIC_CODE``，避免错误码在「错误码」
      字段与「错误信息」正文中重复，仅保留可读信息；剥离后为空则回退原 ``str(exc)``。
    - ``json.JSONDecodeError`` / ``SyntaxError`` 等 stdlib 异常（也有 ``.msg`` 属性，
      且 ``str`` 不以 ``[code]`` 开头）不受影响。

    用 ``isinstance`` 精确匹配 ``ModelServiceError``，延迟导入以避免与 ``resolver``
    的循环依赖。
    """
    try:
        from .resolver import ModelServiceError
        if isinstance(exc, ModelServiceError) and exc.msg:
            return str(exc.msg).strip() or str(exc)
    except ImportError:
        pass
    msg = _LEADING_CODE_PREFIX.sub("", str(exc), count=1).rstrip("\t").strip()
    return msg or str(exc)
