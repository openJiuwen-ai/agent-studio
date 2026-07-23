#!/usr/bin/env bash
# build_apps.sh — 构建应用产物并填入 bundle_template（复刻 docker/package.sh）
# 环境变量：WORKSPACE=仓库根  STAGING=bundle_template 目标目录
set -euo pipefail

WORKSPACE="${WORKSPACE:?需设置 WORKSPACE（仓库根）}"
STAGING="${STAGING:?需设置 STAGING（bundle_template 目录）}"

log(){ echo -e "\033[1;36m[apps]\033[0m $*"; }
die(){ echo -e "\033[1;31m[apps fatal]\033[0m $*"; exit 1; }

mkdir -p "$STAGING/app" "$STAGING/app/frontend" "$STAGING/config"

# ── [1] 后端 Maven 打包 ─────────────────────────────────────────────────────
log "[1/4] 后端 Maven 打包 (backend)"
cd "$WORKSPACE/backend"
if command -v mvn >/dev/null 2>&1; then
  mvn clean package -Dmaven.test.skip=true -U
else
  die "未找到 mvn，请安装 Maven 并加入 PATH"
fi

# studio-manager → app/manager/studio-manager.jar + target/lib 依赖（同级，匹配 jar manifest Class-Path）+ config
log "  复制 studio-manager 产物"
mkdir -p "$STAGING/app/manager"
# 取首个非 sources 的 jar（对齐 ps1 的 Select -First 1）：glob 若匹配多个（如 -sources.jar）cp 会报错。
mgrJar=$(find "$WORKSPACE/backend/studio-manager/target" -maxdepth 1 -name 'studio-manager-*.jar' ! -name '*-sources.jar' | head -1)
[ -n "$mgrJar" ] || die "未找到 studio-manager 产物 jar（先跑 mvn package）"
cp -f "$mgrJar" "$STAGING/app/manager/studio-manager.jar"
# jar 是 thin jar（Main-Class=PropertiesLauncher，依赖在 manifest Class-Path 列为同级 bare 名），
# 必须把 target/lib/*.jar 一并拷到 jar 同级目录，否则 NoClassDefFoundError: org/slf4j/LoggerFactory。
if [ -d "$WORKSPACE/backend/studio-manager/target/lib" ]; then
  cp -f "$WORKSPACE/backend/studio-manager/target/lib/"* "$STAGING/app/manager/"
else
  log "  [warn] studio-manager/target/lib 不存在，依赖缺失将致 NoClassDefFoundError"
fi
cp -f "$WORKSPACE/backend/studio-manager-service/src/main/resources/application-manager.yml" "$STAGING/config/"
cp -f "$WORKSPACE/backend/studio-manager-service/src/main/resources/log4j2.xml" "$STAGING/config/log4j2-manager.xml"

# studio-service ← studio-runtime(target) 重命名 + target/lib 依赖 + config
log "  复制 studio-service 产物（来自 studio-runtime 模块）"
mkdir -p "$STAGING/app/service"
svcJar=$(find "$WORKSPACE/backend/studio-runtime/target" -maxdepth 1 -name 'studio-runtime-*.jar' ! -name '*-sources.jar' | head -1)
[ -n "$svcJar" ] || die "未找到 studio-runtime 产物 jar（先跑 mvn package）"
cp -f "$svcJar" "$STAGING/app/service/studio-service.jar"
if [ -d "$WORKSPACE/backend/studio-runtime/target/lib" ]; then
  cp -f "$WORKSPACE/backend/studio-runtime/target/lib/"* "$STAGING/app/service/"
else
  log "  [warn] studio-runtime/target/lib 不存在，依赖缺失将致 NoClassDefFoundError"
fi
cp -f "$WORKSPACE/backend/studio-runtime-service/src/main/resources/application-runtime.yml" "$STAGING/config/"
cp -f "$WORKSPACE/backend/studio-runtime-service/src/main/resources/log4j2.xml" "$STAGING/config/log4j2-runtime.xml"

# ── [2] 前端构建 (pnpm) ──────────────────────────────────────────────────────
log "[2/4] 前端构建 (frontend → dist/hws)"
cd "$WORKSPACE/frontend"
if ! command -v pnpm >/dev/null 2>&1; then
  log "  安装 pnpm..."; npm install -g pnpm
fi
pnpm install --ignore-scripts
pnpm run build
# angular.json outputPath base=dist/hws
mkdir -p "$STAGING/app/frontend/dist"
rm -rf "$STAGING/app/frontend/dist/hws"
cp -rf "$WORKSPACE/frontend/dist/hws" "$STAGING/app/frontend/dist/hws"

# ── [3] runtime 源码复制 ─────────────────────────────────────────────────────
log "[3/4] runtime(Python) 源码复制"
rm -rf "$STAGING/app/agent_runtime" "$STAGING/app/jiuwen" "$STAGING/app/agent_builder" "$STAGING/app/tests"
cp -rf "$WORKSPACE/agent-runtime/agent_runtime" "$STAGING/app/agent_runtime"
cp -rf "$WORKSPACE/agent-runtime/jiuwen"      "$STAGING/app/jiuwen"
cp -rf "$WORKSPACE/agent_builder"              "$STAGING/app/agent_builder"
cp -rf "$WORKSPACE/agent-runtime/tests"        "$STAGING/app/tests"
cp -f  "$WORKSPACE/agent-runtime/requirements.txt" "$STAGING/app/requirements.txt"

# ── [4] 生成 nginx.conf.tmpl + 复制 init.sql ────────────────────────────────
log "[4/4] 生成 nginx.conf.tmpl + 复制 init.sql"
# 由 deploy/config/nginx.conf 改写为原生模板：
#   upstream studio-*:<port>  → 127.0.0.1:<port>
#   alias /opt/cloud/wiseagent-nginx/nginx/dist/hws/ → @@BUNDLE_ROOT@@/app/frontend/dist/hws/
#   /opt/cloud/wiseagent-nginx/logs/ → @@BUNDLE_ROOT@@/logs/
#   include mime.types → @@BUNDLE_ROOT@@/config/mime.types
#   listen 80; → listen @@CONSOLE_PORT@@;
#   events 去掉 use epoll; multi_accept on;（Windows 不支持 epoll）
SRC_NGINX="$WORKSPACE/deploy/config/nginx.conf"
[ -f "$SRC_NGINX" ] || die "未找到 $SRC_NGINX"
sed \
  -e 's|server studio-manager:31111|server 127.0.0.1:31111|' \
  -e 's|server studio-service:31113|server 127.0.0.1:31113|' \
  -e 's|/opt/cloud/wiseagent-nginx/nginx/dist/hws|@@BUNDLE_ROOT@@/app/frontend/dist/hws|g' \
  -e 's|/opt/cloud/wiseagent-nginx/logs|@@BUNDLE_ROOT@@/logs|g' \
  -e 's|include       mime.types;|include @@BUNDLE_ROOT@@/config/mime.types;|' \
  -e 's|listen 80;|listen @@CONSOLE_PORT@@;|' \
  -e '/use epoll;/d' \
  -e '/multi_accept on;/d' \
  "$SRC_NGINX" > "$STAGING/config/nginx.conf.tmpl"

cp -f "$WORKSPACE/deploy/init.sql" "$STAGING/config/init.sql"
log "应用产物构建完成。"
