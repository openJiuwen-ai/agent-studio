This chapter demonstrates how to rapidly develop a custom Agent based on openJiuwen. The Agent built in this example is capable of calling Large Language Model (LLM) services and identifying sensitive words that may be contained in the LLM output results. Through this example, you will learn the following information:

- How to inherit the `AgentConfig` base class to implement a configuration class for a custom Agent.
- How to override the initialization method `__init__` of the `BaseAgent` base class to implement the initialization method for a custom Agent.
- How to implement the batch execution abstract interface `invoke` defined by the `BaseAgent` base class to asynchronously batch execute the specific business logic of the custom Agent.

# Application Design Flow

This chapter designs a custom Agent to implement a safer Agent: it can validate output answers based on a preset list of sensitive words. To implement this Agent, developers need to:

- Design the configuration class for the custom Agent.
- Configure the preset list of sensitive words for the Agent in its initialization method `__init__`.
- Implement the Agent's business logic in the custom Agent's batch execution abstract interface `invoke`: combine the Agent's default system prompt and the user request to construct the input for calling the LLM; then call the LLM service and wait for the LLM's response; finally, validate the LLM output based on the configured sensitive words list to ensure the Agent does not output malicious information.

  <div align="center">
    <img src="../images/MyAgent.png" alt="MyAgent" width="70%">
  </div>

# Prerequisites

The Python version should be higher than or equal to Python 3.11. Version 3.11.4 is recommended. Please check the Python version information before use.

# Install openJiuwen

Users can choose to create a virtual environment to install openJiuwen. The installation command is as follows:

```bash
pip install -U openjiuwen
```

# Implementing the Custom Agent Configuration Class

