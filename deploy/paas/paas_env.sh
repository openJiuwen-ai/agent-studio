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
#   2. CRLF 行尾 CR 剥离 + k/v 首尾空白裁剪(评审修订 2026-11-03:
#      Windows/平台生成文件常见 CRLF,残留 CR 会以不可见字符进入值,
#      int("6379\r")/URL 解析均在运行期才炸;KEY = VALUE/缩进键/缩进
#      注释是 .properties 习惯写法,不裁剪会被正则静默丢弃)
#   3. 末行无换行符仍处理(read 到 EOF 无换行时赋值但返回非 0,原循环
#      条件会静默丢掉最后一行——自动化生成/截断文件常见)
#   4. 非法变量名跳过 + 危险变量名黑名单(评审修订 2026-11-03:白名单
#      只拦"非标识符字符",拦不住危险标识符——BASH_ENV/LD_PRELOAD 在
#      source 场景等效代码执行,PATH/IFS/HOME 改写破坏调用方 shell。
#      黑名单命中打一行 stderr 便于排查,不注入)
#   5. 值仍含 '${' 的行跳过(平台占位符未被替换,不注入字面量)
#   6. 幂等:重复 source 结果一致(文件值始终覆盖)
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
# || [ -n "$k" ]:read 读到 EOF 且无换行时已赋值但返回非 0——不带此条件,
# 末行(无结尾换行)永远进不了循环体,静默丢参(评审修订 2026-11-03)。
while IFS='=' read -r k v || [ -n "$k" ]; do
  # 剥离行尾 CR(CRLF 文件;EOF 无换行时 CR 同样残留在行尾)
  k=${k%$'\r'}
  v=${v%$'\r'}
  # k/v 首尾空白裁剪:兼容 "KEY = VALUE"/缩进键/缩进注释(.properties 习惯),
  # 防止带空白的键被正则静默丢弃、带空白的值引入不可见差异
  k="${k#"${k%%[![:space:]]*}"}"
  k="${k%"${k##*[![:space:]]}"}"
  v="${v#"${v%%[![:space:]]*}"}"
  v="${v%"${v##*[![:space:]]}"}"
  case "$k" in ''|\#*) continue ;; esac
  # 非法变量名跳过
  [[ "$k" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
  # 危险变量名黑名单:正则只拦"非标识符字符",拦不住危险标识符。
  # source 后在同一 shell 启动服务的场景下,BASH_ENV/ENV/LD_*/DYLD_*
  # 等效代码执行,PATH/IFS/HOME/SHELL 等改写调用方 shell 行为——
  # 与"防污染注入"的防护承诺对齐(评审修订 2026-11-03)。
  case "$k" in
    IFS|PATH|HOME|SHELL|PS1|PS2|PS4|ENV|BASH_ENV|BASHOPTS|SHELLOPTS|BASH_XTRACEFD|LD_*|DYLD_*)
      echo "[paas_env] skip dangerous variable: ${k}" >&2
      continue ;;
  esac
  # 值中仍含占位符 = 该行未被替换,跳过(不注入 "${xxx}" 字面量)
  [[ "$v" == *'${'* ]] && continue
  export "$k=$v"
done < "$ENV_FILE"
echo "[paas_env] done"
