# quick-chat — 调用智能体对话接口

通过 REST API 调用已发布的智能体应用，发送一条问题并接收回复。

## 前置条件

1. AgentStudio 服务已部署并运行（参见 [部署指南](../../docs/zh/how-to/deploy-service.md)）
2. 已在平台中创建并发布至少一个智能体应用
3. 获取以下信息：
   - `ENDPOINT` — 服务访问地址（默认 `https://100.85.117.17:30001`）
   - `AGENT_ID` — 智能体应用 ID（平台「开发中心 > 智能体管理」中创建并发布后，从应用详情页获取）
   - `WORKSPACE_ID` — 工作空间 ID（平台「工作空间管理」中获取）
   - `MODEL_DEPLOYMENT_ID` — 模型部署 ID（平台「模型管理」中获取已部署的模型 ID）

## 鉴权说明

默认使用 **Simple 鉴权**（`AUTH_SSO_VALIDATE_URL` 留空时自动启用），通过 Cookie `AGENT_SID` 传递 Token，格式为 `userId|projectId`。

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `AUTH_TOKEN` | `testUser\|0` | Simple 鉴权 Token，格式 `userId\|projectId` |
| `PROJECT_ID` | `0` | 项目 ID，与 Token 中的 projectId 一致 |

> 如启用了 SSO 鉴权（配置了 `AUTH_SSO_VALIDATE_URL`），请将 `AUTH_TOKEN` 替换为实际 SSO Token。

## 运行

```bash
AGENT_ID=your_agent_id \
WORKSPACE_ID=your_workspace_id \
MODEL_DEPLOYMENT_ID=your_model_deployment_id \
bash quick-chat.sh "什么是 AgentStudio？"
```

或指定完整参数：

```bash
ENDPOINT=https://100.85.117.17:30001 \
PROJECT_ID=0 \
AGENT_ID=your_agent_id \
WORKSPACE_ID=your_workspace_id \
MODEL_DEPLOYMENT_ID=your_model_deployment_id \
AUTH_TOKEN="testUser|0" \
bash quick-chat.sh "什么是 AgentStudio？"
```

## 预期输出

```json
{
  "event": "message",
  "data": "AgentStudio 是一站式 AI Agent 开发平台……",
  "createdTime": 1760169416635
}
```

## 相关文档

- [REST API 参考](../../docs/zh/reference/rest-api.md) — 完整接口规范
- [快速启动](../../docs/zh/tutorial/01-quick-start.md) — 本地开发环境搭建
- [开发指南](../../docs/zh/how-to/development-guide.md) — SSO 鉴权配置
