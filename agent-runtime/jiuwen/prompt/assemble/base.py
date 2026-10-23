#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.

"""Assembler class"""

import re
from copy import deepcopy
from typing import List, Union

from jiuwen.prompt.assemble.message_handler import (
    template_to_messages,
    messages_to_template,
)
from jiuwen.prompt.assemble.variables.textable import TextableVariable
from jiuwen.prompt.assemble.variables.variable import Variable
from jiuwen.prompt.common.exception.assemble import (
    AssemblerInitError,
    InputKeyError,
    TemplateFormatError,
)
from jiuwen.prompt.index.template_store.template_store import Template


class PromptAssembler:
    """
    Class for creating prompt based on a given template.

    Notes:
        Supported template types include list and str. List-type template is essentially a list of messages. By \
        referring to the prompt design of GPT and AgentBuilder, we define 4 types of messages including ``system``, ``user``, \
        ``assistant`` and ``function``. Any type of message should take the form of dictionary with two basic keys \
        ``role`` (its corresponding message type) and ``content``, both given as strings. Exceptionally, ``assistant`` \
        messages can carry an optional field named ``function_call`` which is a dictionary itself. The \
        ``function_call`` dict must have two keys ``name`` and ``arguments``, both given as strings. For example:

        .. code-block:: python

            assistant_message = {
                "role": "assistant",
                "content": "I'm calling function",
                "function_call": {
                    "name": "search",
                    "arguments": "some query"
                }
            }

        Another exception is the ``function`` message with must carry an extra field ``name``. For example:

        .. code-block:: python

            function_message = {
                "role": "function",
                "name": "search",
                "content": "This is the search result.",
            }

        Besides list-type template, we also support str-type template which is the more recommended way of formatting \
        prompts. We provide a unifed template style design for assembling both str-type and list-type prompts. For \
        str-type prompts, the template can be trivially written as a string with tokens and placeholders. For \
        list-type prompts, two groups of special symbols are used to mark different messages:

        - \\`#xxx#\\`: represents the start of a message whose role is ``xxx``. The appended text is regarded as the \
          content of the message.
        - \\`*yyy*\\`: represents an extra field in the message dict whose key is ``yyy``. The appended text is \
          regarded as the value. Note that for the ``function_call`` field, its value must take the form of a json \
          string with keys ``name`` and ``arguments``.

        As as example, for the following list-type template:

        .. code-block:: python

            list_template = [
               {
                  "role":"system",
                  "content":"this is a system message"
               },
               {
                  "role":"assistant",
                  "content":"calling function ...",
                  "function_call":{
                     "name":"search",
                     "arguments":"{'x':'1', 'y':'2'}"
                  }
               },
               {
                  "role":"function",
                  "content":"this is the result of the function",
                  "name":"search"
               },
               {
                  "role":"user",
                  "content":"ok"
               }
            ]

        Its equivalent str-type template can be written as:

        .. code-block:: python

            str_template = \"\"\"`#system#`this is a system message
                `#assistant#`calling function...`*function_call*`{"name": "search", "arguments": "{'x':'1', 'y':'2'}"}
                `#function#`this is the result of the function`*name*`search
                `#user#`ok\"\"\"

    Args:
        template (Template): a `Template` object whose `content` attribute defines the content of a prompt template.
        **variables: user-defined variables passed in as {var_name:var_object} key-value arguments.

    Raises:
        AssemblerInitError: when pass in wrong arguments for instantiate the assember object.
        InputKeyError: when pass in wrong arguments for updating the variable.
        TemplateFormatError: when the template content is not properly formatted.
    """

    def __init__(self, template: Template, return_format: str = "message", **variables):
        template_content = template.content
        if isinstance(template_content, list):
            try:
                template_content = messages_to_template(template_content)
            except Exception as error:
                raise TemplateFormatError(
                    "The list-type prompt should conform to the format of LLM messages, "
                    "please check."
                ) from error
        self.return_format = return_format
        template_formatter = TextableVariable(template_content, name="__inner__")
        for name, variable in variables.items():
            if name not in template_formatter.input_keys:
                raise AssemblerInitError(
                    f"Variable {name} is not defined in the template."
                )
            if not isinstance(variable, Variable):
                raise AssemblerInitError(
                    f"Variable {name} must be instantiated as a `Variable` object."
                )
        for placeholder in template_formatter.input_keys:
            if placeholder in variables:
                variables[placeholder].name = placeholder
            else:
                variables[placeholder] = TextableVariable(
                    name=placeholder, text="{{" + placeholder + "}}"
                )
        self.prompt = ""
        self.template = template
        self.variables = variables
        self._template_formatter = template_formatter

    @property
    def input_keys(self) -> List[str]:
        """
        Get the list of argument names for updating all the variables.

        Returns:
            list[str]: list of argument names.
        """
        keys = []
        for variable in self.variables.values():
            keys.extend(variable.input_keys)
        return list(set(keys))

    @classmethod
    def load_from_template(cls, template: Template):
        """
        Get an instantiated assembler based on the configuration in the template. Note that although a Template object \
        can be instantiated with arbitrary type of fields in its assemble_config and be loaded with this method, some
        objects cannot be registered or stored because some types are not serializable (functions and objects).

        Args:
            template (Template): should contain an dict attribute named assemble_config,
                variable_config as a dict.

        Returns:
            PromptAssembler: an instantiated assembler object.
        """
        variable_config = template.assemble_config.get("variable_config", {})
        variables = {}
        for var_name, var_config in variable_config.items():
            variables[var_name] = Variable.load_from_config(var_config)
        return PromptAssembler(template=template, **variables)

    def assemble(self, **kwargs) -> Union[str, List[dict]]:
        """Update the variables and format the template into a string-type or message-type prompt.

        Args:
            **kwargs: input arguments for updating all the variables.

        Returns:
            Union[str, List[dict]]: a string-type or message-type prompt, depending on the given template.
        """
        kwargs = {
            k: v for k, v in kwargs.items() if v is not None and k in self.input_keys
        }
        all_kwargs = {}
        for k in self.input_keys:
            if k not in kwargs:
                all_kwargs[k] = ""
        all_kwargs.update(**kwargs)
        self._update(**all_kwargs)
        return self._format()

    def _update(self, **kwargs):
        """Update the variables based on the arguments passed in as key-value pairs.

        Args:
            **kwargs: input arguments for updating all the variables.
        """
        missing_keys = set(self.input_keys) - set(kwargs.keys())
        if missing_keys:
            raise InputKeyError("Missing keys for updating the assembler.")
        unexpected_keys = set(kwargs.keys()) - set(self.input_keys)
        if unexpected_keys:
            raise InputKeyError("Unexpected keys for updating the assembler.")
        for variable in self.variables.values():
            input_kwargs = {k: v for k, v in kwargs.items() if k in variable.input_keys}
            variable.eval(**input_kwargs)

    def _format(self) -> Union[str, List[dict]]:
        """Substitute placeholders in the template with variables values and get formatted prompt.

        Returns:
            Union[str, List[dict]]: a string-type or message-type prompt, depending on the given template.
        """
        format_kwargs = {var.name: var.value for var in self.variables.values()}
        formatted_prompt = self._template_formatter.eval(**format_kwargs)
        message_prefix_matches = list(
            re.finditer(r"`#(system|assistant|user|tool|function)#`", formatted_prompt)
        )
        # string-type prompt
        if self.return_format == "text" or not message_prefix_matches:
            self.prompt = formatted_prompt
            return formatted_prompt
        # message-type prompt
        return deepcopy(template_to_messages(formatted_prompt))
