# openJiuwen Agent Studio 部署工具使用手册

本脚本是 openJiuwen Agent Studio 一站式自动化容器部署工具，与本地部署方式存在本质差异 —— 全程基于容器化技术实现，不依赖本地系统环境配置，彻底规避本地部署的环境冲突、版本兼容等问题。本工具实现单机单点部署，支持配置集中化管理、多实例隔离部署，可一键完成服务的部署、启停、卸载等全生命周期操作，操作简洁高效，无需复杂的手动配置。

## 部署目录说明

```bash
scripts/
├── .env                            # 脚本运行的部署相关的环境变量文件（自动生成）（启动的最近的那套实例服务）
├── .env.custom                     # 用户自定义变量覆盖文件（用户手动修改，优先级最高，用于覆盖默认变量）
├── .env.deploy.default             # 部署相关默认变量文件（禁止修改）
├── .env.runtime.default            # 运行时相关默认变量文件（禁止修改）
├── .envs/                          # 多实例服务变量文件归档目录（自动生成）
│   ├── env.deploy.<实例ID>         # 某实例的部署变量备份文件
│   ├── env.runtime.<实例ID>        # 某实例的运行时变量文件（直接挂载到容器的环境变量文件）
│   └── ...                         # 其他服务实例的变量文件
├── conf/                           # 服务配置模板与生成后的配置文件目录
│   ├── config.json                 # Agent Studio配置文件
│   ├── config.yaml                 # Agent Studio配置文件
│   ├── docker-jiuwen.template.yml  # Agent Studio主服务容器模板文件
│   ├── docker-jiuwen.yml           # 当前实例的Agent Studio容器最终配置文件（自动生成）
│   ├── docker-milvus.template.yml  # Milvus向量库容器模板文件
│   ├── docker-milvus.yml           # 当前实例的Milvus容器最终配置文件（自动生成）
│   ├── docker-mysql.template.yml   # MySQL数据库容器模板文件
│   ├── docker-mysql.yml            # 当前实例的MySQL容器最终配置文件（自动生成）
│   ├── docker-sandbox.template.yml # Sandbox沙箱容器模板文件
│   ├── docker-sandbox.yml          # 当前实例的Sandbox容器最终配置文件（自动生成）
│   ├── docker-plugin.template.yml  # Plugin Server插件服务容器模板文件
│   ├── docker-plugin.yml           # 当前实例的Plugin Server容器最终配置文件（自动生成）
│   ├── docker-upgrade.template.yml # 升级服务容器模板文件
│   ├── docker-upgrade.yml          # 当前实例的升级容器最终配置文件（自动生成）
│   ├── docker-deepsearch.template.yml  # deepsearch服务容器模板文件
│   ├── docker-deepsearch.yml           # 当前实例的deepsearch容器最终配置文件（自动生成）
│   ├── nginx.template.conf         # Nginx通用配置模板
│   ├──  .nginx-files/              # 多实例Nginx配置文件目录（自动生成）
│   │   ├── nginx.conf-<实例ID>     # 某前端实例的Nginx最终配置文件（自动生成）
│   │   └── ...                     # 其他实例的Nginx配置文件（自动生成）
│   ├── .ssl-dirs/                  # 多实例前端服务SSL证书存储目录（自动生成）
│   │   ├──  ssl-<实例ID>/          # 某前端服务实例的SSL证书目录（自动生成）
│   │   │   ├── certificate.crt     # SSL公钥证书（供Nginx配置HTTPS）（自动生成）
│   │   │   └── private.key         # SSL私钥文件（禁止泄露）（自动生成）
│   └── ...                         # 其他前端实例的证书目录
├── pre_upgrade_envs/               # 升级前旧实例的变量配置文件目录
├── examples/                       # 后端业务示例配置目录
├── log-dirs/                       # 所有实例的服务日志、升级日志归档目录（自动生成）
│   ├── logs-<实例ID>/              # 某实例的服务日志、升级日志目录
│   │   ├──  deepsearch/            # deepsearch服务模块的log目录
│   │   ├──  server/                # 后端服务模块的log目录
│   └── ...
├── .sqlite-dirs/                   # SQLite数据库升级过程中的临时数据目录（自动生成，升级完成后可清理）
│   ├── databases.preupgrade.<实例ID>
│   ├── databases.postupgrade.<实例ID>
│   └── ...
├── .upgrade/                       # 实例级组件升级脚本存储目录（按组件+实例隔离）
│   ├── upgrade-milvus-<实例ID>.sh
│   ├── upgrade-mysql-<实例ID>.sh
│   ├── upgrade-sqlite-<实例ID>.sh
│   └── ...
├── readme-service-script.md        # 脚本使用直指导文档
├── service.sh                      # 部署脚本核心入口（接收用户指令，调度其他子脚本）
├── args_handler.sh                 # 命令行参数解析脚本
├── common.sh                       # 通用工具函数脚本
├── gen_ssl.sh                      # SSL证书生成脚本
├── prompt_handler.sh               # 交互式提示脚本
├── vars_handler.sh                 # 变量处理核心脚本
├── container_handler.sh            # 容器管理脚本
├── global_vars.sh                  # 全局变量定义脚本
├── envfile_handler.sh              # 环境文件处理脚本
├── ports_handler.sh                # 端口管理脚本
├── cmd.sh                          # 命令封装脚本
├── template_handler.sh             # 模板渲染脚本
├── upgrade_handler.sh              # 升级流程核心处理脚本（封装版本检测、数据迁移、容器升级逻辑）
├── version_handler.sh              # 版本管理脚本（封装版本号解析、版本对比、版本验证等版本相关逻辑）
└── service_handler.sh              # 服务生命周期管理脚本（封装服务启动/停止/重启/状态检查逻辑）

```

