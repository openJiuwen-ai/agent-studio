# agent-runtime 可观测性部署指南（Jaeger）

本指南介绍如何在服务器上部署 Jaeger，并让 agent-runtime 把智能体/工作流的运行链路数据（Trace）上报到 Jaeger，便于事后排查与性能分析。

---

## 1. 概述

agent-runtime 在运行单智能体和工作流时，会通过 OpenTelemetry（OTLP 协议）产出链路追踪 Span。将这些 Span 上报到 Jaeger 后，你可以在 Web 界面里：

- 查看每次调用的完整 Span 树（Agent → LLM → 工具 → 子工作流）
- 定位慢调用、报错节点
- 按 `gen_ai.*` 语义属性筛选 LLM 调用

---

## 2. 架构

```
┌───────────────┐   OTLP gRPC :4317    ┌─────────────────────┐
│ agent-runtime │ ───────────────────► │  Jaeger all-in-one  │
│  (智能体执行)  │   或 HTTP  :4318     │  (接收+存储+UI 一体) │
└───────────────┘                      └──────────┬──────────┘
                                                   │
                                           Badger 持久化存储
                                                   │
                                                   ▼
                                      Web UI  http://<IP>:16686
```

- agent-runtime → Jaeger：gRPC（4317）或 HTTP（4318），无需鉴权
- 无需额外 OpenTelemetry Collector，Jaeger all-in-one 原生支持 OTLP 接收

---

## 3. 环境要求

### 3.1 服务器（部署 Jaeger）

| 项 | 要求 |
|----|------|
| 操作系统 | Linux（CentOS 7+ / Ubuntu 20.04+ 等） |
| Docker | 20+ |
| Docker Compose | v2+（`docker compose` 命令） |
| 内存 | ≥ 2GB（all-in-one 含存储） |
| 磁盘 | ≥ 10GB（Badger 数据卷，按追踪量增长） |
| 网络 | 能访问 Docker Hub 拉取镜像（或离线导入，见第 9 节） |

### 3.2 端口放行

在服务器防火墙 / 云安全组放行以下端口：

| 端口 | 用途 | 是否对外 |
|------|------|---------|
| 4317 | OTLP gRPC（agent-runtime 上报） | 仅对 agent-runtime 所在机器开放 |
| 4318 | OTLP HTTP（备选上报） | 仅对 agent-runtime 所在机器开放 |
| 16686 | Jaeger Web UI | 建议仅内网/VPN，公网需加反代鉴权 |

### 3.3 agent-runtime 侧

- agent-runtime 所在机器能访问 Jaeger 服务器的 4317（或 4318）
- 已安装 agent-runtime 并可正常启动

---

## 4. 部署步骤

### 步骤 1：在服务器上安装 Docker（如已安装可跳过）

```bash
# CentOS
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl enable --now docker

# Ubuntu
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
```

国内服务器拉取镜像慢，可配置镜像加速器：

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": ["https://mirror.ccs.tencentyun.com"]
}
EOF
sudo systemctl restart docker
```

验证：`docker version` 与 `docker compose version` 均有输出。

### 步骤 2：部署 Jaeger

将 `docker-compose.yml` 拷贝到服务器任意路径，例如 `/opt/jaeger/`：

`docker-compose.yml` 内容如下：

```yaml
version: "3.8"

services:
  jaeger:
    image: jaegertracing/all-in-one:1.62
    container_name: openjiuwen-jaeger
    environment:
      - COLLECTOR_OTLP_ENABLED=true
    ports:
      - "16686:16686"
      - "4317:4317"
      - "4318:4318"
    volumes:
      - jaeger-data:/badger
    restart: unless-stopped

volumes:
  jaeger-data:
```

```bash
mkdir -p /opt/jaeger
# 将 docker-compose.yml 上传到 /opt/jaeger/
cd /opt/jaeger
docker compose up -d
```

首次启动会自动拉取 `jaegertracing/all-in-one:1.62` 镜像（约 100MB），等待 10~30 秒。

### 步骤 3：验证 Jaeger 服务正常

```bash
# 容器状态应为 Up / healthy
docker compose ps

# 查看日志，确认 "OTLP receiver" 已监听
docker compose logs jaeger | grep -i otlp

# 健康检查接口
curl http://localhost:14269/
```

浏览器访问 `http://<服务器IP>:16686`，能看到 Jaeger UI 首页即说明部署成功。

### 步骤 4：配置 agent-runtime 上报地址

在 agent-runtime 的 `.env` 文件中添加以下配置（对应 `agent_runtime/common/config.py` 的 `OtelSettings`）：

**推荐：gRPC 方式**

