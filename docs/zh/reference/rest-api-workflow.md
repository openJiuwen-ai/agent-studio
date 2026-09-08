# 工作流 API

---

## 目录

1. [创建工作流](#1-创建工作流)
2. [修改工作流](#2-修改工作流)
3. [删除工作流](#3-删除工作流)
4. [查询工作流列表](#4-查询工作流列表)
5. [调用工作流应用](#5-调用工作流应用)
6. [发布工作流版本](#6-发布工作流版本)
7. [获取工作流版本列表](#7-获取工作流版本列表)
8. [导入工作流](#8-导入工作流)
9. [导出工作流](#9-导出工作流)
10. [解析导入文件](#10-解析导入文件)

---

## 1. 创建工作流

**功能介绍**

该接口用于在指定项目中创建一个新的工作流应用。

**URI**

```
POST /v1/{project_id}/agent-manager/workflows?workspace_id={workspace_id}
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
| name | 是 | String | 工作流名称，长度 2-64 字符 |
| code | 是 | String | 工作流英文标识，需唯一，长度 2-64 字符 |
| description | 否 | String | 工作流描述，长度 1-1024 字符 |
| type | 是 | String | 工作流类型：`chat`（对话型）或 `task`（任务型） |

**响应参数**

状态码：200

| 参数 | 类型 | 描述 |
|------|------|------|
| workflow_id | String | 创建的工作流 ID |

**状态码**

| 状态码 | 描述 |
|--------|------|
| 200 | 创建成功 |
| 400 | 请求参数无效 |
| 403 | 没有操作权限 |
| 500 | 服务内部错误 |

**请求示例**

```
POST /v1/{project_id}/agent-manager/workflows?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "name": "知识库问答工作流",
  "code": "workflow_code",
  "description": "基于知识库检索的问答工作流",
  "type": "chat"
}
```

**响应示例**

```json
{
  "workflow_id": "cd7a8f33-66e3-455c-b008-a6b18dd27319"
}
```

---

## 2. 修改工作流

**功能介绍**

该接口用于修改指定工作流应用的配置信息。

**URI**

```
PUT /v1/{project_id}/agent-manager/workflows/{workflow_id}?workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |
| workflow_id | 是 | String | 工作流 ID |

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
| name | 否 | String | 工作流名称 |
| description | 否 | String | 工作流描述 |

**响应参数**

状态码：200

该接口成功响应无返回体。

**状态码**

| 状态码 | 描述 |
|--------|------|
| 200 | 修改成功 |
| 400 | 请求参数无效 |
| 403 | 没有操作权限 |
| 404 | 工作流不存在 |
| 500 | 服务内部错误 |

**请求示例**

```
PUT /v1/{project_id}/agent-manager/workflows/{workflow_id}?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "name": "知识库问答工作流-更新",
  "description": "更新后的描述"
}
```

---

## 3. 删除工作流

**功能介绍**

该接口用于删除指定的工作流应用。

**URI**

```
DELETE /v1/{project_id}/agent-manager/workflows/{workflow_id}?workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |
| workflow_id | 是 | String | 工作流 ID |

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
| id | String | 被删除的工作流 ID |

**状态码**

| 状态码 | 描述 |
|--------|------|
| 200 | 删除成功 |
| 403 | 没有操作权限 |
| 404 | 工作流不存在 |
| 500 | 服务内部错误 |

**请求示例**

```
DELETE /v1/{project_id}/agent-manager/workflows/{workflow_id}?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**响应示例**

```json
{
  "id": "cd7a8f33-66e3-455c-b008-a6b18dd27319"
}
```

---

## 4. 查询工作流列表

**功能介绍**

该接口用于查询当前项目下的工作流列表。

**URI**

```
GET /v1/{project_id}/agent-manager/workflows?workspace_id={workspace_id}
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
| count | Integer | 工作流总数 |
| workflow_list | Array of Workflow | 工作流列表 |

**Workflow**

| 参数 | 类型 | 描述 |
|------|------|------|
| workflow_id | String | 工作流 ID |
| name | String | 工作流名称 |
| description | String | 工作流描述 |
| status | String | 工作流状态 |
| create_time | Long | 创建时间 |
| update_time | Long | 更新时间 |

**请求示例**

```
GET /v1/{project_id}/agent-manager/workflows?workspace_id={workspace_id}&page=1&page_size=10 HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**响应示例**

```json
{
  "count": 1,
  "workflow_list": [
    {
      "workflow_id": "cd7a8f33-66e3-455c-b008-a6b18dd27319",
      "name": "知识库问答工作流",
      "description": "基于知识库检索的问答工作流",
      "status": "published",
      "create_time": 1735558575017,
      "update_time": 1735558575017
    }
  ]
}
```

---

## 5. 调用工作流应用

**功能介绍**

该接口用于运行场景化应用，支持在指定的项目、工作流和对话上下文中执行工作流逻辑。接口支持流式响应模式。

**适用场景**

- 在项目中运行预定义的工作流
- 支持调试模式和发布模式
- 支持流式响应，适用于需要实时反馈的场景

**URI**

```
POST /v1/{project_id}/agent-manager/workflows/chat/{short_code}/conversations/{conversation_id}?workspace_id={workspace_id}
```

也可不指定 `conversation_id`，由系统自动生成：

```
POST /v1/{project_id}/agent-manager/workflows/chat/{short_code}?workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |
| short_code | 是 | String | 工作流发布版本号（short_code） |
| conversation_id | 否 | String | 会话 ID，每个会话的唯一标识符 |

**Query 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| workspace_id | 是 | String | 工作空间 ID |

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| X-Auth-Token | 是 | String | 用户 Token |
| X-Invoke-Mode | 否 | String | 运行模式：`debug`（调试模式）或 `published`（发布模式），默认 `published` |
| stream | 否 | Boolean | 是否开启流式调用，默认 `true` |
| X-Request-Id | 否 | String | 调用链 ID |
| Content-Type | 是 | String | 发送的实体的 MIME 类型，默认 `application/json` |

**请求 Body 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| inputs | 是 | Map<String,Object> | 用户提出的问题，作为运行工作流的输入 |
| plugin_configs | 否 | Array of PluginConfig | 插件配置信息 |

**PluginConfig**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| plugin_id | 否 | String | 插件 ID |
| config | 否 | Map<String,String> | 配置插件信息 |

**响应参数**

状态码：200

| 参数 | 类型 | 描述 |
|------|------|------|
| event | String | 事件类型 |
| data | data object | 工作流助手回复内容 |
| createdTime | Long | 消息块返回的时间戳 |

**data**

| 参数 | 类型 | 描述 |
|------|------|------|
| text | String | 工作流输出内容消息块 |
| index | Integer | 消息块索引 |
| node_id | String | 节点 ID |
| node_type | String | 节点类型 |
| node_name | String | 节点名称 |
| workflow_id | String | 工作流 ID |
| workflow_name | String | 工作流名称 |
| createdTime | Long | 创建时间 |

**状态码**

| 状态码 | 描述 |
|--------|------|
| 200 | 成功响应 |
| 500 | 错误响应 |

**请求示例**

```
POST /v1/{project_id}/agent-manager/workflows/chat/{short_code}/conversations/{conversation_id}?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}
stream: true

{
  "inputs": {
    "query": "你好"
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

**响应示例**

成功响应（状态码：200）：

```json
{
  "event": "message",
  "data": {
    "text": null,
    "index": 11,
    "node_id": "node_end",
    "node_type": "End",
    "node_name": "结束",
    "workflow_id": "cd7a8f33-66e3-455c-b008-a6b18dd27319",
    "workflow_name": "flowouttest",
    "createdTime": 1760169416635
  },
  "createdTime": 1760169416635
}
```

错误响应（状态码：500）：

```json
{
  "event": "error",
  "data": {
    "text": null,
    "index": 11,
    "node_id": "node_end",
    "node_type": "End",
    "node_name": "结束",
    "code": "101563",
    "message": "执行报错，错误码：101563，错误信息：Get model streaming output error",
    "workflow_id": "cd7a8f33-66e3-455c-b008-a6b18dd27319",
    "workflow_name": "flowouttest",
    "createdTime": 1760169416635
  },
  "createdTime": 1760169416635
}
```

---

## 6. 发布工作流版本

**功能介绍**

该接口用于发布指定工作流应用的新版本，创建工作流 DSL 和 IR 文件的版本快照，校验工作流配置，并返回发布的版本 ID。

**适用场景**

- 将工作流应用的当前配置发布为一个新的版本
- 在发布前自动校验工作流配置的有效性
- 为工作流应用创建版本快照，便于后续回滚或管理

**URI**

```
POST /v1/{project_id}/agent-manager/workflows/{workflow_id}/versions?workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 租户项目 ID，长度不超过 64 字符，仅支持字母、数字、下划线和连字符 |
| workflow_id | 是 | String | 工作流 ID，长度不超过 64 字符，仅支持字母、数字、下划线和连字符 |

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

| 参数 | 类型 | 描述 |
|------|------|------|
| version_id | String | 发布的版本 ID |

状态码：400 / 401 / 403 / 404 / 500

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
| 200 | 发布成功 |
| 400 | 请求错误，如参数无效、版本名称已存在或工作流校验失败 |
| 401 | 鉴权失败 |
| 403 | 没有操作权限 |
| 404 | 找不到资源 |
| 500 | 服务内部错误，如工作流不存在 |

**请求示例**

```
POST /v1/{project_id}/agent-manager/workflows/{workflow_id}/versions?workspace_id={workspace_id} HTTP/1.1
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

```json
"1783341175105"
```

错误响应（状态码：400）：

```json
{
  "error_msg": "The version name already existed."
}
```

---

## 7. 获取工作流版本列表

**功能介绍**

该接口用于获取指定工作流应用的版本列表。

**URI**

```
GET /v1/{project_id}/agent-manager/workflows/{workflow_id}/versions?workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |
| workflow_id | 是 | String | 工作流 ID |

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
| status | String | 版本状态 |
| release_time | Long | 发布时间 |

**请求示例**

```
GET /v1/{project_id}/agent-manager/workflows/{workflow_id}/versions?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**响应示例**

```json
{
  "count": 1,
  "version_list": [
    {
      "version_id": "1783341175105",
      "version_name": "v1.0.0",
      "version_note": "初始发布版本",
      "status": "normal",
      "release_time": 1783341175105
    }
  ]
}
```

---

## 8. 导入工作流

**功能介绍**

该接口用于将导出的工作流配置文件导入到当前项目中，快速创建工作流应用。

**URI**

```
POST /v1/{project_id}/agent-manager/workflows/import?workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |

**Query 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| workspace_id | 是 | String | 工作空间 ID |
| import_workflows | 否 | String | 是否导入工作流，传 `true` 时启用 |
| import_tools | 否 | String | 是否导入插件，传 `true` 时启用 |
| mode | 否 | String | 导入模式：`STRICT`（严格模式）/ `SPACIOUS`（宽松模式），默认 `STRICT` |

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| Content-Type | 是 | String | `multipart/form-data` |
| X-Auth-Token | 是 | String | 用户 Token |

**请求 Body 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| file | 是 | File | 导出的工作流配置文件（`.jsonl` 格式，multipart 上传） |

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
POST /v1/{project_id}/agent-manager/workflows/import?workspace_id={workspace_id}&import_workflows=true&import_tools=true&mode=SPACIOUS HTTP/1.1
Host: api.example.com
Content-Type: multipart/form-data
X-Auth-Token: {token}

file=@workflow_config.jsonl
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

## 9. 导出工作流

**功能介绍**

该接口用于导出指定工作流应用的配置文件，便于迁移或备份。

**URI**

```
POST /v1/{project_id}/agent-manager/workflows/export?workspace_id={workspace_id}
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
| workflow_ids | 是 | Array of String | 要导出的工作流 ID 列表 |

**响应参数**

该接口返回二进制文件流（`Content-Type: application/octet-stream`），通过 `Content-Disposition` 头指定文件名（如 `workflows.jsonl`）。

**请求示例**

```
POST /v1/{project_id}/agent-manager/workflows/export?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "workflow_ids": ["cd7a8f33-66e3-455c-b008-a6b18dd27319"]
}
```

**响应示例**

```
HTTP/1.1 200 OK
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="workflows.jsonl"

<二进制文件内容>
```

---

## 10. 解析导入文件

**功能介绍**

该接口用于解析并转换第三方工作流配置文件（目前支持 Dify 格式），返回解析后的工作流信息，便于在导入前预览内容。

**URI**

```
POST /v1/{project_id}/agent-manager/workflows/import/parse?type={type}&workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |

**Query 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| type | 是 | String | 第三方工作流类型，目前仅支持 `Dify` |
| workspace_id | 是 | String | 工作空间 ID |

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| Content-Type | 是 | String | `multipart/form-data` |
| X-Auth-Token | 是 | String | 用户 Token |

**请求 Body 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| file | 是 | File | 待解析的 Dify 格式工作流配置文件（multipart 上传） |

**响应参数**

| 参数 | 类型 | 描述 |
|------|------|------|
| workflow_id | String | 工作流 ID |
| name | String | 工作流名称 |
| code | String | 工作流英文标识 |
| description | String | 工作流描述 |
| avatar | String | 工作流图标 |
| status | Integer | 工作流状态 |
| workflow_details | Object | 工作流详细配置信息 |
| trigger_list | Array | 触发器配置列表 |

**请求示例**

```
POST /v1/{project_id}/agent-manager/workflows/import/parse?type=Dify&workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: multipart/form-data
X-Auth-Token: {token}

file=@dify_workflow.yml
```

**响应示例**

```json
{
  "name": "知识库问答工作流",
  "code": "kb-qa-workflow",
  "description": "基于知识库检索的问答工作流",
  "workflow_details": {
    "nodes": [],
    "edges": []
  }
}
```

---
