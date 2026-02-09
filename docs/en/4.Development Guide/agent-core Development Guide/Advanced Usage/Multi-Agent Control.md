Multi-Agent is the core mechanism of the openJiuwen framework designed to handle complex task scenarios. When tasks involve multi-dimensional professional capabilities, require step-by-step collaboration, or a single Agent cannot cover the entire process, the multi-Agent control architecture can reasonably decompose tasks, assign different modules to Agents with corresponding expertise, and leverage collaboration between Agents to achieve the overall goal, ultimately enabling efficient coordination and flexible responses.
For example, in a financial transfer scenario, when a user initiates a request like “I want to transfer money,” the system automatically matches the transfer service Agent via intent recognition and starts the transfer workflow. If it detects that the user did not provide the amount parameter, it triggers a workflow interruption and asks the user for the amount. After the user provides the specific amount, the system automatically detects the interrupted Agent and resumes it, continuously advancing the transfer process to completion.

# Multi-Agent Construction and Execution Flow

Multi-Agent is implemented and managed via `HierarchicalGroup`. It can perform intent recognition on user queries, automatically selecting suitable Agents for the task, or you can specify a particular Agent to execute the task and support Agent hopping and resumption.
The Multi-Agent development process includes the following steps:

* Create `WorkflowAgent`: Create a `WorkflowAgent` instance and bind relevant workflows based on the scenario.
* Create `HierarchicalGroup`: Initialize a Leader Agent via `ControllerAgent` (the entry point of the entire Multi-Agent system), then bind this Leader Agent together with all created `WorkflowAgent` instances to the `HierarchicalGroup`.
* Run Multi-Agent: Multi-Agent scenarios support batch and streaming invocations. In addition, task execution provides flexible scheduling strategies: besides autonomous Agent selection to handle tasks, you can directly designate a specific Agent to complete the target task, or trigger collaborative execution through a subscription-based message broadcasting mechanism.

## Create WorkflowAgent

Users can create multiple `WorkflowAgent` objects as needed and bind relevant workflows to each. Refer to [Build Workflow](../Workflows/Build%20Workflow.md), [Build WorkflowAgent](../Agents/Build%20WorkflowAgent.md)

