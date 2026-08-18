"""
Async dict-stream transformer utilities.

This module provides a small utility to transform an async generator of dict frames (structure A)
into an async generator of dict frames (structure B), with:
- configurable JSON templating (variables + JSON templates)
- optional concatenation for selected variables across all frames, emitting an extra final frame
- optional ``is_last`` flag injected into every output frame (default enabled)
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import ExecutionError

MAGIC_CODE = "\t"

WORKFLOW_EXCEPTION_END_ERROR = (
    101924,
    "The workflow anomaly termination component terminates execution",
)


PathToken = Union[str, int]

_TEMPLATE_VAR_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")
_TEMPLATE_MISSING = object()


def _parse_path(path: str) -> List[PathToken]:
    """
    Parse a dot/bracket path like: ``a.b[0].c`` -> ``["a","b",0,"c"]``.

    Notes:
        - This parser is intentionally simple and expects well-formed paths.
        - Keys containing dots/brackets are not supported.
    """
    if not path:
        return []

    tokens: List[PathToken] = []
    i = 0
    buf = ""
    while i < len(path):
        ch = path[i]
        if ch == ".":
            if buf:
                tokens.append(buf)
                buf = ""
            i += 1
            continue
        if ch == "[":
            if buf:
                tokens.append(buf)
                buf = ""
            j = path.find("]", i + 1)
            if j == -1:
                raise ValueError(f"Invalid path (missing ']'): {path}")
            idx_str = path[i + 1 : j].strip()
            if not idx_str.isdigit():
                raise ValueError(f"Invalid list index in path: {path}")
            tokens.append(int(idx_str))
            i = j + 1
            continue
        buf += ch
        i += 1

    if buf:
        tokens.append(buf)
    return tokens


def get_by_path(obj: Any, path: str, default: Any = None) -> Any:
    """Get a nested value from dict/list by a dot/bracket path."""
    tokens = _parse_path(path)
    cur = obj

    def _is_valid(current: Any, token: PathToken) -> bool:
        if (
            isinstance(token, int)
            and isinstance(current, list)
            and 0 <= token < len(current)
        ):
            return True
        if isinstance(token, str) and isinstance(current, dict) and token in current:
            return True
        return False

    for tok in tokens:
        if not _is_valid(cur, tok):
            return default
        cur = cur[tok]
    return cur


def _render_json_template(template: Any, variables: Dict[str, Any]) -> Any:
    """
    Render a JSON template using ``{{var_name}}`` placeholders.

    Rules:
        - If a string value is exactly ``"{{var}}"``, it will be replaced by the variable value as-is.
        - Otherwise, string interpolation will replace all placeholders with ``str(value)`` (None -> "").
        - Dict/list structures are rendered recursively.
    """
    if isinstance(template, dict):
        return {k: _render_json_template(v, variables) for k, v in template.items()}
    if isinstance(template, list):
        return [_render_json_template(v, variables) for v in template]
    if isinstance(template, str):
        m = _TEMPLATE_VAR_RE.fullmatch(template)
        if m:
            name = m.group(1)
            return variables.get(name, _TEMPLATE_MISSING)

        def _repl(match: re.Match) -> str:
            name = match.group(1)
            val = variables.get(name)
            if val is None or val is _TEMPLATE_MISSING:
                return ""
            return str(val)

        return _TEMPLATE_VAR_RE.sub(_repl, template)
    return template


def _prune_none_fields(obj: Any) -> Any:  # noqa: return-statements-mismatch
    """
    Recursively prune dict keys whose values are unresolved placeholders (missing vars)
    or empty dicts after pruning.

    Notes:
        - Explicit null values in templates are preserved.
        - Lists are kept as-is (items are still pruned if they are dicts).
          Unresolved placeholders in lists become None.
    """
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            pv = _prune_none_fields(v)
            if pv is _TEMPLATE_MISSING:
                continue
            if isinstance(pv, dict) and not pv:
                continue
            out[k] = pv
        return out
    if isinstance(obj, list):
        result = []
        for v in obj:
            pv = _prune_none_fields(v)
            result.append(None if pv is _TEMPLATE_MISSING else pv)
        return result
    return obj


@dataclass(frozen=True)
class VariableDef:
    """
    A variable definition used by JSON templates.

    The variable is extracted from the input frame using *src_path*, and can optionally be
    accumulated (``concat=True``) so that the final frame can use the joined value.
    """

    name: str
    src_path: str
    default: Any = None
    concat: bool = False
    concat_sep: str = ""
    skip_none: bool = True
    cast_to_str_for_concat: bool = True

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "VariableDef":
        """
        Supported keys (snake_case only):
            - name
            - src_path
            - default
            - concat
            - concat_sep
            - skip_none
            - cast_to_str_for_concat
        """
        if not isinstance(data, dict):
            raise ValueError("VariableDef must be a dict")
        name = data.get("name")
        src_path = data.get("src_path")
        if not isinstance(name, str) or not name:
            raise ValueError("VariableDef.name must be a non-empty string")
        if not isinstance(src_path, str) or not src_path:
            raise ValueError("VariableDef.src_path must be a non-empty string")

        concat_sep = data.get("concat_sep", "") or ""
        if not isinstance(concat_sep, str):
            concat_sep = str(concat_sep)

        return VariableDef(
            name=name,
            src_path=src_path,
            default=data.get("default", None),
            concat=bool(data.get("concat", False)),
            concat_sep=concat_sep,
            skip_none=bool(data.get("skip_none", True)),
            cast_to_str_for_concat=bool(data.get("cast_to_str_for_concat", True)),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a dict."""
        return {
            "name": self.name,
            "src_path": self.src_path,
            "default": self.default,
            "concat": self.concat,
            "concat_sep": self.concat_sep,
            "skip_none": self.skip_none,
            "cast_to_str_for_concat": self.cast_to_str_for_concat,
        }


