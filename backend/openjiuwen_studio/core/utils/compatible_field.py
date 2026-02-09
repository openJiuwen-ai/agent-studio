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
