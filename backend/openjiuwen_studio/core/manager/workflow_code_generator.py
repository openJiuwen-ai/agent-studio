#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""
Workflow Python Code Generator

Converts a DSL Workflow object into a runnable Python script that uses the
openjiuwen SDK, mirroring the style of the example Jupyter notebooks.
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple, NamedTuple

logger = logging.getLogger(__name__)

from openjiuwen_studio.core.common import dsl
from openjiuwen_studio.core.common.dsl import (
    ComponentType, LLMConfig, IntentDetectionConfig, QuestionerConfig,
    EndConfig, ToolCompConfig, RestfulApiSchema, PluginCodeConfig,
    CodeConfig, TextEditorConfig, VariMergeConfig, SetVariableConfig,
    LoopConfig, ExecSubWfConfig, UserInputsConfig, UserOutputConfig,
    PluginType
)

# Maps DSL client provider names to SDK provider names
_CLIENT_PROVIDER_MAP = {
    "siliconflow": "SiliconFlow",
    "openai": "OpenAI",
    "azure": "Azure",
    "ollama": "Ollama",
}


def _map_client_provider(raw: str) -> str:
    """Normalize client_provider to the format expected by the SDK."""
    return _CLIENT_PROVIDER_MAP.get((raw or "").lower(), raw or "")


class ModelParams(NamedTuple):
    """Encapsulates extracted model configuration parameters."""
    client_provider: str
    api_key_env: str
    api_base: str
    model_name: str
    temperature: float
    top_p: float
    timeout: float


def _repr_str(s: Any) -> str:
    """Return a repr of a string value, with None safety."""
    if s is None:
        return '""'
    return repr(str(s))


def _indent(code: str, spaces: int = 4) -> str:
    """Indent every line of code by the given number of spaces."""
    pad = " " * spaces
    return "\n".join(pad + line if line.strip() else line for line in code.splitlines())


