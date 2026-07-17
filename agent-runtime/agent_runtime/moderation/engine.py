# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""动态 AC 自动机风控引擎 — 基于 pyahocorasick，支持输入/输出双通道审核。"""

import time
from typing import Any, Dict, Tuple

import ahocorasick


class ActionType:
    """审核动作类型"""
    FILTER = 1
    REPLACE = 2
    REPLY = 3


class ModerationEngineDynamicAC:
    """动态 AC 自动机风控引擎

    支持输入侧 (input_ac) 和输出侧 (output_ac) 独立的两套 AC 自动机。
    三种动作：FILTER（过滤/删除）、REPLACE（替换）、REPLY（阻断并返回兜底话术）。
    """

    def __init__(self, config: Dict[str, Any]):
        self.enabled = config.get("enabled", False)

        # 输入和输出独立的两套 AC 自动机
        self.input_ac = ahocorasick.Automaton()
        self.output_ac = ahocorasick.Automaton()

        self._has_input_rules = False
        self._has_output_rules = False

        # 记录词库中最长的敏感词长度（用于流式 buffer 管理）
        self.max_kw_len = 0

        self._build_automata(config)

    @property
    def has_output_rules(self) -> bool:
        """是否有输出侧审核规则。"""
        return self._has_output_rules

    @property
    def has_input_rules(self) -> bool:
        """是否有输入侧审核规则。"""
        return self._has_input_rules

    def _build_automata(self, config: Dict[str, Any]):
        """解析规则格式，构建 AC 自动机。

        Payload 格式：(priority: int, action: int, target_text: str, original_word: str)
        优先级：reply(3) > replace(2) > filter(1)
        """
        type_map = {
            "reply": (3, ActionType.REPLY),
            "replace": (2, ActionType.REPLACE),
            "filter": (1, ActionType.FILTER),
        }

        def add_to_output(word: str, payload: tuple):
            if not word:
                return
            self.output_ac.add_word(word, payload)
            self._has_output_rules = True
            self.max_kw_len = max(self.max_kw_len, len(word))

        def add_to_input(word: str, payload: tuple):
            if not word:
                return
            self.input_ac.add_word(word, payload)
            self._has_input_rules = True
            self.max_kw_len = max(self.max_kw_len, len(word))

        for rule in config.get("rules", []):
            keywords = rule.get("keywords", [])
            if not keywords:
                continue

            actions = rule.get("actions", {})

            for word in keywords:
                if not word:
                    continue

                # 输入侧
                input_cfg = actions.get("input")
                if input_cfg and str(input_cfg.get("enable")).lower() == "true":
                    action_type_str = input_cfg.get("type")
                    priority, action_enum = type_map.get(action_type_str, (1, ActionType.FILTER))
                    add_to_input(word, (priority, action_enum, input_cfg.get("content", ""), word))

                # 输出侧
                output_cfg = actions.get("output")
                if output_cfg and str(output_cfg.get("enable")).lower() == "true":
                    action_type_str = output_cfg.get("type")
                    priority, action_enum = type_map.get(action_type_str, (1, ActionType.FILTER))
                    content = output_cfg.get("content", "")
                    add_to_output(word, (priority, action_enum, content, word))

        if self._has_input_rules:
            self.input_ac.make_automaton()
        if self._has_output_rules:
            self.output_ac.make_automaton()

    def check_input_query(self, text: str) -> Tuple[bool, str]:
        """输入同步检查（阻塞式）。

        Returns:
            (is_safe, text_or_fallback) — 安全时 is_safe=True，命中 REPLY 阻断时
            is_safe=False 并返回兜底话术。
        """
        if not self.enabled or not self._has_input_rules:
            return True, text

        matches = list(self.input_ac.iter(text))
        if matches:
            matches.sort(key=lambda x: (x[1][0], len(x[1][3])), reverse=True)
            _priority, action, target_text, _original_word = matches[0][1]
            if action == ActionType.REPLY:
                return False, target_text

        return True, text

    @staticmethod
    def build_sensitive_event(fallback_msg: str, original_created_time: int = None) -> Dict[str, Any]:
        """构建风控阻断时的 sensitive 事件。"""
        ts = original_created_time or int(time.time() * 1000)
        return {
            "event": "sensitive",
            "data": {
                "text": fallback_msg,
                "createdTime": ts,
                "offset": 0,
            },
            "createdTime": ts,
        }

    def clean_full_text(self, text: str) -> Tuple[bool, str]:
        """非流式场景全量清洗输出。

        Returns:
            (is_interrupted, result_text) — REPLY 阻断时 is_interrupted=True，
            REPLACE/FILTER 时为 False 并返回清洗后文本。
        """
        if not text or not self.enabled or not self._has_output_rules:
            return False, text

        result_text = str(text)
        max_iterations = len(text) + 1  # 防止替换文本自身再触发匹配导致无限循环

        for _ in range(max_iterations):
            matches = list(self.output_ac.iter(result_text))
            if not matches:
                break

            matches.sort(key=lambda x: (x[1][0], len(x[1][3])), reverse=True)
            best_match = matches[0]
            end_idx = best_match[0]
            priority, action, target_text, original_word = best_match[1]
            start_idx = end_idx - len(original_word) + 1

            if action == ActionType.REPLY:
                return True, target_text
            elif action in (ActionType.REPLACE, ActionType.FILTER):
                result_text = result_text[:start_idx] + target_text + result_text[end_idx + 1:]

        return False, result_text
