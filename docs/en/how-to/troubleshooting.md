# Troubleshooting Guide

When encountering issues with workflows (Workflow), single-agent, or multi-agent, follow the steps below to troubleshoot layer by layer. Most issues can be located in the first three steps.

## Table of Contents

- [Step 1: Use Platform Debug Features (Priority)](#step-1-use-platform-debug-features-priority)
- [Step 2: Browser Developer Tools](#step-2-browser-developer-tools)
- [Step 3: Check Service Logs](#step-3-check-service-logs)
  - [3.1 Which Service Logs to Check](#31-which-service-logs-to-check)
  - [3.2 Service Log Locations](#32-service-log-locations)
  - [3.3 Search ERROR Logs First](#33-search-error-logs-first)
  - [3.4 When ERROR Logs Are Insufficient, Check Key Runtime Logs](#34-when-error-logs-are-insufficient-check-key-runtime-logs)
- [Step 4: Deep Troubleshooting](#step-4-deep-troubleshooting)
  - [Enable Debug Logging](#enable-debug-logging)
  - [Full-Chain Tracing](#full-chain-tracing)
- [Common Scenario Quick Reference](#common-scenario-quick-reference)

---

## Step 1: Use Platform Debug Features (Priority)

After running, directly check the debug records — no need to look at logs.

### Single-agent — General Mode

Check debug information in the run records:
- **LLM call info**: request parameters, model response content, token usage
- **Tool call info**: which tool was called, what the input was, what the result was
- **Error info**: error stack traces and descriptions during execution

### Workflow

Check workflow run records:
- **Node errors**: directly locate which node is highlighted in red
- **Error info**: click the error node to view the specific error description

### Multi-agent

Check multi-agent run records:
- **Intent recognition results**: which intent was recognized, which sub-agent was matched
- **Sub-agent call chain**: execution order and results of each sub-agent
- **Error info**: error prompts during execution

---

## Step 2: Browser Developer Tools

If the error information from Step 1 is not clear enough, open the browser F12 developer tools, re-run, and check the network requests:

1. Switch to the **Network** panel
2. Find the corresponding execution request (usually an SSE long-connection request)
3. Check the **Response** — the response returned by the API contains error details not displayed on the frontend

Common points of interest:
- Requests with non-200 HTTP status codes
- `error` type events in the SSE event stream
- `error_message` / `details` fields in the response body

---

## Step 3: Check Service Logs

If the first two steps still cannot locate the issue, check the backend service logs.

### 3.1 Which Service Logs to Check

| Scenario | Priority |
|----------|----------|
| Error during execution (execution phase) | **Runtime** logs, then check Manager agent logs |
| Error before execution (config/definition phase) | **Manager** logs |
| SSE connection issues, timeouts | **Runtime** and Console/Nginx logs |

### 3.2 Service Log Locations

The following are default deployment log paths; actual paths depend on deployment configuration.

| Service | Log directory | Main log file | Description |
|---------|--------------|--------------|-------------|
| Manager | `/opt/cloud/studio-manager/logs/` | `studio-agent-manager.log` | Configured by the `log4j2.xml` loaded at deployment: the directory is fixed by its `LOG_PATH` property (**not an env var** — edit the file and restart to change it); rollover size/count/retention are overridden by `LOG_FILE_*` / `PERFORM_FILE_*` / `TRACE_FILE_*` env vars (e.g. `LOG_FILE_MAX_AGE`, default 7d) |
| Runtime | `/opt/cloud/logs/` (`LOGGING_LOG_PATH`) | `common.log` | Single unified log: `agent_runtime`, `agent-core` and `jiuwen` loggers plus uvicorn all write to the same file; level controlled by `LOG_LEVEL` |

> **Runtime log notes:** All Runtime logs are aggregated into `${LOGGING_LOG_PATH}/common.log`; there are no per-module log files:
> - `LOGGING_LOG_PATH` is the only log path variable for Runtime (defaults to `/opt/cloud/logs` in containers)
> - The level is driven by `LOG_LEVEL` (default `INFO`); legacy variables such as `JIUWEN_LOG_PATH` / `JIUWEN_LOG_FILE` / `TGF_LOG_DIR` are deprecated and no longer take effect
> - Lines longer than `LOG_MSG_MAX_LENGTH` (default 4000 characters) are truncated with a trailing `...` to stay under downstream log platform per-line limits

### 3.3 Search ERROR Logs First

After finding the log file, **search for ERROR by time range first** — this often directly locates the cause:

- **Java services** (Manager / Service): search for `ERROR` in logs; stack traces follow immediately
- **Runtime** (Python): search for `ERROR` in logs; with `LOG_VERBOSE=true` enabled, full stack traces are output

When searching, use `conversationId` or `request-id` to narrow the scope and avoid interference from unrelated errors. How to obtain these two IDs:

- **conversationId**: Browser F12 → Network → find the conversation ID in the execution request URL path; or get it from platform run records
- **request-id**: Browser F12 → Network → find the execution request → check `X-Request-Id` in Request Headers

### 3.4 When ERROR Logs Are Insufficient, Check Key Runtime Logs

If the ERROR information is not clear enough (e.g. only a timeout is reported but you don't know where it's stuck), further troubleshoot using the following key logs.

#### Manager Logs

Focus on CRUD and scheduling phase errors:

```
# Workflow does not exist
workflow does not exist, projectId = {}, workflowId = {}

# Workflow nesting exceeds max level
Workflow nested exceed max level:{}

# Trigger type error
Trigger type is wrong. The wrong type is {}. projectId = {}, workflowId = {}

# Single-agent does not exist
agent does not exist, projectId = {}, workspaceId = {}, agentId = {}

# DSL to IR conversion failed
dsl to ir error

# Multi-agent config is empty
controllerNode.Configs is null
SubController {} configs is null

# Published metadata retrieval failed
Get published metadata failed, version may have not been published yet.
```

#### Service Logs

Focus on request forwarding, SSE communication, and execution status:

```
# === Execution entry ===
runWorkflow begin, conversationId:{}, workflowId:{}, version:{}, debug:{}, trace:{}
runWorkflow end, resp:{}
runWorkflowStream begin, conversationId:{}, workflowId:{}, debug:{}, trace:{}

# === Request body (key! used to confirm params passed to Runtime are correct) ===
JiuWen request param: {}                    # Workflow execution request body
JiuWen component request param: {}          # Single-node debug request body
Request jiuwen body is :{}                  # Single-agent execution request body

# === Single-agent execution process ===
conversation is {}, id {}                   # Conversation info
conversation lastUpdateTime:{} agentMetadata updateAt:{} version:{} agentId:{}

# === Plugin execution ===
Start run plugin, name: [{}], input: [{}], latency: [{}]
End run plugin, name: [{}], output: [{}], latency: [{}]

# === Execution results ===
Final total answer is: [{}]                 # Single-agent final answer
Workflow run status:{}, cost:{}             # Workflow execution status and duration
Agent task is finish. recive task end message.

# === SSE exceptions ===
SSE connection timed out, conversationId [{}]
Fail to send sse, data [{}], reason [{}]

# === Execution failure ===
workflow run failed: {}
Fail to run agent because [{}]
```

#### Runtime Logs

Focus on the detailed process and errors of the underlying execution engine:

**Performance phase logs** (`performance_logger`, follows the global `LOG_LEVEL`; emitted at the default INFO):

```
ir_convert|{ms}              # IR conversion duration
ir_build_total|{ms}          # Total IR -> Workflow graph build duration
node_id_mapping|{ms}         # IR to node mapping duration
context_creation|{ms}        # Context creation duration
session_creation|{ms}        # Session creation duration
inputs_build|{ms}            # Input build duration
pre_exec_total|{ms}          # Total pre-execution duration
first_chunk_latency|{ms}     # First token latency
workflow_stream|{ms}         # Total streaming output duration
total_chunks|{count}         # Total output chunks
workflow_cache|hit|miss|downgrade   # Workflow instance cache outcome
```

> Performance instrumentation shares `LOG_LEVEL` with every other log. To silence
> it, raise `LOG_LEVEL` to WARNING, or set `PERFORMANCE_LOG_ENABLED=false` to
> turn off the performance instrumentation alone.

**Request body logs** (requires `LOG_LEVEL=DEBUG`):

```
IR Execute Request - URL: {method} {url}
IR Execute Request - Headers: {headers}
IR Execute Request - Query Params: {params}
IR Execute Request - Body: {body}           # Complete request body received by Runtime
```

**Error logs** (ERROR/WARNING are always visible, consistent with `LOG_LEVEL`):

```
# Initialization phase
API_KEY is not configured; workflow execution will fail
Failed to load IR from {path}
Failed to build workflow

# Execution phase
Workflow execution failed: {e}, type={type}
ReActAgent stream failed: {e}

# Tool registration
Failed to register plugin {name}
Failed to register MCP server {name}
Failed to register tools: {e}

# Skill download
[SkillDownload] Failed {name}: {e}

# Multi-agent
Agent group streaming failed with exception: {e}
```

**LLM call logs** (requires `LOG_LEVEL=DEBUG` and `MODEL_CALL_LOGGING_ENABLED=true`):

```
model call request data: {...}     # LLM request body
model call response data: {...}    # LLM response body
model call token usage: {...}      # Token consumption
model call latency: {...}          # Call duration
model call tool_calls: [...]       # Tool call info
model call error: {...}            # Call error
```

**Multi-agent task scheduling logs** (requires `LOG_LEVEL=DEBUG`):

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

## Step 4: Deep Troubleshooting

When the first three steps still cannot locate the issue, enable debug logging and use correlation IDs for full-chain tracing.

### Enable Debug Logging

#### Runtime (Python)

Adjust via environment variables; restart the service after changes:

`LOG_LEVEL` is the **only** log level switch for the runtime process — it drives
uvicorn, agent-core and the legacy jiuwen logger alike, and every log line is
written to `${LOGGING_LOG_PATH}/common.log`.

| Environment variable | Default | Debug value | Purpose |
|---------------------|---------|-------------|---------|
| `LOG_LEVEL` | INFO | **DEBUG** | Process-wide level: execution flow + request body + performance instrumentation + graph engine + LLM call details |
| `LOG_MSG_MAX_LENGTH` | 4000 | **40000** | Max characters per log line (whole line, console output only, i.e. common.log); raise it to see full model request bodies |
| `LOG_VERBOSE` | false | **true** | Print full exception stack traces |
| `PERFORMANCE_LOG_ENABLED` | true | **false** | Disable performance instrumentation only, leaving the level untouched |
| `MODEL_CALL_LOGGING_ENABLED` | false | **true** | Enable LLM call details only (still gated by `LOG_LEVEL<=INFO`) |

K8s environment variable configuration reference:

```yaml
env:
  - name: LOG_LEVEL
    value: "DEBUG"
  - name: LOG_VERBOSE
    value: "true"
```

> **Note:** DEBUG level produces a large amount of logs (especially LLM request/response bodies); be sure to restore to INFO after troubleshooting.

#### Manager / Service (Java)

Modify the level of the corresponding Logger in `log4j2.xml`.

### Full-Chain Tracing

Cross-service tracing relies on three correlation IDs, automatically propagated in the request chain:

| ID | Meaning | Java MDC Key | Python log field | HTTP Header |
|----|---------|-------------|-----------------|-------------|
| request-id | Request unique identifier | `request-id` | `request_id` | `X-Request-Id` |
| execution-id | Execution unique identifier | `task-id` | `execution_id` | `X-Execution-Id` |
| trace-id | Conversation tracking | `request-id` | `trace_id` | conversationId |

Tracing method:

1. Get `conversationId` from the frontend request or `request-id` from browser developer tools
2. Service logs: `grep "request-id-value" studio-agent-service.log`
3. Find `X-Execution-Id` (i.e. `task-id`) in Service logs
4. Runtime logs: filter corresponding execution records using `execution_id` or `trace_id`
5. If you need to trace management operations: `grep "request-id-value" studio-agent-manager.log`

---

## Common Scenario Quick Reference

### Workflow Execution No Output / Timeout

```
1. [Step 1] Workflow run records → check which node has an error
2. [Step 2] F12 → check if there are error events in SSE response
3. [Step 3] Service logs → search "SSE connection timed out" to confirm timeout
4. [Step 3] Runtime logs → search "first_chunk_latency" to confirm if there's a first token
5. [Step 4] Runtime performance logs → check if pre_exec_total is abnormally large
6. [Step 4] Runtime logs → search "Failed to load IR" / "Failed to build workflow"
```

### Single-agent Not Calling Tools / Tool Call Failure

```
1. [Step 1] Single-agent run records → check if LLM returned tool_calls, tool execution results
2. [Step 2] F12 → check function_call events in SSE event stream
3. [Step 3] Service logs → search "Start run plugin" / "End run plugin" to check tool execution
4. [Step 3] Service logs → search "JiuWen request param" to confirm plugin config in request body
5. [Step 4] Runtime logs → search "Failed to register plugin" / "Failed to register MCP server"
6. [Step 4] Set LOG_LEVEL=DEBUG and MODEL_CALL_LOGGING_ENABLED=true → check "model call tool_calls" to confirm LLM returned tool calls
```

### Multi-agent Intent Recognition Error / Sub-agent Not Executing

```
1. [Step 1] Multi-agent run records → check intent recognition results and sub-agent call chain
2. [Step 2] F12 → check controller_intermediate events in SSE event stream
3. [Step 3] Service logs → search "Request jiuwen body" to confirm request body
4. [Step 4] Set LOG_LEVEL=DEBUG → check "Planning task" / "Detected Task" task planning
5. [Step 4] Runtime logs → search "Task execution failed" / "Agent group streaming failed"
```

### LLM Call Exception

```
1. [Step 1] Single-agent run records → check errors in LLM call info
2. [Step 2] F12 → check model-related errors in response
3. [Step 3] Service logs → search "Model chat completion exception"
4. [Step 4] Set LOG_LEVEL=DEBUG and MODEL_CALL_LOGGING_ENABLED=true → check "model call request data" / "model call error"
5. [Step 4] Runtime logs → search "API_KEY is not configured"
```

### Suspected Request Parameter Error

```
1. [Step 2] F12 → directly view request Payload
2. [Step 3] Service logs → search "JiuWen request param" to view request body forwarded to Runtime
3. [Step 4] Set LOG_LEVEL=DEBUG → Runtime logs search "IR Execute Request - Body" to view actual request body received by Runtime
```
