The Context Engine is the core component of the openJiuwen framework, primarily responsible for managing the model’s input context information. It provides standardized capabilities for recording, retrieving, and filtering context information (including short/long-term memory, tools, knowledge, etc.), helping developers handle context content more efficiently when building Agents.

The development process of the Context Engine consists of two steps:

- Obtain context: Supports obtaining the Agent-level context instance AgentContext and the workflow-level context instance WorkflowContext of the Agent, and achieves context isolation through session_id.
- Use context: Supports adding single or batch conversation messages, and querying messages by quantity, role, tags, etc. It also supports adding custom tags to messages for metadata management.

# Obtain Context

Users can obtain the context instance of an Agent or the Agent’s workflow as needed.

## Obtain Agent Context

During the process of creating an Agent, the Context Engine is automatically created, so you can create the Agent first to get the corresponding context instance.

### Create an Agent

First, use the constructor of the `ReActAgent` class provided by openJiuwen to instantiate the object. This Agent provides weather query functionality for a specific date. Example code:

```python
import os
os.environ['LLM_SSL_VERIFY'] = 'false'

from datetime import datetime
from openjiuwen.agent.common.schema import PluginSchema
from openjiuwen.agent.react_agent import create_react_agent_config, ReActAgent
from openjiuwen.core.component.common.configs.model_config import ModelConfig
from openjiuwen.core.utils.llm.base import BaseModelInfo
from openjiuwen.core.utils.tool.param import Param
from openjiuwen.core.utils.tool.service_api.restful_api import RestfulApi

API_BASE = os.getenv("API_BASE", "your api base")
API_KEY = os.getenv("API_KEY", "your api key")
MODEL_NAME = os.getenv("MODEL_NAME", "")
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")

def build_current_date():
    current_datetime = datetime.now()
    return current_datetime.strftime("%Y-%m-%d")

def _create_model():
    return ModelConfig(model_provider=MODEL_PROVIDER,
                       model_info=BaseModelInfo(
                           model=MODEL_NAME,
                           api_base=API_BASE,
                           api_key=API_KEY,
                           temperature=0.7,
                           top_p=0.9,
                           timeout=30
                       ))

def _create_tool():
    weather_plugin = RestfulApi(
        name="WeatherReporter",
        description="Weather query plugin",
        params=[
            Param(name="location", description="The location for weather query, must be in English", type="string", required=True),
            Param(name="date", description="The date for weather query, format YYYY-MM-DD", type="string", required=True),
        ],
        path="your weather search api url",
        headers={},
        method="GET",
        response=[],
    )
    return weather_plugin

def _create_prompt_template():
    system_prompt = "You are an AI assistant. Call appropriate tools when appropriate to help me complete tasks! Today's date is: {}\nNote: 1. If the user's request does not specify a specific date, default to today."
    return [
        dict(role="system", content=system_prompt.format(build_current_date()))
    ]

agent_id="react_agent_123"
model_config = _create_model()
prompt_template = _create_prompt_template()

react_agent_config = create_react_agent_config(
    agent_id=agent_id,
    agent_version="0.0.1",
    description="AI Assistant",
    model=model_config,
    prompt_template=prompt_template
)

react_agent: ReActAgent = ReActAgent(react_agent_config)
react_agent.add_tools([_create_tool()])
```

### Obtain the Agent Context Instance

You can access the Agent’s context through `react_agent.context_engine`, then use the `get_agent_context` method to obtain the AgentContext instance by session_id for managing the context across the entire agent scope.

```python
# Obtain the agent context instance via session_id
agent_context = react_agent.context_engine.get_agent_context(session_id= "your_session_id")
```

## Obtain the Agent’s Workflow Context

When creating Agents, users often need to bind one or more workflows. To achieve fine-grained context management, you can use `get_workflow_context` to access the context engine for a specified workflow.

### Create an Agent Bound to a Workflow

First use the `WorkflowAgent` provided by openJiuwen to create a workflow agent and bind a specific workflow. Taking a workflow agent that provides weather query functionality as an example, the creation and binding process is shown below:

```python
from openjiuwen.agent.common.schema import WorkflowSchema
from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
from openjiuwen.core.workflow.base import Workflow
from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata

agent_id = "weather_agent_test"
workflow_id = "your_workflow_id"
workflow_name = "weather"
workflow_version = "1.0"

workflow_config = WorkflowConfig(
    metadata=WorkflowMetadata(
        name=workflow_name,
        id=workflow_id,
        version=workflow_version,
    )
)
flow = Workflow(workflow_config=workflow_config)

schema = WorkflowSchema(
    id=workflow_id,
    name=workflow_name,
    description="Weather query workflow",
    version=workflow_version,
    inputs={"query": {"type": "string"}}
)

config = WorkflowAgentConfig(
    id=agent_id,
    version="0.1.0",
    description="Test weather agent",
    workflows=[schema],
)

workflow_agent = WorkflowAgent(config)
workflow_agent.bind_workflows([flow])
```

