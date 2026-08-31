# API Specification

---

## Table of Contents

1. [Before You Start](#1-before-you-start)
2. [API Overview](#2-api-overview)
3. [How to Call APIs](#3-how-to-call-apis)
4. [Application Examples](#4-application-examples)
5. [Appendix](#5-appendix)

---

## 1. Before You Start

Welcome to OpenJiuwen service. OpenJiuwen is a one-stop enterprise-level agent building platform that includes functional modules such as application management, component library, knowledge base, prompt development, configuration management, and model integration and testing. It covers eight aspects: experience design, code development, application runtime, asset management, data processing, testing and publishing, operations monitoring, and security assurance, providing enterprise users with an out-of-the-box large model application development toolchain.

You can use the APIs provided in this document to perform operations on OpenJiuwen, such as invoking applications and invoking workflows.

### Endpoint

An endpoint is the request address for calling APIs. Endpoints vary by region. To obtain the endpoint:

1. Go to the OpenJiuwen agent development platform
2. In the left navigation, select "Development Center > Agent Management", then select "Single Agent", "Workflow", or "Multi-Agent"
3. Click on a published single agent application, workflow application, or multi-agent application card to enter the editing page, then select "Channel Management"
4. In the "Invocation Method" area, click "View API"
5. On the "API Details" page, view the URL address. The IP address:port number is the API request address

---

## 2. API Overview

Organized by front-end second-level menu functional modules. Click the corresponding link for API details of each module:

### Development Center

| Module | API Count | Description | Documentation Link |
|------|----------|------|----------|
| Single Agent | 10 | Agent CRUD, invocation, version management, import/export | [View Details](rest-api-single-agent.md) |
| Workflow | 10 | Workflow CRUD, invocation, version management, import/export, parse import file | [View Details](rest-api-workflow.md) |
| Multi-Agent | 2 | Multi-agent conversation execution records query, conversation details query | [View Details](rest-api-multi-agent.md) |

### Component Library

| Module | API Count | Description | Documentation Link |
|------|----------|------|----------|
| Tool | 4 | Tool list query, export, update, delete | [View Details](rest-api-plugin.md) |
| MCP Service | 5 | MCP service list query, summary statistics, deployment, delete, modify | [View Details](rest-api-mcp.md) |
| Knowledge Base | 3 | Knowledge base retrieval, image retrieval, file download | [View Details](rest-api-knowledge-base.md) |

### Others

| Module | API Count | Description | Documentation Link |
|------|----------|------|----------|
| Workspace | 16 | Workspace CRUD, query, member management, role management, resource sharing | [View Details](rest-api-workspace.md) |
| File Management | 1 | File upload | [View Details](rest-api-file.md) |

---

## 3. How to Call APIs

### 3.1 Constructing a Request

#### Request URI

A request URI consists of the following parts:
```
{URI-scheme}://{Endpoint}/{resource-path}?{query-string}
```

- **URI-scheme**: Indicates the protocol used for transmitting requests. Supports both HTTP and HTTPS
- **Endpoint**: Specifies the server domain name or IP that hosts the REST service endpoint, e.g., `http://100.85.147.133`
- **resource-path**: The resource path, i.e., the API access path
- **query-string**: Query parameters, which are optional

#### Request Methods

| Method | Description |
|------|------|
| GET | Requests the server to return a specified resource |
| PUT | Requests the server to update a specified resource |
| POST | Requests the server to create a new resource or perform a special operation |
| DELETE | Requests the server to delete a specified resource |
| HEAD | Requests the resource header from the server |
| PATCH | Requests the server to partially update a resource |

#### Request Headers

Common headers need to be added to the request:

| Header | Required | Description |
|--------|------|------|
| Content-Type | Yes | The type of the message body. Default value is `application/json` |
| X-Auth-Token | Yes | User token for authentication |

### 3.2 Authentication

#### Obtaining a Token

Call the following endpoint to obtain a user token:

```
GET http://{manager_host}:{manager_port}/auth/token?user_id={user_id}&project_id={project_id}
```

> **Note**: The `/auth/token` endpoint is provided directly by the Manager service and must be accessed directly via the Manager service port (e.g., 31111), not through the Nginx proxy.

**Request Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| user_id | Yes | String | User ID, e.g., `admin` |
| project_id | Yes | String | Project ID, e.g., `default` |

**Response Example**

```json
{
  "auth_token": "admin|default"
}
```

#### Using the Token

In subsequent API requests, pass the obtained token value via the `X-Auth-Token` request header:

```
X-Auth-Token: admin|default
```

The token format is `userId|projectId`.

#### Workspace ID

Most APIs require `workspace_id` as a query parameter. You can obtain the workspace ID by:

1. Call `POST /v1/{project_id}/agent-manager/workspace/init` to initialize a personal workspace
2. Call `GET /v1/{project_id}/agent-manager/workspace?workspace_id={workspace_id}` to query the workspace list

### 3.3 Response

#### Status Codes

A status code is a numeric code ranging from 1xx to 5xx that indicates the status of the request response

#### Response Body

When an API call fails, an error code and error message are returned:

```json
{
  "error_msg": "Request body is invalid."
}
```

---

## 4. Application Examples

### 4.1 Invoke Workflow Application Example

**Operation Scenario**

This API is used to run scenario-based applications, supporting the execution of workflow logic within a specified project, workflow, and conversation context.

**Prerequisites**

You need to plan the region information of OpenJiuwen and determine the API Endpoint based on the region.

**Invoke Workflow**

```
POST https://1.2.3.4/v1/12345/agent-manager/workflows/chat/{short_code}/conversations/{conversation_id}?workspace_id={workspace_id}
```

**Request Header**

```
Content-Type: application/json
X-Auth-Token: {token}
stream: true
```

**Request Body**

```json
{
  "inputs": {
    "query": "Hello"
  },
  "plugin_configs": [
    {
      "plugin_id": "xxxxxxxxx",
      "config": {
        "key": "value"
      }
    }
  ]
}
```

**Parameter Description**

- `endpoint`: Endpoint
- `project_id`: Current project ID
- `short_code`: Published version code
- `conversation_id`: Conversation ID, the unique identifier for each conversation, string length 1 to 64 characters, supports English letters, numbers, hyphens, and underscores

---

### 4.2 Invoke Agent Application Example

**Operation Scenario**

This API is used to run knowledge-based agent applications (single agent application, multi-agent application).

**Prerequisites**

You need to plan the region information of OpenJiuwen and determine the API Endpoint based on the region.

**Invoke Application**

```
POST https://1.2.3.4/v1/074cabeea7800f622f0ec010bffa6c59/agent-manager/agents/chat/{short_code}/conversations/{conversation_id}?workspace_id={workspace_id}
```

**Request Header**

```
Content-Type: application/json
X-Auth-Token: {token}
stream: true
```

**Request Body**

```json
{
  "inputs": {
    "query": "Check the status of meeting room A12 from 9:00 to 10:00"
  }
}
```

**Parameter Description**

- `endpoint`: Endpoint
- `project_id`: Current project ID
- `short_code`: Published version code
- `conversation_id`: Conversation ID

---

## 5. Appendix

### 5.1 Status Codes

| Status Code | Code | Description |
|--------|------|------|
| 100 | Continue | Continue request |
| 101 | Switching Protocols | Switching protocol |
| 200 | OK | Server has successfully processed the request |
| 201 | Created | Creation request fully successful |
| 202 | Accepted | Request accepted but not yet processed |
| 203 | Non-Authoritative Information | Non-authoritative information, request successful |
| 204 | No Content | Request fully successful, HTTP response contains no response body |
| 205 | Reset Content | Reset content, server processed successfully |
| 206 | Partial Content | Server successfully processed a partial GET request |
| 300 | Multiple Choices | Multiple choices |
| 301 | Moved Permanently | Resource permanently moved |
| 302 | Found | Resource temporarily moved |
| 303 | See Other | See other address |
| 304 | Not Modified | Requested resource not modified |
| 305 | Use Proxy | Requested resource must be accessed through a proxy |
| 400 | Bad Request | Invalid request |
| 401 | Unauthorized | Authentication information incorrect or invalid |
| 402 | Payment Required | Reserved request |
| 403 | Forbidden | Request denied access |
| 404 | Not Found | Requested resource does not exist |
| 405 | Method Not Allowed | Request contains a method not supported by the resource |
| 406 | Not Acceptable | Server cannot fulfill the request based on the client's content characteristics |
| 407 | Proxy Authentication Required | Request requires proxy authentication |
| 408 | Request Time-out | Server timed out waiting for the request |
| 409 | Conflict | Server encountered a conflict while processing the request |
| 410 | Gone | Requested resource no longer exists |
| 411 | Length Required | Server cannot process the request without Content-Length |
| 412 | Precondition Failed | Precondition not met |
| 413 | Request Entity Too Large | Request entity too large, server cannot process |
| 414 | Request-URI Too Large | Request URL too long |
| 415 | Unsupported Media Type | Server cannot process the media format attached to the request |
| 416 | Requested range not satisfiable | Client requested an invalid range |
| 417 | Expectation Failed | Server cannot fulfill the Expect request header |
| 422 | Unprocessable Entity | Request format is correct but contains semantic errors, cannot be processed |
| 429 | Too Many Requests | Request exceeded the client's access frequency limit |
| 500 | Internal Server Error | Internal server error |
| 501 | Not Implemented | Server does not support the requested functionality |
| 502 | Bad Gateway | Server acting as a gateway or proxy received an invalid request from the remote server |
| 503 | Service Unavailable | Requested service unavailable |
| 504 | Server Timeout | Request could not be completed within the given time |
| 505 | HTTP Version not supported | Server does not support the HTTP protocol version of the request |

---

### 5.2 Error Codes

| Status Code | Error Code | Error Message | Description | Action |
|--------|--------|----------|------|----------|
| 400 | OpenJiuwen.03001001 | Input parameter is invalid | Input parameter is invalid | Please check if the input parameters are correct |
| 400 | OpenJiuwen.03002106 | Operation failed | External knowledge base does not support file download | Third-party knowledge base connection does not exist |
| 400 | OpenJiuwen.03003039 | Operation failed | Image not found or expired | Please retry later |
| 403 | OpenJiuwen.03001021 | Operation failed | Downloaded file is empty | Please check and retry |
| 404 | OpenJiuwen.03001003 | Resource does not exist | Resource does not exist | Please contact technical support |
| 404 | OpenJiuwen.03002010 | Cannot retrieve from knowledge base | This knowledge has been deleted or disabled | Check the status of this knowledge |
| 500 | OpenJiuwen.03000000 | System internal error | System internal error | Please contact technical support |
| 500 | OpenJiuwen.03002019 | Operation failed | File not found or expired | Check and retry |
| 500 | OpenJiuwen.03002104 | Query third-party knowledge bases error | Third-party knowledge base connection information error | Check connection information and retry |
| 200 | OpenJiuwen.02101016 | Insufficient execution permissions for Agent | Current user does not have permission to run this single agent application in the specified project | Confirm that the current user has execution permission for this single agent application in the target project |
| 200 | OpenJiuwen.100002 | Validation failed | Input parameter format is incorrect or required parameters are missing | Check if the request parameters conform to the API specification |
| 400 | OpenJiuwen.02101032 | Current Agent version does not exist | The Agent or its version specified in the request does not exist in the system, possibly deleted or not correctly published | Confirm that the Agent ID and version information are correct, and ensure the Agent has been successfully published and is available |
| 403 | OpenJiuwen.02001017 | API call count for Agent exceeds quota | Agent API call quota has been exhausted | Please upgrade the plan |
| 403 | OpenJiuwen.02201020 | Insufficient workflow execution permissions | The projectId of the current execution request does not match the projectId of the workflow | Ensure that the projectId in the current workspace matches the projectId of the workflow |
| 404 | OpenJiuwen.02101007 | Agent does not exist | The requested agent application was not found or has been deleted | Confirm whether the application exists |
| 500 | OpenJiuwen.02201004 | Workflow or workflow version does not exist | The workflow ID in the request does not exist in the current project and workspace | Confirm the workflow ID is correct |
| 400 | OpenJiuwen.02201001 | Version name already existed | Version name already exists | Please use a different version name |
| 400 | OpenJiuwen.02201002 | Release version size exceed limit | Number of published versions exceeds the limit | Please delete unnecessary old versions and retry |
| 400 | OpenJiuwen.02201003 | Workflow information validation failed | Workflow information validation failed | Please check if the workflow configuration is complete and valid |
| 500 | OpenJiuwen.02201005 | Workflow does not exist | The requested workflow was not found or has been deleted | Confirm whether the workflow exists |

---

### 5.3 Get Project ID

Get the project ID from the console:

1. Go to the OpenJiuwen agent development platform
2. In the left navigation, select "Development Center > Agent Management", then select "Single Agent", "Workflow", or "Multi-Agent"
3. Click on a published single agent application, workflow application, or multi-agent application card to enter the editing page, then select "Channel Management"
4. In the "Invocation Method" area, click "View API"
5. On the "API Details" page, view the project_id in the "Request Structure" area. The string after v1 is the project_id
![img.png](../../images/getProjectId.png)
---

### 5.4 Get Workspace ID

When calling APIs, some URLs require a workspace ID. To obtain it:

1. Go to the OpenJiuwen agent development platform
2. Open F12, select "Network", click on any page, such as "Personal Space"
3. You can see `workspace_id=xxx` in the API calls, where xxx is the workspace ID value

---
