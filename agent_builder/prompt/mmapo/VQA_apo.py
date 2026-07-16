# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import heapq
import random
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Any

import regex
from agent_builder.common.logging.base import logger
from agent_builder.common.status import TaskStatus
from agent_builder.prompt.common.config import LLMModelInfo
from agent_builder.prompt.mmapo.apo_evaluator import ApoEvaluatorWithRef
from agent_builder.prompt.mmapo.prompt import (
    TRANSFORMED_PROMPT,
    PLACEHOLDER_RESTORE_TEMPLATE,
)
from agent_builder.prompt.mmapo.utils import (
    ProblemExample,
    get_dataset_multi_modal,
    ApoParams,
    chat_completion,
    WORKERS_NUM,
    ApoCaseManager,
)
from agent_builder.prompt.tune.base.context import History
from agent_builder.prompt.tune.base.context_manager import ContextManager
from agent_builder.prompt.tune.base.utils import (
    OptimizeInfo,
    check_not_none_with_alias,
    LLMModelProcess,
    calc_run_time,
    OnStopException,
)
from agent_builder.prompt.tune.joint_optimizer import JointOptimizer
from agent_builder.adapter.exception_bridge import JiuWenBaseException
from agent_builder.adapter.task_info import TaskInfo

BATCH_NUMBER_PER_EPOCH = 3


