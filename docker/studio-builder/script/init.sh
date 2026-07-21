#!/bin/bash
#
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
#
# studio-builder 容器启动初始化 —— 精简版（参考 studio-runtime/script/init.sh）。
# builder 不运行工作流引擎/定时任务/负载均衡，故仅保留目录创建与 TLS 证书初始化，
# 跳过 SpiffWorkflow/mcp ssl 等运行时专属补丁。
#

set -xe

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# 创建必要目录
mkdir -p ${SERVICE_HOME}/tls
mkdir -p /opt/cloud/logs
mkdir -p /opt/cloud/tool
mkdir -p /opt/cloud/logs/agent-builder/run

# 设置目录权限
chmod -R 700 ${SERVICE_HOME}/tls 2>/dev/null || true
chmod -R 755 /opt/cloud/logs 2>/dev/null || true

# 初始化 TLS 证书（从环境变量读取，base64 解码）
if [ -n "${HTTPS_CERT_FILE}" ]; then
  echo "${HTTPS_CERT_FILE}" | base64 --decode > ${SERVICE_HOME}/tls/cert.pem
  chmod 600 ${SERVICE_HOME}/tls/cert.pem
  echo "TLS cert initialized from HTTPS_CERT_FILE env"
fi

if [ -n "${HTTPS_KEY_FILE}" ]; then
  echo "${HTTPS_KEY_FILE}" | base64 --decode > ${SERVICE_HOME}/tls/key.pem
  chmod 600 ${SERVICE_HOME}/tls/key.pem
  echo "TLS key initialized from HTTPS_KEY_FILE env"
fi

# 执行自定义 bugfix（如果存在）
if [ -f "${SCRIPT_DIR}/bugfix.sh" ]; then
  bash ${SCRIPT_DIR}/bugfix.sh
fi

echo "Open AgentBuilder (studio-builder) initialization completed."
