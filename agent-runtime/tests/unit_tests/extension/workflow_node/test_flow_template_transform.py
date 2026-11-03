import time

import pytest

from agent_runtime.extension.workflow_node.template_jinja import (
    TemplateRenderError,
    render_jinja,
)


def test_render_object_get_and_literal_text():
    text = render_jinja(
        "用户名称：{{ data.get('customerName') }}，户号：{{ data.get('customerCode') }}",
        {"data": {"customerName": "张三", "customerCode": "10086"}},
    )
    assert text == "用户名称：张三，户号：10086"


def test_render_for_and_if():
    text = render_jinja(
        "{% for item in items %}{{ item }}{% if not loop.last %},{% endif %}{% endfor %}",
        {"items": ["a", "b"]},
    )
    assert text == "a,b"


def test_literal_double_underscore_text_allowed():
    text = render_jinja("Markdown __bold__ and field __init__ ok", {})
    assert text == "Markdown __bold__ and field __init__ ok"


def test_dict_key_with_dunder_name_allowed():
    text = render_jinja("{{ data.get('__init__') }}", {"data": {"__init__": "ok"}})
    assert text == "ok"


def test_block_dunder_attribute():
    with pytest.raises(TemplateRenderError, match="forbidden dunder access"):
        render_jinja("{{ ''.__class__ }}", {})


def test_block_private_attribute():
    with pytest.raises(TemplateRenderError, match="forbidden dunder access"):
        render_jinja("{{ obj._secret }}", {"obj": type("O", (), {"_secret": "x"})()})


def test_block_include_import_extends():
    for template in ("{% include 'x' %}", "{% import 'x' as y %}", "{% extends 'x' %}", "{% from 'x' import y %}"):
        with pytest.raises(TemplateRenderError, match="forbidden jinja tag"):
            render_jinja(template, {})


def test_empty_template_rejected():
    with pytest.raises(TemplateRenderError):
        render_jinja("   ", {})


def test_nested_huge_range_rejected_before_render():
    """工单复现：嵌套 range(10000)×range(10000) 应在解析阶段拒绝，不拖死进程。"""
    template = (
        "{% for i in range(10000) %}"
        "{% for j in range(10000) %}AAAAA{% endfor %}"
        "{% endfor %}"
    )
    with pytest.raises(TemplateRenderError, match="iteration limit|range\\(\\) size"):
        render_jinja(template, {})


def test_single_range_over_limit_rejected(monkeypatch):
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_RANGE_SIZE", 100)
    with pytest.raises(TemplateRenderError, match="range\\(\\) size"):
        render_jinja("{% for i in range(101) %}x{% endfor %}", {})


def test_range_zero_step_becomes_template_render_error():
    """range(..., 0) 的 ValueError 须收成 TemplateRenderError，不能裸漏。"""
    with pytest.raises(TemplateRenderError, match="invalid range"):
        render_jinja("{{ range(1, 2, 0) }}", {})
    with pytest.raises(TemplateRenderError, match="invalid range"):
        render_jinja("{% for i in range(1, 2, 0) %}x{% endfor %}", {})


def test_range_overflow_becomes_template_render_error():
    """超大 range 的 len() OverflowError 须收成 TemplateRenderError。"""
    with pytest.raises(TemplateRenderError, match="invalid range"):
        render_jinja("{{ range(10 ** 100) }}", {})


def test_static_invalid_range_does_not_leak_raw_errors():
    """非法/溢出常量 range 经静态分析与渲染均须 TemplateRenderError，不泄漏裸异常。"""
    with pytest.raises(TemplateRenderError, match="invalid range"):
        render_jinja("{% for i in range(1, 2, 0) %}x{% endfor %}", {})
    with pytest.raises(TemplateRenderError, match="invalid range"):
        render_jinja("{% for i in range(" + ("9" * 100) + ") %}x{% endfor %}", {})


