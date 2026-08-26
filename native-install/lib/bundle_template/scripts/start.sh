#!/usr/bin/env bash
# openJiuwen AgentStudio — 原生（免容器）一键启动（Linux）
# 按序拉起：MySQL → Redis → MinIO(+mc) → manager → runtime → builder → console(nginx)
set -uo pipefail

# ── 定位包根 ────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$BUNDLE_ROOT"
RUN="$BUNDLE_ROOT/run"; LOG="$BUNDLE_ROOT/logs"; DATA="$BUNDLE_ROOT/data"
mkdir -p "$RUN" "$LOG" "$DATA" "$DATA/mysql" "$DATA/redis" "$DATA/minio"

# ── 加载 .env ────────────────────────────────────────────────────────────────
if [ ! -f "$BUNDLE_ROOT/.env" ]; then
  cp -f "$BUNDLE_ROOT/.env.template" "$BUNDLE_ROOT/.env"
  echo "[start] 已从 .env.template 创建 .env"
fi
set -a; . "$BUNDLE_ROOT/.env"; set +a

# 派生默认端口（兼容未在 .env 显式设置）
CONSOLE_PORT="${CONSOLE_PORT:-80}"; DB_PORT="${DB_PORT:-3306}"
REDIS_EXTERNAL_PORT="${REDIS_EXTERNAL_PORT:-6379}"
MINIO_API_PORT="${MINIO_API_PORT:-9000}"; MINIO_CONSOLE_PORT="${MINIO_CONSOLE_PORT:-9001}"
MANAGER_PORT="${MANAGER_PORT:-31111}"; RUNTIME_PORT="${RUNTIME_PORT:-31014}"; BUILDER_PORT="${BUILDER_PORT:-31015}"

# ── 原生依赖路径 ──────────────────────────────────────────────────────────────
DEPS="$BUNDLE_ROOT/deps/linux"
export JAVA_HOME="$DEPS/jre-17"
export PATH="$JAVA_HOME/bin:$DEPS/mysql-8.0/bin:$DEPS/redis-7:$DEPS/minio:$DEPS/nginx/sbin:$PATH"
# MySQL 客户端需 libncurses.so.5/libtinfo.so.5、mysqld 需 libaio.so.1/libnuma.so.1。
# 目标 RHEL 系通常自带；缺则用包内 glibc2.17 兼容库（deps/linux/lib）兜底。放 PATH 之后，
# 不覆盖系统库（同 ABI 无害），仅补缺。
[ -d "$DEPS/lib" ] && export LD_LIBRARY_PATH="$DEPS/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
PYTHON_BIN="$DEPS/python-3.11/bin/python3"
MYSQLD="$DEPS/mysql-8.0/bin/mysqld"; MYSQL_CLI="$DEPS/mysql-8.0/bin/mysql"
REDIS_SRV="$DEPS/redis-7/redis-server"; REDIS_CLI="$DEPS/redis-7/redis-cli"
MINIO_BIN="$DEPS/minio/minio"; MC_BIN="$DEPS/minio/mc"
NGINX_BIN="$DEPS/nginx/sbin/nginx"

# ── 补执行位 ──────────────────────────────────────────────────────────────────
# 包可能在 Windows 上用 bsdtar 打（Linux 二进制存成 0666 无 x 位），或经 zip/unzip 解压丢 x 位，
# 直接执行会 permission denied。启动前确保 Linux 二进制与脚本可执行（幂等）。
chmod +x "$DEPS/jre-17/bin/"* "$DEPS/mysql-8.0/bin/"* "$DEPS/redis-7/"* \
         "$DEPS/minio/"* "$DEPS/nginx/sbin/"* "$DEPS/python-3.11/bin/"* 2>/dev/null || true
chmod +x "$BUNDLE_ROOT/scripts/"*.sh "$BUNDLE_ROOT/scripts/runtime_patches.py" 2>/dev/null || true

log(){ echo -e "\033[1;36m[start]\033[0m $*"; }
warn(){ echo -e "\033[1;33m[warn]\033[0m $*"; }
die(){ echo -e "\033[1;31m[fatal]\033[0m $*"; exit 1; }

