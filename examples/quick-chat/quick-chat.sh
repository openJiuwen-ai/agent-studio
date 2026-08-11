#!/bin/bash
# 快速调用智能体对话接口示例
#
# 前置条件：
#   1. AgentStudio 服务已部署并运行
#   2. 已在平台中创建并发布了至少一个智能体应用
#
# 鉴权说明：
#   默认使用 Simple 鉴权，通过 X-Auth-Token 传递 userId|projectId 格式的 Token。
#   默认 Token 为 testUser|0（对应默认用户 testUser、默认项目 0）。
#
# 用法：
#   ENDPOINT=http://localhost:8080 \
#   PROJECT_ID=0 \
#   AGENT_ID=your_agent_id \
#   bash quick-chat.sh "你好"
#
# 参数：
#   $1 — 用户提问内容（可选，默认"你好"）

set -euo pipefail

ENDPOINT="${ENDPOINT:-http://localhost:8080}"
PROJECT_ID="${PROJECT_ID:-0}"
AGENT_ID="${AGENT_ID:?请设置环境变量 AGENT_ID（在平台「开发中心 > 智能体管理」中创建并发布智能体后，从应用详情页获取）}"
AUTH_TOKEN="${AUTH_TOKEN:-testUser|0}"
QUERY="${1:-你好}"
CONVERSATION_ID="conv-$(date +%s)"

echo ">>> 发送问题：$QUERY"
echo ">>> Endpoint:  $ENDPOINT"
echo ">>> Project:   $PROJECT_ID"
echo ">>> Agent:     $AGENT_ID"
echo ">>> AuthToken: $AUTH_TOKEN"
echo ""

curl -s -N "${ENDPOINT}/v1/${PROJECT_ID}/agents/${AGENT_ID}/conversations/${CONVERSATION_ID}" \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: ${AUTH_TOKEN}" \
  -H "stream: false" \
  -d "{\"inputs\": {\"query\": \"${QUERY}\"}}"
