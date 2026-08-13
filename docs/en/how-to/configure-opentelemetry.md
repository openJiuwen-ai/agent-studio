# agent-runtime Observability Deployment Guide (Jaeger)

This guide describes how to deploy Jaeger on a server and have agent-runtime report Agent/workflow execution trace data to Jaeger for post-mortem troubleshooting and performance analysis.

---

## 1. Overview

When running single-agent and workflow, agent-runtime produces tracing Spans via OpenTelemetry (OTLP protocol). After reporting these Spans to Jaeger, you can in the Web UI:

- View the complete Span tree for each call (Agent → LLM → Tool → Sub-workflow)
- Locate slow calls and error nodes
- Filter LLM calls by `gen_ai.*` semantic attributes

---

## 2. Architecture

```
┌───────────────┐   OTLP gRPC :4317    ┌─────────────────────┐
│ agent-runtime │ ───────────────────► │  Jaeger all-in-one  │
│  (Agent exec)  │   or HTTP  :4318     │  (receive+store+UI) │
└───────────────┘                      └──────────┬──────────┘
                                                   │
                                           Badger persistent storage
                                                   │
                                                   ▼
                                      Web UI  http://<IP>:16686
```

- agent-runtime → Jaeger: gRPC (4317) or HTTP (4318), no authentication required
- No separate OpenTelemetry Collector needed; Jaeger all-in-one natively supports OTLP ingestion

---

## 3. Requirements

### 3.1 Server (deploying Jaeger)

| Item | Requirement |
|------|-------------|
| OS | Linux (CentOS 7+ / Ubuntu 20.04+ etc.) |
| Docker | 20+ |
| Docker Compose | v2+ (`docker compose` command) |
| Memory | ≥ 2GB (all-in-one includes storage) |
| Disk | ≥ 10GB (Badger data volume, grows with trace volume) |
| Network | Can access Docker Hub to pull images (or offline import, see Section 9) |

### 3.2 Port Firewall

Open the following ports in the server firewall / cloud security group:

| Port | Purpose | External? |
|------|---------|-----------|
| 4317 | OTLP gRPC (agent-runtime reporting) | Only open to the machine running agent-runtime |
| 4318 | OTLP HTTP (alternative reporting) | Only open to the machine running agent-runtime |
| 16686 | Jaeger Web UI | Internal/VPN recommended; public access requires reverse proxy with auth |

### 3.3 agent-runtime Side

- The machine running agent-runtime can reach the Jaeger server's 4317 (or 4318)
- agent-runtime is installed and can start normally

---

## 4. Deployment Steps

### Step 1: Install Docker on the Server (skip if already installed)

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

For servers in China with slow image pulls, configure a mirror accelerator:

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": ["https://mirror.ccs.tencentyun.com"]
}
EOF
sudo systemctl restart docker
```

Verify: `docker version` and `docker compose version` both produce output.

### Step 2: Deploy Jaeger

Copy `docker-compose.yml` to any path on the server, e.g. `/opt/jaeger/`:

`docker-compose.yml` content:

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
# Upload docker-compose.yml to /opt/jaeger/
cd /opt/jaeger
docker compose up -d
```

The first start will automatically pull the `jaegertracing/all-in-one:1.62` image (~100MB); wait 10~30 seconds.

### Step 3: Verify Jaeger Service

```bash
# Container status should be Up / healthy
docker compose ps

# Check logs for "OTLP receiver" listening
docker compose logs jaeger | grep -i otlp

# Health check endpoint
curl http://localhost:14269/
```

Open `http://<server-IP>:16686` in a browser; seeing the Jaeger UI homepage means deployment is successful.

### Step 4: Configure agent-runtime Reporting Address

Add the following configuration to agent-runtime's `.env` file (corresponding to `agent_runtime/common/config.py` `OtelSettings`):

**Recommended: gRPC**

```env
OTEL_ENABLED=true
OTEL_EXPORTER_TYPE=otlp
OTEL_PROTOCOL=grpc
OTEL_EXPORTER_ENDPOINT=http://<Jaeger-server-IP>:4317
OTEL_SERVICE_NAME=agent-runtime
OTEL_SAMPLE_RATE=1.0
```

**Alternative: HTTP**