def test_loop_iteration_budget_runtime(monkeypatch):
    import agent_runtime.extension.workflow_node.template_jinja as tj

    # range 参数来自变量时静态无法估乘积；运行时计数应拦住
    monkeypatch.setattr(tj, "MAX_RANGE_SIZE", 1000)
    monkeypatch.setattr(tj, "MAX_LOOP_ITERATIONS", 50)
    with pytest.raises(TemplateRenderError, match="loop iterations exceeded"):
        render_jinja(
            "{% for i in range(outer) %}{% for j in range(inner) %}x{% endfor %}{% endfor %}",
            {"outer": 2, "inner": 80},
        )


def test_output_length_limit(monkeypatch):
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_OUTPUT_CHARS", 20)
    monkeypatch.setattr(tj, "MAX_LOOP_ITERATIONS", 10_000)
    with pytest.raises(TemplateRenderError, match="output length"):
        render_jinja("{% for i in range(10) %}abcdefghij{% endfor %}", {})


def test_list_loop_iteration_budget(monkeypatch):
    """for 遍历传入 list 也应计入迭代预算，不能只靠 range 护栏。"""
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_LOOP_ITERATIONS", 50)
    with pytest.raises(TemplateRenderError, match="loop iterations exceeded"):
        render_jinja(
            "{% for item in items %}x{% endfor %}",
            {"items": list(range(80))},
        )


def test_nested_list_loop_iteration_budget(monkeypatch):
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_LOOP_ITERATIONS", 25)
    rows = [list(range(10)) for _ in range(10)]
    with pytest.raises(TemplateRenderError, match="loop iterations exceeded"):
        render_jinja(
            "{% for row in rows %}{% for cell in row %}{{ cell }}{% endfor %}{% endfor %}",
            {"rows": rows},
        )


def test_dict_loop_iteration_budget(monkeypatch):
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_LOOP_ITERATIONS", 30)
    with pytest.raises(TemplateRenderError, match="loop iterations exceeded"):
        render_jinja(
            "{% for k in data %}{{ k }}{% endfor %}",
            {"data": {str(i): i for i in range(50)}},
        )


def test_dictsort_respects_iteration_budget(monkeypatch):
    """|dictsort 须在排序前按 items 计入预算，不能因 Mapping 直通而绕过。"""
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_LOOP_ITERATIONS", 30)
    with pytest.raises(TemplateRenderError, match="loop iterations exceeded"):
        render_jinja(
            "{{ data|dictsort|length }}",
            {"data": {str(i): i for i in range(50)}},
        )


def test_moderate_dictsort_still_ok(monkeypatch):
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_LOOP_ITERATIONS", 100)
    assert render_jinja(
        "{{ data|dictsort|map('first')|join(',') }}",
        {"data": {"b": 2, "a": 1}},
    ) == "a,b"


def test_output_length_caught_during_concat(monkeypatch):
    """超长输出应在 concat 拼接过程中拦截，而不仅依赖最终 len 检查。"""
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_OUTPUT_CHARS", 50)
    monkeypatch.setattr(tj, "MAX_LOOP_ITERATIONS", 10_000)
    with pytest.raises(TemplateRenderError, match="output length"):
        render_jinja(
            "{% for item in items %}{{ item }}{% endfor %}",
            {"items": ["abcdefghij"] * 20},
        )


def test_static_string_mul_rejected_before_render(monkeypatch):
    """字面量 'x' * N 超限应在解析期拒绝，避免先分配超大字符串。"""
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_OUTPUT_CHARS", 100)
    with pytest.raises(TemplateRenderError, match="output length"):
        render_jinja("{{ 'ab' * 1000 }}", {})


def test_static_chained_string_mul_rejected(monkeypatch):
    """链式 'x' * a * b 应静态折叠拦截，不能只认单层 Mul。"""
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_OUTPUT_CHARS", 1000)
    with pytest.raises(TemplateRenderError, match="output length"):
        render_jinja("{{ 'x' * 999 * 999 }}", {})


