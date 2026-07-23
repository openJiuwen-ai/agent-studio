openJiuwen AgentStudio — 原生（免容器）运行包
====================================================

本目录是一个自包含、跨平台（Windows x64 / Linux x64）的运行包。
不依赖 Docker：MySQL / Redis / MinIO + 四个应用服务全部以本机原生进程运行。

目录结构
-------
  .env                 运行配置（首次从 .env.template 复制；改端口/口令改这里）
  .env.template        配置模板
  config/              应用配置（application-*.yml、log4j2-*.xml、nginx.conf.tmpl、init.sql、mime.types）
  app/                 应用产物
    studio-manager.jar / studio-service.jar   Java 服务
    frontend/dist/hws/                         前端构建产物（nginx 托管）
    agent_runtime/ jiuwen/ agent_builder/ tests/  runtime(Python) 源码
    requirements.txt
  deps/
    win/  jre-17 mysql-8.0 redis-7 minio mc python-3.11 nginx   Windows 原生依赖
    linux/ ...                                                Linux 原生依赖
    wheels/                  runtime Python 依赖离线 wheel（目标机免联网安装）
  scripts/
    start.sh / start.ps1     一键启动（infra→java→runtime→console + 健康检查）
    stop.sh  / stop.ps1      停止全部
    status.sh/ status.ps1    查看状态
    logs.sh  / logs.ps1      查看日志
    runtime_patches.py       可移植补丁（pip install 后自动跑一次，替代容器内 init.sh）
  data/   mysql/redis/minio 数据（首启生成）
  logs/   全部服务日志 + PID
  run/    PID 文件、mysql.sock、venv、最终 nginx.conf

一键启动
-------
  Linux:    ./scripts/start.sh
  Windows:  powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1

启动完成后访问：http://localhost/openjiuwen/   默认账号 agent / agent

端口（改 .env 后重启）
  80   控制台(console/nginx)   3306 MySQL   6379 Redis
  9000/9001 MinIO API/控制台    31111 manager   31113 service   31014 runtime

注意
  - Windows 非管理员无法绑 80 端口；start.ps1 检测到非 admin 会自动改用 8080 并提示。
  - Windows 不含 cron，因此不执行 runtime 的日志轮转定时任务（Linux 仍执行）。
  - 首次启动需创建 Python venv 并离线安装依赖（约 1-2 分钟）。