### Obtain the Agent’s Workflow Context Instance

You can access the Agent’s context through `workflow_agent.context_engine`, and then use the `get_workflow_context` method with the workflow id and session id, i.e., `workflow_id` and `session_id`, to obtain the WorkflowContext instance for managing context within the agent’s workflow scope.

```python
# Obtain the workflow context instance via workflow_id and session_id
workflow_context = workflow_agent.context_engine.get_workflow_context(workflow_id = "your_workflow_id", session_id = "your_session_id")
```

# Use Context

After obtaining AgentContext or WorkflowContext, you can flexibly use the context. Main features include:
 - Add messages: Add single or batch conversation messages, and support custom tags for message metadata management.
 - Query messages: Query historical messages and support filtering by role, tags, etc.

## Add Information

Supports adding single or batch messages. You can add custom tags when adding messages for convenient metadata management and future querying.

### Add a Single Message

Use the `add_message` method to add a single message. It supports `SystemMessage`, `ToolMessage`, `HumanMessage`, and `AIMessage`. You can use tags to mark message metadata for subsequent filtering and categorization. Messages are automatically assigned sequential IDs to ensure conversation chronology.

```python
from openjiuwen.core.utils.llm.messages import HumanMessage, AIMessage

# Add a user message
user_message = HumanMessage(content="Hello, please help me check the weather")
agent_context.add_message(user_message, tags={"type": "user_input", "time": "2024-01-01"})

# Add an AI response message
ai_message = AIMessage(content="Today is sunny, with a temperature of 25 degrees.")
agent_context.add_message(ai_message, tags={"type": "ai_response", "model": "gpt-4"})
```

### Add Multiple Messages

Use the `batch_add_messages` method to add multiple messages at once, and set the same tags for the entire batch to improve efficiency. This is suitable for initializing conversation history or batch import scenarios.

```python
from openjiuwen.core.utils.llm.messages import HumanMessage, AIMessage

# Prepare the message list
messages = [
    HumanMessage(content="Hello, what can you help me with?"),
    AIMessage(content="I can help answer questions and handle tasks for you."),
    HumanMessage(content="How is the weather today?"),
    AIMessage(content="Today is sunny, with a temperature of 25 degrees.")
]

# Batch add messages
agent_context.batch_add_messages(messages, tags={"source": "user_input", "batch_id": "001"})
```

## Query Information

Supports querying messages by quantity, role, tags, and other conditions.

### Query Information with get_messages

The `get_messages` method supports querying historical messages by quantity and tags, and returns a list of messages. The returned messages are in chronological order, with the latest messages at the end.

First construct a batch of test messages; the following query methods are based on this:

```python
from openjiuwen.core.utils.llm.messages import HumanMessage, AIMessage, SystemMessage

agent_context.add_message(HumanMessage(content="First user message"), tags={"type": "greeting"})
agent_context.add_message(AIMessage(content="First AI reply"))
agent_context.add_message(HumanMessage(content="How is the weather today?"), tags={"type": "weather_query"})
agent_context.add_message(AIMessage(content="It is sunny today."))
agent_context.add_message(SystemMessage(content="System prompt: conversation ended"))
```

#### Query by Quantity

Query messages by quantity and return the latest `num` messages. If `num` exceeds the maximum message length, all messages are returned.

```python
# Example: Get the latest 3 messages
recent_messages = agent_context.get_messages(3)
print("Latest 3 messages:")
for i, msg in enumerate(recent_messages):
    print(f"  {i+1}. {type(msg).__name__}: {msg.content}")
```

Output:

```text
Latest 3 messages:
  1. HumanMessage: How is the weather today?
  2. AIMessage: It is sunny today.
  3. SystemMessage: System prompt: conversation ended
```

#### Query by Tags

Query messages by tags and return the latest `num` messages that exactly match the tags.

```python
# Example: Get the latest messages with specific tags
tagged_messages = agent_context.get_messages(10, tags={"type": "weather_query"})
print("Messages with tag 'weather_query':")
for i, msg in enumerate(tagged_messages):
    print(f"  {i+1}. {type(msg).__name__}: {msg.content}")
```

Output:

```text
Messages with tag 'weather_query':
  1. HumanMessage: How is the weather today?
```

### Query Information with get_latest_message

The `get_latest_message` method retrieves the latest message.

By default, it retrieves the latest message without filtering by role:

