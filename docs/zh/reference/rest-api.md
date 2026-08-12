# API 接口规范

---

## 目录

1. [使用前必读](#1-使用前必读)
2. [API 概览](#2-api-概览)
3. [如何调用 API](#3-如何调用-api)
4. [API](#4-api)
    - 4.1 [工作流/智能体](#41-工作流智能体)
    - 4.2 [知识库](#42-知识库)
5. [应用示例](#5-应用示例)
6. [附录](#6-附录)

---

## 1. 使用前必读

欢迎使用 OpenJiuwen 服务。OpenJiuwen 服务是一个一站式企业级智能体构建平台，包含应用管理、组件库、知识库、提示词开发、配置管理、模型接入调测等功能模块，覆盖体验设计、代码开发、应用运行、资产管理、数据处理、测试发布、运营监控、安全保障八大面，为企业级用户提供开箱即用的大模型应用开发工具链。

您可以使用本文档提供 API 对 OpenJiuwen 进行相关操作，如调用应用、调用工作流等。

### 终端节点

终端节点即调用 API 的请求地址，不同区域的终端节点不同，获取方法如下：

1. 进入 OpenJiuwen 智能体开发平台
2. 在左侧导航，选择「开发中心 > 智能体管理」，选择「单智能体」、「工作流」或「多智能体」
3. 单击已发布的单智能体应用、工作流应用或多智能体应用卡片，进入编辑页面，选择「渠道管理」
4. 在「调用方式」区域，单击「查看API」
5. 在「API详情」页面，查看 URL 地址，IP 地址:端口号即为 API 的请求地址

---

## 2. API 概览

| 类型 | 说明 |
|------|------|
| 工作流/智能体 | 调用工作流应用、智能体应用、上传文件接口 |
| 知识库 | 知识库检索、获取知识库检索图片、文件下载接口 |

---

## 3. 如何调用 API

### 3.1 构造请求

#### 请求 URI

请求 URI 由如下部分组成：
```
{URI-scheme}://{Endpoint}/{resource-path}?{query-string}
```

- **URI-scheme**: 表示用于传输请求的协议，当前所有 API 均采用 HTTPS 协议
- **Endpoint**: 指定承载 REST 服务端点的服务器域名或 IP，不同服务不同区域的 Endpoint 不同
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
| Authorization | 否 | 签名认证信息，使用平台 API Key 方式认证时必填 |

### 3.2 认证鉴权
- **平台 API Key 认证**: 使用平台 API Key 认证调用请求

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

## 4. API

### 4.1 工作流/智能体

#### 4.1.1 调用工作流应用

**功能介绍**

该接口用于运行场景化应用，支持在指定的项目、工作流和对话上下文中执行工作流逻辑。接口支持流式响应模式。

**适用场景**

- 在项目中运行预定义的工作流
- 支持调试模式和发布模式
- 支持流式响应，适用于需要实时反馈的场景

**URI**

```
POST /v1/{project_id}/workflows/{workflow_id}/conversations/{conversation_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |
| workflow_id | 是 | String | 工作流应用的 ID |
| conversation_id | 是 | String | 会话 ID，每个会话的唯一标识符 |

**Query 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| workspace_id | 否 | String | 工作空间 ID |
| version | 否 | String | 发布版本 |

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| X-Auth-Token | 否 | String | 用户 Token |
| X-Invoke-Mode | 否 | String | 运行模式：`debug`（调试模式）或 `published`（发布模式），默认 `published` |
| stream | 否 | Boolean | 是否开启流式调用，默认 `true` |
| Authorization | 否 | String | 平台 API Key |
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
| event | Map<String,Object> | 工作流最终输出内容 |
| data | data object | 工作流助手回复内容 |

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
| createdTime | Integer | 创建时间 |

**状态码**

| 状态码 | 描述 |
|--------|------|
| 200 | 成功响应 |
| 500 | 错误响应 |

**请求示例**

```json
{
  "method": "POST",
  "url": "https://api.example.com/v1/12345/workflows/67890/conversations/67890",
  "headers": {
    "Content-Type": "application/json",
    "stream": true
  },
  "body": {
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

#### 4.1.2 调用智能体应用

**功能介绍**

该接口用于运行知识型智能体应用，支持单智能体和多智能体，支持在指定的项目、智能体和对话上下文中执行智能体逻辑。接口支持流式响应模式。

**适用场景**

- 在项目中运行预定义的知识型智能体应用
- 支持调试模式和发布模式
- 支持流式响应，适用于需要实时反馈的场景

**URI**

```
POST /v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |
| agent_id | 是 | String | 智能体应用 ID |
| conversation_id | 是 | String | 会话 ID |

**Query 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| workspace_id | 否 | String | 工作空间 ID |
| version | 否 | String | 发布版本 |
| type | 否 | String | 执行类型：`controller`（多智能体）或 `agent`（单智能体），默认 `agent` |

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| X-Auth-Token | 否 | String | 用户 Token |
| X-Invoke-Mode | 否 | String | 运行模式：`debug` 或 `published`，默认 `published` |
| stream | 否 | Boolean | 是否开启流式调用，当前智能体应用只支持流式调用，默认 `true` |
| Authorization | 否 | String | 平台 API Key |
| X-Request-Id | 否 | String | 调用链 ID |
| Content-Type | 是 | String | 默认 `application/json` |

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

**请求示例**

```json
{
  "method": "POST",
  "url": "https://{endpoint}/v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}",
  "headers": {
    "Content-Type": "application/json",
    "stream": true
  },
  "body": {
    "query": "查询A12会议室在9:00到10:00的状态"
  }
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

#### 4.1.3 上传文件

**功能介绍**

该接口用于工作流、智能体上传文件，支持多种图片、文档、表格等多种格式的文件上传。接口返回临时下载路径。

**适用场景**: 在智能体应用中上传文件

**格式要求**

- 办公文档：DOC、DOCX、XLS、XLSX、PPT、PPTX、PDF、Numbers、CSV
- 图像文件：JPG、JPEG、PNG、GIF、WEBP、HEIC、HEIF、BMP、PCD、TIFF
- 音频文件：WAV、MP3、FLAC、M4A、AAC、OGG、WMA、MIDI
- 文本文件：JS、CPP、PY、JAVA、C、TXT、CSS、JAVASCRIPT、HTML、JSON、MD

**URI**

```
POST /v1/{project_id}/agent-runtime/upload-file
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |

**Query 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| workspace_id | 是 | String | 工作空间 ID |
| file | 是 | Object | 上传的文件，大小不超过 60MB |
| expires | 否 | Integer | 访问授权过期时间（天），最长 180 天 |
| is_image | 否 | Boolean | 是否是图片上传，默认 `false` |

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| X-Auth-Token | 否 | String | 用户 Token |
| Content-Type | 是 | String | 默认 `application/json` |
| Authorization | 否 | String | 平台 API Key |

**请求 Body 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| file | 是 | String | 用户上传的文档，文件大小小于 60MB |
| is_image | 否 | Boolean | 用户上传的文档是否是图片，默认 `false` |

**响应参数**

| 参数 | 类型 | 描述 |
|------|------|------|
| url | String | 临时有效，用于访问存储在 OBS 上的文件的下载地址 |
| headers | Object | 请求访问的域名，是 OBS 签名验证的关键信息 |
| file_name | String | 文件名 |

**请求示例**

```json
{
  "method": "POST",
  "url": "https://api.example.com/v1/{project_id}/agent-runtime/upload-file?workspace_id={workspace_id}",
  "headers": {
    "Content-Type": "multipart/form-data"
  },
  "body": {
    "mode": "formdata",
    "formdata": [
      {
        "key": "file",
        "type": "file",
        "src": "C:\\Users\\Desktop\\错误本地日志.txt"
      },
      {
        "key": "is_image",
        "type": "text",
        "value": "false"
      }
    ]
  }
}
```

---

#### 4.1.4 发布智能体版本

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
| workspace_id | 是 | String | 项目空间 ID，长度 1 至 64 字符 |

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| Content-Type | 是 | String | 默认 `application/json` |
| Authorization | 否 | String | 平台 API Key |
| X-Auth-Token | 否 | String | 用户 Token |

**请求 Body 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| version_name | 是 | String | 版本名称，长度不超过 64 字符 |
| version_note | 否 | String | 版本备注，长度不超过 1024 字符 |

**响应 Body 参数**

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

```json
{
  "method": "POST",
  "url": "https://api.example.com/v1/{project_id}/agent-manager/agents/{agent_id}/versions?workspace_id={workspace_id}",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "Bearer {API_KEY}"
  },
  "body": {
    "version_name": "v1.0.0",
    "version_note": "初始发布版本"
  }
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

#### 4.1.5 发布工作流版本

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
| workspace_id | 是 | String | 项目空间 ID，长度 1 至 64 字符 |

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| Content-Type | 是 | String | 默认 `application/json` |
| Authorization | 否 | String | 平台 API Key |
| X-Auth-Token | 否 | String | 用户 Token |

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
| 200 | 发布版本号 |
| 400 | 请求错误，如参数无效、版本名称已存在或工作流校验失败 |
| 401 | 鉴权失败 |
| 403 | 没有操作权限 |
| 404 | 找不到资源 |
| 500 | 服务内部错误，如工作流不存在 |

**请求示例**

```json
{
  "method": "POST",
  "url": "https://api.example.com/v1/{project_id}/agent-manager/workflows/{workflow_id}/versions?workspace_id={workspace_id}",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "Bearer {API_KEY}"
  },
  "body": {
    "version_name": "v1.0.0",
    "version_note": "初始发布版本"
  }
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

### 4.2 知识库

#### 4.2.1 知识库检索

**功能介绍**

提供多知识库并行检索能力，支持语义、关键词、混合及 FAQ 四种检索模式，并允许自定义相似度阈值与返回结果数量。

**适用场景**

- 同时从多个知识库或文档集合中搜索相关内容
- 在预设的问答列表中快速定位最相关的答案（FAQ检索）
- 通过混合模式或调整阈值，兼顾搜索结果的准确性和全面性

**URI**

```
POST /v2/{project_id}/knowledge-bases/retrieve
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| X-Auth-Token | 否 | String | 用户 Token |
| Content-Type | 是 | String | 默认 `application/json` |
| Authorization | 是 | String | 平台 API Key |

**请求 Body 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| knowledge_base_ids | 是 | Array of strings | 知识库 ID 列表，最多可同时检索 3 个知识库 |
| query | 是 | String | 用户输入的问题或关键词，长度 1 至 4096 字符 |
| search_mode | 否 | String | 检索策略模式：`doc`（语义检索）、`keyword`（关键词检索）、`mix`（混合检索）、`faq`（FAQ检索），默认 `doc` |
| top_k | 否 | Integer | 每个知识库最多返回的检索结果数量，默认 10，取值范围 1 至 100 |
| similarity_threshold | 否 | Float | 检索结果的最低相关度得分，默认 0.5，取值范围 [0.0, 1.0] |
| image_mask_policy | 否 | String | 知识检索结果切片中对图片标签的处理方式，默认 `REMOVE_IMAGE` |

**image_mask_policy 取值**

| 值 | 说明 |
|-----|------|
| RETAIN_IMAGE_ID | 保留图片 ID，格式：`{KI\|image_id}` |
| RETAIN_PLACEHOLDER | 保留占位符，格式：`{KI\|N}`，N 为序号 |
| REMOVE_IMAGE | 移除图片（即替换为空字符串） |

**响应参数**

| 参数 | 类型 | 描述 |
|------|------|------|
| total | Integer | 检索结果总数 |
| retrieve_result_list | Array of RetrievalResultInfo | 检索结果列表 |

**RetrievalResultInfo**

| 参数 | 类型 | 描述 |
|------|------|------|
| file_id | String | 文件 ID（或 FAQ ID） |
| title | String | 文档标题（如果是 FAQ，返回 QUESTION） |
| chunk_id | String | 分片 ID |
| content | String | 文本内容（如果是 FAQ，返回 ANSWER） |
| similarity | Float | 相似度，取值范围 [0.0, 1.0] |
| knowledge_base_id | String | 知识库 ID |
| image_ids | Array of strings | 检索到的图片列表，与 content 中的图片占位符一一对应，图片有效期为 7 天 |

**请求示例**

```json
{
  "method": "POST",
  "url": "https://api.example.com/v2/{project_id}/knowledge-bases/retrieve",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "knowledge_base_ids": ["bad2ef8771e6443096b528a8a7gh...."],
    "query": "测试检索问题。",
    "search_mode": "doc",
    "top_k": 10,
    "similarity_threshold": 0.5,
    "image_mask_policy": "RETAIN_PLACEHOLDER"
  }
}
```

**响应示例**

```json
{
  "total": 1,
  "retrieve_result_list": [
    {
      "file_id": "687c7914cbddcc8702cb6698f6230...",
      "title": "test",
      "chunk_id": "840003a72d6f4325958920e52c5a9...",
      "content": "测试检索召回内容，测试图片{KI|1}，测试图片{KI|2}。",
      "similarity": 0.9785156,
      "knowledge_base_id": "bad2ef8771e6443096b528a8a7gh....",
      "image_ids": [
        "df7d169bd3d111f0b3f9fa163e5ce...",
        "eab3e004d3d111f0b3f9fa163e5ce..."
      ]
    }
  ]
}
```

---

#### 4.2.2 获取知识库检索图片

**功能介绍**

通过图片 ID 获取知识库检索图片。

**适用场景**

- 当知识库检索接口的返回内容中包含知识库图片标签 `{KI|image_id}` 时
- 当知识库检索接口返回 image_ids 字段列表时
- 当智能体应用、工作流应用返回内容中包含 `![img](https://agent_arts_knowledge_img_url/image_id)` 时

**说明**: 图片的有效期为 7 天

**URI**

```
GET /v2/{project_id}/knowledge-bases/images/{image_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |
| image_id | 是 | String | 图片 ID，有效期为 7 天 |

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| X-Auth-Token | 否 | String | 用户 Token |
| Authorization | 是 | String | 平台 API Key |

**响应参数**

| 参数 | 类型 | 描述 |
|------|------|------|
| - | File | 图片文件流 |

**请求示例**

```json
{
  "method": "GET",
  "url": "https://api.example.com/v2/{project_id}/knowledge-bases/images/{image_id}",
  "headers": {
    "Authorization": "Bearer sk-21be3****************23"
  }
}
```

**响应示例**

状态码：200，图片文件流

---

#### 4.2.3 文件下载

**功能介绍**

下载知识库中的指定文件。

**适用场景**

- 智能体中添加知识库时，可以通过本接口下载检索结果中的文件
- 工作流中添加知识检索节点时，当工作流运行完成后，可以通过本接口下载检索结果中的文件

**说明**: 知识库内的文件不能通过该接口直接下载，文件的默认有效期为 7 天

**URI**

```
GET /v2/{project_id}/knowledge-bases/{knowledge_base_id}/files/{file_id}/content
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |
| knowledge_base_id | 是 | String | 知识库 ID |
| file_id | 是 | String | 文件 ID |

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| X-Auth-Token | 否 | String | 用户 Token |
| Authorization | 是 | String | 平台 API Key |

**响应参数**

| 参数 | 类型 | 描述 |
|------|------|------|
| - | File | 文件流 |

**请求示例**

```json
{
  "method": "GET",
  "url": "https://api.example.com/v2/{project_id}/knowledge-bases/{knowledge_base_id}/files/{file_id}/content",
  "headers": {
    "Authorization": "Bearer sk-21be3****************23"
  }
}
```

**响应示例**

状态码：200，文件流

---

## 5. 应用示例

### 5.1 调用工作流应用示例

**操作场景**

该接口用于运行场景化应用，支持在指定的项目、工作流和对话上下文中执行工作流逻辑。

**前提条件**

您需要规划 OpenJiuwen 所在的区域信息，并根据区域确定调用 API 的 Endpoint。

**调用工作流**

```
POST https://1.2.3.4/v1/12345/workflows/67890/conversations/67890
```

**Request Header**

```
Content-Type: application/json
Authorization: Bearer sk-*******
stream: true
```

**Request Body**

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
- `workflow_id`: 工作流应用 ID
- `conversation_id`: 会话 ID，每个会话的唯一标识符，字符串长度为 1~64 个字符，支持英文字母、数字、中划线、下划线

---

### 5.2 调用智能体应用示例

**操作场景**

该接口用于运行知识型智能体应用（单智能体应用、多智能体应用）。

**前提条件**

您需要规划 OpenJiuwen 所在的区域信息，并根据区域确定调用 API 的 Endpoint。

**调用应用**

```
POST https://1.2.3.4/v1/074cabeea7800f622f0ec010bffa6c59/agents/7c5be653-71b8-48e7-9058-7191ec0f44e8/conversations/eeb9884b-ef09-4dd5-a13a-803a09339960?workspace_id=default
```

**Request Header**

```
Content-Type: application/json
Authorization: Bearer sk-*******
stream: true
```

**Request Body**

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
- `agent_id`: 智能体应用 ID
- `conversation_id`: 会话 ID

---

## 6. 附录

### 6.1 状态码

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

### 6.2 错误码

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
| 400 | OpenJiuwen.02101032 | Current Agent version does not exist | 请求中指定的 Agent 或其版本在系统中不存在，可能已被删除或未正确发布 | 确认 Agent ID 和版本信息是否正确，并确保该 Agent 已成功发布并可用 || 403 | OpenJiuwen.02001017 | API call count for Agent exceeds quota | 智能体 API 调用次数已用完 | 请升级套餐 |
| 403 | OpenJiuwen.02201020 | Insufficient workflow execution permissions | 当前执行请求的 projectId 与工作流所属的 projectId 不一致 | 确保当前空间中的 projectId 与工作流所属的 projectId 一致 |
| 404 | OpenJiuwen.02101007 | Agent does not exist | 请求的智能体应用未找到或已被删除 | 确认该应用是否存在 |
| 500 | OpenJiuwen.02201004 | Workflow or workflow version does not exist | 请求中的工作流 ID 在当前项目和工作区中不存在 | 确认工作流 ID 是否正确 |
| 400 | OpenJiuwen.02201001 | Version name already existed | 版本名称已存在 | 请使用不同的版本名称 |
| 400 | OpenJiuwen.02201002 | Release version size exceed limit | 发布版本数量超过上限 | 请删除不需要的旧版本后重试 |
| 400 | OpenJiuwen.02201003 | Workflow information validation failed | 工作流信息校验失败 | 请检查工作流配置是否完整有效 |
| 500 | OpenJiuwen.02201005 | Workflow does not exist | 请求的工作流未找到或已被删除 | 确认该工作流是否存在 |

---

### 6.3 获取项目 ID

从控制台获取项目 ID：

1. 进入 OpenJiuwen 智能体开发平台
2. 在左侧导航，选择「开发中心 > 智能体管理」，选择「单智能体」、「工作流」或「多智能体」
3. 单击已发布的单智能体应用、工作流应用或多智能体应用卡片，进入编辑页面，选择「渠道管理」
4. 在「调用方式」区域，单击「查看API」
5. 在「API详情」页面，「请求结构」区域查看 project_id，V1 后面的字符串为 project_id
![img.png](../../images/getProjectId.png)
---

### 6.4 获取工作区 ID

在调用接口的时候，部分 URL 中需要填入工作区 ID，获取方法如下：

1. 进入 OpenJiuwen 智能体开发平台
2. 打开 F12，选择「Network」，单击任意页面，例如「个人空间」
3. 可以在接口调用中看到 `workspace_id=xxx`，xxx 为工作区 ID 的值

---
