# openjiuwen.core.runtime.resources_manager.tool_manager

## class openjiuwen.core.runtime.resources_manager.tool_manager.ToolMgr

```python
class openjiuwen.core.runtime.resources_manager.tool_manager.ToolMgr()
```

工具资源管理类，管理工具实例的注册、查找和移除，支持工具信息获取和MCP服务器集成。


### add_tool

```python
def add_tool(tool_id: str, tool: Union[Tool, ToolProvider]) -> None
```

向资源管理器中添加工具实例或提供者，建立ID与工具实例的映射关系。

**参数**:

- **tool_id**(str): 工具的唯一标识符。
- **tool**(Union[Tool, ToolProvider]): 工具实例或提供者。
	- **ToolProvider**: `Callable[[], Tool]` 类型，工具实例的延迟加载工厂函数，用于按需创建工具对象，实现资源的惰性初始化，提高系统资源管理效率和类型安全性。

**样例**:

```python
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import ToolMgr
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import Tool
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import ToolInfo
>>> 
>>> # 创建工具管理器
>>> tool_mgr = ToolMgr()
>>> 
>>> # 创建模拟工具类
>>> class MockTool(Tool):
...     def __init__(self):
...         self.name = "mock_tool"
...         self.description = "A mock tool for testing"
...     def invoke(self, **kwargs):
...         return {"result": "Tool executed"}
...     def get_tool_info(self):
...         return ToolInfo(name=self.name, description=self.description)
>>> 
>>> # 添加工具实例
>>> tool = MockTool()
>>> tool_mgr.add_tool("test_tool", tool)
>>> print("Tool added successfully")
Tool added successfully
```

### add_tools

```python
def add_tools(tools: List[Tuple[str, Union[Tool, ToolProvider]]]) -> None
```

批量向资源管理器添加工具实例，建立ID与工具实例的映射关系。

**参数**:

- **tools**(List[Tuple[str, Union[Tool, ToolProvider]]]): 工具列表，每个元素为(工具ID, 工具实例)的元组。

**样例**:

```python
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import ToolMgr
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import Tool
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import ToolInfo
>>> 
>>> # 创建工具管理器
>>> tool_mgr = ToolMgr()
>>> 
>>> # 创建模拟工具类
>>> class MockTool(Tool):
...     def __init__(self):
...         self.name = "mock_tool"
...         self.description = "A mock tool for testing"
...     def invoke(self, **kwargs):
...         return {"result": "Tool executed"}
...     def get_tool_info(self):
...         return ToolInfo(name=self.name, description=self.description)
>>> 
>>> # 添加工具实例
>>> tool = MockTool()
>>> tool_mgr.add_tool("test_tool", tool)

>>> # 创建多个工具实例
>>> tools_list = [
...     ("tool1", MockTool()),
...     ("tool2", MockTool())
>>> ]
>>> print("Multiple tools created")
>>> tool_mgr.add_tools(tools_list)
>>> print("Tools added successfully")
Multiple tools created
Tools added successfully
```


### get_tool

```python
def get_tool(tool_id: str, runtime=None) -> Optional[Tool]
```

从资源管理器中获取指定的工具实例。支持延迟加载和执行跟踪功能。

**参数**:

- **tool_id**(str): 工具的唯一标识符。
- **runtime**(可选): 运行时环境实例。

**返回**:

- **Optional[Tool]**: 对应的工具实例，若不存在则返回None。

**样例**:

```python
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import ToolMgr
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import Tool
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import ToolInfo
>>> 
>>> # 创建工具管理器
>>> tool_mgr = ToolMgr()
>>> 
>>> # 创建模拟工具类
>>> class MockTool(Tool):
...     def __init__(self):
...         self.name = "mock_tool"
...         self.description = "A mock tool for testing"
...     def invoke(self, **kwargs):
...         return {"result": "Tool executed"}
...     def get_tool_info(self):
...         return ToolInfo(name=self.name, description=self.description)
>>> 
>>> # 添加工具实例
>>> tool = MockTool()
>>> tool_mgr.add_tool("test_tool", tool)

>>> # 获取工具实例
>>> tool = tool_mgr.get_tool("test_tool")
>>> print(f"Tool found: {tool is not None}")
>>> if tool:
...     result = tool.invoke()
...     print(f"Tool executed: {result}")
Tool found: True
Tool executed: {'result': 'Tool executed'}
```

### remove_tool

```python
def remove_tool(tool_id: str) -> Optional[Tool]
```

从资源管理器中移除指定的工具实例。

**参数**:

- **tool_id**(str): 工具的唯一标识符。

**返回**:

- **Optional[Tool]**: 被移除的工具实例，若不存在则返回None。

**样例**:

```python
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import ToolMgr
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import Tool
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import ToolInfo
>>> 
>>> # 创建工具管理器
>>> tool_mgr = ToolMgr()
>>> 
>>> # 创建模拟工具类
>>> class MockTool(Tool):
...     def __init__(self):
...         self.name = "mock_tool"
...         self.description = "A mock tool for testing"
...     def invoke(self, **kwargs):
...         return {"result": "Tool executed"}
...     def get_tool_info(self):
...         return ToolInfo(name=self.name, description=self.description)
>>> 
>>> # 添加工具实例
>>> tool = MockTool()
>>> tool_mgr.add_tool("test_tool", tool)

>>> # 移除工具实例
>>> removed_tool = tool_mgr.remove_tool("test_tool")
>>> print(f"Removed tool: {removed_tool is not None}")
>>> print(f"Removed tool name: {removed_tool.name}")
Removed tool: True
Removed tool name: mock_tool
```

### get_tool_infos

```python
def get_tool_infos(tool_ids: List[str] = None, *, tool_server_name: str = None) -> Optional[List[Union[ToolInfo, McpToolInfo]]]
```

获取工具信息列表，支持按工具ID或工具服务器名称过滤。

**参数**:

- **tool_ids**(List[str], 可选): 工具ID列表。
- **tool_server_name**(str, 可选): 工具服务器名称。

**返回**:

- **Optional[List[Union[ToolInfo, McpToolInfo]]]**: 工具信息列表。

**样例**:

```python
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import ToolMgr
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import Tool
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import ToolInfo
>>> 
>>> # 创建工具管理器
>>> tool_mgr = ToolMgr()
>>> 
>>> # 创建模拟工具类
>>> class MockTool(Tool):
...     def __init__(self):
...         self.name = "mock_tool"
...         self.description = "A mock tool for testing"
...     def invoke(self, **kwargs):
...         return {"result": "Tool executed"}
...     def get_tool_info(self):
...         return ToolInfo(name=self.name, description=self.description)
>>> 
>>> # 添加工具实例
>>> tool = MockTool()
>>> tool_mgr.add_tool("test_tool", tool)

>>> # 获取所有工具信息
>>> all_infos = tool_mgr.get_tool_infos()
>>> print(f"Tool infos found: {all_infos is not None}")
>>> print(f"Total tools: {len(all_infos) if all_infos else 0}")
>>> if all_infos:
...     for i, info in enumerate(all_infos):
...         print(f"Tool {i+1}: {info}")
Tool infos found: True
Total tools: 1
Tool 1: type='function' name='mock_tool' description='A mock tool for testing' parameters=None
```
