# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""
agent builder chain Template optimizer
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any

from agent_builder.prompt.mmapo.utils import JNT_MODE


class BaseContextStoreAccesser(ABC):
    """Context store accesser base class definition"""

    def __init__(self):
        pass

    @abstractmethod
    def store_context_ids(self, ctx_ids: List[str]):
        """save context ids to store
        Args:
            ctx_ids: context uid
        """

    @abstractmethod
    def store_context(self, ctx_id: str, context: Dict[str, Any]):
        """save context to store
        Args:
            ctx_id: context uid
            context: optimizer context
        """

    @abstractmethod
    def load_context(
        self, ctx_id: str, load_all: bool = False, mode: str = JNT_MODE
    ) -> Dict[str, Any]:
        """load context from store
        Args:
            ctx_id: context uid
            load_all: load all context
            mode: joint or mmapo mode
        Returns:
            optimizer context
        """

    @abstractmethod
    def delete_context(self, ctx_id: str):
        """delete context from store
        Args:
            ctx_id: context uid
        """

    @abstractmethod
    def get_context_attr(self, ctx_id: str, attr_name: str, **kwargs) -> Any:
        """query context attribute from store
        Args:
            ctx_id: context uid
            attr_name: context attribute name
        """

    @abstractmethod
    def set_context_attr(self, ctx_id: str, attr_name: str, attr_value: Any, **kwargs):
        """update context attribute from store
        Args:
            ctx_id: context uid
            attr_name: context attribute name
            attr_value: context attribute value
        """