```env
OTEL_ENABLED=true
OTEL_EXPORTER_TYPE=otlp
OTEL_PROTOCOL=grpc
OTEL_EXPORTER_ENDPOINT=http://<Jaeger服务器IP>:4317
OTEL_SERVICE_NAME=agent-runtime
OTEL_SAMPLE_RATE=1.0
```

**备选：HTTP 方式**

```env
OTEL_ENABLED=true
OTEL_EXPORTER_TYPE=otlp
OTEL_PROTOCOL=http
OTEL_EXPORTER_ENDPOINT=http://<Jaeger服务器IP>:4318
OTEL_SERVICE_NAME=agent-runtime
OTEL_SAMPLE_RATE=1.0
```

> 说明：
> - `<Jaeger服务器IP>` 替换为实际服务器 IP。若 agent-runtime 也跑在同一台机器的容器里，用宿主机 IP 或 Jaeger 容器名（需在同一 Docker 网络）。
> - HTTP 模式下代码会自动补 `/v1/traces` 路径，无需手动加。
> - 若 agent-runtime 与 Jaeger 同机部署且都用 Docker，建议放同一 compose 网络用服务名 `jaeger` 通信。

### 步骤 5：启动 agent-runtime


启动日志中应出现如下一行，表示 OTel 初始化成功：

```
OpenTelemetry tracer initialized: exporter_type=otlp, endpoint=http://<IP>:4317, protocol=grpc, service_name=agent-runtime, sample_rate=1.0
```

若看到 `OpenTelemetry tracer is disabled (OTEL_ENABLED=false)`，说明 `.env` 未生效或 `OTEL_ENABLED` 未设为 true。

### 步骤 6：产生追踪数据

向 agent-runtime 发起一次智能体对话或工作流调用（通过其 HTTP API 或前端入口）。调用完成后，链路数据会异步批量上报到 Jaeger（默认每 5 秒一批）。

---

## 5. 查看追踪数据

1. 浏览器打开 `http://<Jaeger服务器IP>:16686`
2. 左上 **Service** 下拉选择 `agent-runtime`
3. （可选）在 **Operation** 下拉筛选具体操作，或按 Tags 过滤，例如：
   - `gen_ai.operation.name="chat"` 筛选 LLM 调用
   - `openjiuwen.agent.invoke_type=LLM` 筛选智能体 LLM 节点
   - `error=true` 筛选出错的 Span
4. 点击 **Find Traces**，选择一条 Trace 进入
5. 展开 Span 树，可看到：
   - **Agent 根 Span**（`chain.*`）：整次调用的入口
   - **LLM 子 Span**（`llm.*`，SpanKind=CLIENT）：每次大模型调用，含 `gen_ai.request.model`、prompt/completion（可脱敏）
   - **工具子 Span**（`tool.*`）：插件/工具调用
   - **工作流 Span**（`component.*`）：工作流节点执行

每个 Span 上的属性（Attributes）含耗时 `openjiuwen.elapsed_time`、状态 `openjiuwen.status`、输入输出等。

---

## 6. 配置参数参考

以下环境变量在 agent-runtime 的 `.env` 中配置：

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `OTEL_ENABLED` | false | **总开关**，设为 true 才会上报 |
| `OTEL_EXPORTER_TYPE` | console | `otlp`（上报到 Jaeger）或 `console`（打印到控制台，调试用） |
| `OTEL_PROTOCOL` | grpc | `grpc` 或 `http`，OTLP 传输协议 |
| `OTEL_EXPORTER_ENDPOINT` | (空) | OTLP 接收端地址，如 `http://10.0.0.5:4317` |
| `OTEL_SERVICE_NAME` | agent-runtime | 服务名，Jaeger UI 的 Service 下拉项 |
| `OTEL_SERVICE_VERSION` | (空) | 服务版本，写入 OTel Resource |
| `OTEL_SAMPLE_RATE` | 1.0 | 采样率 0.0~1.0，1.0=全量上报 |
| `OTEL_HEADERS` | {} | OTLP 自定义请求头（Jaeger all-in-one 无需鉴权，留空） |
| `OTEL_SCHEDULE_DELAY_MILLIS` | 5000 | 批量上报间隔（毫秒） |
| `OTEL_EXPORT_TIMEOUT_MS` | 30000 | 单批导出超时（毫秒） |
| `OTEL_MAX_EXPORT_BATCH_SIZE` | 512 | 单批最大 Span 数 |
| `OTEL_REDACTION_ENABLED` | true | 脱敏总开关（开启后 prompt/completion 做 SHA-256 哈希） |
| `OTEL_REDACT_PROMPTS` | (跟随总开关) | 单独控制 prompt 脱敏，设 true/false 覆盖总开关 |
| `OTEL_REDACT_COMPLETIONS` | (跟随总开关) | 单独控制 completion 脱敏 |
| `OTEL_MAX_ATTR_LENGTH` | 4096 | 属性值截断长度（字符） |