class WorkflowCodeGenerator:
    """
    Generates a standalone Python script from a DSL Workflow object.

    The generated script:
    - Imports the necessary openjiuwen SDK classes
    - Defines a function for each component
    - Assembles the workflow using the SDK Workflow builder
    - Creates a WorkflowAgent and exposes a runnable main() async function
    """

    def __init__(self, workflow: dsl.Workflow) -> None:
        self.workflow = workflow
        # Build lookup structures for connections and branch targets
        self._non_branch_connections: List[Tuple[str, str]] = []
        self._branch_targets: Dict[Tuple[str, str], List[str]] = {}  # (comp_id, branch_id) -> targets
        self._build_connection_maps()

        # Track which import groups are needed
        self._need_llm_imports = False
        self._need_intent_imports = False
        self._need_questioner_imports = False
        self._need_branch_imports = False
        self._need_plugin_service_imports = False
        self._need_plugin_code_imports = False
        self._need_code_imports = False
        self._need_text_editor_imports = False
        self._need_vari_merge_imports = False
        self._need_loop_imports = False
        self._need_sub_workflow_imports = False
        self._need_user_input_imports = False
        self._need_user_output_imports = False

        self._comp_var_names: Dict[str, str] = {}  # comp_id -> variable name used in build_workflow
        self._comp_type_map: Dict[str, ComponentType] = {}  # comp_id -> type

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self) -> str:
        """Return the complete Python file as a string."""
        # First pass: generate component functions (populates import flags)
        comp_function_blocks = self._gen_all_component_functions()

        # Build the file in order
        sections: List[str] = [
            self._gen_header(),
            self._gen_imports(),
            self._gen_workflow_metadata(),
            self._gen_model_config_helper(),
            comp_function_blocks,
            self._gen_build_workflow(),
            self._gen_main(),
        ]
        return "\n".join(sections)

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    def _build_connection_maps(self) -> None:
        for conn in self.workflow.connections:
            source = conn.source
            if isinstance(source, list):
                # Multi-source connections: add each source → target pair
                for s in source:
                    if conn.branch_id:
                        self._branch_targets.setdefault((s, conn.branch_id), []).append(conn.target)
                    else:
                        self._non_branch_connections.append((s, conn.target))
            else:
                if conn.branch_id:
                    self._branch_targets.setdefault((source, conn.branch_id), []).append(conn.target)
                else:
                    self._non_branch_connections.append((source, conn.target))

    def _get_branch_targets(self, comp_id: str, branch_id: str) -> List[str]:
        return self._branch_targets.get((comp_id, branch_id), [])

    # ------------------------------------------------------------------
    # File sections
    # ------------------------------------------------------------------

    def _gen_header(self) -> str:
        wf = self.workflow
        return (
            f"#!/usr/bin/env python3\n"
            f"# -*- coding: UTF-8 -*-\n"
            f"# Auto-generated workflow runner\n"
            f"# Workflow name   : {wf.name}\n"
            f"# Workflow ID     : {wf.id}\n"
            f"# Workflow version: {wf.version or '1.0.0'}\n"
            f"#\n"
            f"# Usage:\n"
            f"#   pip install -U openjiuwen\n"
            f"#   Set environment variables for LLM credentials (see below)\n"
            f"#   python <this_file>.py\n"
        )

    def _gen_imports(self) -> str:
        lines = [
            "import os",
            "import asyncio",
            "",
        ]

        # Core workflow imports - always needed
        core_wf_imports = [
            "Start",
            "End",
            "Workflow",
            "WorkflowCard",
            "create_workflow_session",
        ]
        if self._need_llm_imports:
            core_wf_imports += ["LLMComponent", "LLMCompConfig"]
        if self._need_intent_imports:
            core_wf_imports += ["IntentDetectionComponent", "IntentDetectionCompConfig"]
        if self._need_questioner_imports:
            core_wf_imports += ["QuestionerComponent", "QuestionerConfig", "FieldInfo"]
        if self._need_branch_imports:
            core_wf_imports += ["BranchComponent"]
        if self._need_loop_imports:
            core_wf_imports += ["LoopComponent", "LoopGroup", "LoopBreakComponent", "LoopSetVariableComponent"]
        if self._need_sub_workflow_imports:
            core_wf_imports += ["SubWorkflowComponent"]
        if self._need_plugin_service_imports or self._need_plugin_code_imports:
            core_wf_imports += ["ToolComponent", "ToolComponentConfig"]

        lines.append(f"from openjiuwen.core.workflow import (")
        for name in sorted(set(core_wf_imports)):
            lines.append(f"    {name},")
        lines.append(")")

        if self._need_llm_imports:
            lines.append("from openjiuwen.core.foundation.llm import ModelRequestConfig, ModelClientConfig")
            lines.append("from openjiuwen.core.foundation.llm import SystemMessage, UserMessage")

        if self._need_plugin_service_imports or self._need_plugin_code_imports:
            lines.append("from openjiuwen.core.foundation.tool import RestfulApi, RestfulApiCard")

        if self._need_code_imports:
            lines.append("# Note: CodeComponent is an internal implementation detail; code plugins use PluginCodeTool")

        lines.append("")
        return "\n".join(lines)

    def _gen_workflow_metadata(self) -> str:
        wf = self.workflow
        inputs_props = wf.inputs.get("properties", {}) if isinstance(wf.inputs, dict) else {}
        inputs_repr = json.dumps(inputs_props, ensure_ascii=False, indent=4)

        return (
            f"\n# {'=' * 60}\n"
            f"# Workflow Metadata\n"
            f"# {'=' * 60}\n"
            f"WORKFLOW_ID = {_repr_str(wf.id)}\n"
            f"WORKFLOW_NAME = {_repr_str(wf.name)}\n"
            f"WORKFLOW_VERSION = {_repr_str(wf.version or '1.0.0')}\n"
            f"WORKFLOW_DESCRIPTION = {_repr_str(wf.description or '')}\n"
            f"\n"
            f"# Input schema for this workflow\n"
            f"WORKFLOW_INPUTS = {inputs_repr}\n"
        )

    def _gen_model_config_helper(self) -> str:
        if not (self._need_llm_imports or self._need_intent_imports or self._need_questioner_imports):
            return ""
        return (
            f"\n# {'=' * 60}\n"
            f"# LLM Model Configuration Helper\n"
            f"# {'=' * 60}\n"
            f"# API keys are read from environment variables.\n"
            f"# Override them by setting the environment variables before running.\n"
            f"\n"
            f"def _build_model_configs(\n"
            f"    client_provider: str,\n"
            f"    api_key_env_var: str,\n"
            f"    api_base: str,\n"
            f"    model_name: str,\n"
            f"    temperature: float = 0.7,\n"
            f"    top_p: float = 0.9,\n"
            f"    timeout: float = 120.0,\n"
            f") -> tuple:\n"
            f"    \"\"\"Build ModelClientConfig and ModelRequestConfig from parameters.\"\"\"\n"
            f"    client_config = ModelClientConfig(\n"
            f"        client_provider=client_provider,\n"
            f"        api_key=os.getenv(api_key_env_var, ''),\n"
            f"        api_base=api_base,\n"
            f"        timeout=timeout,\n"
            f"        max_retries=1,\n"
            f"        verify_ssl=False,\n"
            f"    )\n"
            f"    model_config = ModelRequestConfig(\n"
            f"        model=model_name,\n"
            f"        temperature=temperature,\n"
            f"        top_p=top_p,\n"
            f"    )\n"
            f"    return client_config, model_config\n"
        )

    # ------------------------------------------------------------------
    # Component functions
    # ------------------------------------------------------------------

    def _gen_all_component_functions(self) -> str:
        """Generate one Python function per component."""
        self._comp_var_names: Dict[str, str] = {}  # comp_id -> variable name used in build_workflow
        self._comp_type_map: Dict[str, ComponentType] = {}  # comp_id -> type

        parts = [
            f"\n# {'=' * 60}",
            f"# Component Definitions",
            f"# {'=' * 60}",
        ]

        # Track how many of each type we've seen for naming
        type_counts: Dict[str, int] = {}

        for comp in self.workflow.components:
            type_name = ComponentType(comp.type).name.lower().replace("component_type_", "")
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
            count = type_counts[type_name]
            var_name = f"{type_name}_{count}" if type_counts[type_name] > 1 else type_name
            # Use component name if available, sanitized
            if comp.name:
                sanitized = _sanitize_identifier(comp.name)
                var_name = sanitized if sanitized else var_name

            func_name = f"create_{var_name}_component"
            self._comp_var_names[comp.id] = var_name
            self._comp_type_map[comp.id] = comp.type

            fn_code = self._gen_component_function(comp, func_name)
            if fn_code:
                parts.append("")
                parts.append(fn_code)

        return "\n".join(parts)

    def _gen_component_function(self, comp: dsl.Component, func_name: str) -> Optional[str]:
        """Generate a create_X_component() function for a given DSL component."""
        ctype = comp.type

        if ctype == ComponentType.COMPONENT_TYPE_START:
            return self._gen_start_fn(comp, func_name)
        elif ctype == ComponentType.COMPONENT_TYPE_END:
            return self._gen_end_fn(comp, func_name)
        elif ctype == ComponentType.COMPONENT_TYPE_LLM:
            self._need_llm_imports = True
            return self._gen_llm_fn(comp, func_name)
        elif ctype == ComponentType.COMPONENT_TYPE_INTENT:
            self._need_intent_imports = True
            self._need_llm_imports = True
            return self._gen_intent_fn(comp, func_name)
        elif ctype == ComponentType.COMPONENT_TYPE_QUESTION:
            self._need_questioner_imports = True
            self._need_llm_imports = True
            return self._gen_questioner_fn(comp, func_name)
        elif ctype == ComponentType.COMPONENT_TYPE_IF:
            self._need_branch_imports = True
            return self._gen_branch_fn(comp, func_name)
        elif ctype == ComponentType.COMPONENT_TYPE_PLUGIN:
            return self._gen_plugin_fn(comp, func_name)
        elif ctype == ComponentType.COMPONENT_TYPE_CODE:
            self._need_code_imports = True
            return self._gen_code_fn(comp, func_name)
        elif ctype == ComponentType.COMPONENT_TYPE_TEXT_EDITOR:
            self._need_text_editor_imports = True
            return self._gen_text_editor_fn(comp, func_name)
        elif ctype == ComponentType.COMPONENT_TYPE_VARIABLE_MERGE:
            self._need_vari_merge_imports = True
            return self._gen_vari_merge_fn(comp, func_name)
        elif ctype == ComponentType.COMPONENT_TYPE_LOOP:
            self._need_loop_imports = True
            return self._gen_loop_fn(comp, func_name)
        elif ctype == ComponentType.COMPONENT_TYPE_SUB_WORKFLOW:
            self._need_sub_workflow_imports = True
            return self._gen_subworkflow_fn(comp, func_name)
        elif ctype == ComponentType.COMPONENT_TYPE_INPUT:
            self._need_user_input_imports = True
            return self._gen_user_input_fn(comp, func_name)
        elif ctype == ComponentType.COMPONENT_TYPE_OUTPUT:
            self._need_user_output_imports = True
            return self._gen_user_output_fn(comp, func_name)
        elif ctype in (
            ComponentType.COMPONENT_TYPE_EMPTY,
            ComponentType.COMPONENT_TYPE_EMPTY_START,
            ComponentType.COMPONENT_TYPE_EMPTY_END,
            ComponentType.COMPONENT_TYPE_CONTINUE,
        ):
            return self._gen_empty_fn(comp, func_name)
        elif ctype == ComponentType.COMPONENT_TYPE_BREAK:
            return self._gen_break_fn(comp, func_name)
        elif ctype == ComponentType.COMPONENT_TYPE_SET_VARIABLE:
            return self._gen_set_variable_fn(comp, func_name)
        else:
            return self._gen_unsupported_fn(comp, func_name)

    # ------------------------------------------------------------------
    # Individual component generators
    # ------------------------------------------------------------------

    @staticmethod
    def _gen_start_fn(comp: dsl.Component, func_name: str) -> str:
        comment = f"# Component ID: {comp.id}"
        return (
            f"def {func_name}():\n"
            f"    {comment}\n"
            f"    return Start()\n"
        )

    @staticmethod
    def _gen_end_fn(comp: dsl.Component, func_name: str) -> str:
        comment = f"# Component ID: {comp.id}"
        response_template = ""
        if comp.configs:
            try:
                end_cfg = EndConfig.model_validate(comp.configs)
                response_template = end_cfg.response_template or ""
            except Exception as e:
                logger.warning("Failed to parse EndConfig for component %s: %s", comp.id, e)
        if response_template:
            return (
                f"def {func_name}():\n"
                f"    {comment}\n"
                f"    return End({{\"response_template\": {_repr_str(response_template)}}})\n"
            )
        else:
            return (
                f"def {func_name}():\n"
                f"    {comment}\n"
                f"    return End()\n"
            )

    def _gen_llm_fn(self, comp: dsl.Component, func_name: str) -> str:
        comment = f"# Component ID: {comp.id}"
        configs = comp.configs or {}
        try:
            llm_cfg = LLMConfig.model_validate(configs)
        except Exception as e:
            return self._gen_error_fn(comp, func_name, str(e))

        client_provider, api_key_env, api_base, model_name, temperature, top_p, timeout = \
            self._extract_model_params(llm_cfg.model)

        template_repr = json.dumps(llm_cfg.template_content, ensure_ascii=False, indent=8)
        output_config_repr = json.dumps(llm_cfg.output_config, ensure_ascii=False, indent=8)
        response_fmt = str(llm_cfg.response_format_type) if llm_cfg.response_format_type else "text"

        # Build system/user message lines
        sys_msg_line = ""
        user_msg_line = ""
        for msg in (llm_cfg.template_content or []):
            if not isinstance(msg, dict):
                continue
            if msg.get("role") == "system":
                sys_msg_line = f"    system_prompt_template = SystemMessage(content={_repr_str(msg.get('content',
                                                                                                       ''))})"
            elif msg.get("role") == "user":
                user_msg_line = f"    user_prompt_template = UserMessage(content={_repr_str(msg.get('content',
                                                                                                    ''))})"

        lines = [
            f"def {func_name}():",
            f"    {comment}",
            f"    client_config, model_config = _build_model_configs(",
            f"        client_provider={_repr_str(client_provider)},",
            f"        api_key_env_var={_repr_str(api_key_env)},",
            f"        api_base={_repr_str(api_base)},",
            f"        model_name={_repr_str(model_name)},",
            f"        temperature={temperature},",
            f"        top_p={top_p},",
            f"        timeout={timeout},",
            f"    )",
        ]
        if sys_msg_line:
            lines.append(sys_msg_line)
        if user_msg_line:
            lines.append(user_msg_line)

        lines += [
            f"    config = LLMCompConfig(",
            f"        model_id=None,",
            f"        model_client_config=client_config,",
            f"        model_config=model_config,",
            f"        template_content={template_repr},",
            f"        response_format={{\"type\": {_repr_str(response_fmt)}}},",
            f"        output_config={output_config_repr},",
            f"        enable_history={llm_cfg.enable_history},",
        ]
        if sys_msg_line:
            lines.append(f"        system_prompt_template=system_prompt_template,")
        if user_msg_line:
            lines.append(f"        user_prompt_template=user_prompt_template,")
        lines += [
            f"    )",
            f"    return LLMComponent(config)",
        ]
        return "\n".join(lines) + "\n"

    def _gen_intent_fn(self, comp: dsl.Component, func_name: str) -> str:
        comment = f"# Component ID: {comp.id}"
        configs = comp.configs or {}
        try:
            intent_cfg = IntentDetectionConfig.model_validate(configs)
        except Exception as e:
            return self._gen_error_fn(comp, func_name, str(e))

        client_provider, api_key_env, api_base, model_name, temperature, top_p, timeout = \
            self._extract_model_params(intent_cfg.model)

        categories_repr = json.dumps(intent_cfg.category_name_list, ensure_ascii=False)

        # Branches: for each branch in comp.branches, we need targets
        branch_calls = []
        for idx, branch in enumerate(comp.branches or []):
            targets = self._get_branch_targets(comp.id, branch.branch_id)
            cond = f"${{{comp.id}.classification_id}} == {idx}"
            branch_calls.append(
                f"    intent_comp.add_branch(\n"
                f"        condition={_repr_str(cond)},\n"
                f"        target={repr(targets)},\n"
                f"        branch_id={_repr_str(branch.branch_id)},\n"
                f"    )"
            )

        lines = [
            f"def {func_name}():",
            f"    {comment}",
            f"    client_config, model_config = _build_model_configs(",
            f"        client_provider={_repr_str(client_provider)},",
            f"        api_key_env_var={_repr_str(api_key_env)},",
            f"        api_base={_repr_str(api_base)},",
            f"        model_name={_repr_str(model_name)},",
            f"        temperature={temperature},",
            f"        top_p={top_p},",
            f"        timeout={timeout},",
            f"    )",
            f"    config = IntentDetectionCompConfig(",
            f"        model_id=None,",
            f"        model_client_config=client_config,",
            f"        model_config=model_config,",
            f"        category_name_list={categories_repr},",
            f"        user_prompt={_repr_str(intent_cfg.user_prompt)},",
            f"        enable_history={intent_cfg.enable_history},",
            f"    )",
            f"    intent_comp = IntentDetectionComponent(config)",
        ]
        lines.extend(branch_calls)
        lines.append(f"    return intent_comp")
        return "\n".join(lines) + "\n"

    def _gen_questioner_fn(self, comp: dsl.Component, func_name: str) -> str:
        comment = f"# Component ID: {comp.id}"
        configs = comp.configs or {}
        try:
            q_cfg = QuestionerConfig.model_validate(configs)
        except Exception as e:
            return self._gen_error_fn(comp, func_name, str(e))

        client_provider, api_key_env, api_base, model_name, temperature, top_p, timeout = \
            self._extract_model_params(q_cfg.model)

        # Build FieldInfo list
        field_lines = []
        for fi in (q_cfg.field_names or []):
            if isinstance(fi, dict):
                field_name = fi.get("field_name", "")
                description = fi.get("description", "")
                cn_field_name = fi.get("cn_field_name", "")
                required = fi.get("required", False)
                default_value = fi.get("default_value", "")
                ftype = fi.get("type", "string")
            else:
                field_name = getattr(fi, "field_name", "")
                description = getattr(fi, "description", "")
                cn_field_name = getattr(fi, "cn_field_name", "")
                required = getattr(fi, "required", False)
                default_value = getattr(fi, "default_value", "")
                ftype = getattr(fi, "type", "string")

            field_lines.append(
                f"        FieldInfo(\n"
                f"            field_name={_repr_str(field_name)},\n"
                f"            description={_repr_str(description)},\n"
                f"            cn_field_name={_repr_str(cn_field_name)},\n"
                f"            required={required},\n"
                f"            default_value={repr(default_value)},\n"
                f"            type={_repr_str(ftype)},\n"
                f"        ),"
            )

        field_infos_str = "\n".join(field_lines)
        lines = [
            f"def {func_name}():",
            f"    {comment}",
            f"    client_config, model_config = _build_model_configs(",
            f"        client_provider={_repr_str(client_provider)},",
            f"        api_key_env_var={_repr_str(api_key_env)},",
            f"        api_base={_repr_str(api_base)},",
            f"        model_name={_repr_str(model_name)},",
            f"        temperature={temperature},",
            f"        top_p={top_p},",
            f"        timeout={timeout},",
            f"    )",
            f"    field_names = [",
            field_infos_str,
            f"    ]",
            f"    config = QuestionerConfig(",
            f"        model_id=None,",
            f"        model_client_config=client_config,",
            f"        model_config=model_config,",
            f"        field_names=field_names,",
            f"        with_chat_history={q_cfg.with_chat_history},",
            f"        max_response={q_cfg.max_response},",
            f"    )",
            f"    return QuestionerComponent(config)",
        ]
        return "\n".join(lines) + "\n"

    def _gen_branch_fn(self, comp: dsl.Component, func_name: str) -> str:
        comment = f"# Component ID: {comp.id}"
        branch_calls = []
        for branch in (comp.branches or []):
            targets = self._get_branch_targets(comp.id, branch.branch_id)
            cond = branch.bool_expression or "True"
            branch_calls.append(
                f"    branch_comp.add_branch(\n"
                f"        condition={_repr_str(cond)},\n"
                f"        target={repr(targets)},\n"
                f"        branch_id={_repr_str(branch.branch_id)},\n"
                f"    )"
            )

        lines = [
            f"def {func_name}():",
            f"    {comment}",
            f"    branch_comp = BranchComponent()",
        ]
        lines.extend(branch_calls)
        lines.append(f"    return branch_comp")
        return "\n".join(lines) + "\n"

    def _gen_plugin_fn(self, comp: dsl.Component, func_name: str) -> str:
        comment = f"# Component ID: {comp.id}"
        configs = comp.configs or {}
        try:
            tool_config = ToolCompConfig.model_validate(configs)
        except Exception as e:
            return self._gen_error_fn(comp, func_name, str(e))

        if tool_config.type == PluginType.SERVICE:
            self._need_plugin_service_imports = True
            return self._gen_plugin_service_fn(comp, func_name, tool_config, comment)
        else:
            self._need_plugin_code_imports = True
            return self._gen_plugin_code_fn(comp, func_name, tool_config, comment)

    def _gen_plugin_service_fn(self, comp: dsl.Component, func_name: str,
                                tool_config: ToolCompConfig, comment: str) -> str:
        try:
            api_schema = RestfulApiSchema.model_validate(tool_config.tool)
        except Exception as e:
            return self._gen_error_fn(comp, func_name, str(e))

        headers_repr = repr(dict(api_schema.headers or {}))

        # Build input_params dict for RestfulApiCard (JSON Schema format)
        input_props: Dict[str, Any] = {}
        required_list: List[str] = []
        for param in api_schema.params:
            if param.runtime:
                prop: Dict[str, Any] = {
                    "type": param.type or "string",
                    "description": param.description or "",
                    "location": param.method or "query",
                }
                input_props[param.name] = prop
                if param.required:
                    required_list.append(param.name)

        input_params_dict = {
            "type": "object",
            "properties": input_props,
            "required": required_list,
        }
        input_params_repr = repr(input_params_dict)

        lines = [
            f"def {func_name}():",
            f"    {comment}",
            f"    # REST API tool: {api_schema.name or api_schema.tool_id}",
            f"    card = RestfulApiCard(",
            f"        name={_repr_str(api_schema.name or api_schema.tool_id)},",
            f"        description={_repr_str(api_schema.description)},",
            f"        input_params={input_params_repr},",
            f"        url={_repr_str(api_schema.path)},",
            f"        method={_repr_str(api_schema.method)},",
            f"        headers={headers_repr},",
            f"        queries={{}},",
            f"    )",
            f"    tool = RestfulApi(card)",
            f"    tool_comp_config = ToolComponentConfig(tool_id={_repr_str(comp.id)})",
            f"    return ToolComponent(tool_comp_config).bind_tool(tool)",
        ]
        return "\n".join(lines) + "\n"

    def _gen_plugin_code_fn(self, comp: dsl.Component, func_name: str,
                             tool_config: ToolCompConfig, comment: str) -> str:
        try:
            code_schema = PluginCodeConfig.model_validate(tool_config.tool)
        except Exception as e:
            return self._gen_error_fn(comp, func_name, str(e))

        code_escaped = repr(code_schema.code)
        lines = [
            f"def {func_name}():",
            f"    {comment}",
            f"    # Code plugin: {code_schema.name}",
            f"    # This plugin executes custom code - see openjiuwen_studio plugin_tools for PluginCodeTool",
            f"    # For now, use a ToolComponent with the plugin's inputs as a service stub",
            f"    tool_comp_config = ToolComponentConfig(tool_id={_repr_str(comp.id)})",
            f"    # Code: {code_escaped[:80]}{'...' if len(repr(code_schema.code)) > 80 else ''}",
            f"    # To use this, implement PluginCodeTool.create(code_schema) from plugin_tools.py",
            f"    return ToolComponent(tool_comp_config)",
        ]
        return "\n".join(lines) + "\n"

    def _gen_code_fn(self, comp: dsl.Component, func_name: str) -> str:
        comment = f"# Component ID: {comp.id}"
        configs = comp.configs or {}
        try:
            code_cfg = CodeConfig.model_validate(configs)
        except Exception as e:
            return self._gen_error_fn(comp, func_name, str(e))

        output_params_repr = json.dumps(
            [p.model_dump() for p in code_cfg.output_params],
            ensure_ascii=False, indent=8
        )

        lines = [
            f"def {func_name}():",
            f"    {comment}",
            f"    # Code component: language={code_cfg.language}",
            f"    # Note: Code components require internal executor. See CodeCompCompiler for details.",
            f"    # For standalone use, consider converting to a PluginCodeTool.",
            f"    # Code language: {code_cfg.language}",
            f"    # Output params: {output_params_repr}",
            f"    raise NotImplementedError(",
            f"        'Code components require the internal executor. '",
            f"        'Use the studio to run this workflow, or convert the code to a custom tool.'",
            f"    )",
        ]
        return "\n".join(lines) + "\n"

    @staticmethod
    def _gen_text_editor_fn(comp: dsl.Component, func_name: str) -> str:
        comment = f"# Component ID: {comp.id}"
        configs = comp.configs or {}
        return (
            f"def {func_name}():\n"
            f"    {comment}\n"
            f"    # TextEditorComponent is a studio-internal component and cannot be used standalone.\n"
            f"    # configs: {json.dumps(configs, ensure_ascii=False)}\n"
            f"    raise NotImplementedError(\n"
            f"        'TextEditorComponent requires the studio executor. '\n"
            f"        'Run this workflow via the studio instead.'\n"
            f"    )\n"
        )

    @staticmethod
    def _gen_vari_merge_fn(comp: dsl.Component, func_name: str) -> str:
        comment = f"# Component ID: {comp.id}"
        configs = comp.configs or {}
        return (
            f"def {func_name}():\n"
            f"    {comment}\n"
            f"    # VariableMergeComponent is a studio-internal component and cannot be used standalone.\n"
            f"    # configs: {json.dumps(configs, ensure_ascii=False)}\n"
            f"    raise NotImplementedError(\n"
            f"        'VariableMergeComponent requires the studio executor. '\n"
            f"        'Run this workflow via the studio instead.'\n"
            f"    )\n"
        )

    @staticmethod
    def _gen_loop_fn(comp: dsl.Component, func_name: str) -> str:
        comment = f"# Component ID: {comp.id}"
        return (
            f"def {func_name}():\n"
            f"    {comment}\n"
            f"    # LoopComponent — requires nested workflow assembly.\n"
            f"    # For standalone use, expand the loop body manually.\n"
            f"    raise NotImplementedError('Loop components require manual expansion for standalone use.')\n"
        )

    @staticmethod
    def _gen_subworkflow_fn(comp: dsl.Component, func_name: str) -> str:
        comment = f"# Component ID: {comp.id}"
        configs = comp.configs or {}
        sub_info = {}
        try:
            sub_info = ExecSubWfConfig.model_validate(configs).sub_workflow_info.model_dump()
        except Exception:
            pass
        return (
            f"def {func_name}():\n"
            f"    {comment}\n"
            f"    # SubWorkflowComponent — sub-workflow: {json.dumps(sub_info, ensure_ascii=False)}\n"
            f"    # Load and compile the sub-workflow similarly to this file, then:\n"
            f"    # return SubWorkflowComponent(compiled_sub_workflow)\n"
            f"    raise NotImplementedError('Sub-workflow must be compiled separately.')\n"
        )

    @staticmethod
    def _gen_user_input_fn(comp: dsl.Component, func_name: str) -> str:
        comment = f"# Component ID: {comp.id}"
        configs = comp.configs or {}
        return (
            f"def {func_name}():\n"
            f"    {comment}\n"
            f"    # UserInputComponent is a studio-internal component and cannot be used standalone.\n"
            f"    # configs: {json.dumps(configs, ensure_ascii=False)}\n"
            f"    raise NotImplementedError(\n"
            f"        'UserInputComponent requires the studio executor. '\n"
            f"        'Run this workflow via the studio instead.'\n"
            f"    )\n"
        )

    @staticmethod
    def _gen_user_output_fn(comp: dsl.Component, func_name: str) -> str:
        comment = f"# Component ID: {comp.id}"
        configs = comp.configs or {}
        return (
            f"def {func_name}():\n"
            f"    {comment}\n"
            f"    # UserOutputComponent is a studio-internal component and cannot be used standalone.\n"
            f"    # configs: {json.dumps(configs, ensure_ascii=False)}\n"
            f"    raise NotImplementedError(\n"
            f"        'UserOutputComponent requires the studio executor. '\n"
            f"        'Run this workflow via the studio instead.'\n"
            f"    )\n"
        )

    @staticmethod
    def _gen_empty_fn(comp: dsl.Component, func_name: str) -> str:
        comment = f"# Component ID: {comp.id} (empty/pass-through)"
        return (
            f"def {func_name}():\n"
            f"    {comment}\n"
            f"    from openjiuwen_studio.core.executor.component.component_impl.empty_comp import EmptyComponent\n"
            f"    return EmptyComponent()\n"
        )

    @staticmethod
    def _gen_break_fn(comp: dsl.Component, func_name: str) -> str:
        comment = f"# Component ID: {comp.id} (loop break)"
        return (
            f"def {func_name}():\n"
            f"    {comment}\n"
            f"    return LoopBreakComponent()\n"
        )

    @staticmethod
    def _gen_set_variable_fn(comp: dsl.Component, func_name: str) -> str:
        comment = f"# Component ID: {comp.id}"
        configs = comp.configs or {}
        inter_var = {}
        try:
            inter_var = SetVariableConfig.model_validate(configs).inter_variable
        except Exception:
            pass
        return (
            f"def {func_name}():\n"
            f"    {comment}\n"
            f"    # SetVariable — used inside loop bodies\n"
            f"    inter_variable = {repr(inter_var)}\n"
            f"    return LoopSetVariableComponent(inter_variable)\n"
        )

    @staticmethod
    def _gen_error_fn(comp: dsl.Component, func_name: str, err: str) -> str:
        return (
            f"def {func_name}():\n"
            f"    # Component ID: {comp.id} — ERROR parsing config: {err}\n"
            f"    raise RuntimeError({_repr_str(f'Failed to generate component {comp.id}: {err}')})\n"
        )

    @staticmethod
    def _gen_unsupported_fn(comp: dsl.Component, func_name: str) -> str:
        return (
            f"def {func_name}():\n"
            f"    # Component ID: {comp.id}, type: {comp.type}\n"
            f"    raise NotImplementedError({_repr_str(f'Component type {comp.type} not yet supported in code '
                                                       f'generator.')})\n"
        )

    # ------------------------------------------------------------------
    # Workflow assembly
    # ------------------------------------------------------------------

    def _gen_build_workflow(self) -> str:
        wf = self.workflow
        lines = [
            f"",
            f"# {'=' * 60}",
            f"# Workflow Assembly",
            f"# {'=' * 60}",
            f"def build_workflow() -> Workflow:",
            f"    \"\"\"Create and assemble the workflow from its components.\"\"\"",
            f"    card = WorkflowCard(",
            f"        id=WORKFLOW_ID,",
            f"        name=WORKFLOW_NAME,",
            f"        version=WORKFLOW_VERSION,",
            f"    )",
            f"    flow = Workflow(card=card)",
            f"",
            f"    # --- Instantiate components ---",
        ]

        start_ids = set(wf.start_id)
        end_ids = set(wf.end_id)

        for comp in wf.components:
            var_name = self._comp_var_names.get(comp.id, comp.id)
            func_name = f"create_{var_name}_component"
            lines.append(f"    {var_name} = {func_name}()")

        lines.append(f"")
        lines.append(f"    # --- Register components ---")

        for comp in wf.components:
            var_name = self._comp_var_names.get(comp.id, comp.id)
            inputs_schema_repr = json.dumps(comp.inputs or {}, ensure_ascii=False)

            if comp.id in start_ids:
                lines.append(
                    f"    flow.set_start_comp({_repr_str(comp.id)}, {var_name}, "
                    f"inputs_schema={inputs_schema_repr})"
                )
            elif comp.id in end_ids:
                lines.append(
                    f"    flow.set_end_comp({_repr_str(comp.id)}, {var_name}, "
                    f"inputs_schema={inputs_schema_repr})"
                )
            else:
                lines.append(
                    f"    flow.add_workflow_comp({_repr_str(comp.id)}, {var_name}, "
                    f"inputs_schema={inputs_schema_repr})"
                )

        lines.append(f"")
        lines.append(f"    # --- Wire connections (non-branch) ---")
        for source, target in self._non_branch_connections:
            lines.append(f"    flow.add_connection({_repr_str(source)}, {_repr_str(target)})")

        lines.append(f"")
        lines.append(f"    return flow")
        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------
    # Main / run section
    # ------------------------------------------------------------------

    def _gen_main(self) -> str:
        wf = self.workflow
        inputs_props = wf.inputs.get("properties", {}) if isinstance(wf.inputs, dict) else {}

        # Build example inputs with placeholder values
        example_inputs: Dict[str, Any] = {}
        for k, v in inputs_props.items():
            ptype = v.get("type", "string")
            if ptype == "string":
                example_inputs[k] = f"<your {k}>"
            elif ptype in ("integer", "number"):
                example_inputs[k] = 0
            elif ptype == "boolean":
                example_inputs[k] = False
            elif ptype == "array":
                example_inputs[k] = []
            elif ptype == "object":
                example_inputs[k] = {}
            else:
                example_inputs[k] = None
        inputs_repr = json.dumps(example_inputs, ensure_ascii=False, indent=8)

        return (
            f"\n# {'=' * 60}\n"
            f"# Run\n"
            f"# {'=' * 60}\n"
            f"async def main():\n"
            f"    flow = build_workflow()\n"
            f"    session = create_workflow_session()\n"
            f"\n"
            f"    # Edit the inputs below to match your use case\n"
            f"    inputs = {inputs_repr}\n"
            f"\n"
            f"    result = await flow.invoke(inputs, session)\n"
            f"    print(\"Workflow result:\", result)\n"
            f"\n"
            f"\n"
            f"if __name__ == \"__main__\":\n"
            f"    asyncio.run(main())\n"
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_model_params(model_config) -> ModelParams:
        """
        Extract model parameters from a DSL ModelConfig (or dict).
        Returns a ModelParams named tuple with all relevant model configuration values.
        """
        if model_config is None:
            return ModelParams("OpenAI", "LLM_API_KEY", "", "", 0.7, 0.9, 120.0)

        if isinstance(model_config, dict):
            client_cfg = model_config.get("model_client_config") or {}
            req_cfg = model_config.get("request_config") or {}
        else:
            client_cfg = model_config.model_client_config
            req_cfg = model_config.request_config
            client_cfg = client_cfg.model_dump() if client_cfg else {}
            req_cfg = req_cfg.model_dump() if req_cfg else {}

        raw_provider = client_cfg.get("client_provider", "openai")
        client_provider = _map_client_provider(raw_provider)
        api_base = client_cfg.get("api_base", "")
        timeout = float(client_cfg.get("timeout", 120.0))

        model_name = req_cfg.get("model_name", "")
        temperature = float(req_cfg.get("temperature", 0.7))
        top_p = float(req_cfg.get("top_p", 0.9))

        # Derive an env var name from the provider name
        env_var = f"{raw_provider.upper().replace('-', '_')}_API_KEY" if raw_provider else "LLM_API_KEY"

        return ModelParams(client_provider, env_var, api_base, model_name, temperature, top_p, timeout)


# ------------------------------------------------------------------
# Module-level API
# ------------------------------------------------------------------

def generate_workflow_python(workflow: dsl.Workflow) -> str:
    """
    Generate a runnable Python script from a DSL Workflow object.

    Args:
        workflow: The DSL Workflow to convert.

    Returns:
        A string containing the full Python script content.
    """
    return WorkflowCodeGenerator(workflow).generate()


def _sanitize_identifier(name: str) -> str:
    """ Convert a string to a valid Python identifier (snake_case). """
    import re
    # Replace non-alphanumeric chars with underscores
    s = re.sub(r"[^\w]", "_", name, flags=re.UNICODE)
    # Remove leading digits
    s = re.sub(r"^[0-9]+", "", s)
    # Collapse multiple underscores
    s = re.sub(r"_+", "_", s)
    s = s.strip("_").lower()
    return s or "component"
