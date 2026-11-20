# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Keep tool descriptions in refinement requests with and without placeholders."""

import threading
from unittest.mock import Mock

import pytest

from agent_builder.prompt.tune.base.utils import JointParams, LLMModelProcess
from agent_builder.prompt.tune.instruction.base_optimizer import OptimizeAlgoConfig
from agent_builder.prompt.tune.instruction.instruction_optimizer import (
    get_selected_algorithm,
)
from agent_builder.prompt.tune.joint_evaluator import JointEvaluatorWithRef


@pytest.mark.parametrize("algorithm", ["greedy", "beamsearch"])
@pytest.mark.parametrize("placeholder_mode", ["none", "fixed", "optimized"])
@pytest.mark.parametrize(
    "tools",
    [
        [
            {
                "name": "lookup_weather",
                "description": "Look up weather / 天气",
                "parameters": {"city": "string"},
            }
        ],
        "lookup_weather(city): Look up the current weather.",
        [],
        None,
    ],
    ids=["structured-tools", "text-tools", "empty-tools", "no-tools"],
)
def test_refinement_requests_include_tools(algorithm, placeholder_mode, tools):
    placeholders = []
    if placeholder_mode != "none":
        placeholders = [
            {
                "name": "task",
                "content": "Original task",
                "need_optimize": placeholder_mode == "optimized",
            }
        ]
    params = JointParams(
        placeholder=placeholders,
        opt_schema=["task"] if placeholder_mode == "optimized" else [],
    )
    model = object.__new__(LLMModelProcess)
    model.chat = Mock(
        side_effect=[
            {"content": "Use the available weather tool."},
            {"content": "<PROMPT_OPTIMIZED>Improved {{task}}</PROMPT_OPTIMIZED>"},
            {
                "content": "<PLACEHOLDER_OPTIMIZED><task>Refined task</task></PLACEHOLDER_OPTIMIZED>"
            },
        ]
    )
    evaluator = object.__new__(JointEvaluatorWithRef)
    evaluator.evaluate = Mock(
        side_effect=lambda prompt, dataset, event: (
            float(prompt.startswith("Improved")),
            [],
            [],
        )
    )
    optimizer = get_selected_algorithm(
        algorithm,
        OptimizeAlgoConfig(
            params=params,
            model=model,
            stop_event=threading.Event(),
            evaluator=evaluator,
            tools=tools,
            prompt_combine_func=lambda prompt, placeholder: prompt,
        ),
    )
    dataset = [{"question": "Weather in Paris?", "label": "Call lookup_weather"}]
    bad_cases = [dict(dataset[0], predict="Unknown")]

    result = optimizer.do_optimize("Answer {{task}}", bad_cases, dataset)

    expected_tools = str(tools) if tools else "None"
    refinement_calls = model.chat.call_args_list[1:]
    assert len(refinement_calls) == (2 if placeholder_mode == "optimized" else 1)
    for call in refinement_calls:
        messages = call.args[0]
        user_prompt = messages[-1].get("content")
        tool_section = (
            user_prompt.split("<tools_description>", 1)[1]
            .split("</tools_description>", 1)[0]
            .strip()
        )
        assert tool_section == expected_tools
        assert "{{API_TOOLS_DESCRIPTION}}" not in user_prompt
    assert result.prompt == "Improved {{task}}"
    assert result.score == 1.0
    if placeholder_mode == "optimized":
        assert result.placeholder[0].get("content") == "Refined task"
    elif placeholder_mode == "fixed":
        assert result.placeholder == placeholders
