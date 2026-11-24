#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Any

from jiuwen.orchestration.flow.enum import NodeType
from jiuwen.orchestration.utils import Output, Input

from .base_parser import BaseParser
from ..cache.factory import CacheFactory
from ..utils import get_runtime_memory_key_ids


class SubWorkflowNodeParser(BaseParser):
    @classmethod
    def pre_parse(cls, inputs: Input, *args: Any, **kwargs: Any):
        _, workflow_id, user_id, execution_id = get_runtime_memory_key_ids(**kwargs)
        if not (workflow_id and user_id and execution_id):
            return []

        workflow_id_list = CacheFactory.get_call_workflow_cache().get_all(execution_id)
        if not workflow_id_list:
            CacheFactory.get_call_workflow_cache().save(execution_id, workflow_id)
        sub_workflow_id = (
            kwargs.get("component_metadata", {})
            .get("component_config", {})
            .get("reference", {})
            .get("id")
        )
        if sub_workflow_id:
            CacheFactory.get_call_workflow_cache().save(execution_id, sub_workflow_id)
        return []

    @classmethod
    def post_parse(cls, outputs: Output, *args: Any, **kwargs: Any):
        _, _, user_id, execution_id = get_runtime_memory_key_ids(**kwargs)
        if not (user_id and execution_id):
            return []
        workflow_id_list = CacheFactory.get_call_workflow_cache().get_all(execution_id)
        sub_workflow_id = (
            kwargs.get("component_metadata", {})
            .get("component_config", {})
            .get("reference", {})
            .get("id")
        )
        if (
            sub_workflow_id
            and workflow_id_list
            and sub_workflow_id == workflow_id_list[-1]
        ):
            CacheFactory.get_call_workflow_cache().pop(execution_id)
        return []

    @classmethod
    def get_type(cls):
        return NodeType.SUB_WORKFLOW.value
