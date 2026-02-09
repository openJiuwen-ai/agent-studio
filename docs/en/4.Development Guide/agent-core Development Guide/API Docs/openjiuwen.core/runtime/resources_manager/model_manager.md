# openjiuwen.core.runtime.resources_manager.model_manager

## class openjiuwen.core.runtime.resources_manager.model_manager.ModelMgr

```python
class openjiuwen.core.runtime.resources_manager.model_manager.ModelMgr()
```

A thread-safe model management class that handles the registration, creation, and removal of model instances, providing a runtime environment and performance monitoring for models.

### add_model

```python
def add_model(model_id: str, model: BaseModelClient) -> None
```

Add a model instance to the resource manager.

**Parameters**:

- **model_id** (str): The unique identifier of the model.
- **model** (BaseModelClient): The model instance to add.

**Example**:

```python
>>> from openjiuwen.core.runtime.resources_manager.model_manager import ModelMgr
>>> 
>>> from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
>>>
>>> # Create a model manager
>>> model_mgr = ModelMgr()
>>>
>>> # Prepare a model instance (simplified example; in practice, obtain it from ModelFactory)
>>> model_config = {
... "model_provider": "openai",
... "api_key": "test_key",
... "api_base": "xxx.yyy"
... }
>>> mock_model = ModelFactory().get_model(**model_config)
>>> model_mgr.add_model("test_model", mock_model)
>>> print("Model added successfully")
Model added successfully
```

### add_models

```python
def add_models(models: List[Tuple[str, BaseModelClient]]) -> None
```

Add multiple model instances to the resource manager.

**Parameters**:

- models (List[Tuple[str, BaseModelClient]]): A list of models, where each element is a tuple of (ID, model instance).

**Example**:

```python
>>> from openjiuwen.core.runtime.resources_manager.model_manager import ModelMgr
>>> from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
>>>
>>> # Create a model manager
>>> model_mgr = ModelMgr()
>>>
>>> # Create multiple model instances using ModelFactory
>>> openai_config_a = {
...     "model_provider": "openai",
...     "api_key": "openai_key_a",
...     "api_base": "xxx.yyy"
... }
>>> openai_config_b = {
...     "model_provider": "openai",
...     "api_key": "openai_key_b",
...     "api_base": "xxx.yyy"
... }
>>> openai_model_a = ModelFactory().get_model(**openai_config_a)
>>> openai_model_b = ModelFactory().get_model(**openai_config_b)
>>> print("Multiple models created")
>>> # Batch add models
>>> models = [
...     ("openai_model_a", openai_model_a),
...     ("openai_model_b", openai_model_b)
... ]
>>> model_mgr.add_models(models)
>>> print("Models added successfully")
Multiple models created
Models added successfully
```

### remove_model

```python
def remove_model(model_id: str) -> Optional[BaseModelClient]
```

Remove the specified model instance from the resource manager.

**Parameters**:

- model_id (str): The unique identifier of the model.

**Returns**:

- Optional[BaseModelClient]: The removed model instance, or None if it does not exist.

**Example**:

```python
>>> from openjiuwen.core.runtime.resources_manager.model_manager import ModelMgr
>>> from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
>>> 
>>> # Create a model manager
>>> model_mgr = ModelMgr()
>>> 
>>> model_config = {
... "model_provider": "openai",
... "api_key": "test_key",
... "api_base": "xxx.yyy"
>>> }
>>> mock_model = ModelFactory().get_model(**model_config)
>>> model_mgr.add_model("test_model", mock_model)
>>> 
>>> # Remove the model
>>> removed_model = model_mgr.remove_model("test_model")
>>> print(f"Removed model: {removed_model is not None}")
>>> Removed model: True
```

### get_model

```python
def get_model(model_id: str, runtime=None) -> Optional[BaseModelClient]
```

Retrieve the specified model instance from the resource manager.

**Parameters**:

- model_id (str): The unique identifier of the model.
- runtime (optional): Runtime context used to track model invocations.

**Returns**:

- Optional[BaseModelClient]: The corresponding model instance, or None if it does not exist.

**Example**:

```python
>>> from openjiuwen.core.runtime.resources_manager.model_manager import ModelMgr
>>> from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
>>> 
>>> # Create a model manager
>>> model_mgr = ModelMgr()
>>> 
>>> model_config = {
... "model_provider": "openai",
... "api_key": "test_key",
... "api_base": "xxx.yyy"
>>> }
>>> mock_model = ModelFactory().get_model(**model_config)
>>> model_mgr.add_model("test_model", mock_model)
>>> 
>>> # Get the model
>>> model = model_mgr.get_model("test_model")
>>> 
>>> print(model.model_provider())
openai
```