本脚本原生支持多实例隔离部署能力，所有服务实例均通过「实例ID」做唯一标识，不同实例的配置、容器、数据卷、日志完全隔离，互不干扰，可在同一台服务器上部署多套独立的 Agent Studio 服务。所有配置按「实例ID」区分不同服务实例；

脚本运行依赖环境变量配置：`.env.deploy.default` 和`.env.runtime.default` 为默认环境变量文件（内置基础默认值，请勿修改）；如需自定义配置，可在`.env.custom`中配置变量以覆写默认值；

> 注意：Docker 的镜像、容器运行时数据、数据卷、网络配置等核心存储，默认路径是：/var/lib/docker/， 而多数 Linux 发行版（CentOS、Ubuntu、Debian）默认不单独划分 /var 分区，/var 只是根分区 / 下的普通目录，共用 ** 系统盘（根分区）** 的空间。建议客户把 /var 单独挂载到空间充足的独立分区 / 独立数据盘，和系统盘隔离，即便 /var 占满，也不会影响根分区的系统核心运行。

## 核心功能

✅ 基础核心能力

- 一键启停 / 卸载 Agent Studio 完整服务体系，包含 MySQL、Etcd、MinIO、Milvus、前端、后端、插件服务、沙箱服务等所有依赖组件；
- 独立启停 / 卸载指定的单个或多个组件服务，支持精准运维，组件包含：mysql、milvus、jiuwen、plugin、sandbox；
- 自动创建服务运行所需的 Docker 网络、数据卷，无需手动初始化环境；
- 自动检测并分配未占用端口，避免端口冲突问题，也支持手动指定端口配置；
- 多实例隔离部署，实例间配置、容器、数据完全隔离，支持多套服务共存。

✅ 容器 / 资源生命周期规则

为保障数据安全与运维灵活性，脚本对容器、网络、数据卷的生命周期做标准化管理，规则如下：

- 启动（up）：自动创建 Docker 网络、数据卷，拉取 / 启动所有容器，容器状态为运行中；
- 停止（stop）：仅停止运行中的容器，不删除容器、网络、数据卷，重启时可快速恢复服务，数据不丢失；
- 卸载（down）：停止并删除所有相关容器、Docker 集群网络，保留所有数据卷，保障数据安全；
- 数据清理：如需清理服务数据，需手动删除对应的数据卷，脚本不会自动清理任何持久化数据。

## 使用说明

✔️ **版本要求**

请确保部署环境满足以下版本要求：

- Docker：20.10 版本及以上
- Docker Compose：v2.19.1 及以上版本
- Bash: 5.2及以上版本

✔️ **参数说明**

