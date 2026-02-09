# openjiuwen.core.retrieval.utils.config_manager

## class openjiuwen.core.retrieval.utils.config_manager.ConfigManager

配置管理器，用于统一管理所有配置，支持从文件加载和保存。

### __init__

```python
__init__(config_path: Optional[str] = None)
```

初始化配置管理器。

**参数**：

* **config_path**(str, 可选)：配置文件路径，如果提供将自动加载。默认值：None。

### load_from_file

```python
load_from_file(path: str) -> None
```

从文件加载配置（支持JSON和YAML格式）。

**参数**：

* **path**(str)：配置文件路径。默认值：无。

**异常**：

* **FileNotFoundError**：如果配置文件不存在。
* **ImportError**：如果YAML文件需要PyYAML但未安装。
* **ValueError**：如果不支持的文件格式。

### save_to_file

```python
save_to_file(path: str) -> None
```

保存配置到文件（支持JSON和YAML格式）。

**参数**：

* **path**(str)：配置文件路径。默认值：无。

**异常**：

* **ValueError**：如果没有可保存的配置。
* **ImportError**：如果YAML文件需要PyYAML但未安装。
* **ValueError**：如果不支持的文件格式。

### get_config

```python
get_config(config_type: Type[T]) -> Optional[T]
```

获取指定类型的配置。

**参数**：

* **config_type**(Type[T])：配置类型。

**返回**：

**Optional[T]**，返回指定类型的配置，如果不存在则返回None。

### get_knowledge_base_config

```python
get_knowledge_base_config() -> KnowledgeBaseConfig
```

获取知识库配置。

**返回**：

**KnowledgeBaseConfig**，返回知识库配置。

**异常**：

* **ValueError**：如果知识库配置未加载。

### update_config

```python
update_config(config: BaseModel) -> None
```

更新配置。

**参数**：

* **config**(BaseModel)：配置对象。默认值：无。

