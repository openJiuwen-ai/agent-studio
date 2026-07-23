#!/usr/bin/env bash
# openJiuwen AgentStudio — 原生（免容器）停止全部服务（Linux），逆序停止
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$BUNDLE_ROOT"
RUN="$BUNDLE_ROOT/run"
[ -f "$BUNDLE_ROOT/.env" ] && { set -a; . "$BUNDLE_ROOT/.env"; set +a; }
CONSOLE_PORT="${CONSOLE_PORT:-80}"; DB_PORT="${DB_PORT:-3306}"; REDIS_EXTERNAL_PORT="${REDIS_EXTERNAL_PORT:-6379}"

log(){ echo -e "\033[1;36m[stop]\033[0m $*"; }
kill_pid(){ # <pidfile> <name> [signal]
  local pf="$1" name="$2" sig="${3:-TERM}"
  if [ -f "$pf" ]; then
    local p; p=$(cat "$pf" 2>/dev/null)
    if [ -n "$p" ] && kill -0 "$p" 2>/dev/null; then
      # kill 不杀子进程：先按进程组杀（负 pid），再单杀，成功也清 pid 文件保持整洁。
      kill -s "$sig" -- -"$p" 2>/dev/null || kill -s "$sig" "$p" 2>/dev/null
      log "$name (pid $p) 已发送 $sig"; rm -f "$pf"
    else
      log "$name 未运行（清理残留 pid 文件）"; rm -f "$pf"
    fi
  else
    log "$name 无 pid 文件"
  fi
}

DEPS="$BUNDLE_ROOT/deps/linux"
export PATH="$DEPS/mysql-8.0/bin:$DEPS/redis-7:$DEPS/nginx/sbin:$PATH"

log "停止 console (nginx)..."
[ -x "$DEPS/nginx/sbin/nginx" ] && "$DEPS/nginx/sbin/nginx" -s stop -c "$RUN/nginx.conf" -p "$BUNDLE_ROOT/" 2>/dev/null || kill_pid "$RUN/nginx.pid" nginx

log "停止 studio-runtime..."
kill_pid "$RUN/runtime.pid" runtime
# runtime 用 multiprocessing-fork 起 worker；父进程被杀后 worker 可能成孤儿仍占端口
# （Linux fork 子进程继承父 cmdline，spawn 子进程跑 deps python）。按本包 python 路径
# 兜底清孤儿 worker，不波及用户机器上其它 python。kill_pid 成功也清 pid 文件（见下）。
pkill -f "$BUNDLE_ROOT/run/venv/bin/python" 2>/dev/null || true
pkill -f "$BUNDLE_ROOT/deps/linux/python" 2>/dev/null || true

log "停止 studio-service..."
kill_pid "$RUN/service.pid" service

log "停止 studio-manager..."
kill_pid "$RUN/manager.pid" manager

log "停止 MinIO..."
kill_pid "$RUN/minio.pid" minio

log "停止 Redis..."
"$DEPS/redis-7/redis-cli" -p "$REDIS_EXTERNAL_PORT" shutdown nosave 2>/dev/null || kill_pid "$RUN/redis.pid" redis

log "停止 MySQL..."
"$DEPS/mysql-8.0/bin/mysqladmin" -S "$RUN/mysql.sock" -uroot -p"${SPRING_DATASOURCE_PASSWORD:-123456}" shutdown 2>/dev/null || kill_pid "$RUN/mysqld.pid" mysqld

# 移除日志轮转 cron
if command -v crontab >/dev/null 2>&1; then
  crontab -l 2>/dev/null | grep -v "agentstudio-backup-common-log" | crontab - 2>/dev/null || true
fi
log "完成。"