To implement an Agent capable of calling LLM services and identifying sensitive words that may be contained in the LLM output results, in addition to the basic configuration items defined in `AgentConfig` (such as the Agent's `id`, `version`, `description`, etc.), custom configurations are also needed (specifically including the configuration information `model` for calling the LLM and the custom sensitive words list `sensitive_words`). The example code is as follows:

```python
import os
from typing import Optional, List
from pydantic import Field
from openjiuwen.agent.config.base import AgentConfig
from openjiuwen.core.utils.llm.base import BaseModelInfo
from openjiuwen.core.component.common.configs.model_config import ModelConfig


class MyAgentConfig(AgentConfig):
    model: Optional[ModelConfig] = Field(default=None)
    sensitive_words: List[str] = Field(default_factory=list)


def create_model_config() -> ModelConfig:
    """通过环境变量获取大模型相关的配置信息"""
    return ModelConfig(
        model_provider=os.getenv("MODEL_PROVIDER", ""),
        model_info=BaseModelInfo(
            model=os.getenv("MODEL_NAME", ""),
            api_base=os.getenv("API_BASE", ""),
            api_key=os.getenv("API_KEY", ""),
            temperature=0.7,
            top_p=0.9,
            timeout=30,
        ),
    )

# 创建自定义智能体配置信息的对象
my_agent_config = MyAgentConfig(
    id="my_agent_id",
    version="0.0.1",
    description="我的自定义智能体",
    model=create_model_config(),  # 配置大模型相关参数信息
    sensitive_words=["自定义敏感词列表"]
)
```

Among them, the configuration information of the LLM service is read via the `create_model_config` method through environment variables, including the model provider (`MODEL_PROVIDER`), model name (`MODEL_NAME`), LLM service call path (`API_BASE`), and LLM service authentication information (`API_KEY`), completing the configuration of the LLM service call object.

# Implementing the Initialization Method

Next, developers need to implement the initialization method of the custom Agent to support the creation of custom Agent objects. The initialization method of the `BaseAgent` base class provides the Agent with the capabilities of initializing `Runtime` and configuration management `Config`. In addition to calling the initialization method of the `BaseAgent` base class, the custom Agent also needs to create an LLM call object based on the LLM configuration information and initialize the configured sensitive words list. The specific example is as follows:

```python
from openjiuwen.agent.config.base import AgentConfig
from openjiuwen.core.agent.agent import BaseAgent
from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory

class MyAgent(BaseAgent):
    def __init__(self, agent_config : AgentConfig):
        # 初始化配置信息
        super().__init__(agent_config)
        # 获取大模型配置
        self._model_config = agent_config.model
        # 使用ModelFactory 创建大模型调用对象
        self._llm = ModelFactory().get_model(
            model_provider=self._model_config.model_provider,
            api_key=self._model_config.model_info.api_key,
            api_base=self._model_config.model_info.api_base
        )
        # 初始化配置自定义敏感词列表
        self._sensitive_words = agent_config.sensitive_words
```

Here, the LLM instance is created via the `get_model` method of `ModelFactory` based on the configuration information in `ModelConfig`.

# Implementing the invoke Method

The Agent in this example possesses the following functions: it is capable of calling LLM services and identifying sensitive words that may be contained in the LLM output results.

The `invoke` method is used to call the LLM. Before calling, the user input is encapsulated as a `HumanMessage`, combined with the custom Agent's built-in system prompt `SystemMessage`, and used as input for the LLM to obtain the returned result. Finally, check whether the LLM output contains custom sensitive words. Once the LLM output contains custom sensitive words, a fixed phrase is output: "Sorry, I cannot answer your question." The example code is as follows:

```python
from typing import Dict
from openjiuwen.core.agent.agent import BaseAgent
from openjiuwen.core.runtime.runtime import Runtime
from openjiuwen.core.utils.llm.messages import HumanMessage, SystemMessage

class MyAgent(BaseAgent):
    async def invoke(self, inputs: Dict, runtime: Runtime = None):
        # inputs是自定义智能体的输入，以llm_inputs为键，用户输入信息作为用户提示词
        user_message = HumanMessage(content=inputs.get("llm_inputs", "")).model_dump(exclude_none=True)
        # 自定义智能体的默认系统提示词
        system_message = SystemMessage(content="你是一个AI助手").model_dump(exclude_none=True)
        # 大模型输入包括：系统提示词和用户提示词
        llm_input_messages = [system_message, user_message]
        # 调用模型的异步执行方法方法得到模型的输出
        res = await self._llm.ainvoke(model_name=self._model_config.model_info.model_name, messages=llm_input_messages)
        llm_output = res.content
        for word in self._sensitive_words:
            if word in llm_output:
                return "对不起，无法回答您的问题。"
        # 如果大模型输出不包含敏感词，则直接返回大模型输出内容
        return llm_output
```

# Implementing the stream Method

The `stream` method enables streaming invocation capability for the agent, returning an asynchronous iterator to support real-time responses. In this example implementation, for simplicity, the method directly reuses the complete processing logic from `invoke`, returning the final result as a single streaming chunk. The implementation is as follows:

```python
from typing import AsyncIterator, Any

class MyAgent(BaseAgent):
    async def stream(self, inputs: Dict, runtime: Runtime = None) -> AsyncIterator[Any]:
        content = await self.invoke(inputs)
        yield {"type": "answer", "content": content}
```

# Running the Custom Agent

After the developer completes the relevant implementation of the custom Agent, they can call the `invoke` method to run the custom Agent asynchronously and non-streamingly. The example code is as follows:

```python
import asyncio

# 创建自定义智能体的对象
my_agent = MyAgent(my_agent_config)

inputs = {"llm_inputs": "写一个笑话"}
res = asyncio.run(my_agent.invoke(inputs))
print(res)
```

# Complete Example Code

The complete example reference is as follows:

```python
import asyncio
import os
from typing import Optional, List, Dict, AsyncIterator, Any
from pydantic import Field

from openjiuwen.agent.config.base import AgentConfig
from openjiuwen.core.agent.agent import BaseAgent
from openjiuwen.core.runtime.runtime import Runtime
from openjiuwen.core.utils.llm.base import BaseModelInfo
from openjiuwen.core.component.common.configs.model_config import ModelConfig
from openjiuwen.core.utils.llm.messages import HumanMessage, SystemMessage
from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory


def create_model_config() -> ModelConfig:
    """通过环境变量获取大模型相关的配置信息"""
    return ModelConfig(
        model_provider=os.getenv("MODEL_PROVIDER", ""),
        model_info=BaseModelInfo(
            model=os.getenv("MODEL_NAME", ""),
            api_base=os.getenv("API_BASE", ""),
            api_key=os.getenv("API_KEY", ""),
            temperature=0.7,
            top_p=0.9,
            timeout=30,
        ),
    )


class MyAgentConfig(AgentConfig):
    model: Optional[ModelConfig] = Field(default=None)
    sensitive_words: List[str] = Field(default_factory=list)


class MyAgent(BaseAgent):
    def __init__(self, agent_config : AgentConfig):
        # 初始化配置信息
        super().__init__(agent_config)
        # 获取大模型配置
        self._model_config = agent_config.model
        # 使用ModelFactory 创建大模型调用对象
        self._llm = ModelFactory().get_model(
            model_provider=self._model_config.model_provider,
            api_key=self._model_config.model_info.api_key,
            api_base=self._model_config.model_info.api_base
        )
        # 初始化配置自定义敏感词列表
        self._sensitive_words = agent_config.sensitive_words

    async def invoke(self, inputs: Dict, runtime: Runtime = None):
        # inputs是自定义智能体的输入，以llm_inputs为键，用户输入信息作为用户提示词
        user_message = HumanMessage(content=inputs.get("llm_inputs", "")).model_dump(exclude_none=True)
        # 自定义智能体的默认系统提示词
        system_message = SystemMessage(content="你是一个AI助手").model_dump(exclude_none=True)
        # 大模型输入包括：系统提示词和用户提示词
        llm_input_messages = [system_message, user_message]
        # 调用模型的异步执行方法方法得到模型的输出
        res = await self._llm.ainvoke(model_name=self._model_config.model_info.model_name, messages=llm_input_messages)
        llm_output = res.content
        for word in self._sensitive_words:
            if word in llm_output:
                return "对不起，无法回答您的问题。"
        # 如果大模型输出不包含敏感词，则直接返回大模型输出内容
        return llm_output

    async def stream(self, inputs: Dict, runtime: Runtime = None) -> AsyncIterator[Any]:
        content = await self.invoke(inputs)
        yield {"type": "answer", "content": content}


async def main():
    # 创建自定义智能体配置信息的对象
    my_agent_config = MyAgentConfig(
        id="my_agent_id",
        version="0.0.1",
        description="我的自定义智能体",
        model=create_model_config(),  # 配置大模型相关参数信息
        sensitive_words=["自定义敏感词列表"]
    )

    # 创建自定义智能体的对象
    my_agent = MyAgent(my_agent_config)

    inputs = {"llm_inputs": "写一个笑话"}
    res = await my_agent.invoke(inputs)
    print(res)


if __name__ == "__main__":
    asyncio.run(main())
```

If the joke contains custom sensitive words, the final output result is:

```python
对不起，无法回答您的问题。
```

Conversely, it outputs a joke generated by the LLM.

```python
问：小熊为什么不上班？答：因为它熊啊。
```