# 非 root 无法绑 <1024 特权端口（CONSOLE_PORT 默认 80）；降级 8080，对齐 Windows 的非 admin 降级。
# （Linux 也可改用 root 跑或 setcap cap_net_bind_service 给 nginx，则无需降级。）
if [ "$(id -u)" -ne 0 ] && [ "${CONSOLE_PORT:-0}" -lt 1024 ] 2>/dev/null; then
  CONSOLE_PORT=8080
  warn "非 root 用户无法绑特权端口（<1024），控制台改用 8080。以 root 重跑或给 nginx setcap 可恢复 80。"
fi

wait_port(){ # <port> <name> <max_sec>
  local port="$1" name="$2" max="${3:-90}" t=0
  while ! (echo > /dev/tcp/127.0.0.1/$port) 2>/dev/null; do
    sleep 2; t=$((t+2)); [ $t -ge $max ] && { warn "$name 端口 $port 未就绪（${t}s）"; return 1; }
  done
  log "$name 就绪 (port $port)"
}
wait_http(){ # <url> <name> <max_sec>
  local url="$1" name="$2" max="${3:-120}" t=0
  while ! curl -sf --max-time 3 "$url" >/dev/null 2>&1; do
    sleep 3; t=$((t+3)); [ $t -ge $max ] && { warn "$name 健康检查超时：$url"; return 1; };
  done
  log "$name 就绪 ($url)"
}

# ════════════════════════════════════════════════════════════════════════════
# [1/7] MySQL
# ════════════════════════════════════════════════════════════════════════════
log "[1/7] MySQL"
MYSQL_DATA="$DATA/mysql"; MYSQL_SOCK="$RUN/mysql.sock"; MYSQL_PID="$RUN/mysqld.pid"
if [ ! -f "$RUN/.mysql_initialized" ]; then
  log "  首次初始化 MySQL 数据目录..."
  rm -rf "$MYSQL_DATA"; mkdir -p "$MYSQL_DATA"
  "$MYSQLD" --initialize-insecure --datadir="$MYSQL_DATA" --user="$(whoami)" >/dev/null 2>&1 || die "MySQL 初始化失败"
fi
if [ -f "$MYSQL_PID" ] && kill -0 "$(cat "$MYSQL_PID")" 2>/dev/null; then
  log "  MySQL 已在运行"
else
  nohup "$MYSQLD" --datadir="$MYSQL_DATA" --socket="$MYSQL_SOCK" --port="$DB_PORT" \
    --pid-file="$MYSQL_PID" --user="$(whoami)" \
    --character-set-server=utf8mb4 --collation-server=utf8mb4_general_ci \
    --local-infile=1 --default-authentication-plugin=mysql_native_password \
    >> "$LOG/mysql.log" 2>&1 &
fi
wait_port "$DB_PORT" "MySQL" 60 || die "MySQL 启动失败，见 $LOG/mysql.log"
# 首启设密码 + 建库
if [ ! -f "$RUN/.mysql_initialized" ]; then
  log "  设置 root 口令并导入 init.sql..."
  "$MYSQL_CLI" -S "$MYSQL_SOCK" -uroot <<SQL
ALTER USER 'root'@'localhost' IDENTIFIED BY '${SPRING_DATASOURCE_PASSWORD:-123456}';
CREATE USER IF NOT EXISTS 'root'@'%' IDENTIFIED BY '${SPRING_DATASOURCE_PASSWORD:-123456}';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;
SQL
  "$MYSQL_CLI" -S "$MYSQL_SOCK" -uroot -p"${SPRING_DATASOURCE_PASSWORD:-123456}" < "$BUNDLE_ROOT/config/init.sql" || warn "init.sql 导入有警告"
  touch "$RUN/.mysql_initialized"
fi

# ════════════════════════════════════════════════════════════════════════════
# [2/7] Redis
# ════════════════════════════════════════════════════════════════════════════
log "[2/7] Redis"
REDIS_PID="$RUN/redis.pid"
if [ -f "$REDIS_PID" ] && kill -0 "$(cat "$REDIS_PID")" 2>/dev/null; then
  log "  Redis 已在运行"