```python
import os
from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
from openjiuwen.core.workflow.base import Workflow
from openjiuwen.core.component.common.configs.model_config import ModelConfig
from openjiuwen.core.component.end_comp import End
from openjiuwen.core.component.questioner_comp import (
    FieldInfo,
    QuestionerComponent,
    QuestionerConfig
)
from openjiuwen.agent.config.base import AgentConfig
from openjiuwen.core.component.start_comp import Start
from openjiuwen.core.utils.llm.base import BaseModelInfo
from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata

API_BASE = os.getenv("API_BASE", "your api base")
API_KEY = os.getenv("API_KEY", "your api key")
MODEL_NAME = os.getenv("MODEL_NAME", "")
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")


def _create_model_config() -> ModelConfig:
    """Create model configuration"""
    return ModelConfig(
        model_provider=MODEL_PROVIDER,
        model_info=BaseModelInfo(
            model=MODEL_NAME,
            api_base=API_BASE,
            api_key=API_KEY,
            temperature=0.7,
            top_p=0.9,
            timeout=120,
        ),
    )

def _create_start_component():
    """Create Start component"""
    return Start({
        "inputs": [
            {
                "id": "query",
                "type": "String",
                "required": "true",
                "sourceType": "ref"
            }
        ]
    })


def _build_financial_workflow(
        workflow_id: str,
        workflow_name: str,
        workflow_desc: str,
        field_name: str,
        field_desc: str
) -> Workflow:
    """
    Build a financial business workflow (with an interruption node)

    Args:
        workflow_id: Workflow ID
        workflow_name: Workflow name
        workflow_desc: Workflow description
        field_name: Field name to ask for
        field_desc: Field description to ask for

    Returns:
        Workflow: A workflow containing start -> questioner -> end
    """
    workflow_config = WorkflowConfig(
        metadata=WorkflowMetadata(
            name=workflow_name,
            id=workflow_id,
            version="1.0",
            description=workflow_desc,
        )
    )
    flow = Workflow(workflow_config=workflow_config)

    # Create components
    start = _create_start_component()

    # Create the questioner (interruption node)
    key_fields = [
        FieldInfo(
            field_name=field_name,
            description=field_desc,
            required=True
        ),
    ]
    model_config = _create_model_config()
    questioner_config = QuestionerConfig(
        model=model_config,
        question_content="",
        extract_fields_from_response=True,
        field_names=key_fields,
        with_chat_history=False,
    )
    questioner = QuestionerComponent(questioner_config)

    # End component
    end = End({"responseTemplate": f"{workflow_name} completed: {{{{{field_name}}}}}"})

    # Register components
    flow.set_start_comp("start", start, inputs_schema={"query": "${query}"})
    flow.add_workflow_comp(
        "questioner", questioner, inputs_schema={"query": "${start.query}"}
    )
    flow.set_end_comp(
        "end", end, inputs_schema={field_name: f"${{questioner.{field_name}}}"}
    )

    # Topology: start -> questioner -> end
    flow.add_connection("start", "questioner")
    flow.add_connection("questioner", "end")

    return flow

def _create_workflow_agent(
        agent_id: str,
        description: str,
        workflow: Workflow
) -> WorkflowAgent:
    """Create WorkflowAgent"""
    config = WorkflowAgentConfig(
        id=agent_id,
        version="1.0",
        description=description,
        workflows=[],
        model=_create_model_config(),
    )
    agent = WorkflowAgent(config)
    agent.add_workflows([workflow])
    return agent

# Create financial business workflows
transfer_workflow = _build_financial_workflow(
    workflow_id="transfer_flow",
    workflow_name="Transfer Service",
    workflow_desc="Handle user transfer requests and support transfers to specified accounts",
    field_name="amount",
    field_desc="Transfer amount (numeric)"
)

balance_workflow = _build_financial_workflow(
    workflow_id="balance_flow",
    workflow_name="Balance Inquiry",
    workflow_desc="Query user account balance information",
    field_name="account",
    field_desc="Account number"
)

invest_workflow = _build_financial_workflow(
    workflow_id="invest_flow",
    workflow_name="Wealth Management Service",
    workflow_desc="Provide wealth management product recommendations and purchasing services",
    field_name="product",
    field_desc="Wealth management product name"
)

# Create WorkflowAgent
transfer_agent = _create_workflow_agent(
    agent_id="transfer_agent",
    description="Transfer service, handles users' transfer requests",
    workflow=transfer_workflow
)

balance_agent = _create_workflow_agent(
    agent_id="balance_agent",
    description="Balance inquiry service, queries user account balances",
    workflow=balance_workflow
)

invest_agent = _create_workflow_agent(
    agent_id="invest_agent",
    description="Wealth management service, provides product recommendations and purchasing",
    workflow=invest_workflow
)
```

## Create HierarchicalGroup
`HierarchicalGroup` uses a Leader-Worker multi-Agent architecture, ready to use, with a built-in Leader Agent and multiple Worker Agents.
- Leader Agent: External messages are routed to the Leader Agent by default. The Leader Agent distributes messages to corresponding Worker Agents.
- Worker Agent: Executes tasks assigned by the Leader Agent.

Depending on the scenario, users can create a `HierarchicalGroup` object to handle complex tasks and add the previously created workflow Agents to the group. Note: you must add the Leader Agent first when adding Agents.

