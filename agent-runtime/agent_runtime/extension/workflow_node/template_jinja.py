# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.

"""Jinja2 沙箱渲染。不依赖工作流引擎，方便单测直接覆盖 SSTI 拦截与资源护栏。"""

from __future__ import annotations

import operator
import os
import re
import threading
import time
from collections.abc import Mapping
from string import Formatter
from typing import Any, Callable, Iterable, Iterator

from jinja2 import nodes
from jinja2.exceptions import SecurityError, TemplateError
from jinja2.filters import make_attrgetter
from jinja2.runtime import Context
from jinja2.sandbox import SandboxedEnvironment
from jinja2.utils import pass_eval_context

_FORBIDDEN_TAGS = (nodes.Include, nodes.Import, nodes.FromImport, nodes.Extends)

# 已知会放大分配的 str 方法：必须预检，不能先造串再拒
_AMPLIFYING_STR_METHODS = frozenset(
    {
        "join",
        "replace",
        "format",
        "format_map",
        "ljust",
        "rjust",
        "center",
        "zfill",
        "expandtabs",
    }
)

# printf 风格：%[ (name) ] [flags] [width] [.precision] [hlL] type；%% 单独成字段
# 必须识别 h/l/L，否则 %1000000000ld 等会漏过宽度预检并先分配再拒绝
_PERCENT_FIELD_RE = re.compile(
    r"%"
    r"(?:\(([^)]+)\))?"
    r"([#0\- +]*)"
    r"(\*|\d+)?"
    r"(?:\.(\*|\d+))?"
    r"[hlL]?"
    r"([diouxXeEfFgGcrsa%])"
)

# 内部会自行迭代的过滤器：入参包进 CountingIterable，使预算/deadline 覆盖 |list|sort|join 等
_ITERATING_FILTERS = frozenset(
    {
        "list",
        "sort",
        "join",
        "map",
        "select",
        "reject",
        "selectattr",
        "rejectattr",
        "unique",
        "dictsort",
        "groupby",
        "sum",
        "min",
        "max",
        "batch",
        "slice",
        "reverse",
        "first",
        "last",
        "random",
    }
)


def _positive_int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


# 可被环境变量覆盖，便于现场调参；默认挡住工单里 1e4×1e4 这类拖死进程的模板。
MAX_RANGE_SIZE = _positive_int_env("TEMPLATE_JINJA_MAX_RANGE", 10_000)
MAX_LOOP_ITERATIONS = _positive_int_env("TEMPLATE_JINJA_MAX_LOOP_ITERS", 100_000)
MAX_OUTPUT_CHARS = _positive_int_env("TEMPLATE_JINJA_MAX_OUTPUT_CHARS", 1_000_000)
RENDER_TIMEOUT_SEC = _positive_int_env("TEMPLATE_JINJA_TIMEOUT_SEC", 10)
# 含超时后仍存活的 orphan worker；槽位由 worker finally 释放，避免无限堆积线程
MAX_CONCURRENT_RENDERS = _positive_int_env("TEMPLATE_JINJA_MAX_CONCURRENT", 8)
# 整数幂：限制指数与结果比特数，避免 10**1e9 拖死 CPU/内存
MAX_POW_EXPONENT = _positive_int_env("TEMPLATE_JINJA_MAX_POW_EXP", 10_000)
MAX_POW_RESULT_BITS = _positive_int_env("TEMPLATE_JINJA_MAX_POW_BITS", 1_000_000)

_render_slots = threading.BoundedSemaphore(MAX_CONCURRENT_RENDERS)


class TemplateRenderError(ValueError):
    """模板语法、安全策略、资源护栏或渲染失败。"""


class _RenderBudget:
    """渲染期共享计数：循环迭代次数 + 墙钟截止 + 调用方取消信号。"""

    __slots__ = ("iters", "max_iters", "deadline", "cancel")

    def __init__(
        self,
        max_iters: int,
        deadline: float | None = None,
        cancel: threading.Event | None = None,
    ) -> None:
        self.iters = 0
        self.max_iters = max_iters
        self.deadline = deadline
        self.cancel = cancel

    def check_deadline(self) -> None:
        if self.cancel is not None and self.cancel.is_set():
            raise TemplateRenderError(
                f"template render timed out after {RENDER_TIMEOUT_SEC}s"
            )
        if self.deadline is not None and time.monotonic() >= self.deadline:
            raise TemplateRenderError(
                f"template render timed out after {RENDER_TIMEOUT_SEC}s"
            )

    def consume(self, n: int = 1) -> None:
        self.check_deadline()
        self.iters += n
        if self.iters > self.max_iters:
            raise TemplateRenderError(
                f"template loop iterations exceeded limit {self.max_iters}"
            )


