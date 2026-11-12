#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Knowledge Retrieval component converter.

Converts frontend Knowledge Retrieval node data into DSL Component format.
"""

from openjiuwen_studio.core.common import dsl
from openjiuwen_studio.core.common.dsl import ComponentType
from openjiuwen_studio.core.manager.convertor.components.llm import build_dsl_model_config
from openjiuwen_studio.core.manager.convertor.components.common import (
    outputs_convert,
    input_params_convert,
)
from openjiuwen_studio.schemas.node import Node


def knowledge_retrieval_convert(node: Node, space_id: str) -> dsl.Component:
    """Convert a Knowledge Retrieval frontend node into a DSL Component.

    Args:
        node: The frontend node containing knowledge retrieval configuration.
        space_id: The workspace ID for multi-tenant isolation.

    Returns:
        A DSL Component with type COMPONENT_TYPE_KNOWLEDGE_RETRIEVAL.
    """
    try:
        data = node.data
        inputs = data.inputs
        if inputs is None:
            raise ValueError("knowledge_retrieval_convert inputs is none")

        input_parameters = inputs.input_parameters
        if input_parameters is None:
            raise ValueError("knowledge_retrieval_convert input_parameters is empty")

        converted_inputs = input_params_convert(input_parameters)

        data_outputs = data.outputs
        if data_outputs is None:
            raise ValueError("knowledge_retrieval_convert outputs is none")
        converted_outputs = outputs_convert(data_outputs)

        # Extract knowledge retrieval params
        kr_param = inputs.knowledge_retrieval_param
        if kr_param is None:
            raise ValueError("knowledge_retrieval_param is none")

        # Build retrieval config
        # min_match_score=0 是合法配置（不过滤低分结果），不能用 or 兜底，
        # 否则 0 会被静默覆盖成 0.5 导致召回结果被错误过滤。
        score_threshold = (
            kr_param.min_match_score
            if kr_param.min_match_score is not None
            else 0.5
        )
        retrieval_config = {
            "top_k": kr_param.max_recall_count or 5,
            "score_threshold": score_threshold,
            "use_graph": kr_param.use_graph or False,
            "agentic": kr_param.agentic or False,
        }

        if retrieval_config["agentic"]:
            llm_params = inputs.llm_param
            if llm_params is None:
                raise ValueError("llm_param is none")

            model = build_dsl_model_config(int(llm_params.model.id), space_id)
            kr_configs = dsl.KnowledgeRetrievalConfig(
                kb_ids=kr_param.kb_ids or [],
                retrieval_config=retrieval_config,
                model=model,
            )
        else:
            kr_configs = dsl.KnowledgeRetrievalConfig(
                kb_ids=kr_param.kb_ids or [],
                retrieval_config=retrieval_config,
            )

        # Build the component
        kr_component = dsl.Component(
            id=getattr(node, 'id', ""),
            type=ComponentType.COMPONENT_TYPE_KNOWLEDGE_RETRIEVAL,
            type_version="1.0.0",
            inputs=converted_inputs,
            outputs=converted_outputs,
            configs=kr_configs.model_dump(),
            name=data.title,
        )
        return kr_component
    except Exception as e:
        raise RuntimeError(f"Failed to convert Knowledge Retrieval node: {str(e)}") from e
