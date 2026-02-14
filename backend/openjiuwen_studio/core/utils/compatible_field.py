#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

def compatible_provider(key: str) -> str:
    maps = {
        "openai": "OpenAI",
        "siliconflow": "SiliconFlow"
    }
    if key in maps:
        return maps.get(key)
    return key


def mask_fields(v: str) -> str:
    return "***REDACTED***" + v[-4:] if len(v) >= 4 else "***REDACTED***" + v


def mask_sensitive_fields(objs):
    sensitive_key = ["key", "api_key", "access_token", "refresh_token", "authorization", "cookie", "secret", "password"]

    def _mask(objs):
        if isinstance(objs, dict):
            return {
                k: _mask(v) if k not in sensitive_key else mask_fields(v)
                for k, v in objs.items()
            }
        elif isinstance(objs, (list, tuple)):
            return type(objs)(_mask(item) for item in objs)
        else:
            return objs
    return _mask(objs)
