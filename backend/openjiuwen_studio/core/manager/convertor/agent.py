#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import json
import time
from typing import List, Any, Optional

from fastapi import status
from openjiuwen.core.common.logging import logger
from openjiuwen.core.foundation.llm import BaseModelInfo
from openjiuwen_studio.core.common.language_thread_context import get_language
from openjiuwen_studio.core.common.agent_defaults import AgentDefaults

from openjiuwen_studio.core.common import dsl
from openjiuwen_studio.core.common.dsl import AgentType, ConstrainConfig, ModelConfig, ModelClientConfig, \
    ModelRequestConfig, KBRetrievalConfig
from openjiuwen_studio.core.manager.internal.agent import AgentWorkflowListNodeBase
from openjiuwen_studio.core.manager.model_manager.utils import SecurityUtils
from openjiuwen_studio.core.manager.repositories.tool_repository import tool_repository
from openjiuwen_studio.core.manager.repositories.workflow_repository import workflow_repository
from openjiuwen_studio.core.manager.repositories.knowledge_base_repository import knowledge_base_repository
from openjiuwen_studio.core.manager.utils.utils import convert_to_properties_format
from openjiuwen_studio.models.agent import AgentBaseDBPd
from openjiuwen_studio.schemas import ResponseModel, WorkflowBase
from openjiuwen_studio.schemas.agent import AgentPlugin
from openjiuwen_studio.schemas.plugin import PluginToolId
from openjiuwen_studio.schemas.workflow import WorkflowId
from openjiuwen_studio.schemas.knowledge_base import KnowledgeBaseGet
from openjiuwen_studio.core.manager.knowledge_base import _CURR_INDEX_TYPE


def workflow_convert(space_id: str, workflow: AgentWorkflowListNodeBase):
    """Convert single workflow to DSL format"""
    try:
        workflow_query = WorkflowId(
            workflow_id=workflow.workflow_id,
            space_id=space_id,
            workflow_version=workflow.workflow_version
        )

        canvas_result = workflow_repository.workflow_canvas(workflow_query)

        if canvas_result.code != status.HTTP_200_OK:
            logger.error(
                f"[AGENT_CONVERT] Failed to fetch workflow - ID: {workflow.workflow_id}, Error: {canvas_result.message}")
            return False

        workflow_info = WorkflowBase(**canvas_result.data)
        input_parameters = workflow_info.input_parameters
        output_parameters = workflow_info.output_parameters

        input_properties, input_requires = convert_to_properties_format(input_parameters)
        inputs = {
            "type": "object",
            "properties": input_properties,
            "required": input_requires
        }

        output_properties, output_requires = convert_to_properties_format(output_parameters)

        return inputs, output_properties

    except Exception as e:
        logger.error(f"[AGENT_CONVERT] Workflow conversion failed - ID: {workflow.workflow_id}, Error: {e}")
        return False


def workflows_convert(space_id: str, workflows: List[dict[str, Any]]):
    """Convert workflows list to DSL format"""
    if not workflows:
        return []

    workflows_dsl: list[dsl.WorkflowSchema] = []
    successful_conversions = 0
    failed_conversions = 0

    try:
        for w in workflows:
            try:
                node = AgentWorkflowListNodeBase(**w)
                inputs, outputs = workflow_convert(space_id, node)

                if inputs is False or outputs is False:
                    failed_conversions += 1
                    continue

                workflow_dsl = dsl.WorkflowSchema(
                    id=node.workflow_id,
                    version=node.workflow_version,
                    name=node.workflow_name,
                    description=node.description,
                    inputs=inputs,
                    outputs=outputs,
                    configs={}
                )

                workflows_dsl.append(workflow_dsl)
                successful_conversions += 1

            except Exception as e:
                logger.error(
                    f"[AGENT_CONVERT_WORKFLOWS] Failed to convert workflow - ID: {w.get('workflow_id', 'unknown')}, Error: {e}")
                failed_conversions += 1
                continue

        if failed_conversions > 0:
            logger.warning(
                f"[AGENT_CONVERT_WORKFLOWS] Conversion completed - SpaceID: {space_id}, "
                f"Success: {successful_conversions}, Failed: {failed_conversions}, Total: {len(workflows)}"
            )

        return workflows_dsl

    except Exception as e:
        logger.error(f"[AGENT_CONVERT_WORKFLOWS] Bulk conversion failed - SpaceID: {space_id}, Error: {e}")
        raise ValueError(f"Failed to convert workflows: {e}") from e


