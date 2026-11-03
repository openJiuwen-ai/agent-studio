#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import List, Dict, Tuple, Union

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.controller.common.config import ControlModeConfig
from jiuwen.controller.common.message import Message
from jiuwen.controller.common.message_type import MessageType, MessageSubType
from jiuwen.controller.context_manager.workflow_context import WorkflowContext
from jiuwen.integration import AgentCoreMcpLayer
from jiuwen.orchestration import Invokable
from jiuwen.orchestration.common.exception import TaskPluginException
from jiuwen.orchestration.flow.enum import ExecutionStatus
from jiuwen.planner.common.exception import WorkflowParseException
from jiuwen.plugin import Param
from jiuwen.plugin import PluginManager
from jiuwen.plugin.models.function import Function
from jiuwen.plugin.models.mcpapi import McpAPI
from jiuwen.plugin.models.param import WORKFLOW_NAME, DESCRIPTION, WORKFLOW_PROMPT
from jiuwen.plugin.models.plugin import BasePlugin
from jiuwen.plugin.models.restfulapi import RestFulAPI
from openjiuwen.core.foundation.tool import Tool


class ToolFormatter:
    """
    工具格式化工具类

    将插件、工作流、MCP 等格式化为 LLM 可用的标准 Function Calling 格式
    遵循 OpenAI Function Calling 规范
    """

    @staticmethod
    def format_tools(plugins=None, mcps=None, workflow_contexts=None):
        """
        格式化插件、工作流和MCP工具为标准接口格式

        遵循 OpenAI Function Calling 规范，返回格式：
        {
            "name": "工具名",
            "description": "工具描述",
            "parameters": {
                "type": "object",
                "properties": {...},
                "required": [...]
            }
        }

        Args:
            plugins: 插件列表，可以是 Function 或 BasePlugin 对象的列表
            mcps: MCP 工具列表
            workflow_contexts: 工作流上下文字典 {workflow_id: WorkflowContext}

        Returns:
            list: 格式化后的工具列表
        """
        formatted_tools = []

        # 处理插件
        if plugins:
            for plugin in plugins:
                formatted_tool = ToolFormatter.format_single_plugin(plugin)
                if formatted_tool:
                    formatted_tools.append(formatted_tool)

        # 处理工作流上下文
        if workflow_contexts:
            for _, context in workflow_contexts.items():
                formatted_tool = ToolFormatter.format_workflow_context(context)
                if formatted_tool:
                    formatted_tools.append(formatted_tool)

        # 处理 MCPs
        if mcps:
            for mcp in mcps:
                formatted_tool = ToolFormatter.format_mcp(mcp)
                if formatted_tool:
                    formatted_tools.append(formatted_tool)

        return formatted_tools

    @staticmethod
    def format_single_plugin(plugin):
        """
        格式化单个插件为标准 Function Calling 格式

        Args:
            plugin: 插件对象，可以是 Function、BasePlugin、RestFulAPI 或其他类型

        Returns:
            dict: 格式化后的工具信息，如果无法格式化则返回 None
        """
        result = None
        try:
            if isinstance(plugin, (Function, BasePlugin, RestFulAPI)):
                # 使用标准的 Param.format_functions 方法格式化
                result = Param.format_functions(plugin)
            else:
                # 对于其他类型（如 Mock 对象），手动构建标准格式
                result = ToolFormatter._format_non_standard_plugin(plugin)
        except Exception as e:
            logger.warning(f"Failed to format plugin: {e}")
        return result

    @staticmethod
    def format_workflow_context(context):
        """
        格式化工作流上下文为标准 Function Calling 格式

        Args:
            context: WorkflowContext 对象

        Returns:
            dict: 格式化后的工具信息
        """
        try:
            if all(
                [
                    key in context.workflow_parameters
                    for key in ["name", "description", "parameters"]
                ]
            ):
                # 如果已经有这些字段，直接使用
                workflow_info = context.workflow_parameters
            else:
                workflow_info = {
                    "name": context.workflow_name,
                    "description": context.description,
                    "parameters": context.workflow_parameters,
                }

            # 过滤可见参数
            return ToolFormatter._filter_visible_parameters(workflow_info)
        except Exception as e:
            logger.warning(f"Failed to format workflow context: {e}")
            return None

    @staticmethod
    def format_mcp(mcp):
        """
        格式化 MCP 工具为标准 Function Calling 格式

        Args:
            mcp: MCP 对象

        Returns:
            dict: 格式化后的工具信息
        """
        try:
            return {
                "name": mcp.name,
                "description": mcp.description,
                "parameters": mcp.parameters,
            }
        except Exception as e:
            logger.warning(f"Failed to format MCP: {e}")
            return None

    @staticmethod
    def _format_non_standard_plugin(plugin):
        """
        格式化非标准插件为 Function Calling 格式

        Args:
            plugin: 非标准插件对象

        Returns:
            dict: 格式化后的工具信息，如果无法获取必要信息则返回 None
        """
        # 获取名称
        plugin_name = ToolFormatter._get_plugin_name(plugin)
        if not plugin_name:
            return None

        # 获取描述
        plugin_desc = ToolFormatter._get_plugin_description(plugin)

        # 获取参数
        plugin_params = ToolFormatter._get_plugin_parameters(plugin)

        return {
            "name": plugin_name,
            "description": plugin_desc,
            "parameters": plugin_params,
        }

    @staticmethod
    def _get_plugin_name(plugin) -> str:
        """获取插件名称"""
        if hasattr(plugin, "name"):
            name = plugin.name
            if isinstance(name, str):
                return name
            if callable(name):
                try:
                    return str(name())
                except Exception:
                    return ""
        if hasattr(plugin, "__name__"):
            return str(plugin.__name__)
        return getattr(plugin, "_name", "") or ""

    @staticmethod
    def _get_plugin_description(plugin) -> str:
        """获取插件描述"""
        if hasattr(plugin, "description"):
            desc = plugin.description
            if isinstance(desc, str):
                return desc
            if callable(desc):
                try:
                    return str(desc())
                except Exception:
                    return ""
            if desc is not None:
                return str(desc)
        return ""

    @staticmethod
    def _get_plugin_parameters(plugin) -> dict:
        """获取插件参数，确保返回标准格式"""
        default_params = {"type": "object", "properties": {}, "required": []}

        if hasattr(plugin, "parameters"):
            params = plugin.parameters
            if isinstance(params, dict):
                # 检查是否已经是标准格式
                if "type" in params and "properties" in params:
                    return params
                # 如果是简单的属性字典，包装成标准格式
                return {
                    "type": "object",
                    "properties": params,
                    "required": list(params.keys()) if params else [],
                }
            if callable(params):
                try:
                    result = params()
                    if isinstance(result, dict):
                        if "type" in result and "properties" in result:
                            return result
                        return {
                            "type": "object",
                            "properties": result,
                            "required": list(result.keys()) if result else [],
                        }
                except Exception:
                    return default_params

        # 尝试使用 params 属性（Param 列表）
        if hasattr(plugin, "params") and plugin.params:
            try:
                properties = Param.format_functions_for_complex(plugin.params, {})
                required = properties.pop("required", [])
                return {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                }
            except Exception:
                return default_params

        return default_params

    @staticmethod
    def _filter_visible_parameters(workflow_info: dict) -> dict:
        """
        过滤工作流参数，只保留可见的参数

        Args:
            workflow_info: 工作流信息字典

        Returns:
            dict: 过滤后的工作流信息
        """
        filtered_info = {
            "name": workflow_info.get("name"),
            "description": workflow_info.get("description", ""),
        }

        parameters = workflow_info.get("parameters", {})
        if isinstance(parameters, dict) and "properties" in parameters:
            visible_properties = {}
            for key, value in parameters.get("properties", {}).items():
                if isinstance(value, dict) and value.get("visible", True):
                    visible_properties[key] = value

            filtered_info["parameters"] = {
                "type": parameters.get("type", "object"),
                "properties": visible_properties,
                "required": [
                    r for r in parameters.get("required", []) if r in visible_properties
                ],
            }
        else:
            filtered_info["parameters"] = parameters

        return filtered_info


