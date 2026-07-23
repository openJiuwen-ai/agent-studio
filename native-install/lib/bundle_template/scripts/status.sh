#!/usr/bin/env bash
# openJiuwen AgentStudio — 原生模式状态查看（Linux）
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"; cd "$BUNDLE_ROOT"
RUN="$BUNDLE_ROOT/run"
[ -f "$BUNDLE_ROOT/.env" ] && { set -a; . "$BUNDLE_ROOT/.env"; set +a; }
CONSOLE_PORT="${CONSOLE_PORT:-80}"; DB_PORT="${DB_PORT:-3306}"; REDIS_EXTERNAL_PORT="${REDIS_EXTERNAL_PORT:-6379}"
MINIO_API_PORT="${MINIO_API_PORT:-9000}"; MANAGER_PORT="${MANAGER_PORT:-31111}"; SERVICE_PORT="${SERVICE_PORT:-31113}"; RUNTIME_PORT="${RUNTIME_PORT:-31014}"

GREEN='\033[1;32m'; RED='\033[1;31m'; NC='\033[0m'
ok(){ printf "${GREEN}%-10s${NC}" "RUNNING"; }; no(){ printf "${RED}%-10s${NC}" "DOWN"; }
pid_state(){ local p; [ -f "$1" ] || { echo -n "no-pid"; return; }; p=$(cat "$1" 2>/dev/null); if [ -n "$p" ] && kill -0 "$p" 2>/dev/null; then echo -n "pid=$p"; else echo -n "dead"; fi; }

printf "%-12s %-12s %-12s %s\n" "SERVICE" "PROC" "HEALTH" "PID"
for s in "mysql:$RUN/mysqld.pid:tcp:$DB_PORT" \
         "redis:$RUN/redis.pid:tcp:$REDIS_EXTERNAL_PORT" \
         "minio:$RUN/minio.pid:http:http://127.0.0.1:$MINIO_API_PORT/minio/health/live" \
         "manager:$RUN/manager.pid:http:http://127.0.0.1:$MANAGER_PORT/health" \
         "service:$RUN/service.pid:http:http://127.0.0.1:$SERVICE_PORT/v1/health" \
         "runtime:$RUN/runtime.pid:http:http://127.0.0.1:$RUNTIME_PORT/v1/health" \
         "console:$RUN/nginx.pid:http:http://127.0.0.1:$CONSOLE_PORT/openjiuwen/"; do
  name="${s%%:*}"; rest="${s#*:}"; pf="${rest%%:*}"; rest="${rest#*:}"; kind="${rest%%:*}"; target="${rest#*:}"
  p=$(cat "$pf" 2>/dev/null); proc=down; { [ -n "$p" ] && kill -0 "$p" 2>/dev/null; } && proc=ok
  hs=down
  if [ "$kind" = "http" ]; then curl -sf --max-time 3 "$target" >/dev/null 2>&1 && hs=ok
  else (echo > /dev/tcp/127.0.0.1/"$target") 2>/dev/null && hs=ok; fi
  printf "%-12s %-12s %-12s %s\n" "$name" "$(if [ $proc = ok ]; then ok; else no; fi)" \
    "$(if [ $hs = ok ]; then ok; else no; fi)" "$(pid_state "$pf")"
done
echo
echo "控制台: http://localhost:$CONSOLE_PORT/openjiuwen/   登录 agent/agent"
