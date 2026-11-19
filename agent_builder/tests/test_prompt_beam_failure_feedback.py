# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
"""Beam-search regression tests for an incumbent outside the candidate pool."""

import threading

import pytest

from agent_builder.prompt.tune.base.utils import JointParams, LLMModelProcess
from agent_builder.prompt.tune.instruction.base_optimizer import OptimizeAlgoConfig
from agent_builder.prompt.tune.instruction.instruction_optimizer import (
    BeamSearchOptimizer,
)
from agent_builder.prompt.tune.joint_evaluator import JointEvaluatorWithRef


@pytest.mark.parametrize("with_placeholder", [False, True])
def test_pruned_incumbent_keeps_failure_feedback(with_placeholder):
    params = JointParams()
    if with_placeholder:
        params.placeholder = [
            {"name": "style", "content": "Be concise", "need_optimize": False}
        ]
    critiques = []
    sequence = 0
    model = object.__new__(LLMModelProcess)

    def chat(messages):
        nonlocal sequence
        sequence += 1
        text = messages[-1]["content"]
        if sequence % 2:
            critiques.append(text)
            return {"content": "Use the supplied failure to correct the instruction."}
        return {"content": f"<PROMPT_OPTIMIZED>Candidate {sequence}</PROMPT_OPTIMIZED>"}

    model.chat = chat
    evaluator = object.__new__(JointEvaluatorWithRef)

    def evaluate(prompt, dataset, stop_event):
        # The incumbent wins globally but is pruned by training-subset scores.
        if len(dataset) == 32:
            return (0.0 if prompt == "Incumbent" else 0.8), [], []
        return (0.95 if prompt == "Incumbent" else 0.2), [], []

    evaluator.evaluate = evaluate
    optimizer = BeamSearchOptimizer(
        OptimizeAlgoConfig(
            params=params,
            model=model,
            stop_event=threading.Event(),
            evaluator=evaluator,
            prompt_combine_func=lambda instruction, placeholders: instruction,
        )
    )
    dataset = [{"question": f"Question {i}", "label": f"Answer {i}"} for i in range(33)]
    failures = [
        {
            "question": "FAILED-QUESTION-UNIQUE",
            "label": "EXPECTED-ANSWER-UNIQUE",
            "predict": "WRONG-ANSWER-UNIQUE",
        }
    ]

    # JointOptimizer keeps its incumbent when the returned full score is lower.
    # Two real rounds prune that incumbent from the persistent beam.
    for _ in range(2):
        optimizer.do_optimize("Incumbent", failures, dataset)

    critiques.clear()
    optimizer.do_optimize("Incumbent", failures, dataset)

    assert len(critiques) == 4  # Three beam candidates and the incumbent.
    for critique in critiques:
        for marker in (
            "FAILED-QUESTION-UNIQUE",
            "EXPECTED-ANSWER-UNIQUE",
            "WRONG-ANSWER-UNIQUE",
        ):
            assert marker in critique
