# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.

"""
模型配置适配器 — 将各节点特定配置转换为 IRModelConfigProvider 期望的标准化格式

设计原则：
- 每个节点类型有专属适配器函数
- 适配器返回标准化的 dict 供 Provider 使用
- 节点业务代码不感知 Provider 内部结构
"""


def adapt_llm_chain_config(conf: dict) -> dict:
    """LLMChain 配置适配器

    LLMChain 的 conf 结构包含 model/templateContent/responseFormat 等字段，
    需要提取 model 部分转换为 Provider 期望的格式。

    Args:
        conf: LLMChain 的完整配置字典

    Returns:
        标准化的 IR 节点配置格式
    """
    return {"configs": {"model": conf.get("model", {})}}


def adapt_questioner_config(
    model_name: str,
    hyper_parameters: dict,
    extension: dict,
) -> dict:
    """Questioner 配置适配器

    Questioner 使用分散的配置参数，需要组装为 Provider 期望的格式。

    Args:
        model_name: 模型名称
        hyper_parameters: 超参数字典
        extension: 扩展配置字典（含 authId 等）

    Returns:
        标准化的 IR 节点配置格式
    """
    return {
        "configs": {
            "model": {
                "modelName": model_name,
                "hyperParameters": hyper_parameters or {},
                "extension": extension or {},
            }
        }
    }


def adapt_intent_detection_config(conf: dict) -> dict:
    """IntentDetection 配置适配器

    IntentDetection 的配置嵌套在 conf[llm][model] 下，
    需要提取并转换为目标格式。

    Args:
        conf: IntentDetection 的完整配置字典，包含 llm/model 嵌套结构

    Returns:
        标准化的 IR 节点配置格式
    """
    llm_configs = conf.get("llm", {})
    model_configs = llm_configs.get("model", {})

    return {
        "configs": {
            "model": {
                "modelName": model_configs.get("modelName", ""),
                "hyperParameters": model_configs.get("hyperParameters", {}),
                "extension": model_configs.get("extension", {}),
            }
        }
    }


def adapt_ir_converter_model_config(model_configs: dict, model_id: str) -> dict:
    """IRConverter 模型注册配置适配器

    IRConverter 在注册模型时使用独立的 model_configs 字典，
    需要转换为目标格式，支持 model_id 作为兜底。

    Args:
        model_configs: 模型配置字典
        model_id: 模型 ID（作为 modelName 的兜底值）

    Returns:
        标准化的 IR 节点配置格式
    """
    return {
        "configs": {
            "model": {
                "modelName": model_configs.get("modelName") or model_id,
                "hyperParameters": model_configs.get("hyperParameters", {}) or {},
                "extension": model_configs.get("extension", {}) or {},
            }
        }
    }


def adapt_react_agent_config(configs: dict) -> dict:
    """LLMReAct 节点配置适配器

    LLMReAct 节点的 configs 含 systemPrompt/model/plugins/maxIteration 等字段，
    提取 model 部分转换为 Provider 期望的标准化格式。结构与 LLMChain 的 model
    字段一致，单独建 adapter 保持节点类型清晰。

    Args:
        configs: LLMReAct 节点的完整配置字典

    Returns:
        标准化的 IR 节点配置格式 {"configs": {"model": {...}}}
    """
    return {"configs": {"model": configs.get("model", {})}}
