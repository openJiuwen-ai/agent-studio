# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

import copy
import random
import re
from typing import Optional, List

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.common.logging.base import logger
from agent_builder.prompt.tune.base.constant import TuneConstant
from agent_builder.prompt.tune.instruction.base_optimizer import (
    BasicOptimizer,
    OptimizeOutput,
    OptimizeAlgoConfig,
)
from agent_builder.adapter.exception_bridge import JiuWenBaseException


class GreedyOptimizer(BasicOptimizer):
    def __init__(self, opt_algo_config: OptimizeAlgoConfig):
        super().__init__(
            opt_algo_config.model,
            opt_algo_config.stop_event,
            opt_algo_config.evaluator,
            opt_algo_config.tools,
            opt_algo_config.user_compare_rule,
        )
        self._params = opt_algo_config.params
        self._get_full_prompt = opt_algo_config.prompt_combine_func

    @staticmethod
    def _parse_optimized_prompt(content) -> Optional[str]:
        """
        Extracts and returns meta content between <PROMPT_OPTIMIZED> tags
        """
        prompt_meta_pattern = (
            r"<PROMPT_OPTIMIZED>((?:(?!<PROMPT_OPTIMIZED>).)*?)</PROMPT_OPTIMIZED>"
        )
        prompt_meta_match = re.search(prompt_meta_pattern, content, re.DOTALL)

        if not prompt_meta_match:
            logger.warning("parse optimized prompt failed")
            return None

        prompt_meta_content = prompt_meta_match.group(1)
        return prompt_meta_content.replace("<prompt_base>", "").replace(
            "</prompt_base>", ""
        )

    @staticmethod
    def _parse_optimized_placeholders(content):
        """
        Extracts placeholders and returns them as a list of dictionaries
        """
        placeholder_pattern = r"<PLACEHOLDER_OPTIMIZED>((?:(?!<PLACEHOLDER_OPTIMIZED>).)*?)</PLACEHOLDER_OPTIMIZED>"
        placeholder_match = re.search(placeholder_pattern, content, re.DOTALL)

        if not placeholder_match:
            logger.warning("parse optimized placeholders failed")
            return None

        placeholder_content = placeholder_match.group(1)

        pattern = re.compile(r"<([^<>]{1,50})>([^<]*?)</\1>", re.S)
        matches = pattern.findall(placeholder_content)

        return [
            {"name": tag.strip(), "content": content.strip()}
            for tag, content in matches
        ]

    @staticmethod
    def _prepare_critique_prompt(
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
    def _fill_prompt(instruction, placeholder):
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

    def do_optimize(
        self, prompt: str, bad_cases: List, dataset: List
    ) -> OptimizeOutput:

        textual_gradient, error_example_string = self._get_textual_gradient(
            prompt, bad_cases, self._params.external_knowledge
        )

        for _ in range(5):
            if not self._params.placeholder:
                prompt_update = self._process_without_placeholder(
                    prompt, error_example_string, textual_gradient, self._tools
                )
                placeholder_update = None
            else:
                prompt_update, placeholder_update = self._process_with_placeholder(
                    prompt, error_example_string, textual_gradient, self._tools
                )
            if prompt_update:
                break
        optimized_full_prompt = self._get_full_prompt(prompt_update, placeholder_update)
        acc, sampled_incorrect_data, evaluations = self._evaluator.evaluate(
            optimized_full_prompt, dataset, self._stop_event
        )
        logger.info("prompt update successful")
        return OptimizeOutput(
            prompt=prompt_update,
            placeholder=placeholder_update,
            score=acc,
            error_cases=sampled_incorrect_data or [],
            evaluations=evaluations or [],
        )

    def _process_with_placeholder(
        self, instruction, error_example_string, textual_gradient, tools
    ):
        """处理有占位符的情况"""
        self._params.opt_placeholder = "\n".join(
            "{{{}}}".format(p) for p in self._params.opt_schema if p
        )
        placeholder_contents = "".join(
            f"<{p['name']}>\n{p['content']}\n</{p['name']}>\n"
            for p in self._params.placeholder
        )

        opt_prompt_meta = self._prepare_critique_prompt(
            self._prompt_pool["critique_refine_template_meta"],
            instruction,
            placeholder_contents,
            error_example_string,
            textual_gradient,
        )
        opt_prompt_meta.replace(
            "{{API_TOOLS_DESCRIPTION}}", str(tools) if tools else "None"
        )
        refined_meta = self._chat_completion(opt_prompt_meta)
        meta_update_res = self._parse_optimized_prompt(refined_meta)

        # 更新占位符
        schema_update_res = None
        optimized_placeholders = copy.deepcopy(self._params.placeholder)
        if self._params.opt_schema:
            fixed_placeholders = [
                p
                for p in self._params.placeholder
                if p.get("name") not in self._params.opt_schema
            ]
            opt_placeholders = [
                p
                for p in self._params.placeholder
                if p.get("name") in self._params.opt_schema
            ]
            instruction = self._fill_prompt(instruction, fixed_placeholders)
            placeholder_contents = "".join(
                f"<{p['name']}>\n{p['content']}\n</{p['name']}>\n"
                for p in opt_placeholders
            )
            opt_prompt_schema = self._prepare_critique_prompt(
                self._prompt_pool["critique_refine_template_schema"],
                instruction,
                placeholder_contents,
                error_example_string,
                textual_gradient,
            )
            opt_prompt_schema.replace(
                "{{API_TOOLS_DESCRIPTION}}", str(tools) if tools else "None"
            )
            opt_prompt_schema = opt_prompt_schema.replace(
                "{{PLACEHOLDER_TO_OPTIMIZE}}", self._params.opt_placeholder
            )
            schema_update_res = self._chat_completion(opt_prompt_schema)
            schema_update_res = self._parse_optimized_placeholders(schema_update_res)

        if not schema_update_res:
            return meta_update_res, optimized_placeholders

        self._placeholder_update(schema_update_res, optimized_placeholders)
        return meta_update_res, optimized_placeholders

    def _process_without_placeholder(
        self, instruction, example_string, critique_text, tools
    ):
        """处理没有占位符的情况"""
        opt_prompt_meta = self._prompt_pool["critique_refine_template_normal"]
        opt_prompt_meta = opt_prompt_meta.replace(
            "{{PROMPT_META_TEMPLATE}}", instruction
        )
        opt_prompt_meta = opt_prompt_meta.replace("{{ERROR_CASES}}", example_string)
        opt_prompt_meta = opt_prompt_meta.replace(
            "{{REFLECTIONS_ON_ERROR_CASES}}", critique_text
        )
        opt_prompt_meta = opt_prompt_meta.replace(
            "{{API_TOOLS_DESCRIPTION}}", str(tools) if tools else "None"
        )

        refined_meta = self._chat_completion(opt_prompt_meta)

        return self._parse_optimized_prompt(refined_meta)

    def _placeholder_update(self, new_placeholders: List, placeholders_to_update: List):
        """
        Updates placeholders based on update results
        """
        if not new_placeholders or not self._params.opt_placeholder:
            return
        for update_item in new_placeholders:
            name = update_item.get("name")
            content = update_item.get("content")

            if not name or not content or name not in self._params.opt_placeholder:
                continue

            for i, base_item in enumerate(placeholders_to_update):
                if name == base_item.get("name", ""):
                    placeholders_to_update[i]["content"] = content
                    break


class BeamSearchOptimizer(GreedyOptimizer):
    def __init__(self, opt_algo_config: OptimizeAlgoConfig):
        super().__init__(opt_algo_config)
        self._candidates = []

    def do_optimize(
        self, prompt: str, bad_cases: List, dataset: List
    ) -> OptimizeOutput:
        """
        Generates and applies a critique to improve instruction based on errors
        """
        if len(dataset) > TuneConstant.DEFAULT_TRAIN_DATASET_NUM:
            train_data = random.sample(
                dataset, k=TuneConstant.DEFAULT_TRAIN_DATASET_NUM
            )
        else:
            train_data = dataset

        if not self._candidates:
            self._candidates.append((prompt, self._params.placeholder))

        if not self._evaluator:
            raise JiuWenBaseException(
                StatusCode.PROMPT_OPTIMIZE_REFINE_INSTRUCTION_ERROR.code,
                StatusCode.PROMPT_OPTIMIZE_REFINE_INSTRUCTION_ERROR.errmsg.format(
                    error_msg="Candidates optimization without evaluator"
                ),
            )

        candidate_prompts_with_score = []

        for candidate in self._candidates:
            full_prompt = self._get_full_prompt(candidate[0], candidate[1])
            score, _, _ = self._evaluator.evaluate(
                full_prompt, train_data, self._stop_event
            )
            candidate_prompts_with_score.append((candidate[0], candidate[1], score))
            opt_result = super().do_optimize(candidate[0], bad_cases, train_data)
            prompt_candidate, placeholder_candidate = (
                opt_result.prompt,
                opt_result.placeholder,
            )
            if not prompt_candidate:
                raise JiuWenBaseException(
                    StatusCode.PROMPT_OPTIMIZE_REFINE_INSTRUCTION_ERROR.code,
                    StatusCode.PROMPT_OPTIMIZE_REFINE_INSTRUCTION_ERROR.errmsg.format(
                        error_msg="Get empty model reply"
                    ),
                )
            optimized_full_prompt = self._get_full_prompt(
                prompt_candidate, placeholder_candidate
            )
            score, _, _ = self._evaluator.evaluate(
                optimized_full_prompt, train_data, self._stop_event
            )
            candidate_prompts_with_score.append(
                (prompt_candidate, placeholder_candidate, score)
            )

        # 检查最优提示词是否在候选集中
        is_contain_best_prompt = False
        for candidate in self._candidates:
            if prompt == candidate[0]:
                is_contain_best_prompt = True
                break

        if not is_contain_best_prompt:
            opt_result = super().do_optimize(
                prompt, self._params.placeholder, train_data
            )
            optimized_full_prompt = self._get_full_prompt(
                opt_result.prompt, opt_result.placeholder
            )
            score, _, _ = self._evaluator.evaluate(
                optimized_full_prompt, train_data, self._stop_event
            )
            candidate_prompts_with_score.append(
                (opt_result.prompt, opt_result.placeholder, score)
            )
        self._candidates = sorted(
            candidate_prompts_with_score, key=lambda x: x[2] if x[2] is not None else -1, reverse=True
        )[: TuneConstant.DEFAULT_PROMPT_CANDIDATES_NUM]
        return self._evaluate_topn_candidate(dataset)

    def _evaluate_topn_candidate(self, dataset: List, top_n: int = 2) -> OptimizeOutput:
        n_eval_prompt = min(top_n, len(self._candidates))
        best_score, best_prompt_idx = -1, 0
        best_error_cases = []
        best_evaluations = []
        for i in range(n_eval_prompt):
            candidate = self._candidates[i]
            full_prompt = self._get_full_prompt(candidate[0], candidate[1])
            score, sampled_incorrect_data, evaluations = self._evaluator.evaluate(
                full_prompt, dataset, self._stop_event
            )
            if score is not None and best_score < score:
                best_score = score
                best_prompt_idx = i
                best_error_cases = sampled_incorrect_data
                best_evaluations = evaluations

        best_candidate = self._candidates[best_prompt_idx]
        return OptimizeOutput(
            prompt=best_candidate[0],
            placeholder=best_candidate[1],
            score=best_score,
            error_cases=best_error_cases or [],
            evaluations=best_evaluations or [],
        )


def get_selected_algorithm(algo_name: str, opt_algo_config: OptimizeAlgoConfig):
    """get selected algorithm"""
    algorithm_map = {
        "greedy": GreedyOptimizer,
        "beamsearch": BeamSearchOptimizer,
    }
    algo_name = algo_name.lower().strip()
    logger.info("use {} method optimize the task".format(algo_name))
    func = algorithm_map.get(algo_name)
    if not func:
        raise ValueError(f"Unknown algorithm: {algo_name}")
    return func(opt_algo_config)