class AgentUtils:
    """Agent工具类，用于处理Agent相关的工具操作"""

    @staticmethod
    def verify_task_id(task_id: str = None, max_length: int = 32) -> str:
        """验证任务ID，如果为None则生成新ID，确保长度不超过限制

        Args:
            task_id (str, optional): 任务ID，如果为None则自动生成
            max_length (int): 最大长度限制，默认为32

        Returns:
            str: 验证通过的任务ID

        Raises:
            JiuWenBaseException: 当任务ID长度超过限制时抛出异常
        """
        if task_id is None:
            import secrets

            return secrets.token_hex(16)

        if len(task_id) > max_length:
            raise JiuWenBaseException(
                error_code=StatusCode.AGENT_TASK_ID_INVALID_ERROR.code,
                message=StatusCode.AGENT_TASK_ID_INVALID_ERROR.errmsg.format(
                    max_length
                ),
            )
        return task_id

    @staticmethod
    def create_controller_config(model=None, plan_config=None, task_id=None, **kwargs):
        """创建控制器配置字典

        Args:
            model: 模型实例
            plan_config: 规划配置
            task_id: 任务ID
            **kwargs: 其他配置参数，包括plugins、workflows、context_manager等

        Returns:
            ControlModeConfig: 控制器配置对象
        """
        return ControlModeConfig(
            **{
                "model": model,
                "plan_config": plan_config,
                "task_id": task_id,
                "plugins": kwargs.get("plugins"),
                "workflows": kwargs.get("workflows", []),
                "context_manager": kwargs.get("context_manager"),
            }
        )

    @staticmethod
    def process_input(
        inputs: Union[dict, str],
        query_key: str = "query",
        prompt_key: str = "prompt_info",
    ) -> Tuple[str, dict]:
        """处理输入，统一处理字符串或字典类型的输入

        Args:
            inputs (Union[dict, str]): 输入数据，可以是字典或字符串
            query_key (str): 查询键名，默认为"query"
            prompt_key (str): 提示信息键名，默认为"prompt_info"

        Returns:
            Tuple[str, dict]: (查询字符串, 提示信息字典)

        Raises:
            JiuWenBaseException: 当输入类型不支持时抛出异常
        """
        if isinstance(inputs, dict):
            query = inputs.get(query_key, "")
            prompt_info = inputs.get(prompt_key)
        elif isinstance(inputs, str):
            query = inputs
            prompt_info = None
        else:
            raise JiuWenBaseException(
                error_code=StatusCode.AGENT_INPUT_TYPE_ERROR.code,
                message=StatusCode.AGENT_INPUT_TYPE_ERROR.errmsg.format(type(inputs)),
            )
        return query, prompt_info

    @staticmethod
    def get_interrupted_workflows(workflows: list) -> list:
        """获取被中断的工作流状态列表

        Args:
            workflows (list): 工作流列表

        Returns:
            list: 被中断的工作流状态列表
        """
        interrupted_states = []
        if not workflows:
            return interrupted_states

        for workflow in workflows:
            if (
                workflow.invokable.get_workflow_execute_status()
                == ExecutionStatus.USER_INTERACT
            ):
                interrupted_states.append(workflow.invokable.get_state())
        return interrupted_states


