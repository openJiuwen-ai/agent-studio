# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""
agentBuilder chain Template evaluator
"""

import copy
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.common.logging.base import logger
from agent_builder.prompt.common.config import LLMModelInfo
from agent_builder.prompt.mmapo.VQA_core import VQA
from agent_builder.prompt.mmapo.prompt import ANSWER_CHECK_PROMPT_MM
from agent_builder.prompt.mmapo.utils import (
    ProblemExample,
    chat_completion,
    WORKERS_NUM,
)
from agent_builder.prompt.tune.base.utils import (
    OptimizeInfo,
    LLMModelProcess,
    OnStopException,
    parse_json,
)
from agent_builder.adapter.exception_bridge import JiuWenBaseException

MAX_SCORE = 10
MAX_RETRY = 10


class ApoEvaluatorWithRef:
    """Template evaluator,evaluate the responses of the two assistants
    as good or bad based on the reference answers.
    """

    def __init__(
        self,
        model_info: LLMModelInfo,
        assistant_info: LLMModelInfo,
        optimize_info: OptimizeInfo,
        cancel_event: threading.Event,
    ):
        self.model_info = model_info
        self.assistant_info = assistant_info
        self.optimized_model = LLMModelProcess(model_info)  # 比较，评估
        self.assistant_model = LLMModelProcess(assistant_info)  # 推理数据
        self.data_set = optimize_info.cases
        self.retry_times = optimize_info.retry_times
        self.llm_parallel = optimize_info.llm_parallel
        self.eval_mode = optimize_info.eval_mode
        self.stop_event = cancel_event
        self.vqa = VQA()

    def eval_candidates(
        self, eval_dataset: List[ProblemExample], candidates: List[str]
    ) -> (float, str, List[dict], List[dict]):
        """eval_candidates"""
        if not candidates:
            logger.info("candidates is empty")
            return None

        results = []

        with ThreadPoolExecutor(
            max_workers=min(WORKERS_NUM, len(candidates))
        ) as executor:
            futures = {
                executor.submit(self.evaluate_one_prompt, prompt, eval_dataset): prompt
                for prompt in candidates
            }
            for future in as_completed(futures):
                result = future.result()
                results.append(result)

        if not results:
            logger.warning("No valid results returned from evaluation. Returning None.")
            return None
        return results

    def evaluate_one_example(self, evaluation_dict: dict) -> tuple[float, str]:
        """Compare prediction with labels based on the mode"""
        access_answer_prompt = ANSWER_CHECK_PROMPT_MM.replace(
            "{{question}}", evaluation_dict.get("question")
        )
        access_answer_prompt = access_answer_prompt.replace(
            "{{answer}}", evaluation_dict.get("label")
        )
        access_answer_prompt = access_answer_prompt.replace(
            "{{predict}}", evaluation_dict.get("predict")
        )

        try:
            messages = self.vqa.get_message_from_raw_prompt(
                access_answer_prompt, evaluation_dict, evaluation_dict["image"]
            )
            compare_res = {}
            for _ in range(MAX_RETRY):
                raw_responses = chat_completion(messages, self.assistant_model)
                compare_res = parse_json(raw_responses)
                if compare_res:
                    break
                logger.warning(
                    "JSON parse error: consider using better assistant model"
                )
            reason = compare_res.get("reason", "")
            score = float(compare_res.get("score", "0"))

            return score, reason

        except JiuWenBaseException as e:
            raise JiuWenBaseException(
                error_code=StatusCode.PROMPT_STORAGE_TYPE_NOT_MATCH_ERROR.code,
                message=StatusCode.PROMPT_STORAGE_TYPE_NOT_MATCH_ERROR.errmsg.format(
                    error_msg=f"Failed to get messages:{str(e)}"
                ),
            ) from e

    def evaluate_one_prompt(
        self,
        new_prompt: str,
        test_examples: List[ProblemExample],
    ) -> (float, str, List[dict], List[dict]):
        """evaluate function"""
        current_batch = []
        count_all = 0
        count_success = 0

        with ThreadPoolExecutor(
            max_workers=min(WORKERS_NUM, len(test_examples))
        ) as executor:
            futures = [
                executor.submit(
                    self.process_example,
                    example_index,
                    example,
                    new_prompt,
                    self.stop_event,
                )
                for example_index, example in enumerate(test_examples)
            ]

            for future in as_completed(futures):
                if self.stop_event.is_set():
                    raise OnStopException("The process has been stopped.")
                example_evaluation = future.result()
                current_batch.append(example_evaluation)
                result = example_evaluation.get("score", 0)
                count_success += result / MAX_SCORE
                count_all += 1

        accuracy = count_success / count_all if count_all > 0 else 0.0
        error_data = [
            item for item in current_batch if item.get("score", 1) < MAX_SCORE
        ]

        return accuracy, new_prompt, current_batch, error_data

    def process_example(
        self,
        example_index: int,
        examples: ProblemExample,
        prompt: str,
        cancel_event: threading.Event,
    ):
        """process_example"""
        if cancel_event.is_set():
            raise OnStopException("The process has been stopped.")
        evaluation_dict = {}
        image_path_list = self.vqa.get_all_image_paths(examples.image)
        if examples.image and not image_path_list:
            evaluation_dict["image"] = examples.image
        else:
            evaluation_dict["image"] = [str(p) for p in image_path_list]
        evaluation_dict["label"] = examples.answer
        evaluation_dict["variable"] = examples.variable_dict
        evaluation_dict["order"] = example_index
        evaluation_dict["question"] = ""

        filled_prompt_with_text = self.vqa.generate_filled_prompt(
            prompt,
            examples.variable_dict,
            examples.variable_type_dict,
        )
        messages = self.vqa.get_message_from_filled_prompt(
            filled_prompt_with_text,
            examples.variable_dict,
            examples.variable_type_dict,
            image_path_list,
        )
        predict = chat_completion(messages, self.assistant_model)
        evaluation_dict["predict"] = predict

        if not predict:
            evaluation_dict["score"] = 0
            evaluation_dict["reason"] = "LLM inference failed"
        else:
            evaluation_dict_new = copy.deepcopy(evaluation_dict)
            evaluation_dict_new["variable_dict"] = examples.variable_dict
            evaluation_dict_new["variable_type_dict"] = examples.variable_type_dict
            evaluation_dict_new["question"] = filled_prompt_with_text
            result, detail = self.evaluate_one_example(evaluation_dict_new)
            evaluation_dict["score"] = result
            evaluation_dict["reason"] = detail

        return evaluation_dict
