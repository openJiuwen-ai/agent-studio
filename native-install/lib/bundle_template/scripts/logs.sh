#!/usr/bin/env bash
# openJiuwen AgentStudio — 查看日志（Linux）
# 用法: ./scripts/logs.sh [manager|service|runtime|mysql|redis|minio|nginx|access|error]
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"; cd "$BUNDLE_ROOT"
LOG="$BUNDLE_ROOT/logs"; mkdir -p "$LOG"
svc="${1:-manager}"
case "$svc" in
  nginx) f="nginx" ;;           # nginx 主日志；access/error 见下
  access) f="access" ;;
  error) f="error" ;;
  *) f="$svc" ;;
esac
file="$LOG/$f.log"
[ -f "$file" ] || { echo "日志不存在: $file（可选: manager service runtime mysql redis minio nginx access error）"; ls -1 "$LOG"/*.log 2>/dev/null; exit 1; }
echo "→ tail -f $file   (Ctrl+C 退出)"
tail -f "$file"
