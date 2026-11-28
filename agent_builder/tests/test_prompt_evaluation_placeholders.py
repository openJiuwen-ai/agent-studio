# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Keep evaluation data literal when rendering the judge's prompt template."""

import threading
from unittest.mock import Mock

import pytest

from agent_builder.prompt.tune.base.case import CaseManager
from agent_builder.prompt.tune.base.constant import TuneConstant
from agent_builder.prompt.tune.base.utils import load_prompt_pool_from_yaml
from agent_builder.prompt.tune.joint_evaluator import JointEvaluatorWithRef


@pytest.fixture
def evaluator():
    instance = object.__new__(JointEvaluatorWithRef)
    instance.access_answer_prompt = "Question: {{question}}\nCandidate: {{answer_match}}\nReference: {{actual_answer}}"
    instance.handle_inference_retry = Mock(
        return_value={"content": '```json\n{"result": true, "reason": "correct"}\n```'}
    )
    return instance


@pytest.mark.parametrize(
    "question, candidate, reference",
    [
        ("Explain {{answer_match}} literally.", "candidate", "reference"),
        ("Explain {{actual_answer}} literally.", "candidate", "reference"),
        ("question", "Keep {{actual_answer}} unchanged.", "reference"),
        ("question", "Keep {{question}} unchanged.", "reference"),
        ("question", "candidate", "Keep {{answer_match}} unchanged."),
        ("question", "candidate", "Keep {{actual_answer}} unchanged."),
        ("question", "candidate", "Keep {{question}} unchanged."),
        ("plain question", "plain candidate", "plain reference"),
        ("", "", ""),
        ("line one\n{{answer_match}}", r"\1\n{{actual_answer}}", "参照回答"),
    ],
)
def test_rendering_preserves_field_contents(evaluator, question, candidate, reference):
    assert evaluator.compare_llm(question, reference, candidate) == (1, "correct")
    result = evaluator.handle_inference_retry.call_args.args[0]

    assert result == (
        f"Question: {question}\nCandidate: {candidate}\nReference: {reference}"
    )


def test_repeated_template_fields_and_unknown_markers(evaluator):
    evaluator.access_answer_prompt = (
        "{{actual_answer}}|{{answer_match}}|{{question}}|{{question}}|{{unknown}}"
    )

    assert evaluator.compare_llm(
        "{{answer_match}}", "reference", "{{actual_answer}}"
    ) == (1, "correct")
    assert (
        evaluator.handle_inference_retry.call_args.args[0]
        == "reference|{{actual_answer}}|{{answer_match}}|{{answer_match}}|{{unknown}}"
    )


@pytest.mark.parametrize("template_name", ["access_answer", "subjective_access_answer"])
def test_dataset_evaluation_sends_unmodified_data_to_judge(evaluator, template_name):
    question = "Explain the literal marker {{actual_answer}}."
    candidate = "The marker is {{actual_answer}}."
    reference = "This is a template variable."
    dataset = CaseManager.validate_with_convert(
        [
            {
                "messages": [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": reference},
                ]
            }
        ],
        CaseManager.convert,
    )
    evaluator.access_answer_prompt = load_prompt_pool_from_yaml()[
        template_name
    ].replace("{{user_compare_rules}}", "None")
    evaluator.eval_mode = TuneConstant.EVALUATION_METHOD_LLM
    evaluator.llm_parallel = 1
    evaluator.handle_inference_retry = Mock(
        side_effect=[
            {"content": candidate},
            {"content": '```json\n{"result": false, "reason": "different"}\n```'},
        ]
    )

    accuracy, failed_examples, results = evaluator.evaluate(
        "Explain template syntax accurately.", dataset, threading.Event()
    )

    judge_prompt = evaluator.handle_inference_retry.call_args.args[0]
    assert dataset[0]["question"] in judge_prompt
    assert candidate in judge_prompt
    assert reference in judge_prompt
    assert '"result": true/false' in judge_prompt
    assert evaluator.handle_inference_retry.call_count == 2
    assert accuracy == 0
    assert failed_examples == results
    assert results[0]["predict"] == candidate
    assert results[0]["reason"] == "different"
