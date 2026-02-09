本章节演示了如何基于openJiuwen构建一个用于天气查询的`ReActAgent`应用，该应用支持通过ReAct规划模式引导大模型生成插件调用命令，进而结合插件执行结果生成最终答案。通过示例，你将会了解到如下信息：

- 如何创建提示词。
- 如何使用插件模块。
- 如何创建和执行`ReActAgent`。

# 应用设计流程

`ReActAgent`是一种遵循ReAct（Reasoning + Action）规划模式的Agent，通过 “思考（Thought）→ 行动（Action）→ 观察（Observe）”的循环迭代完成用户任务。

1. 思考：`ReActController`调用LLM进行任务规划，解析 LLM 输出里是否包含工具执行指令。
2. 行动：根据思考中 LLM 的输出，分两种情况进行操作：
    - 有工具执行指令：调工具，选择并调用合适的工具（如检索、数据库、第三方API、代码执行等）执行具体的操作，本用例中是调用一个根据时间和地点查询天气的工具；
    - 无工具执行指令：把LLM输出作为最终答案。
3. 观察：`ReActController`把工具返回的Observation追加到对话历史，再调用LLM进行下一次任务规划。

`ReActAgent`能根据工具执行结果观察与反馈，不断调整策略，优化推理路径，直至达成任务目标或获得最终答案。其强大的多轮推理与自我修正能力，使ReActAgent具备动态决策能力且能够灵活应对环境变化，适用于需要复杂推理和策略调整的多样化任务场景。

  <div align="center">
    <img src="../images/ReActAgent.png" alt="ReActAgent" width="70%">
  </div>

# 前提条件

Python的版本应高于或者等于Python 3.11版本，建议使用3.11.4版本，使用前请检查Python版本信息。

# 安装openJiuwen

执行如下命令安装openJiuwen：

```bash
pip install -U openjiuwen
```

# 创建提示词模板

创建系统提示词模板，用于设定`ReActAgent`的整体行为和角色定位。以下系统提示词不仅定义了人设、任务目标，同时提供了当前日期信息，还给定了约束限制，帮助`ReActAgent`在与用户交互时正确理解当前时间完成任务目标。示例代码如下：

```python
def build_current_date():
    """获取当前日期"""
    from datetime import datetime
    current_datetime = datetime.now()
    return current_datetime.strftime("%Y-%m-%d")

def _create_prompt_template():
    system_prompt = ("你是一个AI助手，在适当的时候调用合适的工具，帮助我完成任务！\n"  # 人设&任务目标
                     "今天的日期为：{}\n"                                       # 当前日期
                     "注意：1. 如果用户请求中未指定具体时间，则默认为今天。")         # 约束限制
    return [
        dict(role="system", content=system_prompt.format(build_current_date()))
    ]
```

# 创建插件对象及其描述信息

本示例创建了天气查询插件，并定义了其输入参数的结构和要求。首先通过`RestfulApi`接口将天气查询服务封装成可以被框架使用的工具类。示例代码如下：

> **注意**
> 本地测试请求服务（http 开头），可以通过配置相关的环境变量关闭SSL校验。但禁用SSL会跳过证书验证，可能遭遇数据篡改、中间人攻击，导致敏感信息泄露，仅允许测试环境临时使用，生产环境务必启用SSL校验保障安全。

```python
import os
from openjiuwen.core.utils.tool.service_api.restful_api import RestfulApi
from openjiuwen.core.utils.tool.param import Param

os.environ["LLM_SSL_VERIFY"] = "false"  # 关闭SSL校验仅用于本地调试，生产环境请务必打开
os.environ["RESTFUL_SSL_VERIFY"] = "false"  # 关闭SSL校验仅用于本地调试，生产环境请务必打开

def _create_tool():
    weather_plugin = RestfulApi(
        name="WeatherReporter",
        description="天气查询插件",
        params=[
            Param(name="location", description="天气查询的地点，必须为英文", type="string", required=True),
            Param(name="date", description="天气查询的时间，格式为YYYY-MM-DD", type="string", required=True),
        ],
        path="your weather search api url",  # 天气查询服务部署地址
        headers={},
        method="GET",
        response=[],
    )
    return weather_plugin
```

同时通过`PluginSchema`接口创建了插件描述信息，该描述信息后续将成为大模型输入的一部分，引导大模型生成工具调用命令。示例代码如下：