@dataclass(frozen=True)
class AsyncDictStreamTransformConfig:
    """
    Configuration for async dict-stream transformation.

    Args:
        input_root_path: Optional root path applied before reading variable src_path.
        variables: Variable definitions used by templates.
        frame_template: JSON template for each frame.
        final_template: Optional JSON template for the extra final frame (defaults to frame_template).
        prune_none_fields: Whether to prune unresolved placeholders (missing vars) from rendered dicts.
        add_is_last: Whether to add the is_last flag into output frames.
        is_last_field: Output field name for the is_last flag.
        emit_final_concat_frame: Whether to emit an extra final frame containing concatenated variables.
    """

    input_root_path: Optional[str] = None

    # Template mode (the only supported mode)
    variables: List[VariableDef] = field(default_factory=list)
    frame_template: Any = None
    final_template: Optional[Any] = None
    prune_none_fields: bool = False

    add_is_last: bool = True
    is_last_field: str = "is_last"

    emit_final_concat_frame: bool = True

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AsyncDictStreamTransformConfig":
        """
        Parse config from a JSON/dict object.

        Supported keys (snake_case only):
            - input_root_path
            - variables (list)
            - frame_template (json template)
            - final_template (json template)
            - prune_none_fields
            - add_is_last
            - is_last_field
            - emit_final_concat_frame
        """
        if not isinstance(data, dict):
            raise ValueError("AsyncDictStreamTransformConfig must be a dict")

        variables_raw = data.get("variables", []) or []
        if not isinstance(variables_raw, list):
            raise ValueError("AsyncDictStreamTransformConfig.variables must be a list")
        variables = [VariableDef.from_dict(x) for x in variables_raw]

        frame_template = data.get("frame_template")
        if frame_template is None:
            raise ValueError(
                "AsyncDictStreamTransformConfig.frame_template is required"
            )
        final_template = data.get("final_template")
        prune_none_fields = bool(data.get("prune_none_fields", False))

        input_root_path = data.get("input_root_path")
        if input_root_path is not None and not isinstance(input_root_path, str):
            input_root_path = str(input_root_path)

        is_last_field = data.get("is_last_field", "is_last")
        if not isinstance(is_last_field, str) or not is_last_field:
            raise ValueError(
                "AsyncDictStreamTransformConfig.is_last_field must be a non-empty string"
            )

        return AsyncDictStreamTransformConfig(
            input_root_path=input_root_path,
            variables=variables,
            frame_template=frame_template,
            final_template=final_template,
            prune_none_fields=prune_none_fields,
            add_is_last=bool(data.get("add_is_last", True)),
            is_last_field=is_last_field,
            emit_final_concat_frame=bool(data.get("emit_final_concat_frame", True)),
        )

    @staticmethod
    def from_json(text: Union[str, bytes]) -> "AsyncDictStreamTransformConfig":
        """Parse config from a JSON string/bytes."""
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="strict")
        if not isinstance(text, str):
            raise ValueError("JSON text must be str or bytes")
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError("Config JSON must decode to an object") from e
        if not isinstance(obj, dict):
            raise ValueError("Config JSON must decode to an object")
        return AsyncDictStreamTransformConfig.from_dict(obj)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize config to a JSON-friendly dict (snake_case keys)."""
        return {
            "input_root_path": self.input_root_path,
            "variables": [v.to_dict() for v in self.variables],
            "frame_template": deepcopy(self.frame_template),
            "final_template": deepcopy(self.final_template),
            "prune_none_fields": self.prune_none_fields,
            "add_is_last": self.add_is_last,
            "is_last_field": self.is_last_field,
            "emit_final_concat_frame": self.emit_final_concat_frame,
        }


class AsyncDictStreamTransformer:
    """Transform an async iterator of dict frames into another async iterator of dict frames."""

    def __init__(self, config: AsyncDictStreamTransformConfig):
        self._cfg = config
        self._concat_vars: List[VariableDef] = [v for v in config.variables if v.concat]
        self._concat_buffers: Dict[str, List[str]] = {
            v.name: [] for v in self._concat_vars
        }
        self._last_var_values: Dict[str, Any] = {}

    async def transform(
        self, stream: AsyncIterator[Dict[str, Any]]
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Transform the input async iterator.

        Implementation detail:
            We use a one-item lookahead buffer to correctly mark the last frame.
        """
        prev_out: Optional[Dict[str, Any]] = None

        async for in_frame in stream:
            out = self._build_frame_from_template(in_frame)
            if prev_out is not None:
                # prev_out is confirmed NOT last at this point
                if self._cfg.add_is_last:
                    prev_out[self._cfg.is_last_field] = False
                yield prev_out
            prev_out = out

        if prev_out is None:
            return

        has_concat = bool(self._concat_buffers)
        if has_concat and self._cfg.emit_final_concat_frame:
            # The last "normal" frame is not last because we will emit an extra final concat frame.
            if self._cfg.add_is_last:
                prev_out[self._cfg.is_last_field] = False
            yield prev_out
            yield self._build_final_extra_frame()
            return

        if self._cfg.add_is_last:
            prev_out[self._cfg.is_last_field] = True
        yield prev_out

    def _read_src(self, frame: Dict[str, Any], src_path: str, default: Any) -> Any:
        base: Any = frame
        if self._cfg.input_root_path:
            base = get_by_path(frame, self._cfg.input_root_path, default={})
        return get_by_path(base, src_path, default=default)

    def _accumulate_concat(
        self, key: str, value: Any, skip_none: bool, cast_to_str: bool
    ) -> None:
        if skip_none and value is None:
            return
        if value is None:
            return
        if cast_to_str and not isinstance(value, str):
            value = str(value)
        self._concat_buffers[key].append(value)

    def _build_frame_from_template(self, in_frame: Dict[str, Any]) -> Dict[str, Any]:
        values: Dict[str, Any] = {}
        for vdef in self._cfg.variables:
            v = self._read_src(in_frame, vdef.src_path, default=vdef.default)
            values[vdef.name] = v
            if v is not None:
                self._last_var_values[vdef.name] = v
            if vdef.concat:
                self._accumulate_concat(
                    vdef.name, v, vdef.skip_none, vdef.cast_to_str_for_concat
                )

        out = _render_json_template(self._cfg.frame_template, values)
        if self._cfg.prune_none_fields:
            out = _prune_none_fields(out)
        if not isinstance(out, dict):
            raise ValueError("frame_template must render to a dict")
        if self._cfg.add_is_last:
            out[self._cfg.is_last_field] = False
        return out

    def _build_final_extra_frame(self) -> Dict[str, Any]:
        final_values = dict(self._last_var_values)
        for vdef in self._concat_vars:
            parts = self._concat_buffers.get(vdef.name, [])
            if parts and not all(isinstance(p, str) for p in parts):
                non_str_types = set(
                    type(p).__name__ for p in parts if not isinstance(p, str)
                )
                raise TypeError(
                    f"can only concatenate str (not '{', '.join(non_str_types)}') to str"
                )
            final_values[vdef.name] = vdef.concat_sep.join(parts)

        tpl = (
            self._cfg.final_template
            if self._cfg.final_template is not None
            else self._cfg.frame_template
        )
        out = _render_json_template(tpl, final_values)
        if self._cfg.prune_none_fields:
            out = _prune_none_fields(out)
        if not isinstance(out, dict):
            raise ValueError("final_template must render to a dict")

        if self._cfg.add_is_last:
            out[self._cfg.is_last_field] = True
        return out


