#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""COM-08 §4.2: 集中内部诊断策略。

本模块是 Runtime 生产代码中**唯一**读取 ``LOG_VERBOSE`` 环境变量的地方。
``LOG_VERBOSE`` 只影响内部、受治理、allowlist、脱敏、限长后的诊断明细；
不得改变 HTTP/SSE 状态、错误码、字段、文案、终态或资源清理；
不得删除调用方传入的 ``exc_info``；不得成为 ``str(exception)`` 的脱敏旁路。

部署开关是进程级配置，不要求运行时热切换。单元测试通过显式注入
``DiagnosticPolicy(verbose=True/False)`` 验证，避免反复修改环境变量和
reload 多个业务模块；部署级环境测试使用隔离子进程。
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Mapping, Optional

__all__ = (
    "DiagnosticPolicy",
    "get_default_policy",
    "set_default_policy",
    "redact_value",
)

# COM-08 §4.2: 唯一环境变量解析入口
_LOG_VERBOSE_ENV = "LOG_VERBOSE"
_DEFAULT_VERBOSE = "false"

# COM-08 §3.2 / §6.4: 非真值集合——仅大小写归一后精确等于 "true" 才视为真。
# 不接受 "1" / "yes" / "on" 等历史上未支持的宽松真值，保持与既有
# ``os.getenv("LOG_VERBOSE", "false").lower() == "true"` 语义一致（零行为翻转）。
_TRUE_LITERAL = "true"

# COM-08 §6.4: 诊断字段值长度上限（字符），超出截断并补 "..."。
_MAX_FIELD_LENGTH = 200
_TRUNCATE_TAIL = "..."

# COM-08 §3.2: 敏感 key 片段——命中即整值脱敏为 _REDACTED（不论 verbose）。
# 收口复审2 §3: 单一 canonical 敏感词源——key 检测（子串）与 value 检测（正则）
# 均由本表生成，防止两套词表漂移（auth/credential/session_id 旁路根因）。
_SENSITIVE_WORDS: tuple[str, ...] = (
    "token", "secret", "password", "passwd", "pwd", "authorization", "auth",
    "cookie", "credential", "api_key", "apikey", "access_key",
    "private_key", "session_id", "bearer",
)
_REDACTED = "***"

# COM-08 §3.2/§6.4: 敏感值内容模式——即使位于合法 allowlist key 的字符串值，
# 命中下列模式也整体替换为 _REDACTED（不依赖 key 名推定 value 安全）。
# 分隔符无关：覆盖 `:`、`=`、JSON 双/单引号、大小写、额外空白、CRLF 转义后形式。
# value 关键字正则由 canonical _SENSITIVE_WORDS 生成（_ 与 - 变体等价），防词表漂移。


def _kw_variant(word: str) -> str:
    """canonical 词 → 正则变体：`_` 与 `-` 等价（session_id 同时匹配 session-id）。"""
    return word.replace("_", r"[_-]?")


_CRED_KEYWORDS = "(?:" + "|".join(_kw_variant(w) for w in _SENSITIVE_WORDS) + ")"
_SENSITIVE_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
    # Authorization/Auth ... Basic 认证（\b 防 authentication/auth-service 误杀）
    re.compile(r"(?:Authorization|Auth)\b\s*['\"\s:=]*\s*Basic\s+\S+", re.IGNORECASE),
    # URL userinfo 凭证：scheme://user:pass@host、redis://:pw@h、scheme://token@h
    # （纯 URL 路径 http://host/path 不含 @ userinfo，不命中）
    re.compile(r"[a-zA-Z][a-zA-Z0-9+.\-]*://[^\s/]*@", re.IGNORECASE),
    # cred 关键字 + 可选引号/空白 + 分隔符(: 或 =) + 可选引号/空白 + 非空值
    # 覆盖 token=abc / token: abc / "password":"pw" / 'secret':'x' / Authorization=Basic ...
    re.compile(_CRED_KEYWORDS + r"['\"\s]*[:=]['\"\s]*\S+", re.IGNORECASE),
)

# COM-08 §3.2 值检测显式契约（未覆盖形式及拒绝原因——复审 §3.2 兼容方案要求）：
# 1. 空白/TAB 分隔无 :/=（"token abc"）：与合法名称（"password reset node"、
#    "token counter"）不可区分，按 :/= 分隔符收敛，不扩大到空白分隔；
# 2. 无关键字的裸密文（base64 等）：无法判定敏感性，不猜测；
# 3. 非 ASCII 关键字（如中文"密码"）：词表为规划 §3.2 点名英文术语，
#    扩展只需改 _SENSITIVE_WORDS 单点；
# 4. 纯 URL 路径（无 userinfo）：非凭证，作为诊断值保留。

