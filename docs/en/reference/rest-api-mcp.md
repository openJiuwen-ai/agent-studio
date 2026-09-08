# MCP Service API

---

## Table of Contents

1. [Query MCP Service List](#1-query-mcp-service-list)
2. [Query MCP Service Summary](#2-query-mcp-service-summary)
3. [Deploy MCP Service](#3-deploy-mcp-service)
4. [Delete MCP Service](#4-delete-mcp-service)
5. [Modify MCP Service](#5-modify-mcp-service)

---

## 1. Query MCP Service List

**Introduction**

This API is used to query the list of MCP (Model Context Protocol) services in a specified project.

**URI**

```
POST /v1/{project_id}/mcp/service/list?workspace_id={workspace_id}
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

**Response Parameters**

Status code: 200

| Parameter | Type | Description |
|------|------|------|
| mcps | Array of MCP | MCP service list |
| total | Integer | Total number of MCP services |

**Request Example**

```
POST /v1/{project_id}/mcp/service/list?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}
```

**Response Example**

```json
{
  "mcps": [],
  "total": 0
}
```

---

## 2. Query MCP Service Summary

**Introduction**

This API is used to query a summary of MCP services, including counts of private, inner, and total MCP services.

**URI**

```
GET /v1/{project_id}/mcp/service/list/summary?workspace_id={workspace_id}
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
| private_mcp | Integer | Number of private MCP services |
| total_mcp | Integer | Total number of MCP services |
| inner_mcp | Integer | Number of inner MCP services |

**Request Example**

```
GET /v1/{project_id}/mcp/service/list/summary?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**Response Example**

```json
{
  "private_mcp": 0,
  "total_mcp": 0,
  "inner_mcp": 0
}
```

---

## 3. Deploy MCP Service

**Introduction**

This API is used to deploy an MCP (Model Context Protocol) service in a specified project, enabling agents and workflows to use the tool capabilities provided by the MCP service.

**Applicable Scenarios**

- Connect custom MCP services to a project
- Connect template MCP services to a project
- Add MCP tool capabilities to agents and workflows

**URI**

```
POST /v1/{project_id}/mcp/deploy/{id}?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |
| id | Yes | String | MCP service template ID or custom MCP configuration ID |

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
| name | No | String | MCP service name |
| description | No | String | MCP service description |
| org_type | Yes | String | Organization type: `SSE`, `NPX`, `UVX`, or `streamable_http` |
| config | No | Object | MCP service configuration |

**Response Parameters**

Status code: 200

| Parameter | Type | Description |
|------|------|------|
| service_id | String | Deployed MCP service ID |

**Status Codes**

| Status Code | Description |
|--------|------|
| 200 | Deployed successfully |
| 400 | Invalid request parameters |
| 403 | No operation permission |
| 500 | Internal service error |

**Request Example**

```
POST /v1/{project_id}/mcp/deploy/{id}?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "name": "Web Search MCP",
  "description": "MCP service providing web search capabilities",
  "org_type": "streamable_http",
  "config": {
    "server_url": "https://mcp.example.com/search",
    "transport": "streamable_http"
  }
}
```

**Response Example**

```json
{
  "service_id": "mcp_service_001"
}
```

---

## 4. Delete MCP Service

**Introduction**

This API is used to delete a specified MCP service. After deletion, the service will no longer be available. Deleting a non-existent MCP service ID returns 400 "Missing MCP service ID parameter".

**URI**

```
DELETE /v1/{project_id}/mcp/service/delete/{id}?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |
| id | Yes | String | MCP service ID |

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
| 200 | Deleted successfully |
| 400 | Missing MCP service ID parameter (non-existent ID) |
| 403 | No operation permission |
| 500 | Internal service error |

**Request Example**

```
DELETE /v1/{project_id}/mcp/service/delete/{id}?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

---

## 5. Modify MCP Service

**Introduction**

This API is used to modify the configuration of a specified MCP service. The `name` field is required (`@NotEmpty`). Modifying a non-existent MCP service ID returns 400 when MCP service does not exist.

**URI**

```
PUT /v1/{project_id}/mcp/service/modify?workspace_id={workspace_id}
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
| service_id | Yes | String | MCP service ID |
| name | Yes | String | MCP service name (required) |
| description | No | String | MCP service description |
| config | No | Object | MCP service configuration |

**Response Parameters**

Status code: 200

This API has no response body for a successful response.

**Status Codes**

| Status Code | Description |
|--------|------|
| 200 | Modified successfully |
| 400 | Invalid request parameters or MCP service does not exist |
| 403 | No operation permission |
| 500 | Internal service error |

**Request Example**

```
PUT /v1/{project_id}/mcp/service/modify?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "service_id": "mcp_service_001",
  "name": "Web Search MCP-Updated",
  "description": "Updated description"
}
```

---
