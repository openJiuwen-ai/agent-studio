# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
"""
ReActAgent Runner — 使用 openjiuwen ReActAgent 执行用户请求
"""

from __future__ import annotations

import os
import re
import time
import uuid
import json
from typing import AsyncGenerator, Optional, Dict

from agent_runtime.runner.react_stream_data_adapter import ReactStreamDataAdapter
from agent_runtime.runner.react_workflow_adapter import ReactWorkflowAdapter
from agent_runtime.runner.react_file_reader_adapter import ReactFileReaderAdapter
from agent_runtime.schemas.orchestration_mgr import ExecutionRequest
from jiuwen.serve.controllers.execution.open_utils import async_ir_load
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.foundation.llm import Model
from openjiuwen.core.session.agent import Session, create_agent_session
from openjiuwen.core.session.stream import BaseStreamMode
from openjiuwen.core.single_agent.agents.react_agent import ReActAgent, ReActAgentConfig
from openjiuwen.core.single_agent.schema.agent_card import AgentCard


def _adapt_react_agent_config(ir_json: dict) -> dict:
    """将 IR 配置适配为 IRModelConfigProvider 期望的格式"""
    configs = ir_json.get("configs", {})
    model_config = configs.get("modelConfig", {})

    return {
        "configs": {
            "model": {
                "modelName": model_config.get("modelName", ""),
                "modelType": model_config.get("modelType", ""),
                "modelBaseUrl": model_config.get("modelBaseUrl", ""),
                "hyperParameters": model_config.get("hyperParameters", {}),
                "extension": model_config.get("extension", {}),
            }
        }
    }