```python
from openjiuwen.agent.common.schema import PluginSchema

def _create_tool_schema():
    tool_info = PluginSchema(
        name='WeatherReporter',
        description='天气查询插件',
        inputs={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "天气查询的地点。\n注意：地点名称必须为英文",
                    "required": True
                },
                "date": {
                    "type": "string",
                    "description": "天气查询的时间，格式为YYYY-MM-DD",
                    "required": True
                }
            }
        }
    )
    return tool_info
```

## 创建MCP扩展插件

openJiuwen支持创建集成MCP（Model Context Protocol）扩展协议的插件。本示例创建了一个基于SSE协议的天气查询MCP插件。openJiuwen提供了MCP客户端的`connect`、`disconnect`方法，实现MCP客户端与MCP服务器建立、断开链接。

```python
from openjiuwen.core.utils.tool.mcp.base import MCPTool, SseClient, McpToolInfo

class McpToolWrapper:
    def __init__(self, server_path, name):
        self.mcp_client = SseClient(server_path=server_path, name=name)

    async def connect(self):
        await self.mcp_client.connect()

    async def disconnect(self):
        await self.mcp_client.disconnect()

    def create_mcp_tools(self):
        mcp_tool_info = McpToolInfo(
            type="function",
            name="query_weather",
            server_name="McpSseServer",
            input_schema={
                "type": "object",
                "title": "query_weatherArguments",
                "properties": {
                    "location": {
                        "title": "Location",
                        "type": "string"
                    }
                },
                "required": [
                    "location"
                ],
            }
        )
        mcp_tool = MCPTool(mcp_client=self.mcp_client, tool_info=mcp_tool_info)
        return [mcp_tool]
```


# 创建ReActAgent

首先使用openJiuwen提供的`create_react_agent_config`方法快速创建天气查询的`ReActAgentConfig`对象，涵盖`ReActAgent`相关的配置参数信息，如提示词定义及大模型配置信息等。示例代码如下：

```python
from openjiuwen.agent.react_agent import create_react_agent_config

react_agent_config = create_react_agent_config(
    agent_id="react_agent_123",
    agent_version="0.0.1",
    description="AI助手",
    model=_create_model_config(),    # 大模型的配置信息
    prompt_template=_create_prompt_template()  # 自定义提示词
)
```

其中，`_create_model_config`用于定义大模型的相关配置信息，如模型提供商、模型名称、API调用和模型温度等信息：

```python
import os
from openjiuwen.core.utils.llm.base import BaseModelInfo
from openjiuwen.core.component.common.configs.model_config import ModelConfig

API_BASE = os.getenv("API_BASE", "your api base")
API_KEY = os.getenv("API_KEY", "your api key")
MODEL_NAME = os.getenv("MODEL_NAME", "")
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")


def _create_model_config() -> ModelConfig:
    return ModelConfig(
        model_provider=MODEL_PROVIDER,
        model_info=BaseModelInfo(
            model=MODEL_NAME,
            api_base=API_BASE,
            api_key=API_KEY,
            temperature=0.7,
            top_p=0.9,
            timeout=30,
        ),
    )
```

接着使用openJiuwen提供的`ReActAgent`类的构造函数实例化对象，包括天气查询助手配置，示例代码如下：

```python
from openjiuwen.agent.react_agent import ReActAgent

react_agent = ReActAgent(react_agent_config)
react_agent.add_tools([_create_tool()])
```

## ReActAgent关联MCP扩展插件

openJiuwen支持`ReActAgent`关联MCP插件。开发者指定连接MCP服务器的IP地址，通过`connect`与MCP服务器建立链接。`ReActAgent`执行结束后，开发者通过`disconnect`与MCP服务器断开链接。

```python
import asyncio
from openjiuwen.agent.react_agent import ReActAgent
from openjiuwen.core.runner.runner import Runner

async def main():
   react_agent = ReActAgent(react_agent_config)
   wrapper = McpToolWrapper(server_path="your path to mcp server", name="McpSseServer")
   await wrapper.connect()  # 与MCP服务器建立链接
   react_agent.add_tools(wrapper.create_mcp_tools())
   
   try:
       # 运行ReActAgent
       result = await Runner.run_agent(react_agent, {"query": "北京天气怎么样"})
       print(f"ReActAgent 最终输出结果：{result}")
   finally:
       await wrapper.disconnect()  # 与MCP服务器断开链接

asyncio.run(main())
```

