# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Exercise retry exhaustion through the public greedy optimizer."""

import threading
from unittest.mock import Mock

import pytest

from agent_builder.adapter.exception_bridge import JiuWenBaseException
from agent_builder.common.exception.status_code import StatusCode
from agent_builder.prompt.tune.base.utils import JointParams, LLMModelProcess
from agent_builder.prompt.tune.instruction.base_optimizer import OptimizeAlgoConfig
from agent_builder.prompt.tune.instruction.instruction_optimizer import GreedyOptimizer
from agent_builder.prompt.tune.joint_evaluator import JointEvaluatorWithRef


@pytest.fixture(params=[False, True], ids=["plain", "with-placeholder"])
def optimizer_components(request):
    params = JointParams()
    if request.param:
        params.placeholder = [
            {"name": "topic", "content": "Weather", "need_optimize": False}
        ]
    model = object.__new__(LLMModelProcess)
    model.chat = Mock()
    evaluator = object.__new__(JointEvaluatorWithRef)
    evaluator.evaluate = Mock(return_value=(0.75, [], []))
    combine = Mock(side_effect=lambda prompt, placeholders: prompt)
    cancel = threading.Event()
    optimizer = GreedyOptimizer(
        OptimizeAlgoConfig(
            params=params,
            model=model,
            evaluator=evaluator,
            stop_event=cancel,
            prompt_combine_func=combine,
        )
    )
    return optimizer, model.chat, evaluator.evaluate, combine, cancel


@pytest.mark.parametrize(
    "reply",
    [
        "No refinement tags",
        "<PROMPT_OPTIMIZED></PROMPT_OPTIMIZED>",
        "<PROMPT_OPTIMIZED> \n </PROMPT_OPTIMIZED>",
    ],
    ids=["missing-tag", "empty-tag", "whitespace-only"],
)
def test_exhausted_refinement_never_scores_an_invalid_candidate(
    optimizer_components, reply
):
    optimizer, chat, evaluate, combine, _ = optimizer_components
    chat.return_value = {"content": reply}

    with pytest.raises(JiuWenBaseException) as exc:
        optimizer.do_optimize("Answer about {{topic}}.", [], [])

    assert (
        exc.value.error_code == StatusCode.PROMPT_OPTIMIZE_REFINE_INSTRUCTION_ERROR.code
    )
    assert chat.call_count == 6  # One critique, then five refinement attempts.
    combine.assert_not_called()
    evaluate.assert_not_called()


@pytest.mark.parametrize("invalid_attempts", [0, 4])
def test_valid_refinement_is_scored(optimizer_components, invalid_attempts):
    optimizer, chat, evaluate, combine, cancel = optimizer_components
    chat.side_effect = (
        [{"content": "Critique"}]
        + [{"content": "No refinement tags"}] * invalid_attempts
        + [{"content": "<PROMPT_OPTIMIZED>  Improved {{topic}}.\n</PROMPT_OPTIMIZED>"}]
    )
    dataset = [{"question": "Q", "label": "A"}]

    result = optimizer.do_optimize("Answer about {{topic}}.", [], dataset)

    assert result.prompt == "  Improved {{topic}}.\n"
    assert result.score == 0.75
    assert chat.call_count == 2 + invalid_attempts
    combine.assert_called_once_with(result.prompt, result.placeholder)
    evaluate.assert_called_once_with(result.prompt, dataset, cancel)
