# openJiuwen AgentStudio — 免容器（Container-Free）构建与一键启动

把 AgentStudio 打成一个**单一跨平台包**（含 Windows x64 + Linux x64 两套原生依赖），
拷到 Windows 或 Linux 机器上**一键拉起全部原生进程**，不依赖 Docker。

## 组成

```
native-install/
  versions.env              # 原生依赖下载源（版本/URL/SHA256）—— 改版本只动这里
  build.sh                  # Linux 构建机：产出含 Win+Linux 依赖的单包（推荐主路径）
  build.ps1                 # Windows 构建机：同上（Linux redis/nginx 经 WSL 编译）
  lib/
    build_apps.sh / .ps1     # 复刻 docker/package.sh：mvn→jar、pnpm→dist、复制 runtime 源码
    fetch_deps.sh / .ps1     # 下载两平台原生依赖并规范化；Linux redis/nginx 从源码编译
    bundle_template/         # 运行时模板（.env.template、config、scripts/）
      scripts/
        start.sh / start.ps1     # 一键启动
        stop.sh  / stop.ps1      # 停止
        status.sh/ status.ps1     # 状态
        logs.sh  / logs.ps1       # 日志
        runtime_patches.py        # 可移植补丁（替代容器内 init.sh 的 sed hack）
        cron_backup_log.sh        # Linux 日志轮转（cron 调用）
```

## 组件与依赖

应用组件（**从源码构建**，跨平台产物，与 docker 新架构对齐）：
- `studio-manager.jar` ← `backend/studio-manager`（profile=manager，端口 31111）
- `frontend/dist/hws` ← `frontend`（pnpm build，nginx 托管，端口 CONSOLE_PORT）
- `agent_runtime/` + `jiuwen/` ← `agent-runtime`（Python 3.11，studio-runtime，端口 31014）
- `agent_builder/` ← `agent_builder`（Python 3.11，studio-builder，端口 31015）
- `model_service/` + `storage/` + `common_utils/` ← `packages/*` 共享包（PYTHONPATH=app 非 pip 安装）
- 注：旧 Java「agent-service」(studio-runtime 模块，31113) 已随代码库删除，由 Python studio-builder 替代。

外部原生依赖（**构建时联网下载并内置**，两平台各一份）：
JRE17(Temurin) / MySQL8.0 / Redis7 / MinIO+mc / Python3.11(python-build-standalone) / nginx
- Linux redis 用 Remi el7 预编译 RPM（glibc 2.17）；Linux nginx 无官方预编译二进制，由构建机 gcc 编译
  （带 gzip+rewrite 模块并静态捆绑 pcre2+zlib，产物自包含）。
- Windows Redis 用社区移植版 redis-windows（官方无 Windows 版）。

## 构建

### 在 Linux 构建机（推荐，产出完整跨平台包）
```bash
cd native-install
./build.sh                    # 全量构建
# 可选：./build.sh --skip-apps / --skip-deps / --skip-wheels  跳过阶段
# 可选：./build.sh -v 1.0.1    自定义版本号
# 可选：./build.sh --seed-deps <上次构建目录或解压后的包根>   复用已有 deps/（免重新下载/编译）
```
构建机前置：JDK17+Maven、Node+pnpm、Python3+pip、gcc+make（编译 redis/nginx）、curl/unzip/tar。
产物：`native-install/dist/AgentStudio-native-<ver>-<windows|linux>.zip`（双平台包）。

### 在 Windows 构建机
```powershell
cd native-install
.\build.ps1
```
构建机前置：JDK17+Maven、Node+pnpm、Python+pip、tar（Win10+ 自带）。
Linux 的 redis/nginx 需 Linux 工具链编译——`fetch_deps.ps1` 会优先用 **WSL** 调用
`fetch_deps.sh` 完成编译；无 WSL 则告警并跳过（请在 Linux 主机跑 `build.sh` 或用 wsl 补齐
`deps/linux/redis-7` 与 `deps/linux/nginx` 后再打包）。

## 目标机一键启动

把包解压到任意目录，进入包根：
```bash
# Linux
./scripts/start.sh
# Windows（建议以管理员运行，否则控制台改用 8080）
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```
启动后访问 `http://localhost/openjiuwen/`（无需登录）。

管理：`stop.sh/.ps1` 停止、`status.sh/.ps1` 状态、`logs.sh/.ps1 [服务名]` 日志。

## 端口（改 .env 重启）

| 服务 | 端口 | | 服务 | 端口 |
|---|---|---|---|---|
| console(nginx) | 80 | | MinIO API/控制台 | 9000/9001 |
| MySQL | 3306 | | manager | 31111 |
| Redis | 6379 | | runtime | 31014 |
| | | | builder | 31015 |

## 平台差异

- **Windows 非 admin 无法绑 80**：`start.ps1` 自动改用 8080 并提示；以管理员重跑恢复 80。
- **Windows 不含 cron**：不执行 runtime 的日志轮转定时任务（Linux 仍执行）。
- **runtime 第三方包补丁**：`scripts/runtime_patches.py` 用 `site.getsitepackages()` 解析真实
  venv 路径后打补丁（SpiffWorkflow 循环、jionlp、mcp SSL），替代容器内 `init.sh` 的硬编码 sed。

## 自定义

- **依赖版本/源**：改 `versions.env`（填 SHA256 后强校验）。
- **端口/口令**：改包内 `.env`。
- **API 文档（Swagger UI）**：`.env` 中设 `API_DOCS_ENABLED=true` 开启，同时启用管理面文档（`http://127.0.0.1:31111/swagger-ui.html`）和运行面文档（`http://127.0.0.1:31014/runtime/docs`）。默认关闭，按需开启。
- **JVM 堆**：`start.sh/.ps1` 按宿主内存 ×0.6 自动计算，可手改。
