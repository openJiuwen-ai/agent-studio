"""COM-03 §4.2: Runtime 错误目录适配器。

以 Manifest ``i18n_key`` 为单一治理根键，解析出 descriptor 的三个查找坐标。
Runtime 自有框架码定义在模块 1210（COM-03 激活）。
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


# --- Runtime self-owned framework definitions (module 1210, COM-03) ---

REQUEST_VALIDATION_FAILED = ErrorDefinition(
    error_code="openjiuwen.12100001",
    http_status=400,
    i18n_key="openjiuwen.12100001",
)

ROUTE_NOT_FOUND = ErrorDefinition(
    error_code="openjiuwen.12100002",
    http_status=404,
    i18n_key="openjiuwen.12100002",
)

METHOD_NOT_ALLOWED = ErrorDefinition(
    error_code="openjiuwen.12100003",
    http_status=405,
    i18n_key="openjiuwen.12100003",
)

INTERNAL_ERROR = ErrorDefinition(
    error_code="openjiuwen.12100004",
    http_status=500,
    i18n_key="openjiuwen.12100004",
)

DOWNSTREAM_BUILDER_FAILED = ErrorDefinition(
    error_code="openjiuwen.12100005",
    http_status=502,
    i18n_key="openjiuwen.12100005",
)

# Plugin response format error (SYNC-01 P5-R3 Phase 3, 决策 A: 105015 canonical 替换)
# sync_01 105015(PLUGIN_RESPONSE_FORMAT_ERROR)未发布 → 替换为受管 canonical。
# raise 端(jiuwen/plugin)保留 105015 作内部诊断；catch 端(agent_runtime)
# 经 from_plugin_exception 映射到本码；响应外露 canonical(105015 不发布)。
PLUGIN_RESPONSE_FORMAT_FAILED = ErrorDefinition(
    error_code="openjiuwen.12100006",
    http_status=422,
    i18n_key="openjiuwen.12100006",
)

# Runtime event encapsulation failure (pre-existing, module 1210)
EVENT_ENCAPSULATION_FAILED = ErrorDefinition(
    error_code="openjiuwen.121007",
    http_status=500,
    i18n_key="121007",
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
    DOWNSTREAM_BUILDER_FAILED,
    PLUGIN_RESPONSE_FORMAT_FAILED,
    EVENT_ENCAPSULATION_FAILED,
):
    _register(_def)


def resolve(error_code: str) -> ErrorDefinition:
    """按 error_code 查找目录定义。未登记的码抛出 KeyError。"""
    try:
        return _CATALOG[error_code]
    except KeyError:
        raise KeyError(f"error_code not in catalog: {error_code}")


def all_definitions() -> list[ErrorDefinition]:
    return list(_CATALOG.values())
