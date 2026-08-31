# Tool API

---

## Table of Contents

1. [Query Tool List](#1-query-tool-list)
2. [Export Tools](#2-export-tools)
3. [Modify Tool](#3-modify-tool)
4. [Delete Tool](#4-delete-tool)

---

## 1. Query Tool List

**Introduction**

This API is used to query the list of tools in the specified project.

**URI**

```
GET /v1/{project_id}/agent-manager/tools?workspace_id={workspace_id}
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
| X-Auth-Token | Yes | String | User Token |

**Response Parameters**

Status code: 200

| Parameter | Type | Description |
|------|------|------|
| count | Integer | Total number of tools |
| tool_list | Array of Tool | Tool list |

**Request Example**

```
GET /v1/{project_id}/agent-manager/tools?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**Response Example**

```json
{
  "count": 1,
  "tool_list": [
    {
      "tool_id": "tool_001",
      "name": "Web Search",
      "description": "Provides web search capability",
      "status": "normal",
      "creator": "admin",
      "create_time": 1735558575017,
      "update_time": 1735558575017
    }
  ]
}
```

---

## 2. Export Tools

**Introduction**

This API is used to export tool configurations from a specified project for migration or backup.

**URI**

```
POST /v1/{project_id}/agent-manager/tools/export?workspace_id={workspace_id}
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
| tool_ids | Yes | Array of String | List of tool IDs to export |

**Response Parameters**

This API returns a binary file stream (`Content-Type: application/octet-stream`), with the filename specified via the `Content-Disposition` header (e.g., `tools.jsonl`).

**Request Example**

```
POST /v1/{project_id}/agent-manager/tools/export?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "tool_ids": ["xxxxxxxxx"]
}
```

**Response Example**

```
HTTP/1.1 200 OK
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="tools.jsonl"

<binary file content>
```

---

## 3. Modify Tool

**Introduction**

This API is used to update the configuration of a specified tool. Modifying a non-existent tool ID returns 404 "Tool does not exist".

**URI**

```
PUT /v1/{project_id}/agent-manager/tools/{tool_id}?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |
| tool_id | Yes | String | Tool ID |

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
| name | No | String | Tool name |
| description | No | String | Tool description |
| config | No | Object | Tool configuration |

**Response Parameters**

Status code: 200

This API has no response body for a successful response.

**Status Codes**

| Status Code | Description |
|--------|------|
| 200 | Updated successfully |
| 400 | Invalid request parameters |
| 403 | No operation permission |
| 404 | Tool does not exist |
| 500 | Internal service error |

**Request Example**

```
PUT /v1/{project_id}/agent-manager/tools/{tool_id}?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "name": "Web Search-Updated",
  "description": "Updated tool description"
}
```

---

## 4. Delete Tool

**Introduction**

This API is used to delete a specified tool. This operation is idempotent - deleting a non-existent tool ID also returns 200.

**URI**

```
DELETE /v1/{project_id}/agent-manager/tools/{tool_id}?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |
| tool_id | Yes | String | Tool ID |

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

This API has no response body for a successful response.

**Status Codes**

| Status Code | Description |
|--------|------|
| 200 | Deleted successfully (idempotent - non-existent ID also returns 200) |
| 403 | No operation permission |
| 500 | Internal service error |

**Request Example**

```
DELETE /v1/{project_id}/agent-manager/tools/{tool_id}?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

---
