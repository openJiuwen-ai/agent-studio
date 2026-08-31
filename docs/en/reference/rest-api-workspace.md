# Workspace API

---

## Table of Contents

1. [Create Workspace](#1-create-workspace)
2. [Update Workspace Configuration](#2-update-workspace-configuration)
3. [Delete Workspace](#3-delete-workspace)
4. [Query Workspace Information](#4-query-workspace-information)
5. [Batch Add Workspace Members](#5-batch-add-workspace-members)
6. [Update Workspace Member Role](#6-update-workspace-member-role)
7. [Batch Remove Workspace Members](#7-batch-remove-workspace-members)
8. [Transfer Workspace Ownership](#8-transfer-workspace-ownership)
9. [Leave Current Workspace](#9-leave-current-workspace)
10. [Query Workspace Member List](#10-query-workspace-member-list)
11. [Query Workspace Role List](#11-query-workspace-role-list)
12. [Query IAM Users](#12-query-iam-users)
13. [Share Resource to Other Workspace](#13-share-resource-to-other-workspace)
14. [Query Shared Resources](#14-query-shared-resources)
15. [Query Shared-by-us Resources](#15-query-shared-by-us-resources)
16. [Cancel Resource Share](#16-cancel-resource-share)

---

## 1. Create Workspace

**Introduction**

This API is used to create a new team workspace. The creator automatically becomes the workspace owner.

**URI**

```
POST /v1/{project_id}/agent-manager/workspace
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| Content-Type | Yes | String | Default `application/json` |
| X-Auth-Token | Yes | String | User Token |

**Request Body Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| name | Yes | String | Workspace name |
| description | No | String | Workspace description |

**Response Parameters**

| Parameter | Type | Description |
|------|------|------|
| id | String | Created workspace ID |
| name | String | Workspace name |
| projectId | String | Project ID |
| type | String | Workspace type (e.g. `TEAM`) |
| status | String | Workspace status (e.g. `ENABLE`) |
| creator | String | Creator |
| createdOn | Long | Creation time |

**Request Example**

```
POST /v1/{project_id}/agent-manager/workspace HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "name": "R&D Team Workspace",
  "description": "R&D team shared workspace"
}
```

**Response Example**

```json
{
  "id": "ws_001",
  "name": "Dev Team Workspace",
  "projectId": "default",
  "type": "TEAM",
  "status": "ENABLE",
  "creator": "admin",
  "createdOn": 1735558575017
}
```

---

## 2. Update Workspace Configuration

**Introduction**

This API is used to update the configuration of a specified workspace. Only the workspace owner or administrators can perform this operation. The request body uses the `id` field to identify the workspace.

**URI**

```
PUT /v1/{project_id}/agent-manager/workspace
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| Content-Type | Yes | String | Default `application/json` |
| X-Auth-Token | Yes | String | User Token |

**Request Body Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| id | Yes | String | Workspace ID |
| name | No | String | Workspace name |
| description | No | String | Workspace description |

**Response Parameters**

Status code: 200

This API has no response body for a successful response.

**Request Example**

```
PUT /v1/{project_id}/agent-manager/workspace HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "id": "ws_001",
  "name": "R&D Team Workspace-Updated",
  "description": "Updated description"
}
```

---

## 3. Delete Workspace

**Introduction**

This API is used to delete a specified workspace. Only the workspace owner can perform this operation. All resources in the workspace will be permanently deleted. The request body uses the `id` field to identify the workspace.

**URI**

```
DELETE /v1/{project_id}/agent-manager/workspace
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| Content-Type | Yes | String | Default `application/json` |
| X-Auth-Token | Yes | String | User Token |

**Request Body Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| id | Yes | String | Workspace ID to delete |

**Response Parameters**

Status code: 200

This API has no response body for a successful response.

**Request Example**

```
DELETE /v1/{project_id}/agent-manager/workspace HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "id": "ws_001"
}
```

---

## 4. Query Workspace Information

**Introduction**

This API is used to query detailed information of a specified workspace, including workspace name, member count, resource count, etc.

**URI**

```
GET /v1/{project_id}/agent-manager/workspace?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| X-Auth-Token | Yes | String | User Token |

**Response Parameters**

| Parameter | Type | Description |
|------|------|------|
| count | Integer | Total number of workspaces |
| workspaceList | Array of Workspace | Workspace list |

**Workspace**

| Parameter | Type | Description |
|------|------|------|
| id | String | Workspace ID |
| name | String | Workspace name |
| projectId | String | Project ID |
| icon | String | Workspace icon |
| description | String | Workspace description |
| tenantId | String | Tenant ID |
| type | String | Workspace type (`PERSON` or `TEAM`) |
| status | String | Workspace status (e.g. `ENABLE`) |
| creator | String | Creator |
| creatorId | String | Creator ID |
| createdOn | Long | Creation time |
| updater | String | Updater |
| updaterId | String | Updater ID |
| updatedOn | Long | Update time |
| role | String | Current user's role in the workspace (e.g. `OWNER`) |

**Request Example**

```
GET /v1/{project_id}/agent-manager/workspace?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**Response Example**

```json
{
  "count": 1,
  "workspaceList": [
    {
      "id": "4c680613d353462fa3d2420eb6cf786f",
      "name": "Personal Workspace",
      "projectId": "default",
      "icon": "data:image/svg+xml;base64,...",
      "description": "Personal workspace",
      "tenantId": "0",
      "type": "PERSON",
      "status": "ENABLE",
      "creator": "admin",
      "creatorId": "admin",
      "createdOn": 1787900850129,
      "updater": "admin",
      "updaterId": "admin",
      "updatedOn": 1787900850129,
      "role": "OWNER"
    }
  ]
}
```

---

## 5. Batch Add Workspace Members

**Introduction**

This API is used to batch add members to a specified workspace, with the ability to set member roles simultaneously.

**URI**

```
POST /v1/{project_id}/agent-manager/workspace/member?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| Content-Type | Yes | String | Default `application/json` |
| X-Auth-Token | Yes | String | User Token |

**Request Body Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| members | Yes | Array of Member | Member list |

**Member**

| Parameter | Required | Type | Description |
|------|------|------|------|
| member_id | Yes | String | User ID |
| member_name | No | String | User name |
| member_source | No | String | Member source (e.g. `IAM`) |
| role | No | String | Member role: `OWNER`, `ADMIN`, `DEVELOPER`, or `OPERATOR`, default `DEVELOPER` |

**Response Parameters**

Status code: 200

This API has no response body for a successful response.

**Request Example**

```
POST /v1/{project_id}/agent-manager/workspace/member?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "members": [
    {
      "member_id": "user_002",
      "member_name": "John Doe",
      "member_source": "IAM",
      "role": "DEVELOPER"
    },
    {
      "member_id": "user_003",
      "member_name": "Jane Smith",
      "member_source": "IAM",
      "role": "OPERATOR"
    }
  ]
}
```

---

## 6. Update Workspace Member Role

**Introduction**

This API is used to update the role of members in a specified workspace. Only the workspace owner or administrators can perform this operation. This API uses the **PATCH** method.

**URI**

```
PATCH /v1/{project_id}/agent-manager/workspace/member?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| Content-Type | Yes | String | Default `application/json` |
| X-Auth-Token | Yes | String | User Token |

**Request Body Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| members | Yes | Array of MemberUpdate | Member list to update |

**MemberUpdate**

| Parameter | Required | Type | Description |
|------|------|------|------|
| member_id | Yes | String | User ID to update role |
| role | Yes | String | New role: `OWNER`, `ADMIN`, `DEVELOPER`, or `OPERATOR` |

**Response Parameters**

Status code: 200

This API has no response body for a successful response.

**Request Example**

```
PATCH /v1/{project_id}/agent-manager/workspace/member?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "members": [
    {
      "member_id": "user_003",
      "role": "OPERATOR"
    }
  ]
}
```

---

## 7. Batch Remove Workspace Members

**Introduction**

This API is used to batch remove members from a specified workspace.

**URI**

```
DELETE /v1/{project_id}/agent-manager/workspace/member?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| Content-Type | Yes | String | Default `application/json` |
| X-Auth-Token | Yes | String | User Token |

**Request Body Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| user_ids | Yes | Array of strings | List of user IDs to remove |

**Response Parameters**

Status code: 200

This API has no response body for a successful response.

**Request Example**

```
DELETE /v1/{project_id}/agent-manager/workspace/member?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "user_ids": ["user_002", "user_003"]
}
```

---

## 8. Transfer Workspace Ownership

**Introduction**

This API is used to transfer workspace ownership to another member. After the transfer, the original owner becomes a regular member. Only the workspace owner can perform this operation.

**URI**

```
PUT /v1/{project_id}/agent-manager/workspace/member/ownership?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| Content-Type | Yes | String | Default `application/json` |
| X-Auth-Token | Yes | String | User Token |

**Request Body Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID |
| next_owner_id | Yes | String | Target user ID to receive ownership, must be a current workspace member |

**Response Parameters**

Status code: 200

This API has no response body for a successful response.

**Request Example**

```
PUT /v1/{project_id}/agent-manager/workspace/member/ownership?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "workspace_id": "ws_001",
  "next_owner_id": "user_002"
}
```

---

## 9. Leave Current Workspace

**Introduction**

This API is used for the current user to leave a workspace. The workspace owner cannot leave directly and must transfer ownership first. No request body is required.

**URI**

```
DELETE /v1/{project_id}/agent-manager/workspace/member/me?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID to leave |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| X-Auth-Token | Yes | String | User Token |

**Response Parameters**

Status code: 200

This API has no response body for a successful response.

**Request Example**

```
DELETE /v1/{project_id}/agent-manager/workspace/member/me?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

---

## 10. Query Workspace Member List

**Introduction**

This API is used to query the member list of a specified workspace with pagination support.

**URI**

```
GET /v1/{project_id}/agent-manager/workspace/member?workspace_id={workspace_id}&page={page}&page_size={page_size}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID |
| page | No | Integer | Page number, default 1 |
| page_size | No | Integer | Page size, default 10 |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| X-Auth-Token | Yes | String | User Token |

**Response Parameters**

Status code: 200

| Parameter | Type | Description |
|------|------|------|
| count | Integer | Total number of members |
| memberList | Array | Member list |

**Request Example**

```
GET /v1/{project_id}/agent-manager/workspace/member?workspace_id={workspace_id}&page=1&page_size=10 HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**Response Example**

```json
{
  "count": 2,
  "memberList": [
    {
      "member_id": "user_001",
      "member_name": "admin",
      "role": "OWNER"
    },
    {
      "member_id": "user_002",
      "member_name": "John Doe",
      "role": "DEVELOPER"
    }
  ]
}
```

---

## 11. Query Workspace Role List

**Introduction**

This API is used to query the available role list for workspace members.

**URI**

```
GET /v1/{project_id}/agent-manager/workspace/member/role?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| X-Auth-Token | Yes | String | User Token |

**Response Parameters**

Status code: 200

| Parameter | Type | Description |
|------|------|------|
| roleList | Array of Role | Role list |

**Role**

| Parameter | Type | Description |
|------|------|------|
| roleId | String | Role ID (e.g. `OWNER`, `ADMIN`, `DEVELOPER`, `OPERATOR`) |
| roleNameCn | String | Role name in Chinese |
| roleNameEn | String | Role name in English |

**Request Example**

```
GET /v1/{project_id}/agent-manager/workspace/member/role?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**Response Example**

```json
{
  "roleList": [
    {
      "roleId": "OWNER",
      "roleNameCn": "所有者",
      "roleNameEn": "Owner"
    },
    {
      "roleId": "ADMIN",
      "roleNameCn": "管理员",
      "roleNameEn": "Admin"
    },
    {
      "roleId": "DEVELOPER",
      "roleNameCn": "开发者",
      "roleNameEn": "Developer"
    },
    {
      "roleId": "OPERATOR",
      "roleNameCn": "操作者",
      "roleNameEn": "Operator"
    }
  ]
}
```

---

## 12. Query IAM Users

**Introduction**

This API is used to query IAM users that can be added to a workspace.

**URI**

```
GET /v1/{project_id}/agent-manager/workspace/users?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| X-Auth-Token | Yes | String | User Token |

**Request Example**

```
GET /v1/{project_id}/agent-manager/workspace/users?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**Response Parameters**

| Parameter | Type | Description |
|------|------|------|
| count | Integer | Total user count |
| user_list | Array of User | User list |

**User**

| Parameter | Type | Description |
|------|------|------|
| user_id | String | User ID |
| user_name | String | User name |

**Response Example**

```json
{
  "count": 1,
  "user_list": [
    {
      "user_id": "user_002",
      "user_name": "Zhang San"
    }
  ]
}
```

---

## 13. Share Resource to Other Workspace

**Introduction**

This API is used to share resources (agents, workflows, tools) from the current workspace to another workspace. After sharing, members of the target workspace can use the shared resource.

**URI**

```
POST /v1/{project_id}/agent-manager/resource/share?workspace_id={workspace_id}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Source workspace ID |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| Content-Type | Yes | String | Default `application/json` |
| X-Auth-Token | Yes | String | User Token |

**Request Body Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| source_workspace_id | No | String | Source workspace ID |
| target_workspace_id | Yes | String | Target workspace ID |
| resource_id | Yes | String | Resource ID to share |
| resource_type | Yes | String | Resource type: `controller`, `workflow`, or `plugin` |

**Response Parameters**

Status code: 200

This API has no response body for a successful response.

**Request Example**

```
POST /v1/{project_id}/agent-manager/resource/share?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Auth-Token: {token}

{
  "target_workspace_id": "ws_002",
  "resource_id": "7c5be653-71b8-48e7-9058-7191ec0f44e8",
  "resource_type": "controller"
}
```

---

## 14. Query Shared Resources

**Introduction**

This API is used to query resources that have been shared to the current workspace by other workspaces.

**URI**

```
GET /v1/{project_id}/agent-manager/resource/share?workspace_id={workspace_id}&resource_type={resource_type}&page={page}&page_size={page_size}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID |
| resource_type | Yes | String | Resource type: `controller`, `workflow`, or `plugin` |
| page | No | Integer | Page number, default 1 |
| page_size | No | Integer | Page size, default 10 |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| X-Auth-Token | Yes | String | User Token |

**Response Parameters**

Status code: 200

| Parameter | Type | Description |
|------|------|------|
| count | Integer | Total number of shared resources |
| resource_list | Array | Shared resource list |

**Request Example**

```
GET /v1/{project_id}/agent-manager/resource/share?workspace_id={workspace_id}&resource_type=controller&page=1&page_size=10 HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**Response Example**

```json
{
  "count": 0,
  "resource_list": []
}
```

---

## 15. Query Shared-by-us Resources

**Introduction**

This API is used to query resources that the current workspace has shared to other workspaces.

**URI**

```
GET /v1/{project_id}/agent-manager/resource/shared?workspace_id={workspace_id}&resource_type={resource_type}&page={page}&page_size={page_size}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID |
| resource_type | Yes | String | Resource type: `controller`, `workflow`, or `plugin` |
| page | No | Integer | Page number, default 1 |
| page_size | No | Integer | Page size, default 10 |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| X-Auth-Token | Yes | String | User Token |

**Request Example**

```
GET /v1/{project_id}/agent-manager/resource/shared?workspace_id={workspace_id}&resource_type=controller&page=1&page_size=10 HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**Response Parameters**

| Parameter | Type | Description |
|------|------|------|
| count | Integer | Total resource count |
| resource_list | Array of Resource | Resource list |

**Response Example**

```json
{
  "count": 0,
  "resource_list": []
}
```

---

## 16. Cancel Resource Share

**Introduction**

This API is used to cancel a resource share, revoking access from the target workspace.

**URI**

```
DELETE /v1/{project_id}/agent-manager/resource/share/{resource_id}?workspace_id={workspace_id}&resource_type={resource_type}
```

**Path Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| project_id | Yes | String | Current tenant project ID |
| resource_id | Yes | String | Resource ID to cancel sharing |

**Query Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| workspace_id | Yes | String | Workspace ID |
| resource_type | Yes | String | Resource type: `controller`, `workflow`, or `plugin` |

**Request Header Parameters**

| Parameter | Required | Type | Description |
|------|------|------|------|
| X-Auth-Token | Yes | String | User Token |

**Response Parameters**

Status code: 200

This API has no response body for a successful response.

**Request Example**

```
DELETE /v1/{project_id}/agent-manager/resource/share/{resource_id}?workspace_id={workspace_id}&resource_type=controller HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

---
