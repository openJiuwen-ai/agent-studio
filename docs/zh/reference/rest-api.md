# API 接口规范

---

## 目录

1. [使用前必读](#1-使用前必读)
2. [API 概览](#2-api-概览)
3. [如何调用 API](#3-如何调用-api)
4. [应用示例](#4-应用示例)
5. [附录](#5-附录)

---

## 1. 使用前必读

欢迎使用 OpenJiuwen 服务。OpenJiuwen 服务是一个一站式企业级智能体构建平台，包含应用管理、组件库、知识库、提示词开发、配置管理、模型接入调测等功能模块，覆盖体验设计、代码开发、应用运行、资产管理、数据处理、测试发布、运营监控、安全保障八大面，为企业级用户提供开箱即用的大模型应用开发工具链。

您可以使用本文档提供的 API 对 OpenJiuwen 进行相关操作，如调用应用、调用工作流等。

### 终端节点

终端节点即调用 API 的请求地址，不同区域的终端节点不同，获取方法如下：

1. 进入 OpenJiuwen 智能体开发平台
2. 在左侧导航，选择「开发中心 > 智能体管理」，选择「单智能体」、「工作流」或「多智能体」
3. 单击已发布的单智能体应用、工作流应用或多智能体应用卡片，进入编辑页面，选择「渠道管理」
4. 在「调用方式」区域，单击「查看API」
5. 在「API详情」页面，查看 URL 地址，IP 地址:端口号即为 API 的请求地址

---

## 2. API 概览

按照前端二级菜单功能模块划分，各模块 API 详情请点击对应链接：

### 开发中心

| 模块 | 接口数量 | 说明 | 文档链接 |
|------|----------|------|----------|
| 单智能体 | 10 | 智能体创建、修改、删除、查询、调用、版本管理、导入导出 | [查看详情](rest-api-single-agent.md) |
| 工作流 | 10 | 工作流创建、修改、删除、查询、调用、版本管理、导入导出、解析导入文件 | [查看详情](rest-api-workflow.md) |
| 多智能体 | 2 | 多智能体对话执行记录查询、对话详情查询 | [查看详情](rest-api-multi-agent.md) |

### 组件库

| 模块 | 接口数量 | 说明 | 文档链接 |
|------|----------|------|----------|
| 插件 | 4 | 插件列表查询、导出、修改、删除 | [查看详情](rest-api-plugin.md) |
| MCP 服务 | 5 | MCP 服务列表查询、汇总统计、部署、删除、修改 | [查看详情](rest-api-mcp.md) |
| 知识库 | 3 | 知识库检索、获取检索图片、文件下载 | [查看详情](rest-api-knowledge-base.md) |

### 其他

| 模块 | 接口数量 | 说明 | 文档链接 |
|------|----------|------|----------|
| 工作空间 | 16 | 空间 CRUD、查询、成员管理、角色管理、资源分享 | [查看详情](rest-api-workspace.md) |
| 文件管理 | 1 | 文件上传 | [查看详情](rest-api-file.md) |

---

## 3. 如何调用 API

### 3.1 构造请求

#### 请求 URI

请求 URI 由如下部分组成：
```
{URI-scheme}://{Endpoint}/{resource-path}?{query-string}
```

- **URI-scheme**: 表示用于传输请求的协议，支持 HTTP 和 HTTPS 协议
- **Endpoint**: 指定承载 REST 服务端点的服务器域名或 IP，如 `100.85.147.133`
- **resource-path**: 资源路径，也即 API 访问路径
- **query-string**: 查询参数，是可选部分

#### 请求方法

| 方法 | 说明 |
|------|------|
| GET | 请求服务器返回指定资源 |
| PUT | 请求服务器更新指定资源 |
| POST | 请求服务器新增资源或执行特殊操作 |
| DELETE | 请求服务器删除指定资源 |
| HEAD | 请求服务器资源头部 |
| PATCH | 请求服务器更新资源的部分内容 |

#### 请求消息头

公共消息头需要添加到请求中：

| 消息头 | 必选 | 说明 |
|--------|------|------|
| Content-Type | 是 | 消息体的类型，默认取值为 `application/json` |
| X-Auth-Token | 是 | 用户 Token，用于用户身份认证 |

### 3.2 认证鉴权

#### 获取 Token

调用以下接口获取用户 Token：

```
GET http://{manager_host}:{manager_port}/auth/token?user_id={user_id}&project_id={project_id}
```

> **注意**：`/auth/token` 端点由 Manager 服务直接提供，需直接访问 Manager 服务端口（如 31111），不经过 Nginx 代理。

**请求参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| user_id | 是 | String | 用户 ID，如 `admin` |
| project_id | 是 | String | 项目 ID，如 `default` |

**响应示例**

```json
{
  "auth_token": "admin|default"
}
```

#### 使用 Token

在后续 API 请求中，将获取的 Token 值通过 `X-Auth-Token` 请求头传递：

```
X-Auth-Token: admin|default
```

Token 格式为 `userId|projectId`。

#### 工作空间 ID

大多数 API 需要 `workspace_id` 作为查询参数。可通过以下步骤获取工作空间 ID：

1. 调用 `POST /v1/{project_id}/agent-manager/workspace/init` 初始化个人工作空间
2. 调用 `GET /v1/{project_id}/agent-manager/workspace?workspace_id={workspace_id}` 查询工作空间列表

### 3.3 返回结果

#### 状态码

状态码是一组从 1xx 到 5xx 的数字代码，表示请求响应的状态

#### 响应消息体

当接口调用出错时，会返回错误码及错误信息说明：

```json
{
  "error_msg": "Request body is invalid."
}
```

---

## 4. 应用示例

### 4.1 调用工作流应用示例

**操作场景**

该接口用于运行场景化应用，支持在指定的项目、工作流和对话上下文中执行工作流逻辑。

**前提条件**

您需要规划 OpenJiuwen 所在的区域信息，并根据区域确定调用 API 的 Endpoint。

**调用工作流**

```
POST https://1.2.3.4/v1/12345/agent-manager/workflows/chat/{short_code}/conversations/{conversation_id}?workspace_id={workspace_id}
```

**请求头**

```
Content-Type: application/json
X-Auth-Token: {token}
stream: true
```

**请求体**

```json
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

**参数说明**

- `endpoint`: 终端节点
- `project_id`: 当前项目 ID
- `short_code`: 工作流发布版本号
- `conversation_id`: 会话 ID，每个会话的唯一标识符，字符串长度为 1~64 个字符，支持英文字母、数字、中划线、下划线

---

### 4.2 调用智能体应用示例

**操作场景**

该接口用于运行知识型智能体应用（单智能体应用、多智能体应用）。

**前提条件**

您需要规划 OpenJiuwen 所在的区域信息，并根据区域确定调用 API 的 Endpoint。

**调用应用**

```
POST https://1.2.3.4/v1/074cabeea7800f622f0ec010bffa6c59/agent-manager/agents/chat/{short_code}/conversations/{conversation_id}?workspace_id={workspace_id}
```

**请求头**

```
Content-Type: application/json
X-Auth-Token: {token}
stream: true
```

**请求体**

```json
{
  "inputs": {
    "query": "查询A12会议室在9:00到10:00的状态"
  }
}
```

**参数说明**

- `endpoint`: 终端节点
- `project_id`: 当前项目 ID
- `short_code`: 智能体发布版本号
- `conversation_id`: 会话 ID

---

## 5. 附录

### 5.1 状态码

| 状态码 | 编码 | 说明 |
|--------|------|------|
| 100 | Continue | 继续请求 |
| 101 | Switching Protocols | 切换协议 |
| 200 | OK | 服务器已成功处理了请求 |
| 201 | Created | 创建类的请求完全成功 |
| 202 | Accepted | 已经接受请求，但未处理完成 |
| 203 | Non-Authoritative Information | 非授权信息，请求成功 |
| 204 | No Content | 请求完全成功，HTTP 响应不包含响应体 |
| 205 | Reset Content | 重置内容，服务器处理成功 |
| 206 | Partial Content | 服务器成功处理了部分 GET 请求 |
| 300 | Multiple Choices | 多种选择 |
| 301 | Moved Permanently | 资源被永久移动 |
| 302 | Found | 资源被临时移动 |
| 303 | See Other | 查看其它地址 |
| 304 | Not Modified | 所请求的资源未修改 |
| 305 | Use Proxy | 所请求的资源必须通过代理访问 |
| 400 | Bad Request | 非法请求 |
| 401 | Unauthorized | 认证信息不正确或非法 |
| 402 | Payment Required | 保留请求 |
| 403 | Forbidden | 请求被拒绝访问 |
| 404 | Not Found | 所请求的资源不存在 |
| 405 | Method Not Allowed | 请求中带有该资源不支持的方法 |
| 406 | Not Acceptable | 服务器无法根据客户端请求的内容特性完成请求 |
| 407 | Proxy Authentication Required | 请求要求代理的身份认证 |
| 408 | Request Time-out | 服务器等候请求时发生超时 |
| 409 | Conflict | 服务器在完成请求时发生冲突 |
| 410 | Gone | 客户端请求的资源已经不存在 |
| 411 | Length Required | 服务器无法处理客户端发送的不带 Content-Length 的请求信息 |
| 412 | Precondition Failed | 未满足前提条件 |
| 413 | Request Entity Too Large | 请求的实体过大，服务器无法处理 |
| 414 | Request-URI Too Large | 请求的 URL 过长 |
| 415 | Unsupported Media Type | 服务器无法处理请求附带的媒体格式 |
| 416 | Requested range not satisfiable | 客户端请求的范围无效 |
| 417 | Expectation Failed | 服务器无法满足 Expect 的请求头信息 |
| 422 | Unprocessable Entity | 请求格式正确，但由于含有语义错误，无法响应 |
| 429 | Too Many Requests | 请求超出了客户端访问频率的限制 |
| 500 | Internal Server Error | 服务端内部错误 |
| 501 | Not Implemented | 服务器不支持请求的功能 |
| 502 | Bad Gateway | 充当网关或代理的服务器，从远端服务器接收到了无效的请求 |
| 503 | Service Unavailable | 被请求的服务无效 |
| 504 | Server Timeout | 请求在给定的时间内无法完成 |
| 505 | HTTP Version not supported | 服务器不支持请求的 HTTP 协议的版本 |

---

### 5.2 错误码

| 状态码 | 错误码 | 错误信息 | 描述 | 处理措施 |
|--------|--------|----------|------|----------|
| 400 | OpenJiuwen.03001001 | Input parameter is invalid | 输入参数无效 | 请检查输入参数是否正确 |
| 400 | OpenJiuwen.03002106 | Operation failed | 外部知识库不支持文件下载 | 第三方知识库连接不存在 |
| 400 | OpenJiuwen.03003039 | Operation failed | 未找到图片或图片已过期 | 请稍后重试 |
| 403 | OpenJiuwen.03001021 | Operation failed | 下载的文件为空 | 请检查并重试 |
| 404 | OpenJiuwen.03001003 | resource not exist | 资源不存在 | 请联系技术支持 |
| 404 | OpenJiuwen.03002010 | Can not retrieve in knowledge base | 这些知识已被删除或关闭 | 检查这些知识的状态 |
| 500 | OpenJiuwen.03000000 | System internal error | 系统内部错误 | 请联系技术支持 |
| 500 | OpenJiuwen.03002019 | Operation failed | 未找到该文件或该文件已过期 | 检查后再重试 |
| 500 | OpenJiuwen.03002104 | Query third party knowledgeBases error | 第三方知识库连接信息错误 | 检查连接信息后重试 |
| 200 | OpenJiuwen.02101016 | Insufficient execution permissions for Agent | 当前用户无权在指定项目中运行该单智能体应用 | 确认当前用户在目标项目中拥有该单智能体应用的执行权限 |
| 200 | OpenJiuwen.100002 | validation failed | 输入参数格式不正确或缺少必要参数 | 检查请求参数是否符合接口规范 |
| 400 | OpenJiuwen.02101032 | Current Agent version does not exist | 请求中指定的 Agent 或其版本在系统中不存在，可能已被删除或未正确发布 | 确认 Agent ID 和版本信息是否正确，并确保该 Agent 已成功发布并可用 |
| 403 | OpenJiuwen.02001017 | API call count for Agent exceeds quota | 智能体 API 调用次数已用完 | 请升级套餐 |
| 403 | OpenJiuwen.02201020 | Insufficient workflow execution permissions | 当前执行请求的 projectId 与工作流所属的 projectId 不一致 | 确保当前空间中的 projectId 与工作流所属的 projectId 一致 |
| 404 | OpenJiuwen.02101007 | Agent does not exist | 请求的智能体应用未找到或已被删除 | 确认该应用是否存在 |
| 500 | OpenJiuwen.02201004 | Workflow or workflow version does not exist | 请求中的工作流 ID 在当前项目和工作区中不存在 | 确认工作流 ID 是否正确 |
| 400 | OpenJiuwen.02201001 | Version name already existed | 版本名称已存在 | 请使用不同的版本名称 |
| 400 | OpenJiuwen.02201002 | Release version size exceed limit | 发布版本数量超过上限 | 请删除不需要的旧版本后重试 |
| 400 | OpenJiuwen.02201003 | Workflow information validation failed | 工作流信息校验失败 | 请检查工作流配置是否完整有效 |
| 500 | OpenJiuwen.02201005 | Workflow does not exist | 请求的工作流未找到或已被删除 | 确认该工作流是否存在 |

---

### 5.3 获取项目 ID

从控制台获取项目 ID：

1. 进入 OpenJiuwen 智能体开发平台
2. 在左侧导航，选择「开发中心 > 智能体管理」，选择「单智能体」、「工作流」或「多智能体」
3. 单击已发布的单智能体应用、工作流应用或多智能体应用卡片，进入编辑页面，选择「渠道管理」
4. 在「调用方式」区域，单击「查看API」
5. 在「API详情」页面，「请求结构」区域查看 project_id，V1 后面的字符串为 project_id
![img.png](../../images/getProjectId.png)
---

### 5.4 获取工作空间 ID

在调用接口的时候，部分 URL 中需要填入工作空间 ID，获取方法如下：

1. 进入 OpenJiuwen 智能体开发平台
2. 打开 F12，选择「Network」，单击任意页面，例如「个人空间」
3. 可以在接口调用中看到 `workspace_id=xxx`，xxx 为工作空间 ID 的值

---