def test_runtime_string_mul_rejected_before_alloc(monkeypatch):
    """变量侧字符串重复在 call_binop 分配前拦截（非 finalize 事后）。"""
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_OUTPUT_CHARS", 50)
    with pytest.raises(TemplateRenderError, match="output length"):
        render_jinja("{{ text * n }}", {"text": "abcdefghij", "n": 20})


def test_runtime_chained_string_mul_rejected(monkeypatch):
    """运行时链式乘法每一步分配前检查，避免中间串再乘爆内存。"""
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_OUTPUT_CHARS", 50)
    with pytest.raises(TemplateRenderError, match="output length"):
        render_jinja("{{ text * a * b }}", {"text": "xy", "a": 10, "b": 10})


def test_moderate_string_mul_still_ok(monkeypatch):
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_OUTPUT_CHARS", 100)
    assert render_jinja("{{ 'ab' * 2 * 3 }}", {}) == "abababababab"


def test_list_repeat_rejected_before_alloc(monkeypatch):
    """list*int 应在分配前拒绝，不能等 OOM。"""
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_LOOP_ITERATIONS", 1000)
    with pytest.raises(TemplateRenderError, match="sequence length"):
        render_jinja("{{ [0] * 1000000000 }}", {})


def test_list_repeat_from_variable_rejected(monkeypatch):
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_LOOP_ITERATIONS", 100)
    with pytest.raises(TemplateRenderError, match="sequence length"):
        render_jinja("{{ items * n }}", {"items": [0], "n": 10_000})


def test_int_pow_rejected_before_compute(monkeypatch):
    """大整数幂应在计算前拒绝。"""
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_POW_EXPONENT", 100)
    with pytest.raises(TemplateRenderError, match="exponent|power result bits"):
        render_jinja("{{ 10 ** 1000000000 }}", {})


def test_moderate_list_repeat_and_pow_ok(monkeypatch):
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_LOOP_ITERATIONS", 100)
    monkeypatch.setattr(tj, "MAX_POW_EXPONENT", 100)
    assert render_jinja("{{ ([1,2] * 2)|join(',') }}", {}) == "1,2,1,2"
    assert render_jinja("{{ 2 ** 10 }}", {}) == "1024"


def test_percent_format_width_rejected_before_alloc(monkeypatch):
    """'%Ns' % x 超限须在分配前拒绝（宽度可达 1e9，不能先造串）。"""
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_OUTPUT_CHARS", 1000)
    with pytest.raises(TemplateRenderError, match="output length"):
        render_jinja("{{ '%1000000000s' % 'x' }}", {})


def test_percent_format_length_modifier_width_rejected_before_alloc(monkeypatch):
    """含 h/l/L 修饰符的 %Nld/%Nls 等也须宽度预检，不能先分配再拒。"""
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_OUTPUT_CHARS", 1000)
    for tmpl in (
        "{{ '%1000000000ld' % 1 }}",
        "{{ '%1000000000ls' % 'x' }}",
        "{{ '%1000000000hd' % 1 }}",
    ):
        with pytest.raises(TemplateRenderError, match="output length"):
            render_jinja(tmpl, {})


def test_percent_star_width_rejected_before_alloc(monkeypatch):
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_OUTPUT_CHARS", 1000)
    with pytest.raises(TemplateRenderError, match="output length"):
        render_jinja("{{ '%*s' % (n, 'x') }}", {"n": 10**9})


def test_str_pad_methods_rejected_before_alloc(monkeypatch):
    """ljust/rjust/center/zfill 按宽度分配前拦截。"""
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_OUTPUT_CHARS", 1000)
    for tmpl in (
        "{{ 'x'.ljust(n) }}",
        "{{ 'x'.rjust(n) }}",
        "{{ 'x'.center(n) }}",
        "{{ 'x'.zfill(n) }}",
    ):
        with pytest.raises(TemplateRenderError, match="output length"):
            render_jinja(tmpl, {"n": 10**9})


def test_str_format_width_rejected_before_alloc(monkeypatch):
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_OUTPUT_CHARS", 1000)
    with pytest.raises(TemplateRenderError, match="output length"):
        render_jinja("{{ '{:>1000000000}'.format('x') }}", {})
    with pytest.raises(TemplateRenderError, match="output length"):
        render_jinja("{{ '{:>{}}'.format('x', n) }}", {"n": 10**9})


