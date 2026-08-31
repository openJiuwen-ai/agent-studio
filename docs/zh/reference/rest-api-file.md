# 文件管理 API

---

## 目录

1. [上传文件](#1-上传文件)

---

## 1. 上传文件

**功能介绍**

该接口用于工作流、智能体上传文件，支持图片、文档、表格等多种格式的文件上传。接口返回临时下载路径。

**适用场景**: 在智能体应用中上传文件

**格式要求**

- 办公文档：DOC、DOCX、XLS、XLSX、PPT、PPTX、PDF、Numbers、CSV
- 图像文件：JPG、JPEG、PNG、GIF、WEBP、HEIC、HEIF、BMP、PCD、TIFF
- 音频文件：WAV、MP3、FLAC、M4A、AAC、OGG、WMA、MIDI
- 文本文件：JS、CPP、PY、JAVA、C、TXT、CSS、JAVASCRIPT、HTML、JSON、MD、JSONL

**URI**

```
POST /v1/{project_id}/agent-runtime/upload-file?workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |

**Query 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| workspace_id | 是 | String | 工作空间 ID |
| expires | 否 | Integer | 访问授权过期时间（天），最长 180 天 |

**请求 Header 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| X-Auth-Token | 是 | String | 用户 Token |
| Content-Type | 是 | String | `multipart/form-data` |

**请求 Body 参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| file | 是 | File | 用户上传的文档，文件大小小于 60MB |
| is_image | 否 | Boolean | 用户上传的文档是否是图片，默认 `false` |

**响应参数**

| 参数 | 类型 | 描述 |
|------|------|------|
| url | String | 临时有效的文件下载地址，包含 OBS 签名信息（AWSAccessKeyId、Expires、Signature） |

**请求示例**

```
POST /v1/{project_id}/agent-runtime/upload-file?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: multipart/form-data
X-Auth-Token: {token}

file=@example.txt
```

**响应示例**

```json
{
  "url": "http://minio:9000/agent-builder/file/xxx.txt?AWSAccessKeyId=xxx&Expires=xxx&Signature=xxx"
}
```

---
