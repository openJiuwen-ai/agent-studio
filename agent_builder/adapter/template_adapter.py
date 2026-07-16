# coding=utf-8
"""
Template adapter: partially delegates to agent-core (openjiuwen).

Provides:
- Template: data model for prompt templates
- LocalTemplateManager: loads .pr template files from disk (custom, no agent-core equiv)
- PromptAssembler: delegates {{variable}} substitution to agent-core's PromptTemplate
- MetaTemplate / StandardMeta: meta-template build pipeline (custom, no agent-core equiv)

agent-core capability used:
  - openjiuwen.core.foundation.prompt.PromptTemplate (for variable substitution)
"""

import logging
import os
import re
from abc import abstractmethod
from typing import List, Optional, Union

from agent_builder.adapter.singleton import Singleton
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Template data model
# ---------------------------------------------------------------------------

class Template(BaseModel):
    """Prompt template data model."""

    name: str = Field(default="")
    content: str = Field(default="")
    description: str = Field(default="")


# ---------------------------------------------------------------------------
# Template Manager (loads .pr files)
# ---------------------------------------------------------------------------

class LocalTemplateManager(metaclass=Singleton):
    """
    Singleton template manager that loads .pr files from the templates directory.

    Templates are loaded from:
    - agent_builder/prompt/templates/meta/   (meta templates for optimization)
    """

    def __init__(self):
        self._templates = {}
        self._loaded = False

    def _ensure_loaded(self):
        """Lazy-load all templates on first access."""
        if self._loaded:
            return
        self._loaded = True
        # Load meta templates
        meta_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "prompt", "templates", "meta",
        )
        self._load_from_dir(meta_dir)

    def _load_from_dir(self, directory: str):
        """Load all .pr files from a directory."""
        if not os.path.isdir(directory):
            return
        for filename in os.listdir(directory):
            if filename.endswith(".pr"):
                name = filename[:-3]  # strip .pr extension
                filepath = os.path.join(directory, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    self._templates[name] = Template(
                        name=name, content=content, description=""
                    )
                except Exception:
                    pass  # Skip files that can't be read

    def get(self, name: str) -> Optional[Template]:
        """Get a template by name."""
        self._ensure_loaded()
        return self._templates.get(name)

    def register(self, template: Template, force: bool = False):
        """Register a template."""
        if force or template.name not in self._templates:
            self._templates[template.name] = template

    def list_templates(self) -> List[str]:
        """List all registered template names."""
        self._ensure_loaded()
        return list(self._templates.keys())


# ---------------------------------------------------------------------------
# Prompt Assembler
# ---------------------------------------------------------------------------

class PromptAssembler:
    """
    Template assembler that delegates {{variable}} substitution to
    agent-core's PromptTemplate.format().

    Compatible with the original jiuwen PromptAssembler interface.
    """

    def __init__(self, template: Template):
        self.template = template
        self._content = template.content if isinstance(template, Template) else str(template)

    @property
    def variables(self) -> dict:
        """Extract all {{variable}} names from the template content."""
        pattern = r"\{\{([^{}]*?)\}\}"
        matches = re.findall(pattern, self._content)
        return {m: "" for m in matches}

    def assemble(self, **kwargs) -> str:
        """
        Substitute placeholders with provided values.

        Delegates to agent-core's PromptTemplate.format() for the
        actual variable substitution.

        Args:
            **kwargs: variable_name=value pairs

        Returns:
            Assembled prompt string
        """
        from openjiuwen.core.foundation.prompt import PromptTemplate

        # Filter out None values
        filtered = {k: v for k, v in kwargs.items() if v is not None}
        pt = PromptTemplate(content=self._content)
        formatted = pt.format(filtered)
        return formatted.content


# ---------------------------------------------------------------------------
# InnerTemplate (backward-compatible accessor)
# ---------------------------------------------------------------------------

class InnerTemplate:
    """
    Backward-compatible accessor for internal/meta templates.
    Delegates to LocalTemplateManager.
    """

    @staticmethod
    def get(name: str) -> Optional[Template]:
        return LocalTemplateManager().get(name)


# ---------------------------------------------------------------------------
# MetaTemplate / StandardMeta
# ---------------------------------------------------------------------------

class MetaTemplate(BaseModel):
    """
    Meta template base class.

    Loads a named template, assembles variables, and optionally
    calls an LLM to produce the final prompt.
    """

    name: str = Field(default="")
    stream: bool = Field(default=False)
    model_info: object = Field(default=None)

    @classmethod
    def create(cls, name: str, stream: bool = False, model_info=None):
        """Factory method to create a StandardMeta instance."""
        return StandardMeta(name=name, stream=stream, model_info=model_info)

    def get_template_content(
        self, instruction: str = "", tools: List[dict] = None, **kwargs
    ):
        """Load template and assemble content."""
        template = InnerTemplate().get(name=self.name)
        if not template:
            if self.stream:
                return dict(code=-1, message=f"Template '{self.name}' not found", data="")
            raise ValueError(f"Template '{self.name}' not found")

        content = self._assemble_input_value(
            template=template, instruction=instruction, tools=tools, **kwargs
        )
        return content

    def build_prompt(self, instruction: str = "", tools: List[dict] = None, **kwargs):
        """Build prompt: load template → assemble → optional LLM call."""
        content = self.get_template_content(
            instruction=instruction, tools=tools, **kwargs
        )
        if self.stream:
            return self._streaming_build(content=content)
        concrete_template = self._full_build(content=content)
        if not concrete_template:
            raise ValueError("Concrete template build failed, content is null!")
        return concrete_template

    @abstractmethod
    def _assemble_input_value(self, template, instruction="", tools=None, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def _streaming_build(self, content: str):
        raise NotImplementedError

    @abstractmethod
    def _full_build(self, content: str):
        raise NotImplementedError


class StandardMeta(MetaTemplate):
    """Standard meta template implementation."""

    @staticmethod
    def _parse_tool_list(tools: List[dict] = None) -> str:
        """Parse tool list into a description string."""
        if not tools:
            return ""
        tool_description = ""
        for tool in tools:
            try:
                tool_description += f"{tool.get('name')}，{tool.get('description')}\n"
            except Exception as e:
                logger.warning(f"Failed to parse tool description: {e}")
        return tool_description

    def _assemble_input_value(self, template, instruction="", tools=None, **kwargs):
        """Assemble template variables."""
        if tools:
            kwargs["tools"] = self._parse_tool_list(tools=tools)
        if instruction:
            kwargs["instruction"] = instruction

        assembler = PromptAssembler(template)
        variables = assembler.variables
        assemble_value = {}
        for variable in variables:
            assemble_value[variable] = kwargs.get(variable)
        content = assembler.assemble(**assemble_value)
        return content

    def _streaming_build(self, content: str):
        """Stream build: send content to LLM as streaming chat."""
        from agent_builder.prompt.template.llm_service import LLMServiceManager
        messages = [{"role": "user", "content": content}]
        return LLMServiceManager.get_llm_backend().chat(
            messages, method="stream", model_info=self.model_info
        )

    def _full_build(self, content: str):
        """Full build: send content to LLM as single request."""
        from agent_builder.prompt.template.llm_service import LLMServiceManager
        messages = [{"role": "user", "content": content}]
        result = LLMServiceManager.get_llm_backend().chat(
            messages, model_info=self.model_info
        )
        if isinstance(result, dict):
            if "latency" in result:
                result.pop("latency")
            return result.get("data", result.get("content", "content not exit"))
        return str(result)
