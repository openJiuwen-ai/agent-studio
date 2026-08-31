# File Management API

---

## Table of Contents

1. [Upload File](#1-upload-file)

---

## 1. Upload File

**Introduction**

This API is used to upload files for workflows and agents. It supports image, document, spreadsheet, and other formats. The API returns a temporary download URL. Import files should use the `.jsonl` extension.

**Applicable Scenarios**: Upload files in agent applications

**Format Requirements**

- Office documents: DOC, DOCX, XLS, XLSX, PPT, PPTX, PDF, Numbers, CSV
- Image files: JPG, JPEG, PNG, GIF, WEBP, HEIC, HEIF, BMP, PCD, TIFF
- Audio files: WAV, MP3, FLAC, M4A, AAC, OGG, WMA, MIDI
- Text files: JS, CPP, PY, JAVA, C, TXT, CSS, JAVASCRIPT, HTML, JSON, MD
- Import files: JSONL

**URI**

```
POST /v1/{project_id}/agent-runtime/upload-file?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID |
| expires | No | Integer | Access authorization expiration time (days), up to 180 days |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| Content-Type | Yes | String | `multipart/form-data` |
| X-Auth-Token | Yes | String | User Token |

**Request Body Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| file | Yes | File | The file to upload, size not exceeding 60MB (multipart upload) |
| is_image | No | Boolean | Whether the uploaded file is an image, default `false` |

**Response Parameters**

Status code: 200

| Parameter | Type | Description |
|------|------|------|
| url | String | Temporarily valid download URL for the uploaded file |

**Request Example**

```
POST /v1/{project_id}/agent-runtime/upload-file?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: multipart/form-data
X-Auth-Token: {token}

{
  "file": "@example.txt",
  "is_image": false
}
```

**Response Example**

```json
{
  "url": "http://minio:9000/agent-builder/file/xxx.txt?AWSAccessKeyId=...&Expires=...&Signature=..."
}
```

---
