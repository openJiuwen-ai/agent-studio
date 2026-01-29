import json
import os
import uuid
from typing import Any

from openjiuwen.core.common.logging import logger
from sqlalchemy.orm import Session

import openjiuwen_studio.core.manager.convertor.workflow as convert
from openjiuwen_studio.core.database import SessionLocal, milliseconds
from openjiuwen_studio.core.manager.repositories import EmbeddingModelConfigRepository, ModelConfigRepository
from openjiuwen_studio.core.manager.repositories.agent_repository import agent_repository
from openjiuwen_studio.core.manager.repositories.system_embedding_model_repository import SystemEmbeddingModelRepository
from openjiuwen_studio.core.manager.repositories.system_llm_model_repository import SystemLLMModelRepository
from openjiuwen_studio.core.manager.repositories.workflow_repository import workflow_repository
from openjiuwen_studio.models.agent import AgentBaseDBPd
from openjiuwen_studio.models.workflow import WorkflowBaseDBPd


def pre_install(space_id: str):
    db = SessionLocal()
    try:
        create_examples(space_id, db)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"[Template] Error during pre-installation: {str(e)}")
    finally:
        db.close()


def _read_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[Template] Error reading template file: {str(e)}, path: {path}")
        return {}


def create_examples(space_id: str, db: Session):
    base_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../examples")
    )
    current_time = milliseconds()

    def _create_workflow_from_template(filename: str) -> dict | None:
        tpl = _read_json(os.path.join(base_dir, filename))
        if not tpl:
            return None

        schema_obj = tpl.get("schema") or {
            "nodes": [
                {
                    "id": "start_0",
                    "type": "1",
                    "meta": {"position": {"x": 180, "y": 36}},
                    "data": {
                        "title": "开始",
                        "outputs": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "default": "你好，请帮我分析一下这个问题。",
                                }
                            },
                        },
                    },
                },
                {
                    "id": "end_0",
                    "type": "2",
                    "meta": {"position": {"x": 1100, "y": 36}},
                    "data": {
                        "title": "结束",
                        "inputs": {
                            "inputParameters": {
                                "result": {
                                    "type": "ref",
                                    "content": ["start_0", "query"],
                                }
                            },
                        },
                        "content": {"type": "template", "content": "{result}"},
                        "streaming": False,
                    },
                },
            ],
            "edges": [],
        }

        if isinstance(schema_obj, str):
            try:
                schema_obj = json.loads(schema_obj)
            except Exception:
                schema_obj = {}

        nodes = schema_obj.get("nodes")
        if isinstance(nodes, list):
            for node in nodes:
                t = str(node.get("type"))
                if t in ("3", "7"):
                    llm_param = ((node.get("data") or {}).get("inputs") or {}).get(
                        "llmParam"
                    ) or {}
                    llm_param["model"] = None
                    node.setdefault("data", {}).setdefault("inputs", {}).setdefault(
                        "llmParam", {}
                    ).update(llm_param)

        inputs, outputs = convert.extract_inputs_and_outputs_from_canvas(schema_obj)

        workflow_id = str(uuid.uuid4())
        workflow = WorkflowBaseDBPd(
            workflow_id=workflow_id,
            workflow_version="draft",
            name=tpl.get("name") or tpl.get("workflow_name") or "模板工作流",
            desc=tpl.get("desc")
            or tpl.get("description")
            or "这是一个示例工作流，用于快速上手。",
            url=tpl.get("url") or "",
            icon_uri=tpl.get("icon_uri") or "",
            space_id=space_id,
            create_time=current_time,
            update_time=current_time,
            schema=json.dumps(schema_obj),
            input_parameters=inputs,
            output_parameters=outputs,
        )
        workflow_repository.workflow_create(workflow)
        return {
            "workflow_id": workflow_id,
            "workflow_version": "draft",
            "workflow_name": workflow.name,
            "description": workflow.desc,
        }

    # Create workflows
    wf_check_balance = _create_workflow_from_template("workflow.check_balance.template.json")
    wf_money_transfer = _create_workflow_from_template("workflow.money_transfer.template.json")
    wf_check_weather = _create_workflow_from_template("workflow.check_weather.template.json")
    wf_plan_route = _create_workflow_from_template("workflow.plan_route_with_amap.template.json")

    finance_wfs = [w for w in [wf_check_balance, wf_money_transfer] if w]
    travel_wfs = [w for w in [wf_check_weather, wf_plan_route] if w]

    # Create Travel Agent
    ag_tpl = _read_json(os.path.join(base_dir, "agent.travel.template.json"))
    agent_id = str(uuid.uuid4())
    _ag_configs = ag_tpl.get("configs") or {}
    _ag_pt = ag_tpl.get("prompt_template") or []
    if isinstance(_ag_pt, list):
        for _m in _ag_pt:
            if (_m or {}).get("role") == "system" and (_m or {}).get("content"):
                _ag_configs.setdefault("system_prompt", _m.get("content"))
                break

    travel_agent = AgentBaseDBPd(
        agent_id=agent_id,
        agent_name=ag_tpl.get("agent_name") or "模板智能体",
        space_id=space_id,
        description=ag_tpl.get("description") or "这是一个示例智能体，可用于快速上手。",
        agent_type=ag_tpl.get("agent_type") or "react",
        icon=ag_tpl.get("icon") or "🤖",
        edit_mode="manual",
        workflows=travel_wfs,
        model=None,
        prompt_template_name=ag_tpl.get("prompt_template_name") or "",
        prompt_template=ag_tpl.get("prompt_template") or None,
        auto_generated_prompt=ag_tpl.get("auto_generated_prompt") or "",
        configs=_ag_configs,
        plugins=[],
        prompt_tuning=ag_tpl.get("prompt_tuning") or {},
        triggers=ag_tpl.get("triggers") or [],
        knowledge=ag_tpl.get("knowledge") or [],
        constraint={"reserved_max_chat_rounds": 10, "max_iteration": 5},
        opening_remarks="您好！我是您的智能旅游助手，很高兴为您服务。请问有什么可以帮助您的吗？",
        memory=ag_tpl.get("memory") or None,
        create_time=current_time,
        update_time=current_time,
    )
    agent_repository.create_agent_db(travel_agent)

    # Create Finance Agent
    finance_tpl = _read_json(os.path.join(base_dir, "agent.finance.template.json"))
    finance_agent_id = str(uuid.uuid4())
    _fi_configs = finance_tpl.get("configs") or {}
    _fi_pt = finance_tpl.get("prompt_template") or []
    if isinstance(_fi_pt, list):
        for _m in _fi_pt:
            if (_m or {}).get("role") == "system" and (_m or {}).get("content"):
                _fi_configs.setdefault("system_prompt", _m.get("content"))
                break

    finance_agent = AgentBaseDBPd(
        agent_id=finance_agent_id,
        agent_name=finance_tpl.get("agent_name") or "金融客服助手",
        space_id=space_id,
        description=finance_tpl.get("description") or "面向金融场景的客服助手",
        agent_type=finance_tpl.get("agent_type") or "react",
        icon=finance_tpl.get("icon") or "",
        edit_mode="manual",
        workflows=finance_wfs,
        model=None,
        prompt_template_name=finance_tpl.get("prompt_template_name") or "",
        prompt_template=finance_tpl.get("prompt_template") or None,
        auto_generated_prompt=finance_tpl.get("auto_generated_prompt") or "",
        configs=_fi_configs,
        plugins=[],
        prompt_tuning=finance_tpl.get("prompt_tuning") or {},
        triggers=finance_tpl.get("triggers") or [],
        knowledge=finance_tpl.get("knowledge") or [],
        constraint={"reserved_max_chat_rounds": 10, "max_iteration": 5},
        opening_remarks="您好！我是您的智能金融客服助手，很高兴为您服务。请问有什么可以帮助您的吗？",
        memory=finance_tpl.get("memory")
        or {
            "max_tokens": 1000,
            "variable_config": [],
            "longterm_memory_config": False,
        },
        create_time=current_time,
        update_time=current_time,
    )
    agent_repository.create_agent_db(finance_agent)

    # pre install system models for user
    pre_install_models_for_user(db, space_id)