class _CountingIterable:
    """对 for / 过滤器可迭代对象计数；补齐下标与 reversed，兼容 |last / |random。"""

    def __init__(self, iterable: Iterable[Any], budget: _RenderBudget) -> None:
        self._iterable = iterable
        self._budget = budget

    def __iter__(self) -> Iterator[Any]:
        for item in self._iterable:
            self._budget.consume()
            yield item

    def __len__(self) -> int:
        return len(self._iterable)  # type: ignore[arg-type]

    def __getitem__(self, index: Any) -> Any:
        """供 |random（random.choice）等需要下标的路径使用。"""
        self._budget.check_deadline()
        inner = self._iterable
        try:
            return inner[index]  # type: ignore[index]
        except TypeError:
            # 底层不支持下标时先按计数迭代物化再取
            return list(self)[index]

    def __reversed__(self) -> Iterator[Any]:
        """供 |last（reversed(seq)）使用；每取出一项计入预算。"""
        inner = self._iterable
        try:
            iterator: Iterator[Any] = reversed(inner)  # type: ignore[arg-type]
        except TypeError:
            materialized = list(self)
            for item in reversed(materialized):
                yield item
            return
        for item in iterator:
            self._budget.consume()
            yield item


class _CountingMapping(Mapping):
    """Mapping 代理：iter/items/values 计入预算，供 |dictsort 等在排序前受控。"""

    __slots__ = ("_data", "_budget")

    def __init__(self, data: Mapping[Any, Any], budget: _RenderBudget) -> None:
        self._data = data
        self._budget = budget

    def __getitem__(self, key: Any) -> Any:
        self._budget.check_deadline()
        return self._data[key]

    def __iter__(self) -> Iterator[Any]:
        for key in self._data:
            self._budget.consume()
            yield key

    def __len__(self) -> int:
        return len(self._data)

    def items(self) -> Iterator[tuple[Any, Any]]:  # type: ignore[override]
        for item in self._data.items():
            self._budget.consume()
            yield item

    def values(self) -> Iterator[Any]:  # type: ignore[override]
        for value in self._data.values():
            self._budget.consume()
            yield value


def _make_guard_iter(budget: _RenderBudget):
    """包装任意 for 目标；已是计数包装则不重复套。"""

    def guard_iter(obj: Any) -> Any:
        if isinstance(obj, (_CountingIterable, _CountingMapping)):
            return obj
        if isinstance(obj, Mapping):
            if len(obj) > MAX_LOOP_ITERATIONS:
                raise TemplateRenderError(
                    f"template loop iterations exceeded limit {MAX_LOOP_ITERATIONS}"
                )
            return _CountingMapping(obj, budget)
        return _CountingIterable(obj, budget)

    return guard_iter


def _prepare_filter_value(value: Any, budget: _RenderBudget) -> Any:
    """过滤器入参：序列/Mapping 包进计数器；str/bytes 保留原类型（|reverse 等依赖特判）。"""
    if isinstance(value, (_CountingIterable, _CountingMapping)):
        return value
    if isinstance(value, Mapping):
        budget.check_deadline()
        if len(value) > MAX_LOOP_ITERATIONS:
            raise TemplateRenderError(
                f"template loop iterations exceeded limit {MAX_LOOP_ITERATIONS}"
            )
        # dictsort 等会直接 .items() 排序；须包装才能计入预算/响应 cancel
        return _CountingMapping(value, budget)
    if isinstance(value, (str, bytes, bytearray)):
        # 不包装：Jinja reverse/join 等对 str 有专用分支；超长仍按输出/迭代上限拒绝
        budget.check_deadline()
        if len(value) > MAX_OUTPUT_CHARS:
            raise TemplateRenderError(
                f"template output length {len(value)} exceeds limit {MAX_OUTPUT_CHARS}"
            )
        if len(value) > MAX_LOOP_ITERATIONS:
            raise TemplateRenderError(
                f"template loop iterations exceeded limit {MAX_LOOP_ITERATIONS}"
            )
        return value
    if isinstance(value, Iterable):
        return _CountingIterable(value, budget)
    budget.check_deadline()
    return value


def _wrap_filter_with_budget(original: Callable[..., Any], budget: _RenderBudget) -> Callable[..., Any]:
    pass_arg = getattr(original, "jinja_pass_arg", None)

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        budget.check_deadline()
        # pass_eval_context / pass_environment 时首参是 ctx，值在第二位
        if pass_arg is not None:
            if len(args) < 2:
                return original(*args, **kwargs)
            ctx, value, *rest = args
            return original(ctx, _prepare_filter_value(value, budget), *rest, **kwargs)
        if not args:
            return original(*args, **kwargs)
        value, *rest = args
        return original(_prepare_filter_value(value, budget), *rest, **kwargs)

    wrapped.__name__ = getattr(original, "__name__", "guarded_filter")
    wrapped.__doc__ = getattr(original, "__doc__", None)
    if pass_arg is not None:
        wrapped.jinja_pass_arg = pass_arg  # type: ignore[attr-defined]
    return wrapped


