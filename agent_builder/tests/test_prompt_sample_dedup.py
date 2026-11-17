# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
"""
提示词优化采样去重（issue #1643）单测。

覆盖 resample_examples / sample_examples 的错误行排除语义：
- 已选错误行对应的原始数据行（按 order 索引）不再进入填充池；
- 同 question、不同 label/variable 的其他行保持可采样（issue #1643 复现场景）；
- 数据集存在重复 question 时填充池收缩不抛 ValueError（min 兜底）；
- 变量模式与非变量模式行为一致。
"""

import random

from agent_builder.prompt.tune.joint_optimizer import JointOptimizer


def _make_optimizer(dataset, sampled_incorrect, example_num=2, cot_example_num=0, variable=False):
    optimizer = JointOptimizer()
    optimizer.dataset = dataset
    optimizer.sampled_incorrect_data = sampled_incorrect
    optimizer.variable = variable
    optimizer.params = type(
        "Params", (), {"example_num": example_num, "cot_example_num": cot_example_num}
    )()
    return optimizer


def _dup_question_dataset():
    """issue #1643 复现数据：同 question 不同 label 的两行 + 其他行"""
    return [
        {"question": "Q0", "label": "A0", "variable": {}},
        {"question": "Q0", "label": "A1", "variable": {}},
        {"question": "Q2", "label": "A2", "variable": {}},
        {"question": "Q3", "label": "A3", "variable": {}},
    ]


def _variable_dataset():
    """变量模式数据：同 question、不同 variable 的两行 + 其他行"""
    return [
        {"question": "shared", "label": "A0", "variable": {"x": "v0"}},
        {"question": "shared", "label": "A1", "variable": {"x": "v1"}},
        {"question": "Q2", "label": "A2", "variable": {}},
        {"question": "Q3", "label": "A3", "variable": {}},
    ]


def _error_row(row, order):
    return dict(row, order=order, score=0, predict="Wrong", reason="Diff")


def test_resample_error_row_source_row_not_resampled():
    """已选错误行（order=0）对应的原始行不再被补入"""
    dataset = _dup_question_dataset()
    opt = _make_optimizer(dataset, [_error_row(dataset[0], 0)])
    result = opt.resample_examples(opt.sampled_incorrect_data)
    q0a0 = []
    for d in result:
        if isinstance(d, dict) and d.get("question") == "Q0" and d.get("label") == "A0":
            q0a0.append(d)
    assert len(q0a0) == 1, "错误行来源行（Q0/A0）被重复补入"
    # 旧实现（按键排除）下 Q0/A1 被一并排除、永不可采样——回归保护：
    # 多轮采样中 Q0/A1 必须出现（同 question 不同 label 的行保持可采样）
    seen_a1 = False
    for _ in range(100):
        r = opt.resample_examples(opt.sampled_incorrect_data)
        for d in r:
            if isinstance(d, dict) and d.get("question") == "Q0" and d.get("label") == "A1":
                seen_a1 = True
                break
        if seen_a1:
            break
    assert seen_a1, "同 question 不同 label 的行（Q0/A1）被按键排除，回归 bug"


def test_resample_same_question_other_label_still_samplable():
    """issue #1643 核心：同 question、不同 label 的其他行保持可采样"""
    # dataset 4 行 > min_len(2)，确保 resample_examples 走按 order 排除
    # 的分支而非 len(dataset) <= min_len 的提前返回
    dataset = _dup_question_dataset()
    opt = _make_optimizer(dataset, [_error_row(dataset[0], 0)])
    opt.params.example_num = 2
    opt.params.cot_example_num = 0
    seen = set()
    for _ in range(100):
        result = opt.resample_examples(opt.sampled_incorrect_data)
        labels = []
        for d in result:
            if isinstance(d, dict):
                labels.append(d.get("label"))
        seen.update(labels)
    assert "A1" in seen, "同 question 不同 label 的行（Q0/A1）不应被按键排除"


def test_resample_never_exceeds_min_len():
    """min_len < len(dataset)：走按 order 排除的填充分支，结果不超上限"""
    dataset = _dup_question_dataset()
    opt = _make_optimizer(dataset, [_error_row(dataset[0], 0)])
    opt.params.example_num = 3
    opt.params.cot_example_num = 0
    result = opt.resample_examples(opt.sampled_incorrect_data)
    assert len(result) <= 3


def test_sample_error_row_source_row_not_sampled_twice():
    """已选错误行的原始行不被再次抽为示例"""
    dataset = _dup_question_dataset()
    opt = _make_optimizer(dataset, [_error_row(dataset[0], 0)])
    random.seed(7)
    for _ in range(100):
        result = opt.sample_examples(2)
        q0a0 = []
        for d in result:
            if (
                isinstance(d, dict)
                and d.get("question", "").startswith("Q0")
                and d.get("label") == "A0"
            ):
                q0a0.append(d)
        assert len(q0a0) == 1, "错误行来源行（Q0/A0）被重复采样"


def test_sample_with_error_cases_keeps_count():
    dataset = _dup_question_dataset()
    opt = _make_optimizer(dataset, [_error_row(dataset[0], 0)])
    result = opt.sample_examples(3)
    assert len(result) == 3


def test_sample_small_dataset_fallback():
    """小样本兜底：num_examples >= len(dataset) 时返回全量副本"""
    dataset = _dup_question_dataset()
    opt = _make_optimizer(dataset, [])
    result = opt.sample_examples(10)
    assert len(result) == 4


def test_variable_mode_error_row_excluded_by_order():
    """变量模式同样按 order 索引排除，同 question 不同 variable 的行保留"""
    # dataset 4 行 > min_len(2)，确保 resample_examples 走按 order 排除
    # 的分支而非 len(dataset) <= min_len 的提前返回（提前返回的全量副本
    # 不携带 order 字段，覆盖不到排除逻辑）
    dataset = _variable_dataset()
    opt = _make_optimizer(
        dataset, [_error_row(dataset[0], 0)], example_num=2, variable=True
    )
    result = opt.resample_examples(opt.sampled_incorrect_data)
    orders = []
    for d in result:
        if isinstance(d, dict) and "order" in d:
            orders.append(d.get("order"))
    assert orders.count(0) == 1
