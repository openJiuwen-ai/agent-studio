# 日志聚合方案

> ⚠️ **适用范围**：本方案（VictoriaLogs + Vector + Grafana）只适用于 **docker-compose 部署**（`deploy/docker-compose.yml`）。K8s 场景请使用日志采集 DaemonSet 和集中式日志存储。

项目提供两套日志聚合栈（均基于 docker-compose），按部署规模选择：

| | **L1 单机模式** | **L2 跨节点模式** |
|---|---|---|
| 适用 | 所有服务同一台主机 | app 与监控分机部署 |
| 存储 | VictoriaLogs 本地文件系统 | VictoriaLogs 本地文件系统（监控节点盘） |
| 日志查询 | LogsQL 全文索引 | LogsQL 全文索引 |
| 鉴权 | 仅本机 Docker 网络 | nginx-gateway HTTPS + 写入/查询分权 Basic Auth |
| 文件位置 | `deploy/docker-compose.yml`（`profiles: [logging]`） | `deploy/observability/` |
| 启停 | `./deploy.sh logging` | `./deploy.sh monitor`（监控节点）+ `./deploy.sh logging-remote`（app 节点） |

两套都使用 **VictoriaLogs + Vector + Grafana**，查询语言、Dashboard 和排障方式一致。

---

## L1 单机模式（所有服务同机）

### 架构
```
studio-manager / service / runtime / console ──命名卷──▶ Vector ──push──▶ VictoriaLogs(本地存储) ──▶ Grafana
```
四个 app 服务把日志写命名卷，Vector 以只读方式 tail，并通过 Elasticsearch Bulk API 写入本机 VictoriaLogs。首次启动从文件开头采集，之后依赖持久化 checkpoint 续采；Vector 使用持久化磁盘缓冲。日志栈用 `profiles: ["logging"]` 隔离，默认 `./deploy.sh start` 不启动。

### 启停
```bash
cd deploy
./deploy.sh start          # 先确保 app 在跑（日志才会写入命名卷）
./deploy.sh logging        # 启动日志栈（等价 logging start）
./deploy.sh logging stop   # 停止
./deploy.sh logging status
```
Grafana：`http://<宿主机IP>:3000/`（admin / admin）

---

## L2 跨节点模式（app 与监控分机）

### 核心设计
1. **Vector 跟 app 走**（每个 app 节点一个）—— 日志文件是本地的，跨节点读不到。
2. **VictoriaLogs + Grafana + gateway 集中**在监控节点。
3. **本地存储**（VictoriaLogs 存监控节点本地盘，无对象存储依赖）。

### 架构
```
┌─ app 节点 1 ─┐  ┌─ app 节点 2 ─┐        ┌─ 监控节点 ──────────────────────┐
│ app 服务     │  │ app 服务     │        │  nginx-gateway (BasicAuth)      │
│ Vector       │  │ Vector       │ ─HTTPS─▶│     ↓                           │
│ host=node-1  │  │ host=node-2  │        │  VictoriaLogs (本地存储)         │
└──────────────┘  └──────────────┘        │  Grafana ─直连─ VictoriaLogs    │
   每个 app 节点一个 Vector，             │                                │
   可水平扩展到 N 个，统一 push 到 gateway  │                                │
                                          └──────────────────────────────────┘
```
> gateway 默认强制 HTTPS，并为 Vector 写入和外部查询使用两套独立凭据。自签名 CA 由监控节点生成，必须安全复制到 app 节点。

### 部署步骤

**① 监控节点**（用 deploy.sh 统一入口，或直接跑脚本）：
```bash
cd deploy
./deploy.sh monitor                # 启动（首次会生成 observability/.env，改完再跑）
./deploy.sh monitor stop           # 停止
./deploy.sh monitor status         # 状态
```

**② app 节点**（先 app 后 vector，顺序不能反）：
```bash
cd deploy
./deploy.sh start          # 1) 先启动 app 服务（建立命名卷）
./deploy.sh logging-remote # 2) 再启动远程 vector（push 到监控节点）
```

监控节点和 app 节点都使用 `deploy/observability/.env`。每个 app 节点需设置自己的
`NODE_NAME`，将 `LOGS_GATEWAY_HOST` 指向与证书 SAN 一致的监控节点地址，并配置相同的
`LOGS_WRITE_USER/LOGS_WRITE_PASSWORD`。监控节点启动后，还需把 `config/gateway-ca.crt`
安全复制到 app 节点。旧版本的 `.env.promtail` 已取消，升级时请把其中的节点和 Gateway 配置合并进 `.env`。

**③ 查询**：浏览器开监控节点 `http://<监控节点IP>:3000/`，Explore → VictoriaLogs。

### 前提条件（跨节点必须满足）
- **网络可达**：app 节点 → 监控节点 gateway 端口
- **时钟同步**：所有节点 chrony/NTP 对齐
- **app 服务先起**：命名卷由 app 服务创建，Vector 用 external 卷引用它们
- **Compose project 隔离**：监控端和采集端默认分别使用 `observability-monitor` / `observability-agent`，同机演练时互不误删

---

## 日志生命周期：自动清理（VictoriaLogs retention）

VictoriaLogs 默认保留 **7 天**，可通过 `VICTORIA_LOGS_RETENTION` 配置。超期日志自动删除。

