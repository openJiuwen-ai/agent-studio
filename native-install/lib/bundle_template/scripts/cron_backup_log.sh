#!/usr/bin/env bash
# 日志轮转（cron 调用）—— 简化版 cron_job.sh 的 backup_common_log
# 每 4 小时由 crontab 触发；轮转 logs/*.log
set -uo pipefail
BUNDLE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$BUNDLE_ROOT"
LOG="$BUNDLE_ROOT/logs"
BACKUP_NUM="${BACKUP_COMMON_LOG_BACKUP_NUM:-5}"
# 单个日志超过此大小才轮转（默认 100MB）。日志被进程持有打开的 fd（如 mysqld 的
# stderr→mysql.log 经 start.sh 的 `>` 重定向）时，不能用 mv（进程会继续写已改名的 inode，
# 新文件恒空、旧文件无限长）。改用 copytruncate 语义：先 cp 一份，再原地截断原文件
# （: > file），持有 fd 的进程继续写到同一 inode（从 0 重新增长），实现有界轮转。
MAX_BYTES="${BACKUP_COMMON_LOG_MAX_BYTES:-104857600}"

[ -d "$LOG" ] || exit 0

# rotate_one <file>：超阈值则 copytruncate + gzip + 滚动旧 .N.gz
rotate_one(){
  local f="$1"
  [ -f "$f" ] || return 0
  local sz; sz=$(wc -c < "$f" 2>/dev/null || echo 0)
  [ "$sz" -lt "$MAX_BYTES" ] && return 0
  # 滚动已有备份 .N.gz -> .N+1.gz，删超出 BACKUP_NUM 的
  local i
  for ((i=BACKUP_NUM; i>=1; i--)); do
    [ -f "$f.$i.gz" ] || continue
    if [ "$i" -eq "$BACKUP_NUM" ]; then rm -f "$f.$i.gz"
    else mv -f "$f.$i.gz" "$f.$((i+1)).gz"; fi
  done
  # copytruncate：cp 当前内容为 .1，原地截断原文件
  cp -pf "$f" "$f.1" 2>/dev/null || return 0
  : > "$f"
  gzip -f "$f.1" 2>/dev/null || true
}

# 轮转 logs/ 下所有顶层 *.log（mysql/redis/manager/service/runtime/minio/access/error/common…）
shopt -s nullglob
for f in "$LOG"/*.log; do rotate_one "$f"; done
# 兼容旧逻辑：若存在独立 common.log 也纳入（上面 *.log 已覆盖，此处幂等无副作用）
