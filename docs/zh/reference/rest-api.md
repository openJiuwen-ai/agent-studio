# REST API 参考指南

## 目录

1. [API 概览](#1-api-概览)
2. [请求格式](#2-请求格式)
3. [响应格式](#3-响应格式)
4. [示例](#4-示例)
5. [附录](#5-附录)

## 1. API 概览

OpenJiuwen 的接口分为管理面（Manager）和运行时（Runtime）两部分，各自的 OpenAPI 接口定义文件如下。可使用任意支持 OpenAPI 3.1 规范的工具打开 YAML 文件进行浏览。

### 管理面 API（Manager）

涵盖智能体管理、工作流管理、知识库管理、插件管理、MCP 服务管理、工作空间管理、提示词工程、模型管理等功能模块的完整接口。

> **[Manager 接口定义 →](../../api/studio-manager/openapi.yaml)**

| 模块 | Controller | 说明 |
|------|-----------|------|
| 单智能体 | agent-management-api-controller | 智能体创建、修改、删除、查询、调用、版本管理、导入导出 |
| 工作流 | workflow-management-api-controller, workflow-runtime-api-controller | 工作流 CRUD、调用、版本管理、异步任务管理 |
| 多智能体 | complex-intent-management-api-controller | 多智能体对话执行记录查询 |
| 插件/工具 | plugin-api-controller, tool-management-api-controller | 插件/工具管理 |
| MCP 服务 | mcp-server-manager-api-controller, mcp-service-manager-api-controller | MCP 服务管理 |
| 知识库 | knowledge-repo-management-api-controller, knowledge-file-management-api-controller, knowledge-faq-management-api-controller | 知识库管理、文件管理、FAQ 管理 |
| 工作空间 | workspace-api-controller, work-space-member-api-controller | 空间管理、成员管理 |
| 提示词工程 | prompt-engineer-api-controller, prompt-library-api-controller | 提示词优化、管理 |
| 模型服务 | model-service-mgmt-api-controller, provider-mgmt-api-controller | 模型服务管理、服务商管理 |
| 异步任务 | task-management-api-controller | 异步任务管理 |
| 其他 | auth-controller, health-api-controller, release-management-api-controller 等 | 认证、健康检查、发布管理等 |

### 运行时 API（Runtime）

涵盖对话执行、推理、知识库检索等运行时接口。

> **[Runtime 接口定义 →](../../api/studio-runtime/openapi.yaml)**

| 模块 | API Tag | 说明 |
|------|---------|------|
| 应用执行 | app_run | 工作流对话、智能体对话（单/多智能体）、单节点调试执行 |
| 网页调用 | web_run | 通过 short_code 调用已发布的工作流/智能体 |
| IR 执行 | execution_app | IR 直接执行、单组件调试、健康检查 |
| 会话变量 | conversation_variable | 会话全局变量读写 |
| 记忆管理 | memory-internal | 记忆仓库增删查搜 |
| 知识库 | openjiuwen_kb | 知识库创建、文档上传、检索、删除 |
| 内部工具 | inner_tools | 文件解析、文档生成 |
| 发布管理 | release | 应用发布信息写入与删除 |

## 2. 请求格式

### 2.1 请求 URI

请求 URI 由如下部分组成：

```
{URI-scheme}://{Endpoint}/{resource-path}?{query-string}
```

| 组成部分 | 说明 |
|----------|------|
| URI-scheme | 协议，支持 HTTP 和 HTTPS，默认 HTTP |
| Endpoint | 服务地址，格式为 IP:端口。获取方式见 [5.3 获取终端节点](#53-获取终端节点) |
| resource-path | 资源路径，即各接口的具体路径，可在 [Manager 接口定义](../../api/studio-manager/openapi.yaml) 或 [Runtime 接口定义](../../api/studio-runtime/openapi.yaml) 中查看 |
| query-string | 查询参数（可选），多个参数以 `&` 连接，如 `version=latest&workspace_id=xxx` |

> **说明**：
> - `project_id`：Manager 和 Runtime 服务的所有接口路径均包含此路径参数（必选）。获取方式见 [5.4 获取项目 ID](#54-获取项目-id)。
> - `workspace_id`：Manager 服务的部分接口需要通过查询参数传递，Runtime 服务为可选。获取方式见 [5.5 获取工作空间 ID](#55-获取工作空间-id)。

### 2.2 请求方法

| 方法 | 说明 |
|------|------|
| GET | 请求服务器返回指定资源 |
| POST | 请求服务器新增资源或执行特殊操作 |
| PUT | 请求服务器更新指定资源 |
| DELETE | 请求服务器删除指定资源 |

### 2.3 公共请求头

以下为 OpenJiuwen API 的公共请求头：

| 请求头 | 必选 | 说明 |
|--------|------|------|
| Content-Type | 是 | 消息体类型，默认 `application/json` |
| X-Auth-Token | 是 | 用户 Token，用于身份认证。获取方式见 [5.6 获取 Token](#56-获取-token) |
| stream | 否 | 是否使用流式响应，仅 Runtime 对话类接口适用。默认为流式响应，设为 `false` 时返回非流式 JSON 响应 |

## 3. 响应格式

### 3.1 成功响应

请求成功时，HTTP 状态码返回 `200`（或 `201` 用于创建类操作），响应体为 JSON 格式。各接口的具体响应结构见 [Manager 接口定义](../../api/studio-manager/openapi.yaml) 或 [Runtime 接口定义](../../api/studio-runtime/openapi.yaml)。

### 3.2 流式响应

当请求头中未设置 `stream` 或设为 `true` 时，API 以 SSE（Server-Sent Events） 格式返回响应。响应以 `data:` 前缀的文本行分块推送，每行为一个 JSON 片段，适用于对话、推理等需要实时输出结果的场景。

格式示例：

```
data: {"event": "message", "data": {"answer": "你好"}, "createdTime": 1719532800000, "executionId": "xxx", "isStructMessage": false}

data: {"event": "done", "data": {}, "createdTime": 1719532800001, "executionId": "xxx", "isStructMessage": false}
```

| 字段 | 说明 |
|------|------|
| event | 事件类型，如 `start`（开始）、`message`（正文回复）、`done`（结束）、`error`（错误）等 |
| data | 事件数据，内容取决于事件类型 |
| createdTime | 创建时间戳（毫秒） |
| executionId | 执行 ID |
| isStructMessage | 是否为结构化消息，默认为 `false` |
| index | 节点索引（可选） |

### 3.3 错误响应

请求失败时，HTTP 状态码为 `4xx` 或 `5xx`，响应体包含错误信息：

```json
{
  "error_code": "openjiuwen.03001001",
  "error_msg": "Input parameter is invalid.",
  "error_reason": "name不能为空",
  "error_suggestion": "请提供name参数",
  "details": [
    {
      "error_code": "...",
      "error_msg": "..."
    }
  ]
}
```

| 字段 | 必选 | 说明 |
|------|------|------|
| error_code | 是 | 错误码，用于精确定位错误类型 |
| error_msg | 是 | 错误消息，简要描述错误原因 |
| error_reason | 否 | 错误原因，详细说明 |
| error_suggestion | 否 | 修复建议 |
| details | 否 | 错误详情列表，每个元素包含 `error_code` 和 `error_msg`（仅 Manager 返回） |

具体的错误码和处理措施请参考 [5.2 错误码](#52-错误码)。

## 4. 示例

以初始化工作空间接口为例，展示完整的请求与响应：

请求：

```bash
curl -X POST "https://{manager_host}:{manager_port}/v1/0/agent-manager/workspace/init" \
  -H "X-Auth-Token: testUser|0"
```

响应：

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

## 5. 附录

### 5.1 常用状态码

下表列出 OpenJiuwen API 可能返回的 HTTP 状态码：

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 201 | 资源创建成功 |
| 400 | 请求参数非法或格式错误 |
| 401 | 认证信息不正确或缺失 |
| 403 | 请求被拒绝访问（权限不足或超出配额） |
| 404 | 请求的资源不存在 |
| 422 | 请求格式正确，但存在语义错误 |
| 429 | 请求频率超出限制 |
| 500 | 服务端内部错误 |
| 502 | 网关错误 |
| 503 | 服务暂时不可用 |
| 504 | 网关超时 |

### 5.2 错误码

#### 智能体相关

| 状态码 | 错误码 | 错误信息 | 描述 | 处理措施 |
|--------|--------|----------|------|----------|
| 403 | openjiuwen.02101016 | Insufficient execution permissions for Agent | 当前用户无权在指定项目中运行该智能体应用 | 确认用户拥有该应用的执行权限 |
| 400 | openjiuwen.02101032 | Current Agent version does not exist | 指定的智能体版本不存在 | 确认智能体 ID 和版本信息正确 |
| 403 | openjiuwen.02001017 | API call count for Agent exceeds quota | 智能体 API 调用次数已用完 | 升级套餐 |
| 404 | openjiuwen.02101007 | Agent does not exist | 智能体应用未找到或已删除 | 确认应用是否存在 |

#### 工作流相关

| 状态码 | 错误码 | 错误信息 | 描述 | 处理措施 |
|--------|--------|----------|------|----------|
| 400 | openjiuwen.02201005 | Workflow information validation failed | 工作流信息校验失败 | 检查工作流配置是否完整有效 |
| 403 | openjiuwen.02201020 | Insufficient workflow execution permissions | 当前 projectId 与工作流所属 projectId 不一致 | 确保 projectId 一致 |
| 404 | openjiuwen.02201004 | Workflow does not exist | 工作流未找到或已删除 | 确认工作流是否存在 |
| 500 | openjiuwen.02201001 | Workflow import failed | 工作流导入失败 | 检查导入文件格式 |
| 500 | openjiuwen.02201003 | Workflow node execution failed | 工作流节点执行异常 | 检查节点配置 |

#### 知识库相关

| 状态码 | 错误码 | 错误信息 | 描述 | 处理措施 |
|--------|--------|----------|------|----------|
| 400 | openjiuwen.03002106 | Operation failed | 外部知识库不支持文件下载 | 检查第三方知识库连接 |
| 400 | openjiuwen.03003039 | Operation failed | 未找到图片或图片已过期 | 稍后重试 |
| 403 | openjiuwen.03001021 | Operation failed | 下载的文件为空 | 检查并重试 |
| 404 | openjiuwen.03001003 | resource not exist | 资源不存在 | 联系技术支持 |
| 404 | openjiuwen.03002010 | Can not retrieve in knowledge base | 知识已被删除或关闭 | 检查知识状态 |
| 500 | openjiuwen.03002019 | Operation failed | 未找到文件或文件已过期 | 检查后重试 |
| 500 | openjiuwen.03002104 | Query third party knowledgeBases error | 第三方知识库连接信息错误 | 检查连接信息后重试 |

#### 通用

| 状态码 | 错误码 | 错误信息 | 描述 | 处理措施 |
|--------|--------|----------|------|----------|
| 400 | openjiuwen.03001001 | Input parameter is invalid | 输入参数无效 | 检查输入参数 |
| 500 | openjiuwen.03000000 | System internal error | 系统内部错误 | 联系技术支持 |

### 5.3 获取终端节点

终端节点即调用 API 的服务地址，格式为 IP:端口。OpenJiuwen 包含两个服务：

| 服务 | 说明 | 获取方式 |
|------|------|----------|
| Manager | 管理面服务，用于智能体/工作流管理、认证等 | 平台部署时配置的 Manager 服务地址 |
| Runtime | 运行时服务，用于对话执行、推理等 | 从控制台已发布应用的「查看 API」页面获取 |

### 5.4 获取项目 ID

从控制台获取项目 ID：

1. 进入 OpenJiuwen 智能体开发平台。
2. 在左侧导航，选择「开发中心 > 智能体管理」，选择「单智能体」、「工作流」或「多智能体」。
3. 单击已发布的应用卡片，进入编辑页面，选择「渠道管理」。
4. 在「调用方式」区域，单击「查看 API」。
5. 在「API 详情」页面，「请求结构」区域查看 project_id，v1 后面的字符串为 project_id。

![获取项目 ID](../../images/getProjectId.png)

### 5.5 获取工作空间 ID

#### 方法一：通过 API 获取

初始化个人工作空间，接口会自动创建个人空间（如不存在）并返回工作空间列表，响应中包含工作空间 ID（`id` 字段）：

```
POST /v1/{project_id}/agent-manager/workspace/init
```

响应示例：

```json
{
  "count": 1,
  "workspaceList": [
    {
      "id": "xxx",
      "name": "个人空间"
    }
  ]
}
```

#### 方法二：从控制台获取

1. 进入 OpenJiuwen 智能体开发平台。
2. 打开浏览器开发者工具（按 F12），切换到「Network」页签。
3. 在页面中执行任意操作（如切换「个人空间」），在 Network 请求中查找 `workspace_id=xxx` 参数，xxx 即为工作空间 ID。

### 5.6 获取 Token

Token 用于 API 请求的身份认证，格式为 `userId|projectId`。开源默认配置中，默认用户为 `testUser`，默认项目为 `0`，可直接使用 `testUser|0` 作为 Token：

```
X-Auth-Token: testUser|0
```

也可调用 `GET http://{manager_host}:{manager_port}/auth/token?user_id={user_id}&project_id={project_id}` 获取 Token（该端点需直接访问 Manager 服务端口，如 31111）。
