# 知识库 API

> **注意**：知识库 API 使用 `/v2/` 版本前缀，与其他模块的 `/v1/` 不同。

---

## 目录

1. [知识库检索](#1-知识库检索)
2. [获取知识库检索图片](#2-获取知识库检索图片)
3. [文件下载](#3-文件下载)

---

## 1. 知识库检索

**功能介绍**

提供多知识库并行检索能力，支持语义、关键词、混合及 FAQ 四种检索模式，并允许自定义相似度阈值与返回结果数量。

**适用场景**

- 同时从多个知识库或文档集合中搜索相关内容
- 在预设的问答列表中快速定位最相关的答案（FAQ检索）
- 通过混合模式或调整阈值，兼顾搜索结果的准确性和全面性

**URI**

```
POST /v2/{project_id}/knowledge-bases/retrieve?workspace_id={workspace_id}
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
| Content-Type | 是 | String | 默认 `application/json` |

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

```
POST /v2/{project_id}/knowledge-bases/retrieve?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "knowledge_base_ids": ["bad2ef8771e6443096b528a8a7gh...."],
  "query": "测试检索问题。",
  "search_mode": "doc",
  "top_k": 10,
  "similarity_threshold": 0.5,
  "image_mask_policy": "RETAIN_PLACEHOLDER"
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

## 2. 获取知识库检索图片

**功能介绍**

通过图片 ID 获取知识库检索图片。

**适用场景**

- 当知识库检索接口的返回内容中包含知识库图片标签 `{KI|image_id}` 时
- 当知识库检索接口返回 image_ids 字段列表时
- 当智能体应用、工作流应用返回内容中包含 `![img](https://agent_arts_knowledge_img_url/image_id)` 时

**说明**: 图片的有效期为 7 天

**URI**

```
GET /v2/{project_id}/knowledge-bases/images/{image_id}?workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |
| image_id | 是 | String | 图片 ID，有效期为 7 天 |

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
| - | File | 图片文件流 |

**请求示例**

```
GET /v2/{project_id}/knowledge-bases/images/{image_id}?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**响应示例**

状态码：200，图片文件流

---

## 3. 文件下载

**功能介绍**

下载知识库中的指定文件。

**适用场景**

- 智能体中添加知识库时，可以通过本接口下载检索结果中的文件
- 工作流中添加知识检索节点时，当工作流运行完成后，可以通过本接口下载检索结果中的文件

**说明**: 知识库内的文件不能通过该接口直接下载，文件的默认有效期为 7 天

**URI**

```
GET /v2/{project_id}/knowledge-bases/{knowledge_base_id}/files/{file_id}/content?workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |
| knowledge_base_id | 是 | String | 知识库 ID |
| file_id | 是 | String | 文件 ID |

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
| - | File | 文件流 |

**请求示例**

```
GET /v2/{project_id}/knowledge-bases/{knowledge_base_id}/files/{file_id}/content?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**响应示例**

状态码：200，文件流

---