class ReActAgentRunner:
    """使用 ReActAgent 运行用户请求的 Runner

    支持从 IR 配置加载并注册 Plugin/MCP/Workflow/Skill 等多种工具类型
    """

    def __init__(self, api_key: str | None = None, api_base: str | None = None):
        self._api_key = api_key or os.environ.get("API_KEY") or ""
        self._api_base = (api_base or os.environ.get("API_BASE", "https://api.deepseek.com")).rstrip("/")

    async def _load_ir(self, ir_path: str) -> dict:
        """从存储加载 IR 配置"""
        try:
            return await async_ir_load(ir_path)
        except Exception as e:
            workflow_logger.error(f"Failed to load IR from {ir_path}: {e}")
            raise

    @staticmethod
    def _resolve_variable_references(template: str, global_variables: dict) -> str:
        """替换模板中的 {{inputs.xxx}} 变量引用

        从 global_variables 中按路径查找变量值并替换。
        若路径不存在，替换为空字符串。支持嵌套路径如 {{inputs.user.name}}。
        """

        def replace_inputs(match):
            path = match.group(1)
            keys = path.split(".")
            value = global_variables
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return ""
            return str(value) if value is not None else ""

        template = re.sub(r"\{\{inputs\.([\w.]+)\}\}", replace_inputs, template)
        return template

    def _parse_prompt_template(self, ir_json: dict, conversation_history: list = None, skill_work_dir: str = "", global_variables: dict = None, has_file_links: bool = False) -> \
    list[dict]:
        """解析 IR 中的提示词模板，添加工具使用说明和 skill 提示词"""
        configs = ir_json.get("configs", {})
        sys_prompt = configs.get("sysPromptTemplate", "")

        # 将 IR 中声明的入参变量默认值合并到 global_variables（用户未传值时回退到默认值）
        if global_variables is not None:
            input_vars = configs.get("inputVariables", [])
            for var in (input_vars or []):
                key = var.get("variable_key", "")
                default = var.get("default_value", "")
                if key and key not in global_variables:
                    global_variables[key] = default

        # 替换 {{inputs.xxx}} 入参变量
        if global_variables and sys_prompt:
            sys_prompt = self._resolve_variable_references(sys_prompt, global_variables)

        tool_instruction = "\n\n你可以通过调用工具来完成任务。可使用 available tools 中提供的工具，工具的参数优先结合上下文进行推断。"

        # 构建 skill 提示词（传入实际工作目录）
        skills_prompt = self._build_skills_prompt(ir_json, skill_work_dir)

        # 文件链接提示词
        file_links_prompt = self._build_file_links_prompt() if has_file_links else ""

        history_section = self._format_conversation_history(conversation_history)

        if sys_prompt:
            full_prompt = sys_prompt + tool_instruction + skills_prompt + file_links_prompt + history_section
        else:
            full_prompt = "你是一个AI助手，能够帮助用户完成任务。" + tool_instruction + skills_prompt + file_links_prompt + history_section

        return [{"role": "system", "content": full_prompt}]

    def _build_file_links_prompt(self) -> str:
        """构建文件链接提示词"""
        return (
            "\n\n## 文件读取指令（重要）\n"
            "用户提供了文件链接（如 .docx, .txt, .pdf 等格式）。\n"
            "可以使用预置的 read_file_from_url 工具来读取文件内容，"
            "当工具返回文件内容后，基于内容回复用户。\n"
        )

    def _build_skills_prompt(self, ir_json: dict, skill_work_dir: str = "") -> str:
        """构建 skill 提示词"""
        import posixpath

        skills_conf = ir_json.get("configs", {}).get("skills", {})
        if not skills_conf:
            return ""

        skill_dir = skills_conf.get("skill_dir", "")
        skill_info_list = skills_conf.get("skill_info", [])
        if not skill_info_list:
            return ""

        skills_info = []
        for index, skill in enumerate(skill_info_list):
            name = skill.get("name", "")
            description = skill.get("description", "")
            if skill_work_dir:
                skill_path = os.path.join(skill_work_dir, skill_dir, name) if skill_dir else os.path.join(
                    skill_work_dir, name)
            else:
                skill_path = posixpath.join(skill_dir, name) if skill_dir else name
            skills_info.append(
                f"{index + 1}. Skill name: {name}; Skill description: {description}; Skill directory file path: {skill_path}")

        return (
                "You are an agent equipped with various skills to solve problems.\n"
                "Before attempting any task, read the relevant skill document (SKILL.md) "
                "using read_file and follow its workflow.\n\n"
                "To help you better complete tasks, the following skill knowledge is equipped:\n"
                + "\n".join(skills_info)
                + "\nYou can use the read_file tool to read the corresponding SKILL.md file.\n"
        )

    def _format_conversation_history(self, history: list) -> str:
        """格式化对话历史"""
        if not history:
            return ""

        history_lines = ["\n\n## 对话历史"]
        for msg in history:
            msg_dict = msg.model_dump() if hasattr(msg, "model_dump") else msg
            role = msg_dict.get("role", "")
            content = msg_dict.get("content", "")
            if content:
                history_lines.append(f"- **{role}**: {content}")

        return "\n".join(history_lines)

    def _parse_max_iterations(self, ir_json: dict) -> int:
        """解析最大迭代次数"""
        return ir_json.get("configs", {}).get("maxIteration", 5)

    async def _create_llm(self, ir_json: dict) -> Model:
        """根据 IR 配置创建 LLM 模型实例"""
        from jiuwen.serve.controllers.execution.ir_converter import _get_model_config_provider

        adapted_conf = _adapt_react_agent_config(ir_json)
        provider = _get_model_config_provider()
        llm_comp_config = await provider.get_llm_config(adapted_conf)

        return Model(
            model_client_config=llm_comp_config.model_client_config,
            model_config=llm_comp_config.model_config,
        )

    def _convert_arguments_to_schema(self, arguments: list) -> dict:
        """将 IR 的 arguments 转换为 JSON Schema 格式"""
        properties = {}
        required = []

        for arg in arguments:
            arg_name = arg.get("name", "")
            arg_type = arg.get("type", "string")
            arg_desc = arg.get("description", "")
            is_required = arg.get("required", False)
            arg_method = arg.get("method", "")

            if arg_method == "Headers":
                continue

            schema_type = self._map_argument_type(arg_type)

            properties[arg_name] = {
                "type": schema_type,
                "description": arg_desc,
            }

            if is_required:
                required.append(arg_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    @staticmethod
    def _map_argument_type(arg_type: str) -> str:
        """映射参数类型到 JSON Schema 类型"""
        type_mapping = {
            "integer": "integer",
            "int": "integer",
            "number": "number",
            "float": "number",
            "double": "number",
            "boolean": "boolean",
            "bool": "boolean",
            "array": "array",
            "list": "array",
            "object": "object",
            "dict": "object",
        }
        return type_mapping.get(arg_type.lower(), "string")

    def _get_agent_functions(self, agent: ReActAgent) -> list[dict]:
        """从 agent 的 ability_manager 获取工具列表，转换为 OpenAI function calling 格式"""
        functions = []
        if not hasattr(agent, "ability_manager"):
            return functions

        try:
            ability_manager = agent.ability_manager
            # 使用 list() 方法获取已注册的工具
            abilities = ability_manager.list()
            for ability in abilities:
                # 获取工具的 input_params（已经是 JSON Schema 格式）
                input_params = {}
                if hasattr(ability, "input_params") and ability.input_params:
                    input_params = ability.input_params

                func = {
                    "name": getattr(ability, "name", "") or getattr(ability, "id", ""),
                    "description": getattr(ability, "description", "") or "",
                    "parameters": input_params if input_params else {"type": "object", "properties": {}},
                }
                functions.append(func)
        except Exception as e:
            workflow_logger.warning(f"Failed to get agent functions: {e}")

        return functions

    async def _register_plugins(self, ir_json: dict, agent: ReActAgent, agent_id: str) -> list[str]:
        """注册 Plugin 工具"""
        from jiuwen.extension.wrapper.restful_api_loader import load_restful_api_from_ir
        from openjiuwen.core.foundation.tool import ToolCard
        from openjiuwen.core.runner import Runner
        from agent_runtime.extension.tool.knowledge_retrieval_tool import (
            build_knowledge_retrieval_openjiuwen_tool,
            is_knowledge_retrieval_ir,
        )

        tool_ids = []
        plugins = ir_json.get("configs", {}).get("plugins", [])

        for plugin_conf in plugins:
            try:
                input_params = self._convert_arguments_to_schema(plugin_conf.get("arguments", []))

                if is_knowledge_retrieval_ir(plugin_conf):
                    # 知识库检索只让模型提供 query，其余参数全部来自 IR，
                    # 因此不传完整 schema，退回到 build 函数内的 query-only 默认 schema。
                    kb_tool = build_knowledge_retrieval_openjiuwen_tool(plugin_conf)
                    result = Runner.resource_mgr.add_tool(kb_tool, tag=agent_id)
                    if not result.is_ok() and "resource already exist" not in str(result.error()):
                        raise result.error()
                    agent.ability_manager.add(kb_tool.card)
                    tool_ids.append(kb_tool.card.id)
                    continue

                tool_id = load_restful_api_from_ir(plugin_conf, tag=agent_id)
                input_params = self._convert_arguments_to_schema(plugin_conf.get("arguments", []))

                card = ToolCard(
                    id=tool_id,
                    name=plugin_conf.get("name", tool_id),
                    description=plugin_conf.get("description", ""),
                    input_params=input_params,
                )
                agent.ability_manager.add(card)
                tool_ids.append(tool_id)
            except Exception as e:
                workflow_logger.error(f"Failed to register plugin {plugin_conf.get('name')}: {e}")

        workflow_logger.info(f"Registered {len(tool_ids)} plugins success")
        return tool_ids

    async def _register_mcp_servers(self, ir_json: dict, agent: ReActAgent, agent_id: str) -> list[str]:
        """注册 MCP Server"""
        from jiuwen.extension.wrapper.mcp_server_loader import convert_ir_to_server_config, load_mcp_server_from_ir

        tool_ids = []
        mcps = ir_json.get("configs", {}).get("mcps", [])

        for mcp_conf in mcps:
            try:
                mcp_tool_ids = await load_mcp_server_from_ir(mcp_conf, tag=agent_id)
                mcp_config = convert_ir_to_server_config(mcp_conf)
                agent.ability_manager.add(mcp_config)
                tool_ids.extend(mcp_tool_ids)
            except Exception as e:
                workflow_logger.error(f"Failed to register MCP server {mcp_conf.get('name')}: {e}")

        workflow_logger.info(f"Registered {len(tool_ids)} MCP tools success")
        return tool_ids

    async def _register_workflows(self, ir_json: dict, agent: ReActAgent, agent_id: str) -> list[str]:
        """注册 Workflow 工具"""
        from jiuwen.serve.controllers.execution.ir_converter import IRConverter
        from openjiuwen.core.runner import Runner
        from openjiuwen.core.workflow import WorkflowCard

        workflow_ids = []
        workflows = ir_json.get("configs", {}).get("workflows", [])

        for wf_conf in workflows:
            try:
                ir_path = wf_conf.get("ir_path", "")
                if not ir_path:
                    continue

                sub_ir = await async_ir_load(ir_path)
                workflow = await IRConverter.async_ir_to_workflow(sub_ir)

                workflow_id = wf_conf.get("name", "") or sub_ir.get("workflow", {}).get("id", "")
                if not workflow_id:
                    workflow_id = str(uuid.uuid4())

                wf_name = workflow.card.name
                wf_instance = workflow
                wf_desc = sub_ir.get("workflow", {}).get("description", "")
                user_fields_keys = [arg.get("name") for arg in wf_conf.get("arguments", [])]

                input_params = {
                    "type": "object",
                    "properties": {
                        arg.get("name", ""): {
                            "type": arg.get("type", "string"),
                            "description": arg.get("description", ""),
                        }
                        for arg in wf_conf.get("arguments", [])
                    },
                    "required": [
                        arg.get("name", "")
                        for arg in wf_conf.get("arguments", [])
                        if arg.get("required", False)
                    ],
                }

                # 清理旧注册
                for key in (wf_instance.card.id, wf_name):
                    try:
                        Runner.resource_mgr.remove_workflow(workflow_id=key, tag=agent_id)
                        Runner.resource_mgr.remove_tool(tool_id=key, tag=agent_id)
                    except Exception:
                        pass

                # 注册到 resource_mgr（使用 workflow 方式）
                new_card = WorkflowCard(
                    id=wf_name,
                    name=wf_name,
                    description=wf_desc,
                )
                Runner.resource_mgr.add_workflow(
                    card=new_card,
                    workflow=lambda card=new_card: wf_instance,
                    tag=agent_id,
                )

                # 注册 Tool 到 resource_mgr
                try:
                    wt_instance = ReactWorkflowAdapter(
                        workflow_instance=wf_instance,
                        workflow_name=wf_name,
                        workflow_desc=wf_desc,
                        input_params=input_params,
                        user_fields_keys=user_fields_keys,
                    )
                    Runner.resource_mgr.add_tool(tool=wt_instance, tag=agent_id)
                except Exception as e:
                    workflow_logger.error(f"Failed to register tool: {e}")

                # 注册到 ability_manager
                agent.ability_manager.add(wt_instance.card)
                workflow_ids.append(workflow_id)
            except Exception as e:
                workflow_logger.error(f"Failed to register workflow {wf_conf.get('name')}: {e}")

        workflow_logger.info(f"Registered {len(workflow_ids)} workflows success")
        return workflow_ids

    async def _download_skills(self, skill_dir: str, skill_info_list: list) -> str:
        """下载并解压 skill 文件到本地工作目录"""
        import os
        import zipfile

        workflow_logger.info(f"[SkillDownload] skill_dir='{skill_dir}', skill_count={len(skill_info_list)}")

        from agent_runtime.common.config import settings
        skill_storage_dir = settings.skill_storage.skill_storage_dir

        if skill_dir and not os.path.isabs(skill_dir):
            work_dir = skill_storage_dir or os.getcwd()
            skill_local_path_prefix = os.path.join(work_dir, skill_dir)
        else:
            work_dir = os.path.dirname(skill_dir) if skill_dir else os.getcwd()
            skill_local_path_prefix = skill_dir

        if not os.path.exists(skill_local_path_prefix):
            if not os.path.exists(work_dir):
                workflow_logger.error(f"[SkillDownload] Both {skill_local_path_prefix} and {work_dir} not found")
                return None
            try:
                os.makedirs(skill_local_path_prefix, exist_ok=True)
            except Exception as e:
                workflow_logger.error(f"[SkillDownload] Failed to create directory: {e}")
                return None

        if not skill_info_list:
            return skill_local_path_prefix

        for skill in skill_info_list:
            skill_name = skill.get("name")
            skill_path = skill.get("skill_path")
            if not skill_name or not skill_path:
                continue

            skill_md_path = os.path.join(skill_local_path_prefix, skill_name, "SKILL.md")
            if os.path.isfile(skill_md_path):
                continue

            local_zip_path = os.path.join(skill_local_path_prefix, f"{skill_name}.zip")

            try:
                from agent_runtime.storage.object_storage import get_storage_provider
                provider = get_storage_provider()
                await provider.download_to_file(object_key=skill_path, local_path=local_zip_path)

                with zipfile.ZipFile(local_zip_path, "r") as zip_ref:
                    for member in zip_ref.infolist():
                        member.filename = member.filename.replace("\\", "/")
                        zip_ref.extract(member, skill_local_path_prefix)
                os.remove(local_zip_path)

                if os.path.isfile(skill_md_path):
                    workflow_logger.info(f"[SkillDownload] Downloaded {skill_name}")
            except Exception as e:
                workflow_logger.error(f"[SkillDownload] Failed {skill_name}: {e}")

        return skill_local_path_prefix

    def _has_file_links(self, query: str) -> bool:
        """检测 query 中是否包含可读取的文件链接（排除图片）"""
        if not query:
            return False
        from urllib.parse import urlparse

        urls = re.findall(r'https?://[^\s\]\"\'<>]+', query)
        # 图片格式扩展名
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico')

        if not urls:
            return False

        for url in urls:
            # 解析 URL 获取路径部分（去掉查询参数）
            path = urlparse(url).path.lower()
            # 如果路径以图片格式结尾，排除
            if any(path.endswith(ext) for ext in image_extensions):
                return False
        return True

    def _register_file_reader_tool(self, agent: ReActAgent, agent_id: str) -> None:
        """注册轻量级的文件读取工具（从 URL 下载并读取内容）"""
        from openjiuwen.core.foundation.tool import ToolCard
        from openjiuwen.core.runner import Runner

        try:
            file_reader = ReactFileReaderAdapter()

            # 1. 注册执行器到 resource_mgr
            Runner.resource_mgr.add_tool(tool=file_reader, tag=agent_id)

            # 2. 注册 ToolCard 到 ability_manager
            agent.ability_manager.add(file_reader.card)

        except Exception as e:
            workflow_logger.error(f"Failed to register: {e}", exc_info=True)

    async def _register_skills(self, ir_json: dict, agent: ReActAgent, agent_id: str, skill_work_dir: str = "") -> None:
        """注册 Skill 工具和配置"""
        import os

        skills_conf = ir_json.get("configs", {}).get("skills", {})
        if not skills_conf:
            return

        skill_dir = skills_conf.get("skill_dir", "")
        skill_info_list = skills_conf.get("skill_info", [])
        if not skill_dir and not skill_info_list:
            return

        actual_work_dir = skill_work_dir or (os.path.join(os.getcwd(), skill_dir) if skill_dir else "")

        agent.lazy_init_skill()

        if agent._skill_util and skill_info_list and actual_work_dir:
            for skill in skill_info_list:
                skill_name = skill.get("name", "")
                try:
                    await agent._skill_util.register_skills(
                        os.path.join(actual_work_dir, skill_name), agent
                    )
                except Exception as e:
                    workflow_logger.warning(f"Failed to register skill {skill_name}: {e}")

    def _create_agent(self, ir_json: dict, conversation_history: list = None, skill_work_dir: str = "", global_variables: dict = None, has_file_links: bool = False) -> tuple[
        ReActAgent, str]:
        """根据 IR 配置创建 ReActAgent 实例

        Args:
            ir_json: IR 配置
            conversation_history: 对话历史
            skill_work_dir: skill 文件的实际工作目录
            global_variables: 全局变量（含用户入参变量）
            has_file_links: query 中是否包含文件链接
        """
        prompt_template = self._parse_prompt_template(ir_json, conversation_history, skill_work_dir, global_variables, has_file_links)
        max_iterations = self._parse_max_iterations(ir_json)
        agent_id = ir_json.get("agentId", "react_agent")

        card = AgentCard(
            id=agent_id,
            name=ir_json.get("agentName", "ReAct Agent"),
            description=ir_json.get("description", "ReAct paradigm Agent"),
        )

        config = ReActAgentConfig()
        config.configure_max_iterations(max_iterations=max_iterations)
        config.configure_prompt_template(prompt_template)

        agent = ReActAgent(card)
        agent.configure(config)

        return agent, agent_id

    async def run_streaming(
            self, req: ExecutionRequest, execution_id: str | None = None
    ) -> AsyncGenerator[Dict, None]:
        """流式运行 ReActAgent 并 yield SSE 事件"""
        exec_id = execution_id or req.conversation_id or str(uuid.uuid4())
        adapter = ReactStreamDataAdapter(execution_id=exec_id)

        # 加载 IR 配置
        try:
            ir_json = await self._load_ir(req.ir_path)
        except Exception as e:
            workflow_logger.error(
                f"Failed to load IR from {req.ir_path}: {e}", exc_info=True
            )
            yield adapter.adapt_error(f"Failed to load workflow configuration: {e}")
            return

        # 创建 LLM 模型
        try:
            llm = await self._create_llm(ir_json)
        except Exception as e:
            workflow_logger.error(f"Failed to create LLM: {e}")
            yield adapter.adapt_error(f"Failed to create LLM: {e}")
            return

        # 1. 先下载 skill 文件（需要知道实际工作目录才能正确注入 prompt）
        skills_conf = ir_json.get("configs", {}).get("skills", {})
        skill_work_dir = ""
        if skills_conf:
            skill_dir = skills_conf.get("skill_dir", "")
            skill_info_list = skills_conf.get("skill_info", [])
            try:
                skill_work_dir = await self._download_skills(skill_dir, skill_info_list) or ""
                workflow_logger.info(f"[run_streaming] Skill download completed, skill_work_dir={skill_work_dir}")
            except Exception as e:
                workflow_logger.error(f"[run_streaming] Skill download failed: {e}", exc_info=True)

        # 获取 query 并检测文件链接
        query = req.query or "Hello"
        has_file_links = self._has_file_links(query)

        # 2. 创建 Agent（传入 skill_work_dir 和 has_file_links 以便正确构建 prompt）
        try:
            conversation_history = req.params.conversation_history
            global_variables = req.params.global_variables or {}
            agent, agent_id = self._create_agent(ir_json, conversation_history, skill_work_dir, global_variables, has_file_links)
            agent.set_llm(llm)
        except Exception as e:
            workflow_logger.error(f"Failed to create agent: {e}")
            yield adapter.adapt_error(f"Failed to create agent: {e}")
            return

        # 3. 注册 OtelRail 以触发 OTel span 生命周期管理
        try:
            from openjiuwen.extensions.tracer_otel.otel_rail import OtelRail
            await agent.register_rail(OtelRail())
        except Exception as e:
            workflow_logger.debug(f"OtelRail registration skipped: {e}")

        # 4. 注册工具
        try:
            await self._register_plugins(ir_json, agent, agent_id)
            await self._register_mcp_servers(ir_json, agent, agent_id)
            await self._register_workflows(ir_json, agent, agent_id)
            await self._register_skills(ir_json, agent, agent_id, skill_work_dir)
            # 有文件链接时注册读文件工具
            if has_file_links:
                self._register_file_reader_tool(agent, agent_id)
        except Exception as e:
            workflow_logger.error(f"Failed to register tools: {e}")
            yield adapter.adapt_error(f"Failed to register tools: {e}")
            return

        # 构建输入
        query = req.query or "Hello"
        inputs = {
            "query": query,
            "conversation_id": req.conversation_id,
            "user_id": req.user_id,
        }

        # 发送初始事件
        yield adapter.create_start_event()
        adapter.start_time = int(time.time() * 1000)

        chain_id = str(uuid.uuid4())

        # 设置 adapter 的 chain ID（chain 节点 ID 与 chain_id 相同）
        adapter.set_chain_and_agent_ids(chain_id, chain_id)

        # 发送 chain 开始事件
        yield adapter.create_agent_node_start_event(
            invoke_id=chain_id,
            chain_id=chain_id,
            invoke_type="chain",
            name=ir_json.get("agentName", "Agent"),
        )

        # 执行并转换输出
        session: Optional[Session] = None
        is_first_llm_call = True

        try:
            session_id = req.conversation_id or "default_session"
            session = create_agent_session(session_id=session_id, card=agent.card)
            await session.pre_run(inputs=inputs)
            # 提取 openjiuwen tracer 并注入到 inputs 中
            inputs.setdefault("_jiuwen_runtime_kwargs", {})["session"] = session

            # 构建 LLM inputs（用于事件记录）—— 包含系统提示词以便调试查看
            prompt_messages = self._parse_prompt_template(ir_json, conversation_history, skill_work_dir, global_variables, has_file_links)
            llm_inputs = list(prompt_messages) + [{"role": "user", "content": query}]

            # 构建 LLM metaData（模型参数）
            # 从 agent 的 ability_manager 获取已注册的工具
            functions = self._get_agent_functions(agent)
            llm_meta_data = {
                "class_name": "Openai",
                "instance_attributes": {
                    "model": ir_json.get("configs", {}).get("modelConfig", {}).get("modelName", ""),
                    "temperature": ir_json.get("configs", {}).get("modelConfig", {}).get("hyperParameters", {}).get("temperature", 0.0),
                    "top_p": ir_json.get("configs", {}).get("modelConfig", {}).get("hyperParameters", {}).get("top_p", 1.0),
                    "functions": functions,
                }
            }

            async for chunk in agent.stream(inputs, session,
                                            [BaseStreamMode.OUTPUT, BaseStreamMode.TRACE, BaseStreamMode.CUSTOM]):
                chunk_type = getattr(chunk, "type", None)

                # 第一次 llm_output 时发送 LLM 开始事件
                if chunk_type == "llm_output" and is_first_llm_call:
                    is_first_llm_call = False
                    llm_invoke_id = str(uuid.uuid4())
                    adapter.set_llm_invoke_id(llm_invoke_id)
                    adapter.set_llm_inputs(llm_inputs)
                    adapter.set_llm_meta_data(llm_meta_data)
                    adapter.add_child_invoke_id(llm_invoke_id)
                    adapter._is_llm_call_started = True

                    yield adapter.create_agent_node_start_event(
                        invoke_id=llm_invoke_id,
                        chain_id=chain_id,
                        invoke_type="llm",
                        name="Openai",
                        inputs=llm_inputs,
                        meta_data=llm_meta_data,
                    )

                # 处理 chunk，适配器会自动生成对应事件
                for event in adapter.adapt(chunk):
                    if event:
                        yield event

            # 发送 Agent 链结束事件
            yield adapter.create_agent_node_end_event(
                invoke_id=chain_id,
                chain_id=chain_id,
                invoke_type="chain",
                name=ir_json.get("agentName", "Agent"),
                inputs={"query": query},
                outputs=adapter.final_output,
                child_invokes=adapter.child_invoke_ids,
            )

        except Exception as e:
            workflow_logger.error(f"ReActAgent stream failed: {e}", exc_info=True)
            yield adapter.adapt_error(f"Agent execution failed: {e}")
        finally:
            if session:
                await session.post_run()

    async def run_blocking(self, req: ExecutionRequest) -> str:
        """运行 ReActAgent 并返回完整的 LLM 响应字符串"""
        result_parts = []
        async for chunk in self.run_streaming(req):
            if chunk is None:
                continue
            try:
                chunk_str = chunk.decode() if isinstance(chunk, bytes) else chunk
                if chunk_str.startswith("data: "):
                    data = json.loads(chunk_str[6:])
                    if data.get("event") == "message":
                        answer = data.get("data", {}).get("answer", "")
                        if answer:
                            result_parts.append(answer)
            except Exception as e:
                workflow_logger.error(f"Error processing agent run blocking chunk: {e}")
                pass

        return "".join(result_parts)