# API Specification

---

## Table of Contents

1. [Before You Start](#1-before-you-start)
2. [API Overview](#2-api-overview)
3. [How to Call APIs](#3-how-to-call-apis)
4. [APIs](#4-apis)
    - 4.1 [Workflow/Agent](#41-workflowagent)
    - 4.2 [Knowledge Base](#42-knowledge-base)
5. [Application Examples](#5-application-examples)
6. [Appendix](#6-appendix)

---

## 1. Before You Start

Welcome to OpenJiuwen service. OpenJiuwen is a one-stop enterprise-level agent building platform that includes functional modules such as application management, component library, knowledge base, prompt development, configuration management, and model integration and testing. It covers eight aspects: experience design, code development, application runtime, asset management, data processing, testing and publishing, operations monitoring, and security assurance, providing enterprise users with an out-of-the-box large model application development toolchain.

You can use the APIs provided in this document to perform operations on OpenJiuwen, such as invoking applications and invoking workflows.

### Endpoint

An endpoint is the request address for calling APIs. Endpoints vary by region. To obtain the endpoint:

1. Go to the OpenJiuwen agent development platform
2. In the left navigation, select "Development Center > Agent Management", then select "Single Agent", "Workflow", or "Multi-Agent"
3. Click on a published single agent application, workflow application, or multi-agent application card to enter the editing page, then select "Channel Management"
4. In the "Invocation Method" area, click "View API"
5. On the "API Details" page, view the URL address. The IP address:port number is the API request address

---

## 2. API Overview

| Type | Description |
|------|------|
| Workflow/Agent | APIs for invoking workflow applications, agent applications, and uploading files |
| Knowledge Base | APIs for knowledge base retrieval, retrieving knowledge base images, and file download |

---

## 3. How to Call APIs

### 3.1 Constructing a Request

#### Request URI

A request URI consists of the following parts:
```
{URI-scheme}://{Endpoint}/{resource-path}?{query-string}
```

- **URI-scheme**: Indicates the protocol used for transmitting requests. All APIs currently use HTTPS
- **Endpoint**: Specifies the server domain name or IP that hosts the REST service endpoint. Endpoints vary by service and region
- **resource-path**: The resource path, i.e., the API access path
- **query-string**: Query parameters, which are optional

#### Request Methods

| Method | Description |
|------|------|
| GET | Requests the server to return a specified resource |
| PUT | Requests the server to update a specified resource |
| POST | Requests the server to create a new resource or perform a special operation |
| DELETE | Requests the server to delete a specified resource |
| HEAD | Requests the resource header from the server |
| PATCH | Requests the server to partially update a resource |

#### Request Headers

Common headers need to be added to the request:

| Header | Required | Description |
|--------|------|------|
| Content-Type | Yes | The type of the message body. Default value is `application/json` |
| Authorization | No | Signature authentication information. Required when using platform API Key authentication |

### 3.2 Authentication
- **Platform API Key Authentication**: Use the platform API Key to authenticate API requests

### 3.3 Response

#### Status Codes

A status code is a numeric code ranging from 1xx to 5xx that indicates the status of the request response

#### Response Body

When an API call fails, an error code and error message are returned:

```json
{
  "error_msg": "Request body is invalid."
}
```

---

## 4. APIs

### 4.1 Workflow/Agent

#### 4.1.1 Invoke Workflow Application

**Introduction**

This API is used to run scenario-based applications. It supports executing workflow logic within a specified project, workflow, and conversation context. The API supports streaming response mode.

**Applicable Scenarios**

- Run predefined workflows in a project
- Supports debug mode and published mode
- Supports streaming responses, suitable for scenarios requiring real-time feedback

**URI**

```
POST /v1/{project_id}/workflows/{workflow_id}/conversations/{conversation_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |
| workflow_id | Yes | String | Workflow application ID |
| conversation_id | Yes | String | Conversation ID, the unique identifier for each conversation |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | No | String | Workspace ID |
| version | No | String | Published version |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| X-Auth-Token | No | String | User Token |
| X-Invoke-Mode | No | String | Run mode: `debug` (debug mode) or `published` (published mode), default `published` |
| stream | No | Boolean | Whether to enable streaming invocation, default `true` |
| Authorization | No | String | Platform API Key |
| X-Request-Id | No | String | Trace ID |
| Content-Type | Yes | String | MIME type of the request body, default `application/json` |

**Request Body Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| inputs | Yes | Map<String,Object> | The user's question, used as input for running the workflow |
| plugin_configs | No | Array of PluginConfig | Plugin configuration information |

**PluginConfig**

| Parameter | Required | Type | Description |
|------|------|------|------|
| plugin_id | No | String | Plugin ID |
| config | No | Map<String,String> | Plugin configuration information |

**Response Parameters**

Status code: 200

| Parameter | Type | Description |
|------|------|------|
| event | Map<String,Object> | Final output content of the workflow |
| data | data object | Workflow assistant reply content |

**data**

| Parameter | Type | Description |
|------|------|------|
| text | String | Workflow output content message block |
| index | Integer | Message block index |
| node_id | String | Node ID |
| node_type | String | Node type |
| node_name | String | Node name |
| workflow_id | String | Workflow ID |
| workflow_name | String | Workflow name |
| createdTime | Integer | Creation time |

**Status Codes**

| Status Code | Description |
|--------|------|
| 200 | Successful response |
| 500 | Error response |

**Request Example**

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

**Response Example**

Successful response (status code: 200):

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

Error response (status code: 500):

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

#### 4.1.2 Invoke Agent Application

**Introduction**

This API is used to run knowledge-based agent applications, supporting both single agent and multi-agent. It supports executing agent logic within a specified project, agent, and conversation context. The API supports streaming response mode.

**Applicable Scenarios**

- Run predefined knowledge-based agent applications in a project
- Supports debug mode and published mode
- Supports streaming responses, suitable for scenarios requiring real-time feedback

**URI**

```
POST /v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |
| agent_id | Yes | String | Agent application ID |
| conversation_id | Yes | String | Conversation ID |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | No | String | Workspace ID |
| version | No | String | Published version |
| type | No | String | Execution type: `controller` (multi-agent) or `agent` (single agent), default `agent` |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| X-Auth-Token | No | String | User Token |
| X-Invoke-Mode | No | String | Run mode: `debug` or `published`, default `published` |
| stream | No | Boolean | Whether to enable streaming invocation. The current agent application only supports streaming invocation, default `true` |
| Authorization | No | String | Platform API Key |
| X-Request-Id | No | String | Trace ID |
| Content-Type | Yes | String | Default `application/json` |

**Request Body Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| query | No | String | User's question |
| inputs | Yes | Map<String,Object> | The user's question |
| user_profile | No | UserProfile object | User profile |
| tool_switch_dict | No | Map<String,Boolean> | Whether plugins are enabled |
| model_deployment_id | No | String | ID of the model configured for the agent |
| enable_history | No | Boolean | Whether to record conversation history, default `true` |
| histories | No | Array of Message | Conversation history passed in |
| files | No | Array of strings | Uploaded file URLs |

**UserProfile**

| Parameter | Required | Type | Description |
|------|------|------|------|
| enable_retrieve | No | Boolean | Whether to read user profile at runtime, default `false` |
| enable_extract | No | Boolean | Whether to build user profile at runtime, default `false` |

**Message**

| Parameter | Required | Type | Description |
|------|------|------|------|
| role | No | String | Conversation role: `user` (user input) or `assistant` (model reply) |
| content | No | String | Conversation content |

**Response Parameters**

Status code: 200

| Parameter | Type | Description |
|------|------|------|
| data | String | Streamed agent message |
| event | String | Data unit type |
| content | Object | Message block content |
| createdTime | Long | Timestamp of the message block response |
| latency | latency object | Latency information |
| plugin | plugin object | Plugin request information |

**event Values**

| Value | Description |
|-----|------|
| start | Start node, indicates the beginning of model invocation for conversation |
| message | Message node, indicates the message returned by the model |
| plugin_start | Plugin invocation request node |
| plugin_end | Plugin invocation response node |
| statistic_data | Execution data node, contains latency information for this invocation |
| summary_response | Message summary node, contains the full response information for this invocation |
| done | Streaming invocation end node |

**latency**

| Parameter | Type | Description |
|------|------|------|
| plugin | Long | Plugin invocation latency |
| model | Long | Model invocation latency |
| overall | Long | Total latency |

**plugin**

| Parameter | Type | Description |
|------|------|------|
| name | String | Plugin name |
| arguments | Object | Plugin input parameters |

**Request Example**

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

**Response Example**

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

#### 4.1.3 Upload File

**Introduction**

This API is used to upload files for workflows and agents. It supports multiple file formats including images, documents, and spreadsheets. The API returns a temporary download path.

**Applicable Scenarios**: Upload files in agent applications

**Format Requirements**

- Office documents: DOC, DOCX, XLS, XLSX, PPT, PPTX, PDF, Numbers, CSV
- Image files: JPG, JPEG, PNG, GIF, WEBP, HEIC, HEIF, BMP, PCD, TIFF
- Audio files: WAV, MP3, FLAC, M4A, AAC, OGG, WMA, MIDI
- Text files: JS, CPP, PY, JAVA, C, TXT, CSS, JAVASCRIPT, HTML, JSON, MD

**URI**

```
POST /v1/{project_id}/agent-runtime/upload-file
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID |
| file | Yes | Object | The file to upload, size not exceeding 60MB |
| expires | No | Integer | Access authorization expiration time (days), up to 180 days |
| is_image | No | Boolean | Whether the upload is an image, default `false` |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| X-Auth-Token | No | String | User Token |
| Content-Type | Yes | String | Default `application/json` |
| Authorization | No | String | Platform API Key |

**Request Body Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| file | Yes | String | The document uploaded by the user, file size less than 60MB |
| is_image | No | Boolean | Whether the uploaded document is an image, default `false` |

**Response Parameters**

| Parameter | Type | Description |
|------|------|------|
| url | String | Temporarily valid download address for accessing files stored on OBS |
| headers | Object | Domain for request access, key information for OBS signature verification |
| file_name | String | File name |

**Request Example**

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

#### 4.1.4 Publish Agent Version

**Introduction**

This API is used to publish a new version of a specified agent application, creating version snapshots of DSL and IR files, and recording version information.

**Applicable Scenarios**

- Publish the current configuration of an agent application as a new version
- Create version snapshots for agent applications for subsequent rollback or management

**URI**

```
POST /v1/{project_id}/agent-manager/agents/{agent_id}/versions?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Project ID |
| agent_id | Yes | String | Agent ID, up to 64 characters, supports only letters, numbers, underscores, and hyphens |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID, 1 to 64 characters |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| Content-Type | Yes | String | Default `application/json` |
| Authorization | No | String | Platform API Key |
| X-Auth-Token | No | String | User Token |

**Request Body Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| version_name | Yes | String | Version name, up to 64 characters |
| version_note | No | String | Version note, up to 1024 characters |

**Response Body Parameters**

Status code: 200

This API has no response body for a successful response.

Status code: 400 / 403 / 404 / 500

| Parameter | Type | Description |
|------|------|------|
| error_code | String | Error code |
| error_msg | String | Error message |
| error_reason | String | Error reason |
| error_suggestion | String | Error handling suggestion |
| details | Array of ErrorDetail | Detailed error information returned by the API |

**Status Codes**

| Status Code | Description |
|--------|------|
| 200 | Agent version created successfully |
| 400 | Request error, such as invalid parameters or version name already exists |
| 403 | No operation permission |
| 404 | Resource not found, such as agent does not exist |
| 500 | Internal service error |

**Request Example**

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

**Response Example**

Successful response (status code: 200):

No response body.

Error response (status code: 400):

```json
{
  "error_msg": "The version name already existed."
}
```

---

#### 4.1.5 Publish Workflow Version

**Introduction**

This API is used to publish a new version of a specified workflow application, creating version snapshots of the workflow DSL and IR files, validating the workflow configuration, and returning the published version ID.

**Applicable Scenarios**

- Publish the current configuration of a workflow application as a new version
- Automatically validate the workflow configuration before publishing
- Create version snapshots for workflow applications for subsequent rollback or management

**URI**

```
POST /v1/{project_id}/agent-manager/workflows/{workflow_id}/versions?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Tenant project ID, up to 64 characters, supports only letters, numbers, underscores, and hyphens |
| workflow_id | Yes | String | Workflow ID, up to 64 characters, supports only letters, numbers, underscores, and hyphens |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID, 1 to 64 characters |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| Content-Type | Yes | String | Default `application/json` |
| Authorization | No | String | Platform API Key |
| X-Auth-Token | No | String | User Token |

**Request Body Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| version_name | Yes | String | Version name, up to 64 characters |
| version_note | No | String | Version note, up to 1024 characters |

**Response Parameters**

Status code: 200

| Parameter | Type | Description |
|------|------|------|
| version_id | String | Published version ID |

Status code: 400 / 401 / 403 / 404 / 500

| Parameter | Type | Description |
|------|------|------|
| error_code | String | Error code |
| error_msg | String | Error message |
| error_reason | String | Error reason |
| error_suggestion | String | Error handling suggestion |
| details | Array of ErrorDetail | Detailed error information returned by the API |

**Status Codes**

| Status Code | Description |
|--------|------|
| 200 | Version published |
| 400 | Request error, such as invalid parameters, version name already exists, or workflow validation failed |
| 401 | Authentication failed |
| 403 | No operation permission |
| 404 | Resource not found |
| 500 | Internal service error, such as workflow does not exist |

**Request Example**

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

**Response Example**

Successful response (status code: 200):

```json
"1783341175105"
```

Error response (status code: 400):

```json
{
  "error_msg": "The version name already existed."
}
```

---

### 4.2 Knowledge Base

#### 4.2.1 Knowledge Base Retrieval

**Introduction**

Provides parallel retrieval capabilities across multiple knowledge bases, supporting four retrieval modes: semantic, keyword, hybrid, and FAQ. It also allows customization of similarity threshold and the number of returned results.

**Applicable Scenarios**

- Search for relevant content across multiple knowledge bases or document collections simultaneously
- Quickly locate the most relevant answers in a preset Q&A list (FAQ retrieval)
- Balance search accuracy and comprehensiveness through hybrid mode or threshold adjustment

**URI**

```
POST /v2/{project_id}/knowledge-bases/retrieve
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| X-Auth-Token | No | String | User Token |
| Content-Type | Yes | String | Default `application/json` |
| Authorization | Yes | String | Platform API Key |

**Request Body Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| knowledge_base_ids | Yes | Array of strings | List of knowledge base IDs, up to 3 knowledge bases can be retrieved simultaneously |
| query | Yes | String | User's question or keyword, 1 to 4096 characters |
| search_mode | No | String | Retrieval strategy mode: `doc` (semantic retrieval), `keyword` (keyword retrieval), `mix` (hybrid retrieval), `faq` (FAQ retrieval), default `doc` |
| top_k | No | Integer | Maximum number of retrieval results returned per knowledge base, default 10, range 1 to 100 |
| similarity_threshold | No | Float | Minimum relevance score for retrieval results, default 0.5, range [0.0, 1.0] |
| image_mask_policy | No | String | How image tags in knowledge retrieval result chunks are handled, default `REMOVE_IMAGE` |

**image_mask_policy Values**

| Value | Description |
|-----|------|
| RETAIN_IMAGE_ID | Retain image ID, format: `{KI\|image_id}` |
| RETAIN_PLACEHOLDER | Retain placeholder, format: `{KI\|N}`, where N is the index |
| REMOVE_IMAGE | Remove image (i.e., replace with empty string) |

**Response Parameters**

| Parameter | Type | Description |
|------|------|------|
| total | Integer | Total number of retrieval results |
| retrieve_result_list | Array of RetrievalResultInfo | List of retrieval results |

**RetrievalResultInfo**

| Parameter | Type | Description |
|------|------|------|
| file_id | String | File ID (or FAQ ID) |
| title | String | Document title (returns QUESTION if it is a FAQ) |
| chunk_id | String | Chunk ID |
| content | String | Text content (returns ANSWER if it is a FAQ) |
| similarity | Float | Similarity, range [0.0, 1.0] |
| knowledge_base_id | String | Knowledge base ID |
| image_ids | Array of strings | List of retrieved images, corresponding one-to-one with image placeholders in content. Images are valid for 7 days |

**Request Example**

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

**Response Example**

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

#### 4.2.2 Retrieve Knowledge Base Image

**Introduction**

Retrieve knowledge base images by image ID.

**Applicable Scenarios**

- When the response content from the knowledge base retrieval API contains knowledge base image tags `{KI|image_id}`
- When the knowledge base retrieval API returns an image_ids field list
- When the response content from agent applications or workflow applications contains `![img](https://agent_arts_knowledge_img_url/image_id)`

**Note**: Images are valid for 7 days

**URI**

```
GET /v2/{project_id}/knowledge-bases/images/{image_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |
| image_id | Yes | String | Image ID, valid for 7 days |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| X-Auth-Token | No | String | User Token |
| Authorization | Yes | String | Platform API Key |

**Response Parameters**

| Parameter | Type | Description |
|------|------|------|
| - | File | Image file stream |

**Request Example**

```json
{
  "method": "GET",
  "url": "https://api.example.com/v2/{project_id}/knowledge-bases/images/{image_id}",
  "headers": {
    "Authorization": "Bearer sk-21be3****************23"
  }
}
```

**Response Example**

Status code: 200, image file stream

---

#### 4.2.3 File Download

**Introduction**

Download a specified file from a knowledge base.

**Applicable Scenarios**

- When adding a knowledge base to an agent, files from retrieval results can be downloaded through this API
- When adding a knowledge retrieval node in a workflow, files from retrieval results can be downloaded through this API after the workflow completes

**Note**: Files within a knowledge base cannot be directly downloaded through this API. The default validity period for files is 7 days

**URI**

```
GET /v2/{project_id}/knowledge-bases/{knowledge_base_id}/files/{file_id}/content
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |
| knowledge_base_id | Yes | String | Knowledge base ID |
| file_id | Yes | String | File ID |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| X-Auth-Token | No | String | User Token |
| Authorization | Yes | String | Platform API Key |

**Response Parameters**

| Parameter | Type | Description |
|------|------|------|
| - | File | File stream |

**Request Example**

```json
{
  "method": "GET",
  "url": "https://api.example.com/v2/{project_id}/knowledge-bases/{knowledge_base_id}/files/{file_id}/content",
  "headers": {
    "Authorization": "Bearer sk-21be3****************23"
  }
}
```

**Response Example**

Status code: 200, file stream

---

## 5. Application Examples

### 5.1 Invoke Workflow Application Example

**Operation Scenario**

This API is used to run scenario-based applications, supporting the execution of workflow logic within a specified project, workflow, and conversation context.

**Prerequisites**

You need to plan the region information of OpenJiuwen and determine the API Endpoint based on the region.

**Invoke Workflow**

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

**Parameter Description**

- `endpoint`: Endpoint
- `project_id`: Current project ID
- `workflow_id`: Workflow application ID
- `conversation_id`: Conversation ID, the unique identifier for each conversation, string length 1 to 64 characters, supports English letters, numbers, hyphens, and underscores

---

### 5.2 Invoke Agent Application Example

**Operation Scenario**

This API is used to run knowledge-based agent applications (single agent application, multi-agent application).

**Prerequisites**

You need to plan the region information of OpenJiuwen and determine the API Endpoint based on the region.

**Invoke Application**

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

**Parameter Description**

- `endpoint`: Endpoint
- `project_id`: Current project ID
- `agent_id`: Agent application ID
- `conversation_id`: Conversation ID

---

## 6. Appendix

### 6.1 Status Codes

| Status Code | Code | Description |
|--------|------|------|
| 100 | Continue | Continue request |
| 101 | Switching Protocols | Switching protocol |
| 200 | OK | Server has successfully processed the request |
| 201 | Created | Creation request fully successful |
| 202 | Accepted | Request accepted but not yet processed |
| 203 | Non-Authoritative Information | Non-authoritative information, request successful |
| 204 | No Content | Request fully successful, HTTP response contains no response body |
| 205 | Reset Content | Reset content, server processed successfully |
| 206 | Partial Content | Server successfully processed a partial GET request |
| 300 | Multiple Choices | Multiple choices |
| 301 | Moved Permanently | Resource permanently moved |
| 302 | Found | Resource temporarily moved |
| 303 | See Other | See other address |
| 304 | Not Modified | Requested resource not modified |
| 305 | Use Proxy | Requested resource must be accessed through a proxy |
| 400 | Bad Request | Invalid request |
| 401 | Unauthorized | Authentication information incorrect or invalid |
| 402 | Payment Required | Reserved request |
| 403 | Forbidden | Request denied access |
| 404 | Not Found | Requested resource does not exist |
| 405 | Method Not Allowed | Request contains a method not supported by the resource |
| 406 | Not Acceptable | Server cannot fulfill the request based on the client's content characteristics |
| 407 | Proxy Authentication Required | Request requires proxy authentication |
| 408 | Request Time-out | Server timed out waiting for the request |
| 409 | Conflict | Server encountered a conflict while processing the request |
| 410 | Gone | Requested resource no longer exists |
| 411 | Length Required | Server cannot process the request without Content-Length |
| 412 | Precondition Failed | Precondition not met |
| 413 | Request Entity Too Large | Request entity too large, server cannot process |
| 414 | Request-URI Too Large | Request URL too long |
| 415 | Unsupported Media Type | Server cannot process the media format attached to the request |
| 416 | Requested range not satisfiable | Client requested an invalid range |
| 417 | Expectation Failed | Server cannot fulfill the Expect request header |
| 422 | Unprocessable Entity | Request format is correct but contains semantic errors, cannot be processed |
| 429 | Too Many Requests | Request exceeded the client's access frequency limit |
| 500 | Internal Server Error | Internal server error |
| 501 | Not Implemented | Server does not support the requested functionality |
| 502 | Bad Gateway | Server acting as a gateway or proxy received an invalid request from the remote server |
| 503 | Service Unavailable | Requested service unavailable |
| 504 | Server Timeout | Request could not be completed within the given time |
| 505 | HTTP Version not supported | Server does not support the HTTP protocol version of the request |

---

### 6.2 Error Codes

| Status Code | Error Code | Error Message | Description | Action |
|--------|--------|----------|------|----------|
| 400 | OpenJiuwen.03001001 | Input parameter is invalid | Input parameter is invalid | Please check if the input parameters are correct |
| 400 | OpenJiuwen.03002106 | Operation failed | External knowledge base does not support file download | Third-party knowledge base connection does not exist |
| 400 | OpenJiuwen.03003039 | Operation failed | Image not found or expired | Please retry later |
| 403 | OpenJiuwen.03001021 | Operation failed | Downloaded file is empty | Please check and retry |
| 404 | OpenJiuwen.03001003 | resource not exist | Resource does not exist | Please contact technical support |
| 404 | OpenJiuwen.03002010 | Can not retrieve in knowledge base | This knowledge has been deleted or disabled | Check the status of this knowledge |
| 500 | OpenJiuwen.03000000 | System internal error | System internal error | Please contact technical support |
| 500 | OpenJiuwen.03002019 | Operation failed | File not found or expired | Check and retry |
| 500 | OpenJiuwen.03002104 | Query third party knowledgeBases error | Third-party knowledge base connection information error | Check connection information and retry |
| 200 | OpenJiuwen.02101016 | Insufficient execution permissions for Agent | Current user does not have permission to run this single agent application in the specified project | Confirm that the current user has execution permission for this single agent application in the target project |
| 200 | OpenJiuwen.100002 | validation failed | Input parameter format is incorrect or required parameters are missing | Check if the request parameters conform to the API specification |
| 400 | OpenJiuwen.02101032 | Current Agent version does not exist | The Agent or its version specified in the request does not exist in the system, possibly deleted or not correctly published | Confirm that the Agent ID and version information are correct, and ensure the Agent has been successfully published and is available || 403 | OpenJiuwen.02001017 | API call count for Agent exceeds quota | Agent API call quota has been exhausted | Please upgrade the plan |
| 403 | OpenJiuwen.02201020 | Insufficient workflow execution permissions | The projectId of the current execution request does not match the projectId of the workflow | Ensure that the projectId in the current workspace matches the projectId of the workflow |
| 404 | OpenJiuwen.02101007 | Agent does not exist | The requested agent application was not found or has been deleted | Confirm whether the application exists |
| 500 | OpenJiuwen.02201004 | Workflow or workflow version does not exist | The workflow ID in the request does not exist in the current project and workspace | Confirm the workflow ID is correct |
| 400 | OpenJiuwen.02201001 | Version name already existed | Version name already exists | Please use a different version name |
| 400 | OpenJiuwen.02201002 | Release version size exceed limit | Number of published versions exceeds the limit | Please delete unnecessary old versions and retry |
| 400 | OpenJiuwen.02201003 | Workflow information validation failed | Workflow information validation failed | Please check if the workflow configuration is complete and valid |
| 500 | OpenJiuwen.02201005 | Workflow does not exist | The requested workflow was not found or has been deleted | Confirm whether the workflow exists |

---

### 6.3 Get Project ID

Get the project ID from the console:

1. Go to the OpenJiuwen agent development platform
2. In the left navigation, select "Development Center > Agent Management", then select "Single Agent", "Workflow", or "Multi-Agent"
3. Click on a published single agent application, workflow application, or multi-agent application card to enter the editing page, then select "Channel Management"
4. In the "Invocation Method" area, click "View API"
5. On the "API Details" page, view the project_id in the "Request Structure" area. The string after V1 is the project_id
![img.png](../../images/getProjectId.png)
---

### 6.4 Get Workspace ID

When calling APIs, some URLs require a workspace ID. To obtain it:

1. Go to the OpenJiuwen agent development platform
2. Open F12, select "Network", click on any page, such as "Personal Space"
3. You can see `workspace_id=xxx` in the API calls, where xxx is the workspace ID value

---