else
  "$REDIS_SRV" --port "$REDIS_EXTERNAL_PORT" --daemonize yes --dir "$DATA/redis" \
    --pidfile "$REDIS_PID" --logfile "$LOG/redis.log" >/dev/null 2>&1 || die "Redis 启动失败"
fi
wait_port "$REDIS_EXTERNAL_PORT" "Redis" 30 || die "Redis 启动失败"

# ════════════════════════════════════════════════════════════════════════════
# [3/7] MinIO + bucket
# ════════════════════════════════════════════════════════════════════════════
log "[3/7] MinIO"
MINIO_PID="$RUN/minio.pid"
if [ -f "$MINIO_PID" ] && kill -0 "$(cat "$MINIO_PID")" 2>/dev/null; then
  log "  MinIO 已在运行"
else
  MINIO_ROOT_USER="${OBS_AK:-minioadmin}" MINIO_ROOT_PASSWORD="${OBS_SK:-minioadmin}" \
    nohup "$MINIO_BIN" server "$DATA/minio" --address ":$MINIO_API_PORT" --console-address ":$MINIO_CONSOLE_PORT" \
    >> "$LOG/minio.log" 2>&1 & echo $! > "$MINIO_PID"
fi
wait_http "http://127.0.0.1:$MINIO_API_PORT/minio/health/live" "MinIO" 60 || die "MinIO 启动失败，见 $LOG/minio.log"
"$MC_BIN" alias set local "http://127.0.0.1:$MINIO_API_PORT" "${OBS_AK:-minioadmin}" "${OBS_SK:-minioadmin}" >/dev/null 2>&1
"$MC_BIN" mb -p "local/${OBS_BUCKET:-agent-builder}" >/dev/null 2>&1 || true
log "  MinIO bucket ${OBS_BUCKET:-agent-builder} 就绪"

# ════════════════════════════════════════════════════════════════════════════
# [4/7] studio-manager (Java)
# ════════════════════════════════════════════════════════════════════════════
log "[4/7] studio-manager"
heap_java(){ # 计算：Xmx=min(物理内存×0.35, 4096)，Xms 用小初值 512m 按需增长；direct=min(×0.1, 512)
  # 旧式 -Xms=-Xmx=物理内存×0.6 会一次性 commit 全堆，提交额度不够时 OOM 启动即崩；
  # 两个 JVM 各 60% 合计更超物理内存。返回 "XmxM directM"，Xms 固定 512。
  local total heapMax direct
  total=$(free -m 2>/dev/null | awk '/^Mem:/{print $2}'); [ -z "$total" ] && total=4096
  heapMax=$(awk "BEGIN{h=$total*0.35; if(h>4096)h=4096; printf \"%.0f\", h}")
  direct=$(awk "BEGIN{d=$total*0.1; if(d>512)d=512; printf \"%.0f\", d}")
  echo "$heapMax $direct"
}
read HEAP_MAX DIRECT < <(heap_java)
HEAP_MIN=512
MGR_PID="$RUN/manager.pid"
if [ -f "$MGR_PID" ] && kill -0 "$(cat "$MGR_PID")" 2>/dev/null; then
  log "  studio-manager 已在运行"
else
  nohup "$JAVA_HOME/bin/java" -Xms${HEAP_MIN}m -Xmx${HEAP_MAX}m -XX:MaxDirectMemorySize=${DIRECT}m \
    -Dfile.encoding=UTF-8 \
    -jar "$BUNDLE_ROOT/app/manager/studio-manager.jar" \
    --spring.config.additional-location="file:$BUNDLE_ROOT/config/" \
    --spring.profiles.active=manager \
    --logging.config="file:$BUNDLE_ROOT/config/log4j2-manager.xml" \
    >> "$LOG/manager.log" 2>&1 & echo $! > "$MGR_PID"
fi
wait_http "http://127.0.0.1:$MANAGER_PORT/health" "studio-manager" 180 || warn "manager 健康检查未通过（可能仍启动中）"

