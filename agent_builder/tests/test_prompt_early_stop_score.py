# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Validate numeric early-stop thresholds through both task entry points."""

import json

import pytest

from agent_builder.prompt.mmapo.validator import ApoTaskParamsValidator
from agent_builder.prompt.tune.service.interface import OptimizeTaskCreationRequest
from agent_builder.prompt.tune.service.validator import (
    TaskParamsValidationException,
    TaskParamsValidator,
)


@pytest.fixture(
    params=[TaskParamsValidator, ApoTaskParamsValidator], ids=["text", "multimodal"]
)
def task_validator(request):
    return request.param


@pytest.fixture
def task_payload():
    return {
        "name": "Early stop regression",
        "desc": "Validate the task's target score before starting optimization.",
        "rawTemplates": "Answer the question accurately.",
        "modelInfo": {"model": "test-model"},
        "assistantInfo": {"model": "test-assistant"},
        "optimizeInfo": {
            "num_iter": 1,
            "cases": [
                {
                    "messages": [
                        {"role": "user", "content": "What is two plus two?"},
                        {"role": "assistant", "content": "Four."},
                    ]
                }
            ],
        },
    }


@pytest.mark.parametrize("score", [0, 1, 0.0, 1.0, 0.65])
def test_json_numeric_thresholds_reach_request_model(
    task_validator, task_payload, score
):
    task_payload["optimizeInfo"]["early_stop_score"] = score
    payload = json.loads(json.dumps(task_payload))

    task_validator.validate_task_parameters(payload)
    creation_info = OptimizeTaskCreationRequest(**payload)

    assert creation_info.optimize_info.early_stop_score == float(score)


@pytest.mark.parametrize("include_null", [False, True], ids=["omitted", "null"])
def test_optional_threshold_behavior_is_preserved(
    task_validator, task_payload, include_null
):
    if include_null:
        task_payload["optimizeInfo"]["early_stop_score"] = None

    task_validator.validate_task_parameters(task_payload)
    creation_info = OptimizeTaskCreationRequest(**task_payload)

    assert creation_info.optimize_info.early_stop_score == (
        None if include_null else 1.0
    )


@pytest.mark.parametrize(
    "score",
    [
        -1,
        2,
        -0.1,
        1.1,
        True,
        False,
        "1",
        [],
        {},
        float("nan"),
        float("inf"),
        -float("inf"),
    ],
)
def test_invalid_thresholds_fail_before_task_creation(
    task_validator, task_payload, score
):
    task_payload["optimizeInfo"]["early_stop_score"] = score

    with pytest.raises(TaskParamsValidationException, match="early_stop_score"):
        task_validator.validate_task_parameters(task_payload)
