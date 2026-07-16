# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""
Joint optimizer
"""

import copy
import random
import re
import threading
from dataclasses import dataclass
from typing import List, Dict, Optional, Any

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.common.logging.base import logger
from agent_builder.common.status import TaskStatus
from agent_builder.prompt.common.config import LLMModelInfo
from agent_builder.prompt.tune.base.case import CaseManager
from agent_builder.prompt.tune.base.constant import TuneConstant
from agent_builder.prompt.tune.base.context import History
from agent_builder.prompt.tune.base.context_manager import ContextManager
from agent_builder.prompt.tune.base.utils import (
    LLMModelProcess,
    OptimizeInfo,
    OnStopException,
    check_not_none_with_alias,
    JointParams,
    placeholder_to_dict,
    calc_run_time,
    load_prompt_pool_from_yaml,
    find_schema,
    parse_json,
)
from agent_builder.prompt.tune.instruction.base_optimizer import (
    BasicOptimizer,
    OptimizeAlgoConfig,
)
from agent_builder.prompt.tune.instruction.instruction_optimizer import (
    get_selected_algorithm,
)
from agent_builder.prompt.tune.joint_evaluator import JointEvaluatorWithRef
from agent_builder.adapter.exception_bridge import JiuWenBaseException
from agent_builder.adapter.task_info import TaskInfo

CANCEL_EVENT = "cancel_event"


@dataclass
class DatasetSpecificProcessing:
    QUESTION_LITERAL = "question"
    ANSWER_LITERAL = "answer"
    QUESTION_KEY = "[query]:"
    ANSWER_KEY = "[assistant answer]:"
    TEXT_DELIMITER_PATTERN = r"(?s)(?<=<START>)(.*?)(?=<END>)"
    INVALID_ANS = "[invalid]"


class JointOptimizer:
    """
    A prompt self-optimization class based on text gradients.
    The main purpose of this class is to evaluate and iteratively optimize prompts
    based on user-provided test cases (cases).
    Currently, two primary optimization strategies are supported: greedy optimization and beam search optimization.
    """

    def __init__(self):
        self.model = None
        self.assistant_model = None
        self.evaluator = None
        self.dataset = None
        self.params = JointParams()
        self.iter_num = 0
        self.acc_base = 0
        self.sampled_incorrect_data = []
        self.variable = []
        self.prompt_pool = load_prompt_pool_from_yaml()
        self.selected_optimizer: Optional[BasicOptimizer] = None

    @staticmethod
    def get_opt_schema(placeholder):
        """
        Returns a list of placeholders requiring optimization
        """
        try:
            if not placeholder:
                return None
            return [p["name"] for p in placeholder if p.get("need_optimize")]
        except (TypeError, KeyError) as e:
            logger.info(f"Error processing placeholder: {e}")
            return None

    @staticmethod
    def parse_string_meta(content) -> Optional[str]:
        """
        Extracts and returns meta content between <PROMPT_OPTIMIZED> tags
        """
        prompt_meta_pattern = (
            r"<PROMPT_OPTIMIZED>((?:(?!<PROMPT_OPTIMIZED>).)*?)</PROMPT_OPTIMIZED>"
        )
        prompt_meta_match = re.search(prompt_meta_pattern, content, re.DOTALL)

        if not prompt_meta_match:
            return None

        prompt_meta_content = prompt_meta_match.group(1)
        return prompt_meta_content.replace("<prompt_base>", "").replace(
            "</prompt_base>", ""
        )

    @staticmethod
    def parse_string_schema(content, schemas):
        """
        Extracts placeholders and returns them as a list of dictionaries
        """

        placeholder_match = find_schema(
            content, "<PLACEHOLDER_OPTIMIZED>", "</PLACEHOLDER_OPTIMIZED>"
        )
        if not placeholder_match:
            return None
        matches = []
        for schema in schemas:
            scheme_content = find_schema(
                placeholder_match, "<{}>".format(schema), "</{}>".format(schema)
            )
            if scheme_content is None:
                logger.info(f"Error processing placeholder: {schema}")
            else:
                matches.append((schema, scheme_content))

        return [
            {"name": tag.strip(), "content": content.strip()}
            for tag, content in matches
        ]

    @staticmethod
    def fill_prompt(instruction, placeholder):
        """
        Replaces placeholders in the instruction with provided content
        """
        if not placeholder:
            return instruction

        for p in placeholder:
            name = p.get("name")
            content = p.get("content")
            if name and content:
                instruction = instruction.replace(f"{{{{{name}}}}}", content)

        return instruction

    @staticmethod
    def prepare_critique_prompt(
        template, instruction, placeholder_contents, error_cases, reflections
    ):
        """
        Generates a critique prompt by filling in the template with provided details
        """
        prompt = template.replace("{{PROMPT_META_TEMPLATE}}", instruction)
        prompt = prompt.replace("{{PLACEHOLDER_CONTENTS}}", placeholder_contents)
        prompt = prompt.replace("{{ERROR_CASES}}", error_cases)
        prompt = prompt.replace("{{REFLECTIONS_ON_ERROR_CASES}}", reflections)
        return prompt

    @staticmethod
    def extract_examples_frm_response(response_with_examples: str) -> List:
        """
        Extracts synthetic examples from a response containing question-answer pairs
        """
        synthetic_examples = []

        question_pattern = re.compile(
            re.escape(DatasetSpecificProcessing.QUESTION_KEY)
            + r"(.*?)"
            + re.escape(DatasetSpecificProcessing.ANSWER_KEY)
            + r"(.*)",
            re.DOTALL,
        )

        for text in re.findall(
            DatasetSpecificProcessing.TEXT_DELIMITER_PATTERN, response_with_examples
        ):
            match = question_pattern.search(text.strip())
            if match:
                question = match.group(1).strip()
                answer_with_reason = match.group(2).strip()
                synthetic_examples.append(
                    {"question": question, "label": answer_with_reason}
                )

        return synthetic_examples

    @staticmethod
    def validate_schema(prompt, schema_list):
        """校验 schema_list 中的元素名称是否都存在于 prompt 中，并确保它们与 prompt 中的双花括号一一匹配。"""
        prompt_placeholders = re.findall(r"\{\{([\w_]+)\}\}", prompt)
        schema_names = [item["name"] for item in schema_list]
        # 校验 schema_list 中的元素字段
        for item in schema_list:
            if not item.get("name"):
                raise JiuWenBaseException(
                    error_code=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.code,
                    message=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.errmsg.format(
                        error_msg="Placeholder item 'name' cannot be empty."
                    ),
                )
            if not item.get("content"):
                raise JiuWenBaseException(
                    error_code=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.code,
                    message=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.errmsg.format(
                        error_msg="Placeholder item 'content' cannot be empty."
                    ),
                )
            if "need_optimize" not in item:
                raise JiuWenBaseException(
                    error_code=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.code,
                    message=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.errmsg.format(
                        error_msg="Placeholder item 'need_optimize' cannot be empty."
                    ),
                )

            if not isinstance(item["name"], str):
                raise JiuWenBaseException(
                    error_code=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.code,
                    message=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.errmsg.format(
                        error_msg="Placeholder item 'name' must be a string."
                    ),
                )
            if not isinstance(item["content"], str):
                raise JiuWenBaseException(
                    error_code=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.code,
                    message=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.errmsg.format(
                        error_msg="Placeholder item 'content' must be a string."
                    ),
                )
            if not isinstance(item["need_optimize"], bool):
                raise JiuWenBaseException(
                    error_code=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.code,
                    message=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.errmsg.format(
                        error_msg="Placeholder item 'need_optimize' must be a boolean."
                    ),
                )

        missing_names = [
            name for name in schema_names if name not in prompt_placeholders
        ]
        if missing_names:
            raise JiuWenBaseException(
                error_code=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.code,
                message=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.errmsg.format(
                    error_msg="One or more placeholders in schema are missing from the prompt."
                ),
            )

        logger.info("Schema validation successful.")

    @staticmethod
    def _check_event(progress_info: Dict[str, Any]) -> bool:
        """Check optimization status"""
        task_id = progress_info["id"]
        if (
            progress_info
            and progress_info[CANCEL_EVENT]
            and progress_info[CANCEL_EVENT].is_set()
        ):
            raise OnStopException(f"Task {task_id} stopped")
        return True

    def chat_completion(self, user_prompt, system_prompt=None, is_assistant=False):
        """
        Generates a chat response from user and optional system prompts
        """
        messages = (
            [{"role": "system", "content": system_prompt}] if system_prompt else []
        )
        messages.append({"role": "user", "content": user_prompt})
        for i in range(TuneConstant.DEFAULT_LLM_CHAT_RETRY_TIMES):
            try:
                response = (
                    self.assistant_model.chat(messages)
                    if is_assistant
                    else self.model.chat(messages)
                )
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
                    f"Inference failed at round {i}/{TuneConstant.DEFAULT_LLM_CHAT_RETRY_TIMES}: "
                    f"{type(e).__name__}"
                )
                if i == TuneConstant.DEFAULT_LLM_CHAT_RETRY_TIMES - 1:
                    raise e
        return None

    def resample_examples(self, sampled_incorrect_data):
        """re-sample examples from dataset"""
        dataset = copy.deepcopy(self.dataset)
        min_len = self.params.example_num + self.params.cot_example_num
        if len(sampled_incorrect_data) >= min_len:
            return sampled_incorrect_data

        if len(dataset) <= min_len:
            return dataset

        num_to_add = min_len - len(sampled_incorrect_data)
        unique_data = []
        query_set = set()
        for data in sampled_incorrect_data:
            key = (
                data["question"]
                if not self.variable
                else str(data[TuneConstant.VARIABLE_KEY])
            )
            if key not in query_set:
                query_set.add(key)
                unique_data.append(data)

        remaining_data = [data for data in dataset if data not in unique_data]

        sampled_data = random.sample(remaining_data, num_to_add)

        return sampled_incorrect_data + sampled_data

    def eval(self, prompt, progress_info: Dict[str, Any]):
        """evaluation"""
        try:
            acc, sampled_incorrect_data, evaluations = self.evaluator.evaluate(
                prompt, self.dataset, progress_info[CANCEL_EVENT]
            )
        except JiuWenBaseException as e:
            raise e
        if (
            not self._check_event(progress_info)
            or acc is None
            or sampled_incorrect_data is None
        ):
            return None, None, None
        sampled_data = self.resample_examples(sampled_incorrect_data)
        progress_info["cur_accuracy"].append(acc)
        return acc, sampled_data, evaluations

    def params_init(self, optimize_info, raw_templates, progress_info: Dict[str, Any]):
        """params init"""
        self.params.num_iter = optimize_info.num_iter
        self.params.example_num = optimize_info.example_num
        self.params.cot_example_num = optimize_info.cot_example_num
        self.params.placeholder = copy.deepcopy(optimize_info.placeholder)
        self.params.original_placeholder = optimize_info.placeholder
        self.params.base_instruction = raw_templates[0]
        self.params.opt_schema = self.get_opt_schema(self.params.placeholder)
        self.params.filled_instruction = self.fill_prompt(
            raw_templates[0], optimize_info.placeholder
        )
        self.params.external_knowledge = optimize_info.external_knowledge
        if optimize_info.early_stop_score is not None:
            self.params.early_stop_score = optimize_info.early_stop_score
        self.save_state(progress_info, force_save=True)
        # 避免大模型调用失败直接返回，需要捕获异常延迟抛出，确保状态被保存
        try:
            self.params.task_description = self.get_task_description()
            self.params.answer_format = self.get_answer_format()
        except JiuWenBaseException as e:
            raise e

    def get_task_description(self):
        """get task description"""
        prompt = self.prompt_pool["get_task_description"].format(
            instruction=self.params.base_instruction
        )
        return self.chat_completion(prompt)

    def get_answer_format(self):
        """get answer format"""
        prompt = self.prompt_pool["get_answer_format"].format(
            instruction=self.params.base_instruction
        )
        return self.chat_completion(prompt)

    def prompt_combine(self, instruction, example_string=None, example_string_cot=None):
        """
        Combines instruction and optional example strings into a single prompt
        """
        prompt_parts = [
            instruction,
            f"\n## 示例\n{example_string}" if example_string else "",
            f"\n## 包含思维链示例\n{example_string_cot}" if example_string_cot else "",
            f"\n{self.params.answer_format}" if self.params.answer_format else "",
        ]

        return "".join(filter(None, prompt_parts))

    def placeholder_update(self, new_placeholders: List, placeholders_to_update: List):
        """
        Updates placeholders based on schema update results
        """
        if not new_placeholders or not self.params.opt_schema:
            return
        for update_item in new_placeholders:
            name = update_item.get("name")
            content = update_item.get("content")

            if not name or not content or name not in self.params.opt_schema:
                continue

            for i, base_item in enumerate(placeholders_to_update):
                if name == base_item.get("name", ""):
                    placeholders_to_update[i]["content"] = content
                    break

    def generate_best_examples(self, progress_info: Dict[str, Any]) -> List:
        """
        Generates optimized examples based on critique and error data for a task
        """
        if not self._check_event(progress_info):
            return []

        try:
            example_string = self._prepare_example_strings(self.params.cot_examples)

            # 使用列表推导和 join 提高效率
            example_string_error = "".join(
                self.prompt_pool["quest_reason_ans_error"].format(
                    question=example.get("question", ""),
                    answer=example.get("label", ""),
                    predict=example.get("predict", ""),
                )
                for example in self.sampled_incorrect_data
            )

            # 生成 critique 提示
            few_shot_critique_prompt = self.prompt_pool[
                "examples_critique_template_error"
            ].format(
                examples=example_string,
                task_description=self.params.filled_instruction,
                num_examples=self.params.cot_example_num,
                error_examples=example_string_error,
                external_knowledge=self.params.external_knowledge,
            )

            # 获取模型反馈的 critique
            critique = self.chat_completion(few_shot_critique_prompt)

            # 生成优化提示
            few_shot_opt_prompt = self.prompt_pool[
                "examples_optimization_template"
            ].format(
                examples=example_string,
                critique=critique,
                task_description=self.params.filled_instruction,
                num_examples=self.params.cot_example_num,
            )

            # 获取模型返回的 synthetic examples
            response = self.chat_completion(few_shot_opt_prompt)
            return self.extract_examples_frm_response(response)

        except (KeyError, TypeError, AttributeError) as e:
            # 捕获异常，处理数据结构不匹配或访问错误的情况
            logger.info(f"Error generating best examples: {e}")
            return []

    def select_best_examples(self, progress_info: Dict[str, Any]) -> List:
        """
        Selects the best examples for a task based on error data and ground truth
        """
        if not self._check_event(progress_info):
            return []

        try:
            example_string_error = "\n".join(
                self.prompt_pool["quest_reason_ans"].format(
                    question=example.get("question", "")
                    if not self.variable
                    else example.get("variable", ""),
                    answer=example.get("label", ""),
                )
                for example in self.sampled_incorrect_data
            )

            gt_example = random.sample(self.dataset, 1)[0]
            gt_example_string = self.prompt_pool["quest_reason_ans"].format(
                question=gt_example.get("question", "")
                if not self.variable
                else gt_example.get("variable", ""),
                answer=gt_example.get("label", ""),
            )

            # 构建 few-shot 优化提示
            few_shot_opt_prompt = self.prompt_pool["examples_select_template"].format(
                gt_example=gt_example_string,
                task_description=self.params.task_description,
                num_examples=self.params.example_num,
                error_examples=example_string_error,
            )

            # 获取模型生成的 synthetic examples
            response = self.chat_completion(few_shot_opt_prompt)
            return self.extract_examples_frm_response(response)

        except (KeyError, TypeError, AttributeError, IndexError) as e:
            logger.info(f"Error selecting best examples: {e}")
            return []

    def generate_reasoning(self, question: str, answer: str) -> str:
        """
        Generates reasoning for a given question and answer based on the prompt template
        """
        try:
            prompt_template = self.prompt_pool["generate_reason_template"].format(
                task_description=self.params.task_description,
                instruction=self.params.base_instruction,
                question=question,
                answer=answer,
            )

            response = self.chat_completion(user_prompt=prompt_template)
            return response

        except (KeyError, TypeError, AttributeError):
            logger.info("Error occur when generating reasoning")
            return ""

    def evaluate_baseline(self, progress_info: Dict[str, Any]) -> History:
        """
        Evaluate the baseline performance using the base prompt and log the results.
        """
        if not self._check_event(progress_info):
            raise JiuWenBaseException(
                StatusCode.PROMPT_OPTIMIZE_EVALUATE_ERROR.code,
                StatusCode.PROMPT_OPTIMIZE_EVALUATE_ERROR.errmsg.format(
                    error_msg="evaluation baseline stopped."
                ),
            )

        base_prompt = self.fill_prompt(
            self.params.base_instruction, self.params.placeholder
        )
        self.acc_base, self.sampled_incorrect_data, evaluations = self.eval(
            base_prompt, progress_info
        )

        if self.acc_base is None or self.sampled_incorrect_data is None:
            raise JiuWenBaseException(
                StatusCode.PROMPT_OPTIMIZE_EVALUATE_ERROR.code,
                StatusCode.PROMPT_OPTIMIZE_EVALUATE_ERROR.errmsg.format(
                    error_msg="evaluation baseline failed"
                ),
            )

        return History(
            optimized_prompt=base_prompt,
            iteration_round=0,
            success_rate=self.acc_base,
            evaluations=evaluations,
        )

    def sample_examples(self, num_examples):
        """
        Sample a specified number of examples from a dataset, giving priority to erroneous examples.
        """
        dataset = copy.deepcopy(self.dataset)
        error_cases = self.sampled_incorrect_data
        if num_examples >= len(dataset):
            return [
                {
                    TuneConstant.QUESTION_KEY: data.get(TuneConstant.QUESTION_KEY, "")
                    if not self.variable
                    else str(data.get(TuneConstant.VARIABLE_KEY, "")),
                    TuneConstant.LABEL_KEY: data.get(TuneConstant.LABEL_KEY, ""),
                }
                for data in dataset
            ]  # 返回整个数据集的副本

        sampled_examples = []

        if error_cases:
            # 优先从错误用例中采样
            num_error_examples = min(num_examples, len(error_cases))
            sampled_examples.extend(random.sample(error_cases, num_error_examples))

            # 如果需要更多示例，从数据集中随机采样
            if len(sampled_examples) < num_examples:
                remaining_examples = num_examples - len(sampled_examples)
                remaining_dataset = [
                    item for item in dataset if item not in sampled_examples
                ]  # 确保不重复采样
                sampled_examples.extend(
                    random.sample(remaining_dataset, remaining_examples)
                )
        else:
            # 如果没有错误用例，直接从数据集中采样
            sampled_examples.extend(random.sample(dataset, num_examples))

        return [
            {
                TuneConstant.QUESTION_KEY: data.get(TuneConstant.QUESTION_KEY, "")
                if not self.variable
                else str(data.get(TuneConstant.VARIABLE_KEY, "")),
                TuneConstant.LABEL_KEY: data.get(TuneConstant.LABEL_KEY, ""),
            }
            for data in sampled_examples
        ]

    def prepare_few_shot_examples(self):
        """
        Prepare few-shot examples for CoT and No-CoT based on the specified counts.
        """
        example_num = self.params.example_num
        cot_example_num = self.params.cot_example_num

        self.params.examples = self.sample_examples(example_num)
        self.params.cot_examples = self.sample_examples(cot_example_num)
        self._generate_reasoning()

    def select_sample_set(self, count):
        """
        Select a sample set based on the available data size.
        """
        return (
            self.sampled_incorrect_data
            if len(self.sampled_incorrect_data) >= count
            else self.dataset
        )

    def do_optimize(
        self,
        task_info: TaskInfo,
        raw_templates: List[str],
        optimize_info: OptimizeInfo,
        model_info: LLMModelInfo,
        assistant_info: LLMModelInfo = None,
    ):
        """do optimize"""
        optimize_info.example_num_assign()
        check_not_none_with_alias(task_info, "task_info")
        assistant_info = model_info if assistant_info is None else assistant_info
        progress_info = dict(
            id=task_info.task_id,
            name=task_info.name,
            desc=task_info.desc,
            create_time=task_info.create_time,
            run_time=0,
            raw_templates=raw_templates,
            optimize_info=optimize_info,
            model_info=model_info,
            assistant_info=assistant_info,
            progress_rate=0.0,
            templates=raw_templates,
            scores=[0.0] * len(raw_templates),
            error_msg="",
            cancel_event=threading.Event(),
            status=TaskStatus.TASK_RUNNING,
            cur_accuracy=[],
            task_iter=0,
            history=[],
        )
        ContextManager().set(task_info.task_id, progress_info)
        try:
            self.model = LLMModelProcess(model_info)
            self.assistant_model = LLMModelProcess(assistant_info)
            if (
                optimize_info.user_compare_options
                == TuneConstant.LLM_EVALUATION_TYPE_SUBJECTIVE
            ):
                result_compare_prompt = self.prompt_pool["subjective_access_answer"]
                logger.info(
                    f"user_compare_options: {optimize_info.user_compare_options}"
                )
            else:
                result_compare_prompt = self.prompt_pool["access_answer"]
                logger.info(
                    f"user_compare_options: {TuneConstant.LLM_EVALUATION_TYPE_OBJECTIVE}"
                )
            result_compare_prompt = result_compare_prompt.replace(
                "{{user_compare_rules}}", optimize_info.user_compare_rules
            )
            logger.info(f"user_compare_rules: {optimize_info.user_compare_rules}")
            self.evaluator = JointEvaluatorWithRef(
                model_info, assistant_info, optimize_info, result_compare_prompt
            )

            optimize_algo_config = OptimizeAlgoConfig(
                params=self.params,
                model=self.model,
                stop_event=progress_info.get("cancel_event"),
                evaluator=self.evaluator,
                tools=progress_info.get("optimize_info").tools,
                user_compare_rule=optimize_info.user_compare_rules,
                prompt_combine_func=self._get_full_prompt,
            )
            self.selected_optimizer = get_selected_algorithm(
                optimize_info.optimize_algo, optimize_algo_config
            )
            self.dataset = CaseManager.validate_with_convert(
                [case.model_dump() for case in optimize_info.cases],
                CaseManager.convert,
                default_tools=optimize_info.tools,
            )
            self.variable = self._get_variable_from_dataset(
                self.dataset, raw_templates[0]
            )
            self.validate_schema(raw_templates[0], optimize_info.placeholder)
            self.params_init(optimize_info, raw_templates, progress_info)
            logger.info(f"external knowledge: {self.params.external_knowledge}")
            baseline_history = self.evaluate_baseline(progress_info)

            self.prepare_few_shot_examples()
            if baseline_history.success_rate >= self.params.early_stop_score:
                logger.info(
                    "Early stopping activated due to target accuracy being reached."
                )
                progress_info[TaskStatus.TASK_STATUS] = TaskStatus.TASK_FINISHED
                progress_info["run_time"] = calc_run_time(progress_info["create_time"])
                self.save_state(progress_info, baseline_history)
                if ContextManager().has_store():
                    ContextManager().delete(progress_info["id"])
                logger.info(f"Joint optimize task finished: {progress_info['id']}")
                return
            self.save_state(progress_info, baseline_history)
            self._refine_task_iteratively(progress_info)
        except OnStopException:
            ContextManager().set_context_attr(
                task_info.task_id, TaskStatus.TASK_STATUS, TaskStatus.TASK_STOPPED
            )
            if ContextManager().has_store():
                ContextManager().delete(task_info.task_id)
            logger.info(f"Joint optimize task-{task_info.task_id} stopped.")
            return
        except Exception as e:
            import traceback
            logger.error(f"failed to do optimize by error: {e}\n{traceback.format_exc()}")
            progress_info[TaskStatus.TASK_STATUS] = TaskStatus.TASK_FAILED
            progress_info["run_time"] = calc_run_time(progress_info["create_time"])
            check_point = (
                ContextManager().get_checkpoint(task_info.task_id) or progress_info
            )
            if check_point:
                check_point["error_msg"] = (
                    f"Joint optimize failed, {str(e)}"
                    if isinstance(e, JiuWenBaseException)
                    else "Joint optimize failed, other reasons"
                )
                check_point[TaskStatus.TASK_STATUS] = TaskStatus.TASK_FAILED
                check_point["run_time"] = calc_run_time(check_point["create_time"])
                if ContextManager().has_store():
                    try:
                        ContextManager().store_context(task_info.task_id, check_point)
                    except Exception as store_err:
                        import traceback as tb
                        logger.error(
                            f"store context failed: {store_err}\n{tb.format_exc()}"
                        )
                    ContextManager().delete(task_info.task_id)
                else:
                    ContextManager().set_checkpoint(task_info.task_id, check_point)

    def continue_optimize(self, task_id: str):
        """continue optimize"""
        progress_info = ContextManager().get_checkpoint(task_id)
        progress_info["id"] = task_id
        ContextManager().set(task_id, progress_info)
        new_run_time = calc_run_time(progress_info.get("create_time"))
        ContextManager().set_context_attr(
            task_id, "run_time", new_run_time, attr_name_alias="time_cost"
        )
        ContextManager().set_context_attr(
            task_id, TaskStatus.TASK_STATUS, TaskStatus.TASK_RUNNING
        )
        check_not_none_with_alias(progress_info, "progress_info")
        raw_templates = progress_info["raw_templates"]
        optimize_info = progress_info["optimize_info"]
        model_info = progress_info["model_info"]
        assistant_info = progress_info["assistant_info"]
        is_loaded = self.load_state(progress_info)
        if optimize_info is None or not is_loaded:
            progress_info["error_msg"] = (
                "Joint optimize continue_optimize failed, optimize_info is None"
            )
            progress_info[TaskStatus.TASK_STATUS] = TaskStatus.TASK_FAILED
            progress_info["run_time"] = calc_run_time(progress_info["create_time"])
            return
        if self.iter_num == 0:
            self.do_optimize(
                TaskInfo(
                    task_id,
                    progress_info["name"],
                    progress_info["desc"],
                    progress_info["create_time"],
                ),
                raw_templates,
                optimize_info,
                model_info,
                assistant_info,
            )
        else:
            try:
                self.model = LLMModelProcess(model_info)
                self.assistant_model = LLMModelProcess(assistant_info)
                if (
                    optimize_info.user_compare_options
                    == TuneConstant.LLM_EVALUATION_TYPE_SUBJECTIVE
                ):
                    result_compare_prompt = self.prompt_pool["subjective_access_answer"]
                    logger.info(
                        f"user_compare_options: {optimize_info.user_compare_options}"
                    )
                else:
                    result_compare_prompt = self.prompt_pool["access_answer"]
                    logger.info(
                        f"user_compare_options: {TuneConstant.LLM_EVALUATION_TYPE_OBJECTIVE}"
                    )
                result_compare_prompt = result_compare_prompt.replace(
                    "{{user_compare_rules}}", optimize_info.user_compare_rules
                )
                self.evaluator = JointEvaluatorWithRef(
                    model_info, assistant_info, optimize_info, result_compare_prompt
                )
                optimize_algo_config = OptimizeAlgoConfig(
                    params=self.params,
                    model=self.model,
                    stop_event=progress_info.get("cancel_event"),
                    evaluator=self.evaluator,
                    tools=progress_info.get("optimize_info").tools,
                    user_compare_rule=optimize_info.user_compare_rules,
                    prompt_combine_func=self._get_full_prompt,
                )
                self.selected_optimizer = get_selected_algorithm(
                    optimize_info.optimize_algo, optimize_algo_config
                )
                logger.info(f"external knowledge: {self.params.external_knowledge}")
                self.dataset = CaseManager.validate_with_convert(
                    [case.model_dump() for case in optimize_info.cases],
                    CaseManager.convert,
                    default_tools=optimize_info.tools,
                )
                self.variable = self._get_variable_from_dataset(
                    self.dataset, raw_templates[0]
                )
                progress_info[CANCEL_EVENT] = threading.Event()
                logger.info(f"restart task: {task_id}")
                self._refine_task_iteratively(progress_info, self.iter_num)
            except OnStopException:
                ContextManager().set_context_attr(
                    task_id, TaskStatus.TASK_STATUS, TaskStatus.TASK_STOPPED
                )
                if ContextManager().has_store():
                    ContextManager().delete(task_id)
                logger.info(f"Joint optimize task-{task_id} stopped.")
                return
            except Exception as e:
                progress_info[TaskStatus.TASK_STATUS] = TaskStatus.TASK_FAILED
                progress_info["run_time"] = calc_run_time(progress_info["create_time"])
                check_point = ContextManager().get_checkpoint(task_id) or progress_info
                if check_point:
                    check_point["error_msg"] = (
                        f"Joint optimize continue_optimize failed, {str(e)}"
                        if isinstance(e, JiuWenBaseException)
                        else "Joint optimize continue_optimize failed, other reasons"
                    )
                    check_point[TaskStatus.TASK_STATUS] = TaskStatus.TASK_FAILED
                    check_point["run_time"] = calc_run_time(check_point["create_time"])
                    if ContextManager().has_store():
                        try:
                            ContextManager().store_context(task_id, check_point)
                        except JiuWenBaseException:
                            logger.error(
                                "store context failed, please check storage service"
                            )
                        ContextManager().delete(task_id)
                    else:
                        ContextManager().set_checkpoint(task_id, check_point)

    def save_state(
        self,
        progress_info: Dict[str, Any],
        history_record: Dict = None,
        force_save: bool = False,
    ):
        """save"""
        if force_save or self._check_event(progress_info):
            ex_str = (
                self._prepare_example_strings(self.params.examples)
                if self.params.examples
                else ""
            )
            ex_str_cot = (
                self._prepare_example_strings(self.params.cot_examples)
                if self.params.cot_examples
                else ""
            )
            self.params.full_prompt = self.prompt_combine(
                self.params.filled_instruction, ex_str, ex_str_cot
            )
            progress_info["progress_rate"] = self.iter_num / self.params.num_iter
            progress_info["scores"] = [self.acc_base]
            progress_info["params"] = self.params
            progress_info["iter_num"] = self.iter_num
            progress_info["sampled_incorrect_data"] = self.sampled_incorrect_data
            progress_info["run_time"] = calc_run_time(progress_info["create_time"])

            if history_record:
                if "history" not in progress_info:
                    progress_info["history"] = []
                original_placeholder = {}
                if self.params.original_placeholder:
                    for placeholder in self.params.original_placeholder:
                        original_placeholder[placeholder["name"]] = placeholder[
                            "content"
                        ]
                history_record.original_placeholder = original_placeholder
                progress_info["history"].append(history_record)

            job_id = progress_info["id"]
            ContextManager().set_checkpoint(job_id, progress_info)
            if ContextManager().has_store():
                # 持久化保存的状态均为stop
                check_point = ContextManager().get_checkpoint(job_id)
                ContextManager().store_context(job_id, check_point)

    def load_state(self, progress_info) -> bool:
        """ "load"""
        if progress_info.get("iter_num", -1) != 0 and "params" not in progress_info:
            return False
        if "params" in progress_info:
            self.params = progress_info["params"]
        self.iter_num = progress_info["iter_num"]
        self.acc_base = progress_info["scores"][0]
        self.params.filled_instruction = self.fill_prompt(
            self.params.base_instruction, self.params.placeholder
        )
        self.sampled_incorrect_data = progress_info["sampled_incorrect_data"]
        if "cur_accuracy" not in progress_info:
            progress_info["cur_accuracy"] = [
                hist.success_rate for hist in progress_info["history"]
            ]
        return True

    def _get_full_prompt(self, instruction, placeholder) -> str:
        prompt_instruction = self.fill_prompt(instruction, placeholder)
        example_string = self._prepare_example_strings(self.params.examples)
        example_string_cot = self._prepare_example_strings(self.params.cot_examples)
        full_prompt = self.prompt_combine(
            prompt_instruction, example_string, example_string_cot
        )
        return full_prompt

    def _get_variable_from_dataset(self, dataset, prompt):
        variables = set()
        for case in dataset:
            vari = case.get(TuneConstant.VARIABLE_KEY, {})
            variables.update(set(vari.keys()))

        variable_summary_template = (
            self.prompt_pool["variable_summary_template"]
            .replace("{{INSTRUCTION}}", prompt)
            .replace("{{VARIABLE_LIST}}", str(list(variables)))
        )
        response = self.chat_completion(variable_summary_template)
        summary_variables = parse_json(response)

        reorder_variables = [(prompt.find(f"{{{{{v}}}}}"), v) for v in variables]
        reorder_variables = [
            v[1] for v in sorted(reorder_variables, key=lambda x: x[0], reverse=False)
        ]
        return [
            (v, summary_variables.get(v) if v in summary_variables else v)
            for v in reorder_variables
        ]

    def _generate_reasoning(self):
        """
        Generate reasoning for each example in the CoT (Chain-of-Thought) examples.
        """
        if self.params.cot_example_num <= 0:
            return
        self.params.cot_examples = [
            {
                **example,
                "label": self.generate_reasoning(example["question"], example["label"]),
            }
            for example in self.params.cot_examples
        ]

    def _prepare_example_strings(self, examples: List) -> str:
        """
        Prepares formatted example strings from a list of examples
        """
        if not examples:
            return ""

        return "\n".join(self._prepare_examples(examples)) if examples else ""

    def _prepare_examples(self, examples: List) -> List[str]:
        """
        Prepares formatted example string list from a list of examples
        """
        if not examples:
            return []

        example_template = self.prompt_pool["quest_reason_ans"]
        example_strings = []

        for i, example in enumerate(examples):
            question = str(example.get("question", ""))
            answer = example.get("label", "")
            formatted_example = example_template.format(
                question=question, answer=answer
            )
            example_strings.append(f"示例{i + 1}：\n{formatted_example}")

        return example_strings

    def _refine_task_instruction(self, progress_info: Dict[str, Any]) -> History:
        """
        Refines task instruction by evaluating and updating based on critique feedback
        """
        opt_result = self.selected_optimizer.do_optimize(
            self.params.base_instruction, self.sampled_incorrect_data, self.dataset
        )
        meta_update_res = opt_result.prompt
        schema_update_res = opt_result.placeholder
        acc_tmp = opt_result.score
        sampled_incorrect_data = opt_result.error_cases
        evaluations = opt_result.evaluations
        if acc_tmp is None:
            raise JiuWenBaseException(
                error_code=StatusCode.PROMPT_OPTIMIZE_REFINE_INSTRUCTION_ERROR.code,
                message=StatusCode.PROMPT_OPTIMIZE_REFINE_INSTRUCTION_ERROR.errmsg.format(
                    error_msg="get error evaluation result."
                ),
            )
        full_prompt = self._get_full_prompt(meta_update_res, schema_update_res)
        if acc_tmp > self.acc_base:
            self.sampled_incorrect_data = sampled_incorrect_data
            self.acc_base = acc_tmp
            self.params.base_instruction = meta_update_res
            self.placeholder_update(schema_update_res, self.params.placeholder)
            self.params.filled_instruction = self.fill_prompt(
                meta_update_res, schema_update_res
            )
            self.params.full_prompt = full_prompt

        optimized_placeholder = {}
        if schema_update_res and self.params.opt_schema:
            for placeholder in schema_update_res:
                if placeholder.get("name") in self.params.opt_schema:
                    optimized_placeholder[placeholder["name"]] = placeholder["content"]

        return History(
            optimized_prompt=meta_update_res,
            optimized_placeholder=optimized_placeholder,
            examples=self._prepare_examples(self.params.examples)
            + self._prepare_examples(self.params.cot_examples),
            filled_prompt=full_prompt,
            success_rate=acc_tmp,
            iteration_round=self.iter_num,
            evaluations=evaluations,
        )

    def _refine_examples(self, progress_info: Dict[str, Any]) -> Optional[History]:
        """
        Refines examples by selecting the best ones and evaluating their impact on task performance
        """
        if self.params.example_num == 0 and self.params.cot_example_num == 0:
            return None

        examples_tmp = (
            self.select_best_examples(progress_info)
            if self.params.example_num > 0
            else None
        )
        cot_examples_tmp = (
            self.generate_best_examples(progress_info)
            if self.params.cot_example_num > 0
            else None
        )

        example_string = (
            self._prepare_example_strings(examples_tmp) if examples_tmp else ""
        )
        example_string_cot = (
            self._prepare_example_strings(cot_examples_tmp) if cot_examples_tmp else ""
        )

        full_prompt = self.prompt_combine(
            self.params.filled_instruction, example_string, example_string_cot
        )
        acc_tmp, sampled_incorrect_data, evaluations = self.eval(
            full_prompt, progress_info
        )

        if acc_tmp is None:
            return None

        if acc_tmp > self.acc_base:
            self.sampled_incorrect_data = sampled_incorrect_data
            self.acc_base = acc_tmp
            self.params.examples = examples_tmp or []
            self.params.cot_examples = cot_examples_tmp or []
            self.params.full_prompt = full_prompt

        return History(
            optimized_prompt=self.params.base_instruction,
            optimized_placeholder=placeholder_to_dict(self.params.placeholder),
            examples=self._prepare_examples(examples_tmp)
            + self._prepare_examples(cot_examples_tmp),
            filled_prompt=full_prompt,
            success_rate=acc_tmp,
            iteration_round=self.iter_num,
            evaluations=evaluations,
        )

    def _refine_task_iteratively(
        self, progress_info: Dict[str, Any], begin_iter: int = 0
    ):
        """
        Refine the task description and examples iteratively for the given number of iterations.
        """
        logger.info("\nRefining Task description and Examples iteratively....")
        record = {}
        # Iterate through the refinement process for the specified number of iterations
        for iter_num in range(begin_iter, self.params.num_iter):
            if not self._check_event(progress_info):
                return
            self.iter_num = iter_num + 1
            refine_task_flag = random.choice([True, False])
            if self.params.cot_example_num == 0 and self.params.example_num == 0:
                refine_task_flag = True

            logger.info(
                f"Iteration {iter_num + 1}/{self.params.num_iter}, refine_task_flag: {refine_task_flag}"
            )
            # Perform refinement based on the random choice
            if refine_task_flag:
                record = self._refine_task_instruction(progress_info)
            else:
                record = self._refine_examples(progress_info)

            if self.acc_base >= self.params.early_stop_score:
                logger.info(
                    "Early stopping activated due to target accuracy being reached."
                )
                break

            if iter_num < self.params.num_iter - 1:
                self.save_state(progress_info, record)

        progress_info[TaskStatus.TASK_STATUS] = TaskStatus.TASK_FINISHED
        progress_info["run_time"] = calc_run_time(progress_info["create_time"])
        self.save_state(progress_info, record)
        if ContextManager().has_store():
            ContextManager().delete(progress_info["id"])
        logger.info(f"Joint optimize task finished: {progress_info['id']}")