class WorkspaceUtils:
    """
    工作空间工具类，用于管理工作流和插件
    """

    @staticmethod
    def get_workflow_params(workflow_ir: dict) -> dict:
        """格式化workflow Panel接口

        Args:
            workflow_ir (dict): 工作流IR定义

        Returns:
            dict: 格式化后的工作流参数，包含名称、描述和参数定义

        Raises:
            WorkflowParseException: 当解析失败时抛出异常
        """
        components_list = workflow_ir.get("components", {})

        if len(components_list) == 0:
            raise WorkflowParseException(message="get workflow start node failed")
        for component in components_list:
            if component.get("type", "") == "jiuwen.start":
                start_node = component
                break
        else:
            raise WorkflowParseException(message="get workflow start node failed")

        properties = dict()
        input_param = start_node.get("inputs", {})
        if not input_param:
            raise WorkflowParseException(
                message="get workflow start node param is null"
            )
        configs = start_node.get("configs", dict())
        system_fields = configs.get("systemFields", dict()).get("inputs", list())
        sys_params_with_desc = {
            _.get("id"): {
                "description": _.get("description", ""),
                "type": _.get("type", ""),
                "required": _.get("required", False),
            }
            for _ in system_fields
            if _.get("id") is not None and _.get("id", "") != "sys"
        }
        user_fields = configs.get("userFields", dict()).get("inputs", list())
        user_params_with_desc = WorkspaceUtils.transform_fields_to_dict(user_fields)
        properties.update(sys_params_with_desc)
        properties.update(user_params_with_desc)
        workflow_info = dict(
            name=workflow_ir.get(WORKFLOW_NAME),
            description=workflow_ir.get(DESCRIPTION, "") + WORKFLOW_PROMPT,
            parameters=dict(type="object", properties=properties),
        )
        return workflow_info

    @staticmethod
    def transform_fields_to_dict(fields):
        """
        将 user_fields 列表转换为以 id 为 key 的嵌套 dict，
        并将 object 类型的 schema 递归转换为 properties (dict)。
        """

        def normalize_type(t: str) -> str:
            mapping = {
                "String": "string",
                "Number": "number",
                "Boolean": "boolean",
            }
            return mapping.get(t, t.lower())

        result = {}
        for field in fields:
            field_id = field.get("id")
            if field_id is None:
                continue

            base = {
                "description": field.get("description", ""),
                "type": normalize_type(field.get("type", "")),
                "required": field.get("required", False),
            }

            # 如果是 object 且有 schema，递归处理 schema 并转为 properties (dict)
            if base["type"] == "object" and "schema" in field:
                base["properties"] = WorkspaceUtils.transform_fields_to_dict(
                    field["schema"]
                )

            result[field_id] = base

        return result

    @staticmethod
    def get_plugin_from_list(plugin_functions: list) -> list:
        """从插件列表中获取函数

        Args:
            plugin_functions (list): 插件或函数列表

        Returns:
            list: 函数列表，支持Function、RestfulAPI、FunctionPlugin、RestfulAPIPlugin等类型
        """
        functions = list()
        # support plugin_functions belong to Function, RestfulAPI, FunctionPlugin, RestfulAPIPlugin
        for plugin_or_function in plugin_functions:
            if isinstance(plugin_or_function, BasePlugin):
                if getattr(plugin_or_function, "function_map", None):
                    functions.extend(plugin_or_function.function_map.values())
                else:
                    functions.extend(plugin_or_function.api_map.values())
            else:
                functions.append(plugin_or_function)
        return functions

    @staticmethod
    def plugin_operate(
        result: dict, intent: str, plugin_err_code=None
    ) -> List[Invokable]:
        """处理插件操作结果

        Args:
            result (dict): 操作结果字典
            intent (str): 操作意图描述
            plugin_err_code: 插件错误代码枚举，用于判断操作是否成功

        Returns:
            List[Invokable]: 可调用对象列表

        Raises:
            TaskPluginException: 当插件操作失败时抛出异常
        """
        code = result.get("code")
        if code != plugin_err_code.SUCCESS:
            msg = (
                f"{intent} failed ({code=}) with error message: {result.get('message')}"
            )
            logger.error(
                f"Plugin operate failed: intent={intent}, code={code}, message={msg}",
                simple_log="Plugin operate failed.",
            )
            raise TaskPluginException(
                StatusCode.TASK_PLUGIN_OPERATE_ERROR.code,
                StatusCode.TASK_PLUGIN_OPERATE_ERROR.errmsg.format(
                    intent, code, result.get("message")
                ),
            )
        ret = result.get("body")
        if not ret:
            logger.warning("Intent succeed but with empty result.")
        return ret if isinstance(ret, list) else [ret]

    @staticmethod
    def init_plugins(plugins, plugin_manager=None):
        """初始化插件

        Args:
            plugins: 插件定义，可以是字典、字符串、实例或列表
            plugin_manager: 插件管理器实例，如果为None则创建新实例

        Returns:
            list: 初始化后的插件列表

        Raises:
            ValueError: 当插件类型不支持时抛出异常
        """
        if plugin_manager is None:
            plugin_manager = PluginManager()

        if plugins:
            # plugin names in dict
            if isinstance(plugins, dict):
                functions = WorkspaceUtils.get_plugin_from_dict(plugins, plugin_manager)
            # plugin name
            elif isinstance(plugins, str):
                functions = WorkspaceUtils.get_plugin_by_name(plugins, plugin_manager)
            # plugin instance
            elif isinstance(plugins, (BasePlugin, Invokable)):
                functions = [plugins]
            # plugin instance list
            elif isinstance(plugins, list):
                functions = plugins
            else:
                raise ValueError("Unsupported type for plugin functions")
        else:
            functions = []

        functions = WorkspaceUtils.get_plugin_from_list(functions)
        return functions

    @staticmethod
    async def gen_tools(
        input_content: str, plugins=None, workflows=None, mcps=None, **kwargs
    ):
        """生成插件和工作流工具列表

        Args:
            input_content (str): 用户输入内容
            plugins (list, optional): 插件列表
            workflows (list, optional): 工作流列表
            mcps (list, optional): mcp列表
            **kwargs: 其他参数，包括：
                plugin_retrieve_enable (bool): 是否启用插件检索
                top_k (int): 检索时返回的最大插件数量
                plugin_manager: 插件管理器实例，如果为None则创建新实例
                workflow_map (dict): 工作流映射字典，如果为None则创建新字典

        Returns:
            tuple: (plugins列表, workflows列表, mcps列表)，均为Tool对象列表
        """
        plugin_retrieve_enable = kwargs.get("plugin_retrieve_enable", False)
        top_k = kwargs.get("top_k", 3)
        plugin_manager = kwargs.get("plugin_manager", None)
        workflow_map = kwargs.get("workflow_map", None)
        if plugin_manager is None:
            plugin_manager = PluginManager()

        if workflow_map is None:
            workflow_map = {}

        plugin_tools = []

        # 处理插件
        if plugins is None:
            plugins = []

        output_plugins = WorkspaceUtils.get_all_plugins(
            input_content, plugins, plugin_retrieve_enable, top_k, plugin_manager
        )

        for plugin in output_plugins:
            if not isinstance(plugin, Invokable):
                logger.error("plugin type error while wrap plugin into Tool")
                continue
            plugin_tools.append(plugin)

        mcps = await WorkspaceUtils.get_all_mcp_apis(
            mcps,
            agent_id=kwargs.get("agent_id", ""),
            session_id=getattr(kwargs.get("runtime_context"), "conversation_id", "")
            or "",
        )
        return plugin_tools, workflows, mcps

    @staticmethod
    def update_tool_switch(
        plugins: Union[List[Union[Function, BasePlugin]]] = None,
        workflows=None,
        tool_switch_dict: Dict = None,
    ):
        """根据开关配置筛选启用的插件和工作流工具

        Args:
            plugins (Union[List[Union[Function, BasePlugin]], optional): 插件工具列表
            workflows (list, optional): 工作流工具列表
            tool_switch_dict (Dict, optional): 工具开关配置字典，键为工具ID，值为布尔值表示是否启用

        Returns:
            tuple: (更新后的插件列表, 更新后的工作流列表)
        """

        # 如果没有提供开关配置，直接返回原始列表
        if tool_switch_dict is None:
            return plugins or [], workflows or []

        updated_plugins = []
        updated_workflows = []
        exist_ids = []

        # 处理插件工具
        if plugins:
            for plugin in plugins:
                cur_id = plugin.id
                exist_ids.append(cur_id)

                # 检查工具是否启用，默认为True
                enable = tool_switch_dict.get(cur_id, True)

                if not enable:
                    logger.info(f"react skip plugin tool {cur_id}")
                    continue

                updated_plugins.append(plugin)

        # 处理工作流工具
        if workflows:
            for workflow in workflows:
                cur_id = workflow.workflow_id
                exist_ids.append(cur_id)

                # 检查工具是否启用，默认为True
                enable = tool_switch_dict.get(cur_id, True)

                if not enable:
                    logger.info(f"react skip workflow tool {cur_id}")
                    continue

                updated_workflows.append(workflow)

        # 检查是否存在无效的工具ID
        tool_ids = list(tool_switch_dict.keys())
        differ_ids = set(tool_ids).difference(set(exist_ids))
        if differ_ids:
            logger.error(f"tool switch includes invalid ids {list(differ_ids)}")

        return updated_plugins, updated_workflows

    @staticmethod
    def get_plugin_from_dict(
        plugin_dict: Dict[str, List[str]], plugin_manager
    ) -> List[Invokable]:
        """从插件字典中获取插件

        Args:
            plugin_dict (Dict[str, List[str]]): 插件名称到函数名列表的映射
            plugin_manager: 插件管理器实例

        Returns:
            List[Invokable]: 可调用对象列表

        Raises:
            TaskPluginException: 当插件操作失败时抛出异常
        """
        function_or_api_list = list()
        for plugin_name, functions_or_rest_apis in plugin_dict.items():
            if not isinstance(functions_or_rest_apis, (list, tuple, set)):
                msg = (
                    f"The functions of plugin {plugin_name} should be a list/tuple/set of str"
                    f" but got {type(functions_or_rest_apis).__name__}"
                )
                logger.error(msg)
                raise TaskPluginException(
                    StatusCode.TASK_PLUGIN_TYPE_ERROR.code,
                    StatusCode.TASK_PLUGIN_TYPE_ERROR.errmsg.format(
                        plugin_name, type(functions_or_rest_apis).__name__
                    ),
                )
            for func_name in functions_or_rest_apis:
                # Plugin name and function name are checked by plugin_manager.
                function_or_api_list.extend(
                    WorkspaceUtils.plugin_operate(
                        plugin_manager.get(
                            plugin_name=plugin_name, func_name=func_name
                        ),
                        f"Get plugin by {plugin_name=} and {func_name=}",
                    )
                )
        return function_or_api_list

    @staticmethod
    def get_plugin_by_name(plugin_name: str, plugin_manager) -> List[Invokable]:
        """通过名称获取插件

        Args:
            plugin_name (str): 插件名称
            plugin_manager: 插件管理器实例

        Returns:
            List[Invokable]: 可调用对象列表
        """
        return WorkspaceUtils.plugin_operate(
            plugin_manager.get(plugin_name=plugin_name), f"Get plugin by {plugin_name=}"
        )

    @staticmethod
    def get_all_plugins(
        instruction, plugins, plugin_retrieve_enable, top_k, plugin_manager
    ) -> list:
        """返回用户输入和推荐插件的合集

        Args:
            instruction (str): 用户指令
            plugins (list): 插件列表
            plugin_retrieve_enable (bool): 是否启用插件检索
            top_k (int): 检索时返回的最大插件数量
            plugin_manager: 插件管理器实例

        Returns:
            list: 插件列表，包含用户指定插件和推荐插件
        """
        output_plugins = list()
        if plugin_retrieve_enable:
            recommend_plugins = plugin_manager.retrieve(query=instruction, top_k=top_k)
            redundant_plugins = recommend_plugins
            if plugins and isinstance(plugins, list):
                redundant_plugins += plugins
            for plugin in redundant_plugins:
                if plugin in output_plugins:
                    continue
                output_plugins.append(plugin)
        else:
            output_plugins = plugins
        return output_plugins

    @staticmethod
    async def _resolve_mcp_tool_id(
        server_id: str, server_name: str, tool_name: str, agent_id: str
    ) -> str:
        """Resolve the MCP tool id from resource registry and fall back to the open-source convention."""
        try:
            from openjiuwen.core.runner import Runner

            tool = await Runner.resource_mgr.get_mcp_tool(
                name=tool_name,
                server_id=server_id,
                server_name=server_name,
                tag=agent_id,
            )
            if isinstance(tool, Tool):
                return tool.card.id
            elif isinstance(tool, list) and len(tool) > 0:
                tool = tool[0]
                if tool is not None:
                    return tool.card.id
        except Exception:
            logger.warning(
                "failed to resolve MCP tool id from resource registry, fallback to convention"
            )

        return f"{server_id}.{server_name}.{tool_name}"

    @staticmethod
    async def get_all_mcp_apis(mcps, agent_id="", session_id="") -> list:
        """获取所有MCP服务器的API

        Args:
            mcps (list): MCP服务器列表
            runtime_context: 运行时上下文，用于透传 conversation_id 作为 MCP session_id

        Returns:
            list: MCP API列表
        """
        if not mcps:
            return []

        wrapped_mcps = []
        for mcp in mcps:
            if isinstance(mcp, AgentCoreMcpLayer) or (
                getattr(mcp, "is_mcp", False)
                and getattr(mcp, "mcp_api", None) is not None
            ):
                wrapped_mcps.append(mcp)
                continue

            mcp_tools = await mcp.ainvoke(inputs={})
            if not mcp_tools:
                continue

            for mcp_tool in mcp_tools.tools:
                mcp_api = McpAPI(
                    server_url=mcp.server_url,
                    name=mcp_tool.name,
                    parameters=mcp_tool.inputSchema,
                    headers=mcp.headers,
                    description=mcp_tool.description,
                    server_name=mcp.name,
                    transport_type=mcp.transport_type,
                    plugin_dependency=mcp.plugin_dependency,
                    auth=mcp.auth,
                )
                tool_id = await WorkspaceUtils._resolve_mcp_tool_id(
                    server_id=mcp.name,
                    server_name=mcp.name,
                    tool_name=mcp_tool.name,
                    agent_id=agent_id,
                )
                wrapped_mcps.append(
                    AgentCoreMcpLayer(
                        mcp_api=mcp_api,
                        tool_id=tool_id,
                        agent_id=agent_id,
                        session_id=session_id,
                    )
                )
        return wrapped_mcps