def agent_plugin_convert(space_id: str, plugin: AgentPlugin) -> dsl.PluginSchema:
    """Convert single plugin to DSL format"""
    try:
        tool_id = PluginToolId(
            plugin_id=plugin.plugin_id,
            tool_id=plugin.tool_id,
            space_id=space_id,
            plugin_version=plugin.plugin_version,
        )

        res, _ = tool_repository.tool_get(tool_id.model_dump())
        get_result = ResponseModel(**res)

        if get_result.code != status.HTTP_200_OK:
            logger.error(
                f"[AGENT_CONVERT_PLUGIN] Failed to fetch plugin tool - ToolID: {plugin.tool_id}, "
                f"Error: {get_result.message}"
            )
            raise ValueError(
                f"get plugin tool info with id {plugin.tool_id} from db failed, error: {get_result.message}")

        tool_info = get_result.data
        input_parameters = tool_info.input_parameters
        output_parameters = tool_info.output_parameters

        input_properties, input_requires = convert_to_properties_format(input_parameters)
        inputs = {
            "type": "object",
            "properties": input_properties,
            "required": input_requires
        }

        output_properties, output_requires = convert_to_properties_format(output_parameters)

        plugin_schema = dsl.PluginSchema(
            id=plugin.tool_id,
            plugin_id=plugin.plugin_id,
            version=plugin.plugin_version,
            name=plugin.tool_name,
            description=tool_info.desc,
            inputs=inputs,
            outputs=output_properties,
            configs={}
        )

        return plugin_schema

    except Exception as e:
        logger.error(
            f"[AGENT_CONVERT_PLUGIN] Conversion failed - PluginID: {plugin.plugin_id}, "
            f"ToolID: {plugin.tool_id}, Error: {e}"
        )
        raise ValueError(f"Failed to convert plugin {plugin.tool_id}: {e}")


def agent_plugins_convert(space_id: str, plugins: List[AgentPlugin]) -> List[dsl.PluginSchema]:
    """Convert plugins list to DSL format"""
    if not plugins:
        return []

    convert_plugins: List[dsl.PluginSchema] = []
    successful_conversions = 0
    failed_conversions = 0

    try:
        for plugin in plugins:
            try:
                convert_plugin = agent_plugin_convert(space_id, plugin)
                convert_plugins.append(convert_plugin)
                successful_conversions += 1
            except Exception as e:
                logger.error(
                    f"[AGENT_CONVERT_PLUGINS] Failed to convert plugin - PluginID: {plugin.plugin_id}, ToolID: {plugin.tool_id}, Error: {e}")
                failed_conversions += 1
                continue

        if failed_conversions > 0:
            logger.warning(
                f"[AGENT_CONVERT_PLUGINS] Conversion completed - SpaceID: {space_id}, "
                f"Success: {successful_conversions}, Failed: {failed_conversions}, Total: {len(plugins)}"
            )

        return convert_plugins

    except Exception as e:
        logger.error(f"[AGENT_CONVERT_PLUGINS] Bulk conversion failed - SpaceID: {space_id}, Error: {e}")
        raise ValueError(f"Failed to convert plugins: {e}") from e


def knowledge_convert(space_id: str, knowledgeid: str) -> dsl.KnowledgeSchema:
    try:
        knowledge_id = KnowledgeBaseGet(
            space_id=space_id,
            kb_id=knowledgeid,
            index_manager_type=_CURR_INDEX_TYPE,
        )

        get_result = knowledge_base_repository.knowledge_base_get(knowledge_id)

        if get_result.code != status.HTTP_200_OK:
            logger.error(
                f"[AGENT_CONVERT_KNOWLEDGE] Failed to fetch knowledge - knowledgeID: {knowledgeid}, Error: {get_result.message}")
            raise ValueError(
                f"[AGENT_CONVERT_KNOWLEDGE] Failed to fetch knowledge - knowledgeID: {knowledgeid}, error: {get_result.message}")

        knowledge_info = get_result.data
        logger.warning(f"knowledge_convert knowledge_info: {knowledge_info}")

        knowledge_schema = dsl.KnowledgeSchema(
            id=knowledge_info.get('kb_id', None),
            version="",
            name=knowledge_info.get('name', None),
            description=knowledge_info.get('description', None),
        )
        return knowledge_schema

    except Exception as e:
        logger.error(
            f"[AGENT_CONVERT_KNOWLEDGE] Conversion failed - knowledgeID: {knowledgeid}, Error: {e}")
        raise ValueError(f"Failed to convert knowledge {knowledgeid}: {e}") from e


