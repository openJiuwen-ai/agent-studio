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
| Manager | `/opt/cloud/studio-manager/logs/` | `studio-agent-manager.log` | 由部署时加载的 `log4j2.xml` 配置：目录由其中 `LOG_PATH` 属性固定（**不是环境变量**，改路径需改该文件后重启）；滚动大小/份数/保留期等由 `LOG_FILE_*` / `PERFORM_FILE_*` / `TRACE_FILE_*` 环境变量覆盖（如 `LOG_FILE_MAX_AGE`，默认 7d） |
| Runtime | `/opt/cloud/logs/`（`LOGGING_LOG_PATH`） | `common.log` | 全进程统一日志：`agent_runtime`、`agent-core`、`jiuwen` 三套 logger 与 uvicorn 均写入同一文件，级别由 `LOG_LEVEL` 统一控制 |

> **Runtime 日志补充说明：** 日志统一汇聚到 `${LOGGING_LOG_PATH}/common.log`，不再按模块拆分文件：
> - `LOGGING_LOG_PATH` 是 Runtime 唯一的日志路径变量（容器内默认 `/opt/cloud/logs`）
> - 级别由 `LOG_LEVEL` 统一驱动（默认 `INFO`）；`JIUWEN_LOG_PATH` / `JIUWEN_LOG_FILE` / `TGF_LOG_DIR` 等旧变量已废弃，设置不再生效
> - 单行日志超过 `LOG_MSG_MAX_LENGTH`（默认 4000 字符）会被截断并追加 `...`，避免超长请求体触发下游日志平台单行上限

### 3.3 先搜 ERROR 日志

找到日志文件后，**优先按时间范围搜索 ERROR**，往往能直接定位原因：

- **Java 服务**（Manager / Service）：日志中搜索 `ERROR`，堆栈紧跟其后
- **Runtime**（Python）：日志中搜索 `ERROR`，堆栈紧随其后（traceback 随 ERROR 始终输出）

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

**性能阶段日志**（`performance_logger`，级别跟随全局 `LOG_LEVEL`；默认 INFO 即输出）：

```
ir_convert|{ms}              # IR转换耗时
ir_build_total|{ms}          # IR -> Workflow 建图总耗时
node_id_mapping|{ms}         # IR到节点映射耗时
context_creation|{ms}        # 上下文创建耗时
session_creation|{ms}        # 会话创建耗时
inputs_build|{ms}            # 输入构建耗时
pre_exec_total|{ms}          # 执行前总耗时
first_chunk_latency|{ms}     # 首Token延迟
workflow_stream|{ms}         # 流式输出总耗时
total_chunks|{count}         # 总输出块数
workflow_cache|hit|miss|downgrade   # 工作流实例缓存命中情况
```

> 性能埋点与其它日志共用 `LOG_LEVEL`：需要静默时把 `LOG_LEVEL` 调到 WARNING，
> 或单独设 `PERFORMANCE_LOG_ENABLED=false` 关掉性能埋点。

**请求体日志**（需 `LOG_LEVEL=DEBUG`）：

```
IR Execute Request - URL: {method} {url}
IR Execute Request - Headers: {headers}
IR Execute Request - Query Params: {params}
IR Execute Request - Body: {body}           # Runtime收到的完整请求体
```

**错误日志**（ERROR/WARNING 级别恒可见，与 `LOG_LEVEL` 一致）：

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

**LLM调用日志**（需 `LOG_LEVEL=DEBUG` 且 `MODEL_CALL_LOGGING_ENABLED=true`）：

```
model call request data: {...}     # LLM请求体
model call response data: {...}    # LLM响应体
model call token usage: {...}      # Token消耗
model call latency: {...}          # 调用耗时
model call tool_calls: [...]       # 工具调用信息
model call error: {...}            # 调用错误
```

**多智能体任务调度日志**（需 `LOG_LEVEL=DEBUG`）：

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

`LOG_LEVEL` 是 runtime 进程内**唯一**的日志级别开关——它同时驱动 uvicorn、agent-core
与 legacy jiuwen logger，且所有日志统一写入 `${LOGGING_LOG_PATH}/common.log`。

| 环境变量 | 默认值 | 调试值 | 作用 |
|----------|--------|--------|------|
| `LOG_LEVEL` | INFO | **DEBUG** | 全进程日志级别：执行全流程 + 请求体 + 性能埋点 + 图执行 + LLM 调用详情 |
| `LOG_MSG_MAX_LENGTH` | 4000 | **40000** | 单条日志的字符上限（整行，仅 console 输出即 common.log）；看完整模型请求体时调大 |
| `PERFORMANCE_LOG_ENABLED` | true | **false** | 只关性能埋点（保留其它日志级别不变） |
| `MODEL_CALL_LOGGING_ENABLED` | false | **true** | 只开模型调用详情（仍需 `LOG_LEVEL<=INFO`） |

K8s 环境变量配置参考：

```yaml
env:
  - name: LOG_LEVEL
    value: "DEBUG"
```

> **注意：** DEBUG 级别会产生大量日志（特别是 LLM 请求/响应体），排查完毕后务必恢复为 INFO。

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
6. [第四步] 设置 LOG_LEVEL=DEBUG 且 MODEL_CALL_LOGGING_ENABLED=true → 查看 "model call tool_calls" 确认LLM是否返回工具调用
```

### 多智能体（Multi-agent）意图识别错误/子智能体不执行

```
1. [第一步] 多智能体运行记录 → 查看意图识别结果和子智能体调用链路
2. [第二步] F12 → 查看SSE事件流中 controller_intermediate 事件
3. [第三步] Service日志 → 搜 "Request jiuwen body" 确认请求体是否正确
4. [第四步] 设置 LOG_LEVEL=DEBUG → 查看 "Planning task" / "Detected Task" 任务规划
5. [第四步] Runtime日志 → 搜 "Task execution failed" / "Agent group streaming failed"
```

### LLM 调用异常

```
1. [第一步] 单智能体运行记录 → 查看大模型调用信息中的错误
2. [第二步] F12 → 查看响应中模型相关错误
3. [第三步] Service日志 → 搜 "Model chat completion exception"
4. [第四步] 设置 LOG_LEVEL=DEBUG 且 MODEL_CALL_LOGGING_ENABLED=true → 查看 "model call request data" / "model call error"
5. [第四步] Runtime日志 → 搜 "API_KEY is not configured"
```

### 请求参数疑似错误

```
1. [第二步] F12 → 直接查看请求 Payload
2. [第三步] Service日志 → 搜 "JiuWen request param" 查看转发给 Runtime 的请求体
3. [第四步] 设置 LOG_LEVEL=DEBUG → Runtime日志搜 "IR Execute Request - Body" 查看 Runtime 实际收到的请求体
```
