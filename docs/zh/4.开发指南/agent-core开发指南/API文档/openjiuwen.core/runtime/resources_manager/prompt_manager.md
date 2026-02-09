# openjiuwen.core.runtime.resources_manager.prompt_manager

## class openjiuwen.core.runtime.resources_manager.prompt_manager.PromptMgr

```python
class openjiuwen.core.runtime.resources_manager.prompt_manager.PromptMgr()
```

Prompt资源管理类，管理Prompt模板的注册、创建和移除，为Prompt模板提供版本管理和缓存功能。

### add_prompt

```python
def add_prompt(template_id: str, template: Template) -> None
```

向资源管理器中添加Prompt模板，建立ID与模板实例的映射关系。

**参数**:

- **template_id**(str): 模板的唯一标识符。
- **template**(Template): 要添加的模板实例。

**样例**:

```python
>>> from openjiuwen.core.runtime.resources_manager.prompt_manager import PromptMgr
>>> from openjiuwen.core.utils.prompt.template.template import Template
>>> 
>>>  # 创建Prompt管理器
>>> prompt_mgr = PromptMgr()
>>> 
>>>  # 创建Prompt模板
>>> template = Template(
...     name = "hello_template",
...     content = "Hello {{name}}, welcome to our system!"
>>> )
>>>  # 添加模板实例
>>> prompt_mgr.add_prompt("hello_template", template)
>>> print("Template added successfully")
Template added successfully
```

### add_prompts

```python
def add_prompts(templates: List[Tuple[str, Template]]) -> None
```

向资源管理器批量添加Prompt模板，建立ID与模板实例的映射关系。

**参数**:

- **templates**(List[Tuple[str, Template]]): 模板列表，每个元素为(模板ID, 模板实例)的元组。

**样例**:

```python
>>> from openjiuwen.core.runtime.resources_manager.prompt_manager import PromptMgr
>>> from openjiuwen.core.utils.prompt.template.template import Template
>>>
>>>  # 创建Prompt管理器
>>> prompt_mgr = PromptMgr()
>>> 
>>> # 创建多个模板实例
>>> template1 = Template(
...     name="hello_template",
...     content="Hello {{name}}, welcome to our system!"
>>> )
>>> template2 = Template(
...     name="goodbye_template",
...     content="Goodbye {{name}}, see you later!"
>>> )
>>> print("Templates created successfully")
>>> 
>>> # 批量添加模板
>>> templates = [
...     ("hello_template", template1),
...     ("goodbye_template", template2)
>>> ]
>>> prompt_mgr.add_prompts(templates)
>>> print("Templates added successfully")
Templates created successfully
Templates added successfully
```

### remove_prompt

```python
def remove_prompt(template_id: str) -> Optional[Template]
```

从资源管理器中移除指定的Prompt模板，返回被移除的Template实例。

**参数**:

- **template_id**(str): 模板的唯一标识符。

**返回**:

- **Optional[Template]**: 被移除的模板实例，若不存在则返回None。

**样例**:

```python
>>> from openjiuwen.core.runtime.resources_manager.prompt_manager import PromptMgr
>>> from openjiuwen.core.utils.prompt.template.template import Template
>>>
>>>  # 创建Prompt管理器
>>> prompt_mgr = PromptMgr()
>>> 
>>> # 创建多个模板实例
>>> template1 = Template(
...     name="hello_template",
...     content="Hello {{name}}, welcome to our system!"
>>> )
>>> template2 = Template(
...     name="goodbye_template",
...     content="Goodbye {{name}}, see you later!"
>>> )
>>> 
>>> # 批量添加模板
>>> templates = [
...     ("hello_template", template1),
...     ("goodbye_template", template2)
>>> ]
>>> prompt_mgr.add_prompts(templates)
>>> 
>>> # 移除存在的模板
>>> removed_template = prompt_mgr.remove_prompt("hello_template")
>>> print(f"模板是否被移除: {removed_template is not None}")
>>> print(f"被移除的模板名称: {removed_template.name}")
模板是否被移除: True
被移除的模板名称: hello_template
```

### get_prompt

```python
def get_prompt(template_id: str) -> Optional[Template]
```

从资源管理器中获取指定的Prompt模板，支持延迟加载机制，按需创建模板实例。

**参数**:

- **template_id**(str): 模板的唯一标识符。

**返回**:

- **Optional[Template]**: 对应的模板实例，若不存在则返回None。

**样例**:

```python
>>> from openjiuwen.core.runtime.resources_manager.prompt_manager import PromptMgr
>>> from openjiuwen.core.utils.prompt.template.template import Template
>>>
>>>  # 创建Prompt管理器
>>> prompt_mgr = PromptMgr()
>>> 
>>> # 创建多个模板实例
>>> template1 = Template(
...     name="hello_template",
...     content="Hello {{name}}, welcome to our system!"
>>> )
>>> template2 = Template(
...     name="goodbye_template",
...     content="Goodbye {{name}}, see you later!"
>>> )
>>> 
>>> # 批量添加模板
>>> templates = [
...     ("hello_template", template1),
...     ("goodbye_template", template2)
>>> ]
>>> prompt_mgr.add_prompts(templates)
>>> 
>>> # 获取存在的模板
>>> template = prompt_mgr.get_prompt("goodbye_template")
>>> print(f"模板是否存在: {template is not None}")
>>> print(f"模板内容: {template.content}")
>>> print(f"模板名称: {template.name}")
模板是否存在: True
模板内容: Goodbye {{name}}, see you later!
模板名称: goodbye_template
```