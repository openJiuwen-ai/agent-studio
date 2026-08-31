# 插件 API

---

## 目录

1. [查询工具列表](#1-查询工具列表)
2. [导出工具](#2-导出工具)
3. [修改指定工具](#3-修改指定工具)
4. [删除指定工具](#4-删除指定工具)

---

## 1. 查询工具列表

**功能介绍**

该接口用于查询当前项目下的工具列表。

**URI**

```
GET /v1/{project_id}/agent-manager/tools?workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |

**Query 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| workspace_id | 是 | String | 工作空间 ID |
| page | 否 | Integer | 页码，默认 1 |
| page_size | 否 | Integer | 每页数量，默认 10 |
| name | 否 | String | 按名称模糊搜索 |

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| X-Auth-Token | 是 | String | 用户 Token |

**响应参数**

| 参数 | 类型 | 描述 |
|------|------|------|
| count | Integer | 工具总数 |
| tool_list | Array of Tool | 工具列表 |

**Tool**

| 参数 | 类型 | 描述 |
|------|------|------|
| tool_id | String | 工具 ID |
| name | String | 工具名称 |
| description | String | 工具描述 |
| status | String | 工具状态 |
| creator | String | 创建者 |
| create_time | Long | 创建时间 |
| update_time | Long | 更新时间 |

**请求示例**

```
GET /v1/{project_id}/agent-manager/tools?workspace_id={workspace_id}&page=1&page_size=10 HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**响应示例**

```json
{
  "count": 1,
  "tool_list": [
    {
      "tool_id": "tool_001",
      "name": "联网搜索",
      "description": "提供联网搜索能力",
      "status": "normal",
      "creator": "admin",
      "create_time": 1735558575017,
      "update_time": 1735558575017
    }
  ]
}
```

---

## 2. 导出工具

**功能介绍**

该接口用于导出指定项目下的工具配置，便于迁移或备份。

**URI**

```
POST /v1/{project_id}/agent-manager/tools/export?workspace_id={workspace_id}
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

**请求 Body 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| tool_ids | 是 | Array of String | 要导出的工具 ID 列表 |

**响应参数**

该接口返回二进制文件流（`Content-Type: application/octet-stream`），通过 `Content-Disposition` 头指定文件名（如 `tools.jsonl`）。

**请求示例**

```
POST /v1/{project_id}/agent-manager/tools/export?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "tool_ids": ["xxxxxxxxx"]
}
```

**响应示例**

```
HTTP/1.1 200 OK
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="tools.jsonl"

<二进制文件内容>
```

---

## 3. 修改指定工具

**功能介绍**

该接口用于修改指定工具的配置信息。

**URI**

```
PUT /v1/{project_id}/agent-manager/tools/{tool_id}?workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |
| tool_id | 是 | String | 工具 ID |

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
| name | 否 | String | 工具名称 |
| description | 否 | String | 工具描述 |
| config | 否 | Object | 工具配置信息 |

**响应参数**

状态码：200

该接口成功响应无返回体。

**状态码**

| 状态码 | 描述 |
|--------|------|
| 200 | 修改成功 |
| 400 | 请求参数无效 |
| 403 | 没有操作权限 |
| 404 | 工具不存在 |
| 500 | 服务内部错误 |

**请求示例**

```
PUT /v1/{project_id}/agent-manager/tools/{tool_id}?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "name": "联网搜索-更新",
  "description": "更新后的工具描述"
}
```

---

## 4. 删除指定工具

**功能介绍**

该接口用于删除指定的工具。该接口为幂等删除，不存在的工具 ID 也会返回 200。

**URI**

```
DELETE /v1/{project_id}/agent-manager/tools/{tool_id}?workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |
| tool_id | 是 | String | 工具 ID |

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
| 200 | 删除成功（幂等，不存在的 ID 也返回 200） |
| 403 | 没有操作权限 |
| 500 | 服务内部错误 |

**请求示例**

```
DELETE /v1/{project_id}/agent-manager/tools/{tool_id}?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

---
