#!/usr/bin/env bash
# 日志轮转（cron 调用）—— 简化版 cron_job.sh 的 backup_common_log
# 每 4 小时由 crontab 触发；轮转 logs/common.log
set -uo pipefail
BUNDLE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$BUNDLE_ROOT"
LOG="$BUNDLE_ROOT/logs"
BACKUP_NUM="${BACKUP_COMMON_LOG_BACKUP_NUM:-5}"
TARGET="$LOG/common.log"
[ -f "$TARGET" ] || exit 0
for i in $(seq $((BACKUP_NUM-1)) -1 1); do [ -f "$TARGET.$i" ] && mv "$TARGET.$i" "$TARGET.$((i+1))"; done
mv "$TARGET" "$TARGET.1" 2>/dev/null || true
gzip -f "$TARGET.1" 2>/dev/null || true
find "$LOG" -name 'common.log.*.gz' -mtime +${BACKUP_NUM} -delete 2>/dev/null || true