# COM-08 §3.1: 严格标识符字段——值必须匹配安全字符集，否则 fail closed。
# 这些字段语义上是标识符（不应含自由文本/凭证），非标识符值整体脱敏。
# node_name 为自由文本字段，不在此集合（依赖 _SENSITIVE_VALUE_PATTERDS 兜底）。
_IDENTIFIER_FIELDS: frozenset[str] = frozenset(
    {"node_id", "execution_id", "model_id", "error_code", "workflow_id",
     "node_type", "operation", "attempt", "http_status", "plugin_name"}
)
_IDENTIFIER_CHARSET = re.compile(r"^[A-Za-z0-9_\-.:/]{0,128}$")

# COM-08 §4.2条3: 每个事件类型显式 allowlist。未登记的事件类型在 verbose 下
# 也不输出任何附加字段（fail-closed，不伪装安全）。
_EVENT_ALLOWLIST: Mapping[str, frozenset[str]] = {
    "workflow.execute": frozenset(
        {"node_id", "node_name", "node_type", "execution_id", "error_code"}
    ),
    "workflow.abort": frozenset({"node_id", "execution_id", "error_code"}),
    "llm.invoke": frozenset({"model_id", "error_code", "attempt"}),
    "plugin.rest": frozenset({"plugin_name", "operation", "error_code", "http_status"}),
    "sub_workflow": frozenset({"workflow_id", "error_code"}),
    "runtime.internal": frozenset({"error_code", "execution_id"}),
}


def _is_sensitive_key(key: str) -> bool:
    if not key:
        return False
    lowered = key.lower()
    return any(frag in lowered for frag in _SENSITIVE_WORDS)


def _truncate(value: str) -> str:
    if len(value) <= _MAX_FIELD_LENGTH:
        return value
    return value[: _MAX_FIELD_LENGTH - len(_TRUNCATE_TAIL)] + _TRUNCATE_TAIL


def _sanitize_string(value: str) -> str:
    """§3.2/§6.4: 字符串值统一脱敏 + 限长。

    - replace_crlf 转义控制字符；
    - 命中敏感值模式（Bearer/Authorization Basic/token=/password=/cookie/api_key/
      secret/access_key 等）整体替换为 _REDACTED，不依赖 key 名推定 value 安全；
    - 截断到 _MAX_FIELD_LENGTH。
    """
    from jiuwen.common.log.base import replace_crlf

    s = replace_crlf(value)
    for pat in _SENSITIVE_VALUE_PATTERNS:
        if pat.search(s):
            return _REDACTED
    return _truncate(s)


