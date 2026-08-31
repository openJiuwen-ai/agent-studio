# 工作空间 API

---

## 目录

1. [创建工作空间](#1-创建工作空间)
2. [修改工作空间配置](#2-修改工作空间配置)
3. [删除工作空间](#3-删除工作空间)
4. [查询指定工作空间信息](#4-查询指定工作空间信息)
5. [批量添加空间成员](#5-批量添加空间成员)
6. [修改团队成员角色](#6-修改团队成员角色)
7. [批量移除空间成员](#7-批量移除空间成员)
8. [转让空间所有权](#8-转让空间所有权)
9. [退出当前用户所在空间](#9-退出当前用户所在空间)
10. [查询成员列表](#10-查询成员列表)
11. [查询角色列表](#11-查询角色列表)
12. [查询 IAM 用户列表](#12-查询-iam-用户列表)
13. [查询共享资源](#13-查询共享资源)
14. [查询已共享资源](#14-查询已共享资源)
15. [创建/更新共享](#15-创建更新共享)
16. [取消共享](#16-取消共享)

---

## 1. 创建工作空间

**功能介绍**

该接口用于创建一个新的工作空间，创建者自动成为空间所有者。

**URI**

```
POST /v1/{project_id}/agent-manager/workspace?workspace_id={workspace_id}
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
| name | 是 | String | 工作空间名称 |
| description | 否 | String | 工作空间描述 |

**响应参数**

| 参数 | 类型 | 描述 |
|------|------|------|
| id | String | 创建的工作空间 ID |
| name | String | 工作空间名称 |
| projectId | String | 项目 ID |
| type | String | 空间类型（如 `TEAM`） |
| status | String | 空间状态（如 `ENABLE`） |
| creator | String | 创建者 |
| createdOn | Long | 创建时间 |

**请求示例**

```
POST /v1/{project_id}/agent-manager/workspace?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "name": "研发团队空间",
  "description": "研发团队共享工作空间"
}
```

**响应示例**

```json
{
  "id": "ws_001",
  "name": "研发团队空间",
  "projectId": "default",
  "type": "TEAM",
  "status": "ENABLE",
  "creator": "admin",
  "createdOn": 1735558575017
}
```

---

## 2. 修改工作空间配置

**功能介绍**

该接口用于修改指定工作空间的配置信息，仅空间所有者或管理员可操作。

**URI**

```
PUT /v1/{project_id}/agent-manager/workspace?workspace_id={workspace_id}
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
| id | 是 | String | 工作空间 ID |
| name | 否 | String | 工作空间名称 |
| description | 否 | String | 工作空间描述 |

> **注意**：请求体使用 `id` 字段（不是 `workspace_id`）。

**响应参数**

状态码：200

该接口成功响应无返回体。

**请求示例**

```
PUT /v1/{project_id}/agent-manager/workspace?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "id": "ws_001",
  "name": "研发团队空间-更新",
  "description": "更新后的描述"
}
```

---

## 3. 删除工作空间

**功能介绍**

该接口用于删除指定的工作空间，仅空间所有者可操作。删除后空间内所有资源将不可恢复。

**URI**

```
DELETE /v1/{project_id}/agent-manager/workspace?workspace_id={workspace_id}
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
| id | 是 | String | 要删除的工作空间 ID |

> **注意**：请求体使用 `id` 字段（不是 `workspace_id`）。

**响应参数**

状态码：200

该接口成功响应无返回体。

**请求示例**

```
DELETE /v1/{project_id}/agent-manager/workspace?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "id": "ws_001"
}
```

---

## 4. 查询指定工作空间信息

**功能介绍**

该接口用于查询指定工作空间的详细信息，包括空间名称、成员数量、资源数量等。

**URI**

```
GET /v1/{project_id}/agent-manager/workspace?workspace_id={workspace_id}
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

| 参数 | 类型 | 描述 |
|------|------|------|
| count | Integer | 工作空间总数 |
| workspaceList | Array of Workspace | 工作空间列表 |

**Workspace**

| 参数 | 类型 | 描述 |
|------|------|------|
| id | String | 工作空间 ID |
| name | String | 工作空间名称 |
| projectId | String | 项目 ID |
| icon | String | 工作空间图标 |
| description | String | 工作空间描述 |
| tenantId | String | 租户 ID |
| type | String | 空间类型（`PERSON` 或 `TEAM`） |
| status | String | 空间状态（如 `ENABLE`） |
| creator | String | 创建者 |
| creatorId | String | 创建者 ID |
| createdOn | Long | 创建时间 |
| updater | String | 更新者 |
| updaterId | String | 更新者 ID |
| updatedOn | Long | 更新时间 |
| role | String | 当前用户在空间中的角色（如 `OWNER`） |

**请求示例**

```
GET /v1/{project_id}/agent-manager/workspace?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**响应示例**

```json
{
  "count": 1,
  "workspaceList": [
    {
      "id": "4c680613d353462fa3d2420eb6cf786f",
      "name": "个人空间",
      "projectId": "default",
      "icon": "data:image/svg+xml;base64,...",
      "description": "个人空间",
      "tenantId": "0",
      "type": "PERSON",
      "status": "ENABLE",
      "creator": "admin",
      "creatorId": "admin",
      "createdOn": 1787900850129,
      "updater": "admin",
      "updaterId": "admin",
      "updatedOn": 1787900850129,
      "role": "OWNER"
    }
  ]
}
```

---

## 5. 批量添加空间成员

**功能介绍**

该接口用于向指定工作空间批量添加成员，可同时设置成员角色。

**URI**

```
POST /v1/{project_id}/agent-manager/workspace/member?workspace_id={workspace_id}
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
| members | 是 | Array of Member | 成员列表 |

**Member**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| member_id | 是 | String | 用户 ID |
| member_name | 是 | String | 用户名称 |
| member_source | 否 | String | 成员来源，默认 `IAM` |
| role | 否 | String | 成员角色：`OWNER`、`ADMIN`、`DEVELOPER`、`OPERATOR`，默认 `DEVELOPER` |

**响应参数**

状态码：200

该接口成功响应无返回体。

**请求示例**

```
POST /v1/{project_id}/agent-manager/workspace/member?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "members": [
    {
      "member_id": "user_002",
      "member_name": "张三",
      "member_source": "IAM",
      "role": "DEVELOPER"
    },
    {
      "member_id": "user_003",
      "member_name": "李四",
      "member_source": "IAM",
      "role": "OPERATOR"
    }
  ]
}
```

---

## 6. 修改团队成员角色

**功能介绍**

该接口用于修改指定工作空间中成员的角色，仅空间所有者或管理员可操作。

**URI**

```
PATCH /v1/{project_id}/agent-manager/workspace/member?workspace_id={workspace_id}
```

> **注意**：该方法使用 `PATCH`（不是 `PUT`）。

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
| members | 是 | Array of Member | 成员列表 |

**Member**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| member_id | 是 | String | 要修改角色的用户 ID |
| role | 是 | String | 新角色：`OWNER`、`ADMIN`、`DEVELOPER`、`OPERATOR` |

**响应参数**

状态码：200

该接口成功响应无返回体。

**请求示例**

```
PATCH /v1/{project_id}/agent-manager/workspace/member?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "members": [
    {
      "member_id": "user_003",
      "role": "OPERATOR"
    }
  ]
}
```

---

## 7. 批量移除空间成员

**功能介绍**

该接口用于从指定工作空间中批量移除成员。

**URI**

```
DELETE /v1/{project_id}/agent-manager/workspace/member?workspace_id={workspace_id}
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
| user_ids | 是 | Array of strings | 要移除的用户 ID 列表 |

**响应参数**

状态码：200

该接口成功响应无返回体。

**请求示例**

```
DELETE /v1/{project_id}/agent-manager/workspace/member?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "user_ids": ["user_002", "user_003"]
}
```

---

## 8. 转让空间所有权

**功能介绍**

该接口用于将工作空间的所有权转让给其他成员，转让后原所有者变为普通成员。仅空间所有者可操作。

**URI**

```
PUT /v1/{project_id}/agent-manager/workspace/member/ownership?workspace_id={workspace_id}
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
| workspace_id | 是 | String | 工作空间 ID |
| next_owner_id | 是 | String | 接收所有权的目标用户 ID，该用户须为当前空间成员 |

**响应参数**

状态码：200

该接口成功响应无返回体。

**请求示例**

```
PUT /v1/{project_id}/agent-manager/workspace/member/ownership?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "workspace_id": "ws_001",
  "next_owner_id": "user_002"
}
```

---

## 9. 退出当前用户所在空间

**功能介绍**

该接口用于当前用户退出所在的工作空间。空间所有者不能直接退出，需先转让所有权。

**URI**

```
DELETE /v1/{project_id}/agent-manager/workspace/member/me?workspace_id={workspace_id}
```

> **注意**：该接口无请求体。

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |

**Query 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| workspace_id | 是 | String | 要退出的工作空间 ID |

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| X-Auth-Token | 是 | String | 用户 Token |

**响应参数**

状态码：200

该接口成功响应无返回体。

**请求示例**

```
DELETE /v1/{project_id}/agent-manager/workspace/member/me?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

---

## 10. 查询成员列表

**功能介绍**

该接口用于查询指定工作空间的成员列表。

**URI**

```
GET /v1/{project_id}/agent-manager/workspace/member?workspace_id={workspace_id}&page={page}&page_size={page_size}
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

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| X-Auth-Token | 是 | String | 用户 Token |

**响应参数**

| 参数 | 类型 | 描述 |
|------|------|------|
| count | Integer | 成员总数 |
| memberList | Array of Member | 成员列表 |

**请求示例**

```
GET /v1/{project_id}/agent-manager/workspace/member?workspace_id={workspace_id}&page=1&page_size=10 HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**响应示例**

```json
{
  "count": 2,
  "memberList": [
    {
      "member_id": "user_001",
      "member_name": "管理员",
      "role": "OWNER"
    },
    {
      "member_id": "user_002",
      "member_name": "张三",
      "role": "DEVELOPER"
    }
  ]
}
```

---

## 11. 查询角色列表

**功能介绍**

该接口用于查询工作空间中可用的角色列表。

**URI**

```
GET /v1/{project_id}/agent-manager/workspace/member/role?workspace_id={workspace_id}
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

| 参数 | 类型 | 描述 |
|------|------|------|
| roleList | Array of Role | 角色列表 |

**Role**

| 参数 | 类型 | 描述 |
|------|------|------|
| roleId | String | 角色 ID（如 `OWNER`、`ADMIN`、`DEVELOPER`、`OPERATOR`） |
| roleNameCn | String | 角色中文名称 |
| roleNameEn | String | 角色英文名称 |

**请求示例**

```
GET /v1/{project_id}/agent-manager/workspace/member/role?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**响应示例**

```json
{
  "roleList": [
    {
      "roleId": "OWNER",
      "roleNameCn": "空间所有者",
      "roleNameEn": "Owner"
    },
    {
      "roleId": "ADMIN",
      "roleNameCn": "空间管理员",
      "roleNameEn": "Admin"
    },
    {
      "roleId": "DEVELOPER",
      "roleNameCn": "开发者",
      "roleNameEn": "Developer"
    },
    {
      "roleId": "OPERATOR",
      "roleNameCn": "操作者",
      "roleNameEn": "Operator"
    }
  ]
}
```

---

## 12. 查询 IAM 用户列表

**功能介绍**

该接口用于查询指定工作空间中可添加的 IAM 用户列表。

**URI**

```
GET /v1/{project_id}/agent-manager/workspace/users?workspace_id={workspace_id}
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

| 参数 | 类型 | 描述 |
|------|------|------|
| count | Integer | 用户总数 |
| user_list | Array of User | 用户列表 |

**User**

| 参数 | 类型 | 描述 |
|------|------|------|
| user_id | String | 用户ID |
| user_name | String | 用户名称 |

**请求示例**

```
GET /v1/{project_id}/agent-manager/workspace/users?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**响应示例**

```json
{
  "count": 1,
  "user_list": [
    {
      "user_id": "user_002",
      "user_name": "张三"
    }
  ]
}
```

---

## 13. 查询共享资源

**功能介绍**

该接口用于查询当前工作空间中可以共享的资源列表。

**URI**

```
GET /v1/{project_id}/agent-manager/resource/share?workspace_id={workspace_id}&resource_type={resource_type}&page={page}&page_size={page_size}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |

**Query 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| workspace_id | 是 | String | 工作空间 ID |
| resource_type | 是 | String | 资源类型：`controller`（多智能体）、`workflow`（工作流）、`plugin`（插件） |
| page | 否 | Integer | 页码，默认 1 |
| page_size | 否 | Integer | 每页数量，默认 10 |

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| X-Auth-Token | 是 | String | 用户 Token |

**响应参数**

| 参数 | 类型 | 描述 |
|------|------|------|
| count | Integer | 资源总数 |
| resource_list | Array of Resource | 资源列表 |

**请求示例**

```
GET /v1/{project_id}/agent-manager/resource/share?workspace_id={workspace_id}&resource_type=controller&page=1&page_size=10 HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**响应示例**

```json
{
  "count": 0,
  "resource_list": []
}
```

---

## 14. 查询已共享资源

**功能介绍**

该接口用于查询当前工作空间已经共享出去的资源列表。

**URI**

```
GET /v1/{project_id}/agent-manager/resource/shared?workspace_id={workspace_id}&resource_type={resource_type}&page={page}&page_size={page_size}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |

**Query 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| workspace_id | 是 | String | 工作空间 ID |
| resource_type | 是 | String | 资源类型：`controller`、`workflow`、`plugin` |
| page | 否 | Integer | 页码，默认 1 |
| page_size | 否 | Integer | 每页数量，默认 10 |

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| X-Auth-Token | 是 | String | 用户 Token |

**响应参数**

| 参数 | 类型 | 描述 |
|------|------|------|
| count | Integer | 资源总数 |
| resource_list | Array of Resource | 资源列表 |

**请求示例**

```
GET /v1/{project_id}/agent-manager/resource/shared?workspace_id={workspace_id}&resource_type=controller&page=1&page_size=10 HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**响应示例**

```json
{
  "count": 0,
  "resource_list": []
}
```

---

## 15. 创建/更新共享

**功能介绍**

该接口用于将当前空间的资源共享到其他工作空间，共享后目标空间成员可以使用该资源。

**URI**

```
POST /v1/{project_id}/agent-manager/resource/share?workspace_id={workspace_id}
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
| resource_id | 是 | String | 要共享的资源 ID |
| resource_type | 是 | String | 资源类型：`controller`、`workflow`、`plugin` |
| target_workspace_id | 否 | String | 目标工作空间 ID |

**响应参数**

状态码：200

该接口成功响应无返回体。

**请求示例**

```
POST /v1/{project_id}/agent-manager/resource/share?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "resource_id": "7c5be653-71b8-48e7-9058-7191ec0f44e8",
  "resource_type": "controller",
  "target_workspace_id": "ws_002"
}
```

---

## 16. 取消共享

**功能介绍**

该接口用于取消已共享的资源。

**URI**

```
DELETE /v1/{project_id}/agent-manager/resource/share/{resource_id}?workspace_id={workspace_id}&resource_type={resource_type}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |
| resource_id | 是 | String | 要取消共享的资源 ID |

**Query 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| workspace_id | 是 | String | 工作空间 ID |
| resource_type | 是 | String | 资源类型：`controller`、`workflow`、`plugin` |

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| X-Auth-Token | 是 | String | 用户 Token |

**响应参数**

状态码：200

该接口成功响应无返回体。

**请求示例**

```
DELETE /v1/{project_id}/agent-manager/resource/share/{resource_id}?workspace_id={workspace_id}&resource_type=controller HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

---