class MessageConverter:
    """消息转换工具类"""

    @staticmethod
    def create_user_input_message(query: str, runtime_data: dict) -> Message:
        """创建用户输入消息

        Args:
            query (str): 用户查询内容
            runtime_data (dict): 运行时数据，应包含 prompt_info, plugins, workflows 等

        Returns:
            Message: 用户输入消息对象
        """
        return Message(
            message_type=MessageType.USER_INPUT,
            content=query,
            runtime_data=runtime_data,
        )

    @staticmethod
    def create_plugin_completion_message(
        plugin_name: str, exec_res: dict, runtime_data=None
    ) -> Message:
        """创建插件完成消息

        Args:
            plugin_name (str): 插件名称
            exec_res (dict): 执行结果
            runtime_data (dict, optional): 运行时数据，应包含 prompt_info, plugins, workflows 等

        Returns:
            Message: 插件完成消息对象
        """
        return Message(
            message_type=MessageType.PLUGIN_COMPLETION,
            content={"plugin_name": plugin_name, "exec_res": exec_res},
            runtime_data=runtime_data,
        )

    @staticmethod
    def create_mcp_completion_message(
        mcp_name: str, exec_res: dict, runtime_data=None
    ) -> Message:
        """创建MCP完成消息

        Args:
            mcp_name (str): MCP服务器名称
            exec_res (dict): 执行结果
            runtime_data (dict, optional): 运行时数据，应包含 prompt_info, plugins, workflows 等

        Returns:
            Message: MCP完成消息对象
        """
        return Message(
            message_type=MessageType.MCP_COMPLETION,
            content={"mcp_name": mcp_name, "exec_res": exec_res},
            runtime_data=runtime_data,
        )

    @staticmethod
    def create_end_message_from_controller_message(
        fix_message: str, terminate: bool, **kwargs
    ) -> Message:
        """创建控制器结束消息

        Args:
            fix_message (str): 修复消息内容
            terminate (bool): 是否终止
            **kwargs: 其他关键字参数

        Returns:
            Message: 控制器结束消息对象
        """
        content = {"message": fix_message, "terminate": terminate}

        for key, value in kwargs.items():
            if value is not None:
                content[key] = value

        return Message(
            message_type=MessageType.WORKFLOW_MESSAGE,
            content=content,
        )

    @staticmethod
    def create_workflow_completion_message(
        workflow_context: WorkflowContext, exec_res: dict, runtime_data=None
    ) -> Message:
        """创建工作流完成消息

        Args:
            workflow_context (WorkflowContext): 工作流上下文
            exec_res (dict): 执行结果
            runtime_data (dict, optional): 运行时数据，应包含 prompt_info, plugins, workflows 等

        Returns:
            Message: 工作流完成消息对象
        """
        return Message(
            message_type=MessageType.WORKFLOW_COMPLETION,
            content={
                "workflow_name": workflow_context.workflow_name,
                "workflow_id": workflow_context.workflow_id,
                "workflow_type": workflow_context.type,
                "exec_res": exec_res,
            },
            runtime_data=runtime_data,
        )

    @staticmethod
    def create_workflow_interrupt_from_questioner_message(
        workflow_name: str, exec_res: dict, runtime_data=None
    ) -> Message:
        """创建提问器工作流中断消息

        Args:
            workflow_name (str): 工作流名称
            exec_res (dict): 执行结果
            runtime_data (dict, optional): 运行时数据，应包含 prompt_info, plugins, workflows 等

        Returns:
            Message: 提问器组件的中断消息对象
        """
        return Message(
            message_type=MessageType.WORKFLOW_INTERRUPT,
            content={"workflow_name": workflow_name, "exec_res": exec_res},
            runtime_data=runtime_data,
            sub_type=MessageSubType.QUESTIONER_ASK,
        )

    @staticmethod
    def create_workflow_interrupt_from_controller_message(
        workflow_name: str, question: str, runtime_data=None
    ) -> Message:
        """创建控制器工作流中断消息

        Args:
            workflow_name (str): 工作流名称
            question (str): 问题内容
            runtime_data (dict, optional): 运行时数据，应包含 prompt_info, plugins, workflows 等

        Returns:
            Message: 控制器自主追问的中断消息对象
        """
        return Message(
            message_type=MessageType.WORKFLOW_INTERRUPT,
            content={"workflow_name": workflow_name, "question": question},
            runtime_data=runtime_data,
            sub_type=MessageSubType.CONTROLLER_ASK,
        )