# ════════════════════════════════════════════════════════════════════════════
# [5/7] studio-runtime (Python, agent_runtime/EIStart)
# ════════════════════════════════════════════════════════════════════════════
log "[5/7] studio-runtime"
RT_PID="$RUN/runtime.pid"
VENV="$RUN/venv"; VENV_PY="$VENV/bin/python"; VENV_PIP="$VENV/bin/pip"
if [ ! -f "$RUN/.venv_ready" ]; then
  log "  首次创建 venv 并安装依赖（约 1-2 分钟）..."
  "$PYTHON_BIN" -m venv "$VENV" || die "venv 创建失败"
  # 不用 --no-index：离线 wheel 不全（Phase C best-effort 有缺），--no-index 下任一缺失即整体失败。
  # 改 --find-links（优先本地 wheel）+ aliyun index 兜底补缺。仅装成功（openjiuwen 可导入）才 touch .venv_ready。
  if [ -d "$BUNDLE_ROOT/deps/wheels" ]; then
    "$VENV_PIP" install --find-links "$BUNDLE_ROOT/deps/wheels/" \
      -i "${PIP_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple/}" --trusted-host "${PIP_TRUSTED_HOST:-mirrors.aliyun.com}" \
      -r "$BUNDLE_ROOT/app/requirements.txt" || warn "依赖安装有部分失败（见 $LOG/runtime.log）"
  else
    "$VENV_PIP" install -i "${PIP_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple/}" \
      --trusted-host "${PIP_TRUSTED_HOST:-mirrors.aliyun.com}" \
      -r "$BUNDLE_ROOT/app/requirements.txt" || warn "依赖安装失败"
  fi
  if "$VENV_PY" -c "import openjiuwen" 2>/dev/null; then
    "$VENV_PY" "$BUNDLE_ROOT/scripts/runtime_patches.py" || warn "runtime 补丁有警告"
    touch "$RUN/.venv_ready"
  else
    warn "依赖安装不完整（openjiuwen 不可导入）。不写 .venv_ready，下次启动重试。请检查网络或 deps/wheels。"
  fi
fi
if [ -f "$RT_PID" ] && kill -0 "$(cat "$RT_PID")" 2>/dev/null; then
  log "  studio-runtime 已在运行"
else
  export PYTHONPATH="$VENV/lib/python3.11/site-packages:$BUNDLE_ROOT/app:$BUNDLE_ROOT/app/agent_runtime${PYTHONPATH:+:$PYTHONPATH}"
  export JIUWEN_EXTENSION_PATH="$BUNDLE_ROOT/app/agent_runtime/extension"
  export LOGGING_LOG_PATH="$LOG"; export TGF_LOG_DIR="$LOG"
  export host=127.0.0.1; export PORT="$RUNTIME_PORT"
  nohup "$VENV_PY" -u "$BUNDLE_ROOT/app/agent_runtime/EIStart.py" --host 0.0.0.0 --port "$RUNTIME_PORT" \
    >> "$LOG/runtime.log" 2>&1 & echo $! > "$RT_PID"
fi
wait_http "http://127.0.0.1:$RUNTIME_PORT/v1/health" "studio-runtime" 180 || warn "runtime 健康检查未通过（可能仍启动中）"

# ════════════════════════════════════════════════════════════════════════════
# [6/7] studio-builder (Python, agent_builder/EIBuilder)
# ════════════════════════════════════════════════════════════════════════════
log "[6/7] studio-builder"
BDR_PID="$RUN/builder.pid"
if [ -f "$BDR_PID" ] && kill -0 "$(cat "$BDR_PID")" 2>/dev/null; then
  log "  studio-builder 已在运行"
else
  # 复用 runtime 同一 venv；PYTHONPATH 含 app（model_service/storage/common_utils/agent_builder 经此解析）。
  # 与 docker/studio-builder 对齐在 app/ 下执行（config.yaml 按 cwd 相对解析 "./logs" → $BUNDLE_ROOT/logs）。
  export PYTHONPATH="$VENV/lib/python3.11/site-packages:$BUNDLE_ROOT/app${PYTHONPATH:+:$PYTHONPATH}"
  export LOGGING_LOG_PATH="$LOG"; export host=127.0.0.1
  ( cd "$BUNDLE_ROOT/app" && nohup "$VENV_PY" -u -m agent_builder.EIBuilder --host 0.0.0.0 --port "$BUILDER_PORT" \
    >> "$LOG/builder.log" 2>&1 & echo $! > "$BDR_PID" )
