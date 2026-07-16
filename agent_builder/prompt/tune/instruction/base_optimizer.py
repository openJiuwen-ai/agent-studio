# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""
partition optimizer
"""

import threading
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Tuple, Callable

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.common.logging.base import logger
from agent_builder.prompt.tune.base.constant import TuneConstant
from agent_builder.prompt.tune.base.utils import (
    LLMModelProcess,
    OnStopException,
    JointParams,
    load_prompt_pool_from_yaml,
)
from agent_builder.prompt.tune.joint_evaluator import JointEvaluatorWithRef
from agent_builder.adapter.exception_bridge import JiuWenBaseException
from pydantic import BaseModel, Field


class OptimizeOutput(BaseModel):
    prompt: Optional[str] = None
    placeholder: Optional[Any] = None
    score: Optional[float] = None
    error_cases: Optional[List] = Field(default=[])
    evaluations: Optional[List] = Field(default=[])
    examples: Optional[List] = Field(default=[])


class BasicOptimizer(ABC):
    def __init__(
        self,
        model: LLMModelProcess,
        stop_event: threading.Event,
        evaluator: JointEvaluatorWithRef = None,
        tools: Dict[str, Any] = None,
        user_compare_rule: str = "None",
    ):
        self._model = model
        self._prompt_pool = load_prompt_pool_from_yaml()
        self._stop_event = stop_event
        self._evaluator = evaluator
        self._tools = tools
        self._user_compare_rule = user_compare_rule

    @abstractmethod
    def do_optimize(
        self, prompt: str, bad_cases: List, dataset: List
    ) -> OptimizeOutput:
        """do partition optimization"""
        pass

    def _get_textual_gradient(
        self, prompt: str, bad_cases: List, external_knowledge: str
    ) -> Tuple[str, str]:
        """get textual gradient"""
        error_example_string = "".join(
            self._prompt_pool["quest_reason_ans_error"].format(
                question=example.get("question", "")
                if TuneConstant.RAW_PROMPT_TAG not in example.get("question", "")
                else str(example.get(TuneConstant.VARIABLE_KEY, "")),
                answer=example.get("label", ""),
                predict=example.get("predict", ""),
            )
            for example in bad_cases
        )

        if self._tools:
            system_prompt_prefix = TuneConstant.DEFAULT_SYSTEM_PROMPT_PREFIX.replace(
                "{{APIS_DESCRIPTION}}", str(self._tools) if self._tools else "None"
            )
            prompt = system_prompt_prefix + prompt
        else:
            prompt = prompt

        meta_critique_prompt = self._prompt_pool["meta_critique_template"].format(
            instruction=prompt,
            examples=error_example_string,
            external_knowledge=external_knowledge,
        )
        return self._chat_completion(meta_critique_prompt), error_example_string

    def _chat_completion(self, user_prompt, system_prompt=None):
        """
        Generates a chat response from user and optional system prompts
        """
        messages = (
            [{"role": "system", "content": system_prompt}] if system_prompt else []
        )
        messages.append({"role": "user", "content": user_prompt})
        for i in range(TuneConstant.DEFAULT_LLM_CHAT_RETRY_TIMES):
            if self._stop_event.is_set():
                raise OnStopException("Task stop")
            try:
                response = self._model.chat(messages)
                if not response or response.get("content") is None:
                    raise JiuWenBaseException(
                        StatusCode.LLM_FALSE_RESULT_ERROR.code,
                        StatusCode.LLM_FALSE_RESULT_ERROR.errmsg.format(
                            error_msg="call llm service failed."
                        ),
                    )
                return response.get("content")

            except (KeyError, AttributeError, TypeError, JiuWenBaseException) as e:
                logger.info(
                    f"Inference failed at round {i}/{TuneConstant.DEFAULT_LLM_CHAT_RETRY_TIMES}: {str(e)}"
                )
                if i == TuneConstant.DEFAULT_LLM_CHAT_RETRY_TIMES - 1:
                    raise e
            except Exception as e:
                logger.info(
                    f"Inference failed at round {i}/{TuneConstant.DEFAULT_LLM_CHAT_RETRY_TIMES}: {str(e)}"
                )
                if i == TuneConstant.DEFAULT_LLM_CHAT_RETRY_TIMES - 1:
                    raise e
        return None


class OptimizeAlgoConfig(BaseModel):
    params: JointParams
    model: LLMModelProcess
    stop_event: threading.Event
    evaluator: JointEvaluatorWithRef = None
    tools: Optional[list[dict] | str] = None
    user_compare_rule: str = "None"
    prompt_combine_func: Callable

    class Config:
        arbitrary_types_allowed = True
