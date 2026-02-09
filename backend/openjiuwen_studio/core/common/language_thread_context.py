#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""
Thread-Local Context Module

Provides context-local storage for request-scoped context variables.
This module manages context that needs to be accessed across the call chain
without explicit parameter passing.
"""
import contextvars
from typing import Optional

# 使用 contextvars 替代 threading.local 以支持异步环境
_language_context = contextvars.ContextVar("language", default="cn")


def get_highest_priority_language(accept_language: str) -> list:
    """
    Parse Accept-Language header and return languages sorted by q-value (priority).

    Args:
        accept_language: Accept-Language header string (e.g., "zh-CN,zh;q=0.9,en;q=0.6")

    Returns:
        List of language codes sorted by priority (highest q-value first)
    """
    if not accept_language:
        return []

    language_prefs = []
    
    # Split by comma to get individual language ranges
    parts = [p.strip() for p in accept_language.split(',') if p.strip()]
    
    for part in parts:
        # Each part might contain parameters separated by semicolons
        subparts = [sp.strip() for sp in part.split(';')]
        if not subparts:
            continue
            
        lang = subparts[0]
        q_value = 1.0
        
        # Parse parameters to find q-value
        for param in subparts[1:]:
            if param.lower().startswith('q='):
                try:
                    q_str = param[2:].strip()
                    if q_str:
                        q_value = float(q_str)
                except ValueError:
                    pass
        
        language_prefs.append((lang.lower(), q_value))

    # Sort by q-value descending
    language_prefs.sort(key=lambda x: x[1], reverse=True)

    return [lang_code for lang_code, q_value in language_prefs]


def set_language(language: str) -> None:
    """
    Set the current request's language in context storage.

    Args:
        language: Language code (e.g., 'cn', 'en')
    """
    _language_context.set(language)


def get_language() -> str:
    """
    Get the current request's language from context storage.

    Returns:
        str: Language code, defaults to 'cn' if not set
    """
    return _language_context.get()


def clear_language() -> None:
    """
    Reset the language context to default.
    Typically called at the end of a request lifecycle.
    Note: In contextvars, we usually just let the context exit scope, 
    but for compatibility we reset it to default.
    """
    _language_context.set("cn")