```env
OTEL_ENABLED=true
OTEL_EXPORTER_TYPE=otlp
OTEL_PROTOCOL=http
OTEL_EXPORTER_ENDPOINT=http://<Jaeger-server-IP>:4318
OTEL_SERVICE_NAME=agent-runtime
OTEL_SAMPLE_RATE=1.0
```

> Notes:
> - Replace `<Jaeger-server-IP>` with the actual server IP. If agent-runtime also runs in a container on the same machine, use the host IP or Jaeger container name (must be on the same Docker network).
> - In HTTP mode, the code automatically appends `/v1/traces`; no need to add manually.
> - If agent-runtime and Jaeger are on the same machine and both use Docker, place them in the same compose network and communicate using the service name `jaeger`.

### Step 5: Start agent-runtime

The startup log should show the following line, indicating OTel initialization success:

```
OpenTelemetry tracer initialized: exporter_type=otlp, endpoint=http://<IP>:4317, protocol=grpc, service_name=agent-runtime, sample_rate=1.0
```

If you see `OpenTelemetry tracer is disabled (OTEL_ENABLED=false)`, the `.env` is not in effect or `OTEL_ENABLED` is not set to true.

### Step 6: Generate Trace Data

Send an Agent conversation or workflow call to agent-runtime (via its HTTP API or frontend entry). After the call completes, trace data is reported to Jaeger asynchronously in batches (default every 5 seconds).

---

## 5. Viewing Trace Data

1. Open `http://<Jaeger-server-IP>:16686` in a browser
2. Select `agent-runtime` from the **Service** dropdown in the upper left
3. (Optional) Filter by specific operation in the **Operation** dropdown, or filter by Tags, e.g.:
   - `gen_ai.operation.name="chat"` to filter LLM calls
   - `openjiuwen.agent.invoke_type=LLM` to filter Agent LLM nodes
   - `error=true` to filter error Spans
4. Click **Find Traces** and select a Trace
5. Expand the Span tree to see:
   - **Agent root Span** (`chain.*`): entry point for the entire call
   - **LLM child Span** (`llm.*`, SpanKind=CLIENT): each LLM call, with `gen_ai.request.model`, prompt/completion (can be redacted)
   - **Tool child Span** (`tool.*`): plugin/tool calls
   - **Workflow Span** (`component.*`): workflow node execution

Each Span's Attributes include duration `openjiuwen.elapsed_time`, status `openjiuwen.status`, inputs/outputs, etc.

---

## 6. Configuration Parameter Reference

The following environment variables are configured in agent-runtime's `.env`:

| Environment variable | Default | Description |
|---------------------|---------|-------------|
| `OTEL_ENABLED` | false | **Master switch**; set to true to enable reporting |
| `OTEL_EXPORTER_TYPE` | console | `otlp` (report to Jaeger) or `console` (print to console, for debugging) |
| `OTEL_PROTOCOL` | grpc | `grpc` or `http`, OTLP transport protocol |
| `OTEL_EXPORTER_ENDPOINT` | (empty) | OTLP receiver address, e.g. `http://10.0.0.5:4317` |
| `OTEL_SERVICE_NAME` | agent-runtime | Service name, appears in Jaeger UI Service dropdown |
| `OTEL_SERVICE_VERSION` | (empty) | Service version, written to OTel Resource |
| `OTEL_SAMPLE_RATE` | 1.0 | Sampling rate 0.0~1.0, 1.0=full reporting |
| `OTEL_HEADERS` | {} | OTLP custom request headers (Jaeger all-in-one needs no auth, leave empty) |
| `OTEL_SCHEDULE_DELAY_MILLIS` | 5000 | Batch reporting interval (ms) |
| `OTEL_EXPORT_TIMEOUT_MS` | 30000 | Single batch export timeout (ms) |
| `OTEL_MAX_EXPORT_BATCH_SIZE` | 512 | Max Spans per batch |
| `OTEL_REDACTION_ENABLED` | true | Redaction master switch (when enabled, prompt/completion are SHA-256 hashed) |
| `OTEL_REDACT_PROMPTS` | (follows master switch) | Independently control prompt redaction; set true/false to override |
| `OTEL_REDACT_COMPLETIONS` | (follows master switch) | Independently control completion redaction |
| `OTEL_MAX_ATTR_LENGTH` | 4096 | Attribute value truncation length (characters) |

