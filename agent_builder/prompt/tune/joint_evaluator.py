# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""
agentBuilder chain Template evaluator
"""

import ast
import copy
import json
import random
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from agent_builder.common.logging.base import logger
from agent_builder.prompt.common.config import LLMModelInfo
from agent_builder.prompt.tune.base.constant import TuneConstant
from agent_builder.prompt.tune.base.utils import (
    OptimizeInfo,
    LLMModelProcess,
    OnStopException,
)
from agent_builder.adapter.exception_bridge import JiuWenBaseException


class JointEvaluatorWithRef:
    """Template evaluator,evaluate the responses of the two assistants
    as good or bad based on the reference answers.
    """

    def __init__(
        self,
        model_info: LLMModelInfo,
        assistant_info: LLMModelInfo,
        optimize_info: OptimizeInfo,
        prompt: str,
    ):
        self.model_info = model_info
        self.assistant_info = assistant_info
        self.model = LLMModelProcess(model_info)  # 比较，评估
        self.assistant_model = LLMModelProcess(assistant_info)  # 推理数据
        self.data_set = optimize_info.cases
        self.retry_times = optimize_info.retry_times
        self.llm_parallel = optimize_info.llm_parallel
        self.eval_mode = optimize_info.eval_mode
        self.access_answer_prompt = prompt

    @staticmethod
    def parse_json(input_string, max_length=10000):
        """parse json"""
        if len(input_string) > max_length:
            logger.warning("Parse failed due to length exceed limit")
            return None
        pattern = rf"```json(.{{1,{max_length}}}?)```"
        match = re.search(pattern, input_string, re.DOTALL)

        if match:
            json_string = match.group(1).strip()
            try:
                parsed_data = json.loads(json_string)
            except json.decoder.JSONDecodeError:
                logger.warning("Parse failed due to json decode error")
                return None
            return parsed_data

        logger.info("No valid JSON string found")
        return None

    @staticmethod
    def compare_text(label, predict):
        """text mode"""
        if not isinstance(label, str) or not isinstance(predict, str):
            return 0, "Failed to compare non-string result"
        result = label.strip() == predict.strip()
        return int(result), "Same" if result else "Different"

    @staticmethod
    def compare_json(label, predict):
        """json mode"""
        """ Compare prediction with labels based on the mode """
        try:
            label_dict = ast.literal_eval(label)

        except (ValueError, SyntaxError):
            return 0, "Error: label strings is not a valid dictionary format."

        try:
            predict_dict = ast.literal_eval(predict)
        except (ValueError, SyntaxError):
            return 0, "Error: prediction strings is not a valid dictionary format."

        if label_dict == predict_dict:
            return 1, "The dictionaries are identical."

        if label_dict.keys() != predict_dict.keys():
            missing_in_dict1 = set(predict_dict.keys()) - set(label_dict.keys())
            missing_in_dict2 = set(label_dict.keys()) - set(predict_dict.keys())
            return (
                0,
                f"Key mismatch. Missing in dict1: {missing_in_dict1}. Missing in dict2: {missing_in_dict2}.",
            )

        mismatched_values = {
            key: (label_dict[key], predict_dict[key])
            for key in label_dict
            if label_dict[key] != predict_dict.get(key)
        }

        if mismatched_values:
            return 0, f"Value mismatch at keys: {mismatched_values}"

        return 1, "Dictionaries have the same keys and values."

    def compare_llm(self, question, label, predict):
        """llm mode"""
        prompt_template = self._format_prompt_template(question, predict, label)

        try:
            response = self.handle_inference_retry(prompt_template, is_assistant=False)
        except JiuWenBaseException:
            return 0, "Failed to compare result due to LLM calling."

        if not response or "content" not in response:
            return 0, "Attribute error during LLM comparison"

        compare_res = self.parse_json(response["content"])
        if not compare_res:
            return 0, "Parse JSON error: Empty result"

        score = 1 if compare_res.get("result", False) is True else 0
        reason = compare_res.get("reason", "")

        return score, reason

    def evaluate_result(self, question, label, predict):
        """eval mode"""
        if self.eval_mode == TuneConstant.EVALUATION_METHOD_JSON:
            return self.compare_json(label, predict)
        if self.eval_mode == TuneConstant.EVALUATION_METHOD_TEXT:
            return self.compare_text(label, predict)
        return self.compare_llm(question, label, predict)

    def chat_completion(self, user_prompt, system_prompt=None, is_assistant=True):
        """get llm res"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        return (
            self.assistant_model.chat(messages)
            if is_assistant
            else self.model.chat(messages)
        )

    def handle_inference_retry(self, dialogue, prompt=None, is_assistant=True):
        """Handle retries on failed inference"""
        for i in range(self.retry_times):
            try:
                return self.chat_completion(
                    user_prompt=dialogue,
                    system_prompt=prompt,
                    is_assistant=is_assistant,
                )
            except JiuWenBaseException as e:
                logger.info(f"Inference failed at round {i}/{self.retry_times}: {e}")
                if i == self.retry_times - 1:
                    raise e
        return None

    def process_example(
        self, example_idx, prompt, example, cancel_event: threading.Event
    ):
        """process"""
        if cancel_event.is_set():
            raise OnStopException("Task stopped.")
        dialogue = example["question"]
        example_evaluation = copy.deepcopy(example)
        example_evaluation["order"] = example_idx
        # 示例移除tools字段，避免内存占用过高
        example_evaluation.pop(TuneConstant.TOOLS_KEY, None)

        if example.get(TuneConstant.VARIABLE_KEY, None):
            for var_name, var_content in example[TuneConstant.VARIABLE_KEY].items():
                prompt = prompt.replace(f"{{{{{var_name}}}}}", var_content)

        if TuneConstant.RAW_PROMPT_TAG in dialogue:
            full_dialogue = dialogue.replace(TuneConstant.RAW_PROMPT_TAG, prompt)
            response = self.handle_inference_retry(full_dialogue)
            dialogue = str(example.get(TuneConstant.VARIABLE_KEY, ""))
        else:
            if example.get(TuneConstant.TOOLS_KEY, None):
                system_prompt_prefix = (
                    TuneConstant.DEFAULT_SYSTEM_PROMPT_PREFIX.replace(
                        "{{APIS_DESCRIPTION}}",
                        str(example[TuneConstant.TOOLS_KEY])
                        if example[TuneConstant.TOOLS_KEY]
                        else "None",
                    )
                )
                response = self.handle_inference_retry(
                    dialogue, system_prompt_prefix + prompt
                )
            else:
                response = self.handle_inference_retry(dialogue, prompt)
        predict = response.get("content", "")
        if not predict:
            example_evaluation["score"] = 0
            example_evaluation["predict"] = None
            return example_evaluation, 0, "Parse json error"

        # Evaluate result based on mode
        res_compare, reason = self.evaluate_result(dialogue, example["label"], predict)
        example_evaluation["score"] = res_compare
        example_evaluation["predict"] = predict
        example_evaluation["reason"] = reason

        return example_evaluation, res_compare, reason

    def evaluate(self, prompt, dataset, cancel_event: threading.Event):
        """eval"""
        res_evaluation = []
        score_result = []
        num_thread = min(self.llm_parallel, len(dataset))

        with ThreadPoolExecutor(max_workers=num_thread) as executor:
            futures = [
                executor.submit(
                    self.process_example, example_idx, prompt, example, cancel_event
                )
                for example_idx, example in enumerate(dataset)
            ]

            for future in as_completed(futures):
                if cancel_event.is_set():
                    logger.info("Evaluation process cancelled.")
                    return None, None, None

                try:
                    example_evaluation, res_compare, _ = future.result()
                except Exception as e:
                    logger.error(f"Error processing future result: {e}")
                    raise e

                score_result.append(res_compare)
                res_evaluation.append(example_evaluation)

        accuracy = sum(score_result) / len(score_result) if score_result else 0
        res_evaluation = sorted(res_evaluation, key=lambda x: x["order"])
        res_eval = [item for item in res_evaluation if item.get("score", 0) == 0]
        res_eval = random.sample(
            res_eval,
            min(TuneConstant.DEFAULT_EVAL_MAX_EXAMPLE_SAMPLE_NUM, len(res_eval)),
        )

        return accuracy, res_eval, res_evaluation

    def _format_prompt_template(self, question, predict, label):
        """format_prompt_template"""
        prompt_template = self.access_answer_prompt.replace("{{question}}", question)
        prompt_template = prompt_template.replace("{{answer_match}}", predict)
        prompt_template = prompt_template.replace("{{actual_answer}}", label)

        return prompt_template