class ApoOptimizer(JointOptimizer):
    def __init__(self):
        """init"""
        super().__init__()
        self.params = ApoParams()
        self.optimized_model = None
        self.dataset: Optional[List[ProblemExample]] = None
        self._candidates = []
        self.evaluator = None
        self.placeholders_in_original_prompt = None

    @staticmethod
    def parse_tagged_text(text, start_tag: str, end_tag: str) -> List[str]:
        """Parse text that is tagged with start and end tags, returning all matches."""
        if not isinstance(text, str):
            text = str(text)

        # 使用 findall 来获取所有匹配的值
        pattern = f"{re.escape(start_tag)}(.*?){re.escape(end_tag)}"
        matches = regex.findall(pattern, text, re.DOTALL, timeout=1)
        return [match.strip() for match in matches]

    @staticmethod
    def format_error_str(sampled_error_data: List[dict]) -> str:
        """format_error_str"""
        error_string = ""
        count = 1
        for error_data in sampled_error_data:
            question = error_data.get("question", "")
            predict = error_data.get("predict", "")
            answer = error_data.get("answer", "")

            error_string += f"### Example {count}\n"
            error_string += f'Input Question: "{str(question)}"\n'
            error_string += f'Prediction: "{str(predict)}"\n'
            error_string += f'Ground Truth: "{str(answer)}"\n'
            count += 1
        return error_string.strip()

    def sample_error_str(self, error_data: List[dict], sample_num: int) -> str:
        """sample and construct error str"""
        if not error_data:
            return ""

        def weight_fn(item):
            score = item.get("score")
            return 10 - score

        weights = [weight_fn(item) for item in error_data]

        # 加权采样（可重复）
        sampled_error_data = random.choices(
            population=error_data, weights=weights, k=min(len(error_data), sample_num)
        )
        return self.format_error_str(sampled_error_data)

    def get_gradients(
        self, prompt: str, error_data: List[dict]
    ) -> list[tuple[str, str]]:
        """get_gradients"""
        prompt_feedbacks = []
        for _ in range(self.params.n_gradients):
            error_string = self.sample_error_str(
                error_data, self.params.sampled_error_num
            )
            gradients = self._get_gradients(
                prompt, error_string, self.params.gradients_per_error
            )
            prompt_feedbacks.extend((g, error_string) for g in gradients)

        prompt_feedbacks = list(set(prompt_feedbacks))

        return prompt_feedbacks

    def apply_gradient(
        self, prompt: str, error_str: str, feedback_str: str
    ) -> List[str]:
        """Incorporate feedback gradient into a prompt."""
        transformation_prompt = f"""
        I'm trying to refine a prompt for large language model.

        My current prompt is:
        "{prompt}"

        But it gets the following examples wrong:
        {error_str}

        Based on these examples the problem with this prompt is that {feedback_str}

        Based on the above information, I wrote a different improved prompts.
        The improved prompt should be wrapped with <INS> and </INS>.
        
        **Important**:
        - Do NOT summarize or omit any part of the improved prompt.
        - Do NOT replace long text with ellipses like "...".
        - Always output the full and exact improved prompt in its entirety.
        - The improved prompt must appear fully between <INS> and </INS>, with no truncation.
        
        The new prompt are:
        """
        transformation_prompt = "\n".join(
            [line.lstrip() for line in transformation_prompt.split("\n")]
        )
        responses = chat_completion(transformation_prompt, self.optimized_model)
        new_prompts = self.parse_tagged_text(responses, "<INS>", "</INS>")
        return new_prompts

    def generate_new_prompts(self, candidate: str, error_data: List[dict]) -> List[str]:
        """Generate new prompts based on gradients."""
        cur_new_prompts = []
        gradients = self.get_gradients(candidate, error_data)
        for feedback, error_string in gradients:
            tmp = self.apply_gradient(candidate, error_string, feedback)
            cur_new_prompts += tmp
        return cur_new_prompts

    def generate_synonyms(self, prompt_section: str) -> List[str]:
        """Generate synonyms for a prompt section."""
        rewriter_prompt = (
            f"Generate a variation of the following instruction while keeping the semantic "
            f"meaning.\n\nInput: {prompt_section}\n\nOutput:"
        )
        new_instruction = chat_completion(rewriter_prompt, self.optimized_model)
        return [new_instruction]

    def generate_mc_samples(
        self, cur_new_prompts: List[str], candidate: str
    ) -> List[str]:
        """Generate Monte Carlo synonyms from new prompts and the candidate."""
        all_prompts = cur_new_prompts + [candidate]
        mc_sampled_prompts = []

        def worker(prompt):
            return self.generate_synonyms(prompt)

        with ThreadPoolExecutor(
            max_workers=min(WORKERS_NUM, len(all_prompts))
        ) as executor:
            futures = [executor.submit(worker, prompt) for prompt in all_prompts]
            for future in as_completed(futures):
                result = future.result()
                mc_sampled_prompts += result
        return mc_sampled_prompts

    def expand_candidates(
        self, train_dataset: List[ProblemExample], cancel_event: threading.Event
    ):
        """并发扩展 candidates"""
        logger.info(f"expanding from {len(self._candidates)} candidates")
        if len(train_dataset) > self.params.minibatch_size:
            minibatch = random.sample(train_dataset, k=self.params.minibatch_size)
        else:
            minibatch = train_dataset

        def process_candidate(prompt):
            logger.info(
                f"evaluating on {len(minibatch)} samples from train data on candidate"
            )
            accuracy, _, _, error_data = self.evaluator.evaluate_one_prompt(
                prompt, minibatch
            )

            cur_new_prompts = []
            if accuracy < self.params.early_stop_score and self.params.n_gradients > 0:
                logger.info("text grading on error samples on candidate")
                cur_new_prompts = self.generate_new_prompts(prompt, error_data)

            mc_sampled_prompts = []
            if self.params.mc_samples_per_step:
                logger.info("mc-ing on candidate")
                mc_sampled_prompts = self.generate_mc_samples(cur_new_prompts, prompt)

            cur_merged_prompts = list(set(cur_new_prompts + mc_sampled_prompts))
            if len(cur_merged_prompts) > self.params.max_expansion_factor:
                cur_merged_prompts = random.sample(
                    cur_merged_prompts, self.params.max_expansion_factor
                )

            return cur_merged_prompts

        all_prompts = []

        with ThreadPoolExecutor(
            max_workers=min(WORKERS_NUM, len(self._candidates))
        ) as executor:
            futures = {
                executor.submit(process_candidate, prompt): prompt
                for prompt in self._candidates
            }
            for future in as_completed(futures):
                result = future.result()
                all_prompts += result

        if not all_prompts:
            logger.info("generate 0 new prompt, add original candidates")

        for index, prompt in enumerate(all_prompts):
            missing_placeholders = self._check_placeholders_from_prompt(prompt)
            if missing_placeholders:
                all_prompts[index] = self._add_missing_placeholders_to_prompt(
                    prompt, missing_placeholders
                )

        self._candidates += all_prompts

    def get_concrete_prompt(self, situation):
        """get_concrete_prompt"""
        content = TRANSFORMED_PROMPT
        content = content.replace("{{instruction}}", situation)
        response = chat_completion(content, self.assistant_model)
        response = self.parse_tagged_text(response, "<INS>", "</INS>")
        return response

    def params_init(self, optimize_info, raw_templates, progress_info: Dict[str, Any]):
        """params init"""
        self.params.num_iter = optimize_info.num_iter
        if optimize_info.early_stop_score is not None:
            self.params.early_stop_score = optimize_info.early_stop_score
        self.params.cot_example_num = 0
        self.params.base_instruction = raw_templates[0]
        self.params.full_prompt = raw_templates[0]
        self.save_state(progress_info, force_save=True)

    def do_optimize(
        self,
        task_info: TaskInfo,
        raw_templates: List[str],
        optimize_info: OptimizeInfo,
        model_info: LLMModelInfo,
        assistant_info: LLMModelInfo = None,
    ):
        """_do_optimize"""
        check_not_none_with_alias(task_info, "task_info")
        self.placeholders_in_original_prompt = set(
            re.findall(r"\{\{(.*?)\}\}", raw_templates[0])
        )
        ApoCaseManager.apo_validate_with_convert(
            [case.model_dump() for case in optimize_info.cases],
            self.placeholders_in_original_prompt,
        )
        self._candidates = raw_templates[:]
        progress_info = dict(
            id=task_info.task_id,
            name=task_info.name,
            desc=task_info.desc,
            create_time=task_info.create_time,
            run_time=0,
            raw_templates=self._candidates,
            optimize_info=optimize_info,
            model_info=model_info,
            assistant_info=assistant_info,
            progress_rate=0.0,
            templates=self._candidates,
            scores=[0.0] * len(self._candidates),
            error_msg="",
            cancel_event=threading.Event(),
            status=TaskStatus.TASK_RUNNING,
            cur_accuracy=[],
            task_iter=0,
            history=[],
        )
        ContextManager().set(task_info.task_id, progress_info)
        try:
            self.optimized_model = LLMModelProcess(model_info)
            self.assistant_model = LLMModelProcess(assistant_info)
            self.params_init(optimize_info, raw_templates, progress_info)
            self.evaluator = ApoEvaluatorWithRef(
                model_info,
                assistant_info,
                optimize_info,
                progress_info.get("cancel_event"),
            )
            self.dataset = get_dataset_multi_modal(optimize_info.cases)
            # 基线分数评测
            baseline_result = self.evaluator.eval_candidates(
                self.dataset, self._candidates
            )
            base_score, base_prompt, base_eval_data, self.sampled_incorrect_data = (
                self._select_top_k(baseline_result)
            )
            self.acc_base = base_score[0]
            baseline_history = History(
                optimized_prompt=base_prompt[0],
                iteration_round=0,
                success_rate=base_score[0],
                evaluations=base_eval_data[0],
            )
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
            logger.info(f"MMAPO optimize task-{task_info.task_id} stopped.")
        except Exception as e:
            logger.error(f"failed to do MMAPO optimize by error: {e}")
            progress_info[TaskStatus.TASK_STATUS] = TaskStatus.TASK_FAILED
            progress_info["run_time"] = calc_run_time(progress_info["create_time"])
            check_point = (
                ContextManager().get_checkpoint(task_info.task_id) or progress_info
            )
            if check_point:
                check_point["error_msg"] = (
                    f"MMAPO optimize failed, {str(e)}"
                    if isinstance(e, JiuWenBaseException)
                    else "Joint optimize failed, other reasons"
                )
                check_point[TaskStatus.TASK_STATUS] = TaskStatus.TASK_FAILED
                check_point["run_time"] = calc_run_time(check_point["create_time"])
                if ContextManager().has_store():
                    try:
                        ContextManager().store_context(task_info.task_id, check_point)
                    except Exception:
                        logger.error(
                            "store MMAPO context failed, please check storage service"
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
                self.placeholders_in_original_prompt = set(
                    re.findall(r"\{\{(.*?)\}\}", raw_templates[0])
                )
                self.optimized_model = LLMModelProcess(model_info)
                self.assistant_model = LLMModelProcess(assistant_info)
                self._candidates = raw_templates[:]
                self.dataset = get_dataset_multi_modal(optimize_info.cases)
                self.params_init(optimize_info, raw_templates, progress_info)
                progress_info["cancel_event"] = threading.Event()
                self.evaluator = ApoEvaluatorWithRef(
                    model_info,
                    assistant_info,
                    optimize_info,
                    progress_info.get("cancel_event"),
                )
                logger.info(
                    f"Total {optimize_info.num_iter} rounds optimize task last."
                )
                self._refine_task_iteratively(progress_info, self.iter_num)
            except OnStopException:
                ContextManager().set_context_attr(
                    task_id, TaskStatus.TASK_STATUS, TaskStatus.TASK_STOPPED
                )
                if ContextManager().has_store():
                    ContextManager().delete(task_id)
                logger.info(f"MMAPO optimize task-{task_id} stopped.")
            except Exception as e:
                logger.error(f"failed to do MMAPO optimize by error: {e}")
                progress_info[TaskStatus.TASK_STATUS] = TaskStatus.TASK_FAILED
                progress_info["run_time"] = calc_run_time(progress_info["create_time"])
                check_point = ContextManager().get_checkpoint(task_id) or progress_info
                if check_point:
                    check_point["error_msg"] = (
                        f"MMAPO optimize failed, {str(e)}"
                        if isinstance(e, JiuWenBaseException)
                        else "Joint optimize failed, other reasons"
                    )
                    check_point[TaskStatus.TASK_STATUS] = TaskStatus.TASK_FAILED
                    check_point["run_time"] = calc_run_time(check_point["create_time"])
                    if ContextManager().has_store():
                        try:
                            ContextManager().store_context(task_id, check_point)
                        except Exception:
                            logger.error(
                                "store MMAPO context failed, please check storage service"
                            )
                        ContextManager().delete(task_id)
                    else:
                        ContextManager().set_checkpoint(task_id, check_point)

    def save_state(
        self,
        progress_info: Dict[str, Any],
        history_record: History = None,
        force_save: bool = False,
    ):
        """save"""
        if not (force_save or self._check_event(progress_info)):
            return
        progress_info["progress_rate"] = self.iter_num / self.params.num_iter
        progress_info["scores"] = [self.acc_base]
        progress_info["params"] = self.params
        progress_info["iter_num"] = self.iter_num
        progress_info["sampled_incorrect_data"] = self.sampled_incorrect_data
        progress_info["run_time"] = calc_run_time(progress_info["create_time"])

        if history_record:
            if "history" not in progress_info:
                progress_info["history"] = []
            progress_info["history"].append(history_record)
        job_id = progress_info["id"]
        ContextManager().set_checkpoint(job_id, progress_info)
        if ContextManager().has_store():
            # 持久化保存的状态均为stop
            check_point = ContextManager().get_checkpoint(job_id)
            ContextManager().store_context(job_id, check_point)

    def _get_gradients(
        self, prompt: str, error_string: str, num_feedbacks: int
    ) -> List[str]:
        """Get "gradients" for a prompt based on the error string."""
        gradient_prompt = f"""
        I'm trying to refine a prompt for large language model.

        My current prompt is:
        "{prompt}"

        But this prompt gets the following examples wrong:
        {error_string}

        Please focus on the difference of ground truth and prediction,
        and give {num_feedbacks} reasons why the prompt could have gotten these examples wrong.
        Wrap each reason with <INS> and </INS>
        """
        gradient_prompt = "\n".join(
            [line.lstrip() for line in gradient_prompt.split("\n")]
        )
        response = chat_completion(gradient_prompt, self.assistant_model)
        feedbacks = []
        feedbacks += self.parse_tagged_text(response, "<INS>", "</INS>")
        return feedbacks

    def _refine_task_iteratively(
        self, progress_info: Dict[str, Any], begin_iter: int = 0
    ):
        logger.info("Refining MMAPO Task description and Examples iteratively....")
        for iter_num in range(begin_iter, self.params.num_iter):
            self.iter_num += 1
            logger.info(f"Iteration {self.iter_num}/{self.params.num_iter}")
            if not self._check_event(progress_info):
                return
            if iter_num > 0 and iter_num % BATCH_NUMBER_PER_EPOCH == 0:
                # 每BATCH_NUMBER_PER_EPOCH轮找出历史上最好的提示词，然后加入candidates
                self._candidates.append(self.params.base_instruction)

            record = self._refine_task_instruction(progress_info)
            if record.success_rate >= self.params.early_stop_score:
                logger.info(
                    f"[Early Stop] Accuracy {record.success_rate:.4f} "
                    f"already exceeds target {self.params.early_stop_score}"
                )
                break
            if iter_num < self.params.num_iter - 1:
                self.save_state(progress_info, record)

        progress_info[TaskStatus.TASK_STATUS] = TaskStatus.TASK_FINISHED
        progress_info["run_time"] = calc_run_time(progress_info.get("create_time"))
        self.save_state(progress_info, record)
        if ContextManager().has_store():
            ContextManager().delete(progress_info["id"])
        logger.info(f"Joint optimize task finished: {progress_info.get('id')}")

    def _refine_task_instruction(self, progress_info: Dict[str, Any]) -> History:
        self.expand_candidates(self.dataset, progress_info.get("cancel_event"))
        if len(self.dataset) > self.params.eval_budget:
            eval_dataset = random.sample(self.dataset, k=self.params.eval_budget)
        else:
            eval_dataset = self.dataset
        current_states = self.evaluator.eval_candidates(eval_dataset, self._candidates)
        # 排序以找出当前轮最优
        _, self._candidates, _, _ = self._select_top_k(
            current_states, self.params.beam_size
        )

        concrete_prompt = self.get_concrete_prompt(self._candidates[0])

        for index, prompt in enumerate(concrete_prompt):
            missing_placeholders = self._check_placeholders_from_prompt(prompt)
            if missing_placeholders:
                concrete_prompt[index] = self._add_missing_placeholders_to_prompt(
                    prompt, missing_placeholders
                )

        self._candidates += concrete_prompt
        current_states = self.evaluator.eval_candidates(self.dataset, self._candidates)
        (
            best_one_scores,
            best_one_prompts,
            best_eval_data,
            self.sampled_incorrect_data,
        ) = self._select_top_k(current_states)
        if best_one_scores[0] > self.acc_base:
            self.acc_base = best_one_scores[0]
            self.params.base_instruction = best_one_prompts[0]
            self.params.full_prompt = best_one_prompts[0]

        return History(
            optimized_prompt=best_one_prompts[0],
            success_rate=best_one_scores[0],
            iteration_round=self.iter_num,
            evaluations=best_eval_data[0],
        )

    def _select_top_k(self, current_state, k: int = 1):
        top_k_results = heapq.nlargest(k, current_state, key=lambda x: x[0])
        best_scores = [result[0] for result in top_k_results]
        best_prompts = [result[1] for result in top_k_results]
        best_eval_data = [result[2] for result in top_k_results]
        incorrect_data = [result[3] for result in top_k_results]
        return best_scores, best_prompts, best_eval_data, incorrect_data

    def _check_placeholders_from_prompt(self, prompt: str):
        placeholders_in_prompt = set(re.findall(r"\{\{(.*?)\}\}", prompt))
        return list(
            set(self.placeholders_in_original_prompt) - set(placeholders_in_prompt)
        )

    def _add_missing_placeholders_to_prompt(
        self,
        opt_prompt,
        missing_placeholders,
    ) -> str:
        placeholder_restore_template = PLACEHOLDER_RESTORE_TEMPLATE.replace(
            "{{original_prompt}}", self.params.base_instruction
        )
        placeholder_restore_template = placeholder_restore_template.replace(
            "{{revised_prompt}}", opt_prompt
        )
        placeholder_restore_template = placeholder_restore_template.replace(
            "{{all_placeholders}}", str(self.placeholders_in_original_prompt)
        )
        placeholder_restore_template = placeholder_restore_template.replace(
            "{{missing_placeholders}}", str(missing_placeholders)
        )

        restored_prompt = chat_completion(
            placeholder_restore_template, self.optimized_model
        )
        missing_placeholders = self._check_placeholders_from_prompt(restored_prompt)
        pattern = r"<revised_prompt>\n?(.*?)\n?</revised_prompt>"
        match = re.search(pattern, restored_prompt, re.DOTALL)

        if match:
            content = match.group(1).strip()
            if missing_placeholders:
                content = (
                    content
                    + "\n"
                    + "\n".join(f"{{{{{ph}}}}}" for ph in missing_placeholders)
                )
            return content
        if missing_placeholders:
            restored_prompt = (
                restored_prompt
                + "\n"
                + "\n".join(f"{{{{{ph}}}}}" for ph in missing_placeholders)
            )
        return restored_prompt
