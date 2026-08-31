# Workflow API

---

## Table of Contents

1. [Create Workflow](#1-create-workflow)
2. [Update Workflow](#2-update-workflow)
3. [Delete Workflow](#3-delete-workflow)
4. [Query Workflow List](#4-query-workflow-list)
5. [Invoke Workflow Application](#5-invoke-workflow-application)
6. [Publish Workflow Version](#6-publish-workflow-version)
7. [Get Workflow Version List](#7-get-workflow-version-list)
8. [Import Workflow](#8-import-workflow)
9. [Export Workflow](#9-export-workflow)
10. [Parse Import File](#10-parse-import-file)

---

## 1. Create Workflow

**Introduction**

This API is used to create a new workflow application in the specified project.

**URI**

```
POST /v1/{project_id}/agent-manager/workflows?workspace_id={workspace_id}
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
| name | Yes | String | Workflow name, 2-64 characters |
| description | Yes | String | Workflow description, 1-1024 characters |
| code | Yes | String | Workflow English identifier, must be unique, 2-64 characters |
| type | Yes | String | Workflow type: `chat` or `task` |

**Response Parameters**

Status code: 200

| Parameter | Type | Description |
|------|------|------|
| workflow_id | String | Created workflow ID |

**Status Codes**

| Status Code | Description |
|--------|------|
| 200 | Created successfully |
| 400 | Invalid request parameters |
| 403 | No operation permission |
| 500 | Internal service error |

**Request Example**

```
POST /v1/{project_id}/agent-manager/workflows?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "name": "Knowledge Base Q&A Workflow",
  "code": "workflow_code",
  "description": "Q&A workflow based on knowledge base retrieval",
  "type": "chat"
}
```

**Response Example**

```json
{
  "workflow_id": "cd7a8f33-66e3-455c-b008-a6b18dd27319"
}
```

---

## 2. Update Workflow

**Introduction**

This API is used to update the configuration of a specified workflow application.

**URI**

```
PUT /v1/{project_id}/agent-manager/workflows/{workflow_id}?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |
| workflow_id | Yes | String | Workflow ID |

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
| name | No | String | Workflow name |
| description | No | String | Workflow description |

**Response Parameters**

Status code: 200

This API has no response body for a successful response.

**Status Codes**

| Status Code | Description |
|--------|------|
| 200 | Updated successfully |
| 400 | Invalid request parameters |
| 403 | No operation permission |
| 404 | Workflow does not exist |
| 500 | Internal service error |

**Request Example**

```
PUT /v1/{project_id}/agent-manager/workflows/{workflow_id}?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "name": "Knowledge Base Q&A Workflow-Updated",
  "description": "Updated description"
}
```

---

## 3. Delete Workflow

**Introduction**

This API is used to delete a specified workflow application.

**URI**

```
DELETE /v1/{project_id}/agent-manager/workflows/{workflow_id}?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |
| workflow_id | Yes | String | Workflow ID |

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
| id | String | Deleted workflow ID |

**Status Codes**

| Status Code | Description |
|--------|------|
| 200 | Deleted successfully |
| 403 | No operation permission |
| 404 | Workflow does not exist |
| 500 | Internal service error |

**Request Example**

```
DELETE /v1/{project_id}/agent-manager/workflows/{workflow_id}?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**Response Example**

```json
{
  "id": "cd7a8f33-66e3-455c-b008-a6b18dd27319"
}
```

---

## 4. Query Workflow List

**Introduction**

This API is used to query the list of workflows in the current project.

**URI**

```
GET /v1/{project_id}/agent-manager/workflows?workspace_id={workspace_id}
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
| count | Integer | Total number of workflows |
| workflow_list | Array of Workflow | Workflow list |

**Workflow**

| Parameter | Type | Description |
|------|------|------|
| workflow_id | String | Workflow ID |
| name | String | Workflow name |
| description | String | Workflow description |
| status | String | Workflow status |
| create_time | Long | Creation time |
| update_time | Long | Update time |

**Request Example**

```
GET /v1/{project_id}/agent-manager/workflows?workspace_id={workspace_id}&page=1&page_size=10 HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**Response Example**

```json
{
  "count": 1,
  "workflow_list": [
    {
      "workflow_id": "cd7a8f33-66e3-455c-b008-a6b18dd27319",
      "name": "Knowledge Base Q&A Workflow",
      "description": "Q&A workflow based on knowledge base retrieval",
      "status": "published",
      "create_time": 1735558575017,
      "update_time": 1735558575017
    }
  ]
}
```

---

## 5. Invoke Workflow Application

**Introduction**

This API is used to run scenario-based applications. It supports executing workflow logic within a specified project, workflow, and conversation context. The API supports streaming response mode.

**Applicable Scenarios**

- Run predefined workflows in a project
- Supports debug mode and published mode
- Supports streaming responses, suitable for scenarios requiring real-time feedback

**URI**

```
POST /v1/{project_id}/agent-manager/workflows/chat/{short_code}/conversations/{conversation_id}?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |
| short_code | Yes | String | Published version code |
| conversation_id | Yes | String | Conversation ID, the unique identifier for each conversation |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| Content-Type | Yes | String | MIME type of the request body, default `application/json` |
| X-Auth-Token | Yes | String | User Token |
| X-Invoke-Mode | No | String | Run mode: `debug` (debug mode) or `published` (published mode), default `published` |
| stream | No | Boolean | Whether to enable streaming invocation, default `true` |
| X-Request-Id | No | String | Trace ID |

**Request Body Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| inputs | Yes | Map<String,Object> | The user's question, used as input for running the workflow |
| plugin_configs | No | Array of PluginConfig | Plugin configuration information |

**PluginConfig**

| Parameter | Required | Type | Description |
|------|------|------|------|
| plugin_id | No | String | Plugin ID |
| config | No | Map<String,String> | Plugin configuration information |

**Response Parameters**

Status code: 200

| Parameter | Type | Description |
|------|------|------|
| event | String | Event type |
| data | data object | Workflow assistant reply content |
| createdTime | Long | Timestamp of the response message |

**data**

| Parameter | Type | Description |
|------|------|------|
| text | String | Workflow output content message block |
| index | Integer | Message block index |
| node_id | String | Node ID |
| node_type | String | Node type |
| node_name | String | Node name |
| workflow_id | String | Workflow ID |
| workflow_name | String | Workflow name |
| createdTime | Long | Creation time |

**Status Codes**

| Status Code | Description |
|--------|------|
| 200 | Successful response |
| 500 | Error response |

**Request Example**

```
POST /v1/{project_id}/agent-manager/workflows/chat/{short_code}/conversations/{conversation_id}?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}
stream: true

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

**Response Example**

Successful response (status code: 200):

```json
{
  "event": "message",
  "data": {
    "text": null,
    "index": 11,
    "node_id": "node_end",
    "node_type": "End",
    "node_name": "End",
    "workflow_id": "cd7a8f33-66e3-455c-b008-a6b18dd27319",
    "workflow_name": "flowouttest",
    "createdTime": 1760169416635
  },
  "createdTime": 1760169416635
}
```

Error response (status code: 500):

```json
{
  "event": "error",
  "data": {
    "text": null,
    "index": 11,
    "node_id": "node_end",
    "node_type": "End",
    "node_name": "End",
    "code": "101563",
    "message": "Execution error, error code: 101563, error message: Get model streaming output error",
    "workflow_id": "cd7a8f33-66e3-455c-b008-a6b18dd27319",
    "workflow_name": "flowouttest",
    "createdTime": 1760169416635
  },
  "createdTime": 1760169416635
}
```

---

## 6. Publish Workflow Version

**Introduction**

This API is used to publish a new version of a specified workflow application, creating version snapshots of the workflow DSL and IR files, validating the workflow configuration, and returning the published version ID.

**Applicable Scenarios**

- Publish the current configuration of a workflow application as a new version
- Automatically validate the workflow configuration before publishing
- Create version snapshots for workflow applications for subsequent rollback or management

**URI**

```
POST /v1/{project_id}/agent-manager/workflows/{workflow_id}/versions?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Tenant project ID, up to 64 characters, supports only letters, numbers, underscores, and hyphens |
| workflow_id | Yes | String | Workflow ID, up to 64 characters, supports only letters, numbers, underscores, and hyphens |

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

**Response Parameters**

Status code: 200

| Parameter | Type | Description |
|------|------|------|
| version_id | String | Published version ID |

Status code: 400 / 401 / 403 / 404 / 500

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
| 200 | Publish successful |
| 400 | Request error, such as invalid parameters, version name already exists, or workflow validation failed |
| 401 | Authentication failed |
| 403 | No operation permission |
| 404 | Resource not found |
| 500 | Internal service error, such as workflow does not exist |

**Request Example**

```
POST /v1/{project_id}/agent-manager/workflows/{workflow_id}/versions?workspace_id={workspace_id} HTTP/1.1
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

```json
"1783341175105"
```

Error response (status code: 400):

```json
{
  "error_msg": "The version name already existed."
}
```

---

## 7. Get Workflow Version List

**Introduction**

This API is used to get the version list of a specified workflow application.

**URI**

```
GET /v1/{project_id}/agent-manager/workflows/{workflow_id}/versions?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |
| workflow_id | Yes | String | Workflow ID |

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
| status | String | Version status |
| release_time | Long | Release time |

**Request Example**

```
GET /v1/{project_id}/agent-manager/workflows/{workflow_id}/versions?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**Response Example**

```json
{
  "count": 1,
  "version_list": [
    {
      "version_id": "1783341175105",
      "version_name": "v1.0.0",
      "version_note": "Initial release version",
      "status": "normal",
      "release_time": 1783341175105
    }
  ]
}
```

---

## 8. Import Workflow

**Introduction**

This API is used to import an exported workflow configuration file into the current project to quickly create a workflow application.

**URI**

```
POST /v1/{project_id}/agent-manager/workflows/import?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID |
| import_workflows | No | String | Whether to import workflows, set to `true` to enable |
| import_tools | No | String | Whether to import tools, set to `true` to enable |
| mode | No | String | Import mode: `STRICT` (strict mode) / `SPACIOUS` (lenient mode), default `STRICT` |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| Content-Type | Yes | String | `multipart/form-data` |
| X-Auth-Token | Yes | String | User Token |

**Request Body Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| file | Yes | File | Exported workflow configuration file in `.jsonl` format (multipart upload) |

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
POST /v1/{project_id}/agent-manager/workflows/import?workspace_id={workspace_id}&import_workflows=true&import_tools=true&mode=SPACIOUS HTTP/1.1
Host: api.example.com
Content-Type: multipart/form-data
X-Auth-Token: {token}

file=@workflow_config.jsonl
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

## 9. Export Workflow

**Introduction**

This API is used to export the configuration file of a specified workflow application for migration or backup.

**URI**

```
POST /v1/{project_id}/agent-manager/workflows/export?workspace_id={workspace_id}
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
| workflow_ids | Yes | Array of String | List of workflow IDs to export |

**Response Parameters**

This API returns a binary file stream (`Content-Type: application/octet-stream`), with the filename specified via the `Content-Disposition` header (e.g., `workflows.jsonl`).

**Request Example**

```
POST /v1/{project_id}/agent-manager/workflows/export?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "workflow_ids": ["cd7a8f33-66e3-455c-b008-a6b18dd27319"]
}
```

**Response Example**

```
HTTP/1.1 200 OK
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="workflows.jsonl"

<binary file content>
```

---

## 10. Parse Import File

**Introduction**

This API is used to parse and convert third-party workflow configuration files (currently supports Dify format), returning the parsed workflow information for preview before import.

**URI**

```
POST /v1/{project_id}/agent-manager/workflows/import/parse?type={type}&workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| type | Yes | String | Third-party workflow type, currently only supports `Dify` |
| workspace_id | Yes | String | Workspace ID |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| Content-Type | Yes | String | `multipart/form-data` |
| X-Auth-Token | Yes | String | User Token |

**Request Body Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| file | Yes | File | Dify format workflow configuration file to parse (multipart upload) |

**Response Parameters**

| Parameter | Type | Description |
|------|------|------|
| workflow_id | String | Workflow ID |
| name | String | Workflow name |
| code | String | Workflow code identifier |
| description | String | Workflow description |
| avatar | String | Workflow avatar |
| status | Integer | Workflow status |
| workflow_details | Object | Workflow detailed configuration |
| trigger_list | Array | Trigger configuration list |

**Request Example**

```
POST /v1/{project_id}/agent-manager/workflows/import/parse?type=Dify&workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: multipart/form-data
X-Auth-Token: {token}

file=@dify_workflow.yml
```

**Response Example**

```json
{
  "name": "Knowledge Base Q&A Workflow",
  "code": "kb-qa-workflow",
  "description": "Q&A workflow based on knowledge base retrieval",
  "workflow_details": {
    "nodes": [],
    "edges": []
  }
}
```

---
