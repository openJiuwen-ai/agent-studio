"""COM-03 §4.2: Builder 错误目录适配器。

以 Manifest ``i18n_key`` 为单一治理根键，解析出 descriptor 的三个查找坐标。
Builder 自有框架码定义在模块 1310（COM-03 新分配）。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorDefinition:
    """错误目录定义的不可变元数据。"""

    error_code: str
    http_status: int
    i18n_key: str

    @property
    def message_key(self) -> str:
        return self.i18n_key

    @property
    def reason_key(self) -> str:
        return f"{self.i18n_key}.reason"

    @property
    def suggestion_key(self) -> str:
        return f"{self.i18n_key}.suggestion"


# --- Builder self-owned framework definitions (module 1310, COM-03) ---

REQUEST_VALIDATION_FAILED = ErrorDefinition(
    error_code="openjiuwen.13100001",
    http_status=400,
    i18n_key="openjiuwen.13100001",
)

ROUTE_NOT_FOUND = ErrorDefinition(
    error_code="openjiuwen.13100002",
    http_status=404,
    i18n_key="openjiuwen.13100002",
)

METHOD_NOT_ALLOWED = ErrorDefinition(
    error_code="openjiuwen.13100003",
    http_status=405,
    i18n_key="openjiuwen.13100003",
)

INTERNAL_ERROR = ErrorDefinition(
    error_code="openjiuwen.13100004",
    http_status=500,
    i18n_key="openjiuwen.13100004",
)

DOWNSTREAM_MODEL_FAILED = ErrorDefinition(
    error_code="openjiuwen.13100005",
    http_status=502,
    i18n_key="openjiuwen.13100005",
)

# --- DEF-06: Builder prompt-optimization business codes (canonical) ---
# Builder-owned canonical codes for the eight Prompt/MMAPO business exception
# cases. The JiuWenBaseException carries a legacy integer code (e.g. 102154);
# from_builder_exception maps that legacy integer to one of these canonical
# definitions. Builder registers ONLY these canonical codes (not the legacy
# integers) so there is no collision with Runtime's independent StatusCode copy
# (Runtime keeps 102154 etc. untouched in its own jiuwen package).
PROMPT_OPTIMIZE_INVALID_PARAMS = ErrorDefinition(
    error_code="openjiuwen.13100006",
    http_status=400,
    i18n_key="openjiuwen.13100006",
)

PROMPT_OPTIMIZE_JOB_NOT_FOUND = ErrorDefinition(
    error_code="openjiuwen.13100007",
    http_status=404,
    i18n_key="openjiuwen.13100007",
)

PROMPT_OPTIMIZE_JOB_STATUS_NOT_EXPECTED = ErrorDefinition(
    error_code="openjiuwen.13100008",
    http_status=409,
    i18n_key="openjiuwen.13100008",
)

PROMPT_OPTIMIZE_START_TASK_FAILED = ErrorDefinition(
    error_code="openjiuwen.13100009",
    http_status=500,
    i18n_key="openjiuwen.13100009",
)

PROMPT_OPTIMIZE_RESTART_TASK_FAILED = ErrorDefinition(
    error_code="openjiuwen.13100010",
    http_status=500,
    i18n_key="openjiuwen.13100010",
)

PROMPT_OPTIMIZE_STORAGE_FAILED = ErrorDefinition(
    error_code="openjiuwen.13100011",
    http_status=500,
    i18n_key="openjiuwen.13100011",
)

PROMPT_OPTIMIZE_FEEDBACK_FAILED = ErrorDefinition(
    error_code="openjiuwen.13100012",
    http_status=500,
    i18n_key="openjiuwen.13100012",
)

PROMPT_OPTIMIZE_BADCASE_FAILED = ErrorDefinition(
    error_code="openjiuwen.13100013",
    http_status=500,
    i18n_key="openjiuwen.13100013",
)

# SYNC-01 P5-BLD-01: NL2 意图识别失败（100029 legacy → canonical 13100014）。
# 100029 是 sync_01 nl2._error_sse_generator 的模型意图识别失败码（960dbf23 谱系）,
# 其 DeepSeek-V3 业务建议作为 i18n suggestion 保留（经公共 descriptor 五字段输出,
# 不再裸码 + 两字段 schema）。
NL2_INTENT_RECOGNITION_FAILED = ErrorDefinition(
    error_code="openjiuwen.13100014",
    http_status=500,
    i18n_key="openjiuwen.13100014",
)

_CATALOG: dict[str, ErrorDefinition] = {}


def _register(defn: ErrorDefinition) -> ErrorDefinition:
    if defn.error_code in _CATALOG:
        raise ValueError(f"duplicate error_code: {defn.error_code}")
    _CATALOG[defn.error_code] = defn
    return defn


for _def in (
    REQUEST_VALIDATION_FAILED,
    ROUTE_NOT_FOUND,
    METHOD_NOT_ALLOWED,
    INTERNAL_ERROR,
    DOWNSTREAM_MODEL_FAILED,
    PROMPT_OPTIMIZE_INVALID_PARAMS,
    PROMPT_OPTIMIZE_JOB_NOT_FOUND,
    PROMPT_OPTIMIZE_JOB_STATUS_NOT_EXPECTED,
    PROMPT_OPTIMIZE_START_TASK_FAILED,
    PROMPT_OPTIMIZE_RESTART_TASK_FAILED,
    PROMPT_OPTIMIZE_STORAGE_FAILED,
    PROMPT_OPTIMIZE_FEEDBACK_FAILED,
    PROMPT_OPTIMIZE_BADCASE_FAILED,
    NL2_INTENT_RECOGNITION_FAILED,
):
    _register(_def)

# DEF-06: legacy integer code (as string) → canonical ErrorDefinition mapping.
# The legacy integers live in JiuWenBaseException.error_code and are NOT
# registered in _CATALOG (Runtime keeps its own independent copy of these
# integers); from_builder_exception uses this map to translate the legacy
# integer into the Builder-owned canonical definition for the HTTP response.
_LEGACY_TO_CANONICAL: dict[str, ErrorDefinition] = {
    "102154": PROMPT_OPTIMIZE_INVALID_PARAMS,
    "102155": PROMPT_OPTIMIZE_JOB_NOT_FOUND,
    "102156": PROMPT_OPTIMIZE_JOB_STATUS_NOT_EXPECTED,
    "102158": PROMPT_OPTIMIZE_START_TASK_FAILED,
    "102159": PROMPT_OPTIMIZE_RESTART_TASK_FAILED,
    "102170": PROMPT_OPTIMIZE_STORAGE_FAILED,
    "102213": PROMPT_OPTIMIZE_FEEDBACK_FAILED,
    "102214": PROMPT_OPTIMIZE_BADCASE_FAILED,
    # SYNC-01 P5-BLD-01: 100029（NL2 意图识别失败,模型响应错误）→ 13100014
    "100029": NL2_INTENT_RECOGNITION_FAILED,
}


def lookup_business_definition(legacy_code: str) -> ErrorDefinition | None:
    """DEF-06: map a legacy business exception code to its canonical definition.

    Takes the legacy integer code (as string) carried by JiuWenBaseException and
    returns the Builder-owned canonical ErrorDefinition, or None if the code is
    not in the mapped legacy set (framework codes, unknown values, -1, booleans,
    objects, and dynamic codes all miss). The returned definition's error_code is
    a Builder canonical string, not the legacy integer (controlled remap, not
    verbatim preservation).
    """
    return _LEGACY_TO_CANONICAL.get(legacy_code)


def resolve(error_code: str) -> ErrorDefinition:
    """按 error_code 查找目录定义。未登记的码抛出 KeyError。"""
    try:
        return _CATALOG[error_code]
    except KeyError:
        raise KeyError(f"error_code not in catalog: {error_code}") from None


def all_definitions() -> list[ErrorDefinition]:
    return list(_CATALOG.values())
