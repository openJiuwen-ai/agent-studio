# 单智能体 API

---

## 目录

1. [创建智能体](#1-创建智能体)
2. [修改智能体](#2-修改智能体)
3. [删除智能体](#3-删除智能体)
4. [查询智能体列表](#4-查询智能体列表)
5. [获取智能体详情](#5-获取智能体详情)
6. [调用智能体应用](#6-调用智能体应用)
7. [发布智能体版本](#7-发布智能体版本)
8. [获取智能体版本列表](#8-获取智能体版本列表)
9. [导入智能体](#9-导入智能体)
10. [导出智能体](#10-导出智能体)

---

## 1. 创建智能体

**功能介绍**

该接口用于在指定项目中创建一个新的智能体应用。

**URI**

```
POST /v1/{project_id}/agent-manager/agents?workspace_id={workspace_id}
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
| name | 是 | String | 智能体名称，长度 1-64 字符 |
| description | 是 | String | 智能体描述，长度 1-256 字符 |
| type | 否 | String | 智能体类型：`agent`（单智能体，默认）或 `controller`（多智能体） |
| icon | 否 | String | 智能体图标 |

**响应参数**

状态码：200

| 参数 | 类型 | 描述 |
|------|------|------|
| agent_id | String | 创建的智能体 ID |
| project_id | String | 项目 ID |
| name | String | 智能体名称 |
| type | String | 智能体类型 |
| sub_type | String | 智能体子类型 |
| description | String | 智能体描述 |
| icon | String | 智能体图标 |
| model_config | Object | 模型配置信息 |
| status | String | 智能体状态 |
| creator | String | 创建者 |
| create_time | Long | 创建时间 |
| update_time | Long | 更新时间 |

**状态码**

| 状态码 | 描述 |
|--------|------|
| 200 | 创建成功 |
| 400 | 请求参数无效 |
| 403 | 没有操作权限 |
| 500 | 服务内部错误 |

**请求示例**

```
POST /v1/{project_id}/agent-manager/agents?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "name": "医疗问诊助手",
  "description": "基于大模型的医疗问诊智能体",
  "type": "agent"
}
```

**响应示例**

```json
{
  "agent_id": "7f949107-e394-4897-8816-8c7e92bfada1",
  "project_id": "default",
  "name": "医疗问诊助手",
  "type": "agent",
  "sub_type": "common",
  "description": "基于大模型的医疗问诊智能体",
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

## 2. 修改智能体

**功能介绍**

该接口用于修改指定智能体应用的配置信息。

**URI**

```
PUT /v1/{project_id}/agent-manager/agents/{agent_id}?workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |
| agent_id | 是 | String | 智能体 ID |

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
| name | 否 | String | 智能体名称 |
| description | 否 | String | 智能体描述 |

**响应参数**

状态码：200

返回更新后的完整智能体信息，响应参数同[创建智能体](#1-创建智能体)响应参数。

**状态码**

| 状态码 | 描述 |
|--------|------|
| 200 | 修改成功 |
| 400 | 请求参数无效 |
| 403 | 没有操作权限 |
| 404 | 智能体不存在 |
| 500 | 服务内部错误 |

**请求示例**

```
PUT /v1/{project_id}/agent-manager/agents/{agent_id}?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "name": "医疗问诊助手-更新",
  "description": "更新后的描述"
}
```

---

## 3. 删除智能体

**功能介绍**

该接口用于删除指定的智能体应用。

**URI**

```
DELETE /v1/{project_id}/agent-manager/agents/{agent_id}?workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |
| agent_id | 是 | String | 智能体 ID |

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
| id | String | 被删除的智能体 ID |

**状态码**

| 状态码 | 描述 |
|--------|------|
| 200 | 删除成功 |
| 403 | 没有操作权限 |
| 404 | 智能体不存在 |
| 500 | 服务内部错误 |

**请求示例**

```
DELETE /v1/{project_id}/agent-manager/agents/{agent_id}?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**响应示例**

```json
{
  "id": "7f949107-e394-4897-8816-8c7e92bfada1"
}
```

---

## 4. 查询智能体列表

**功能介绍**

该接口用于查询当前项目下的智能体列表。

**URI**

```
GET /v1/{project_id}/agent-manager/agents?workspace_id={workspace_id}
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
| count | Integer | 智能体总数 |
| agent_list | Array of Agent | 智能体列表 |

**Agent**

| 参数 | 类型 | 描述 |
|------|------|------|
| agent_id | String | 智能体 ID |
| project_id | String | 项目 ID |
| name | String | 智能体名称 |
| type | String | 智能体类型 |
| sub_type | String | 智能体子类型 |
| description | String | 智能体描述 |
| icon | String | 智能体图标 |
| model_config | Object | 模型配置信息 |
| status | String | 智能体状态 |
| url | String | 智能体调用 URL |
| creator | String | 创建者 |
| create_time | Long | 创建时间 |
| update_time | Long | 更新时间 |

**请求示例**

```
GET /v1/{project_id}/agent-manager/agents?workspace_id={workspace_id}&page=1&page_size=10 HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**响应示例**

```json
{
  "count": 1,
  "agent_list": [
    {
      "agent_id": "7f949107-e394-4897-8816-8c7e92bfada1",
      "project_id": "default",
      "name": "医疗问诊助手",
      "type": "agent",
      "sub_type": "common",
      "description": "基于大模型的医疗问诊智能体",
      "icon": "data:image/svg+xml;base64,...",
      "model_config": {
        "top_p": 1.0,
        "temperature": 0.0,
        "history_size": 20,
        "output_format": "text",
        "max_tokens": 4096
      },
      "status": "draft",
      "url": "/v1/default/agent-manager/agents/chat/7f949107-e394-4897-8816-8c7e92bfada1/conversations/:conversation_id",
      "creator": "admin",
      "creator_id": "admin",
      "create_time": 1787901076487,
      "update_time": 1787901076487
    }
  ]
}
```

---

## 5. 获取智能体详情

**功能介绍**

该接口用于获取指定智能体应用的详细信息。

**URI**

```
GET /v1/{project_id}/agent-manager/agents/{agent_id}?workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |
| agent_id | 是 | String | 智能体 ID |

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
| agent_id | String | 智能体 ID |
| project_id | String | 项目 ID |
| name | String | 智能体名称 |
| type | String | 智能体类型 |
| sub_type | String | 智能体子类型 |
| description | String | 智能体描述 |
| icon | String | 智能体图标 |
| model_config | Object | 模型配置信息 |
| details | Object | 智能体详细配置（包含 nodes、tools、workflows、mcp_servers、skills、knowledge_repos 等） |
| status | String | 智能体状态 |
| creator | String | 创建者 |
| create_time | Long | 创建时间 |
| update_time | Long | 更新时间 |

**请求示例**

```
GET /v1/{project_id}/agent-manager/agents/{agent_id}?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**响应示例**

```json
{
  "agent_id": "7c5be653-71b8-48e7-9058-7191ec0f44e8",
  "name": "医疗问诊助手",
  "description": "基于大模型的医疗问诊智能体",
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

## 6. 调用智能体应用

**功能介绍**

该接口用于运行知识型智能体应用，支持单智能体和多智能体，支持在指定的项目、智能体和对话上下文中执行智能体逻辑。接口支持流式响应模式。

**适用场景**

- 在项目中运行预定义的知识型智能体应用
- 支持调试模式和发布模式
- 支持流式响应，适用于需要实时反馈的场景

**URI**

```
POST /v1/{project_id}/agent-manager/agents/chat/{short_code}?workspace_id={workspace_id}
```

也可指定 `conversation_id`：

```
POST /v1/{project_id}/agent-manager/agents/chat/{short_code}/conversations/{conversation_id}?workspace_id={workspace_id}
```

> **注意**：`short_code` 是智能体发布版本号（非 agent_id）。未发布的智能体调用会返回 404，错误码为 `OpenJiuwen.02201022`。

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |
| short_code | 是 | String | 智能体发布版本号（short_code），非 agent_id |
| conversation_id | 否 | String | 会话 ID，每个会话的唯一标识符 |

**Query 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| workspace_id | 是 | String | 工作空间 ID |

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| X-Auth-Token | 是 | String | 用户 Token |
| X-Invoke-Mode | 否 | String | 运行模式：`debug` 或 `published`，默认 `published` |
| stream | 否 | Boolean | 是否开启流式调用，当前智能体应用只支持流式调用，默认 `true` |
| X-Request-Id | 否 | String | 调用链 ID |
| Content-Type | 是 | String | `application/json` |

**请求 Body 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| query | 否 | String | 用户请求的问题 |
| inputs | 是 | Map<String,Object> | 用户提出的问题 |
| user_profile | 否 | UserProfile object | 用户画像 |
| tool_switch_dict | 否 | Map<String,Boolean> | 插件是否开启 |
| model_deployment_id | 否 | String | 为智能体配置的模型的 id |
| enable_history | 否 | Boolean | 是否记录会话历史，默认 `true` |
| histories | 否 | Array of Message | 传入的会话历史 |
| files | 否 | Array of strings | 上传文件 url |

**UserProfile**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| enable_retrieve | 否 | Boolean | 运行时是否读取用户画像，默认 `false` |
| enable_extract | 否 | Boolean | 运行时是否构建用户画像，默认 `false` |

**Message**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| role | 否 | String | 会话角色：`user`（用户输入）或 `assistant`（模型回复） |
| content | 否 | String | 会话内容 |

**响应参数**

状态码：200

| 参数 | 类型 | 描述 |
|------|------|------|
| data | String | 流式返回的智能体消息 |
| event | String | 数据单元类型 |
| content | Object | 消息块内容 |
| createdTime | Long | 消息块返回的时间戳 |
| latency | latency object | 耗时信息 |
| plugin | plugin object | 插件请求信息 |

**event 取值**

| 值 | 说明 |
|-----|------|
| start | 开始节点，表示开始调用模型进行会话 |
| message | 消息节点，表示模型返回的消息 |
| plugin_start | 插件调用请求节点 |
| plugin_end | 插件调用响应节点 |
| statistic_data | 执行数据节点，包含本次调用的耗时信息 |
| summary_response | 消息总结节点，包含本次调用的全量响应信息 |
| done | 流式调用结束节点 |

**latency**

| 参数 | 类型 | 描述 |
|------|------|------|
| plugin | Long | 插件调用耗时 |
| model | Long | 模型调用耗时 |
| overall | Long | 总耗时 |

**plugin**

| 参数 | 类型 | 描述 |
|------|------|------|
| name | String | 插件名 |
| arguments | Object | 插件入参名 |

**状态码**

| 状态码 | 描述 |
|--------|------|
| 200 | 成功响应 |
| 404 | 智能体未发布或不存在（error_code: `openjiuwen.02201022`） |
| 500 | 错误响应 |

**请求示例**

```
POST /v1/{project_id}/agent-manager/agents/chat/{short_code}/conversations/{conversation_id}?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}
stream: true

{
  "query": "查询A12会议室在9:00到10:00的状态"
}
```

**响应示例**

```
data:{"event":"start","createdTime":1735558575017}
data:{"event":"message","content":"好的","createdTime":1735558576300}
data:{"event":"message","content":"，","createdTime":1735558576301}
data:{"event":"message","content":"我将","createdTime":1735558576301}
data:{"event":"message","content":"调用","createdTime":1735558576302}
data:{"event":"message","content":"query","createdTime":1735558576302}
data:{"event":"statistic_data","latency":{"overall":1.97},"createdTime":1735558576986}
data:{"event":"summary_response","content":"A12会议室在9:00到10:00的时间段内是空闲的。","role":"assistant","createdTime":1735558576987}
data:{"event":"done","createdTime":1735558577011}
```

---

## 7. 发布智能体版本

**功能介绍**

该接口用于发布指定智能体应用的新版本，创建 DSL 和 IR 文件的版本快照，并记录版本信息。

**适用场景**

- 将智能体应用的当前配置发布为一个新的版本
- 为智能体应用创建版本快照，便于后续回滚或管理

**URI**

```
POST /v1/{project_id}/agent-manager/agents/{agent_id}/versions?workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 项目 ID |
| agent_id | 是 | String | 智能体 ID，长度不超过 64 字符，仅支持字母、数字、下划线和连字符 |

**Query 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| workspace_id | 是 | String | 工作空间 ID，长度 1 至 64 字符 |

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| Content-Type | 是 | String | 默认 `application/json` |
| X-Auth-Token | 是 | String | 用户 Token |

**请求 Body 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| version_name | 是 | String | 版本名称，长度不超过 64 字符 |
| version_note | 否 | String | 版本备注，长度不超过 1024 字符 |

**响应参数**

状态码：200

该接口成功响应无返回体。

状态码：400 / 403 / 404 / 500

| 参数 | 类型 | 描述 |
|------|------|------|
| error_code | String | 错误码 |
| error_msg | String | 错误信息 |
| error_reason | String | 错误原因 |
| error_suggestion | String | 错误处理建议 |
| details | Array of ErrorDetail | 调用接口返回的错误详细信息 |

**状态码**

| 状态码 | 描述 |
|--------|------|
| 200 | 创建智能体版本成功 |
| 400 | 请求错误，如参数无效或版本名称已存在 |
| 403 | 没有操作权限 |
| 404 | 找不到资源，如智能体不存在 |
| 500 | 服务内部错误 |

**请求示例**

```
POST /v1/{project_id}/agent-manager/agents/{agent_id}/versions?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "version_name": "v1.0.0",
  "version_note": "初始发布版本"
}
```

**响应示例**

成功响应（状态码：200）：

无返回体。

错误响应（状态码：400）：

```json
{
  "error_msg": "The version name already existed."
}
```

---

## 8. 获取智能体版本列表

**功能介绍**

该接口用于获取指定智能体应用的版本列表。

**URI**

```
GET /v1/{project_id}/agent-manager/agents/{agent_id}/versions?workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |
| agent_id | 是 | String | 智能体 ID |

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
| count | Integer | 版本总数 |
| version_list | Array of Version | 版本列表 |

**Version**

| 参数 | 类型 | 描述 |
|------|------|------|
| version_id | String | 版本 ID |
| version_name | String | 版本名称 |
| version_note | String | 版本备注 |
| status | String | 版本状态（如 `normal`） |
| release_time | Long | 发布时间 |
| creator | String | 创建者 |
| creator_id | String | 创建者 ID |

**请求示例**

```
GET /v1/{project_id}/agent-manager/agents/{agent_id}/versions?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**响应示例**

```json
{
  "count": 1,
  "version_list": [
    {
      "version_id": "1787901244768",
      "version_name": "v1.0.0",
      "version_note": "初始发布版本",
      "status": "normal",
      "release_time": 1787901244802,
      "creator": "admin",
      "creator_id": "admin"
    }
  ]
}
```

---

## 9. 导入智能体

**功能介绍**

该接口用于将导出的智能体配置文件导入到当前项目中，快速创建智能体应用。

**URI**

```
POST /v1/{project_id}/agent-manager/agents/import?workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |

**Query 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| workspace_id | 是 | String | 工作空间 ID |
| import_agents | 否 | String | 是否导入智能体，传 `true` 时启用 |
| import_tools | 否 | String | 是否导入插件，传 `true` 时启用 |
| import_workflows | 否 | String | 是否导入工作流，传 `true` 时启用 |
| mode | 否 | String | 导入模式：`STRICT`（严格模式）/ `SPACIOUS`（宽松模式），默认 `STRICT` |

> **注意**：建议同时传 `import_agents=true`、`import_tools=true`、`import_workflows=true`，否则可能返回 500 内部错误。

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| Content-Type | 是 | String | `multipart/form-data` |
| X-Auth-Token | 是 | String | 用户 Token |

**请求 Body 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| file | 是 | File | 导出的智能体配置文件（`.jsonl` 格式，multipart 上传） |

**响应参数**

| 参数 | 类型 | 描述 |
|------|------|------|
| succeed_len | Integer | 成功导入数量 |
| count | Integer | 总数量 |
| succeed_ids | Array of String | 成功导入的 ID 列表 |
| failed_len | Integer | 失败数量 |
| imported_len | Integer | 新导入数量 |
| updated_len | Integer | 更新数量 |
| skipped_len | Integer | 跳过数量 |
| failed_ids | Array of String | 失败的 ID 列表 |
| import_list | Array | 导入详情列表 |

**请求示例**

```
POST /v1/{project_id}/agent-manager/agents/import?workspace_id={workspace_id}&import_agents=true&import_tools=true&import_workflows=true&mode=SPACIOUS HTTP/1.1
Host: api.example.com
Content-Type: multipart/form-data
X-Auth-Token: {token}

file=@agent_config.jsonl
```

**响应示例**

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

## 10. 导出智能体

**功能介绍**

该接口用于导出指定智能体应用的配置文件，便于迁移或备份。

**URI**

```
POST /v1/{project_id}/agent-manager/agents/export?workspace_id={workspace_id}
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
| agent_ids | 是 | Array of String | 要导出的智能体 ID 列表 |

**响应参数**

该接口返回二进制文件流（`Content-Type: application/octet-stream`），通过 `Content-Disposition` 头指定文件名（如 `agents.jsonl`）。

**请求示例**

```
POST /v1/{project_id}/agent-manager/agents/export?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "agent_ids": ["7c5be653-71b8-48e7-9058-7191ec0f44e8"]
}
```

**响应示例**

```
HTTP/1.1 200 OK
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="agents.jsonl"

<二进制文件内容>
```

---