```python
from openjiuwen.agent_group.hierarchical_group import (
    HierarchicalGroup,
    HierarchicalGroupConfig
)

config = HierarchicalGroupConfig(
    group_id="financial_group",
    leader_agent_id="main_controller"
)
hierarchical_group = HierarchicalGroup(config)
```
### Create Leader Agent
The Leader Agent is a `ControllerAgent` holding `HierarchicalMainController`. Creating a `HierarchicalGroup` requires specifying the corresponding Leader Agent. As the controller, `HierarchicalMainController` is responsible for intent recognition and task distribution. By default, `HierarchicalGroup` routes messages directly to the Leader Agent, which uses the LLM to identify the next Agent to handle the task and then forwards the message accordingly.
```python
from openjiuwen.agent.config.base import AgentConfig
from openjiuwen.agent_group.hierarchical_group.agents.main_controller import HierarchicalMainController
from openjiuwen.core.agent.agent import ControllerAgent

main_config = AgentConfig(
    id="main_controller",
    description="Financial services main controller, recognizes user intent and distributes tasks"
)
main_controller = HierarchicalMainController()
main_agent = ControllerAgent(main_config, controller=main_controller)
```

### Add all sub-agents
Use `add_agent` to add all sub-Agents (Leader Agent and Worker Agents) to the Group to complete the `HierarchicalGroup` instantiation.

```python
# Add all agents to the group
hierarchical_group.add_agent("main_controller", main_agent)
hierarchical_group.add_agent("transfer_agent", transfer_agent)
hierarchical_group.add_agent("balance_agent", balance_agent)
hierarchical_group.add_agent("invest_agent", invest_agent)
```

## Run Multi-Agent
Multi-Agent supports batch and streaming invocation and provides 3 message routing methods.
### Message routing
By default, Multi-Agent automatically selects a bound Agent to execute the task based on user input. You can also execute Agents via broadcasting and point-to-point calls. Among them, point-to-point communication has the highest priority, broadcasting is second, and by default messages are routed to the Leader Agent for processing.
#### Pub/Sub broadcasting
Multi-Agent allows bound Agents to subscribe to topics. When an input message carries topic information, the relevant Agents will receive and process the message.
```python
from openjiuwen.core.agent.message.message import Message
import asyncio

conversation_id = "session_001"
hierarchical_group.group_controller.subscribe("test_query1", ["transfer_agent"])
message1 = Message.create_user_message(
    content="Transfer money to Zhang San",
    conversation_id=conversation_id
)
# Broadcast the message to all agents subscribed to the test_query1 topic
message1.message_type = "test_query1"
result1 = asyncio.run(hierarchical_group.invoke(message1))
print(result1)
```
Expected output
```
[OutputSchema(type='__interaction__', index=0, payload=InteractionOutput(id='questioner', value='Please provide information about the transfer amount (numeric)'))]
```
#### Point-to-point communication
Multi-Agent supports point-to-point calls to bound Agents to process messages.

```python
from openjiuwen.core.agent.message.message import Message
import asyncio

conversation_id = "session_002"
message2 = Message.create_user_message(
    content="Transfer money to Zhang San",
    conversation_id=conversation_id
)
# receiver_id specifies the Agent bound to the group with the corresponding agent_id to execute the task
message2.receiver_id = "transfer_agent"
result2 = asyncio.run(hierarchical_group.invoke(message2))
print(result2)
```
Expected output
```
[OutputSchema(type='__interaction__', index=0, payload=InteractionOutput(id='questioner', value='Please provide information about the transfer amount (numeric)'))]
```

#### Default routing to the Leader Agent
If no message routing method is specified, the message will be sent directly to the Leader Agent for processing by default.

```python
from openjiuwen.core.agent.message.message import Message
import asyncio

conversation_id = "session_003"
message3 = Message.create_user_message(
    content="Transfer money to Zhang San",
    conversation_id=conversation_id
)
result3 = asyncio.run(hierarchical_group.invoke(message3))
print(result3)
```
Expected output
```
[OutputSchema(type='__interaction__', index=0, payload=InteractionOutput(id='questioner', value='Please provide information about the transfer amount (numeric)'))]
```

