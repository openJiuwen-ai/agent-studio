# Webhook Server Setup Guide

The webhook server exposes OpenJiuwen workflows and agents as plain HTTP endpoints.
Any tool that can make an HTTP request — n8n, Zapier, Make, curl, CI pipelines,
custom scripts — can trigger them without a bot account.

---

## Prerequisites

- OpenJiuwen backend running and accessible
- Python dependencies installed: `pip install -r channels/requirements.txt`

---

## Step 1 — Start the Server

From the project root:

```bash
python -m connect.adapters.channels.run webhook
```

The server starts on `http://0.0.0.0:8080` by default. You should see:

```
✅ Connected to OpenJiuwen backend at http://localhost:8000
🌐 OpenJiuwen Webhook Server running on http://0.0.0.0:8080
   Docs: http://0.0.0.0:8080/docs
```

### Common options

```bash
# Custom port
python -m connect.adapters.channels.run webhook --port 9000

# Custom backend URL
python -m connect.adapters.channels.run webhook --backend-url http://my-server:8000

# Static backend token (requests don't need to supply their own)
python -m connect.adapters.channels.run webhook --token eyJhbGci...

# Protect the server with an API key
python -m connect.adapters.channels.run webhook --api-key mysecret

# All together
python -m connect.adapters.channels.run webhook --port 9000 --backend-url http://my-server:8000 --token eyJhbGci... --api-key mysecret
```

All options can also be set via environment variables:

| Option | Env var |
|---|---|
| `--host` | `WEBHOOK_HOST` |
| `--port` | `WEBHOOK_PORT` |
| `--backend-url` | `BACKEND_URL` |
| `--token` | `ACCESS_TOKEN` |
| `--api-key` | `WEBHOOK_API_KEY` |

---

## Step 2 — Explore the API

Open **http://localhost:8080/docs** in your browser.

FastAPI generates interactive documentation (Swagger UI) automatically.
You can read the request/response schemas and try every endpoint directly from the browser.

---

## Step 3 — Authenticate

The server resolves the backend token from (highest priority first):

1. **`X-Token` header**
   ```bash
   curl -H "X-Token: eyJhbGci..."
   ```

2. **`Authorization: Bearer` header**
   ```bash
   curl -H "Authorization: Bearer eyJhbGci..."
   ```

3. **Static token** configured at startup via `--token` / `ACCESS_TOKEN`

### Login via API

If you don't have a token, call `/auth/login` once to get one:

```bash
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "you@example.com", "password": "yourpassword"}'
```

```json
{
  "success": true,
  "token": "eyJhbGci...",
  "space_id": "your-space-id",
  "refresh_token": "...",
  "error": null
}
```

After a successful login the Swagger UI (`/docs`) stores the token automatically — all subsequent requests in that session are authenticated without any extra steps.

---

## Step 4 — Make Requests

### Health check

```bash
curl http://localhost:8080/health
```

```json
{"webhook": "ok", "backend": {"status": "healthy"}}
```

---

### Workflows

#### List all workflows

```bash
curl http://localhost:8080/workflows/list \
  -H "X-Token: eyJhbGci..."
```

#### Search workflows

```bash
curl "http://localhost:8080/workflows/search?keyword=weather" \
  -H "X-Token: eyJhbGci..."
```

#### Get workflow details

```bash
curl "http://localhost:8080/workflows/get?workflow_id=your-workflow-id" \
  -H "X-Token: eyJhbGci..."
```

#### Execute a workflow

```bash
curl -X POST http://localhost:8080/workflows/execute \
  -H "Content-Type: application/json" \
  -H "X-Token: eyJhbGci..." \
  -d '{
    "workflow_id": "your-workflow-id",
    "inputs": {
      "param1": "value1"
    }
  }'
```

Response:
```json
{
  "success": true,
  "outputs": {
    "result": "..."
  },
  "error": null
}
```

---

### Agents

#### List all agents

```bash
curl http://localhost:8080/agents/list \
  -H "X-Token: eyJhbGci..."
```

#### Search agents

```bash
curl "http://localhost:8080/agents/search?keyword=support" \
  -H "X-Token: eyJhbGci..."
```

#### Send a single message to an agent

```bash
curl -X POST http://localhost:8080/agents/execute \
  -H "Content-Type: application/json" \
  -H "X-Token: eyJhbGci..." \
  -d '{
    "agent_id": "your-agent-id",
    "message": "Hello, how can you help me?"
  }'
```

Response:
```json
{
  "success": true,
  "text": "I can help you with...",
  "conversation_id": "3f2a1b4c-...",
  "error": null
}
```

#### Continue a conversation

Pass `conversation_id` from the previous response to maintain context:

```bash
curl -X POST http://localhost:8080/agents/execute \
  -H "Content-Type: application/json" \
  -H "X-Token: eyJhbGci..." \
  -d '{
    "agent_id": "your-agent-id",
    "message": "Tell me more",
    "conversation_id": "3f2a1b4c-..."
  }'
```

---

## All Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Webhook server and backend health |
| `POST` | `/auth/login` | Exchange credentials for a token |
| `GET` | `/workflows/list` | List all workflows |
| `GET` | `/workflows/search?keyword=...` | Search workflows by name |
| `GET` | `/workflows/get?workflow_id=...` | Get workflow details |
| `POST` | `/workflows/execute` | Execute a workflow and return outputs |
| `GET` | `/agents/list` | List all agents |
| `GET` | `/agents/search?keyword=...` | Search agents by name |
| `POST` | `/agents/execute` | Send a message to an agent and get a reply |

---

## Protecting the Server with an API Key

If started with `--api-key`, every request must include the header:

```bash
curl -X POST http://localhost:8080/workflows/execute \
  -H "X-API-Key: mysecret" \
  -H "X-Token: eyJhbGci..." \
  -H "Content-Type: application/json" \
  -d '{"workflow_id": "xyz", "inputs": {}}'
```

---

## Connecting from External Tools

### n8n

1. Add an **HTTP Request** node
2. Method: `POST`
3. URL: `http://your-server:8080/workflows/execute`
4. Body (JSON):
   ```json
   {
     "workflow_id": "{{ $json.workflow_id }}",
     "inputs": {{ $json.inputs }}
   }
   ```
5. Add header `X-API-Key: <your-key>` if using API key protection
6. Add header `X-Token: <your-token>`

### curl / scripts

```bash
#!/bin/bash
RESULT=$(curl -s -X POST http://localhost:8080/workflows/execute \
  -H "Content-Type: application/json" \
  -H "X-Token: $BACKEND_TOKEN" \
  -d "{\"workflow_id\": \"$WORKFLOW_ID\", \"inputs\": {}}")
echo $RESULT | python3 -m json.tool
```

### GitHub Actions

```yaml
- name: Run OpenJiuwen workflow
  run: |
    curl -X POST ${{ secrets.WEBHOOK_URL }}/workflows/execute \
      -H "X-API-Key: ${{ secrets.WEBHOOK_API_KEY }}" \
      -H "X-Token: ${{ secrets.BACKEND_TOKEN }}" \
      -H "Content-Type: application/json" \
      -d '{"workflow_id": "${{ vars.WORKFLOW_ID }}", "inputs": {}}'
```

---

## Notes

- The server is **synchronous per request** — it blocks until the workflow/agent completes.
  Set generous HTTP timeouts for long-running workflows.
- There is no per-user session management — all requests use the same backend token.
- To expose the server publicly (e.g. for Zapier webhooks), put it behind a reverse proxy
  (nginx, Caddy) with HTTPS. Always use `--api-key` when exposed publicly.
