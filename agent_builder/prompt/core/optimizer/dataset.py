# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""
dataset.py
"""

from typing import Any, Dict, Union, List, TypedDict


class BaseCaseData(TypedDict):
    """
    A dictionary class representing the structure of case datas.
    """

    input: Union[str, List[Dict[str, Any]]]
    label: Union[str, Dict[str, Any]]
