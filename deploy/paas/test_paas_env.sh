#!/bin/bash
# test_paas_env.sh —— paas_env.sh 加载器最小测试(评审补测 2026-11-03)
# 运行: bash deploy/paas/test_paas_env.sh
# 零外部依赖:自建夹具(BOM/CRLF/空白键值/多=值/非法键/敏感名/占位符/末行无换行),
# source 加载器后逐项断言,任一失败退出码非 0。
# 注意:加载器使用 bash 专有语法,本测试与生产用法都须在 bash 中执行。

SELF_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
LOADER="${SELF_DIR}/paas_env.sh"
FAIL=0

check() {
  # check <描述> <实际> <期望>
  if [ "$2" = "$3" ]; then
    echo "ok:   $1"
  else
    echo "FAIL: $1 (got [$2] want [$3])"
    FAIL=1
  fi
}

check_unset() {
  # check_unset <描述> <变量名> —— 期望未注入
  # 用 printenv 而非 ${!2} 间接展开:非法变量名(如 9BAD)会让 ${!9BAD}
  # 本身报"invalid variable name",printenv 对任意名字都安全
  if [ -z "$(printenv "$2" 2>/dev/null)" ]; then
    echo "ok:   $1"
  else
    echo "FAIL: $1 (不该导出却得到 [$(printenv "$2")])"
    FAIL=1
  fi
}

# ---- 构造夹具 ----
FIXTURE=$(mktemp)
trap 'rm -f "$FIXTURE"' EXIT
{
  printf '\xEF\xBB\xBFGOOD1=1\r\n'          # UTF-8 BOM + 正常键值
  printf 'SPACED = 2 \r\n'                  # KEY = VALUE 带空白(.properties 习惯)
  printf '  INDENT=3\r\n'                   # 缩进键
  printf '  # indented comment\r\n'         # 缩进注释
  printf 'MULTIEQ=a=b=c\r\n'                # 值内含多个 =(JDBC URL 常见形态)
  printf '9BAD=x\r\n'                       # 非法变量名(数字开头)
  printf 'has-dash=x\r\n'                   # 非法变量名(连字符)
  printf 'LD_PRELOAD=/tmp/evil.so\r\n'      # 敏感:动态库注入
  printf 'PATH=/tmp/evil-bin\r\n'           # 敏感:PATH 改写
  printf 'BASH_ENV=/tmp/evil.sh\r\n'        # 敏感:非交互 shell 启动配置
  printf 'KEEPPLACE=${NOT_REPLACED}\r\n'    # 未替换占位符
  printf 'CRLFV=6379\r\n'                   # CRLF 值
  printf 'LASTLINE=42'                      # 末行无换行符
} > "$FIXTURE"

# ---- source 加载器(仅吞 stdout,敏感名告警走 stderr 保持可见) ----
PATH_BEFORE="$PATH"
export PAAS_ENV_FILE="$FIXTURE"
. "$LOADER" > /dev/null

# ---- 断言 ----
check "BOM 首行键被处理" "$GOOD1" "1"
check "KEY = VALUE 空白裁剪" "$SPACED" "2"
check "缩进键被处理" "$INDENT" "3"
check "值内多 = 完整保留" "$MULTIEQ" "a=b=c"
check "CRLF 值无残留 CR" "$CRLFV" "6379"
check "末行无换行仍导出" "$LASTLINE" "42"
check_unset "非法变量名(数字开头)跳过" "9BAD"
check_unset "非法变量名(连字符)跳过" "has_dash"
check_unset "敏感 LD_PRELOAD 拒绝" "LD_PRELOAD"
check_unset "敏感 BASH_ENV 拒绝" "BASH_ENV"
check_unset "未替换占位符跳过" "KEEPPLACE"
check "PATH 未被改写" "$PATH" "$PATH_BEFORE"

if [ "$FAIL" = 0 ]; then
  echo "==== 全部通过 ===="
else
  echo "==== 存在失败 ===="
fi
exit "$FAIL"
