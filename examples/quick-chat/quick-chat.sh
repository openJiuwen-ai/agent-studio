#!/bin/bash
# 快速调用智能体对话接口示例
#
# 前置条件：
#   1. AgentStudio 服务已部署并运行
#   2. 已在平台中创建并发布了至少一个智能体应用
#
# 鉴权说明：
#   默认使用 Simple 鉴权，通过 Cookie AGENT_SID 传递 userId|projectId 格式的 Token。
#   默认 Token 为 testUser|0（对应默认用户 testUser、默认项目 0）。
#
# 用法：
#   ENDPOINT=https://100.85.117.17:30001 \
#   AGENT_ID=your_agent_id \
#   WORKSPACE_ID=your_workspace_id \
#   MODEL_DEPLOYMENT_ID=your_model_deployment_id \
#   bash quick-chat.sh "你好"
#
# 参数：
#   $1 — 用户提问内容（可选，默认"你好"）

set -euo pipefail

ENDPOINT="${ENDPOINT:-https://100.85.117.17:30001}"
PROJECT_ID="${PROJECT_ID:-0}"
AGENT_ID="${AGENT_ID:?请设置环境变量 AGENT_ID（在平台「开发中心 > 智能体管理」中创建并发布智能体后，从应用详情页获取）}"
WORKSPACE_ID="${WORKSPACE_ID:?请设置环境变量 WORKSPACE_ID（在平台「工作空间管理」中获取）}"
MODEL_DEPLOYMENT_ID="${MODEL_DEPLOYMENT_ID:?请设置环境变量 MODEL_DEPLOYMENT_ID（在平台「模型管理」中获取已部署的模型 ID）}"
AUTH_TOKEN="${AUTH_TOKEN:-testUser|0}"
QUERY="${1:-你好}"
CONVERSATION_ID="conv-$(date +%s)"

echo ">>> 发送问题：$QUERY"
echo ">>> Endpoint:  $ENDPOINT"
echo ">>> Project:   $PROJECT_ID"
echo ">>> Agent:     $AGENT_ID"
echo ">>> Workspace: $WORKSPACE_ID"
echo ">>> Model:     $MODEL_DEPLOYMENT_ID"
echo ""

QUERY_ESC="${QUERY//\\/\\\\}"
QUERY_ESC="${QUERY_ESC//\"/\\\"}"
JSON_BODY=$(printf '{"query": "%s", "files": [], "model_deployment_id": "%s"}' "$QUERY_ESC" "$MODEL_DEPLOYMENT_ID")

curl -sSf -k --location \
  "${ENDPOINT}/v1/${PROJECT_ID}/agent-manager/agents/${AGENT_ID}/conversations/${CONVERSATION_ID}?workspace_id=${WORKSPACE_ID}" \
  -H "Content-Type: application/json" \
  -b "AGENT_SID=${AUTH_TOKEN}" \
  -d "${JSON_BODY}"