def knowledges_convert(space_id: str, knowledges: List[str]):
    """Convert workflows list to DSL format"""
    if not knowledges:
        return []

    convert_knowledges: List[dsl.KnowledgeSchema] = []
    successful_conversions = 0
    failed_conversions = 0

    try:
        for kid in knowledges:
            try:
                convert_knowledge = knowledge_convert(space_id, kid)
                convert_knowledges.append(convert_knowledge)
                successful_conversions += 1
            except Exception as e:
                logger.error(
                    f"[AGENT_CONVERT_KNOWLEDGE] Failed to convert knowledge - Knowledge ID: {kid}, Error: {e}")
                failed_conversions += 1
                continue

        if failed_conversions > 0:
            logger.warning(
                f"[AGENT_CONVERT_KNOWLEDGE] Conversion completed - SpaceID: {space_id}, "
                f"Success: {successful_conversions}, Failed: {failed_conversions}, Total: {len(knowledges)}"
            )

        return convert_knowledges

    except Exception as e:
        logger.error(f"[AGENT_CONVERT_KNOWLEDGE] Bulk conversion failed - SpaceID: {space_id}, Error: {e}")
        raise ValueError(f"Failed to convert plugins: {e}") from e


def knowledges_retrieval_config_convert(configs: dict[str, Any]):
    if "retrieval_config" not in configs.keys():
        logger.warning(f"Key retrieval_config is not in the configs JSON: {configs}")
        return KBRetrievalConfig()
    retrieval_config = configs["retrieval_config"]
    logger.warning(f"knowledges_retrieval_config_convert retrieval_config: {retrieval_config}")

    # 从配置中获取 use_agent 和 use_sync（前端直接传递）
    use_agent = retrieval_config.get("use_agent", False)
    use_sync = retrieval_config.get("use_sync", False)

    # 如果 use_agent 或 use_sync 中有一个为 True，则设置 use_graph 和 graph_expansion 为 True
    if use_agent or use_sync:
        use_graph = True
        graph_expansion = True
    else:
        use_graph = False
        graph_expansion = False

    kb_retrieval_config = KBRetrievalConfig(
        retrieval_type=retrieval_config["retrieval_type"],
        use_graph=use_graph,
        source=retrieval_config.get("source", 1),
        topk=retrieval_config["topk"],
        score_threshold=retrieval_config["score_threshold"],
        graph_expansion=graph_expansion,
        use_agent=use_agent,
        use_sync=use_sync
    )
    return kb_retrieval_config


