# Single Agent API

---

## Table of Contents

1. [Create Agent](#1-create-agent)
2. [Update Agent](#2-update-agent)
3. [Delete Agent](#3-delete-agent)
4. [Query Agent List](#4-query-agent-list)
5. [Get Agent Details](#5-get-agent-details)
6. [Invoke Agent Application](#6-invoke-agent-application)
7. [Publish Agent Version](#7-publish-agent-version)
8. [Get Agent Version List](#8-get-agent-version-list)
9. [Import Agent](#9-import-agent)
10. [Export Agent](#10-export-agent)

---

## 1. Create Agent

**Introduction**

This API is used to create a new agent application in the specified project.

**URI**

```
POST /v1/{project_id}/agent-manager/agents?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| Content-Type | Yes | String | Default `application/json` |
| X-Auth-Token | Yes | String | User Token |

**Request Body Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| name | Yes | String | Agent name, 1-64 characters |
| description | Yes | String | Agent description, 1-256 characters |
| type | No | String | Agent type: `agent` (single agent, default) or `controller` (multi-agent) |
| icon | No | String | Agent icon |

**Response Parameters**

Status code: 200

| Parameter | Type | Description |
|------|------|------|
| agent_id | String | Created agent ID |
| project_id | String | Project ID |
| name | String | Agent name |
| type | String | Agent type |
| sub_type | String | Agent sub-type |
| description | String | Agent description |
| icon | String | Agent icon |
| model_config | Object | Model configuration |
| status | String | Agent status |
| creator | String | Creator |
| create_time | Long | Creation time |
| update_time | Long | Update time |

**Status Codes**

| Status Code | Description |
|--------|------|
| 200 | Created successfully |
| 400 | Invalid request parameters |
| 403 | No operation permission |
| 500 | Internal service error |

**Request Example**

```
POST /v1/{project_id}/agent-manager/agents?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "name": "Medical Consultation Assistant",
  "description": "AI-powered medical consultation agent",
  "type": "agent"
}
```

**Response Example**

```json
{
  "agent_id": "7f949107-e394-4897-8816-8c7e92bfada1",
  "project_id": "default",
  "name": "Medical Consultation Assistant",
  "type": "agent",
  "sub_type": "common",
  "description": "AI-powered medical consultation agent",
  "icon": "data:image/svg+xml;base64,...",
  "model_config": {
    "top_p": 1.0,
    "temperature": 0.0,
    "history_size": 20,
    "output_format": "text",
    "max_tokens": 4096
  },
  "status": "draft",
  "creator": "admin",
  "creator_id": "admin",
  "create_time": 1787901076487,
  "update_time": 1787901076487,
  "workflow_switch_enabled": false,
  "scheduling_mode": "ReAct",
  "is_share": 0
}
```

---

## 2. Update Agent

**Introduction**

This API is used to update the configuration of a specified agent application.

**URI**

```
PUT /v1/{project_id}/agent-manager/agents/{agent_id}?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |
| agent_id | Yes | String | Agent ID |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| Content-Type | Yes | String | Default `application/json` |
| X-Auth-Token | Yes | String | User Token |

**Request Body Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| name | No | String | Agent name |
| description | No | String | Agent description |

**Response Parameters**

Status code: 200

Returns the updated full agent information, the response parameters are the same as [Create Agent](#1-create-agent) response parameters.

**Status Codes**

| Status Code | Description |
|--------|------|
| 200 | Updated successfully |
| 400 | Invalid request parameters |
| 403 | No operation permission |
| 404 | Agent does not exist |
| 500 | Internal service error |

**Request Example**

```
PUT /v1/{project_id}/agent-manager/agents/{agent_id}?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "name": "Medical Consultation Assistant-Updated",
  "description": "Updated description"
}
```

---

## 3. Delete Agent

**Introduction**

This API is used to delete a specified agent application.

**URI**

```
DELETE /v1/{project_id}/agent-manager/agents/{agent_id}?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |
| agent_id | Yes | String | Agent ID |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| X-Auth-Token | Yes | String | User Token |

**Response Parameters**

Status code: 200

| Parameter | Type | Description |
|------|------|------|
| id | String | Deleted agent ID |

**Status Codes**

| Status Code | Description |
|--------|------|
| 200 | Deleted successfully |
| 403 | No operation permission |
| 404 | Agent does not exist |
| 500 | Internal service error |

**Request Example**

```
DELETE /v1/{project_id}/agent-manager/agents/{agent_id}?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**Response Example**

```json
{
  "id": "7f949107-e394-4897-8816-8c7e92bfada1"
}
```

---

## 4. Query Agent List

**Introduction**

This API is used to query the list of agents in the current project.

**URI**

```
GET /v1/{project_id}/agent-manager/agents?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID |
| page | No | Integer | Page number, default 1 |
| page_size | No | Integer | Page size, default 10 |
| name | No | String | Fuzzy search by name |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| X-Auth-Token | Yes | String | User Token |

**Response Parameters**

| Parameter | Type | Description |
|------|------|------|
| count | Integer | Total number of agents |
| agent_list | Array of Agent | Agent list |

**Agent**

| Parameter | Type | Description |
|------|------|------|
| agent_id | String | Agent ID |
| project_id | String | Project ID |
| name | String | Agent name |
| type | String | Agent type |
| sub_type | String | Agent sub-type |
| description | String | Agent description |
| icon | String | Agent icon |
| model_config | Object | Model configuration |
| status | String | Agent status |
| url | String | Agent invocation URL |
| creator | String | Creator |
| create_time | Long | Creation time |
| update_time | Long | Update time |

**Request Example**

```
GET /v1/{project_id}/agent-manager/agents?workspace_id={workspace_id}&page=1&page_size=10 HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**Response Example**

```json
{
  "count": 1,
  "agent_list": [
    {
      "agent_id": "7f949107-e394-4897-8816-8c7e92bfada1",
      "project_id": "default",
      "name": "Medical Consultation Assistant",
      "type": "agent",
      "sub_type": "common",
      "description": "AI-powered medical consultation agent",
      "icon": "data:image/svg+xml;base64,...",
      "model_config": {
        "top_p": 1.0,
        "temperature": 0.0,
        "history_size": 20,
        "output_format": "text",
        "max_tokens": 4096
      },
      "status": "draft",
      "url": "/v1/default/agents/7f949107-e394-4897-8816-8c7e92bfada1/conversations/:conversation_id",
      "creator": "admin",
      "creator_id": "admin",
      "create_time": 1787901076487,
      "update_time": 1787901076487
    }
  ]
}
```

---

## 5. Get Agent Details

**Introduction**

This API is used to get detailed information of a specified agent application.

**URI**

```
GET /v1/{project_id}/agent-manager/agents/{agent_id}?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |
| agent_id | Yes | String | Agent ID |

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
| agent_id | String | Agent ID |
| project_id | String | Project ID |
| name | String | Agent name |
| type | String | Agent type |
| sub_type | String | Agent sub-type |
| description | String | Agent description |
| icon | String | Agent icon |
| model_config | Object | Model configuration |
| details | Object | Agent detailed configuration (includes nodes, tools, workflows, mcp_servers, skills, knowledge_repos, etc.) |
| status | String | Agent status |
| creator | String | Creator |
| create_time | Long | Creation time |
| update_time | Long | Update time |

**Request Example**

```
GET /v1/{project_id}/agent-manager/agents/{agent_id}?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**Response Example**

```json
{
  "agent_id": "7c5be653-71b8-48e7-9058-7191ec0f44e8",
  "name": "Medical Consultation Assistant",
  "description": "AI-powered medical consultation agent",
  "status": "published",
  "details": {
    "nodes": [],
    "tools": [],
    "workflows": [],
    "mcp_servers": [],
    "skills": [],
    "knowledge_repos": []
  },
  "create_time": 1735558575017,
  "update_time": 1735558575017
}
```

---

## 6. Invoke Agent Application

**Introduction**

This API is used to run knowledge-based agent applications, supporting both single-agent and multi-agent applications. It supports executing agent logic within a specified project and conversation context. The API supports streaming response mode. The `short_code` is a published version code, not the agent ID. Invoking an unpublished agent returns 404 (error_code: `OpenJiuwen.02201022`).

**Applicable Scenarios**

- Run predefined knowledge-based agent applications in a project
- Supports streaming responses, suitable for scenarios requiring real-time feedback

**URI**

```
POST /v1/{project_id}/agent-manager/agents/chat/{short_code}?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |
| short_code | Yes | String | Published version code (not agent ID) |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| Content-Type | Yes | String | Default `application/json` |
| X-Auth-Token | Yes | String | User Token |
| X-Invoke-Mode | No | String | Run mode: `debug` or `published`, default `published` |
| stream | No | Boolean | Whether to enable streaming invocation. This agent application currently supports only streaming invocation, default `true` |
| X-Request-Id | No | String | Trace ID |

**Request Body Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| query | No | String | User's question |
| inputs | Yes | Map<String,Object> | The user's question |
| user_profile | No | UserProfile object | User profile |
| tool_switch_dict | No | Map<String,Boolean> | Whether plugins are enabled |
| model_deployment_id | No | String | ID of the model configured for the agent |
| enable_history | No | Boolean | Whether to record conversation history, default `true` |
| histories | No | Array of Message | Conversation history passed in |
| files | No | Array of strings | Uploaded file URLs |

**UserProfile**

| Parameter | Required | Type | Description |
|------|------|------|------|
| enable_retrieve | No | Boolean | Whether to read user profile at runtime, default `false` |
| enable_extract | No | Boolean | Whether to build user profile at runtime, default `false` |

**Message**

| Parameter | Required | Type | Description |
|------|------|------|------|
| role | No | String | Conversation role: `user` (user input) or `assistant` (model reply) |
| content | No | String | Conversation content |

**Response Parameters**

Status code: 200

| Parameter | Type | Description |
|------|------|------|
| data | String | Streamed agent message |
| event | String | Data unit type |
| content | Object | Message block content |
| createdTime | Long | Timestamp of the message block response |
| latency | latency object | Latency information |
| plugin | plugin object | Plugin request information |

**event Values**

| Value | Description |
|-----|------|
| start | Start node, indicates the beginning of model invocation for conversation |
| message | Message node, indicates the message returned by the model |
| plugin_start | Plugin invocation request node |
| plugin_end | Plugin invocation response node |
| statistic_data | Execution data node, contains latency information for this invocation |
| summary_response | Message summary node, contains the full response information for this invocation |
| done | Streaming invocation end node |

**latency**

| Parameter | Type | Description |
|------|------|------|
| plugin | Long | Plugin invocation latency |
| model | Long | Model invocation latency |
| overall | Long | Total latency |

**plugin**

| Parameter | Type | Description |
|------|------|------|
| name | String | Plugin name |
| arguments | Object | Plugin input parameters |

**Status Codes**

| Status Code | Description |
|--------|------|
| 200 | Successful response |
| 404 | Agent not published (error_code: `OpenJiuwen.02201022`) |
| 500 | Error response |

**Request Example**

```
POST /v1/{project_id}/agent-manager/agents/chat/{short_code}?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}
stream: true

{
  "query": "Check the status of meeting room A12 from 9:00 to 10:00"
}
```

**Response Example**

```
data:{"event":"start","createdTime":1735558575017}
data:{"event":"message","content":"OK","createdTime":1735558576300}
data:{"event":"message","content":", ","createdTime":1735558576301}
data:{"event":"message","content":"I will","createdTime":1735558576301}
data:{"event":"message","content":"call","createdTime":1735558576302}
data:{"event":"message","content":"query","createdTime":1735558576302}
data:{"event":"statistic_data","latency":{"overall":1.97},"createdTime":1735558576986}
data:{"event":"summary_response","content":"Meeting room A12 is available from 9:00 to 10:00.","role":"assistant","createdTime":1735558576987}
data:{"event":"done","createdTime":1735558577011}
```

---

## 7. Publish Agent Version

**Introduction**

This API is used to publish a new version of a specified agent application, creating version snapshots of DSL and IR files, and recording version information.

**Applicable Scenarios**

- Publish the current configuration of an agent application as a new version
- Create version snapshots for agent applications for subsequent rollback or management

**URI**

```
POST /v1/{project_id}/agent-manager/agents/{agent_id}/versions?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |
| agent_id | Yes | String | Agent ID, up to 64 characters, supports only letters, numbers, underscores, and hyphens |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID, 1 to 64 characters |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| Content-Type | Yes | String | Default `application/json` |
| X-Auth-Token | Yes | String | User Token |

**Request Body Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| version_name | Yes | String | Version name, up to 64 characters |
| version_note | No | String | Version note, up to 1024 characters |

**Response Body Parameters**

Status code: 200

This API has no response body for a successful response.

Status code: 400 / 403 / 404 / 500

| Parameter | Type | Description |
|------|------|------|
| error_code | String | Error code |
| error_msg | String | Error message |
| error_reason | String | Error reason |
| error_suggestion | String | Error handling suggestion |
| details | Array of ErrorDetail | Detailed error information returned by the API |

**Status Codes**

| Status Code | Description |
|--------|------|
| 200 | Agent version created successfully |
| 400 | Request error, such as invalid parameters or version name already exists |
| 403 | No operation permission |
| 404 | Resource not found, such as agent does not exist |
| 500 | Internal service error |

**Request Example**

```
POST /v1/{project_id}/agent-manager/agents/{agent_id}/versions?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "version_name": "v1.0.0",
  "version_note": "Initial release version"
}
```

**Response Example**

Successful response (status code: 200):

No response body.

Error response (status code: 400):

```json
{
  "error_msg": "The version name already existed."
}
```

---

## 8. Get Agent Version List

**Introduction**

This API is used to get the version list of a specified agent application.

**URI**

```
GET /v1/{project_id}/agent-manager/agents/{agent_id}/versions?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |
| agent_id | Yes | String | Agent ID |

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
| count | Integer | Total number of versions |
| version_list | Array of Version | Version list |

**Version**

| Parameter | Type | Description |
|------|------|------|
| version_id | String | Version ID |
| version_name | String | Version name |
| version_note | String | Version note |
| status | String | Version status (e.g. `normal`) |
| release_time | Long | Release time |
| creator | String | Creator |
| creator_id | String | Creator ID |

**Request Example**

```
GET /v1/{project_id}/agent-manager/agents/{agent_id}/versions?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**Response Example**

```json
{
  "count": 1,
  "version_list": [
    {
      "version_id": "1787901244768",
      "version_name": "v1.0.0",
      "version_note": "Initial release version",
      "status": "normal",
      "release_time": 1787901244802,
      "creator": "admin",
      "creator_id": "admin"
    }
  ]
}
```

---

## 9. Import Agent

**Introduction**

This API is used to import an exported agent configuration file into the current project to quickly create an agent application.

**URI**

```
POST /v1/{project_id}/agent-manager/agents/import?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID |
| import_agents | No | String | Whether to import agents, set to `true` to enable |
| import_tools | No | String | Whether to import tools, set to `true` to enable |
| import_workflows | No | String | Whether to import workflows, set to `true` to enable |
| mode | No | String | Import mode: `STRICT` (strict mode) / `SPACIOUS` (lenient mode), default `STRICT` |

> **Note**: It is recommended to pass `import_agents=true`, `import_tools=true`, `import_workflows=true` together, otherwise a 500 internal error may occur.

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| Content-Type | Yes | String | `multipart/form-data` |
| X-Auth-Token | Yes | String | User Token |

**Request Body Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| file | Yes | File | Exported agent configuration file in `.jsonl` format (multipart upload) |

**Response Parameters**

| Parameter | Type | Description |
|------|------|------|
| succeed_len | Integer | Number of successfully imported items |
| count | Integer | Total count |
| succeed_ids | Array of String | List of successfully imported IDs |
| failed_len | Integer | Number of failed items |
| imported_len | Integer | Number of newly imported items |
| updated_len | Integer | Number of updated items |
| skipped_len | Integer | Number of skipped items |
| failed_ids | Array of String | List of failed IDs |
| import_list | Array | Import detail list |

**Request Example**

```
POST /v1/{project_id}/agent-manager/agents/import?workspace_id={workspace_id}&import_agents=true&import_tools=true&import_workflows=true&mode=SPACIOUS HTTP/1.1
Host: api.example.com
Content-Type: multipart/form-data
X-Auth-Token: {token}

file=@agent_config.jsonl
```

**Response Example**

```json
{
  "succeed_len": 0,
  "count": 0,
  "succeed_ids": [],
  "failed_len": 0,
  "imported_len": 0,
  "updated_len": 0,
  "skipped_len": 0,
  "failed_ids": [],
  "import_list": []
}
```

---

## 10. Export Agent

**Introduction**

This API is used to export the configuration file of a specified agent application for migration or backup.

**URI**

```
POST /v1/{project_id}/agent-manager/agents/export?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| Content-Type | Yes | String | Default `application/json` |
| X-Auth-Token | Yes | String | User Token |

**Request Body Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| agent_ids | Yes | Array of String | List of agent IDs to export |

**Response Parameters**

This API returns a binary file stream (`Content-Type: application/octet-stream`), with the filename specified via the `Content-Disposition` header (e.g., `agents.jsonl`).

**Request Example**

```
POST /v1/{project_id}/agent-manager/agents/export?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "agent_ids": ["7c5be653-71b8-48e7-9058-7191ec0f44e8"]
}
```

**Response Example**

```
HTTP/1.1 200 OK
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="agents.jsonl"

<binary file content>
```

---
