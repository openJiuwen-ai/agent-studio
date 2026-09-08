# 多智能体 API

---

## 目录

1. [查询对话执行记录](#1-查询对话执行记录)
2. [查询指定多智能体对话详情](#2-查询指定多智能体对话详情)

---

## 1. 查询对话执行记录

**功能介绍**

该接口用于查询指定多智能体应用的对话执行记录，返回该会话中所有执行步骤的概要信息。

**适用场景**

- 查看多智能体对话的完整执行链路
- 排查多智能体对话中的执行问题
- 获取对话中各子智能体的调用情况

**URI**

```
GET /v1/{project_id}/agent-manager/controller/{agent_id}/conversations/{conversation_id}/executions?workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |
| agent_id | 是 | String | 多智能体应用 ID |
| conversation_id | 是 | String | 会话 ID |

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
| count | Integer | 执行记录总数 |
| executions | Array of Execution | 执行记录列表 |

**Execution**

| 参数 | 类型 | 描述 |
|------|------|------|
| execution_id | String | 执行记录 ID |
| agent_id | String | 子智能体 ID |
| agent_name | String | 子智能体名称 |
| status | String | 执行状态 |
| input | String | 输入内容 |
| output | String | 输出内容 |
| start_time | Long | 开始时间 |
| end_time | Long | 结束时间 |
| duration | Long | 执行耗时（毫秒） |

**请求示例**

```
GET /v1/{project_id}/agent-manager/controller/{agent_id}/conversations/{conversation_id}/executions?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**响应示例**

```json
{
  "count": 2,
  "executions": [
    {
      "execution_id": "exec_001",
      "agent_id": "sub_agent_01",
      "agent_name": "搜索助手",
      "status": "success",
      "input": "搜索A12会议室状态",
      "output": "A12会议室在9:00-10:00空闲",
      "start_time": 1735558575017,
      "end_time": 1735558576986,
      "duration": 1969
    },
    {
      "execution_id": "exec_002",
      "agent_id": "sub_agent_02",
      "agent_name": "回复助手",
      "status": "success",
      "input": "根据搜索结果回复用户",
      "output": "A12会议室在9:00到10:00的时间段内是空闲的。",
      "start_time": 1735558576986,
      "end_time": 1735558577011,
      "duration": 25
    }
  ]
}
```

---

## 2. 查询指定多智能体对话详情

**功能介绍**

该接口用于查询多智能体应用中指定执行记录的详细信息，包括子智能体的调用过程、中间结果等。

**适用场景**

- 深入分析多智能体某个执行步骤的详细信息
- 排查多智能体执行链路中的具体问题

**URI**

```
GET /v1/{project_id}/agent-manager/controller/{agent_id}/executions/{execution_id}?workspace_id={workspace_id}
```

**路径参数**

| 参数 | 必选 | 类型 | 描述 |
|------|------|------|------|
| project_id | 是 | String | 当前租户项目 ID |
| agent_id | 是 | String | 多智能体应用 ID |
| execution_id | 是 | String | 执行记录 ID |

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
| execution_id | String | 执行记录 ID |
| agent_id | String | 子智能体 ID |
| agent_name | String | 子智能体名称 |
| status | String | 执行状态 |
| input | String | 输入内容 |
| output | String | 输出内容 |
| steps | Array of Step | 执行步骤详情 |
| start_time | Long | 开始时间 |
| end_time | Long | 结束时间 |
| duration | Long | 执行耗时（毫秒） |

**Step**

| 参数 | 类型 | 描述 |
|------|------|------|
| step_id | String | 步骤 ID |
| step_name | String | 步骤名称 |
| step_type | String | 步骤类型 |
| input | Object | 步骤输入 |
| output | Object | 步骤输出 |
| status | String | 步骤状态 |
| start_time | Long | 开始时间 |
| end_time | Long | 结束时间 |

**请求示例**

```
GET /v1/{project_id}/agent-manager/controller/{agent_id}/executions/{execution_id}?workspace_id={workspace_id} HTTP/1.1
Host: api.example.com
X-Auth-Token: {token}
```

**响应示例**

```json
{
  "execution_id": "exec_001",
  "agent_id": "sub_agent_01",
  "agent_name": "搜索助手",
  "status": "success",
  "input": "搜索A12会议室状态",
  "output": "A12会议室在9:00-10:00空闲",
  "steps": [
    {
      "step_id": "step_01",
      "step_name": "意图识别",
      "step_type": "intent",
      "input": {"query": "搜索A12会议室状态"},
      "output": {"intent": "search_meeting_room"},
      "status": "success",
      "start_time": 1735558575017,
      "end_time": 1735558575500
    },
    {
      "step_id": "step_02",
      "step_name": "插件调用",
      "step_type": "plugin",
      "input": {"intent": "search_meeting_room", "params": {"room": "A12", "time": "9:00-10:00"}},
      "output": {"status": "空闲"},
      "status": "success",
      "start_time": 1735558575500,
      "end_time": 1735558576986
    }
  ],
  "start_time": 1735558575017,
  "end_time": 1735558576986,
  "duration": 1969
}
```

---
