# openjiuwen.core.runtime.resources_manager.tool_manager

## class openjiuwen.core.runtime.resources_manager.tool_manager.ToolMgr

```python
class openjiuwen.core.runtime.resources_manager.tool_manager.ToolMgr()
```

Tool resource manager for registering, looking up, and removing tool instances, with support for retrieving tool metadata and integrating with MCP servers.


### add_tool

```python
def add_tool(tool_id: str, tool: Union[Tool, ToolProvider]) -> None
```

Add a tool instance or provider to the resource manager, establishing a mapping between the ID and the tool instance.

**Parameters**:

- **tool_id** (str): The unique identifier of the tool.
- **tool** (Union[Tool, ToolProvider]): A tool instance or provider.
  - ToolProvider: A Callable[[], Tool] factory for lazy instantiation of tool objects, enabling on-demand creation for better resource efficiency and type safety.

**Examples**:

```python
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import ToolMgr
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import Tool
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import ToolInfo
>>> 
>>> # Create a tool manager
>>> tool_mgr = ToolMgr()
>>> 
>>> # Create a mock tool class
>>> class MockTool(Tool):
...     def __init__(self):
...         self.name = "mock_tool"
...         self.description = "A mock tool for testing"
...     def invoke(self, **kwargs):
...         return {"result": "Tool executed"}
...     def get_tool_info(self):
...         return ToolInfo(name=self.name, description=self.description)
>>> 
>>> # Add a tool instance
>>> tool = MockTool()
>>> tool_mgr.add_tool("test_tool", tool)
>>> print("Tool added successfully")
Tool added successfully
```

### add_tools

```python
def add_tools(tools: List[Tuple[str, Union[Tool, ToolProvider]]]) -> None
```

Add multiple tool instances to the resource manager in batch, establishing ID-to-instance mappings.

**Parameters**:

- tools (List[Tuple[str, Union[Tool, ToolProvider]]]): A list of tools, where each element is a tuple of (tool ID, tool instance or provider).

Examples:

```python
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import ToolMgr
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import Tool
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import ToolInfo
>>> 
>>> # Create a tool manager
>>> tool_mgr = ToolMgr()
>>> 
>>> # Create a mock tool class
>>> class MockTool(Tool):
...     def __init__(self):
...         self.name = "mock_tool"
...         self.description = "A mock tool for testing"
...     def invoke(self, **kwargs):
...         return {"result": "Tool executed"}
...     def get_tool_info(self):
...         return ToolInfo(name=self.name, description=self.description)
>>> 
>>> # Add a tool instance
>>> tool = MockTool()
>>> tool_mgr.add_tool("test_tool", tool)

>>> # Create multiple tool instances
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

Retrieve a tool instance by ID from the resource manager. Supports lazy loading and execution tracing.

**Parameters**:

- tool_id (str): The unique identifier of the tool.
- runtime (optional): The runtime environment instance.

**Returns**:

- Optional[Tool]: The corresponding tool instance, or None if not found.

Examples:

```python
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import ToolMgr
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import Tool
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import ToolInfo
>>> 
>>> # Create a tool manager
>>> tool_mgr = ToolMgr()
>>> 
>>> # Create a mock tool class
>>> class MockTool(Tool):
...     def __init__(self):
...         self.name = "mock_tool"
...         self.description = "A mock tool for testing"
...     def invoke(self, **kwargs):
...         return {"result": "Tool executed"}
...     def get_tool_info(self):
...         return ToolInfo(name=self.name, description=self.description)
>>> 
>>> # Add a tool instance
>>> tool = MockTool()
>>> tool_mgr.add_tool("test_tool", tool)

>>> # Retrieve the tool instance
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

Remove a specified tool instance from the resource manager.

**Parameters**:

- tool_id (str): The unique identifier of the tool.

**Returns**:

- Optional[Tool]: The removed tool instance, or None if it does not exist.

Examples:

```python
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import ToolMgr
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import Tool
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import ToolInfo
>>> 
>>> # Create a tool manager
>>> tool_mgr = ToolMgr()
>>> 
>>> # Create a mock tool class
>>> class MockTool(Tool):
...     def __init__(self):
...         self.name = "mock_tool"
...         self.description = "A mock tool for testing"
...     def invoke(self, **kwargs):
...         return {"result": "Tool executed"}
...     def get_tool_info(self):
...         return ToolInfo(name=self.name, description=self.description)
>>> 
>>> # Add a tool instance
>>> tool = MockTool()
>>> tool_mgr.add_tool("test_tool", tool)

>>> # Remove the tool instance
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

Retrieve a list of tool metadata, with optional filtering by tool IDs or tool server name.

**Parameters**:

- tool_ids (List[str], optional): A list of tool IDs.
- tool_server_name (str, optional): The name of the tool server.

**Returns**:

- Optional[List[Union[ToolInfo, McpToolInfo]]]: A list of tool metadata.

Examples:

```python
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import ToolMgr
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import Tool
>>> from openjiuwen.core.runtime.resources_manager.tool_manager import ToolInfo
>>> 
>>> # Create a tool manager
>>> tool_mgr = ToolMgr()
>>> 
>>> # Create a mock tool class
>>> class MockTool(Tool):
...     def __init__(self):
...         self.name = "mock_tool"
...         self.description = "A mock tool for testing"
...     def invoke(self, **kwargs):
...         return {"result": "Tool executed"}
...     def get_tool_info(self):
...         return ToolInfo(name=self.name, description=self.description)
>>> 
>>> # Add a tool instance
>>> tool = MockTool()
>>> tool_mgr.add_tool("test_tool", tool)

>>> # Get all tool metadata
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