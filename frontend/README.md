# jiuwen-agent-console

## 前提

建议使用 Node.js 22.12.0+。启动前应先按照[本地开发快速启动](../docs/zh/tutorial/01-quick-start.md)运行后端服务。

## 本地调试
### 1. 安装依赖
```bash
pnpm install --ignore-scripts
```
### 2. 配置代理
根据本地服务端口检查 `.staging/proxy.json`。默认配置将管理 API 转发到 `studio-manager` 的 `31111`，将运行时 API 转发到 `studio-runtime` 的 `31014`；使用项目 Compose 默认端口时不需要修改。
### 3. 启动
```bash
pnpm exec ng serve --configuration development
```

默认访问地址为 `http://localhost:4200/`。
