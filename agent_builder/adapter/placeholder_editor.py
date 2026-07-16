# coding=utf-8
"""
PlaceholderEditor: local replacement for jiuwen.prompt.template.template_editor.

Provides TemplateEditor base class and PlaceholderEditor for injecting
missing placeholder blocks into prompt templates.
"""

from abc import abstractmethod
from typing import Optional

from pydantic import BaseModel, Field


class TemplateEditor(BaseModel):
    """Abstract base class for template editors."""

    def __call__(self, concrete_template: str):
        return self.run(concrete_template)

    @abstractmethod
    def run(self, concrete_template: str):
        """Process the template and return the result."""
        raise NotImplementedError("run method not implemented")

    @abstractmethod
    def stream_run(self, concrete_template: str):
        """Stream process the template, yielding characters and events."""
        raise NotImplementedError("stream_run method not implemented")


class PlaceholderData(BaseModel):
    """
    Data model for a single placeholder entry.

    Matches the original jiuwen PlaceholderData interface.
    """

    value: str = Field(default="", min_length=0, max_length=200)
    prefix: str = Field(default="", min_length=0, max_length=200)
    description: Optional[str] = Field(default="", max_length=200)
    type: Optional[str] = Field(default="中文", max_length=64)
    inserted: Optional[bool] = Field(default=False)

    def format(self) -> str:
        """Format the placeholder for injection into a template."""
        if self.inserted:
            return f"{self.value}"
        return f"\n\n## {self.prefix} \n" + "{{" + f"{self.value}" + "}}"


class PlaceholderEditor(TemplateEditor):
    """
    Editor for injecting placeholder blocks into templates.

    When a meta template is missing certain placeholders that the editor
    knows about, this editor appends them to the concrete template.
    """

    placeholders: list = Field(default=[])

    def run(self, concrete_template: str):
        """Inject missing placeholders into the template."""
        if self.placeholders:
            for placeholder in self.placeholders:
                if isinstance(placeholder, PlaceholderData):
                    if (placeholder.value) and (
                        placeholder.format() not in concrete_template
                    ):
                        concrete_template += placeholder.format()
                elif isinstance(placeholder, dict):
                    value = placeholder.get("value", "")
                    if value and f"{{{{{value}}}}}" not in concrete_template:
                        prefix = placeholder.get("prefix", "")
                        inserted = placeholder.get("inserted", False)
                        if inserted:
                            concrete_template += f"{value}"
                        else:
                            concrete_template += f"\n\n## {prefix} \n{{{{{value}}}}}"
        return concrete_template

    def stream_run(self, concrete_template: str):
        """Stream template characters and placeholder injection events."""
        for char in concrete_template:
            yield char
        for placeholder in self.placeholders:
            if isinstance(placeholder, PlaceholderData):
                yield dict(code=0, message="success", data=placeholder.format())
            elif isinstance(placeholder, dict):
                value = placeholder.get("value", "")
                prefix = placeholder.get("prefix", "")
                inserted = placeholder.get("inserted", False)
                if inserted:
                    fmt = f"{value}"
                else:
                    fmt = f"\n\n## {prefix} \n{{{{{value}}}}}"
                yield dict(code=0, message="success", data=fmt)
