#!/bin/bash
#
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
#
# studio-builder 启动入口 —— 参考 studio-runtime/script/start.sh，去掉 cron/nginx
# （builder 不运行定时任务与负载均衡）。后台 nohup 拉起服务进程，主循环保活容器。
#

umask 0027

SHELL_DIR=$(cd `dirname $0`; pwd)

function main() {
  chmod 750 ${SERVICE_HOME}

  bash ${SHELL_DIR}/start_server.sh
}

main

# 服务以 nohup 后台运行，主循环保持容器存活
while [ 1 ]; do
  sleep 30
done