### Batch invocation
Multi-Agent directly returns the final message result.
```python
from openjiuwen.core.agent.message.message import Message
import asyncio

conversation_id = "session_test"
message = Message.create_user_message(
    content="Transfer 500 yuan to Zhang San",
    conversation_id=conversation_id,
)
# Batch invocation
result = asyncio.run(hierarchical_group.invoke(message))
print(result)
```
Expected return
```
{'output': WorkflowOutput(result={'responseContent': 'Transfer Service completed: 500'}, state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>), 'result_type': 'answer'}
```

### Streaming invocation
Multi-Agent supports streaming returns of intermediate results.
```python
import asyncio
from openjiuwen.core.agent.message.message import Message

async def main():
    message = Message.create_user_message(
        content="Transfer 500 yuan to Zhang San",
        conversation_id="stream_session_test"
    )

    # Streaming invocation
    async for chunk in hierarchical_group.stream(message):
        print(f"Output: {chunk}")

if __name__ == "__main__":
    asyncio.run(main())
```
Expected return
```
Output: type='tracer_agent' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 167499), 'endTime': None, 'inputs': {'inputs': {'query': 'Transfer 500 yuan to Zhang San'}}, 'outputs': None, 'error': None, 'invokeId': '3f309daf-b9cb-40ca-b918-4aa738e534fd', 'parentInvokeId': 'b8127943-24af-4f89-8097-18cb3caf2e2f', 'childInvokes': [], 'invokeType': 'workflow', 'name': 'Transfer Service', 'elapsedTime': None, 'metaData': {'class_name': 'Transfer Service', 'type': 'workflow', 'metadata': {'name': 'Transfer Service', 'id': 'transfer_flow', 'version': '1.0', 'description': 'Handle user transfer requests and support transfers to specified accounts'}}}
Output: type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 167805), 'endTime': None, 'inputs': {'query': 'Transfer 500 yuan to Zhang San'}, 'outputs': None, 'error': None, 'invokeId': 'transfer_flow', 'parentInvokeId': None, 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'transfer_flow', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
Output: type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 168923), 'endTime': None, 'inputs': {'query': 'Transfer 500 yuan to Zhang San'}, 'outputs': None, 'error': None, 'invokeId': 'start', 'parentInvokeId': 'transfer_flow', 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'start', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
Output: type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 168923), 'endTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 169086), 'inputs': {'query': 'Transfer 500 yuan to Zhang San'}, 'outputs': {'query': 'Transfer 500 yuan to Zhang San'}, 'error': None, 'invokeId': 'start', 'parentInvokeId': 'transfer_flow', 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'start', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
Output: type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 169679), 'endTime': None, 'inputs': {'query': 'Transfer 500 yuan to Zhang San'}, 'outputs': None, 'error': None, 'invokeId': 'questioner', 'parentInvokeId': 'start', 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'questioner', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
Output: type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 169679), 'endTime': datetime.datetime(2025, 12, 9, 15, 34, 44, 750914), 'inputs': {'query': 'Transfer 500 yuan to Zhang San'}, 'outputs': {'amount': 500}, 'error': None, 'invokeId': 'questioner', 'parentInvokeId': 'start', 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'questioner', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
Output: type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 44, 752452), 'endTime': None, 'inputs': {'amount': 500}, 'outputs': None, 'error': None, 'invokeId': 'end', 'parentInvokeId': 'questioner', 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'end', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
Output: type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 44, 752452), 'endTime': datetime.datetime(2025, 12, 9, 15, 34, 44, 752861), 'inputs': {'amount': 500}, 'outputs': {'responseContent': 'Transfer Service completed: 500'}, 'error': None, 'invokeId': 'end', 'parentInvokeId': 'questioner', 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'end', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
Output: type='end node stream' index=0 payload={'answer': 'Transfer Service completed: 500'}
Output: type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 167805), 'endTime': datetime.datetime(2025, 12, 9, 15, 34, 44, 754020), 'inputs': {'query': 'Transfer 500 yuan to Zhang San'}, 'outputs': {'responseContent': 'Transfer Service completed: 500'}, 'error': None, 'invokeId': 'transfer_flow', 'parentInvokeId': None, 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'transfer_flow', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
Output: type='tracer_agent' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 167499), 'endTime': datetime.datetime(2025, 12, 9, 15, 34, 44, 766519), 'inputs': {'inputs': {'query': 'Transfer 500 yuan to Zhang San'}}, 'outputs': {'outputs': [{'type': 'end node stream', 'index': 0, 'payload': {'answer': 'Transfer Service completed: 500'}}, {'type': 'workflow_final', 'index': 0, 'payload': {'responseContent': 'Transfer Service completed: 500'}}]}, 'error': None, 'invokeId': '3f309daf-b9cb-40ca-b918-4aa738e534fd', 'parentInvokeId': 'b8127943-24af-4f89-8097-18cb3caf2e2f', 'childInvokes': [], 'invokeType': 'workflow', 'name': 'Transfer Service', 'elapsedTime': '3.60s', 'metaData': {'class_name': 'Transfer Service', 'type': 'workflow', 'metadata': {'name': 'Transfer Service', 'id': 'transfer_flow', 'version': '1.0', 'description': 'Handle user transfer requests and support transfers to specified accounts'}}}
Output: type='workflow_final' index=0 payload={'output': WorkflowOutput(result={'responseContent': 'Transfer Service completed: 500'}, state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>), 'result_type': 'answer'}
```