def react_agent_convert(
        space_id: str,
        agent_info: AgentBaseDBPd,
        model_details: Optional[dict] = None
) -> tuple[Optional[dict], Optional[str]]:
    """Convert ReAct type agent to DSL format"""
    start_time = time.time()

    logger.info(f"[AGENT_CONVERT_REACT] Converting ReAct agent - ID: {agent_info.agent_id}, SpaceID: {space_id}")

    try:
        workflows_dsl = workflows_convert(space_id, agent_info.workflows)
        constrain_dsl = ConstrainConfig(**agent_info.constraint)

        model_dsl = None
        if model_details:
            # Prepare model info (model_details already contains overrides from agent_config)
            info = model_details

            model_info_dict = {
                "api_key": info.get("api_key"),
                "api_base": info.get("base_url"),
                "model_name": info.get("name"),
                "model_type": info.get("model_type"),
                "model_id": info.get("id"),
                "streaming": info.get("enable_streaming"),
                "timeout": info.get("timeout"),
            }
            # Add parameters if present in model_details
            if info.get("parameters"):
                model_info_dict.update(info.get("parameters"))

            # Create ModelConfig DSL
            # Need to decrypt api_key if needed, but here we assume raw or handled
            api_key = model_info_dict.get("api_key")
            if api_key:
                try:
                    api_key = SecurityUtils().decrypt_api_key(api_key)
                except ValueError as e:
                    logger.warning(
                        f"[AGENT_CONVERT] Failed to decrypt API key: {str(e)}, using original key"
                    )
                except Exception as e:
                    logger.error(
                        f"[AGENT_CONVERT] Unexpected error decrypting API key: {str(e)}"
                    )

            provider = info.get("provider")
            model_dsl = ModelConfig(
                model_client_config=ModelClientConfig(
                    client_provider=provider,
                    api_key=api_key,
                    api_base=model_info_dict.get("api_base"),
                    timeout=model_info_dict.get("timeout", 60)
                ),
                request_config=ModelRequestConfig(
                    model_name=model_info_dict.get("model_type"),
                    temperature=model_info_dict.get("temperature", 0.7),
                    top_p=model_info_dict.get("top_p", 0.9),
                    stream=model_info_dict.get("streaming", False),
                )
            )
        elif hasattr(agent_info, 'model_id') and agent_info.model_id:
            # Get model config by model_id
            from openjiuwen_studio.core.manager.repositories.model_config_repository import ModelConfigRepository
            from openjiuwen_studio.core.manager.repositories.jiuwen_base_repository import get_db_jw

            with get_db_jw() as db:
                model_repo = ModelConfigRepository(db)
                model_config = model_repo.get_by_id(agent_info.model_id)

            if model_config:
                # Create model_dsl from model_config
                # Get parameters from JSON field
                parameters = model_config.parameters or {}

                model_dsl = ModelConfig(
                    model_client_config=ModelClientConfig(
                        client_provider=model_config.provider,
                        api_key=SecurityUtils().decrypt_api_key(model_config.api_key) if model_config.api_key else '',
                        api_base=model_config.base_url,
                        timeout=model_config.timeout
                    ),
                    request_config=ModelRequestConfig(
                        model_name=model_config.model_type,
                        temperature=parameters.get('temperature', 0.7),
                        top_p=parameters.get('top_p', 0.9),
                        stream=model_config.enable_streaming,
                    )
                )

                # Apply agent_model_config overrides if available
                if hasattr(agent_info, 'agent_model_config') and agent_info.agent_model_config:
                    agent_model_config = agent_info.agent_model_config
                    if 'temperature' in agent_model_config and model_dsl.request_config:
                        model_dsl.request_config.temperature = agent_model_config['temperature']
                    if 'top_p' in agent_model_config and model_dsl.request_config:
                        model_dsl.request_config.top_p = agent_model_config['top_p']
                    if 'timeout' in agent_model_config and model_dsl.model_client_config:
                        model_dsl.model_client_config.timeout = agent_model_config['timeout']

        plugins: list[AgentPlugin] = [AgentPlugin(**p) for p in agent_info.plugins]

        plugins_dsl = agent_plugins_convert(space_id, plugins)
        logger.info(f"react_agent_convert agent_info: {agent_info}")

        knowledges_dsl = knowledges_convert(space_id, agent_info.knowledge)
        logger.warning(f"react_agent_convert knowledges_dsl: {knowledges_dsl}")
        kb_retrieval_config = knowledges_retrieval_config_convert(agent_info.configs)
        prompt_templates = []
        if "system_prompt" in agent_info.configs:
            prompt_templates.append(dict(role="system", content=agent_info.configs.get("system_prompt")))

        agent_dsl = dsl.ReactAgent(
            id=agent_info.agent_id,
            version="",
            name=agent_info.agent_name,
            description=agent_info.description,
            agent_type=agent_info.agent_type,
            configs=agent_info.memory,
            plugins=plugins_dsl,
            workflows=workflows_dsl,
            model=model_dsl,
            prompt_template_name=agent_info.prompt_template_name or "",
            prompt_template=prompt_templates,
            constrain=constrain_dsl,
            knowledges=knowledges_dsl,
            kb_retrieval=kb_retrieval_config
        )

        conversion_duration = time.time() - start_time
        logger.info(
            f"[AGENT_CONVERT_REACT] Conversion completed - ID: {agent_info.agent_id}, "
            f"Duration: {conversion_duration:.3f}s, Workflows: {len(workflows_dsl)}, Plugins: {len(plugins_dsl)}"
        )
        return agent_dsl.model_dump(), None

    except (json.JSONDecodeError, TypeError, AttributeError, ValueError) as e:
        conversion_duration = time.time() - start_time
        logger.error(
            f"[AGENT_CONVERT_REACT] Invalid agent configuration - ID: {agent_info.agent_id}, "
            f"Error: {e}, Duration: {conversion_duration:.3f}s"
        )
        raise ValueError(f"Invalid agent info for agent {agent_info.agent_id}: {e}")
    except Exception as e:
        conversion_duration = time.time() - start_time
        logger.error(
            f"[AGENT_CONVERT_REACT] Unexpected error - ID: {agent_info.agent_id}, "
            f"Error: {e}, Duration: {conversion_duration:.3f}s"
        )
        raise ValueError(f"Failed to convert ReAct agent {agent_info.agent_id}: {e}")