def test_format_and_center_filters_rejected_before_alloc(monkeypatch):
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_OUTPUT_CHARS", 1000)
    with pytest.raises(TemplateRenderError, match="output length"):
        render_jinja("{{ '%1000000000s'|format('x') }}", {})
    with pytest.raises(TemplateRenderError, match="output length"):
        render_jinja("{{ 'x'|center(n) }}", {"n": 10**9})


def test_moderate_percent_and_pad_still_ok(monkeypatch):
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_OUTPUT_CHARS", 100)
    assert render_jinja("{{ 10 % 3 }}", {}) == "1"
    assert render_jinja("{{ '%5s' % 'x' }}", {}) == "    x"
    assert render_jinja("{{ 'x'.ljust(5) }}", {}) == "x    "
    assert render_jinja("{{ 'x'|center(5) }}", {}) == "  x  "
    assert render_jinja("{{ '%3s'|format('ab') }}", {}) == " ab"
    assert render_jinja("{{ sep.join(items) }}", {"sep": ",", "items": ["a", "b"]}) == "a,b"


def test_str_join_infinite_hits_budget_and_stops(monkeypatch):
    """sep.join(无限迭代) 须计入预算/cancel，超时后 worker 不得继续狂跑。"""
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "RENDER_TIMEOUT_SEC", 1)
    monkeypatch.setattr(tj, "MAX_LOOP_ITERATIONS", 10**9)
    iters = {"n": 0}

    def _infinite_items():
        while True:
            iters["n"] += 1
            yield "a"

    with pytest.raises(
        TemplateRenderError, match="timed out|loop iterations|output length"
    ):
        render_jinja("{{ sep.join(items) }}", {"sep": ",", "items": _infinite_items()})
    n_at_return = iters["n"]
    time.sleep(0.4)
    # 护栏抛错后 worker 应结束；允许少量在途增量，但不能再涨数百万
    assert iters["n"] - n_at_return < 50_000


def test_join_filter_rejects_large_output_before_alloc(monkeypatch):
    """|join 须与 str.join 一样在拼接前累计长度，不能等 do_join 造完超大串。"""
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_OUTPUT_CHARS", 1000)
    with pytest.raises(TemplateRenderError, match="output length"):
        render_jinja(
            "{{ items|join('') }}",
            {"items": ["y" * 500_000, "z" * 500_000]},
        )


def test_moderate_join_filter_still_ok(monkeypatch):
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_OUTPUT_CHARS", 100)
    assert render_jinja("{{ items|join(',') }}", {"items": [1, 2, 3]}) == "1,2,3"
    assert (
        render_jinja(
            "{{ users|join(',', attribute='name') }}",
            {"users": [{"name": "a"}, {"name": "b"}]},
        )
        == "a,b"
    )


def test_str_replace_amplify_rejected_before_alloc(monkeypatch):
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_OUTPUT_CHARS", 1000)
    owner = ("a" + "b") * 450
    replacement = "y" * 900
    with pytest.raises(TemplateRenderError, match="output length"):
        render_jinja(
            "{{ owner.replace(old, replacement) }}",
            {"owner": owner, "old": "a", "replacement": replacement},
        )


def test_str_format_repeated_args_rejected_before_alloc(monkeypatch):
    """'{}{}{}'.format(x,x,x) 须按字段值总长预拒，不能先拼再拒。"""
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_OUTPUT_CHARS", 1000)
    x = "z" * 900
    with pytest.raises(TemplateRenderError, match="output length"):
        render_jinja("{{ '{}{}{}'.format(x, x, x) }}", {"x": x})


def test_str_format_invalid_string_becomes_template_render_error():
    """非法 format 串的 ValueError 须收成 TemplateRenderError。"""
    with pytest.raises(TemplateRenderError, match="invalid format string|format failed"):
        render_jinja("{{ '{'.format() }}", {})
    with pytest.raises(TemplateRenderError, match="invalid format string|format failed"):
        render_jinja("{{ '}'.format() }}", {})