# 运行ReActAgent

创建完`ReActAgent`对象后，可以调用`invoke`方法，获取用户query的回复。`ReActAgent`的`invoke`方法实现了ReAct的规划流程，通过大模型生成计划，判断是否需要执行工具，如果需要，执行工具调用来完成任务，返回最终结果，否则直接返回模型输出结果，结束流程。示例代码如下：

```python
import asyncio

result = asyncio.run(react_agent.invoke({"query": "查询杭州的天气"}))
print(f"ReActAgent 最终输出结果：{result.get("output")}")
```

查询成功后，会得到如下的结果：

```text
ReActAgent 最终输出结果：
当前杭州的天气情况如下：
- 天气现象：小雨
- 实时温度：30.78℃
- 体感温度：37.78℃
- 空气湿度：74%
- 风速：0.77米/秒（约2.8公里/小时）

建议外出时携带雨具，注意防雨防滑。需要其他天气信息可以随时告诉我哦~
```


# 完整示例代码

```python
import asyncio
import os
from datetime import datetime

from openjiuwen.agent.react_agent import create_react_agent_config, ReActAgent
from openjiuwen.core.component.common.configs.model_config import ModelConfig
from openjiuwen.core.utils.llm.base import BaseModelInfo
from openjiuwen.core.utils.tool.param import Param
from openjiuwen.core.utils.tool.service_api.restful_api import RestfulApi

API_BASE = os.getenv("API_BASE", "your api base")
API_KEY = os.getenv("API_KEY", "your api key")
MODEL_NAME = os.getenv("MODEL_NAME", "")
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
os.environ.setdefault("LLM_SSL_VERIFY", "false")  # 关闭SSL校验仅用于本地调试，生产环境请务必打开
os.environ.setdefault("RESTFUL_SSL_VERIFY", "false")  # 关闭SSL校验仅用于本地调试，生产环境请务必打开

def build_current_date():
    current_datetime = datetime.now()
    return current_datetime.strftime("%Y-%m-%d")

class ReactAgentImpl:
    @staticmethod
    def _create_model():
        return ModelConfig(model_provider=MODEL_PROVIDER,
                           model_info=BaseModelInfo(
                               model=MODEL_NAME,
                               api_base=API_BASE,
                               api_key=API_KEY,
                               temperature=0.7,
                               top_p=0.9,
                               timeout=30  # 添加超时设置
                           ))

    @staticmethod
    def _create_tool():
        weather_plugin = RestfulApi(
            name="WeatherReporter",
            description="天气查询插件",
            params=[
                Param(name="location", description="天气查询的地点，必须为英文", type="string", required=True),
                Param(name="date", description="天气查询的时间，格式为YYYY-MM-DD", type="string", required=True),
            ],
            path="user's path to weather service",
            headers={},
            method="GET",
            response=[],
        )
        return weather_plugin

    @staticmethod
    def _create_prompt_template():
        system_prompt = "你是一个AI助手，在适当的时候调用合适的工具，帮助我完成任务！今天的日期为：{}\n注意：1. 如果用户请求中未指定具体时间，则默认为今天。"
        return [
            dict(role="system", content=system_prompt.format(build_current_date()))
        ]

async def main():
    model_config = ReactAgentImpl._create_model()
    prompt_template = ReactAgentImpl._create_prompt_template()

    react_agent_config = create_react_agent_config(
        agent_id="react_agent_123",
        agent_version="0.0.1",
        description="AI助手",
        model=model_config,
        prompt_template=prompt_template
    )

    react_agent: ReActAgent = ReActAgent(react_agent_config)
    react_agent.add_tools([ReactAgentImpl._create_tool()])

    result = await react_agent.invoke({"query": "查询杭州的天气"})
    print(f"ReActAgent 最终输出结果：{result}")

if __name__ == "__main__":
    asyncio.run(main())
```

最终输出结果为：

```
ReActAgent 最终输出结果：
当前杭州的天气情况如下：
- 天气现象：小雨
- 实时温度：30.78℃
- 体感温度：37.78℃
- 空气湿度：74%
- 风速：0.77米/秒（约2.8公里/小时）

建议外出时携带雨具，注意防雨防滑。需要其他天气信息可以随时告诉我哦~
```