def workflow_agent_convert(
        space_id: str,
        agent_info: AgentBaseDBPd,
        model_details: Optional[dict] = None
) -> tuple[Optional[dict], Optional[str]]:
    """Convert Workflow type agent to DSL format"""
    start_time = time.time()

    logger.info(f"[AGENT_CONVERT_WORKFLOW] Converting Workflow agent - ID: {agent_info.agent_id}, SpaceID: {space_id}")

    try:
        workflows_dsl = workflows_convert(space_id, agent_info.workflows)

        model_dsl = None
        if model_details:
            # Prepare model info (model_details already contains overrides from agent_config)
            info = model_details

            model_info_dict = {
                "api_key": info.get("api_key"),
                "api_base": info.get("base_url"),
                "model_name": info.get("name"),
                "model_type": info.get("model_type"),
                "model_id": info.get("id"),
                "streaming": info.get("enable_streaming"),
                "timeout": info.get("timeout"),
            }
            if info.get("parameters"):
                model_info_dict.update(info.get("parameters"))

            api_key = model_info_dict.get("api_key")
            if api_key:
                try:
                    api_key = SecurityUtils().decrypt_api_key(api_key)
                except ValueError as e:
                    logger.warning(
                        f"[AGENT_CONVERT] Failed to decrypt API key: {str(e)}, using original key"
                    )
                except Exception as e:
                    logger.error(
                        f"[AGENT_CONVERT] Unexpected error decrypting API key: {str(e)}"
                    )

            model_dsl = ModelConfig(
                model_client_config=ModelClientConfig(
                    client_provider=info.get("provider"),
                    api_key=api_key,
                    api_base=model_info_dict.get("api_base"),
                    timeout=model_info_dict.get("timeout", 60)
                ),
                request_config=ModelRequestConfig(
                    model_name=model_info_dict.get("model_type"),
                    temperature=model_info_dict.get("temperature", 0.7),
                    top_p=model_info_dict.get("top_p", 0.9),
                    stream=model_info_dict.get("streaming", False),
                )
            )
        elif hasattr(agent_info, 'model_id') and agent_info.model_id:
            # Get model config by model_id
            from openjiuwen_studio.core.manager.repositories.model_config_repository import ModelConfigRepository
            from openjiuwen_studio.core.manager.repositories.jiuwen_base_repository import get_db_jw

            with get_db_jw() as db:
                model_repo = ModelConfigRepository(db)
                model_config = model_repo.get_by_id(agent_info.model_id)

            if model_config:
                # Create model_dsl from model_config
                # Get parameters from JSON field
                parameters = model_config.parameters or {}

                model_dsl = ModelConfig(
                    model_client_config=ModelClientConfig(
                        client_provider=model_config.provider,
                        api_key=SecurityUtils().decrypt_api_key(model_config.api_key) if model_config.api_key else '',
                        api_base=model_config.base_url,
                        timeout=model_config.timeout
                    ),
                    request_config=ModelRequestConfig(
                        model_name=model_config.model_type,
                        temperature=parameters.get('temperature', 0.7),
                        top_p=parameters.get('top_p', 0.9),
                        stream=model_config.enable_streaming,
                    )
                )

                # Apply agent_model_config overrides if available
                if hasattr(agent_info, 'agent_model_config') and agent_info.agent_model_config:
                    agent_model_config = agent_info.agent_model_config
                    if 'temperature' in agent_model_config and model_dsl.request_config:
                        model_dsl.request_config.temperature = agent_model_config['temperature']
                    if 'top_p' in agent_model_config and model_dsl.request_config:
                        model_dsl.request_config.top_p = agent_model_config['top_p']
                    if 'timeout' in agent_model_config and model_dsl.model_client_config:
                        model_dsl.model_client_config.timeout = agent_model_config['timeout']

        if agent_info.default_response and agent_info.default_response.strip():
            default_response = agent_info.default_response
        else:
            default_response = AgentDefaults.DEFAULT_RESPONSE.msg

        agent_dsl = dsl.WorkflowAgent(
            id=agent_info.agent_id,
            version="",
            name=agent_info.agent_name,
            description=agent_info.description,
            agent_type=agent_info.agent_type,
            configs={},
            workflows=workflows_dsl,
            model=model_dsl,
            default_response=default_response
        )

        conversion_duration = time.time() - start_time
        logger.info(
            f"[AGENT_CONVERT_WORKFLOW] Conversion completed - ID: {agent_info.agent_id}, "
            f"Duration: {conversion_duration:.3f}s, Workflows: {len(workflows_dsl)}"
        )
        return agent_dsl.model_dump(), None

    except (json.JSONDecodeError, TypeError, AttributeError, ValueError) as e:
        conversion_duration = time.time() - start_time
        logger.error(
            f"[AGENT_CONVERT_WORKFLOW] Invalid agent configuration - ID: {agent_info.agent_id}, "
            f"Error: {e}, Duration: {conversion_duration:.3f}s"
        )
        raise ValueError(f"Invalid agent info for agent {agent_info.agent_id}: {e}")
    except Exception as e:
        conversion_duration = time.time() - start_time
        logger.error(
            f"[AGENT_CONVERT_WORKFLOW] Unexpected error - ID: {agent_info.agent_id}, "
            f"Error: {e}, Duration: {conversion_duration:.3f}s"
        )
        raise ValueError(f"Failed to convert Workflow agent {agent_info.agent_id}: {e}")


