#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
"""llm service"""

from typing import Dict, Any, Tuple

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.ops.config import ModelConfigManager
from openjiuwen_studio.ops.modules.llm.model import ModelConfig, ListModelResponse
from openjiuwen_studio.ops.modules.llm.schema import ListModelRequest
from openjiuwen_studio.ops.modules.prompt.domain.repositories import AgentRepository
from openjiuwen_studio.ops.modules.prompt.infra.repositories import orm_repo
from openjiuwen_studio.core.utils.compatible_field import mask_fields


class LLMService:
    """llm service"""

    def __init__(self, model_config_manager: ModelConfigManager, agent_repo: AgentRepository, ):
        self.model_config_manager = model_config_manager
        self.agent_repo = agent_repo

    async def get_model(self, model_id: str, source: str) -> Dict[str, Any]:
        """
        获取单个模型信息
        """
        logger.info(f"get model called with model_id{model_id}")

        if source == "config":
            model_config = self.model_config_manager.get_model_config(model_id)
            if not model_config:
                logger.error(f"Model with id {model_id} not found")
                raise ValueError(f"Model with id {model_id} not found")
            model_config["protocol_config"] = {}
            # 将字典转换为 ModelConfig 对象
            model_config_obj = ModelConfig(**model_config)
        else:
            try:
                model_config = self.agent_repo.find_model_config_by_modelid(model_id, orm_repo.ModelConfig)
                model_config_obj = convert_orm_to_model_config(model_config)
            except Exception as e:
                logger.error(f"Query Model Config from DB {model_id} failed: {e}")
                raise ValueError(f"Model with id {model_id} not found") from e

        logger.info(f"Model retrieved: {model_config_obj}")

        return {
            "msg": "success",
            "code": 0,
            "model": model_config_obj
        }

    def get_llm_model_info(self, model_id: str, source: str) -> Tuple[str, str]:
        """
        获取单个模型信息
        """
        logger.info(f"get model called with model_id{model_id}")
        base_url = ""
        api_key = ""

        if source == "config":
            model_config = self.model_config_manager.get_model_config(model_id)
            if not model_config:
                logger.error(f"Model with id {model_id} not found")
                raise ValueError(f"Model with id {model_id} not found")

            base_url = model_config.get("protocol_config", {}).get("base_url", "")
            api_key = model_config.get("protocol_config", {}).get("api_key", "")
        else:
            try:
                model_config = self.agent_repo.find_model_config_by_modelid(model_id, orm_repo.ModelConfig)
                base_url = model_config.base_url
                api_key = model_config.api_key
            except Exception as e:
                logger.error(f"Query Model Config from DB {model_id} failed: {e}")
                raise ValueError(f"Model with id {model_id} not found") from e

        logger.info(f"base_url: {base_url}, api_key: {mask_fields(api_key)}")
        return base_url, api_key

    async def list_models(
            self,
            request: ListModelRequest
    ) -> ListModelResponse:
        """
        获取所有可用模型列表
        :param request:
        :return:
        """
        logger.info(f"list models called with request {request}")

        # 配置文件中获取模型配置
        models = self.model_config_manager.list_models()
        # 将字典列表转换为 ModelConfig 对象列表
        model_objects = [ModelConfig(**model) for model in models]

        # 从studio库中获取模型配置
        try:
            models_db = self.agent_repo.find_model_config_by_spaceid(request.workspace_id, orm_repo.ModelConfig)
            if models_db is None:
                models_db = []
            for model_db in models_db:
                model_db_res = convert_orm_to_model_config(model_db)
                model_objects.append(model_db_res)

        except Exception as e:
            logger.warning(f"Query Model Config from DB failed: {e}")

        # 模拟分页逻辑
        start_index = int(request.page_token) * request.page_size
        end_index = start_index + request.page_size
        paginated_models = model_objects[start_index:end_index]
        next_page_token = str(int(request.page_token) + 1) if end_index < len(model_objects) else "0"
        has_more = next_page_token != "0"

        response = ListModelResponse(
            msg="success",
            code=0,
            has_more=has_more,
            models=paginated_models,
            next_page_token=next_page_token,
            total=len(model_objects),
        )
        logger.info(f"Model retrieved: {response}")
        return response


def convert_orm_to_model_config(orm_obj) -> ModelConfig:
    """
    转换数据为ModelConfig
    """
    # 解析 tags
    tags = orm_obj.tags or []

    # 构建 series
    series = {
        "icon": "",
        "name": orm_obj.provider,
        "vendor": orm_obj.provider
    }

    parameters = orm_obj.parameters or {}

    # 构建 param_schemas
    param_schemas = [
        {
            "name": "temperature",
            "label": "温度",
            "desc": "temperature:控制模型生成结果的随机性与创造性。值越高，输出越随机、多样；值越低，结果越确定、保守。范围通常为0~2，推荐设置0.1~1.0。示例：0.7（平衡随机性与一致性）、1.2（更具创造性的输出）。",
            "type": "float",
            "min": "0",
            "max": "2.0",
            "default_val": str(parameters.get("temperature", 0.7))
        },
        {
            "name": "max_tokens",
            "label": "最大回复长度",
            "desc": "限制模型在单次生成中输出的最大标记数。控制生成文本的长度，防止输出过长或消耗过多资源。建议：根据实际需求设置，避免设置过小导致输出被截断。",
            "type": "int",
            "min": "1",
            "max": "4096",
            "default_val": str(parameters.get("max_tokens", 2048))
        },
        {
            "name": "top_p",
            "label": "核采样",
            "desc": "Top-p:选择累计概率达到p的最小词集合进行采样。动态调整候选词的数量，平衡输出的多样性和质量。建议：通常设置为0.9-0.95，与温度配合使用时建议只调整其中一个。",
            "type": "float",
            "min": "0.001",
            "max": "1.0",
            "default_val": str(parameters.get("top_p", 0.7))
        }
    ]

    # 构建 openModel
    open_model = {
        "workspace_id": orm_obj.space_id,
        "desc": orm_obj.description or "",
        "name": orm_obj.name,
        "model_id": str(orm_obj.id),
        "param_config": {
            "param_schemas": param_schemas
        }
    }

    # 创建并返回目标对象
    return ModelConfig(
        tags=tags,
        icon="",
        openModel=open_model,
        series=series,
        model_from="db"
    )
