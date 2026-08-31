# MCP 服务 API

---

## 目录

1. [查询 MCP 服务列表](#1-查询-mcp-服务列表)
2. [查询 MCP 服务汇总](#2-查询-mcp-服务汇总)
3. [部署 MCP 服务](#3-部署-mcp-服务)
4. [删除 MCP 服务](#4-删除-mcp-服务)
5. [修改 MCP 服务信息](#5-修改-mcp-服务信息)

---

## 1. 查询 MCP 服务列表

**功能介绍**

该接口用于查询当前项目下的 MCP（Model Context Protocol）服务列表。

**URI**

```
POST /v1/{project_id}/mcp/service/list?workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |

**Query 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| workspace_id | 是 | String | 工作空间 ID |

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| Content-Type | 是 | String | 默认 `application/json` |
| X-Auth-Token | 是 | String | 用户 Token |

**响应参数**

状态码：200

| 参数 | 类型 | 描述 |
|------|------|------|
| mcps | Array of McpService | MCP 服务列表 |
| total | Integer | MCP 服务总数 |

**McpService**

| 参数 | 类型 | 描述 |
|------|------|------|
| id | String | MCP 服务 ID |
| name | String | MCP 服务名称 |
| description | String | MCP 服务描述 |
| org_type | String | 部署类型：`SSE`、`NPX`、`UVX`、`streamable_http` |
| status | String | 服务状态 |
| creator | String | 创建者 |
| create_time | Long | 创建时间 |

**请求示例**

```
POST /v1/{project_id}/mcp/service/list?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{}
```

**响应示例**

```json
{
  "mcps": [],
  "total": 0
}
```

---

## 2. 查询 MCP 服务汇总

**功能介绍**

该接口用于查询当前项目下 MCP 服务的汇总统计信息，包括私有 MCP、内部 MCP 和总数。

**URI**

```
GET /v1/{project_id}/mcp/service/list/summary?workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |

**Query 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| workspace_id | 是 | String | 工作空间 ID |

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| X-Auth-Token | 是 | String | 用户 Token |

**响应参数**

状态码：200

| 参数 | 类型 | 描述 |
|------|------|------|
| private_mcp | Integer | 私有 MCP 数量 |
| total_mcp | Integer | MCP 服务总数 |
| inner_mcp | Integer | 内部 MCP 数量 |

**请求示例**

```
GET /v1/{project_id}/mcp/service/list/summary?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**响应示例**

```json
{
  "private_mcp": 0,
  "total_mcp": 0,
  "inner_mcp": 0
}
```

---

## 3. 部署 MCP 服务

**功能介绍**

该接口用于在指定项目中部署 MCP（Model Context Protocol）服务，使智能体和工作流可以使用该 MCP 服务提供的工具能力。

**适用场景**

- 在项目中接入自定义 MCP 服务
- 在项目中接入模板 MCP 服务
- 为智能体和工作流添加 MCP 工具能力

**URI**

```
POST /v1/{project_id}/mcp/deploy/{id}?workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |
| id | 是 | String | MCP 服务模板 ID 或自定义 MCP 配置 ID |

**Query 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| workspace_id | 是 | String | 工作空间 ID |

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| Content-Type | 是 | String | 默认 `application/json` |
| X-Auth-Token | 是 | String | 用户 Token |

**请求 Body 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| name | 否 | String | MCP 服务名称 |
| description | 否 | String | MCP 服务描述 |
| org_type | 是 | String | 部署类型：`SSE`、`NPX`、`UVX`、`streamable_http` 之一 |
| config | 否 | Object | MCP 服务配置信息 |

**响应参数**

状态码：200

| 参数 | 类型 | 描述 |
|------|------|------|
| service_id | String | 部署的 MCP 服务 ID |

**状态码**

| 状态码 | 描述 |
|--------|------|
| 200 | 部署成功 |
| 400 | 请求参数无效 |
| 403 | 没有操作权限 |
| 500 | 服务内部错误 |

**请求示例**

```
POST /v1/{project_id}/mcp/deploy/{id}?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "name": "联网搜索MCP",
  "description": "提供联网搜索能力的MCP服务",
  "org_type": "streamable_http",
  "config": {
    "server_url": "https://mcp.example.com/search",
    "transport": "streamable_http"
  }
}
```

**响应示例**

```json
{
  "service_id": "mcp_service_001"
}
```

---

## 4. 删除 MCP 服务

**功能介绍**

该接口用于删除指定的 MCP 服务，删除后该服务将不再可用。

**URI**

```
DELETE /v1/{project_id}/mcp/service/delete/{id}?workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |
| id | 是 | String | MCP 服务 ID |

**Query 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| workspace_id | 是 | String | 工作空间 ID |

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| Content-Type | 是 | String | 默认 `application/json` |
| X-Auth-Token | 是 | String | 用户 Token |

**响应参数**

状态码：200

该接口成功响应无返回体。

**状态码**

| 状态码 | 描述 |
|--------|------|
| 200 | 删除成功 |
| 400 | 缺少 MCP 服务 ID 参数（不存在的 ID 返回 400） |
| 403 | 没有操作权限 |
| 500 | 服务内部错误 |

**请求示例**

```
DELETE /v1/{project_id}/mcp/service/delete/{id}?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}
```

---

## 5. 修改 MCP 服务信息

**功能介绍**

该接口用于修改指定 MCP 服务的配置信息。

**URI**

```
PUT /v1/{project_id}/mcp/service/modify?workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |

**Query 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| workspace_id | 是 | String | 工作空间 ID |

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| Content-Type | 是 | String | 默认 `application/json` |
| X-Auth-Token | 是 | String | 用户 Token |

**请求 Body 参数（McpServiceModifyReq）**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| service_id | 是 | String | MCP 服务 ID |
| name | 是 | String | MCP 服务名称（必填） |
| description | 否 | String | MCP 服务描述 |
| config | 否 | Object | MCP 服务配置信息 |

**响应参数**

状态码：200

该接口成功响应无返回体。

**状态码**

| 状态码 | 描述 |
|--------|------|
| 200 | 修改成功 |
| 400 | 请求参数无效，或 MCP 服务不存在（MCP 服务不存在时返回 400） |
| 403 | 没有操作权限 |
| 500 | 服务内部错误 |

**请求示例**

```
PUT /v1/{project_id}/mcp/service/modify?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "service_id": "mcp_service_001",
  "name": "联网搜索MCP-更新",
  "description": "更新后的描述"
}
```

---
