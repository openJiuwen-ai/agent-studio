# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
"""instruction_optimizer critique prompt 的工具描述占位替换单测。

`_process_with_placeholder` 的 meta/schema 两条路径对
`{{API_TOOLS_DESCRIPTION}}` 调用 `str.replace()` 但丢弃返回值（字符串不可变，
replace 返回新串），占位符原样进入 LLM prompt；同函数下一行的
`{{PLACEHOLDER_TO_OPTIMIZE}}`（:207-208）与 `_process_without_placeholder`
（:231-232）均为正确赋值写法——本用例钉住两条路径的正确替换。
"""

from types import SimpleNamespace

from agent_builder.prompt.tune.instruction.instruction_optimizer import GreedyOptimizer


def _make_optimizer(captured):
    """构造最小 GreedyOptimizer：桩 _chat_completion 捕获发往 LLM 的 prompt。"""
    opt = object.__new__(GreedyOptimizer)
    setattr(opt, "_params", SimpleNamespace(
        opt_schema=["tone"],
        placeholder=[{"name": "tone", "content": "friendly"}],
        opt_placeholder=None,
    ))
    setattr(opt, "_prompt_pool", {
        "critique_refine_template_meta": "TOOLS={{API_TOOLS_DESCRIPTION}}\nINS={{PROMPT_META_TEMPLATE}}",
        "critique_refine_template_schema": "TOOLS={{API_TOOLS_DESCRIPTION}}\nPH={{PLACEHOLDER_TO_OPTIMIZE}}",
    })

    def fake_chat(prompt):
        captured.append(prompt)
        return "{}"

    setattr(opt, "_chat_completion", fake_chat)
    setattr(opt, "_parse_optimized_prompt", lambda refined: "meta-result")
    # 返回 None 触发 schema_update_res 早退，避开评估器依赖
    setattr(opt, "_parse_optimized_placeholders", lambda refined: None)
    return opt


def test_placeholder_path_substitutes_tools_description():
    """meta 路径：LLM 收到的 prompt 不得残留 {{API_TOOLS_DESCRIPTION}} 字面量。"""
    captured = []
    opt = _make_optimizer(captured)
    process = getattr(GreedyOptimizer, "_process_with_placeholder")

    process(opt, "instr", "err-str", "tg-str", ["toolA"])

    assert len(captured) == 2, "meta/schema 两条路径各应发一次 LLM 请求"
    # meta 路径：工具描述须被替换为实际内容
    assert "{{API_TOOLS_DESCRIPTION}}" not in captured[0]
    assert "toolA" in captured[0]
    # schema 路径：工具描述替换 + 既有占位（opt_placeholder）替换同时成立
    assert "{{API_TOOLS_DESCRIPTION}}" not in captured[1]
    assert "toolA" in captured[1]
