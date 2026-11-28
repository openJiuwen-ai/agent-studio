# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Do not select an evaluated dataset row again when filling example slots."""

import copy
import threading
from unittest.mock import Mock

import pytest

from agent_builder.prompt.tune.base.constant import TuneConstant
from agent_builder.prompt.tune.joint_evaluator import JointEvaluatorWithRef
from agent_builder.prompt.tune.joint_optimizer import JointOptimizer


@pytest.fixture(params=["resample", "few-shot"])
def select_cases(request, monkeypatch):
    # Pick the first eligible rows so an incorrectly retained row is always exposed.
    monkeypatch.setattr("random.sample", lambda population, k: list(population[:k]))

    def select(optimizer, errors, count):
        optimizer.params.example_num = count
        optimizer.params.cot_example_num = 0
        optimizer.sampled_incorrect_data = errors
        if request.param == "resample":
            return optimizer.resample_examples(errors)
        return optimizer.sample_examples(count)

    return select


def example_identity(case):
    return (
        case.get("question"),
        case.get("label"),
        case.get("variable", {}),
    )


@pytest.mark.parametrize("failed_index", [0, 1, 3])
@pytest.mark.parametrize("with_variables", [False, True])
def test_real_evaluation_rows_are_not_selected_again(
    select_cases, failed_index, with_variables
):
    dataset = [
        {
            "question": "user: <RAW_PROMPT>\n"
            if with_variables
            else f"Question {index}",
            "label": "Answer" if with_variables else f"Answer {index}",
            "variable": {"topic": f"Topic {index}"} if with_variables else {},
            "tools": [{"name": f"tool_{index}"}],
        }
        for index in range(4)
    ]
    original_dataset = copy.deepcopy(dataset)
    evaluator = object.__new__(JointEvaluatorWithRef)
    evaluator.eval_mode = TuneConstant.EVALUATION_METHOD_TEXT
    evaluator.llm_parallel = 1
    evaluator.handle_inference_retry = Mock(
        side_effect=[
            {"content": "Wrong" if index == failed_index else case.get("label")}
            for index, case in enumerate(dataset)
        ]
    )
    accuracy, errors, evaluations = evaluator.evaluate(
        "Answer {{topic}}", dataset, threading.Event()
    )
    assert accuracy == 0.75
    assert len(errors) == 1
    assert errors[0].get("order") == failed_index
    assert "tools" not in errors[0]
    original_errors = copy.deepcopy(errors)
    optimizer = JointOptimizer()
    optimizer.dataset = dataset
    optimizer.variable = ["topic"] if with_variables else []

    selected = select_cases(optimizer, errors, 2)

    assert len(selected) == 2
    expected_question = (
        str(dataset[failed_index].get("variable"))
        if with_variables
        else dataset[failed_index].get("question")
    )
    if "order" in selected[0]:
        assert example_identity(selected[0]) == example_identity(errors[0])
        assert example_identity(selected[1]) != example_identity(errors[0])
    else:
        assert selected[0].get("question") == expected_question
        assert selected[1] != selected[0]
    assert dataset == original_dataset
    assert errors == original_errors
    assert len(evaluations) == 4


@pytest.mark.parametrize(
    "variant", ["different-labels", "different-variables", "duplicate-rows"]
)
def test_records_without_order_keep_other_dataset_occurrences(select_cases, variant):
    dataset = [
        {"question": "Question", "label": "Answer", "variable": {}},
        {
            "question": "Question",
            "label": "Other" if variant == "different-labels" else "Answer",
            "variable": {"topic": "Other"} if variant == "different-variables" else {},
        },
        {"question": "Question 2", "label": "Answer 2", "variable": {}},
        {"question": "Question 3", "label": "Answer 3", "variable": {}},
    ]
    errors = [dict(dataset[1], score=0, predict="Wrong", reason="Different")]
    original_dataset = copy.deepcopy(dataset)
    original_errors = copy.deepcopy(errors)
    optimizer = JointOptimizer()
    optimizer.dataset = dataset
    optimizer.variable = ["topic"] if variant == "different-variables" else []

    selected = select_cases(optimizer, errors, 3)

    assert len(selected) == 3
    assert selected[1].get("label") == dataset[0].get("label")
    assert selected[2].get("label") == "Answer 2"
    if "score" in selected[0]:
        assert selected[1].get("variable") == dataset[0].get("variable")
    elif variant == "different-variables":
        assert selected[0].get("question") == "{'topic': 'Other'}"
        assert selected[1].get("question") == "{}"
    assert dataset == original_dataset
    assert errors == original_errors


@pytest.mark.parametrize("count", [0, 1, 4, 8])
def test_sampling_without_errors_preserves_count_limits(select_cases, count):
    dataset = [{"question": f"Q{index}", "label": f"A{index}"} for index in range(4)]
    optimizer = JointOptimizer()
    optimizer.dataset = dataset

    selected = select_cases(optimizer, [], count)

    assert len(selected) == min(count, len(dataset))
    assert selected == dataset[:count]
