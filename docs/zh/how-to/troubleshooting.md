# 运行问题排查指南

遇到工作流（Workflow）、单智能体（Single-agent）、多智能体（Multi-agent）运行问题时，按以下步骤逐层排查，大部分问题在前三步即可定位。

## 目录

- [第一步：使用平台调试功能（优先）](#第一步使用平台调试功能优先)
- [第二步：浏览器开发者工具](#第二步浏览器开发者工具)
- [第三步：查看服务日志](#第三步查看服务日志)
  - [3.1 看哪个服务的日志](#31-看哪个服务的日志)
  - [3.2 各服务日志位置](#32-各服务日志位置)
  - [3.3 先搜 ERROR 日志](#33-先搜-error-日志)
  - [3.4 ERROR 日志仍不够时，查看关键运行日志](#34-error-日志仍不够时查看关键运行日志)
- [第四步：深度排查](#第四步深度排查)
  - [开启调试日志](#开启调试日志)
  - [全链路追踪](#全链路追踪)
- [典型场景速查](#典型场景速查)

---

## 第一步：使用平台调试功能（优先）

运行后直接查看调试记录，无需看日志。

### 单智能体（Single-agent）— 通用模式

查看运行记录中的调试信息：
- **大模型调用信息**：请求参数、模型响应内容、Token 用量
- **工具调用信息**：调用了哪个工具、入参是什么、返回结果是什么
- **错误信息**：运行中报错的堆栈和描述

### 工作流（Workflow）

查看工作流运行记录：
- **节点报错**：直接定位到哪个节点标红报错
- **报错信息**：点击报错节点查看具体错误描述

### 多智能体（Multi-agent）

查看多智能体运行记录：
- **意图识别结果**：识别到了哪个意图、匹配到哪个子智能体
- **子智能体调用链路**：各子智能体的执行顺序和结果
- **错误信息**：执行中的错误提示

---

## 第二步：浏览器开发者工具

如果第一步的错误信息不够明确，打开浏览器 F12 开发者工具，重新运行后查看网络请求：

1. 切到 **Network** 面板
2. 找到对应的执行请求（通常为 SSE 长连接请求）
3. 查看 **Response**，接口返回的响应中包含前端未展示的错误详情

常见关注点：
- HTTP 状态码非 200 的请求
- SSE 事件流中的 `error` 类型事件
- 响应体中的 `error_message` / `details` 字段

---

## 第三步：查看服务日志

如果前两步仍无法定位，查看后端服务日志。

### 3.1 看哪个服务的日志

| 场景 | 优先查看 |
|------|----------|
| 运行中报错（执行阶段） | **Runtime** 日志，其次检查 Manager 代理日志 |
| 未执行就报错（配置/定义阶段） | **Manager** 日志 |
| SSE 连接异常、超时 | **Runtime** 与 Console/Nginx 日志 |

### 3.2 各服务日志位置

以下为默认部署的日志路径，实际路径以部署配置为准。

| 服务 | 日志目录 | 主日志文件 | 说明 |
|------|----------|-----------|------|
| Manager | `/opt/cloud/studio-manager/logs/` | `studio-agent-manager.log` | 由 `log4j2.xml` 配置，路径可通过 `LOG_PATH` 环境变量修改 |
| Runtime | `./logs/` | `run/jiuwen.log` | 由 `jiuwen/config.yaml` 配置；`log_path` 可通过 `JIUWEN_LOG_PATH` 环境变量覆盖，`log_file` / `output` 等也可在配置文件中自定义 |

> **Runtime 日志补充说明：** Runtime 有两套日志输出：
> - `agent_runtime` 模块的日志（`workflow_logger`、`performance_logger`）默认输出到 **stdout**
> - `jiuwen` 模块的日志由 `jiuwen/config.yaml` 控制，默认 `output: console`，部署时通常改为 `output: log` 写入文件
> - 实际部署中日志文件名可能被定制（如 `common.log`），以实际 `config.yaml` 中的 `log_file` 配置为准

### 3.3 先搜 ERROR 日志

找到日志文件后，**优先按时间范围搜索 ERROR**，往往能直接定位原因：

- **Java 服务**（Manager / Service）：日志中搜索 `ERROR`，堆栈紧跟其后
- **Runtime**（Python）：日志中搜索 `ERROR`，开启 `LOG_VERBOSE=true` 后会输出完整堆栈

搜索时结合 `conversationId` 或 `request-id` 缩小范围，避免被无关错误干扰。这两个 ID 的获取方式：

- **conversationId**：浏览器 F12 → Network → 找到执行请求的 URL 路径中包含的会话 ID；或从平台运行记录中获取
- **request-id**：浏览器 F12 → Network → 找到执行请求 → 查看 Request Headers 中的 `X-Request-Id`

### 3.4 ERROR 日志仍不够时，查看关键运行日志

如果 ERROR 信息不够明确（如只报了超时但不知道卡在哪），按以下关键日志进一步排查。

#### Manager 日志

关注 CRUD 和调度阶段的错误：

```
# 工作流不存在
workflow does not exist, projectId = {}, workflowId = {}

# 工作流嵌套层级超限
Workflow nested exceed max level:{}

# 触发类型错误
Trigger type is wrong. The wrong type is {}. projectId = {}, workflowId = {}

# 单智能体不存在
agent does not exist, projectId = {}, workspaceId = {}, agentId = {}

# DSL转IR失败
dsl to ir error

# 多智能体配置为空
controllerNode.Configs is null
SubController {} configs is null

# 发布元数据获取失败
Get published metadata failed, version may have not been published yet.
```

#### Service 日志

关注请求转发、SSE 通信和执行状态：

```
# === 执行入口 ===
runWorkflow begin, conversationId:{}, workflowId:{}, version:{}, debug:{}, trace:{}
runWorkflow end, resp:{}
runWorkflowStream begin, conversationId:{}, workflowId:{}, debug:{}, trace:{}

# === 请求体（关键！用于确认传给Runtime的参数是否正确）===
JiuWen request param: {}                    # 工作流执行请求体
JiuWen component request param: {}          # 单节点调测请求体
Request jiuwen body is :{}                  # 单智能体执行请求体

# === 单智能体执行过程 ===
conversation is {}, id {}                   # 会话信息
conversation lastUpdateTime:{} agentMetadata updateAt:{} version:{} agentId:{}

# === 插件执行 ===
Start run plugin, name: [{}], input: [{}], latency: [{}]
End run plugin, name: [{}], output: [{}], latency: [{}]

# === 执行结果 ===
Final total answer is: [{}]                 # 单智能体最终回答
Workflow run status:{}, cost:{}             # 工作流执行状态和耗时
Agent task is finish. recive task end message.

# === SSE异常 ===
SSE connection timed out, conversationId [{}]
Fail to send sse, data [{}], reason [{}]

# === 执行失败 ===
workflow run failed: {}
Fail to run agent because [{}]
```

#### Runtime 日志

关注底层执行引擎的详细过程和错误：

**性能阶段日志**（`performance_logger`，INFO 级别，默认可见）：

```
ir_convert|{ms}              # IR转换耗时
node_id_mapping|{ms}         # IR到节点映射耗时
context_creation|{ms}        # 上下文创建耗时
session_creation|{ms}        # 会话创建耗时
inputs_build|{ms}            # 输入构建耗时
pre_exec_total|{ms}          # 执行前总耗时
first_chunk_latency|{ms}     # 首Token延迟
workflow_stream|{ms}         # 流式输出总耗时
total_chunks|{count}         # 总输出块数
```

**请求体日志**（需 `WORKFLOW_LOG_LEVEL=DEBUG`）：

```
IR Execute Request - URL: {method} {url}
IR Execute Request - Headers: {headers}
IR Execute Request - Query Params: {params}
IR Execute Request - Body: {body}           # Runtime收到的完整请求体
```

**错误日志**（需 `WORKFLOW_LOG_LEVEL >= WARNING`）：

```
# 初始化阶段
API_KEY is not configured; workflow execution will fail
Failed to load IR from {path}
Failed to build workflow

# 执行阶段
Workflow execution failed: {e}, type={type}
ReActAgent stream failed: {e}

# 工具注册
Failed to register plugin {name}
Failed to register MCP server {name}
Failed to register tools: {e}

# Skill下载
[SkillDownload] Failed {name}: {e}

# 多智能体
Agent group streaming failed with exception: {e}
```

**LLM调用日志**（需 `LLM_LOG_LEVEL=DEBUG`）：

```
model call request data: {...}     # LLM请求体
model call response data: {...}    # LLM响应体
model call token usage: {...}      # Token消耗
model call latency: {...}          # 调用耗时
model call tool_calls: [...]       # 工具调用信息
model call error: {...}            # 调用错误
```

**多智能体任务调度日志**（需 `JIUWEN_LOG_LEVEL=DEBUG`）：

```
Planning task for message type {type}
Detected Task object in stream: {task_type}
Before execute task in task queue, length = {len}
Stream executing task: {id}, type: {type}
Task stream executed successfully: {id}, execution time: {time}s
Task execution failed: {type}
Starting agent_group.astream for query: {query}
agent_group_stream|{ms}
```

---

## 第四步：深度排查

前三步仍无法定位时，开启调试日志并结合关联ID进行全链路追踪。

### 开启调试日志

#### Runtime (Python)

通过环境变量调整，修改后重启服务生效：

| 环境变量 | 默认值 | 调试值 | 作用 |
|----------|--------|--------|------|
| `WORKFLOW_LOG_LEVEL` | WARNING | **DEBUG** | 工作流/单智能体执行全流程日志 + 请求体 |
| `GRAPH_LOG_LEVEL` | WARNING | **DEBUG** | 图执行引擎日志 |
| `LLM_LOG_LEVEL` | WARNING | **DEBUG** | LLM 调用详情（请求/响应/Token/耗时） |
| `LOG_VERBOSE` | false | **true** | 打印完整异常堆栈 |
| `JIUWEN_LOG_LEVEL` | INFO | **DEBUG** | jiuwen 模块（多智能体/TaskPlanner）日志 |

K8s 环境变量配置参考：

```yaml
env:
  - name: WORKFLOW_LOG_LEVEL
    value: "DEBUG"
  - name: GRAPH_LOG_LEVEL
    value: "DEBUG"
  - name: LLM_LOG_LEVEL
    value: "DEBUG"
  - name: LOG_VERBOSE
    value: "true"
  - name: JIUWEN_LOG_LEVEL
    value: "DEBUG"
```

> **注意：** DEBUG 级别会产生大量日志（特别是 LLM 请求/响应体），排查完毕后务必恢复为 WARNING。

#### Manager / Service (Java)

修改 `log4j2.xml` 中对应 Logger 的 level 即可。

### 全链路追踪

跨服务追踪依赖三个关联 ID，在请求链路中自动透传：

| ID | 含义 | Java MDC Key | Python 日志字段 | HTTP Header |
|----|------|-------------|---------------|-------------|
| request-id | 请求唯一标识 | `request-id` | `request_id` | `X-Request-Id` |
| execution-id | 执行唯一标识 | `task-id` | `execution_id` | `X-Execution-Id` |
| trace-id | 会话追踪 | `request-id` | `trace_id` | conversationId |

追踪方法：

1. 从前端请求中获取 `conversationId` 或浏览器开发者工具中的 `request-id`
2. Service 日志：`grep "request-id值" studio-agent-service.log`
3. Service 日志中找到 `X-Execution-Id`（即 `task-id`）
4. Runtime 日志：用 `execution_id` 或 `trace_id` 过滤对应执行记录
5. 若需回溯管理操作：`grep "request-id值" studio-agent-manager.log`

---

## 典型场景速查

### 工作流（Workflow）执行无输出/超时

```
1. [第一步] 工作流运行记录 → 查看哪个节点报错
2. [第二步] F12 → 查看SSE响应中是否有error事件
3. [第三步] Service日志 → 搜 "SSE connection timed out" 确认是否超时
4. [第三步] Runtime日志 → 搜 "first_chunk_latency" 确认是否有首Token
5. [第四步] Runtime性能日志 → 检查 pre_exec_total 是否异常大
6. [第四步] Runtime日志 → 搜 "Failed to load IR" / "Failed to build workflow"
```

### 单智能体（Single-agent）不调用工具/工具调用失败

```
1. [第一步] 单智能体运行记录 → 查看大模型是否返回了 tool_calls，工具执行结果
2. [第二步] F12 → 查看SSE事件流中 function_call 事件
3. [第三步] Service日志 → 搜 "Start run plugin" / "End run plugin" 查看工具执行
4. [第三步] Service日志 → 搜 "JiuWen request param" 确认请求体中插件配置是否正确
5. [第四步] Runtime日志 → 搜 "Failed to register plugin" / "Failed to register MCP server"
6. [第四步] 设置 LLM_LOG_LEVEL=DEBUG → 查看 "model call tool_calls" 确认LLM是否返回工具调用
```

### 多智能体（Multi-agent）意图识别错误/子智能体不执行

```
1. [第一步] 多智能体运行记录 → 查看意图识别结果和子智能体调用链路
2. [第二步] F12 → 查看SSE事件流中 controller_intermediate 事件
3. [第三步] Service日志 → 搜 "Request jiuwen body" 确认请求体是否正确
4. [第四步] 设置 JIUWEN_LOG_LEVEL=DEBUG → 查看 "Planning task" / "Detected Task" 任务规划
5. [第四步] Runtime日志 → 搜 "Task execution failed" / "Agent group streaming failed"
```

### LLM 调用异常

```
1. [第一步] 单智能体运行记录 → 查看大模型调用信息中的错误
2. [第二步] F12 → 查看响应中模型相关错误
3. [第三步] Service日志 → 搜 "Model chat completion exception"
4. [第四步] 设置 LLM_LOG_LEVEL=DEBUG → 查看 "model call request data" / "model call error"
5. [第四步] Runtime日志 → 搜 "API_KEY is not configured"
```

### 请求参数疑似错误

```
1. [第二步] F12 → 直接查看请求 Payload
2. [第三步] Service日志 → 搜 "JiuWen request param" 查看转发给 Runtime 的请求体
3. [第四步] 设置 WORKFLOW_LOG_LEVEL=DEBUG → Runtime日志搜 "IR Execute Request - Body" 查看 Runtime 实际收到的请求体
```
