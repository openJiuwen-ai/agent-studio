# openjiuwen.core.component.start_comp

## class openjiuwen.core.component.start_comp.Start

```python
class openjiuwen.core.component.start_comp.Start(conf: dict)
```

`Start`为openJiuwen内置的工作流开始组件，该组件定义了工作流的入口，用于接收用户的输入，且提供了校验和格式化用户输入的功能。

**参数**：

- **conf**(dict, 可选)：用户输入的格式化配置，传{}或`None`表示不对用户输入做格式化。默认值：`None`。
  - 格式化配置dict有格式规定，需要包含"inputs"键，值为list[dict]类型。若"inputs"类型错误则会返回异常`JiuWenBaseException`。
  - "inputs"中的每个元素为一个输入字段的配置，包含以下字段：

    - id(str)：输入字段的名字，若不提供，则会返回`JiuWenBaseException`异常。
    - default_value(Any, 可选)：输入字段的默认值，仅对于`required=False`的字段生效。默认值：`None`，表示没有默认值。
    - required(bool, 可选)：输入字段是否为必选。默认值：`False`。
  - `config`的样例如下，样例中表示"query"为必选字段，用户在调用工作流时必须提供该输入。

    ```python
    {
        "inputs": [
            {"id": "query", "required": True}, 
            {"id": "dialogueHistory", "default_value": [], "required": False}, 
            {"id": "conversationHistory", "required": False},
        ]
    }
    ```

**异常**：

- **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode)。

**样例**：

```python
>>> import asyncio
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> # 演示Start组件的基本用法和工作流创建流程
>>> async def demo_start_component():
...     # 1. 创建工作流实例
...     workflow = Workflow()
...     
...     # 2. 配置Start组件的输入参数
...     start_config = {
...         "inputs": [
...             {"id": "query", "required": True},
...             {"id": "dialogueHistory", "default_value": ["c", "d"], "required": False},
...             {"id": "conversationHistory", "default_value": ["a", "b"], "required": False},
...         ]
...     }
...     
...     # 3. 创建并设置开始组件
...     start_comp = Start(start_config)
...     workflow.set_start_comp("start", start_comp,
...                            inputs_schema={
...                                "query": "${user_inputs.query}", 
...                                "dialogueHistory": "${user_inputs.dialogueHistory}", 
...                                "conversationHistory": "${user_inputs.conversationHistory}"
...                            })
...     
...     # 4. 设置结束组件捕获输出
...     workflow.set_end_comp("end", Start(),
...                          inputs_schema={
...                              "query": "${start.query}", 
...                              "dialogueHistory": "${start.dialogueHistory}", 
...                              "conversationHistory": "${start.conversationHistory}"
...                          })
...     
...     # 5. 添加组件间连接
...     workflow.add_connection("start", "end")
...     
...     # 6. 执行工作流
...     result = await workflow.invoke(
...         inputs={"user_inputs": {
...             "query": "hello world",
...             "conversationHistory": ["a", "b"]
...         }},
...         runtime=WorkflowRuntime()
...     )
... 
...     print(f"{result}")
>>> 
>>> def main():
...     asyncio.run(demo_start_component())
>>> 
>>> if __name__ == "__main__":
...     main()
>>> # `Start`组件会根据`conf`对于用户的`input`进行格式化，传递给下一个组件，格式化完的结果为：
result={'query': 'hello world', 'dialogueHistory': ['c', 'd'], 'conversationHistory': ['a', 'b']} state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>
```

## class  openjiuwen.core.component.start_comp.StartInputSchema（预留类）

`StartInputSchema`为**预留类**，是内置的`Start`组件定制输入的schema定义，用于替代`config`的功能，当前还未使用。

## class  openjiuwen.core.component.start_comp.StartOutputSchema（预留类）

`StartOutputSchema`为**预留类**，是内置的`Start`组件定制输出的schema定义，用于替代`config`的功能，当前还未使用。