def _install_filter_guards(env: SandboxedEnvironment, budget: _RenderBudget) -> None:
    for name in _ITERATING_FILTERS:
        if name == "join":
            # |join 单独安装：须在拼接前累计输出长度，不能只计迭代
            continue
        original = env.filters.get(name)
        if original is None:
            continue
        env.filters[name] = _wrap_filter_with_budget(original, budget)
    _install_join_filter_guard(env, budget)
    _install_alloc_filter_guards(env)


def _install_join_filter_guard(
    env: SandboxedEnvironment, budget: _RenderBudget
) -> None:
    """|join 走 _budgeted_join，避免 do_join 先整串分配再被 finalize 拒绝。"""
    if env.filters.get("join") is None:
        return

    @pass_eval_context
    def guarded_join(
        eval_ctx: Any,
        value: Any,
        d: Any = "",
        attribute: Any = None,
    ) -> str:
        budget.check_deadline()
        iterable: Any = value
        if attribute is not None:
            iterable = map(
                make_attrgetter(eval_ctx.environment, attribute),
                value,
            )
        return _budgeted_join(str(d), iterable, budget)

    guarded_join.__name__ = "join"
    env.filters["join"] = guarded_join


def _install_alloc_filter_guards(env: SandboxedEnvironment) -> None:
    """|format / |center 等会按宽度分配，须在过滤器内预检。"""
    fmt = env.filters.get("format")
    if fmt is not None:
        def guarded_format(value: Any, *args: Any, **kwargs: Any) -> Any:
            if isinstance(value, str):
                _guard_percent_format(value, kwargs if kwargs else args)
            elif isinstance(value, (bytes, bytearray)):
                _guard_percent_format(value, kwargs if kwargs else args)
            return fmt(value, *args, **kwargs)

        guarded_format.__name__ = getattr(fmt, "__name__", "format")
        env.filters["format"] = guarded_format

    center = env.filters.get("center")
    if center is not None:
        def guarded_center(value: Any, width: Any = 80, *args: Any, **kwargs: Any) -> Any:
            if isinstance(width, int) and isinstance(value, (str, bytes, bytearray)):
                _reject_if_over_limit(max(width, len(value)))
            elif isinstance(width, int):
                _reject_if_over_limit(width)
            return center(value, width, *args, **kwargs)

        guarded_center.__name__ = getattr(center, "__name__", "center")
        env.filters["center"] = guarded_center


def _make_guarded_range(budget: _RenderBudget):
    def guarded_range(*args: int):
        try:
            r = range(*args)
            size = len(r)
        except (TypeError, ValueError, OverflowError) as exc:
            # step=0 → ValueError；超大起止 → len() OverflowError；统一成 TemplateRenderError
            raise TemplateRenderError(f"invalid range(): {exc}") from exc
        if size > MAX_RANGE_SIZE:
            raise TemplateRenderError(
                f"range() size {size} exceeds limit {MAX_RANGE_SIZE}"
            )
        return _CountingIterable(r, budget)

    return guarded_range


def _make_guarded_concat():
    """渲染拼接时累计长度，避免只在最终结果上做事后检查。"""

    def guarded_concat(pieces: Iterable[Any]) -> str:
        parts: list[str] = []
        total = 0
        for piece in pieces:
            if piece is None:
                continue
            text = piece if isinstance(piece, str) else str(piece)
            total += len(text)
            if total > MAX_OUTPUT_CHARS:
                raise TemplateRenderError(
                    f"template output length {total} exceeds limit {MAX_OUTPUT_CHARS}"
                )
            parts.append(text)
        return "".join(parts)

    return guarded_concat


def _make_guarded_finalize():
    """每个输出表达式落地前检查长度，尽早拒绝超大中间产物。"""

    def guarded_finalize(value: Any) -> Any:
        if isinstance(value, str) and len(value) > MAX_OUTPUT_CHARS:
            raise TemplateRenderError(
                f"template output length {len(value)} exceeds limit {MAX_OUTPUT_CHARS}"
            )
        if isinstance(value, (list, tuple)) and len(value) > MAX_LOOP_ITERATIONS:
            raise TemplateRenderError(
                f"template sequence length {len(value)} exceeds limit {MAX_LOOP_ITERATIONS}"
            )
        return value

    return guarded_finalize


def _const_str(node: nodes.Node) -> str | None:
    if isinstance(node, nodes.Const) and isinstance(node.value, str):
        return node.value
    return None


def _const_int(node: nodes.Node) -> int | None:
    if isinstance(node, nodes.Const) and isinstance(node.value, int):
        return node.value
    return None


def _const_seq(node: nodes.Node) -> list[Any] | tuple[Any, ...] | None:
    if isinstance(node, nodes.Const) and isinstance(node.value, (list, tuple)):
        return node.value
    return None


def _raise_output_too_long(size: int) -> None:
    raise TemplateRenderError(
        f"template output length {size} exceeds limit {MAX_OUTPUT_CHARS}"
    )


def _raise_seq_too_long(size: int) -> None:
    raise TemplateRenderError(
        f"template sequence length {size} exceeds limit {MAX_LOOP_ITERATIONS}"
    )