def pre_install_models_for_user(db: Session, space_id: str):
    """Pre install system llm and embedding models for user"""
    llm_model_repo = ModelConfigRepository(db)
    embedding_model_repo = EmbeddingModelConfigRepository(db)
    system_llm_model_repo = SystemLLMModelRepository(db)
    system_embedding_model_repo = SystemEmbeddingModelRepository(db)

    # add system llm models to model config
    system_llm_models = system_llm_model_repo.query().all()
    for model in system_llm_models:
        model_dict = _model_to_dict(model, space_id)
        created_llm_model_config = llm_model_repo.create(model_dict)
        logger.info(f"Added llm model config: {created_llm_model_config.id} from system llm model: {model.id}")

    # add system embedding models to embedding model config
    system_embedding_models = system_embedding_model_repo.query().all()
    for model in system_embedding_models:
        model_dict = _model_to_dict(model, space_id)
        created_embedding_model_config = embedding_model_repo.create(model_dict)
        logger.info(
            f"Added embedding model config: {created_embedding_model_config.id} from system embedding model: {model.id}"
        )


def _model_to_dict(model, space_id: str) -> dict[str, Any]:
    model_dict = model.to_dict(exclude_invalid=True)
    model_dict.update({'space_id': space_id})
    model_dict.update({'is_system_model': True})
    model_dict.update({'system_model_id': model.id})
    model_dict.pop("id")
    model_dict.pop("created_at")
    model_dict.pop("updated_at")
    return model_dict
