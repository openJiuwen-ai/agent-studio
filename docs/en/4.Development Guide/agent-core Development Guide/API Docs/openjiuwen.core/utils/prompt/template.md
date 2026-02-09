# openjiuwen.core.utils.prompt.template

## class openjiuwen.core.utils.prompt.template.template.Template

```python
class openjiuwen.core.utils.prompt.template.template.Template.Template(content, name="", filters={})
```

The Template class represents a prompt template and provides features such as format conversion and prompt filling.

**Parameters**:

- **content** (Union[List[Dict], List[[BaseMessage](../llm/messages.md#class-openjiuwencoreutilsllmmessagesbasemessage)], str]): The template content. If the content contains placeholders to be filled, use double curly braces {{}} to indicate them, for example, {{role}}. Supports the following types:
  - **List[Dict]**: A list of dictionaries in BaseMessage format. For example: [{"role": "system", "content": "You are a {{role}} assistant"}]
  - **List[BaseMessage]**: A list of BaseMessage instances, e.g., [SystemMessage(content="You are a {{role}} assistant")].
  - **str**: For example, You are a {{role}} assistant.
- **name** (str, optional): Template name. Default: "".
- **filters** (Dict[str, str], optional): Tags for the prompt template, used as filter conditions in the TemplateManager. Default: {}. For example, if this prompt template belongs to a specific model, filters can be set to {"model_name": "model_A"}.

Note

When registering a prompt template in TemplateManager, name must be non-empty, and the combination of name and filters must be unique to avoid duplication.

**Examples**:

```python
>>> from openjiuwen.core.utils.prompt.template.template import Template
>>> from openjiuwen.core.utils.llm.messages import AIMessage
>>> 
>>> # Create a string-type prompt template
>>> str_template = Template(content="12345{{num}}")
>>> # Create a BaseMessage list-type prompt template
>>> messages_template = Template(content=[AIMessage(content="12345{{num}}")])
>>> # Create a dict list-type prompt template
>>> dict_template = Template(content=[{"role": "user", "content": "12345{{num}}"}])
>>> 
>>> print("string-template:", str_template.content)
Output: string-template: 12345{{num}}
>>> print("messages-template:", messages_template.content)
Output: messages-template: [AIMessage(role='assistant', content='12345{{num}}', name=None, tool_calls=None, usage_metadata=None, raw_content=None, reason_content=None)]
>>> print("dict-template:", dict_template.content)
Output: dict-template: [{'role': 'user', 'content': '12345{{num}}'}]
```

### format

```python
format(self, keywords: Dict[str, str]=None) -> Template
```

Fill the prompt template using key-value pairs.

**Parameters**:

- **keywords** (Dict[str, str]): Placeholders to fill. The key is the placeholder name, and the value is the content to fill.

**Returns**:

**Template**, a new template object with placeholders filled.

**Exceptions**:

- **JiuWenBaseException**: Base exception class for openJiuwen. For details and solutions, see StatusCode (../../common/exception/status_code.md)).

**Examples**:

```python
>>> from openjiuwen.core.utils.prompt.template.template import Template
>>> from openjiuwen.core.utils.llm.messages import AIMessage
>>> 
>>> str_template = Template(content="12345{{num}}")
>>> str_template = str_template.format({"num": "67890"})
>>> # Create a BaseMessage list-type prompt template and fill it
>>> messages_template = Template(content=[AIMessage(content="12345{{num}}")])
>>> messages_template = messages_template.format({"num": "67890"})
>>> # Create a dict list-type prompt template and fill it
>>> dict_template = Template(content=[{"role": "user", "content": "12345{{num}}"}])
>>> dict_template = dict_template.format({"num": "67890"})
>>> 
>>> # Supports chained filling
>>> chain_template = Template(content="12345{{num_1}}{{num_2}}{{num_3}}{{num_4}}{{num_5}}")
>>> chain_template = chain_template.format({"num_1": "6"}) \
...                                .format({"num_2": "7"}) \
...                                .format({"num_3": "8"}) \
...                                .format({"num_4": "9"}) \
...                                .format({"num_5": "0"})
... 
>>> print("string-template:", str_template.content)
Output: string-template: 1234567890
>>> print("messages-template:", messages_template.content)
Output: messages-template: [AIMessage(role='assistant', content='1234567890', name=None, tool_calls=None, usage_metadata=None, raw_content=None, reason_content=None)]
>>> print("dict-template:", dict_template.content)
Output: dict-template: [{'role': 'user', 'content': '1234567890'}]
>>> print("chain-template:", chain_template.content)
Output: chain-template: 1234567890
```

### to_messages

```python
to_messages(self) -> List[BaseMessage]
```

Convert the prompt template to a list of BaseMessage messages.

**Returns**:

**List[BaseMessage]**, the converted message list.

Notes:

1. When converting a string-type template to a message list, the default message type is HumanMessage.
2. When converting a dict-type template to a message list, instantiate the corresponding message type based on the role field, e.g., user -> HumanMessage, assistant -> AIMessage, system -> SystemMessage, tool -> ToolMessage.
3. When converting a BaseMessage-type template to a message list, the original message type is preserved.

**Examples**:

```python
>>> from openjiuwen.core.utils.prompt.template.template import Template
>>> from openjiuwen.core.utils.llm.messages import AIMessage
>>> 
>>> # Create a string-type prompt template
>>> str_template = Template(content="12345{{num}}")
>>> # Create a BaseMessage list-type prompt template
>>> messages_template = Template(content=[AIMessage(content="12345{{num}}")])
>>> # Create a dict list-type prompt template
>>> dict_template = Template(content=[{"role": "user", "content": "12345{{num}}"}])
>>> 
>>> print("string-template:", str_template.to_messages())
Output: string-template: [HumanMessage(role='user', content='12345{{num}}', name=None)]
>>> print("messages-template:", messages_template.to_messages())
Output: messages-template: [AIMessage(role='assistant', content='12345{{num}}', name=None, tool_calls=None, usage_metadata=None, raw_content=None, reason_content=None)]
>>> print("dict-template:", dict_template.to_messages())
Output: dict-template: [HumanMessage(role='user', content='12345{{num}}', name=None)]
```