def _product_against_limit(base_len: int, times: int, limit: int) -> int:
    """base_len * times，超 limit 则由 caller 抛错；返回乘积。"""
    if times <= 0 or base_len <= 0:
        return 0
    if base_len > limit:
        return limit + 1
    if times > limit // base_len:
        return limit + 1
    return base_len * times


def _product_len_or_raise(base_len: int, times: int) -> int:
    """计算 base_len * times；超限则抛错，避免先分配再检查。"""
    size = _product_against_limit(base_len, times, MAX_OUTPUT_CHARS)
    if size > MAX_OUTPUT_CHARS:
        _raise_output_too_long(size)
    return size


def _product_seq_or_raise(base_len: int, times: int) -> int:
    size = _product_against_limit(base_len, times, MAX_LOOP_ITERATIONS)
    if size > MAX_LOOP_ITERATIONS:
        _raise_seq_too_long(size)
    return size


def _guard_int_pow(base: int, exp: int) -> None:
    """整数幂运算前检查指数与结果比特上限。"""
    if exp < 0:
        return
    if exp > MAX_POW_EXPONENT:
        raise TemplateRenderError(
            f"integer exponent {exp} exceeds limit {MAX_POW_EXPONENT}"
        )
    if base in (0, 1, -1) or exp == 0:
        return
    bits = abs(base).bit_length() * exp
    if bits > MAX_POW_RESULT_BITS:
        raise TemplateRenderError(
            f"integer power result bits {bits} exceeds limit {MAX_POW_RESULT_BITS}"
        )


def _reject_if_over_limit(size: int) -> None:
    if size > MAX_OUTPUT_CHARS:
        _raise_output_too_long(size)


def _guard_percent_format(fmt: Any, args: Any) -> None:
    """str/bytes % args 分配前：按宽度字段与代入值估算产物下限。"""
    if not isinstance(fmt, (str, bytes, bytearray)):
        return
    fmt_text = fmt.decode("utf-8", "replace") if isinstance(fmt, (bytes, bytearray)) else fmt
    if len(fmt_text) > MAX_OUTPUT_CHARS:
        _raise_output_too_long(len(fmt_text))

    mapping: Mapping[str, Any] | None
    seq: list[Any] | None
    if isinstance(args, Mapping):
        mapping, seq = args, None
    elif isinstance(args, tuple):
        mapping, seq = None, list(args)
    else:
        mapping, seq = None, [args]

    field_sizes: list[int] = []
    idx = 0
    for match in _PERCENT_FIELD_RE.finditer(fmt_text):
        name, _flags, width, prec, conv = match.groups()
        if conv == "%":
            continue
        size = 0
        if width == "*":
            if seq is None or idx >= len(seq) or not isinstance(seq[idx], int):
                # 让原生 % 报错；无法预估则跳过该字段宽度
                idx += 1
                continue
            size = max(size, seq[idx])
            idx += 1
        elif width is not None and width.isdigit():
            size = max(size, int(width))
        if prec == "*":
            if seq is not None and idx < len(seq):
                idx += 1
        if mapping is not None:
            if name is not None and name in mapping:
                val = mapping[name]
                if isinstance(val, (str, bytes, bytearray)):
                    size = max(size, len(val))
        elif seq is not None:
            if idx < len(seq):
                val = seq[idx]
                idx += 1
                if isinstance(val, (str, bytes, bytearray)):
                    size = max(size, len(val))
        _reject_if_over_limit(size)
        field_sizes.append(size)

    if field_sizes:
        _reject_if_over_limit(max(field_sizes))
        _reject_if_over_limit(sum(field_sizes))


def _literal_format_spec_width(spec: str) -> int | None:
    """解析 format_spec 中的字面量 width；含嵌套字段则返回 None。"""
    if not spec or "{" in spec:
        return None
    i = 0
    if len(spec) >= 2 and spec[1] in "<>=^":
        i = 2
    elif spec and spec[0] in "<>=^":
        i = 1
    if i < len(spec) and spec[i] in "+- ":
        i += 1
    if i < len(spec) and spec[i] == "z":
        i += 1
    if i < len(spec) and spec[i] == "#":
        i += 1
    if i < len(spec) and spec[i] == "0":
        i += 1
    j = i
    while j < len(spec) and spec[j].isdigit():
        j += 1
    if j > i:
        return int(spec[i:j])
    return None


def _format_field_arg(
    field_name: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    auto_idx: list[int],
) -> Any:
    """解析 format 字段名对应的实参；auto_idx 为单元素列表以模拟可变计数。"""
    if field_name == "":
        i = auto_idx[0]
        auto_idx[0] = i + 1
        return args[i] if i < len(args) else None
    if field_name.isdigit():
        i = int(field_name)
        return args[i] if i < len(args) else None
    key = field_name.split(".", 1)[0].split("[", 1)[0]
    if key.isdigit():
        i = int(key)
        return args[i] if i < len(args) else None
    return kwargs.get(key)


