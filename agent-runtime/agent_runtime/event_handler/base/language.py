# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Language manager — i18n错误码消息加载器."""

import os
from typing import Dict, Optional


class LanguageManager:
    """加载并缓存i18n properties文件的错误码消息."""

    _instance: Optional['LanguageManager'] = None
    _cache: Dict[str, Dict[str, str]] = {}

    LANG_MAP = {
        'en-us': 'en_US',
        'en': 'en_US',
        'zh-cn': 'zh_CN',
        'zh': 'zh_CN',
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._resource_dir = os.path.join(
                os.path.dirname(__file__), 'resources', 'i18n'
            )
            self._initialized = True

    @staticmethod
    def _parse_properties(filepath: str) -> Dict[str, str]:
        """解析Java .properties文件为dict."""
        props = {}
        if not os.path.exists(filepath):
            return props

        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, _, value = line.partition('=')
                    props[key.strip()] = value.strip()
        return props

    def _load_language(self, language: str) -> Dict[str, str]:
        """加载指定语言的properties文件."""
        lang_key = self.LANG_MAP.get(language.lower(), language)
        if lang_key in self._cache:
            return self._cache[lang_key]

        filename = f'runtime-msg_{lang_key}.properties'
        filepath = os.path.join(self._resource_dir, filename)
        props = self._parse_properties(filepath)
        self._cache[lang_key] = props
        return props

    def get_error_context(self, language: str, code: int) -> tuple[str, str, str]:
        """根据语言和错误码查询 (error_msg, error_reason, error_suggestion).

        Args:
            language: 语言代码，如 "en-us", "zh-cn"
            code: 数字错误码

        Returns:
            (error_msg, error_reason, error_suggestion) 三元组
        """
        props = self._load_language(language)
        code_str = str(code)

        error_msg = props.get(code_str, f'Error {code}')
        error_reason = props.get(f'{code_str}.reason', 'Internal error')
        error_suggestion = props.get(f'{code_str}.suggestion', 'Please try again later')

        return error_msg, error_reason, error_suggestion
