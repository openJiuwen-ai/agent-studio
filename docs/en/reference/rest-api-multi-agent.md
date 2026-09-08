# Multi-Agent API

---

## Table of Contents

1. [Query Conversation Execution Records](#1-query-conversation-execution-records)
2. [Query Multi-Agent Conversation Details](#2-query-multi-agent-conversation-details)

---

## 1. Query Conversation Execution Records

**Introduction**

This API is used to query the execution records of a specified multi-agent application conversation, returning summary information of all execution steps in the conversation.

**Applicable Scenarios**

- View the complete execution chain of a multi-agent conversation
- Troubleshoot execution issues in multi-agent conversations
- Get the invocation details of sub-agents in a conversation

**URI**

```
GET /v1/{project_id}/agent-manager/controller/{agent_id}/conversations/{conversation_id}/executions
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |
| agent_id | Yes | String | Multi-agent application ID |
| conversation_id | Yes | String | Conversation ID |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| X-Auth-Token | Yes | String | User Token |

**Response Parameters**

| Parameter | Type | Description |
|------|------|------|
| count | Integer | Total number of execution records |
| executions | Array of Execution | Execution record list |

**Execution**

| Parameter | Type | Description |
|------|------|------|
| execution_id | String | Execution record ID |
| agent_id | String | Sub-agent ID |
| agent_name | String | Sub-agent name |
| status | String | Execution status |
| input | String | Input content |
| output | String | Output content |
| start_time | Long | Start time |
| end_time | Long | End time |
| duration | Long | Execution duration (ms) |

**Request Example**

```
GET /v1/{project_id}/agent-manager/controller/{agent_id}/conversations/{conversation_id}/executions?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**Response Example**

```json
{
  "count": 2,
  "executions": [
    {
      "execution_id": "exec_001",
      "agent_id": "sub_agent_01",
      "agent_name": "Search Assistant",
      "status": "success",
      "input": "Search meeting room A12 status",
      "output": "Meeting room A12 is available from 9:00-10:00",
      "start_time": 1735558575017,
      "end_time": 1735558576986,
      "duration": 1969
    },
    {
      "execution_id": "exec_002",
      "agent_id": "sub_agent_02",
      "agent_name": "Reply Assistant",
      "status": "success",
      "input": "Reply to user based on search results",
      "output": "Meeting room A12 is available from 9:00 to 10:00.",
      "start_time": 1735558576986,
      "end_time": 1735558577011,
      "duration": 25
    }
  ]
}
```

---

## 2. Query Multi-Agent Conversation Details

**Introduction**

This API is used to query detailed information of a specified execution record in a multi-agent application, including sub-agent invocation process, intermediate results, etc.

**Applicable Scenarios**

- Deep analysis of a specific execution step in a multi-agent
- Troubleshoot specific issues in the multi-agent execution chain

**URI**

```
GET /v1/{project_id}/agent-manager/controller/{agent_id}/executions/{execution_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |
| agent_id | Yes | String | Multi-agent application ID |
| execution_id | Yes | String | Execution record ID |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| X-Auth-Token | Yes | String | User Token |

**Response Parameters**

| Parameter | Type | Description |
|------|------|------|
| execution_id | String | Execution record ID |
| agent_id | String | Sub-agent ID |
| agent_name | String | Sub-agent name |
| status | String | Execution status |
| input | String | Input content |
| output | String | Output content |
| steps | Array of Step | Execution step details |
| start_time | Long | Start time |
| end_time | Long | End time |
| duration | Long | Execution duration (ms) |

**Step**

| Parameter | Type | Description |
|------|------|------|
| step_id | String | Step ID |
| step_name | String | Step name |
| step_type | String | Step type |
| input | Object | Step input |
| output | Object | Step output |
| status | String | Step status |
| start_time | Long | Start time |
| end_time | Long | End time |

**Request Example**

```
GET /v1/{project_id}/agent-manager/controller/{agent_id}/executions/{execution_id}?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**Response Example**

```json
{
  "execution_id": "exec_001",
  "agent_id": "sub_agent_01",
  "agent_name": "Search Assistant",
  "status": "success",
  "input": "Search meeting room A12 status",
  "output": "Meeting room A12 is available from 9:00-10:00",
  "steps": [
    {
      "step_id": "step_01",
      "step_name": "Intent Recognition",
      "step_type": "intent",
      "input": {"query": "Search meeting room A12 status"},
      "output": {"intent": "search_meeting_room"},
      "status": "success",
      "start_time": 1735558575017,
      "end_time": 1735558575500
    },
    {
      "step_id": "step_02",
      "step_name": "Plugin Invocation",
      "step_type": "plugin",
      "input": {"intent": "search_meeting_room", "params": {"room": "A12", "time": "9:00-10:00"}},
      "output": {"status": "available"},
      "status": "success",
      "start_time": 1735558575500,
      "end_time": 1735558576986
    }
  ],
  "start_time": 1735558575017,
  "end_time": 1735558576986,
  "duration": 1969
}
```

---