```python
# Example 1: Get the latest message (no role restriction)
latest_message = agent_context.get_latest_message()
print(f"Latest message: {type(latest_message).__name__}: {latest_message.content}")
```

Output:

```text
Latest message: SystemMessage: System prompt: conversation ended
```

You can also pass the `role` parameter to filter for the latest message of a specific role. Supported role types: `user`, `assistant`, `system`, and `tool`.

```python
# Example 2: Get the latest user message
latest_user_message = agent_context.get_latest_message(role="user")
print(f"Latest user message: {type(latest_user_message).__name__}: {latest_user_message.content}")
```

Output:

```text
Latest user message: HumanMessage: How is the weather today?
```

If no matching message is found, it returns `None`.

```python
# Example 3: Get a non-existent role message
nonexistent_message = agent_context.get_latest_message(role="tool")
print(f"Non-existent role message: {nonexistent_message}")
```

Output:

```text
Non-existent role message: None
```

# Complete Code Example Using the Context Engine

Below is a complete code example using the Context Engine:

```python
import os
import asyncio
from datetime import datetime
from openjiuwen.agent.react_agent import create_react_agent_config, ReActAgent
from openjiuwen.core.component.common.configs.model_config import ModelConfig
from openjiuwen.core.utils.llm.base import BaseModelInfo
from openjiuwen.core.utils.tool.param import Param
from openjiuwen.core.utils.tool.service_api.restful_api import RestfulApi
from openjiuwen.core.utils.llm.messages import HumanMessage, AIMessage, SystemMessage

os.environ['LLM_SSL_VERIFY'] = 'false'
API_BASE = os.getenv("API_BASE", "your api base")
API_KEY = os.getenv("API_KEY", "your api key")
MODEL_NAME = os.getenv("MODEL_NAME", "")
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")

def build_current_date():
    current_datetime = datetime.now()
    return current_datetime.strftime("%Y-%m-%d")


def _create_model():
    return ModelConfig(model_provider=MODEL_PROVIDER,
                       model_info=BaseModelInfo(
                           model=MODEL_NAME,
                           api_base=API_BASE,
                           api_key=API_KEY,
                           temperature=0.7,
                           top_p=0.9,
                           timeout=30
                       ))


def _create_tool():
    weather_plugin = RestfulApi(
        name="WeatherReporter",
        description="Weather query plugin",
        params=[
            Param(name="location", description="The location for weather query, must be in English", type="string", required=True),
            Param(name="date", description="The date for weather query, format YYYY-MM-DD", type="string", required=True),
        ],
        path="your weather search api url",
        headers={},
        method="GET",
        response=[],
    )
    return weather_plugin


def _create_prompt_template():
    system_prompt = "You are an AI assistant. Call appropriate tools when appropriate to help me complete tasks! Today's date is: {}\nNote: 1. If the user's request does not specify a specific date, default to today."
    return [
        dict(role="system", content=system_prompt.format(build_current_date()))
    ]


agent_id = "react_agent_123"
model_config = _create_model()
prompt_template = _create_prompt_template()

react_agent_config = create_react_agent_config(
    agent_id=agent_id,
    agent_version="0.0.1",
    description="AI Assistant",
    model=model_config,
    prompt_template=prompt_template
)

# The context engine is automatically created during react_agent creation
react_agent = ReActAgent(react_agent_config)
react_agent.add_tools([_create_tool()])


async def run():
    # Generate session id
    session_id = "your_session_id"

    # Invoke the agent
    result = await react_agent.invoke({"query": "Check the weather in Hangzhou", "conversation_id": session_id})

    # Obtain the agent context instance via session_id
    agent_context = react_agent.context_engine.get_agent_context(session_id=session_id)

    # 1. Messages automatically produced by the agent
    recent_msgs = agent_context.get_messages(10)
    print("1. Messages automatically produced by the agent:")
    for i, msg in enumerate(recent_msgs):
        print(f"     {i + 1}. {type(msg).__name__}: {msg.content}")

    # 2. Add a single message manually
    print("2. Manually add a single message")
    user_msg1 = HumanMessage(content="Hello, I'd like to check the weather")
    agent_context.add_message(user_msg1, tags={"intent": "weather_query", "step": "init"})
    print(f"   Added user message: '{user_msg1.content}'")

    ai_msg1 = AIMessage(content="Hello! I can help you check the weather. Which city would you like to check?")
    agent_context.add_message(ai_msg1, tags={"type": "response", "step": "ask_city"})
    print(f"   Added AI reply: '{ai_msg1.content}'\n")

    # 3. Batch add messages
    print("3. Batch add messages")
    conversation_messages = [
        HumanMessage(content="I want to check the weather in Beijing"),
        AIMessage(content="Beijing is sunny turning to partly cloudy today, 15-25°C, air quality is good"),
        HumanMessage(content="Thank you for your help"),
        AIMessage(content="You're welcome. Feel free to ask me anything!")
    ]
    agent_context.batch_add_messages(
        conversation_messages,
        tags={"city": "beijing", "conversation": "complete"}
    )
    print(f"   Batch added {len(conversation_messages)} messages\n")

    # 4. Add a system message
    print("4. Add a system message")
    system_msg = SystemMessage(content="System: Conversation saved")
    agent_context.add_message(system_msg, tags={"type": "system_notification"})
    print(f"   Added system message: '{system_msg.content}'\n")

    # 5. Demonstration of query features
    print("5. Message query feature demonstration")

    # 5.1 Query recent messages
    recent_msgs = agent_context.get_messages(10)
    print("   Latest 10 messages:")
    for i, msg in enumerate(recent_msgs):
        print(f"     {i + 1}. {type(msg).__name__}: {msg.content}")

    # 5.2 Query by tags
    tagged_msgs = agent_context.get_messages(10, tags={"city": "beijing"})
    print(f"\n   Messages with tag 'city=beijing' ({len(tagged_msgs)} items):")
    for i, msg in enumerate(tagged_msgs):
        print(f"     {i + 1}. {type(msg).__name__}: {msg.content}")

    # 5.3 Query latest message
    print("\n   Latest message query:")
    latest_msg = agent_context.get_latest_message()
    print(f"     No role restriction: {type(latest_msg).__name__}: {latest_msg.content}")

    latest_user = agent_context.get_latest_message(role="user")
    print(f"     User role: {type(latest_user).__name__}: {latest_user.content}")

    latest_ai = agent_context.get_latest_message(role="assistant")
    print(f"     AI role: {type(latest_ai).__name__}: {latest_ai.content}")

    # 6. Statistics
    print("\n6. Context statistics")
    all_msgs = agent_context.get_messages(-1)
    user_count = len([msg for msg in all_msgs if hasattr(msg, 'role') and msg.role == 'user'])
    ai_count = len([msg for msg in all_msgs if hasattr(msg, 'role') and msg.role == 'assistant'])
    system_count = len([msg for msg in all_msgs if hasattr(msg, 'role') and msg.role == 'system'])

    print(f"   Total messages: {len(all_msgs)}")
    print(f"   User messages: {user_count}")
    print(f"   AI replies: {ai_count}")
    print(f"   System messages: {system_count}")


if __name__ == "__main__":
    asyncio.run(run())
```