def agent_convert(
        space_id: str,
        agent_info: AgentBaseDBPd,
        model_details: Optional[dict] = None
) -> tuple[Optional[dict], Optional[str]]:
    """Select appropriate conversion method based on agent type"""
    start_time = time.time()

    try:
        agent_type = agent_info.agent_type
        logger.info(f"[AGENT_CONVERT] Converting agent - ID: {agent_info.agent_id}, Type: {agent_type}")

        if agent_type == AgentType.ReAct:
            result = react_agent_convert(space_id, agent_info, model_details)
        elif agent_type == AgentType.Workflow:
            result = workflow_agent_convert(space_id, agent_info, model_details)
        else:
            logger.error(f"[AGENT_CONVERT] Invalid agent type - ID: {agent_info.agent_id}, Type: {agent_type}")
            return None, f"agent with id {agent_info.agent_id} invalid agent type: {agent_type}"

        conversion_duration = time.time() - start_time
        if result[0] is not None:
            logger.info(
                f"[AGENT_CONVERT] Conversion completed - ID: {agent_info.agent_id}, "
                f"Type: {agent_type}, Duration: {conversion_duration:.3f}s"
            )
        else:
            logger.error(
                f"[AGENT_CONVERT] Conversion failed - ID: {agent_info.agent_id}, "
                f"Type: {agent_type}, Error: {result[1]}, Duration: {conversion_duration:.3f}s"
            )

        return result

    except Exception as e:
        conversion_duration = time.time() - start_time
        logger.error(
            f"[AGENT_CONVERT] Unexpected error - ID: {agent_info.agent_id}, Error: {e}, Duration: {conversion_duration:.3f}s")
        return None, f"Failed to convert agent {agent_info.agent_id}: {e}"