# Complete Sample Code

```python
import os
import asyncio

from openjiuwen.core.agent.message.message import Message
from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
from openjiuwen.core.agent.agent import ControllerAgent
from openjiuwen.core.workflow.base import Workflow
from openjiuwen.core.component.common.configs.model_config import ModelConfig
from openjiuwen.core.component.end_comp import End
from openjiuwen.core.component.questioner_comp import (
    FieldInfo,
    QuestionerComponent,
    QuestionerConfig
)
from openjiuwen.agent.config.base import AgentConfig
from openjiuwen.core.component.start_comp import Start
from openjiuwen.core.utils.llm.base import BaseModelInfo
from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
from openjiuwen.agent_group.hierarchical_group import (
    HierarchicalGroup,
    HierarchicalGroupConfig
)
from openjiuwen.agent_group.hierarchical_group.agents.main_controller import HierarchicalMainController

API_BASE = os.getenv("API_BASE", "your api base")
API_KEY = os.getenv("API_KEY", "your api key")
MODEL_NAME = os.getenv("MODEL_NAME", "")
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")


def _create_model_config() -> ModelConfig:
    """Create model configuration"""
    return ModelConfig(
        model_provider=MODEL_PROVIDER,
        model_info=BaseModelInfo(
            model=MODEL_NAME,
            api_base=API_BASE,
            api_key=API_KEY,
            temperature=0.7,
            top_p=0.9,
            timeout=120,
        ),
    )

def _create_start_component():
    """Create Start component"""
    return Start({
        "inputs": [
            {
                "id": "query",
                "type": "String",
                "required": "true",
                "sourceType": "ref"
            }
        ]
    })


def _build_financial_workflow(
        workflow_id: str,
        workflow_name: str,
        workflow_desc: str,
        field_name: str,
        field_desc: str
) -> Workflow:
    """
    Build a financial business workflow (with an interruption node)

    Args:
        workflow_id: Workflow ID
        workflow_name: Workflow name
        workflow_desc: Workflow description
        field_name: Field name to ask for
        field_desc: Field description to ask for

    Returns:
        Workflow: A workflow containing start -> questioner -> end
    """
    workflow_config = WorkflowConfig(
        metadata=WorkflowMetadata(
            name=workflow_name,
            id=workflow_id,
            version="1.0",
            description=workflow_desc,
        )
    )
    flow = Workflow(workflow_config=workflow_config)

    # Create components
    start = _create_start_component()

    # Create the questioner (interruption node)
    key_fields = [
        FieldInfo(
            field_name=field_name,
            description=field_desc,
            required=True
        ),
    ]
    model_config = _create_model_config()
    questioner_config = QuestionerConfig(
        model=model_config,
        question_content="",
        extract_fields_from_response=True,
        field_names=key_fields,
        with_chat_history=False,
    )
    questioner = QuestionerComponent(questioner_config)

    # End component
    end = End({"responseTemplate": f"{workflow_name} completed: {{{{{field_name}}}}}"})

    # Register components
    flow.set_start_comp("start", start, inputs_schema={"query": "${query}"})
    flow.add_workflow_comp(
        "questioner", questioner, inputs_schema={"query": "${start.query}"}
    )
    flow.set_end_comp(
        "end", end, inputs_schema={field_name: f"${{questioner.{field_name}}}"}
    )

    # Topology: start -> questioner -> end
    flow.add_connection("start", "questioner")
    flow.add_connection("questioner", "end")

    return flow

def _create_workflow_agent(
        agent_id: str,
        description: str,
        workflow: Workflow
) -> WorkflowAgent:
    """Create WorkflowAgent"""
    config = WorkflowAgentConfig(
        id=agent_id,
        version="1.0",
        description=description,
        workflows=[],
        model=_create_model_config(),
    )
    agent = WorkflowAgent(config)
    agent.add_workflows([workflow])
    return agent

# Create financial business workflows
transfer_workflow = _build_financial_workflow(
    workflow_id="transfer_flow",
    workflow_name="Transfer Service",
    workflow_desc="Handle user transfer requests and support transfers to specified accounts",
    field_name="amount",
    field_desc="Transfer amount (numeric)"
)

balance_workflow = _build_financial_workflow(
    workflow_id="balance_flow",
    workflow_name="Balance Inquiry",
    workflow_desc="Query user account balance information",
    field_name="account",
    field_desc="Account number"
)

invest_workflow = _build_financial_workflow(
    workflow_id="invest_flow",
    workflow_name="Wealth Management Service",
    workflow_desc="Provide wealth management product recommendations and purchasing services",
    field_name="product",
    field_desc="Wealth management product name"
)

# Create WorkflowAgent
transfer_agent = _create_workflow_agent(
    agent_id="transfer_agent",
    description="Transfer service, handles users' transfer requests",
    workflow=transfer_workflow
)

balance_agent = _create_workflow_agent(
    agent_id="balance_agent",
    description="Balance inquiry service, queries user account balances",
    workflow=balance_workflow
)

invest_agent = _create_workflow_agent(
    agent_id="invest_agent",
    description="Wealth management service, provides product recommendations and purchasing",
    workflow=invest_workflow
)

# Create HierarchicalGroup
config = HierarchicalGroupConfig(
    group_id="financial_group",
    leader_agent_id="main_controller"
)
hierarchical_group = HierarchicalGroup(config)

# Create the main agent (HierarchicalMainController)
main_config = AgentConfig(
    id="main_controller",
    description="Financial services main controller, recognizes user intent and distributes tasks"
)
main_controller = HierarchicalMainController()
main_agent = ControllerAgent(main_config, controller=main_controller)

# Add all agents to the group
hierarchical_group.add_agent("main_controller", main_agent)
hierarchical_group.add_agent("transfer_agent", transfer_agent)
hierarchical_group.add_agent("balance_agent", balance_agent)
hierarchical_group.add_agent("invest_agent", invest_agent)

async def main():
    message = Message.create_user_message(
        content="Transfer 500 yuan to Zhang San",
        conversation_id="stream_session_test"
    )

    # Streaming invocation
    async for chunk in hierarchical_group.stream(message):
        print(f"Output: {chunk}")

if __name__ == "__main__":
    asyncio.run(main())
```