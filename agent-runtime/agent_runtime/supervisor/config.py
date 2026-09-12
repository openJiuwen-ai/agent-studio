# -*- coding: UTF-8 -*-
"""ReActAgent 配置构建 —— 监督者与子 Agent 共用。

⚠️ 语义标注（避免后续误解）：
- 本模块的入参叫 `model_deployment_id`（部署 id），不是模型名。这是 D0-8 实证结论：
  模型层接受"部署 id"并解析成真实模型名后调 LLM；传模型名（如
  `deepseek-v4-flash`）反而报"模型策略信息为空"。
- openjiuwen 原生 `ReActAgentConfig.model_name` / `ModelRequestConfig.model_name` 是 SDK 对
  "发给 LLM 接口的 model 字符串"的通用命名（直接连 LLM 时它确实是模型名）。在我们的架构里，
  这个字段装的是**部署 id**，由模型层（client_provider="studio"，model_service 进程内解析）
  解析。因此我们自己的入参语义用 `model_deployment_id`，与 SDK 的 `model_name` 字段名不同属正常。
"""

from openjiuwen.core.foundation.llm import ModelClientConfig, ModelRequestConfig
from openjiuwen.core.single_agent.agents.react_agent import ReActAgentConfig

from agent_runtime.common.config import settings


def format_conversation_history(history: list | None) -> str:
    """把对话历史格式化成 LLM 可读的文本段（复用平台 `ReActAgentRunner._format_conversation_history` 同款格式）。

    表的行是结构化的（role/content 独立列），LLM 的 system prompt 是单个字符串——
    必须序列化成本文段：段标题 `## 对话历史` 让 LLM 区分历史与当前任务，每行 `- **role**:`
    标明说话人，跳空 content 去噪音。仅注入监督者（方案 B），子 Agent 不感知。

    Args:
        history: list[{role, content}]，容忍 dict / pydantic Message / None

    Returns:
        "\\n\\n## 对话历史\\n- **user**: ...\\n- **assistant**: ..." 文本段；空/None 返回 ""
    """
    if not history:
        return ""
    lines = ["\n\n## 对话历史"]
    for msg in history:
        msg_dict = msg.model_dump() if hasattr(msg, "model_dump") else msg
        role = msg_dict.get("role", "")
        content = msg_dict.get("content", "")
        if content:
            lines.append(f"- **{role}**: {content}")
    return "\n".join(lines)


def build_react_config(
    system_prompt: str, model_deployment_id: str
) -> ReActAgentConfig:
    """构建 ReActAgentConfig（client_provider="studio" + model_service_id，进程内解析部署 id）。

    Args:
        system_prompt: 系统提示词
        model_deployment_id: 模型部署 id（非模型名，D0-8）。由路由解析成真实模型名后调 LLM。
    """
    # 2026-08-12 切到新模型层（dev 移除 Java runtime 模型路由 31113 → model_service 进程内解析）：
    # client_provider="studio"（model_service 注册的 StudioModelClient），model_service_id = 部署 id
    # （= t_model_service.ID，OBS 元数据 key）。api_base/api_key 为占位，真实连接由 resolver 在
    # invoke 时解析；project_id/workspace_id/auth_id 由 StudioModelClient 从请求头取。
    model_client_config = ModelClientConfig(
        client_provider="studio",
        api_key="sk-placeholder",
        api_base="https://studio-placeholder",
        timeout=settings.llm.timeout,
        verify_ssl=settings.llm.ssl_verify,
        model_service_id=model_deployment_id,
    )
    model_request_config = ModelRequestConfig(
        model=model_deployment_id,
        temperature=0.7,
        top_p=1.0,
    )
    return ReActAgentConfig(
        model_name=model_deployment_id,
        model_provider="studio",
        api_key="sk-placeholder",
        api_base="https://studio-placeholder",
        max_iterations=5,
        prompt_template=[{"role": "system", "content": system_prompt}]
        if system_prompt
        else [],
        model_client_config=model_client_config,
        model_config_obj=model_request_config,
    )