def _coerce_safe_str(value: Any) -> str:
    """安全字符串化：禁止 ``repr()``/``str()`` 旁路（§3.2/§4.2）。

    - str → _sanitize_string（敏感模式脱敏 + 截断）
    - bool/int/float → str()
    - None → ""
    - dict/list/tuple/set/任意对象/异常 → 仅返回类型名（不递归、不 repr，
      防嵌套敏感值泄漏与恶意 ``__repr__`` 抛二次异常）
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return _sanitize_string(value)
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return str(value)
    # 容器、异常对象、任意模型对象：只返回类型标识，不 str()/repr()。
    return type(value).__name__


def redact_value(key: str, value: Any) -> Any:
    """按 key 判定是否脱敏，并安全化值。

    敏感 key → 返回 _REDACTED（原值不进日志）。
    标量（str/bool/int/float/None）→ 安全化后返回。
      - str 经 _sanitize_string（敏感模式脱敏 + 截断）；
      - 严格标识符字段（_IDENTIFIER_FIELDS）的值若不符合安全字符集，fail closed → _REDACTED。
    容器/对象/异常 → 返回类型名（不 repr/str，防嵌套泄漏与二次抛错）。
    """
    if _is_sensitive_key(key):
        return _REDACTED
    if isinstance(value, str):
        sanitized = _sanitize_string(value)
        if key in _IDENTIFIER_FIELDS and not _IDENTIFIER_CHARSET.match(sanitized):
            # 标识符字段含非标识符值（如 "Bearer ..."）→ fail closed
            return _REDACTED
        return sanitized
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return type(value).__name__


class DiagnosticPolicy:
    """内部诊断策略。``verbose`` 只控制是否追加 allowlist 诊断字段。

    不论 verbose 取值：
    - 基础日志 message 一致（不随开关选择 message 正文）；
    - ``exc_info`` 始终到达底层 logger（traceback 两种配置都保留）；
    - 不向响应、descriptor safe_details、HTTP/SSE builder 反向流动。
    """

    __slots__ = ("_verbose",)

    def __init__(self, verbose: bool = False) -> None:
        self._verbose = bool(verbose)

    @property
    def verbose(self) -> bool:
        return self._verbose

    @classmethod
    def from_env(cls) -> "DiagnosticPolicy":
        """从 ``LOG_VERBOSE`` 环境变量构造策略（方案 A）。

        仅当环境值大小写归一后精确等于 ``"true"`` 时 verbose=True；
        ``"1"`` / ``"0"`` / ``"false"`` / 空值 / 缺失 / 带额外空白 / 其他非法值
        均 verbose=False。缺省和异常输入安全降级为 False，不抛错。
        """
        try:
            raw = os.getenv(_LOG_VERBOSE_ENV, _DEFAULT_VERBOSE) or _DEFAULT_VERBOSE
        except Exception:
            return cls(verbose=False)
        return cls(verbose=(raw.lower() == _TRUE_LITERAL))

    @staticmethod
    def sanitize_value(value: Any) -> str:
        """对诊断值做脱敏 + 限长 + 安全字符串化。"""
        return _coerce_safe_str(value)

    def build_verbose_fields(
        self,
        event_type: str,
        fields: Optional[Mapping[str, Any]] = None,
    ) -> dict[str, Any]:
        """按事件类型 allowlist 构造 verbose 诊断字段。

        - 非 verbose → 永远返回空 dict（不输出附加字段）；
        - verbose + 事件未登记 → 空 dict（fail-closed）；
        - verbose + 事件登记 → 只保留 allowlist 内的 key，逐值脱敏 + 限长；
        - 敏感 key 即使在 allowlist 内也脱敏为 _REDACTED；
        - 任何意外异常（含恶意 ``__repr__``/``__str__``）→ fail-closed 返回空 dict，
          不让日志路径产生二次失败（§4.2/§6.4）。
        """
        if not self._verbose or not fields:
            return {}
        allowlist = _EVENT_ALLOWLIST.get(event_type)
        if allowlist is None:
            return {}
        result: dict[str, Any] = {}
        try:
            for key, value in fields.items():
                if key not in allowlist:
                    continue
                result[key] = redact_value(key, value)
        except Exception:
            # fail-closed：日志诊断不得因值构造异常而抛出二次错误。
            return {}
        return result

    def log_terminal_exception(
        self,
        logger: logging.Logger,
        event: str,
        exc: BaseException,
        *,
        fields: Optional[Mapping[str, Any]] = None,
        level: int = logging.ERROR,
        base_message: Optional[str] = None,
    ) -> None:
        """最终责任边界异常日志：两种配置都保留 traceback，verbose 只增 allowlist 字段。

        - ``base_message`` 缺省时使用固定 ``f"{event} failed"``，不读取 ``str(exc)``；
        - ``exc_info=True`` 始终传入，traceback 两种配置都到达底层 logger；
        - verbose 时把 allowlist 字段拼入 message 尾部（脱敏 + 限长），不新增第二条 ERROR；
        - 不向调用方返回任何可用于响应的内容。
        """
        msg = base_message if base_message else f"{event} failed"
        verbose_fields = self.build_verbose_fields(event, fields)
        if verbose_fields:
            msg = f"{msg} | {verbose_fields}"
        # exc_info 始终保留——这是 traceback 的唯一载体，不受 verbose 控制。
        logger.log(level, msg, exc_info=exc)


# --- 进程级默认策略（生产路径）-----------------------------------------
# 单例缓存，进程级配置不要求热切换。测试通过 set_default_policy 或显式注入
# DiagnosticPolicy 覆盖，避免模块缓存造成的假阳性（§6.1/§9.5）。
_default_policy: Optional[DiagnosticPolicy] = None


def get_default_policy() -> DiagnosticPolicy:
    """返回进程级默认诊断策略，惰性初始化自环境。"""
    global _default_policy
    if _default_policy is None:
        _default_policy = DiagnosticPolicy.from_env()
    return _default_policy


def set_default_policy(policy: Optional[DiagnosticPolicy]) -> None:
    """测试用：覆盖默认策略。传 None 重置为惰性 from_env。"""
    global _default_policy
    _default_policy = policy
