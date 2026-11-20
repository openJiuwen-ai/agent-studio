# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Regression tests for unexpected JSON types returned by an LLM judge."""

import threading
from unittest.mock import Mock

import pytest

from agent_builder.prompt.tune.base.constant import TuneConstant
from agent_builder.prompt.tune.joint_evaluator import JointEvaluatorWithRef


@pytest.fixture
def evaluator():
    """Exercise evaluation without configuring or calling external models."""
    instance = object.__new__(JointEvaluatorWithRef)
    instance.access_answer_prompt = (
        "Question: {{question}}\nAnswer: {{answer_match}}\nReference: {{actual_answer}}"
    )
    instance.eval_mode = TuneConstant.EVALUATION_METHOD_LLM
    instance.llm_parallel = 2
    instance.handle_inference_retry = Mock()
    return instance


@pytest.mark.parametrize(
    "judge_json",
    [
        '[{"result": true, "reason": "correct"}]',
        '"unexpected response"',
        "42",
        "true",
        "[]",
        "null",
        "{}",
        '{"result":',
    ],
)
def test_non_object_or_invalid_judge_json_scores_zero(evaluator, judge_json):
    evaluator.handle_inference_retry.return_value = {
        "content": f"```json\n{judge_json}\n```"
    }

    score, reason = evaluator.compare_llm("question", "reference", "answer")

    assert score == 0
    assert reason.startswith("Parse JSON error:")


@pytest.mark.parametrize("result, expected_score", [(True, 1), (False, 0)])
def test_object_judge_response_keeps_score_and_reason(
    evaluator, result, expected_score
):
    evaluator.handle_inference_retry.return_value = {
        "content": (
            '```json\n{\n  "result": '
            + str(result).lower()
            + ',\n  "reason": "judge explanation"\n}\n```'
        )
    }

    assert evaluator.compare_llm("question", "reference", "answer") == (
        expected_score,
        "judge explanation",
    )


def test_evaluation_finishes_when_one_judge_response_is_an_array(evaluator):
    dataset = [
        {"question": "invalid judge case", "label": "reference"},
        {"question": "valid judge case", "label": "reference"},
    ]

    def model_response(dialogue, prompt=None, is_assistant=True):
        if is_assistant:
            return {"content": "answer"}
        if "invalid judge case" in dialogue:
            return {"content": '```json\n[{"result": true}]\n```'}
        return {"content": '```json\n{"result": true, "reason": "correct"}\n```'}

    evaluator.handle_inference_retry.side_effect = model_response

    accuracy, failed_examples, results = evaluator.evaluate(
        "You are a helpful assistant.", dataset, threading.Event()
    )

    assert accuracy == 0.5
    assert [result["score"] for result in results] == [0, 1]
    assert results[0]["reason"] == "Parse JSON error: Expected an object"
    assert [example["question"] for example in failed_examples] == [
        "invalid judge case"
    ]
    assert evaluator.handle_inference_retry.call_count == 4