class JiuWenBaseException(ExecutionError):
    """
    JiuWen异常基类，继承 ExecutionError 以融入 openjiuwen 异常体系。

    通过继承 ExecutionError，使得工作流引擎能够正确识别并直接抛出此类异常，
    而不是将其包装为新的 ExecutionError。
    """

    def __init__(
        self,
        error_code: int,
        message: str,
        node_id: str = None,
        node_name: str = None,
        node_type: str = None,
    ) -> None:
        """
        用于表示JiuWen相关的错误，并提供初始化方法设置错误代码、错误信息和其他参数。

        Args:
            error_code (int): 错误代码，表示错误的状态码。
            message (str): 错误信息，提供关于错误的详细描述。
            node_id (str, optional): 节点ID，用于标识发生错误的节点。默认为None。
            node_name (str, optional): 节点名称，用于标识发生错误的节点。默认为None。
            node_type (str, optional): 节点类型，用于标识发生错误的节点类型。默认为None。
        """
        super().__init__(status=StatusCode.ERROR, msg=message)
        self._error_code = error_code
        self.code = error_code
        self.message = message
        self.node_id = node_id
        self.node_name = node_name
        self.node_type = node_type

    def __str__(self):
        """
        返回异常的字符串表示，包含错误代码和错误信息。

        Returns:
            str: 异常的字符串表示。
        """
        return f"[{self._error_code}]{self.message}{MAGIC_CODE}"

    @property
    def error_code(self):
        """
        返回错误代码。

        Returns:
            int: 错误代码。
        """
        return self._error_code

    def __reduce__(self):
        """重写序列化方法，适配自定义构造函数签名。"""
        return (
            self.__class__._reconstruct,
            (
                self._error_code,
                self.message,
                self.node_id,
                self.node_name,
                self.node_type,
            ),
        )

    @classmethod
    def _reconstruct(
        cls, error_code: int, message: str, node_id: str, node_name: str, node_type: str
    ):
        """从序列化数据重建实例。"""
        return cls(
            error_code,
            message,
            node_id=node_id,
            node_name=node_name,
            node_type=node_type,
        )


