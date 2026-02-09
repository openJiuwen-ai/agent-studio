# openjiuwen.core.runtime.resources_manager.model_manager

## class openjiuwen.core.runtime.resources_manager.model_manager.ModelMgr

```python
class openjiuwen.core.runtime.resources_manager.model_manager.ModelMgr()
```

线程安全的模型管理类，负责管理模型实例的注册、创建和移除，为模型提供运行时环境和性能监控功能。

### add_model

```python
def add_model(model_id: str, model: BaseModelClient) -> None
```

向资源管理器中添加模型实例。

**参数**:

- **model_id**(str): 模型的唯一标识符。
- **model**(BaseModelClient): 要添加的模型实例。

**样例**:

```python
>>> from openjiuwen.core.runtime.resources_manager.model_manager import ModelMgr
>>> 
>>> from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
>>>
>>> # 创建模型管理器
>>> model_mgr = ModelMgr()
>>>
>>> # 准备模型实例 (这里简化示例，实际应从 ModelFactory 获取)
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

向资源管理器批量添加模型实例。

**参数**:

- **models**(List[Tuple[str, BaseModelClient]]): 模型列表，每个元素为(ID, 模型实例)的元组。

**样例**:

```python
>>> from openjiuwen.core.runtime.resources_manager.model_manager import ModelMgr
>>> from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
>>>
>>> # 创建模型管理器
>>> model_mgr = ModelMgr()
>>>
>>> # 使用 ModelFactory 创建多个模型实例
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
>>> # 批量添加模型
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

从资源管理器中移除指定的模型实例。

**参数**:

- **model_id**(str): 模型的唯一标识符。

**返回**:

- **Optional[BaseModelClient]**: 移除的模型实例，若不存在则返回None。

**样例**:

```python
>>> from openjiuwen.core.runtime.resources_manager.model_manager import ModelMgr
>>> from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
>>> 
>>> # 创建模型管理器
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
>>> # 移除模型
>>> removed_model = model_mgr.remove_model("test_model")
>>> print(f"Removed model: {removed_model is not None}")
>>> Removed model: True
```

### get_model

```python
def get_model(model_id: str, runtime=None) -> Optional[BaseModelClient]
```

从资源管理器中获取指定的模型实例。

**参数**:

- **model_id**(str): 模型的唯一标识符。
- **runtime**(optional): 运行时上下文，用于跟踪模型调用。

**返回**:

- **Optional[BaseModelClient]**: 对应的模型实例，若不存在则返回None。

**样例**:

```python
>>> from openjiuwen.core.runtime.resources_manager.model_manager import ModelMgr
>>> from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
>>> 
>>> # 创建模型管理器
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
>>> # 获取模型
>>> model = model_mgr.get_model("test_model")
>>> 
>>> print(model.model_provider())
openai
```