def test_moderate_nested_loops_still_ok():
    text = render_jinja(
        "{% for i in range(3) %}{% for j in range(2) %}{{ i }}{{ j }};{% endfor %}{% endfor %}",
        {},
    )
    assert text == "00;01;10;11;20;21;"


def test_render_timeout_does_not_block_on_shutdown(monkeypatch):
    """超时后调用方应立刻收到错误，不无限 join 工作线程。"""
    import threading

    import agent_runtime.extension.workflow_node.template_jinja as tj

    release = threading.Event()

    def _hang(*_args, **_kwargs):
        release.wait(timeout=30)
        return "never"

    monkeypatch.setattr(tj, "RENDER_TIMEOUT_SEC", 1)
    monkeypatch.setattr(tj, "_render_with_guards", _hang)
    started = time.monotonic()
    try:
        with pytest.raises(TemplateRenderError, match="timed out"):
            render_jinja("{{ x }}", {"x": 1})
        elapsed = time.monotonic() - started
        assert elapsed < 5, f"timeout path blocked too long: {elapsed:.2f}s"
    finally:
        release.set()


def test_infinite_iterator_hits_loop_budget(monkeypatch):
    """无限迭代器经 for 遍历时应被迭代预算拦住，调用方尽快返回。"""
    import agent_runtime.extension.workflow_node.template_jinja as tj

    def _infinite():
        while True:
            yield "x"

    monkeypatch.setattr(tj, "MAX_LOOP_ITERATIONS", 100)
    monkeypatch.setattr(tj, "RENDER_TIMEOUT_SEC", 5)
    started = time.monotonic()
    with pytest.raises(TemplateRenderError, match="loop iterations exceeded"):
        render_jinja("{% for item in items %}{{ item }}{% endfor %}", {"items": _infinite()})
    assert time.monotonic() - started < 3, "infinite iterator should fail via budget, not hang"


def test_static_range_zero_outer_not_false_positive(monkeypatch):
    """外层 range(0) 的 size=0 不应触发嵌套乘积误杀。"""
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_LOOP_ITERATIONS", 50)
    text = render_jinja(
        "{% for i in range(0) %}"
        "{% for j in range(100) %}"
        "{% for k in range(100) %}x{% endfor %}"
        "{% endfor %}{% endfor %}",
        {},
    )
    assert text == ""


def test_filter_last_and_random_still_work():
    """|last / |random 需要下标或 reversed，包装后不能破坏合法模板。"""
    items = ["a", "b", "c"]
    assert render_jinja("{{ items|last }}", {"items": items}) == "c"
    assert render_jinja("{{ items|first }}", {"items": items}) == "a"
    assert render_jinja("{{ 'xyz'|last }}", {}) == "z"
    picked = render_jinja("{{ items|random }}", {"items": items})
    assert picked in items


def test_filter_reverse_on_string_keeps_str_semantics():
    """|reverse 对 str 必须走 Jinja 字符串分支，输出 cba 而非 generator repr。"""
    assert render_jinja("{{ 'abc'|reverse }}", {}) == "cba"
    assert render_jinja("{{ items|reverse|list|join('') }}", {"items": ["a", "b", "c"]}) == "cba"


def test_filter_list_hits_loop_budget(monkeypatch):
    """|list / |join 等过滤器内部迭代也应计入预算。"""
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_LOOP_ITERATIONS", 50)
    with pytest.raises(TemplateRenderError, match="loop iterations exceeded"):
        render_jinja("{{ items|list|join('') }}", {"items": list(range(80))})


