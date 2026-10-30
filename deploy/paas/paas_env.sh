#!/bin/bash
# paas_env.sh —— paas-env.properties 加载器(通用,零部署改动)
#
# 在启动服务前 source 本脚本,把参数文件中的 KEY=VALUE 导出为环境变量:
#     . /path/to/paas_env.sh
# 随后在同一 shell 中启动的服务进程(Java/Python)自动继承这些变量,
# 与 docker-compose 的 environment 注入效果等价。
#
# 设计规则:
#   1. 文件缺失静默退出(不干扰非文件化部署/本地开发)
#   2. 值仍含 '${' 的行跳过(平台占位符未被替换,不注入字面量)
#   3. 非法变量名跳过(防文件被污染后注入任意 shell 代码)
#   4. 幂等:重复 source 结果一致(文件值始终覆盖)
#
# 参数文件定位(按优先级):
#   1. 环境变量 PAAS_ENV_FILE 显式指定
#   2. 本脚本同目录的 paas-env.properties

SELF_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ENV_FILE=${PAAS_ENV_FILE:-${SELF_DIR}/paas-env.properties}

# 文件缺失:静默返回。
# 注意用 return 而非 exit——本脚本设计为被 source,exit 会连带终止调用方 shell;
# 直接执行(非 source)场景下 return 非法,退化为 exit 0。
[ -f "$ENV_FILE" ] || { return 0 2>/dev/null || exit 0; }

echo "[paas_env] loading: ${ENV_FILE}"
while IFS='=' read -r k v; do
  case "$k" in ''|\#*) continue ;; esac
  # 非法变量名跳过
  [[ "$k" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
  # 值中仍含占位符 = 该行未被替换,跳过(不注入 "${xxx}" 字面量)
  [[ "$v" == *'${'* ]] && continue
  export "$k=$v"
done < "$ENV_FILE"
echo "[paas_env] done"
