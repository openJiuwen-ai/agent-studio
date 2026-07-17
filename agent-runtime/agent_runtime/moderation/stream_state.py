# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""流式审核状态机 — 处理跨 chunk 边界的敏感词匹配。"""

from typing import Tuple, Union

from agent_runtime.moderation.engine import ActionType, ModerationEngineDynamicAC


class StreamModeratorState:
    """独立的流式风控状态机，用于处理单条文本流（如 think 或 answer）"""

    def __init__(self, engine: ModerationEngineDynamicAC):
        self.engine = engine
        self.buffer = ""
        self.is_interrupted = False

    def process_chunk(self, chunk: Union[str, list, dict, None]) -> Tuple[str, str]:
        """处理传入的流式切片。

        Args:
            chunk: 文本切片，支持 str / list / dict / None

        Returns:
            (safe_text, interrupt_text) — safe_text 为可安全放行的文本，
            interrupt_text 非空时表示命中 REPLY 阻断。
        """
        if isinstance(chunk, list):
            chunk = "".join(
                [str(c.get("content", c)) if isinstance(c, dict) else str(c) for c in chunk]
            )
        elif isinstance(chunk, dict):
            chunk = str(chunk.get("content", "") or chunk.get("answer", ""))
        elif not isinstance(chunk, str):
            chunk = str(chunk) if chunk is not None else ""

        if not chunk or not self.engine.enabled or not self.engine.has_output_rules:
            return chunk, ""

        self.buffer += chunk

        max_iterations = len(self.buffer) + 1  # 防止替换文本自身再触发匹配导致无限循环

        for _ in range(max_iterations):
            matches = list(self.engine.output_ac.iter(self.buffer))
            if not matches:
                break

            # 排序：优先级最高优先，词长最长优先
            matches.sort(key=lambda x: (x[1][0], len(x[1][3])), reverse=True)
            best_match = matches[0]
            end_idx = best_match[0]
            priority, action, target_text, original_word = best_match[1]
            start_idx = end_idx - len(original_word) + 1

            if action == ActionType.REPLY:
                self.is_interrupted = True
                interrupt_text = target_text
                self.buffer = ""
                return "", interrupt_text
            elif action in (ActionType.REPLACE, ActionType.FILTER):
                self.buffer = self.buffer[:start_idx] + target_text + self.buffer[end_idx + 1:]

        # buffer 尾部 max_kw_len 范围内检查前缀嫌疑
        max_len = getattr(self.engine, "max_kw_len", 20)
        start_search_idx = max(0, len(self.buffer) - max_len)

        safe_idx = len(self.buffer)  # 默认全部安全

        for i in range(start_search_idx, len(self.buffer)):
            suffix = self.buffer[i:]
            try:
                next(self.engine.output_ac.keys(suffix))
                safe_idx = i  # 找到前缀嫌疑，i 之前才是安全的
                break
            except (KeyError, StopIteration):
                continue

        safe_text = self.buffer[:safe_idx]
        self.buffer = self.buffer[safe_idx:]

        return safe_text, ""

    def flush(self) -> str:
        """流结束时，强制吐出 buffer 中残留的安全碎片。"""
        res = self.buffer
        self.buffer = ""
        return res

    def clean_full_text(self, text: str) -> str:
        """非流式场景全量清洗。

        Returns:
            清洗后的文本（REPLY 阻断时返回兜底话术）。
        """
        if not text or not self.engine.enabled or not self.engine.has_output_rules:
            return text

        result_text = str(text)

        max_iterations = len(text) + 1  # 防止替换文本自身再触发匹配导致无限循环

        for _ in range(max_iterations):
            matches = list(self.engine.output_ac.iter(result_text))
            if not matches:
                break

            matches.sort(key=lambda x: (x[1][0], len(x[1][3])), reverse=True)
            best_match = matches[0]
            end_idx = best_match[0]
            priority, action, target_text, original_word = best_match[1]
            start_idx = end_idx - len(original_word) + 1

            if action == ActionType.REPLY:
                self.is_interrupted = True
                return target_text
            elif action in (ActionType.REPLACE, ActionType.FILTER):
                result_text = result_text[:start_idx] + target_text + result_text[end_idx + 1:]

        return result_text