Output:

```text
1. Messages automatically produced by the agent:
     1. HumanMessage: Check the weather in Hangzhou
     2. AIMessage: 
     3. ToolMessage: {"errCode": 182000, "errMessage": "plugin request unknown error", "data": ""}
     4. AIMessage: An unknown error occurred while checking the weather in Hangzhou. The service might be temporarily unavailable. You can try again later, or let me know if you need help with something else.
2. Manually add a single message
   Added user message: 'Hello, I'd like to check the weather'
   Added AI reply: 'Hello! I can help you check the weather. Which city would you like to check?'

3. Batch add messages
   Batch added 4 messages

4. Add a system message
   Added system message: 'System: Conversation saved'

5. Message query feature demonstration
   Latest 10 messages:
     1. AIMessage: 
     2. ToolMessage: {"errCode": 182000, "errMessage": "plugin request unknown error", "data": ""}
     3. AIMessage: An unknown error occurred while checking the weather in Hangzhou. The service might be temporarily unavailable. You can try again later, or let me know if you need help with something else.
     4. HumanMessage: Hello, I'd like to check the weather
     5. AIMessage: Hello! I can help you check the weather. Which city would you like to check?
     6. HumanMessage: I want to check the weather in Beijing
     7. AIMessage: Beijing is sunny turning to partly cloudy today, 15-25°C, air quality is good
     8. HumanMessage: Thank you for your help
     9. AIMessage: You're welcome. Feel free to ask me anything!
     10. SystemMessage: System: Conversation saved

   Messages with tag 'city=beijing' (4 items):
     1. HumanMessage: I want to check the weather in Beijing
     2. AIMessage: Beijing is sunny turning to partly cloudy today, 15-25°C, air quality is good
     3. HumanMessage: Thank you for your help
     4. AIMessage: You're welcome. Feel free to ask me anything!

   Latest message query:
     No role restriction: SystemMessage: System: Conversation saved
     User role: HumanMessage: Thank you for your help
     AI role: AIMessage: You're welcome. Feel free to ask me anything!

6. Context statistics
   Total messages: 11
   User messages: 4
   AI replies: 5
   System messages: 1
```