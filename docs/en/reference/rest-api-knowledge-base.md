# Knowledge Base API

> **Note**: Knowledge Base APIs use the `/v2/` version prefix, unlike other modules which use `/v1/`.

---

## Table of Contents

1. [Knowledge Base Retrieval](#1-knowledge-base-retrieval)
2. [Retrieve Knowledge Base Image](#2-retrieve-knowledge-base-image)
3. [File Download](#3-file-download)

---

## 1. Knowledge Base Retrieval

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
| X-Auth-Token | Yes | String | User Token |
| Content-Type | Yes | String | Default `application/json` |

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

```
POST /v2/{project_id}/knowledge-bases/retrieve HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "knowledge_base_ids": ["bad2ef8771e6443096b528a8a7gh...."],
  "query": "Test retrieval query.",
  "search_mode": "doc",
  "top_k": 10,
  "similarity_threshold": 0.5,
  "image_mask_policy": "RETAIN_PLACEHOLDER"
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
      "content": "Test retrieval recall content, test image{KI|1}, test image{KI|2}.",
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

## 2. Retrieve Knowledge Base Image

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
| X-Auth-Token | Yes | String | User Token |

**Response Parameters**

| Parameter | Type | Description |
|------|------|------|
| - | File | Image file stream |

**Request Example**

```
GET /v2/{project_id}/knowledge-bases/images/{image_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**Response Example**

Status code: 200, image file stream

---

## 3. File Download

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
| X-Auth-Token | Yes | String | User Token |

**Response Parameters**

| Parameter | Type | Description |
|------|------|------|
| - | File | File stream |

**Request Example**

```
GET /v2/{project_id}/knowledge-bases/{knowledge_base_id}/files/{file_id}/content HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**Response Example**

Status code: 200, file stream

---
