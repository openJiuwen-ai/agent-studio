# openjiuwen.core.runtime.resources_manager.prompt_manager

## class openjiuwen.core.runtime.resources_manager.prompt_manager.PromptMgr

```python
class openjiuwen.core.runtime.resources_manager.prompt_manager.PromptMgr()
```

Prompt resource manager that manages the registration, creation, and removal of Prompt templates, and provides versioning and caching for Prompt templates.

### add_prompt

```python
def add_prompt(template_id: str, template: Template) -> None
```

Add a Prompt template to the resource manager, establishing a mapping between the ID and the template instance.

**Parameters**:

- **template_id** (str): The unique identifier of the template.
- **template** (Template): The template instance to add.

**Example**:

```python
>>> from openjiuwen.core.runtime.resources_manager.prompt_manager import PromptMgr
>>> from openjiuwen.core.utils.prompt.template.template import Template
>>> 
>>> # Create Prompt manager
>>> prompt_mgr = PromptMgr()
>>> 
>>> # Create a Prompt template
>>> template = Template(
...     name = "hello_template",
...     content = "Hello {{name}}, welcome to our system!"
>>> )
>>> # Add the template instance
>>> prompt_mgr.add_prompt("hello_template", template)
>>> print("Template added successfully")
Template added successfully
```

### add_prompts

```python
def add_prompts(templates: List[Tuple[str, Template]]) -> None
```

Batch add Prompt templates to the resource manager, establishing mappings between IDs and template instances.

**Parameters**:

- templates (List[Tuple[str, Template]]): A list of templates, where each item is a tuple of (template ID, template instance).

**Example**:

```python
>>> from openjiuwen.core.runtime.resources_manager.prompt_manager import PromptMgr
>>> from openjiuwen.core.utils.prompt.template.template import Template
>>>
>>> # Create Prompt manager
>>> prompt_mgr = PromptMgr()
>>> 
>>> # Create multiple template instances
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
>>> # Batch add templates
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

Remove the specified Prompt template from the resource manager and return the removed Template instance.

**Parameters**:

- template_id (str): The unique identifier of the template.

**Returns**:

- Optional[Template]: The removed template instance, or None if it does not exist.

**Example**:

```python
>>> from openjiuwen.core.runtime.resources_manager.prompt_manager import PromptMgr
>>> from openjiuwen.core.utils.prompt.template.template import Template
>>>
>>> # Create Prompt manager
>>> prompt_mgr = PromptMgr()
>>> 
>>> # Create multiple template instances
>>> template1 = Template(
...     name="hello_template",
...     content="Hello {{name}}, welcome to our system!"
>>> )
>>> template2 = Template(
...     name="goodbye_template",
...     content="Goodbye {{name}}, see you later!"
>>> )
>>> 
>>> # Batch add templates
>>> templates = [
...     ("hello_template", template1),
...     ("goodbye_template", template2)
>>> ]
>>> prompt_mgr.add_prompts(templates)
>>> 
>>> # Remove an existing template
>>> removed_template = prompt_mgr.remove_prompt("hello_template")
>>> print(f"Was the template removed: {removed_template is not None}")
>>> print(f"Removed template name: {removed_template.name}")
Was the template removed: True
Removed template name: hello_template
```

### get_prompt

```python
def get_prompt(template_id: str) -> Optional[Template]
```

Retrieve the specified Prompt template from the resource manager. Supports lazy loading to create template instances on demand.

**Parameters**:

- template_id (str): The unique identifier of the template.

**Returns**:

- Optional[Template]: The corresponding template instance, or None if it does not exist.

**Example**:

```python
>>> from openjiuwen.core.runtime.resources_manager.prompt_manager import PromptMgr
>>> from openjiuwen.core.utils.prompt.template.template import Template
>>>
>>> # Create Prompt manager
>>> prompt_mgr = PromptMgr()
>>> 
>>> # Create multiple template instances
>>> template1 = Template(
...     name="hello_template",
...     content="Hello {{name}}, welcome to our system!"
>>> )
>>> template2 = Template(
...     name="goodbye_template",
...     content="Goodbye {{name}}, see you later!"
>>> )
>>> 
>>> # Batch add templates
>>> templates = [
...     ("hello_template", template1),
...     ("goodbye_template", template2)
>>> ]
>>> prompt_mgr.add_prompts(templates)
>>> 
>>> # Get an existing template
>>> template = prompt_mgr.get_prompt("goodbye_template")
>>> print(f"Template exists: {template is not None}")
>>> print(f"Template content: {template.content}")
>>> print(f"Template name: {template.name}")
Template exists: True
Template content: Goodbye {{name}}, see you later!
Template name: goodbye_template
```