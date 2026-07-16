#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
"""
embedding
"""

from __future__ import annotations

from abc import ABC

from pydantic import Field, BaseModel


class Document(BaseModel, ABC):
    """Class for storing a piece of text and associated metadata.

    Args:
        page_content (str): main content of the document.
        metadata (dict, optional): arbitrary metadta associated with the document. Default: ``{}``.
    """

    page_content: str = Field(default="")
    metadata: dict = Field(default={})
