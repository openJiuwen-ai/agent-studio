#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""
Thread-Local Context Module

Provides thread-local storage for request-scoped context variables.
This module manages context that needs to be accessed across the call chain
without explicit parameter passing.
"""
import threading
from typing import Optional

_thread_local = threading.local()


def get_highest_priority_language(accept_language: str) -> list:
    """
    Parse Accept-Language header and return languages sorted by q-value (priority).

    Args:
        accept_language: Accept-Language header string (e.g., "zh-CN,zh;q=0.9,en;q=0.6")

    Returns:
        List of language codes sorted by priority (highest q-value first)

    Note:
        Languages before a q-value specifier share that q-value.
        Example: "zh-CN,zh;q=0.9,en;q=0.6" means both zh-CN and zh have q=0.9
    """
    if not accept_language:
        return []

    language_prefs = []
    accumulated_languages = []
    default_q = 1.0

    segments = accept_language.split(';')

    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue

        if segment.lower().startswith('q='):
            q_str = segment[2:].strip()
            if q_str:
                try:
                    parsed_q = float(q_str)
                    if 0.0 <= parsed_q <= 1.0:
                        for lang in accumulated_languages:
                            language_prefs.append((lang.lower(), parsed_q))
                        accumulated_languages = []
                        default_q = parsed_q
                except ValueError:
                    pass
        else:
            languages = [lang.strip() for lang in segment.split(',') if lang.strip()]
            accumulated_languages.extend(languages)

    for lang in accumulated_languages:
        language_prefs.append((lang.lower(), default_q))

    language_prefs.sort(key=lambda x: x[1], reverse=True)

    return [lang_code for lang_code, q_value in language_prefs]


def set_language(language: str) -> None:
    """
    Set the current request's language in thread-local storage.

    Args:
        language: Language code (e.g., 'cn', 'en')
    """
    _thread_local.language = language


def get_language() -> str:
    """
    Get the current request's language from thread-local storage.

    Returns:
        str: Language code, defaults to 'cn' if not set
    """
    return getattr(_thread_local, 'language', 'cn')


def clear_language() -> None:
    """
    Clear the language from thread-local storage.
    Typically called at the end of a request lifecycle.
    """
    try:
        delattr(_thread_local, 'language')
    except AttributeError:
        pass