def test_filter_sum_infinite_hits_budget_or_cancel(monkeypatch):
    """|sum 走过滤器护栏；超时后 cancel 应让生成器停止推进。"""
    import agent_runtime.extension.workflow_node.template_jinja as tj

    progress = {"n": 0}

    def _infinite():
        while True:
            progress["n"] += 1
            yield 1

    monkeypatch.setattr(tj, "MAX_LOOP_ITERATIONS", 10_000_000)
    monkeypatch.setattr(tj, "RENDER_TIMEOUT_SEC", 0.2)
    with pytest.raises(TemplateRenderError, match="timed out|loop iterations exceeded"):
        render_jinja("{{ items|sum }}", {"items": _infinite()})
    n_at_return = progress["n"]
    time.sleep(0.3)
    # cancel/deadline 后不应再大幅推进
    assert progress["n"] - n_at_return < 50_000, (
        f"generator kept running after return: {n_at_return} -> {progress['n']}"
    )


def test_filter_sort_hits_loop_budget(monkeypatch):
    import agent_runtime.extension.workflow_node.template_jinja as tj

    monkeypatch.setattr(tj, "MAX_LOOP_ITERATIONS", 30)
    with pytest.raises(TemplateRenderError, match="loop iterations exceeded"):
        render_jinja("{{ items|sort|join(',') }}", {"items": list(range(50))})


def test_render_concurrency_limit_blocks_extra(monkeypatch):
    """槽被占满且在总超时内未释放时，超额请求应报 concurrency limit。"""
    import threading

    import agent_runtime.extension.workflow_node.template_jinja as tj

    release = threading.Event()
    started = threading.Event()
    monkeypatch.setattr(tj, "_render_slots", threading.BoundedSemaphore(1))
    monkeypatch.setattr(tj, "RENDER_TIMEOUT_SEC", 1)

    def _hang(*_args, **_kwargs):
        started.set()
        release.wait(timeout=30)
        return "never"

    monkeypatch.setattr(tj, "_render_with_guards", _hang)

    errors: list[BaseException] = []

    def _first_call() -> None:
        try:
            render_jinja("{{ x }}", {"x": 1})
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    t = threading.Thread(target=_first_call)
    t.start()
    assert started.wait(timeout=3), "first worker did not start"
    try:
        started_wait = time.monotonic()
        with pytest.raises(TemplateRenderError, match="concurrency limit"):
            render_jinja("{{ x }}", {"x": 1})
        # 等槽应对齐 RENDER_TIMEOUT_SEC，而非硬编码 1s 的更短值；此处超时=1
        assert time.monotonic() - started_wait >= 0.8
        t.join(timeout=5)
        assert errors and "timed out" in str(errors[0])
    finally:
        release.set()
        t.join(timeout=5)


def test_render_waits_for_slot_within_timeout(monkeypatch):
    """合法渲染占满槽时，后来者应能等到槽释放（在总超时内），而不是 1s 就失败。"""
    import threading

    import agent_runtime.extension.workflow_node.template_jinja as tj

    release_first = threading.Event()
    first_started = threading.Event()
    monkeypatch.setattr(tj, "_render_slots", threading.BoundedSemaphore(1))
    monkeypatch.setattr(tj, "RENDER_TIMEOUT_SEC", 3)

    def _first_guard(*_args, **_kwargs):
        first_started.set()
        release_first.wait(timeout=30)
        return "first"

    calls = {"n": 0}

    def _dispatch(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return _first_guard(*args, **kwargs)
        return "second"

    # 用字符串名 setattr，避免测试里直接访问受保护成员（G.CLS.11）
    monkeypatch.setattr(tj, "_render_with_guards", _dispatch)

    results: list[str] = []
    errors: list[BaseException] = []

    def _run_first() -> None:
        try:
            results.append(render_jinja("{{ a }}", {"a": 1}))
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    t = threading.Thread(target=_run_first)
    t.start()
    assert first_started.wait(timeout=3)

    def _release_soon() -> None:
        time.sleep(0.5)
        release_first.set()

    threading.Thread(target=_release_soon, daemon=True).start()
    # 若仍 min(1.0,...) 且第一槽永不释放会失败；这里 0.5s 后释放，应成功等到
    second = render_jinja("{{ b }}", {"b": 2})
    t.join(timeout=5)
    assert not errors
    assert results == ["first"]
    assert second == "second"
