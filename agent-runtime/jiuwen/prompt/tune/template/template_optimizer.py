# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""
agentBuilder chain Template evaluator
"""

import copy
import random
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import List

from cacheout import Cache
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.common.status import TaskStatus
from jiuwen.common.utils.singleton import Singleton
from jiuwen.prompt import PromptAssembler
from jiuwen.prompt.common.config import LLMModelInfo
from jiuwen.prompt.common.exception.base import JiuWenBaseException
from jiuwen.prompt.template.template_manager import InnerTemplate
from jiuwen.prompt.tune.template.template_evaluator import TemplateEvaluatorWithRef
from jiuwen.prompt.tune.template.utils import (
    LLMModelProcess,
    OptimizeInfo,
    TaskInfo,
    check_not_none_with_alias,
)

CANCEL_EVENT = "cancel_event"


@dataclass
class OptimizeParameter:
    """Definition of Optimize Parameters."""

    task_id: str
    optimize_info: OptimizeInfo
    assistant_info: LLMModelInfo
    evaluator: TemplateEvaluatorWithRef
    cur_batch: int
    num_batch: int


class TemplateOptimizer(metaclass=Singleton):
    """Template optimizer"""

    progress_cache = Cache(maxsize=65536)

    def __init__(self):
        self.assistant_model = None

    @staticmethod
    def calc_run_time(create_time: str) -> int:
        """Calculate the task duration."""
        if not create_time:
            raise JiuWenBaseException(
                error_code=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.code,
                message=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.errmsg.format(
                    error_msg="invalid create_time"
                ),
            )
        try:
            # calculate run time, simple calculation here
            create_time = datetime.strptime(create_time, "%Y-%m-%d %H:%M:%S")
            cur_time = datetime.now(tz=timezone(timedelta(hours=8))).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            cur_time = datetime.strptime(cur_time, "%Y-%m-%d %H:%M:%S")
        except Exception as error:
            raise JiuWenBaseException(
                error_code=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.code,
                message=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.errmsg.format(
                    error_msg="invalid time format"
                ),
            ) from error
        return int((cur_time - create_time).total_seconds())

    @staticmethod
    def check_new_template(new_template: str, ori_template: str) -> bool:
        """Check the placeholders are same between new_template and ori_template"""
        ori_variables = re.findall(r"{{([^{}]*)}}", ori_template)
        new_variables = re.findall(r"{{([^{}]*)}}", new_template)
        if set(ori_variables) != set(new_variables):
            return False
        return True

    @staticmethod
    def all_parents_same(templates: List[str]) -> bool:
        """Check whether the parent templates are the same."""
        if not templates:
            return True
        first_parent = templates[0]
        return all(parent == first_parent for parent in templates)

    @staticmethod
    def select_parents(templates: List[str], scores: List[float]) -> List[str]:
        """Select two parents templates by scores,
        the higher the score, the greater the probability of being selected
        """
        if templates is None or len(templates) < 2:
            raise JiuWenBaseException(
                error_code=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.code,
                message=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.errmsg.format(
                    error_msg="the number of templates is less than 2."
                ),
            )
        if TemplateOptimizer.all_parents_same(templates):
            return [templates[0], templates[0]]

        max_attempts = len(templates) * len(templates)
        for _ in range(max_attempts):
            parents = random.choices(templates, weights=scores, k=min(len(scores), 2))
            if parents[0] != parents[1]:
                return parents
        return [templates[0], templates[0]]

    @staticmethod
    def get_error_info(error, status_code):
        """get mutate_template and crossover_parents operation error info"""
        if isinstance(error, JiuWenBaseException):
            raise JiuWenBaseException(
                status_code.code, status_code.errmsg.format(error_msg=error.message)
            ) from error
        raise JiuWenBaseException(
            status_code.code,
            status_code.errmsg.format(error_msg=str(error)),
        ) from error

    def mutate_template(self, template: str, optimize_info: OptimizeInfo):
        """Mutate original template for new template, increase population diversity"""
        mutate_template = InnerTemplate().get(name="prompt_epo_mutate")
        assembler = PromptAssembler(mutate_template)
        messages = assembler.assemble(initial_prompt=template)
        exc_mutate = ""
        for _ in range(optimize_info.retry_times if optimize_info else 5):
            try:
                response = self.assistant_model.chat(messages)
                text_match = re.findall(
                    r"<prompt>\s{1,5}([^<]*?)\s{1,5}</prompt>",
                    response.get("content"),
                    re.DOTALL,
                )
                new_template = (
                    text_match[-1] if len(text_match) >= 1 else response.get("content")
                )
                if self.check_new_template(new_template, template) and len(
                    new_template
                ) > 0.8 * len(template):
                    return new_template
            except JiuWenBaseException as error:
                exc_mutate = error
            except Exception as e:
                exc_mutate = e

        if exc_mutate:
            self.get_error_info(exc_mutate, StatusCode.PROMPT_TEMPLATE_MUTATE_ERROR)
        return template

    def crossover_parents(self, parents: List[str], optimize_info: OptimizeInfo):
        """Crossover two parents templates to get a child template"""
        if parents is None or len(parents) < 2:
            raise JiuWenBaseException(
                error_code=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.code,
                message=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.errmsg.format(
                    error_msg="the number of parents is less than 2. "
                ),
            )
        crossover_template = InnerTemplate().get(name="prompt_epo_crossover")
        assembler = PromptAssembler(crossover_template)
        messages = assembler.assemble(prompt1=parents[0], prompt2=parents[1])

        exc_crossover = ""
        for _ in range(optimize_info.retry_times if optimize_info else 5):
            try:
                response = self.assistant_model.chat(messages)
                text_match = re.findall(
                    r"<prompt>\s{1,5}([^<]*?)\s{1,5}</prompt>",
                    response.get("content"),
                    re.DOTALL,
                )
                child = (
                    text_match[-1] if len(text_match) >= 1 else response.get("content")
                )
                if self.check_new_template(child, parents[0]) and len(child) > 0.4 * (
                    len(parents[0]) + len(parents[1])
                ):
                    return child
            except JiuWenBaseException as error:
                exc_crossover = error
            except Exception as e:
                exc_crossover = e

        if exc_crossover:
            self.get_error_info(
                exc_crossover, StatusCode.PROMPT_TEMPLATE_CROSSOVER_ERROR
            )
        return random.choice(parents)

    def do_optimize(
        self,
        task_info: TaskInfo,
        raw_templates: List[str],
        optimize_info: OptimizeInfo,
        model_info: LLMModelInfo,
        assistant_info: LLMModelInfo = None,
    ):
        """Template optimizer interface"""
        check_not_none_with_alias(task_info, "task_info")
        assistant_info = model_info if assistant_info is None else assistant_info
        assistant_info.top_p = 0.95
        self.progress_cache.set(
            task_info.task_id,
            dict(
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
                scores=[1.0] * len(raw_templates),
                error_msg="",
                cancel_event=threading.Event(),
                status=TaskStatus.TASK_RUNNING,
            ),
        )

        try:
            # When optimizing_info is defined, the value of len(optimize_info.cases) is not 0.
            check_not_none_with_alias(optimize_info, "optimize_info")

            optimize_info.pop_size = max(optimize_info.pop_size, optimize_info.num_iter)
            optimize_info.eval_size = min(
                optimize_info.eval_size, len(optimize_info.cases)
            )
            raw_templates = raw_templates[: optimize_info.pop_size]
            self.assistant_model = LLMModelProcess(assistant_info)

            evaluator = TemplateEvaluatorWithRef(
                raw_templates, model_info, assistant_info
            )
            new_templates = [
                self.mutate_template(
                    raw_templates[i % len(raw_templates)], optimize_info
                )
                for i in range(optimize_info.pop_size - len(raw_templates))
            ]
            templates = raw_templates + new_templates
            scores = [1.0 for _ in range(optimize_info.pop_size)]
            # The value of eval_size cannot be 0 when OptimizeInfo is defined.
            logger.info(f"Template optimize task start: {task_info.task_id}")
            num_batch = optimize_info.num_iter * (
                len(optimize_info.cases) // optimize_info.eval_size
            )
            for cur_batch in range(num_batch):
                optim_para = OptimizeParameter(
                    task_id=task_info.task_id,
                    optimize_info=optimize_info,
                    assistant_info=assistant_info,
                    evaluator=evaluator,
                    cur_batch=cur_batch,
                    num_batch=num_batch,
                )
                self._do_evolve(optim_para, templates, scores)
                progress_info = self.progress_cache.get(task_info.task_id)
                if progress_info is not None:
                    templates = copy.deepcopy(progress_info["templates"])
                    scores = copy.deepcopy(progress_info["scores"])

            progress_info = self.progress_cache.get(task_info.task_id)
            if (
                progress_info is not None
                and progress_info[TaskStatus.TASK_STATUS] == TaskStatus.TASK_RUNNING
            ):
                progress_info[TaskStatus.TASK_STATUS] = TaskStatus.TASK_FINISHED
                progress_info["run_time"] = self.calc_run_time(
                    progress_info["create_time"]
                )
                logger.info(f"Template optimize task finished: {task_info.task_id}")

        except Exception as e:
            progress_info = self.progress_cache.get(task_info.task_id)
            if progress_info is not None:
                progress_info["error_msg"] = (
                    "Template optimize failed"
                    if isinstance(e, JiuWenBaseException)
                    else "Template optimize failed, other reasons"
                )
                progress_info[TaskStatus.TASK_STATUS] = TaskStatus.TASK_FAILED
                progress_info["run_time"] = self.calc_run_time(
                    progress_info["create_time"]
                )
                self.progress_cache.set(task_info.task_id, progress_info)

    def continue_optimize(self, task_id: str):
        """Template continue optimizer interface"""
        progress_info = self.progress_cache.get(task_id)
        check_not_none_with_alias(progress_info, "progress_info")
        raw_templates = progress_info["raw_templates"]
        optimize_info = progress_info["optimize_info"]
        model_info = progress_info["model_info"]
        assistant_info = progress_info["assistant_info"]
        if optimize_info is None:
            progress_info["error_msg"] = (
                "Template optimize continue_evolve failed, optimize_info is None"
            )
            progress_info[TaskStatus.TASK_STATUS] = TaskStatus.TASK_FAILED
            progress_info["run_time"] = self.calc_run_time(progress_info["create_time"])
            self.progress_cache.set(task_id, progress_info)
            return
        # The value of eval_size cannot be 0 when OptimizeInfo is defined.
        num_batch = optimize_info.num_iter * (
            len(optimize_info.cases) // optimize_info.eval_size
        )
        optimized_batch = int(progress_info["progress_rate"] * num_batch)
        if optimized_batch == 0:
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
                self.assistant_model = LLMModelProcess(assistant_info)
                evaluator = TemplateEvaluatorWithRef(
                    raw_templates, model_info, assistant_info
                )
                progress_info[TaskStatus.TASK_STATUS] = TaskStatus.TASK_RUNNING
                progress_info[CANCEL_EVENT] = threading.Event()
                logger.info(f"restart task: {task_id}")
                for cur_batch in range(optimized_batch, num_batch):
                    optim_para = OptimizeParameter(
                        task_id=task_id,
                        optimize_info=optimize_info,
                        assistant_info=assistant_info,
                        evaluator=evaluator,
                        cur_batch=cur_batch,
                        num_batch=num_batch,
                    )
                    progress_info_tmp = self.progress_cache.get(task_id)
                    self._do_evolve(
                        optim_para,
                        copy.deepcopy(progress_info_tmp["templates"]),
                        copy.deepcopy(progress_info_tmp["scores"]),
                    )
                progress_info = self.progress_cache.get(task_id)
                if (
                    progress_info is not None
                    and progress_info[TaskStatus.TASK_STATUS] == TaskStatus.TASK_RUNNING
                ):
                    progress_info[TaskStatus.TASK_STATUS] = TaskStatus.TASK_FINISHED
                    progress_info["run_time"] = self.calc_run_time(
                        progress_info["create_time"]
                    )
                    logger.info(f"Template optimize task finished: {task_id}")
            except Exception as e:
                progress_info = self.progress_cache.get(task_id)
                if progress_info is not None:
                    progress_info["error_msg"] = (
                        f"Template optimize continue_evolve failed, {str(e)}"
                        if isinstance(e, JiuWenBaseException)
                        else "Template optimize continue_evolve failed, other reasons"
                    )
                    progress_info[TaskStatus.TASK_STATUS] = TaskStatus.TASK_FAILED
                    progress_info["run_time"] = self.calc_run_time(
                        progress_info["create_time"]
                    )
                    self.progress_cache.set(task_id, progress_info)

    def _check_event(self, task_id) -> bool:
        """Check optimization status"""
        progress_info = self.progress_cache.get(task_id)
        if (
            progress_info
            and progress_info[CANCEL_EVENT]
            and progress_info[CANCEL_EVENT].is_set()
        ):
            logger.info("evolve finished")
            if progress_info[TaskStatus.TASK_STATUS] == TaskStatus.TASK_DELETED:
                self.progress_cache.delete(task_id)
                logger.info("clean task")
            return False
        return True

    def _do_evolve(self, optim_para, templates, scores):
        """Specific implementation of template optimization"""
        check_not_none_with_alias(optim_para, "optim_para")
        if not self._check_event(optim_para.task_id):
            return

        check_not_none_with_alias(optim_para.optimize_info, "optim_para.optimize_info")
        # crossover & mutate
        cross_templates = []
        for _ in range(optim_para.optimize_info.pop_size):
            if not self._check_event(optim_para.task_id):
                return
            parents = self.select_parents(templates, scores)
            child = self.crossover_parents(parents, optim_para.optimize_info)
            cross_templates.append(child)
        templates.extend(cross_templates)

        # evaluate & select
        progress_info = self.progress_cache.get(optim_para.task_id)
        check_not_none_with_alias(progress_info, "progress_info")
        check_not_none_with_alias(optim_para.evaluator, "optim_para.evaluator")
        scores = optim_para.evaluator.evaluate(
            templates, optim_para.optimize_info, progress_info[CANCEL_EVENT]
        )
        sorted_id = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        templates = [
            templates[i] for i in sorted_id[: optim_para.optimize_info.pop_size]
        ]
        scores = [scores[i] for i in sorted_id[: optim_para.optimize_info.pop_size]]
        logger.info(
            f"Template optimize: optimization progress {optim_para.cur_batch + 1} / {optim_para.num_batch}"
        )
        logger.info(f"Template optimize: best template {templates[0]}")
        if self._check_event(optim_para.task_id):
            progress_info["progress_rate"] = (
                optim_para.cur_batch + 1
            ) / optim_para.num_batch
            progress_info["templates"] = copy.deepcopy(templates)
            progress_info["scores"] = copy.deepcopy(scores)
            progress_info["run_time"] = self.calc_run_time(progress_info["create_time"])
            self.progress_cache.set(optim_para.task_id, progress_info)