```
$ ./service.sh --help
用法: ./service.sh [模块] [命令] [选项]

命令:
  up        启动服务
  down      停止服务并彻底清理相关资源
  stop      临时暂停运行中的服务（可重新启动）

选项:
  -h,--help  显示此帮助信息并立即退出
  -f,--file  指定.env配置文件的路径（适用于已存在的服务）
  -n,--new   强制启动全新的服务实例（忽略已存在的.env文件,自动生成全新配置）
  --upgrade  启动由低版本服务升级而来的全新服务实例。

模块（可选参数）:
  milvus        部署 Milvus 模块
  jiuwen        部署 Jiuwen 模块
  mysql         部署 MySQL 模块
  plugin        部署插件模块
  sandbox       部署沙箱模块
  deepsearch    部署deepsearch模块

注意: 未指定任何模块时，默认部署所有模块
```

✔️ **完整服务 一键运维指令**

1. 一键启动全新完整服务

```
# 自动整合配置、生成新实例标识、启动全套服务（首次部署推荐使用）
# 如需自定义配置，请先在当前目录的.env.custom文件中配置相关变量后再执行
$ ./service.sh up -n
```

- 若需全新部署全套服务，建议添加 -n 参数执行启动命令。该参数将忽略现有配置文件，重新生成全新的标准化配置后启动服务。
- 若只是需要重新初始化完整服务，并且十分确定历史启动残留的`.env`配置文件准确无误，可以不加-n 参数，继续沿用老配置信息。

2. 重启指定的已有服务实例

```
# 通过脚本自动备份的配置文件，精准重启指定的服务实例
$ ./service.sh up -f .envs/env.deploy.<实例ID>
```

3. 一键停止当前生效的服务实例

```
# 停止最近一次启动的服务（默认读取当前目录的 .env 配置文件）
$ ./service.sh stop

# 精准停止指定的服务实例
$ ./service.sh stop -f .envs/env.deploy.<实例ID>
```

4. 一键卸载当前生效的服务实例

```
# 停止并删除所有容器、清理集群网络，保留所有数据卷（读取当前目录 .env 文件）
$ ./service.sh down

# 精准卸载指定的服务实例
$ ./service.sh down -f .envs/env.deploy.<实例ID>
```

✔️ **指定组件 独立运维指令**
支持对单个组件进行精准启停 / 卸载，也支持同时对任意数量的组件进行批量运维，组件名称固定支持：mysql、milvus、jiuwen、plugin、sandbox、deepsearch，指令格式统一、灵活易用，单点 / 集群完全通用。

1. 独立启动指定组件（全新实例 / 已有实例）

```
# 启动单个组件（全新实例，自动生成配置）
$ ./service.sh mysql up -n
$ ./service.sh milvus up -n
$ ./service.sh jiuwen up -n
$ ./service.sh plugin up -n
$ ./service.sh sandbox up -n
$ ./service.sh deepsearch up -n

# 重启指定的已有组件实例
$ ./service.sh mysql up -f .envs/env.deploy.<实例ID>
$ ./service.sh milvus up -f .envs/env.deploy.<实例ID>
```

2. 独立停止指定组件（当前实例 / 指定实例）

```
# 停止单个组件（当前生效的服务实例）
$ ./service.sh mysql stop
$ ./service.sh milvus stop
$ ./service.sh sandbox stop

# 停止指定的组件实例
$ ./service.sh mysql stop -f .envs/env.deploy.<实例ID>
$ ./service.sh jiuwen stop -f .envs/env.deploy.<实例ID>
```

3. 独立卸载指定组件（当前实例 / 指定实例）

```
# 卸载单个组件（停止并删除对应容器，保留数据卷）
$ ./service.sh mysql down
$ ./service.sh plugin down
$ ./service.sh milvus down

# 卸载指定的组件实例
$ ./service.sh milvus down -f .envs/env.deploy.<实例ID>
$ ./service.sh sandbox down -f .envs/env.deploy.<实例ID>
```

✔️ **多组件 批量运维指令（高效推荐）**
支持一次指定任意数量的组件，执行批量启动 / 停止 / 卸载操作，指令格式简洁，大幅提升运维效率，所有组合均支持指定备份配置文件，单点 / 集群通用，是日常运维的最优选择：

```
# 批量启动多个组件（全新实例）
$ ./service.sh milvus mysql plugin jiuwen up -n

# 批量重启多个指定组件实例
$ ./service.sh milvus mysql sandbox up -f .envs/env.deploy.<实例ID>

# 批量停止多个组件
$ ./service.sh milvus plugin jiuwen stop

# 批量卸载多个指定组件实例
$ ./service.sh mysql milvus plugin sandbox down -f .envs/env.deploy.<实例ID>

```

## 变量说明