---

## 7. Test Verification

Send a request via Postman / curl:

```bash
curl -X POST http://127.0.0.1:8000/v1/orchestration/ir/execute \
  -H "Content-Type: application/json" \
  -d '{
    "conversationId": "test-agent-001",
    "userId": "anonymous",
    "irPath": "<your-IR-file-path>",
    "query": "hello",
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

1. Go to Jaeger UI → Service select `agent-runtime` → Find Traces
2. You should see a Trace containing `chain.*` (root Span) and `llm.*` (child Span)
3. Expand the LLM Span and check whether `openjiuwen.agent.outputs` contains `usage_metadata` (token data)

## 8. Production Environment Recommendations

1. **Reduce sampling rate**: In production with high traffic, set `OTEL_SAMPLE_RATE=0.1` (10% sampling); keep `1.0` during development.
2. **Persistent storage**: This solution uses Badger (single-machine disk). For large data volumes or multi-node queries, switch to `SPAN_STORAGE_TYPE=elasticsearch` and deploy a separate ES cluster.
3. **Security hardening**:
   - The 16686 UI has no authentication; public access must add nginx reverse proxy + Basic Auth, or access only via VPN/bastion host
   - Restrict source IPs for 4317/4318 reporting ports to agent-runtime machines via security groups
4. **Resource isolation**: all-in-one single container is suitable for small-to-medium scale. For high throughput (>1k spans/s), consider splitting into Jaeger Collector + Query + independent storage multi-container architecture.
5. **Data retention**: Badger has no auto-cleanup policy; periodically `docker compose down -v` to clean up based on disk capacity, or configure index lifecycle management when using ES.

---

## 9. Offline Deployment (server without internet)

On a machine with internet, pull and export the image:

```bash
docker pull jaegertracing/all-in-one:1.62
docker save jaegertracing/all-in-one:1.62 -o jaeger.tar
```

Copy `jaeger.tar` and `docker-compose.yml` to the offline server, then:

```bash
docker load -i jaeger.tar
docker compose up -d
```

---

## 10. Stop and Clean Up

```bash
cd /opt/jaeger

# Stop service (retain trace data)
docker compose down

# Stop and delete all trace data
docker compose down -v

# View real-time logs
docker compose logs -f jaeger

# Restart
docker compose restart
```

---

## 11. Common Issue Troubleshooting

| Symptom | Troubleshooting Direction |
|---------|--------------------------|
| `agent-runtime` service not visible in Jaeger UI | ① Confirm `OTEL_ENABLED=true`; ② Confirm `OTEL_EXPORTER_TYPE=otlp` (not console); ③ Check agent-runtime logs for `OpenTelemetry tracer initialized` |
| Log shows `OpenTelemetry tracer is disabled` | `.env` not loaded or `OTEL_ENABLED` not set to true; confirm `.env` path and environment variables are in effect |
| Log shows `OpenTelemetry tracer extension not installed` | Missing OTel dependency; run `pip install openjiuwen[tracer-otel]` or confirm `opentelemetry-exporter-otlp-proto-grpc` is installed |
| Initialization log present but no data in Jaeger | ① Network: from agent-runtime machine, `telnet <IP> 4317` reachable?; ② Port: server firewall/security group opened 4317?; ③ Protocol: gRPC uses 4317, HTTP uses 4318, do not mix |
| Data has delay | Normal behavior; BatchSpanProcessor reports in batches every 5 seconds (`OTEL_SCHEDULE_DELAY_MILLIS`) by default; reduce this value to lower latency |
| prompt/completion shows as `sha256:xxxx` | Redaction enabled (`OTEL_REDACTION_ENABLED=true`). To view plaintext, set `OTEL_REDACT_PROMPTS=false` and `OTEL_REDACT_COMPLETIONS=false` (note compliance risks) |
| Jaeger container restarts frequently | Check `docker compose logs jaeger`; common causes are full disk or insufficient memory; clean data volume or expand capacity |
| Span count far fewer than call count | Sampling rate `OTEL_SAMPLE_RATE<1.0` will probabilistically drop Traces; keep 1.0 during development |