def _value_len_hint(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (str, bytes, bytearray)):
        return len(value)
    if isinstance(value, bool):
        return 4 if value else 5
    if isinstance(value, int):
        return len(str(value))
    if isinstance(value, float):
        return len(str(value))
    return len(str(value))


def _guard_str_format(fmt: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
    """str.format / format_map 分配前：宽度 + 各字段代入值长度总和。"""
    if len(fmt) > MAX_OUTPUT_CHARS:
        _raise_output_too_long(len(fmt))
    total = 0
    auto_idx = [0]
    try:
        fields = list(Formatter().parse(fmt))
    except ValueError as exc:
        raise TemplateRenderError(f"invalid format string: {exc}") from exc
    for literal, field_name, format_spec, _conv in fields:
        total += len(literal or "")
        _reject_if_over_limit(total)
        if field_name is None:
            continue
        width = _literal_format_spec_width(format_spec) if format_spec else None
        if format_spec and "{" in format_spec:
            # 嵌套宽度：保守拒绝超限 int 实参
            for arg in args:
                if isinstance(arg, int):
                    _reject_if_over_limit(arg)
            for val in kwargs.values():
                if isinstance(val, int):
                    _reject_if_over_limit(val)
        val = _format_field_arg(field_name, args, kwargs, auto_idx)
        piece = max(width or 0, _value_len_hint(val))
        total += piece
        _reject_if_over_limit(total)


def _guard_str_replace(
    owner: str, args: tuple[Any, ...], kwargs: dict[str, Any]
) -> None:
    """replace 分配前按出现次数估算产物长度。"""
    old = args[0] if args else kwargs.get("old")
    new = args[1] if len(args) > 1 else kwargs.get("new")
    count = args[2] if len(args) > 2 else kwargs.get("count", -1)
    if not isinstance(old, str) or not isinstance(new, str):
        return
    if old == "":
        # 空串替换会在每个间隙插入 new
        est = len(owner) + (len(owner) + 1) * len(new)
        _reject_if_over_limit(est)
        return
    n = owner.count(old)
    if isinstance(count, int) and count >= 0:
        n = min(n, count)
    est = len(owner) + n * (len(new) - len(old))
    _reject_if_over_limit(est)


def _budgeted_join(sep: str, iterable: Any, budget: _RenderBudget) -> str:
    """str.join：逐项计入迭代预算并响应 cancel，同时累计输出长度。"""
    parts: list[str] = []
    total = 0
    for item in iterable:
        budget.consume()
        text = item if isinstance(item, str) else str(item)
        add = len(text) if not parts else len(sep) + len(text)
        total += add
        _reject_if_over_limit(total)
        parts.append(text)
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return sep.join(parts)


def _guard_str_alloc_method(
    owner: str, name: str, args: tuple[Any, ...], kwargs: dict[str, Any]
) -> None:
    """ljust/rjust/center/zfill/expandtabs/format/replace 调用前按产物长度拒绝。"""
    if name in ("ljust", "rjust", "center", "zfill"):
        width = args[0] if args else kwargs.get("width")
        if isinstance(width, int):
            _reject_if_over_limit(max(width, len(owner)))
        return
    if name == "expandtabs":
        tabsize = args[0] if args else kwargs.get("tabsize", 8)
        if isinstance(tabsize, int) and tabsize > 0:
            ntabs = owner.count("\t")
            est = len(owner) - ntabs + ntabs * tabsize
            _reject_if_over_limit(est)
        return
    if name == "replace":
        _guard_str_replace(owner, args, kwargs)
        return
    if name == "format":
        _guard_str_format(owner, args, kwargs)
        return
    if name == "format_map":
        mapping = args[0] if args else kwargs.get("mapping", {})
        if isinstance(mapping, Mapping):
            _guard_str_format(owner, (), dict(mapping))


def _dispatch_str_method(
    owner: str,
    method: Any,
    name: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    budget: _RenderBudget,
) -> Any:
    """统一分发 str 方法：join 走预算迭代；放大类预检；其余调用后校验长度。"""
    budget.check_deadline()
    if name == "join":
        iterable = args[0] if args else ()
        return _budgeted_join(owner, iterable, budget)
    if name in _AMPLIFYING_STR_METHODS:
        _guard_str_alloc_method(owner, name, args, kwargs)
    result = method(*args, **kwargs)
    if isinstance(result, str):
        _reject_if_over_limit(len(result))
    elif isinstance(result, (list, tuple)) and len(result) > MAX_LOOP_ITERATIONS:
        raise TemplateRenderError(
            f"template sequence length {len(result)} exceeds limit {MAX_LOOP_ITERATIONS}"
        )
    return result


def _wrap_str_method(
    owner: str, method: Any, name: str, budget: _RenderBudget
) -> Callable[..., Any]:
    def guarded(*args: Any, **kwargs: Any) -> Any:
        return _dispatch_str_method(owner, method, name, args, kwargs, budget)

    guarded.__name__ = name
    guarded.__doc__ = getattr(method, "__doc__", None)
    return guarded


def _guard_mod_operands(left: Any, right: Any) -> Any:
    """%：str/bytes 走格式化护栏；其余走取模。返回运算结果。"""
    if isinstance(left, (str, bytes, bytearray)):
        _guard_percent_format(left, right)
        try:
            return left % right
        except (TypeError, ValueError, KeyError) as exc:
            raise TemplateRenderError(f"template % format failed: {exc}") from exc
    return operator.mod(left, right)


def _guard_mul_operands(left: Any, right: Any) -> None:
    """* 运算分配前：str/bytes 按输出长度；list/tuple 按元素数。"""
    if isinstance(left, str) and isinstance(right, int):
        _product_len_or_raise(len(left), right)
        return
    if isinstance(right, str) and isinstance(left, int):
        _product_len_or_raise(len(right), left)
        return
    if isinstance(left, (bytes, bytearray)) and isinstance(right, int):
        _product_len_or_raise(len(left), right)
        return
    if isinstance(right, (bytes, bytearray)) and isinstance(left, int):
        _product_len_or_raise(len(right), left)
        return
    if isinstance(left, (list, tuple)) and isinstance(right, int):
        _product_seq_or_raise(len(left), right)
        return
    if isinstance(right, (list, tuple)) and isinstance(left, int):
        _product_seq_or_raise(len(right), left)


def _guard_pow_operands(left: Any, right: Any) -> None:
    if isinstance(left, int) and isinstance(right, int):
        _guard_int_pow(left, right)


class _GuardedSandboxedEnvironment(SandboxedEnvironment):
    """拦截 * / ** / %，并对 str 方法统一做分配前护栏（含 join 预算）。"""

    intercepted_binops = frozenset(["*", "**", "%"])

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._render_budget: _RenderBudget | None = None

    def bind_render_budget(self, budget: _RenderBudget) -> None:
        """由渲染入口注入预算；避免模块外直接写受保护字段（G.CLS.11）。"""
        self._render_budget = budget

    @staticmethod
    def _skip_str_method_wrap(attribute: str, value: Any) -> bool:
        if not callable(value):
            return True
        if attribute.startswith("_"):
            return True
        return attribute in ("format", "format_map")

    @staticmethod
    def _is_public_str_bound(owner: Any, name: Any) -> bool:
        if not isinstance(owner, str) or not isinstance(name, str):
            return False
        return not name.startswith("_")

    @staticmethod
    def _is_amplifying_bytes_bound(owner: Any, name: Any) -> bool:
        if not isinstance(owner, (bytes, bytearray)) or not isinstance(name, str):
            return False
        return name in _AMPLIFYING_STR_METHODS

    def call_binop(
        self, context: Context, op: str, left: Any, right: Any
    ) -> Any:
        # 参数名用 op，避免遮蔽模块级 import operator（G.VAR.03）
        if op == "%":
            return _guard_mod_operands(left, right)
        if op == "*":
            _guard_mul_operands(left, right)
        elif op == "**":
            _guard_pow_operands(left, right)
        return super().call_binop(context, op, left, right)

    def wrap_str_format(self, value: Any) -> Callable[..., str] | None:
        """Jinja 在 getattr 时替换 format；预检宽度与字段值长度后再调用。"""
        wrapped = super().wrap_str_format(value)
        if wrapped is None:
            return None
        owner = getattr(value, "__self__", None)
        name = getattr(value, "__name__", None)
        if not isinstance(owner, str) or name not in ("format", "format_map"):
            return wrapped

        def guarded(*args: Any, **kwargs: Any) -> str:
            if name == "format_map":
                mapping = args[0] if args else {}
                if isinstance(mapping, Mapping):
                    _guard_str_format(owner, (), dict(mapping))
            else:
                _guard_str_format(owner, args, kwargs)
            try:
                result = wrapped(*args, **kwargs)
            except (ValueError, TypeError, KeyError, IndexError) as exc:
                raise TemplateRenderError(f"template format failed: {exc}") from exc
            _reject_if_over_limit(len(result))
            return result

        guarded.__name__ = getattr(wrapped, "__name__", name)
        guarded.__doc__ = getattr(wrapped, "__doc__", None)
        return guarded

    def getattr(self, obj: Any, attribute: str) -> Any:
        value = super().getattr(obj, attribute)
        budget = self._render_budget
        if budget is None or not isinstance(obj, str):
            return value
        if self._skip_str_method_wrap(attribute, value):
            # format/format_map 已由 wrap_str_format 接管
            return value
        # 统一包装公开 str 方法，避免只维护白名单漏网
        return _wrap_str_method(obj, value, attribute, budget)

    def call(
        self,
        context: Context,
        obj: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        budget = self._render_budget
        owner = getattr(obj, "__self__", None)
        name = getattr(obj, "__name__", None)
        if budget is not None and self._is_public_str_bound(owner, name):
            return _dispatch_str_method(owner, obj, name, args, kwargs, budget)
        if budget is not None and self._is_amplifying_bytes_bound(owner, name):
            text = owner.decode("utf-8", "replace")
            if name == "join":
                iterable = args[0] if args else ()
                return _budgeted_join(text, iterable, budget)
            _guard_str_alloc_method(text, name, args, kwargs)
        return super().call(context, obj, *args, **kwargs)


def _fold_static_str_len(node: nodes.Node) -> int | None:
    """静态折叠字符串表达式长度；支持链式 Mul(Mul(...), ...)。无法折叠则 None。"""
    text = _const_str(node)
    if text is not None:
        return len(text)
    if not isinstance(node, nodes.Mul):
        return None
    left_len = _fold_static_str_len(node.left)
    right_times = _const_int(node.right)
    if left_len is not None and right_times is not None:
        return _product_len_or_raise(left_len, right_times)
    right_len = _fold_static_str_len(node.right)
    left_times = _const_int(node.left)
    if right_len is not None and left_times is not None:
        return _product_len_or_raise(right_len, left_times)
    return None


def _static_seq_len(node: nodes.Node) -> int | None:
    seq = _const_seq(node)
    if seq is not None:
        return len(seq)
    # Jinja 字面量 [0] / (0,1) 是 List/Tuple 节点，不是 Const
    if isinstance(node, (nodes.List, nodes.Tuple)):
        return len(node.items)
    return None


def _reject_static_huge_seq_mul(node: nodes.Mul) -> None:
    """字面量 list/tuple * int 静态拒绝。"""
    left_len = _static_seq_len(node.left)
    times = _const_int(node.right)
    if left_len is None:
        left_len = _static_seq_len(node.right)
        times = _const_int(node.left)
    if left_len is None or times is None:
        return
    _product_seq_or_raise(left_len, times)


def _reject_static_huge_percent(node: nodes.Mod) -> None:
    """字面量 '%Ns' % ... 解析期拒绝，避免编译后才分配。"""
    fmt = _const_str(node.left)
    if fmt is None:
        return
    right = node.right
    if isinstance(right, nodes.Const):
        _guard_percent_format(fmt, right.value)
        return
    if isinstance(right, nodes.Tuple):
        values: list[Any] = []
        for item in right.items:
            if not isinstance(item, nodes.Const):
                # 宽度字面量仍可扫 format 串本身
                _guard_percent_format(fmt, ())
                return
            values.append(item.value)
        _guard_percent_format(fmt, tuple(values))
        return
    # 右侧非常量：至少按 format 串内字面量宽度拒绝
    _guard_percent_format(fmt, ())


def _reject_static_huge_ops(parsed: nodes.Template) -> None:
    """解析期拒绝可静态折叠的超大 str/seq 重复、%-宽度与整数幂。"""
    for node in parsed.find_all(nodes.Mul):
        _fold_static_str_len(node)
        _reject_static_huge_seq_mul(node)
    for node in parsed.find_all(nodes.Mod):
        _reject_static_huge_percent(node)
    for node in parsed.find_all(nodes.Pow):
        base = _const_int(node.left)
        exp = _const_int(node.right)
        if base is not None and exp is not None:
            _guard_int_pow(base, exp)


def _wrap_for_iters_with_guard(parsed: nodes.Template) -> None:
    """把每个 for 的可迭代表达式包进 guard_iter(...)，list/dict 等也会计入预算。"""
    for for_node in list(parsed.find_all(nodes.For)):
        for_node.iter = nodes.Call(
            nodes.Name("guard_iter", "load"),
            [for_node.iter],
            [],
            None,
            None,
        )


def _has_forbidden_attr_access(parsed: nodes.Template) -> bool:
    """拒绝 AST 中对 _ / __ 开头属性的访问，避免误杀正文里的双下划线文本。"""
    for node in parsed.find_all(nodes.Getattr):
        attr = getattr(node, "attr", None)
        if isinstance(attr, str) and attr.startswith("_"):
            return True
    return False


def _const_range_len(call: nodes.Call) -> int | None:
    """若 call 是 range(常量...)，返回长度；否则 None。"""
    node = call.node
    if not isinstance(node, nodes.Name) or node.name != "range":
        return None
    args: list[int] = []
    for arg in call.args:
        if not isinstance(arg, nodes.Const) or not isinstance(arg.value, int):
            return None
        args.append(arg.value)
    if call.kwargs or call.dyn_args or call.dyn_kwargs:
        return None
    try:
        return len(range(*args))
    except (TypeError, ValueError, OverflowError):
        return None


def _reject_static_nested_range_blowup(parsed: nodes.Template) -> None:
    """嵌套 for + 常量 range 时，若乘积超过迭代上限则在解析阶段拒绝。"""

    def walk(node: nodes.Node, product: int) -> None:
        if isinstance(node, nodes.For):
            iter_node = node.iter
            size = 1
            if isinstance(iter_node, nodes.Call):
                const_len = _const_range_len(iter_node)
                if const_len is not None:
                    size = const_len
                    if size > MAX_RANGE_SIZE:
                        raise TemplateRenderError(
                            f"range() size {size} exceeds limit {MAX_RANGE_SIZE}"
                        )
            # 必须用乘法：range(0) 的 size=0 是合法的「零次迭代」，不能当 falsy 丢掉
            next_product = product * size
            if next_product > MAX_LOOP_ITERATIONS:
                raise TemplateRenderError(
                    f"nested range loops would exceed iteration limit {MAX_LOOP_ITERATIONS}"
                )
            for child in node.iter_child_nodes():
                walk(child, next_product)
            return
        for child in node.iter_child_nodes():
            walk(child, product)

    walk(parsed, 1)


def _render_with_guards(
    template: str,
    variables: dict[str, Any],
    deadline: float | None = None,
    cancel: threading.Event | None = None,
) -> str:
    env = _GuardedSandboxedEnvironment(autoescape=False)
    try:
        parsed = env.parse(template)
    except TemplateError as exc:
        raise TemplateRenderError(str(exc)) from exc

    forbidden = next(parsed.find_all(_FORBIDDEN_TAGS), None)
    if forbidden is not None:
        raise TemplateRenderError(f"forbidden jinja tag: {type(forbidden).__name__}")

    if _has_forbidden_attr_access(parsed):
        raise TemplateRenderError("forbidden dunder access")

    # 静态检查必须在 AST 改写之前（改写后 for 目标变成 guard_iter(...)）
    _reject_static_nested_range_blowup(parsed)
    _reject_static_huge_ops(parsed)
    _wrap_for_iters_with_guard(parsed)

    budget = _RenderBudget(MAX_LOOP_ITERATIONS, deadline=deadline, cancel=cancel)
    env.bind_render_budget(budget)
    env.globals["range"] = _make_guarded_range(budget)
    env.globals["guard_iter"] = _make_guard_iter(budget)
    _install_filter_guards(env, budget)
    env.concat = _make_guarded_concat()
    env.finalize = _make_guarded_finalize()

    try:
        code = env.compile(parsed)
        tmpl = env.template_class.from_code(env, code, env.make_globals(None), None)
        rendered = tmpl.render(**variables)
    except (SecurityError, TemplateError) as exc:
        # TemplateRenderError（护栏主动抛出）不在此捕获，原样向上传播
        raise TemplateRenderError(str(exc)) from exc

    if not isinstance(rendered, str):
        raise TemplateRenderError("template render result must be a string")
    # concat 已在渲染中拦截；此处兜底单表达式直接产出超长字符串的路径
    if len(rendered) > MAX_OUTPUT_CHARS:
        raise TemplateRenderError(
            f"template output length {len(rendered)} exceeds limit {MAX_OUTPUT_CHARS}"
        )
    return rendered


def render_jinja(template: str, variables: dict[str, Any]) -> str:
    """用 SandboxedEnvironment 渲染。

    - 拒绝 include/import/extends，并按 AST 拦住私有属性访问（SSTI）
    - 限制 range 大小、for / 迭代类过滤器次数、输出长度与渲染超时
    - 超时用 daemon 线程 + join(timeout)：调用方按时返回；超时后 set cancel，
      for/过滤器路径在 consume 时协作退出；worker 持有并发槽直至结束
    """
    if not isinstance(template, str) or not template.strip():
        raise TemplateRenderError("template must be a non-empty string")
    if not isinstance(variables, dict):
        raise TemplateRenderError("template variables must be a dict")

    slots = _render_slots
    # 等槽 + 渲染共用同一 RENDER_TIMEOUT_SEC 总预算，避免硬编码 1s 误杀排队请求
    overall_deadline = time.monotonic() + float(RENDER_TIMEOUT_SEC)
    slot_wait = max(0.0, overall_deadline - time.monotonic())
    if not slots.acquire(blocking=True, timeout=slot_wait):
        raise TemplateRenderError(
            f"template render concurrency limit exceeded ({MAX_CONCURRENT_RENDERS})"
        )

    remain = max(0.0, overall_deadline - time.monotonic())
    if remain <= 0:
        slots.release()
        raise TemplateRenderError(
            f"template render timed out after {RENDER_TIMEOUT_SEC}s"
        )

    deadline = overall_deadline
    cancel = threading.Event()
    box: dict[str, Any] = {}

    def _worker() -> None:
        try:
            box["result"] = _render_with_guards(
                template, variables, deadline, cancel
            )
        except Exception as exc:  # noqa: BLE001 — 传回调用线程统一处理
            box["error"] = exc
        finally:
            slots.release()

    thread = threading.Thread(
        target=_worker,
        name="template-jinja-render",
        daemon=True,
    )
    try:
        thread.start()
    except RuntimeError as exc:
        slots.release()
        raise TemplateRenderError(
            f"template render failed to start worker: {exc}"
        ) from exc

    thread.join(timeout=remain)
    if thread.is_alive():
        # 通知 worker 在下一次 consume/check_deadline 时退出；不 join 到底
        cancel.set()
        raise TemplateRenderError(
            f"template render timed out after {RENDER_TIMEOUT_SEC}s"
        )
    if "error" in box:
        raise box["error"]
    return box["result"]