✅ 配置文件分类：部署类变量(deploy) + 运行时类变量(runtime)，两类配置分离管理，职责清晰；
✅ 部署类变量：其默认值定义于 `.env.deploy.default`;
✅ 运行类变量：其默认值定义于 `.env.runtime.default`；
✅ 所有变量均可在当前目录的 `.env.custom`文件中配置，优先级最高，用于覆盖默认配置，无特殊需求请勿修改默认值；
✅ 注释为 #变量名=值 的为脚本自动分配的默认值，无需手动配置；无注释的为固定配置项，按需修改即可。

**部署类变量的处理**
服务第一次启动时，本工具会自动整合部署类变量的配置，也就是`.env.deploy.default` + `.env.custom`，并生成最终生效的 `.env` 文件（该文件是当前服务运行的核心配置）, 并将该`.env` 文件备份成`.envs/env.deploy.<实例ID>`， 该文件是对应服务启动、运行和重启的核心配置，请勿删除。

> 注意，多次启动之后， `.env` 文件记录的是启动的最近的那套实例服务的配置。

**运行类变量的处理**
服务第一次启动时，本工具也会自动整合运行类变量的配置， 也就是`.env.runtime.default` + `.env.custom`，并生成`.envs/env.runtime.<实例ID>`，此文件会作为前后端容器的环境变量文件。

✔️ **补充说明**

- 所有配置变量均为 按需配置，对于没有定义的变量，脚本将自动使用内置默认值，不影响服务运行；
- 多实例部署场景下，所有实例的端口、容器名、数据卷名均由脚本自动生成唯一值，无需手动配置，彻底避免资源冲突；若需自定义相关配置，需由使用者自行关注并处理潜在的资源冲突问题。

# 一键部署升级指导

## 前置准备：旧版本配置文件

将旧版本实例的配置文件，复制至新版本部署工具的 pre_upgrade_envs 目录下。不同版本旧实例的配置文件如下：

- 旧版本 0.1.1：`.env.<实例ID>`
- 旧版本 0.1.2：`.envs/env.<实例ID>`
- 旧版本 0.1.3：`.envs/env.deploy.<实例ID>` 与 `.envs/env.runtime.<实例ID>`