class WorkflowAbortException(JiuWenBaseException):
    """异常结束组件抛出的异常，用于终止流程"""

    def __init__(
        self,
        data: dict,
        node_id: str = None,
        node_name: str = None,
        node_type: str = None,
    ) -> None:
        super().__init__(
            WORKFLOW_EXCEPTION_END_ERROR[0],
            WORKFLOW_EXCEPTION_END_ERROR[1],
            node_id=node_id,
            node_name=node_name,
            node_type=node_type,
        )
        self.data = data

    def to_payload(self) -> dict:
        """
        Returns:
            dict: 包含异常信息的字典。
        """
        return self.data

    def __reduce__(self):
        """重写序列化方法，适配自定义构造函数签名。"""
        return (
            self.__class__._reconstruct,
            (self.data, self.node_id, self.node_name, self.node_type),
        )

    @classmethod
    def _reconstruct(cls, data: dict, node_id: str, node_name: str, node_type: str):
        """从序列化数据重建实例。"""
        return cls(data, node_id=node_id, node_name=node_name, node_type=node_type)


def get_workflow_param(session, key: str, default: Any = None) -> Any:
    """读取工作流参数，优先从 global_state 取（checkpoint 恢复场景有最新值），fallback 到 envs（首次执行场景有初始值）。

    旧框架中全局变量（_REQUEST、global_variables 等）在 runtime_context 中统一管理，
    新框架中这些变量存放在 session.global_state（利用 commit_user_inputs(inputs)机制，将 params 通过 inputs 传入，
    或由组件通过 update_global_state 写入、由 checkpoint 恢复）。

    - 首次执行：global_state 为空 → fallback 到 envs → 获取初始值
    - 组件修改后：global_state 有更新值 → 直接返回
    - 中断恢复：checkpoint 恢复 global_state → 返回最新值（而非 envs 中的旧值）

    Args:
        session: 工作流会话实例
        key: 参数键名
        default: 默认值

    Returns:
        参数值
    """
    if hasattr(session, "get_global_state"):
        value = session.get_global_state(key)
        if value is not None:
            return value
    return default


@dataclass
class WorkflowMetadata:
    """
    Workflow component metadata.

    Contains basic information about a workflow component node.

    Args:
        node_id: Node ID.
        node_type: Node type.
        node_name: Node name.
        should_interrupt: Whether to interrupt.
    """

    node_id: str
    node_type: str
    node_name: str
    should_interrupt: bool = False
