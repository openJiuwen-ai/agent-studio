# REST API Reference Guide

## Table of Contents

1. [API Overview](#1-api-overview)
2. [Request Format](#2-request-format)
3. [Response Format](#3-response-format)
4. [Example](#4-example)
5. [Appendix](#5-appendix)

## 1. API Overview

OpenJiuwen's APIs are divided into management-plane (Manager) and runtime (Runtime) components, each with its own OpenAPI definition file as shown below. You can open the YAML files using any tool that supports the OpenAPI 3.1 specification.

### Manager API

Covers the complete APIs for agent management, workflow management, knowledge base management, plugin management, MCP service management, workspace management, prompt engineering, model management, and more.

> **[Manager API Definition →](../../api/studio-manager/openapi.yaml)**

| Module | Controller | Description |
|--------|-----------|-------------|
| Single Agent | agent-management-api-controller | Agent CRUD, invocation, version management, import/export |
| Workflow | workflow-management-api-controller, workflow-runtime-api-controller | Workflow CRUD, invocation, version management, async task management |
| Multi-Agent | complex-intent-management-api-controller | Multi-agent conversation execution records query |
| Plugin/Tool | plugin-api-controller, tool-management-api-controller | Plugin/tool management |
| MCP Service | mcp-server-manager-api-controller, mcp-service-manager-api-controller | MCP service management |
| Knowledge Base | knowledge-repo-management-api-controller, knowledge-file-management-api-controller, knowledge-faq-management-api-controller | Knowledge base management, file management, FAQ management |
| Workspace | workspace-api-controller, work-space-member-api-controller | Workspace management, member management |
| Prompt Engineering | prompt-engineer-api-controller, prompt-library-api-controller | Prompt optimization, management |
| Model Service | model-service-mgmt-api-controller, provider-mgmt-api-controller | Model service management, provider management |
| Async Tasks | task-management-api-controller | Async task management |
| Others | auth-controller, health-api-controller, release-management-api-controller, etc. | Authentication, health check, release management, etc. |

### Runtime API

Covers runtime APIs for conversation execution, inference, knowledge base retrieval, and more.

> **[Runtime API Definition →](../../api/studio-runtime/openapi.yaml)**

| Module | API Tag | Description |
|--------|---------|-------------|
| App Execution | app_run | Workflow conversation, agent conversation (single/multi-agent), node debug execution |
| Web Invocation | web_run | Invoke published workflows/agents via short_code |
| IR Execution | execution_app | Direct IR execution, component debug, health check |
| Conversation Variables | conversation_variable | Read/write conversation global variables |
| Memory Management | memory-internal | Memory repo create, delete, search |
| Knowledge Base | openjiuwen_kb | Knowledge base creation, document upload, search, deletion |
| Internal Tools | inner_tools | File parsing, document generation |
| Release Management | release | Application release info creation and deletion |

## 2. Request Format

### 2.1 Request URI

A request URI consists of the following parts:

```
{URI-scheme}://{Endpoint}/{resource-path}?{query-string}
```

| Component | Description |
|-----------|-------------|
| URI-scheme | Protocol, supports HTTP and HTTPS, defaults to HTTP |
| Endpoint | Service address in IP:port format. See [5.3 Obtain Endpoint](#53-obtain-endpoint) |
| resource-path | Resource path, i.e., the specific path of each API, available in the [Manager API Definition](../../api/studio-manager/openapi.yaml) or [Runtime API Definition](../../api/studio-runtime/openapi.yaml) |
| query-string | Query parameters (optional), joined by `&`, e.g., `version=latest&workspace_id=xxx` |

> **Note**:
> - `project_id`: Required path parameter in all Manager and Runtime API paths. See [5.4 Obtain Project ID](#54-obtain-project-id).
> - `workspace_id`: Required query parameter for some Manager APIs; optional for Runtime APIs. See [5.5 Obtain Workspace ID](#55-obtain-workspace-id).

### 2.2 Request Methods

| Method | Description |
|--------|-------------|
| GET | Requests the server to return a specified resource |
| POST | Requests the server to create a new resource or perform a special operation |
| PUT | Requests the server to update a specified resource |
| DELETE | Requests the server to delete a specified resource |

### 2.3 Common Request Headers

The following are common headers for OpenJiuwen APIs:

| Header | Required | Description |
|--------|----------|-------------|
| Content-Type | Yes | Message body type, default `application/json` |
| X-Auth-Token | Yes | User token for authentication. See [5.6 Obtain Token](#56-obtain-token) |
| stream | No | Whether to use streaming response, applies to Runtime conversation APIs only. Defaults to streaming; set to `false` to return non-streaming JSON response |

## 3. Response Format

### 3.1 Success Response

When a request succeeds, the HTTP status code is `200` (or `201` for creation operations), and the response body is in JSON format. The specific response structure for each API is defined in the [Manager API Definition](../../api/studio-manager/openapi.yaml) or [Runtime API Definition](../../api/studio-runtime/openapi.yaml).

### 3.2 Streaming Response

When the `stream` header is not set or set to `true`, the API returns the response in SSE (Server-Sent Events) format. The response is pushed in chunks as text lines prefixed with `data:`, each containing a JSON fragment. This is suitable for scenarios requiring real-time output, such as conversations and inference.

Format example:

```
data: {"event": "message", "data": {"answer": "Hello"}, "createdTime": 1719532800000, "executionId": "xxx", "isStructMessage": false}

data: {"event": "done", "data": {}, "createdTime": 1719532800001, "executionId": "xxx", "isStructMessage": false}
```

| Field | Description |
|-------|-------------|
| event | Event type, e.g., `start` (begin), `message` (content reply), `done` (end), `error` (error) |
| data | Event data, content depends on the event type |
| createdTime | Creation timestamp (milliseconds) |
| executionId | Execution ID |
| isStructMessage | Whether it is a structured message, defaults to `false` |
| index | Node index (optional) |

### 3.3 Error Response

When a request fails, the HTTP status code is `4xx` or `5xx`, and the response body contains error information:

```json
{
  "error_code": "openjiuwen.03001001",
  "error_msg": "Input parameter is invalid.",
  "error_reason": "name must not be empty",
  "error_suggestion": "Please provide the name parameter",
  "details": [
    {
      "error_code": "...",
      "error_msg": "..."
    }
  ]
}
```

| Field | Required | Description |
|-------|----------|-------------|
| error_code | Yes | Error code for precisely identifying the error type |
| error_msg | Yes | Error message, briefly describing the error reason |
| error_reason | No | Detailed error reason |
| error_suggestion | No | Suggested fix |
| details | No | Error detail list, each element contains `error_code` and `error_msg` (Manager only) |

For specific error codes and recommended actions, see [5.2 Error Codes](#52-error-codes).

## 4. Example

Using the workspace initialization endpoint as an example, showing a complete request and response:

Request:

```bash
curl -X POST "https://{manager_host}:{manager_port}/v1/0/agent-manager/workspace/init" \
  -H "X-Auth-Token: testUser|0"
```

Response:

```json
{
  "count": 1,
  "workspaceList": [
    {
      "id": "d12a210ab39947909f616498bc219013",
      "name": "个人空间",
      "projectId": "0",
      "icon": "...",
      "description": "个人空间",
      "tenantId": "0",
      "type": "PERSON",
      "status": "ENABLE",
      "creator": "testUser",
      "creatorId": "testUser",
      "createdOn": 1785134755000,
      "updater": "testUser",
      "updaterId": "testUser",
      "updatedOn": 1785134755000,
      "role": "OWNER"
    }
  ]
}
```

## 5. Appendix

### 5.1 Common Status Codes

The following table lists HTTP status codes that OpenJiuwen APIs may return:

| Status Code | Description |
|-------------|-------------|
| 200 | Request successful |
| 201 | Resource created successfully |
| 400 | Invalid request parameters or format error |
| 401 | Authentication information incorrect or missing |
| 403 | Access denied (insufficient permissions or quota exceeded) |
| 404 | Requested resource does not exist |
| 422 | Request format correct, but contains semantic errors |
| 429 | Request frequency exceeds limit |
| 500 | Internal server error |
| 502 | Bad gateway |
| 503 | Service temporarily unavailable |
| 504 | Gateway timeout |

### 5.2 Error Codes

#### Agent

| Status Code | Error Code | Error Message | Description | Action |
|-------------|-----------|---------------|-------------|--------|
| 403 | openjiuwen.02101016 | Insufficient execution permissions for Agent | Current user does not have permission to run this agent application | Confirm user has execution permission |
| 400 | openjiuwen.02101032 | Current Agent version does not exist | The specified agent version does not exist | Confirm agent ID and version |
| 403 | openjiuwen.02001017 | API call count for Agent exceeds quota | Agent API call quota exhausted | Upgrade plan |
| 404 | openjiuwen.02101007 | Agent does not exist | Agent application not found or deleted | Confirm application exists |

#### Workflow

| Status Code | Error Code | Error Message | Description | Action |
|-------------|-----------|---------------|-------------|--------|
| 400 | openjiuwen.02201005 | Workflow information validation failed | Workflow validation failed | Check workflow configuration |
| 403 | openjiuwen.02201020 | Insufficient workflow execution permissions | Current projectId does not match workflow's projectId | Ensure projectId matches |
| 404 | openjiuwen.02201004 | Workflow does not exist | Workflow not found or deleted | Confirm workflow exists |
| 500 | openjiuwen.02201001 | Workflow import failed | Workflow import failed | Check import file format |
| 500 | openjiuwen.02201003 | Workflow node execution failed | Workflow node execution exception | Check node configuration |

#### Knowledge Base

| Status Code | Error Code | Error Message | Description | Action |
|-------------|-----------|---------------|-------------|--------|
| 400 | openjiuwen.03002106 | Operation failed | External knowledge base does not support file download | Check third-party connection |
| 400 | openjiuwen.03003039 | Operation failed | Image not found or expired | Retry later |
| 403 | openjiuwen.03001021 | Operation failed | Downloaded file is empty | Check and retry |
| 404 | openjiuwen.03001003 | resource not exist | Resource does not exist | Contact technical support |
| 404 | openjiuwen.03002010 | Can not retrieve in knowledge base | Knowledge has been deleted or disabled | Check knowledge status |
| 500 | openjiuwen.03002019 | Operation failed | File not found or expired | Check and retry |
| 500 | openjiuwen.03002104 | Query third party knowledgeBases error | Third-party knowledge base connection error | Check connection info and retry |

#### General

| Status Code | Error Code | Error Message | Description | Action |
|-------------|-----------|---------------|-------------|--------|
| 400 | openjiuwen.03001001 | Input parameter is invalid | Input parameter is invalid | Check input parameters |
| 500 | openjiuwen.03000000 | System internal error | System internal error | Contact technical support |

### 5.3 Obtain Endpoint

An endpoint is the service address for calling APIs, in IP:port format. OpenJiuwen consists of two services:

| Service | Description | How to Obtain |
|---------|-------------|---------------|
| Manager | Management-plane service for agent/workflow management, authentication, etc. | Manager service address configured during platform deployment |
| Runtime | Runtime service for conversation execution, inference, etc. | Obtained from the "View API" page of a published application in the console |

### 5.4 Obtain Project ID

Get the project ID from the console:

1. Go to the OpenJiuwen agent development platform.
2. In the left navigation, select "Development Center > Agent Management", then select "Single Agent", "Workflow", or "Multi-Agent".
3. Click on a published application card to enter the editing page, then select "Channel Management".
4. In the "Invocation Method" area, click "View API".
5. On the "API Details" page, view the project_id in the "Request Structure" area. The string after v1 is the project_id.

![Get Project ID](../../images/getProjectId.png)

### 5.5 Obtain Workspace ID

#### Method 1: Via API

Initialize a personal workspace. This endpoint automatically creates a personal workspace if it does not exist and returns the workspace list, which includes the workspace ID (`id` field):

```
POST /v1/{project_id}/agent-manager/workspace/init
```

Response example:

```json
{
  "count": 1,
  "workspaceList": [
    {
      "id": "xxx",
      "name": "Personal Workspace"
    }
  ]
}
```

#### Method 2: From Console

1. Go to the OpenJiuwen agent development platform.
2. Open browser developer tools (press F12), switch to the "Network" tab.
3. Perform any action on the page (e.g., switch to "Personal Workspace"), then look for `workspace_id=xxx` in the Network requests, where xxx is the workspace ID.

### 5.6 Obtain Token

The token is used for API request authentication, in the format `userId|projectId`. In the default open-source configuration, the default user is `testUser` and the default project is `0`, so you can directly use `testUser|0` as the token:

```
X-Auth-Token: testUser|0
```

Alternatively, call `GET http://{manager_host}:{manager_port}/auth/token?user_id={user_id}&project_id={project_id}` to obtain a token (this endpoint requires direct access to the Manager service port, e.g., 31111).