> 关于如何查看本实例的实例ID，请参考[这里](#如何查看服务实例的实例id)。

## 升级约束说明和配置要求

1. 本升级流程仅支持从低版本向高版本升级，或者同版本的数据迁移，不支持版本回退或降级操作。支持的版本迁移路径如下：

| 源版本 | 目标版本 | 支持状态               |
| :----- | :------- | :--------------------- |
| 0.1.1  | 0.1.4    | 支持                   |
| 0.1.2  | 0.1.4    | 支持                   |
| 0.1.3  | 0.1.4    | 支持                   |
| 0.1.4  | 0.1.4    | 支持（同版本数据迁移） |

2. 本升级流程仅支持同类型数据库组件的平滑迁移，需确保新旧版本实例的数据库组件类型完全一致：

- 若旧版本实例使用 MySQL 组件，新版本实例需继续使用 MySQL 组件；
- 若旧版本实例使用 Milvus 组件，新版本实例需继续使用 Milvus 组件。

3. 若升级涉及 MySQL 或 Milvus 组件，请确保[旧版本实例配置文件](#前置准备旧版本配置文件)中，已正确配置实例运行所在机器的 IP 地址变量，保障升级组件和旧版本实例的宿主机的网络连通性。

```
IP=<实例组件所在服务器的IP地址>
```

4. 若升级涉及 SQLITE 组件，请确保新旧版本实例在同一台物理机上。

5. 不支持外挂 MySQL 组件或者外挂 Milvus 组件的数据迁移和升级。

6. 升级过程中需对旧实例的 MySQL 与 Milvus 组件数据进行拷贝，并迁移至新实例。请在升级前核查旧实例上述组件的数据总量，确保磁盘剩余空间不低于该总量的两倍，以满足升级所需空间条件。

## 执行升级命令

在新版本部署工具的根目录下，执行以下一键升级命令，启动新版本实例并完成旧数据迁移：

```
$ ./service.sh up -n --upgrade
```

命令执行完成后，新启动的新版本实例将自动继承旧版本实例的大部分业务数据，实现无感知升级与数据平滑迁移。

> 注意，部分数据，如`记忆数据`和`知识库原文件`，暂不支持迁移，将在未来版本中支持。

此外，针对有手动升级需求的客户，本部署工具支持独立启动升级容器。容器镜像已预装全部升级所需工具包，无需客户额外下载，可直接通过以下命令启动使用：

```
$ ./service.sh upgrade up -n
```

# FAQ

## 如何查看服务实例的实例ID

实例ID是每个服务实例的唯一身份标识，用于区分不同的服务实例配置文件、容器资源等核心关联信息，在多实例部署场景中尤为关键—— 所有针对指定实例的配置修改、运维操作，均需通过该随机标识精准定位目标实例，避免操作串号、资源冲突等问题。

**查看步骤**

1. 确认当前服务的访问地址：启动服务后，通过 `https://<服务运行IP>:<服务运行端口>/login` 访问 openJiuwen 智能体平台，请务必记录该访问端口；

2. 登录服务运行的服务器，执行`docker ps -a | grep <服务运行端口>`命令，查询对应的前端服务容器。从查询结果的容器名称中，提取末尾的实例ID（容器名格式为jiuwen-frontend-<实例ID>）。

**实操示例**

若当前服务的访问地址为：`https://localhost:3000/login`，则需记录核心端口为3000；
在服务运行服务器执行查询命令：

```
docker ps -a | grep 3000
```

命令返回结果如下，重点查看最后一列的容器名称：

```
6e9db4f73a03   swr.cn-north-4.myhuaweicloud.com/openjiuwen/studio-web-amd64:0.1.2b6   "/usr/local/bin/star…"   22 hours ago   Up 5 minutes (healthy)   0.0.0.0:3000->3001/tcp, [::]:3000->3001/tcp   jiuwen-frontend-wd63t
```

该容器名称为`jiuwen-frontend-wd63t`，末尾的`wd63t`即为该服务实例的实例ID。

> 注意：实例ID十分重要，后续对该实例执行配置修改、服务重启、实例维护等所有操作，均需基于此标识定位对应配置文件（如.envs/env.deploy.<实例ID>、.envs/env.runtime.<实例ID>）。

## 如何修改配置中变量

本工具的配置变量分为**部署类变量**和**运行时类变量**两类，不同服务状态（全新部署 / 已有服务调整）对应不同的变量修改流程，以下为标准化操作步骤：

### 全新服务启动（首次部署）

若为全新服务部署，部署类变量与运行时类变量均在统一配置文件中修改 `deploy/service/.env.custom`，修改完毕请如下执行启动命令完成部署：

```
$ ./service.sh up -n
```

### 已有服务配置变量修改

针对已部署的服务调整配置变量，需先停止服务，再根据变量类型修改对应文件，最后重新启动，分以下两种场景操作：

**场景 1：单套服务部署 / 确认修改最近启动的服务**

```
# 第一步：停止当前服务
$ ./service.sh down
# 第二步：根据变量类型修改对应文件
# 部署类变量：编辑根目录 .env 文件
# 运行时类变量：编辑 .envs/env.runtime.<实例ID> 文件
# 第三步：重新启动服务
$ ./service.sh up -f .env
```

**场景 2：通用万能流程（推荐，适配所有已部署场景）**

适用于部署过多套服务、无法确认目标服务实例，或需确保操作无误差的所有场景，为最稳妥的标准化操作：

```
# 第一步：停止当前服务
$ ./service.sh down
# 第二步：根据变量类型修改对应文件
# 部署类变量：编辑 .envs/env.deploy.<实例ID> 文件
# 运行时类变量：编辑 .envs/env.runtime.<实例ID> 文件
# 第三步：指定配置文件重新启动服务
$ ./service.sh up -f .envs/env.deploy.<实例ID>
```

## 如何修改前端页面服务的端口号

通过部署工具部署的前端容器服务，其访问端口默认由系统自动分配（未定义指定变量时，将分配当前未被占用的端口）；若需自定义固定端口，可参考[如何修改配置中变量](#如何修改配置中变量)的操作方法，在配置文件中新增端口定义变量即可，配置示例如下：

```
FRONTEND_HOST_PORT=3008
```

## 如何对接外部服务

除了**全量服务部署**， 本部署工具还支持**部分服务组合部署**。若需跳过工具内置的配套服务、对接外部已有服务，可参考以下配置流程。

### 如何对接外部 MySQL 数据库服务

**操作步骤**

1. 配置外部 MySQL 连接信息

在部署目录的配置文件`deploy/service/.env.custom`中，新增并完善以下环境变量，填入外部 MySQL 服务的真实参数：

```
DB_TYPE=mysql
DB_HOST=<MySQL服务地址>
DB_PORT=<MySQL服务端口>
DB_USER=<MySQL服务用户名>
DB_PASSWORD=<MySQL服务密码>
OPS_DB_NAME=<运维数据库名称，示例：openjiuwen_ops>
AGENT_DB_NAME=<业务数据库名称，示例：openjiuwen_agent>
```

2. 前置数据库准备

需提前在外部 MySQL 服务中，手动创建上述配置中指定的 OPS_DB_NAME 和 AGENT_DB_NAME 两个数据库实例；同时确保配置的 MySQL 账号，具备这两个数据库的 读写权限，避免服务启动后无法正常连接

3. 启动不含内置 MySQL 组件的服务群

执行以下命令，启动剔除内置 MySQL 模块的服务组：

```
$ ./service.sh milvus plugin sandbox jiuwen up -n
```

### 如何对接外部 Milvus 数据库服务

**操作步骤**

1. 配置外部 Milvus 连接信息

在部署目录的配置文件`deploy/service/.env.custom`中，新增并完善以下环境变量，填入外部 Milvus 服务的真实参数：

```
MILVUS_HOST=<Milvus服务地址>
MILVUS_PORT=<Milvus服务端口>
# 向量集合名称，默认无需修改
MILVUS_COLLECTION_NAME="memory_vector"
# 若外部 Milvus 开启认证，填入对应 Token；无认证则留空
MILVUS_TOKEN=""
```

2. 启动不含内置 Milvus 组件的服务群

执行以下命令，启动剔除内置 Milvus 模块的服务组：

```
$ ./service.sh mysql plugin sandbox jiuwen up -n
```

## 如何启动 Agent Studio 的依赖服务

若用户采用**本地部署模式**搭建 Agent Studio，通常需要自行部署 MySQL、Milvus、Plugin Server、SandBox 这四个依赖服务，存在部署难度高、环境配置复杂、耗时较长等问题。

为降低用户使用门槛、帮助用户快速上手，本部署工具支持**单个或多个组合服务独立部署**功能，可按需拉起指定的**容器化服务**，供本地部署的 Agent Studio 直接调用，用户可选择自行部署，或者利用本工具拉起依赖服务。

**操作步骤**

1.  一键拉起所需依赖服务，执行命令后请重点关注终端输出的配置信息：
    > 说明：示例中为启动全部 4 个依赖服务的命令，实际操作时可按需传入对应服务参数，仅启动需要的服务组件。

```
$ ./service.sh mysql milvus plugin sandbox up -n
✅ MYSQL Server started
=== To use it, please set the following value in .env: ===
DB_HOST=localhost
DB_PORT=3041
DB_USER=root
DB_PASSWORD=root
===  ===
✅ Milvus Server started
=== To use it, please set the following value in .env: ===
MILVUS_HOST=localhost
MILVUS_PORT=3044
===  ===
✅ Plugin Server started
=== To use it, please set the following value in .env: ===
VITE_PLUGIN_CONFIG_PATH=/config.json
VITE_PLUGIN_SERVICE_URL=http://localhost:3045
===  ===
✅ Sandbox Server started
=== To use it, please set the following value in .env: ===
CODE_SANDBOX_URL=http://localhost:3046/run
===  ===
```

2. 将终端输出的上述所有环境变量，完整配置到本地部署目录下的 .env 环境变量文件中。
   > 注意：命令输出中默认的 localhost 仅适用于依赖服务与本地部署的 Agent Studio 同机部署的场景；若依赖服务部署在远端服务器，请将所有 localhost 替换为该远端服务器的实际 IP 地址。

## 部署工具获取 IP 失败，怎么办？

**问题现象**
部署脚本默认会自动探测并获取当前运行机器的 IP 地址。但在部分客户环境中，可能出现 IP 获取失败或获取不准确的情况：例如服务器存在多张网卡，部分网卡未接入网络、部分网卡仅用于内网隔离，仅特定网卡的 IP 可被外部网络访问。此时脚本无法自动判断应选用哪一个 IP，需由客户手动指定。

**解决方案**
在部署目录的对应配置文件`deploy/service/.env.custom`中，新增并设置 IP 环境变量，填入当前物理机可被外部访问的实际 IP 地址：

```
IP=<客户物理机的可访问IP地址>
```

## 镜像拉取到一半失败（连接超时）

**问题现象**
执行 `./service.sh up` 启动服务时，出现类似以下报错，提示服务启动失败：

```
✅ up PLUGIN container
[+] Running 7/9
 - js-server-a5jd4 Pulling                                                             21.5s
 ✔ sandbox-gateway-a5jd4 Pulled                                                        18.2s
   ...（省略镜像拉取成功日志）...
 - python-server-a5jd4 Pulling                                                         21.5s
failed to copy: httpReadSeeker: failed open: failed to do request: Get "https://op-svc-swr-b051-10-38-19-62-3az.obs.cn-north-4.myhuaweicloud.com:443/...":
dial tcp 121.36.121.197:443: connectex: A connection attempt failed because the connected party did not properly respond after a period of time, or established connection failed because connected host has failed to respond.
❌ up SANDBOX service failed
```

**问题原因**
该报错的核心原因是 临时网络波动 / 华为云 OBS 镜像仓库连接超时, 服务启动时需要从华为云 OBS（对象存储服务）拉取 容器镜像；网络链路临时不稳定、镜像仓库服务器响应延迟，或短时间内并发请求过高，导致连接超时，镜像拉取失败；该问题属于偶发性网络问题，非服务配置或环境异常导致。

**解决方案**
无需做任何额外操作，重新执行一次即可，临时网络问题大概率会自动恢复。

## 升级过程中，老实例的MySQL 容器远程连接失败（健康状态正常)

**问题现象**

老实例的MySQL 容器状态显示 healthy、日志无报错，但升级容器通过宿主机IP+外部映射端口连接老实例的MySQL容器时提示：

```
** (mydumper:20): CRITICAL **: 06:52:18.012: Error connecting to database: Lost connection to MySQL server at 'reading initial communication packet', system error: 2

```

**问题原因**

这是容器端口映射的底层 iptables 转发规则缓存异常，虽 nc测试该端口，显示端口 open，但 MySQL 协议请求无法穿透到容器内；

**解决方案**

重启老实例系统，「重置网络状态」：重建端口转发规则、刷新网络命名空间、清空 MySQL 隐性连接缓存，可快速恢复。

```
./service.sh down
./service.sh up
```

## 某些环境下低于 0.1.4 版本的部署工具关闭实例时报网络删除错误

**问题现象**
使用低于 0.1.4 版本的部署工具关闭实例时，部分环境会直接报错并退出：

```
error while removing network: network ... has active endpoints
```

**问题原因**
该问题由 Docker Compose 版本差异 导致：

- 旧版本 Compose对网络状态校验极严格，发现网络有活跃端点时，直接抛出 ERROR: error while removing network 并终止命令，返回非 0 退出码。

- 新版本 Compose优化了容错逻辑，遇到网络有活跃容器时，不再直接报错终止，而是仅输出孤儿容器的 warning，跳过网络删除步骤，命令整体仍返回成功）。

  0.1.4 及以上版本的部署工具，新增了 Docker Compose 版本校验机制，可在启动初期自动检测环境依赖，并提前提示用户将 Docker Compose 升级至符合要求的版本。

**解决方案**
请将 Docker 和 Docker Compose 升级至满足[版本要求](#使用说明)的版本，即可避免此类错误。

## 执行部署命令时出现 "Found orphan containers" 警告，是否需要处理？

**问题现象**
部署工具在启动服务的过程，终端输出类似如下警告信息：

```
time="2026-02-13T11:12:41+08:00" level=warning msg="Found orphan containers ([jiuwen-milvus-standalone-6vnaj ...]) for this project..."
```

**问题原因**
本部署工具支持同一目录下多实例并行部署，每个实例会生成独立的容器（命名含唯一实例 ID，如 mysql-6vnaj、milvus-ujb38）。部署工具调用的Docker Compose命令 检测到当前 compose 文件未声明的、同目录下的其他实例容器时，会触发 "孤儿容器" 警告，属于正常现象。

**处理建议**
本部署工具采用实例 ID实现强隔离机制，不同实例的容器、数据卷、网络与配置文件均通过唯一实例 ID 进行维度隔离，彼此独立、互不干扰。同时，工具支持通过与实例 ID 绑定的专属配置文件，精细化控制每个实例的部署、启动、停止与升级流程。因此，Docker Compose 输出的孤儿容器警告仅为常规提示信息，可完全忽略，不会对任何实例的核心生命周期操作造成影响。