Vector 会从 Java、Python runtime 和 NGINX 日志正文解析事件时间，并将其写入 VictoriaLogs
的 `_time`。首次导入历史文件时，保留期和 Grafana 时间范围均按日志真实发生时间计算，
不会把历史错误误判为采集时刻的新错误；无法识别时间格式时才回退到采集时间。

### 关键注意
1. **retention 是时间维度**。保留期内的日志量如果超过监控节点磁盘容量，仍会写满，需要通过宿主机磁盘工具定期检查。
2. **VictoriaLogs 用本地存储**（不是对象存储）。监控节点盘满会影响 VictoriaLogs、Grafana 和 Docker 本身。
3. **app 节点也有盘满风险**：除 app 自己的滚动日志外，后端不可用时 Vector 会写持久化缓冲。用 `VECTOR_BUFFER_MAX_SIZE` 限制缓冲上限。

---

## LogsQL 查询（VictoriaLogs，L1/L2 通用）

Grafana → Explore → VictoriaLogs datasource：
```
*                                  # 所有日志
_stream:{service="manager"}        # 按 service 过滤（LogsQL stream filter）
_stream:{service="runtime"} WARN   # runtime 的 WARN 日志（全文搜索）
WARN                                # 所有服务的 WARN
```

> **VictoriaLogs 变量限制**：Grafana 变量查询（`field_values`/`label_values`）在当前 plugin 版本报 "missing field"（[Issue #308](https://github.com/VictoriaMetrics/victorialogs-datasource/issues/308)）。dashboard 用 **custom 变量**（manager/service/runtime/console）绕过。

---

## Grafana Dashboard 预览

### Grafana 总览（所有 dashboard）
![Grafana 总览](../observability/images/1-grafana_overviews.png)

### VictoriaLogs 日志查询（全文搜索，秒级，按 service 过滤）
![VictoriaLogs 日志查询](../observability/images/3-grafana_victoriallogs.png)

### Grafana Explore（临时查询，LogsQL）
![Grafana Explore](../observability/images/5-grafana_explore.png)

---

## 排障（L1/L2 通用）

**Grafana 查不到日志**：
1. app 在跑吗？`./deploy.sh status`（L1）/ 确认 app 服务在跑（L2）。
2. Vector 在读吗？`docker logs --tail 30 <vector容器>`。
3. VictoriaLogs 有数据吗？
   ```bash
   docker exec observability-victoria-logs-1 wget -qO- "http://127.0.0.1:9428/select/logsql/query?query=*&limit=3"
   ```

**某服务没日志（如 runtime）**：
Vector 是「被动 tail」——只在日志文件有新行时才 push。服务没活动时（如 runtime 没跑工作流），日志文件不增长，不 push。**触发该服务活动**（界面调试 agent / 发起对话）。

**push 失败 / VictoriaLogs 收不到数据**：
1. 看 Vector 日志：`docker logs --tail 100 <vector容器>`；健康端点：`http://127.0.0.1:8686/health`。
2. L2 看 gateway 日志：`docker logs <gateway容器>`
3. VictoriaLogs 健康：`docker exec observability-victoria-logs-1 wget -qO- http://127.0.0.1:9428/health`

**L2 特有**：
- Vector 报 401/403 → app 节点与监控节点 `.env` 中的 Gateway 凭据不一致
- Vector 报 connection refused / no route → 监控节点 gateway 未启动或 `LOGS_GATEWAY_HOST` IP 写错
- Vector external 卷不存在 → app 服务没先启动

**VictoriaLogs dashboard 变量报 "missing field"**：
VictoriaLogs plugin 的动态变量查询（field_values）不支持。用 **custom 变量**（硬编码选项）。

**常见配置报错速查**：

| 报错 | 根因 | 修复 |
|---|---|---|
| Grafana `Plugin not found` | 未使用项目的内置插件镜像 | 配置 `${GHCR_IMAGE_REPOSITORY}/grafana-victorialogs:${GRAFANA_IMAGE_TAG}` 或显式 `GRAFANA_IMAGE`，不要在容器启动时在线安装 |
| Vector 缓冲持续增长 | VictoriaLogs 或 gateway 不可达 | 修复后端后观察缓冲回落，并确认 Vector 无重试错误 |
| gateway `htpasswd Permission denied` | htpasswd 权限过严 | `chmod 644`（deploy-monitor.sh 已默认） |
| Vector push `no route to host` | LOGS_GATEWAY_HOST IP 写错 | 确认是监控节点真实 IP（`hostname -I`） |

---

## 演进路径

| 级别 | 形态 | 适用 |
|---|---|---|
| **L1** | 单机 + VictoriaLogs 本地存储（当前内置） | 1-2 个 app 节点 |
| **L2** | 单监控节点 + VictoriaLogs 本地 + gateway | 中小规模生产 |
| L3 | 监控节点 HA（多副本 + 共享存储）；Grafana 多副本 + 共享 DB | 监控节点不能单点 |

**L1 → L2** 增加跨节点集中采集和鉴权网关。VictoriaLogs 当前使用本地存储，监控节点是单点；需要更高可靠性时，应增加备份或评估支持共享存储的集群方案。