fi
wait_http "http://127.0.0.1:$BUILDER_PORT/v1/health" "studio-builder" 180 || warn "builder 健康检查未通过（可能仍启动中）"

# ════════════════════════════════════════════════════════════════════════════
# [7/7] console (nginx)
# ════════════════════════════════════════════════════════════════════════════
log "[7/7] console (nginx)"
NGINX_PID="$RUN/nginx.pid"
# 建 temp 目录：nginx 用 -p $BUNDLE_ROOT/ 改了 prefix，temp 路径（client_body_temp 等）落到包内，
# 缺目录可能致启动失败。对齐 start.ps1 的 New-Item temp。
mkdir -p "$BUNDLE_ROOT/temp"
# 兜底：包内缺 config/mime.types 时（如 seed 复用构建路径遗漏），从 nginx 依赖补一份，
# 否则 nginx 起不来（include 指令 CreateFile 失败 → worker 不驻听）。
if [ ! -f "$BUNDLE_ROOT/config/mime.types" ]; then
  for m in "$DEPS/nginx/conf/mime.types" "$DEPS/nginx/mime.types"; do
    if [ -f "$m" ]; then cp -f "$m" "$BUNDLE_ROOT/config/mime.types" && warn "已补 config/mime.types（来自 $m）"; break; fi
  done
fi
# 由 tmpl 生成最终配置：注入 pid、user、替换 BUNDLE_ROOT/CONSOLE_PORT
# user 设为启动用户：worker 默认 nobody 读不到 700 的 /root（index.html Permission denied）。
{
  echo "pid $NGINX_PID;"
  echo "user $(id -un);"
  sed -e "s|@@BUNDLE_ROOT@@|$BUNDLE_ROOT|g" -e "s|@@CONSOLE_PORT@@|$CONSOLE_PORT|g" \
    "$BUNDLE_ROOT/config/nginx.conf.tmpl"
} > "$RUN/nginx.conf"
if [ -f "$NGINX_PID" ] && kill -0 "$(cat "$NGINX_PID")" 2>/dev/null; then
  log "  nginx 已在运行，重载配置"
  "$NGINX_BIN" -s reload -c "$RUN/nginx.conf" -p "$BUNDLE_ROOT/" 2>/dev/null || true
else
  "$NGINX_BIN" -c "$RUN/nginx.conf" -p "$BUNDLE_ROOT/" || die "nginx 启动失败，见 $LOG/access.log"
fi
wait_http "http://127.0.0.1:$CONSOLE_PORT/openjiuwen/" "console" 60 || warn "console 健康检查未通过"

# ── 日志轮转定时任务（仅 Linux）─────────────────────────────────────────────
if [ "${BACKUP_COMMON_LOG:-true}" = "true" ] && command -v crontab >/dev/null 2>&1; then
  if ! crontab -l 2>/dev/null | grep -q "agentstudio-backup-common-log"; then
    (crontab -l 2>/dev/null; echo "0 */4 * * * $BUNDLE_ROOT/scripts/cron_backup_log.sh # agentstudio-backup-common-log") | crontab - 2>/dev/null || warn "cron 安装失败（不影响服务）"
    log "已安装日志轮转 cron（每 4 小时）"
  fi
fi

# ── 完成 ──────────────────────────────────────────────────────────────────────
CONSOLE_URL="http://localhost:${CONSOLE_PORT}/openjiuwen/"
echo
echo "================================================================"
echo "  openJiuwen AgentStudio 已启动"
echo "================================================================"
echo "  控制台 :  $CONSOLE_URL"
echo "  状态   :  ./scripts/status.sh"
echo "  停止   :  ./scripts/stop.sh"
echo "  日志   :  ./scripts/logs.sh [manager|runtime|builder|mysql|redis|minio|nginx]"
echo "================================================================"
# URL 作为脚本最后一行输出，确保执行结束时它就在光标正上方
echo
echo ">>> 控制台地址: $CONSOLE_URL <<<"