---

## 7. 测试验证

发送请求
Postman / curl：

```bash
curl -X POST http://127.0.0.1:8000/v1/orchestration/ir/execute \
  -H "Content-Type: application/json" \
  -d '{
    "conversationId": "test-agent-001",
    "userId": "anonymous",
    "irPath": "<你的IR文件路径>",
    "query": "你好",
    "responseMode": "streaming",
    "agentType": "auto",
    "params": {
      "conversationHistory": [],
      "pluginConfigs": [],
      "globalVariables": {},
      "toolSwitchDict": {},
      "enableHistory": true,
      "environmentVariables": {}
    }
  }'
```


1. 访问 Jaeger UI → Service 选 `agent-runtime` → Find Traces
2. 应看到包含 `chain.*`（根 Span）和 `llm.*`（子 Span）的 Trace
3. 展开 LLM Span，检查 `openjiuwen.agent.outputs` 中是否包含 `usage_metadata`（token 数据）


## 8. 生产环境建议

1. **降低采样率**：生产流量大时设 `OTEL_SAMPLE_RATE=0.1`（10% 采样），开发期保持 `1.0`。
2. **持久化存储**：本方案用 Badger（单机磁盘）。数据量大或需多节点查询，改 `SPAN_STORAGE_TYPE=elasticsearch` 并部署独立 ES 集群。
3. **安全加固**：
   - 16686 UI 无鉴权，公网必须加 nginx 反向代理 + Basic Auth，或仅通过 VPN/堡垒机访问
   - 4317/4318 上报端口用安全组限制来源 IP 为 agent-runtime 机器
4. **资源隔离**：all-in-one 单容器适合中小规模。高吞吐（>1k spans/s）建议拆分为 Jaeger Collector + Query + 独立存储的多容器架构。
5. **数据保留**：Badger 无自动清理策略，按磁盘容量定期 `docker compose down -v` 清理，或对接 ES 时配置索引生命周期。

---


## 9. 离线部署（服务器无法联网）

在能联网的机器上拉取并导出镜像：

```bash
docker pull jaegertracing/all-in-one:1.62
docker save jaegertracing/all-in-one:1.62 -o jaeger.tar
```

将 `jaeger.tar` 和 `docker-compose.yml` 拷贝到离线服务器，然后：

```bash
docker load -i jaeger.tar
docker compose up -d
```

---

## 10. 停止与清理

```bash
cd /opt/jaeger

# 停止服务（保留追踪数据）
docker compose down

# 停止并删除所有追踪数据
docker compose down -v

# 查看实时日志
docker compose logs -f jaeger

# 重启
docker compose restart
```

---

## 11. 常见问题排查

| 现象 | 排查方向 |
|------|---------|
| Jaeger UI 里看不到 `agent-runtime` 服务 | ① 确认 `OTEL_ENABLED=true`；② 确认 `OTEL_EXPORTER_TYPE=otlp`（非 console）；③ 检查 agent-runtime 日志有无 `OpenTelemetry tracer initialized` |
| 日志显示 `OpenTelemetry tracer is disabled` | `.env` 未加载或 `OTEL_ENABLED` 未设为 true，确认 `.env` 路径和环境变量生效 |
| 日志显示 `OpenTelemetry tracer extension not installed` | 缺少 OTel 依赖，执行 `pip install openjiuwen[tracer-otel]` 或确认 `opentelemetry-exporter-otlp-proto-grpc` 已安装 |
| 有初始化日志但 Jaeger 无数据 | ① 网络：从 agent-runtime 机器 `telnet <IP> 4317` 是否通；② 端口：服务器防火墙/安全组是否放行 4317；③ 协议：gRPC 用 4317、HTTP 用 4318，勿混用 |
| 数据有延迟 | 正常现象，BatchSpanProcessor 默认每 5 秒（`OTEL_SCHEDULE_DELAY_MILLIS`）批量上报，调小该值可降低延迟 |
| prompt/completion 显示为 `sha256:xxxx` | 脱敏开启（`OTEL_REDACTION_ENABLED=true`）。查看明文设 `OTEL_REDACT_PROMPTS=false` 和 `OTEL_REDACT_COMPLETIONS=false`（注意合规风险） |
| Jaeger 容器频繁重启 | 检查 `docker compose logs jaeger`；常见为磁盘满或内存不足，清理数据卷或扩容 |
| Span 数量远少于调用次数 | 采样率 `OTEL_SAMPLE_RATE<1.0` 会按概率丢弃 Trace，开发期保持 1.0 |

