#!/bin/bash
#
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
#
#

set -xe

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# 创建必要目录
mkdir -p ${SERVICE_HOME}/tls
mkdir -p /opt/cloud/logs
mkdir -p /opt/cloud/tool

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

# 修改 SpiffWorkflow 中 inclusiveGateway 代码，支持连线循环
PACKAGES_HOME="/usr/local/lib/python3.11/site-packages"
if [ -d "${PACKAGES_HOME}" ]; then
  if [ ! -e ${PACKAGES_HOME}/SpiffWorkflow/bpmn/specs/mixins/inclusive_gateway.py.bak ]; then
    cp ${PACKAGES_HOME}/SpiffWorkflow/bpmn/specs/mixins/inclusive_gateway.py ${PACKAGES_HOME}/SpiffWorkflow/bpmn/specs/mixins/inclusive_gateway.py.bak
    cp ${PACKAGES_HOME}/SpiffWorkflow/bpmn/specs/mixins/unstructured_join.py ${PACKAGES_HOME}/SpiffWorkflow/bpmn/specs/mixins/unstructured_join.py.bak
    sed -i 's%tasks = my_task.workflow.get_tasks(TaskState.READY | TaskState.WAITING, workflow=my_task.workflow)%tasks = my_task.workflow.get_tasks(TaskState.READY | TaskState.WAITING | TaskState.STARTED, workflow=my_task.workflow)  # STARTED /NOT_YET_COMPLETED 也算活跃状态%g' ${PACKAGES_HOME}/SpiffWorkflow/bpmn/specs/mixins/inclusive_gateway.py
    sed -i '95a\\n            # 覆盖原有 check 函数，允许循环\n            import copy\n            def check(spec, path_history=None):\n                path_history = [] if not isinstance(path_history, list) else path_history\n                for parent in spec.inputs:\n                    if parent is self or parent in path_history:\n                        continue\n                    if parent in sources:\n                        return parent\n                    path_history_continue = copy.copy(path_history)\n                    path_history_continue.append(spec)\n                    found = check(parent, path_history=path_history_continue)\n                    if found:\n                        return found\n                return None' ${PACKAGES_HOME}/SpiffWorkflow/bpmn/specs/mixins/inclusive_gateway.py
    sed -i "/for task in tasks/a\            if task._has_state(TaskState.CANCELLED | TaskState.COMPLETED):\n                continue" ${PACKAGES_HOME}/SpiffWorkflow/bpmn/specs/mixins/unstructured_join.py
  fi
fi

# 删除三方包中打印的敏感信息
sed -i "/微信公众号/d" /usr/local/lib/python3.11/site-packages/jionlp/util/help_search.py 2>/dev/null || true

# 去掉mcp调用的ssl认证
sed -i 's/async with httpx.AsyncClient(headers=headers)/async with httpx.AsyncClient(headers=headers, verify=False)/g' /usr/local/lib/python3.11/site-packages/mcp/client/sse.py 2>/dev/null || true
sed -i 's/return httpx\.AsyncClient(\*\*kwargs)/return httpx.AsyncClient(verify=False,\*\*kwargs)/g' /usr/local/lib/python3.11/site-packages/mcp/shared/_httpx_utils.py 2>/dev/null || true

# 执行自定义bugfix（如果存在）
if [ -f "${SCRIPT_DIR}/bugfix.sh" ]; then
  bash ${SCRIPT_DIR}/bugfix.sh
fi

echo "Open AgentBuilder Engine initialization completed."