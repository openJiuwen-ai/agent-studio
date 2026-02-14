本指南介绍在 Linux 系统采用本地方式安装 openJiuwen。本地高级安装提供两种方法：

* **方法一：使用一键安装部署脚本**：自动完成大部分安装和配置工作，包括前后端和所有依赖服务，简化安装流程，适合快速部署。
* **方法二：全部手动安装**（不推荐）：需要手动安装和配置所有依赖服务，适合需要灵活调整配置的开发者。

## 一、环境准备

请确保机器满足以下要求：

* 硬件：
  * CPU：最低 2 核，推荐 4 核及以上
  * RAM：最低 4GB，推荐 8GB 及以上

* 操作系统：
  * Ubuntu：最低 Ubuntu 20.04，推荐 Ubuntu 22.04 (Jammy) 及以上
    > **注意**：Ubuntu 官方与主流软件源已停止支持 Ubuntu 20.04 (Focal) 及以下版本系统。

* 软件（安装方法详见下文）	 
  * Git 2.40及以上 
  * Node.js 20.0及以上 
  * npm 10.0及以上 
  * Python 3.11及以上 
  * uv 0.5.0及以上 
  * MySQL 8.0及以上 
  * Milvus 2.6.2及以上

## 二、安装方法

### 方法一：使用一键安装部署脚本

一键安装脚本可以自动完成基础工具检查、代码拉取、环境配置和服务启动等步骤，大幅简化安装流程。

#### 1. 获取安装脚本

* 下载 <a href="https://openjiuwen-ci.obs.cn-north-4.myhuaweicloud.com/agentstudio/setup_scripts/setup_scripts_linux_v2.zip" target="_blank" rel="nofollow noopener noreferrer"> 安装包脚本</a>，安装包脚本包含以下文件：
  * `setup.sh`：主安装脚本，串联整个安装流程
  * `utils.sh`：公共工具
  * `check_curl.sh`：检查 curl 是否安装，未安装则安装 curl
  * `check_git.sh`：检查 Git 是否安装，未安装则安装 Git
  * `check_nodejs.sh`：检查 Node.js 是否安装，未安装则通过 NVM 安装 Node.js
  * `check_python.sh`：检查 Python 是否安装，未安装则安装 Python
  * `check_mysql.sh`：检查 MySQL 是否安装，未安装则安装 MySQL
  * `config_mysql.sh`：配置 MySQL（创建数据库、用户等）
  * `fetch_codes.sh`：克隆 agent-studio 代码仓库（支持指定分支）
  * `user_config.sh`：用户配置文件（可选，包含代理、NVM 镜像、pip 源、npm 源配置）

#### 2. 配置代理、pip 源、NVM 镜像和 npm 源（可选）

如果您的网络环境需要通过代理访问外网，或者需要使用自定义的 pip 源、NVM Node.js 镜像或 npm 源，可以在 `user_config.sh` 文件中进行配置：

* 打开 `user_config.sh` 文件，修改以下变量：

  ```bash
  # 代理配置（可选）
  HTTP_PROXY=""   # HTTP 代理地址，例如 http://127.0.0.1:7890
  HTTPS_PROXY=""  # HTTPS 代理地址，例如 http://127.0.0.1:7890
  SSL_VERIFY=""   # 可选：true/false（对应 git http.sslVerify）

  # pip 源配置（可选）
  PIP_INDEX_URL=""      # pip 源地址，例如 https://pypi.tuna.tsinghua.edu.cn/simple
  PIP_TRUSTED_HOST=""   # 信任的主机地址，例如 pypi.tuna.tsinghua.edu.cn

  # NVM Node.js 下载镜像（可选，安装 Node.js 时使用）
  NVM_NODEJS_ORG_MIRROR=""  # 例如 https://npmmirror.com/mirrors/node

  # npm 源配置（可选）
  NPM_REGISTRY=""       # npm 源地址，例如 https://registry.npmmirror.com
  ```

* 代理配置说明：
  * **不需要代理**：保持变量为空即可（脚本会自动跳过代理配置）
  * **需要代理**：填写完整代理地址，例如 `http://127.0.0.1:7890`
  * **带认证的代理**：支持用户名密码，例如 `http://user:pass@proxy.example.com:8080`
  * **SSL 验证**：`SSL_VERIFY` 设置为 `true` 或 `false`，`true` 表示开启 Git 的 SSL 证书验证，`false` 为不开启。

* pip 源配置说明：
  * **不需要配置 pip 源**：保持 `PIP_INDEX_URL` 和 `PIP_TRUSTED_HOST` 为空即可（脚本会自动跳过 pip 源配置，使用默认源）
  * **需要配置 pip 源**：必须同时设置 `PIP_INDEX_URL` 和 `PIP_TRUSTED_HOST` 两个参数
  * **常用国内镜像源示例**：
    * 清华大学：`https://pypi.tuna.tsinghua.edu.cn/simple`，信任主机：`pypi.tuna.tsinghua.edu.cn`
    * 阿里云：`https://mirrors.aliyun.com/pypi/simple/`，信任主机：`mirrors.aliyun.com`
    * 中科大：`https://pypi.mirrors.ustc.edu.cn/simple/`，信任主机：`pypi.mirrors.ustc.edu.cn`

* NVM Node.js 镜像说明：
  * **不需要配置**：保持 `NVM_NODEJS_ORG_MIRROR` 为空，使用 nvm 默认源（nodejs.org）
  * **需要加速或无法访问默认源**：可配置为 `https://npmmirror.com/mirrors/node` 等镜像，供 check_nodejs.sh 安装 Node.js 时使用。

* npm 源配置说明：
  * **不需要配置 npm 源**：保持 `NPM_REGISTRY` 为空即可（脚本会自动跳过 npm 源配置，使用默认源）
  * **需要配置 npm 源**：设置 `NPM_REGISTRY` 为所需的 npm 源地址
  * **常用国内镜像源示例**：
    * 淘宝镜像：`https://registry.npmmirror.com`
    * 腾讯云：`https://mirrors.cloud.tencent.com/npm/`
    * 华为云：`https://repo.huaweicloud.com/repository/npm/`

#### 3. 运行安装脚本

* 进入脚本目录，赋予执行权限：

  ```bash
  chmod +x *.sh
  ```

* 运行主安装脚本：

  ```bash
  # 默认使用 MySQL 数据库
  ./setup.sh

  # 或指定使用 SQLite 数据库
  ./setup.sh --db_type=sqlite
  ```


* 脚本执行完成后，会输出后端和前端服务的PID、日志文件路径、前端页面访问地址，在浏览器中访问输出的页面访问地址即可进入openJiuwen界面。

 ![image](../images/一键安装运行完成截图linux.png)

#### 4. 脚本常用参数说明

  ```bash
  # 查看前后端服务状态和访问地址
  ./setup.sh --status

  # 启动后端和前端服务
  ./setup.sh --start
  
  # 停止后端和前端服务
  ./setup.sh --stop

  # 重启后端和前端服务
  ./setup.sh --restart

  # 查看脚本支持的所有参数
  ./setup.sh --help
  ```


### 方法二：全部手动安装（不推荐）

> **注意**：此方法需要手动安装所有依赖服务，步骤复杂，不推荐使用。建议优先使用方法一或方法二。

进行正式安装前需先完成依赖的安装，再执行源码获取和安装等后续步骤。

#### 1. 安装依赖（以下以 Ubuntu 22.04 为例）

##### 1.1. 安装 Git

* 运行以下命令安装Git：

  ```bash
  sudo apt update
  sudo apt install git
  ```

##### 1.2. 安装 Node.js 和 npm

* 运行以下命令安装 Node.js 和 npm：

  ```bash
  sudo apt update
  sudo apt install -y nodejs

  # 确认 node 与 npm 版本号
  node -v && npm -v
  ```
  > **注意**：部分 linux 系统软件源 nodejs 与 npm 版本较老，如 node 版本号低于 20.0 或 npm 版本号低于10.0，请参考 <a href="https://nodejs.org/zh-cn/download" target="_blank" rel="nofollow noopener noreferrer"> nodejs 官网</a> 安装新版本。

##### 1.3. 安装 Python 和 uv

* 运行以下命令安装 Python3.11：

  ```bash
  sudo add-apt-repository ppa:deadsnakes/ppa

  sudo apt update
  sudo apt install python3.11 python3-pip
  ```
  > **注意**：Deadsnakes PPA 已停止支持 Ubuntu 20.04 (Focal) 及以下版本系统。如您的系统为上述版本，请参考 <a href="https://www.anaconda.com/docs/getting-started/miniconda/install" target="_blank" rel="nofollow noopener noreferrer"> Miniconda 官方指导</a> 使用 conda 创建 Python 3.11 环境。

* 运行以下命令安装 uv：

  ```bash
  pip3 install uv
  ```

  > **注意**：若安装失败，请参考 <a href="https://uv.doczh.com/getting-started/installation/#_1" target="_blank" rel="nofollow noopener noreferrer"> uv 官方指导</a> 。
  

##### 1.4. 安装 MySQL（可选组件）

* **SQLite vs MySQL**：
  * SQLite 无需额外安装和配置，适合开发和测试环境，但功能受限（如不支持高并发写入、无用户权限管理等）。
  * MySQL 功能更完善，能够满足复杂场景的需求，因此在实际工程和生产环境中更推荐使用。

###### 1.4.1 SQLite

* **说明**：默认使用 SQLite，只需 `.env.example` 保持 `DB_TYPE` 为 `sqlite` 即可直接启动后端服务，无需额外安装或配置。

###### 1.4.2 MySQL

* **说明**：若需使用 MySQL，请将 `.env.example` 中的 `DB_TYPE` 改为 `mysql`，并按照下列步骤完成 MySQL 的安装与配置。

* 运行以下命令安装 MySQL：

  ```bash
  sudo apt update
  sudo apt install mysql-server
  sudo apt install libmysqlclient-dev pkg-config build-essential python3-dev
  ```

* 安装完成后，运行以下命令登录 MySQL：
   
  ```bash
  sudo mysql -u root
  ```

* 在 MySQL 中执行以下命令创建数据库：
  > 说明：`your_user_name`、`your_password` 需自行设置，后续配置 .env 文件将会用到。

  ```sql
  # 新建数据库
  CREATE DATABASE openjiuwen_agent;
  CREATE DATABASE openjiuwen_ops;
  # 新建 MySQL 用户
  CREATE USER 'your_user_name'@'localhost' IDENTIFIED BY 'your_password';
  # 用户授权并刷新
  GRANT ALL PRIVILEGES ON openjiuwen_agent.* TO 'your_user_name'@'localhost';
  GRANT ALL PRIVILEGES ON openjiuwen_ops.* TO 'your_user_name'@'localhost';
  FLUSH PRIVILEGES;
  ```

##### 1.5. Milvus（可选组件）

* **说明**：`.env.example` 默认使用 Chroma，只需保持 `INDEX_MANAGER_TYPE` 为 `chroma` 即可直接启动后端服务，无需额外安装或配置；若需使用 Milvus，请将 `.env.example` 中的 `INDEX_MANAGER_TYPE` 改为 `milvus`，并参考 [如何启用记忆及知识库功能](#linux-memory) 完成 Milvus 的安装配置。

* **Chroma vs Milvus**：
  * Chroma 无需额外安装，配置简单，只需要获取向量模型，适合快速体验，适合开发和测试环境。 向量模型的获取可参考 [如何获取向量模型](#linux-embed-model)。
  * Milvus 功能更完善，能够满足复杂场景的需求，因此在实际工程和生产环境中更推荐使用。

#### 2. openJiuwen 安装

##### 2.1. 获取源码

* 请确认已获取 <a href="https://gitcode.com/org/openJiuwen" target="_blank" rel="nofollow noopener noreferrer"> openJiuwen 代码仓</a> 的访问权限，若无权限请及时申请。

* 在 gitcode 代码仓按照图示步骤 2 获取 Git 的全局配置，输入以下命令配置 Git：

  ```bash
  git config --global user.name your_username
  git config --global user.email your_useremail
  ```

  ![image](../images/gitcode-token.png)

* 按照图示步骤 3 获取个人访问令牌，克隆代码时需要输入 gitcode 账号以及个人访问令牌。

* 执行以下命令克隆源码并进入源码根目录：

  ```bash
  # 安装过程需要多次 git 操作，建议配置凭证存储，避免认证错误。
  git config --global credential.helper store

  git clone https://gitcode.com/openJiuwen/agent-studio.git
  cd agent-studio
  ```

##### 2.2. 生成 AES 密钥（可选）

* 如果不需要对关键字段加密存储，可跳过当前步骤
* 运行以下命令生成密钥：
  ```bash
  cd backend
    
  bash build_AES_master_key.sh
  ```
* 脚本执行完，会将密钥打屏输出，可按需使用，推荐作为环境变量使用并另行保存。
  ```bash
  export SERVER_AES_MASTER_KEY_ENV=your_aes_key
  ```
* 注意，AES密钥需要保持稳定，中途更换密钥会导致已加密数据无法解密。

##### 2.3. 启动 openJiuwen

* 进入源码根目录；

* 复制 *.env* 文件：
  ```bash
  cp .env.example .env
  ```

* 请在 *.env* 文件中根据实际情况修改以下变量的值（勿覆盖其他变量）：

  > **说明**：DB_HOST、DB_PORT 等变量的值可替换为实际数据库信息，DB_USER、DB_PASSWORD 为上文新建的 MySQL 用户与密码。如果密码中包含特殊字符，可参考 [特殊字符转义表](#linux-special-char) 将特殊字符替换为 URL 编码。

  ```env
   # 配置数据库（样例）
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=your_user_name
   DB_PASSWORD=your_password

   # 向量索引类型配置（样例，可选值：chroma、milvus，默认值：chroma）
   INDEX_MANAGER_TYPE=chroma
  
   # 记忆数据存储路径（样例，默认值：memory-data,可根据实际情况修改）
   MEMORY_DATA_PATH=memory-data

   # 配置Milvus（样例，仅当 INDEX_MANAGER_TYPE=milvus 时需要配置）
   MILVUS_HOST=127.0.0.1
   MILVUS_PORT=19530
   MILVUS_COLLECTION_NAME=memory_vector

   # 配置代码沙箱服务（样例，启动代码执行沙箱服务详情请见[问题二：如何启用沙箱功能]）
   CODE_SANDBOX_URL=http://localhost:8188/run

   # 配置插件服务（样例，启动插件服务详情请见[问题三：如何启用插件服务]）
   VITE_PLUGIN_SERVICE_URL=http://localhost:8185
   VITE_PLUGIN_CONFIG_PATH=/config.json
   ```

  变量说明可参考如下表格，如需选择 Milvus 启用记忆功能，请参考 [如何启用记忆及知识库功能](#linux-memory)，如果选择 Chroma 启用记忆功能，只需要获取向量模型，可参考 [如何获取向量模型](#linux-embed-model)。

   | 变量名                                   | 变量说明                              | 配置样例                                                                      |
   |---------------------------------------|-----------------------------------|---------------------------------------------------------------------------|
   | **DB_HOST**                           | 数据库的主机地址                          | `localhost`                                                               |
   | **DB_PORT**                           | 数据库的端口号                           | `3306`                                                                    |
   | **DB_USER**                           | 数据库的用户名                           | `your_user_name`                                                             |
   | **DB_PASSWORD**                       | 数据库的密码                            | `your_password`                                                         |
   | **INDEX_MANAGER_TYPE**        | 向量数据库类型，可选值：chroma、milvus，默认值：chroma | `chroma`                              |
   | **MEMORY_DATA_PATH**          | 记忆数据存储路径,默认值：memory-data    | `memory-data`                         |
   | **MILVUS_HOST**                 | Milvus服务的主机地址                     | `127.0.0.1`                                                                    |
   | **MILVUS_PORT**                 | Milvus服务的端口                       | `19530`                                                                    |
   | **MILVUS_COLLECTION_NAME**                | Milvus服务的数据库名                     | `memory_vector`
   | **CODE_SANDBOX_URL**                 | 代码沙箱服务地址                          | `http://localhost:8188/run`                                                                    |
   | **VITE_PLUGIN_SERVICE_URL**                 | 插件服务地址                            | `http://localhost:8185`                                                                    |
   | **VITE_PLUGIN_CONFIG_PATH**                 | 前端使用的插件服务配置文件                     | `/config.json`                                                                    |

* 在源码根目录下，运行以下命令启动后端服务，并耐心等待：
   
  ```bash
  cd backend
  uv venv
  uv sync
  ```
* 执行数据库版本标识命令，确认当前数据库版本：
  ```bash
  # Agent数据库
  alembic -n alembic_mysql_agent stamp head
  alembic -n alembic_mysql_ops stamp head

  # SQLite数据库
  alembic -n alembic_sqlite_agent stamp head
  alembic -n alembic_sqlite_ops stamp head
  ```

  > 详细说明：以上命令用于标识当前数据库已是最新版本，方便后续进行数据库操作。需要分别对agent和ops数据库执行。如使用MySQL需执行alembic -n alembic_mysql_agent stamp head和alembic -n alembic_mysql_ops stamp head，关于alembic的使用方法参考[DATABASE_MIGRATION_DEVELOPMENT_GUIDE.md](../../../../backend/DATABASE_MIGRATION_DEVELOPMENT_GUIDE.md)

  > **注意**：如果持续卡死超过 20 分钟，请按下 “Ctrl + C”，尝试修改本目录下 “pyproject.toml” 文件中 [[tool.uv.index]] 的 url 值，切换成其他可用源后，再重新执行 “uv sync”。

  > **注意**：若执行 `uv sync` 失败，可尝试：`uv sync --native-tls`  强制使用系统原生TLS库（解决HTTPS下载兼容问题）

* 创建日志目录并启动后端服务
  ```bash
  mkdir -p logs/run
  source .venv/bin/activate
  python main.py
  ```

  启动成功后，会输出 "Application startup complete"。

  > **说明**：若需代码执行沙箱服务，可参考 [如何启用沙箱功能](#linux-sandbox) 完成沙箱服务启动和配置。若需插件服务，可参考 [如何启用插件服务](#linux-plugin) 完成插件服务启动和配置。

* 新打开一个窗口，在源码根目录下，运行以下命令安装依赖：

  ```bash
  cd frontend
  npm install
  ```
  > **注意**：图示漏洞为 npm 官方已知漏洞，不影响后续运行。

  ![image](../images/npm-error.png)

* 运行以下命令启动前端服务：

  ```
  npm run dev
  ```

* 启动成功后会输出:

  Local：*本地访问地址*

  Network：*网络访问地址*

##### 2.4. 访问系统

  * 若在本地查看，ctrl+左键单击 *本地访问地址* 可在本地浏览器查看到 openJiuwen 的界面；或者复制上述 *本地访问地址* 到浏览器地址栏，按下“回车键”将看到 openJiuwen 的界面。
  
  * 若在外部机器查看，复制上述 *网络访问地址* 到浏览器地址栏，按下“回车键”将看到 openJiuwen 的界面。

## 三、常见问题（FAQ）

<a id="linux-memory"></a>
### 问题一：如何启用记忆及知识库功能

记忆功能的体验与大模型的参数规模相关。

记忆及知识库功能支持 Chroma 和 Milvus 两种向量数据库，如果选择 Milvus，具体安装步骤可参考下文。

#### 1. 启动 Milvus

* 启动 Milvus 推荐使用 Docker 方式，请参照 <a href="https://docs.docker.com/engine/install/" target="_blank" rel="nofollow noopener noreferrer">Docker 官方安装指南</a> 以及 <a href="https://docs.docker.com/compose/install/" target="_blank" rel="nofollow noopener noreferrer">Docker Compose 官方安装指南</a> 完成配置。
* 安装后请执行命令启动 Docker：`sudo systemctl start docker`。

* 执行以下命令，将在当前目录下保存 “standalone_embed.sh” 脚本

  ```
  curl -sfL https://raw.githubusercontent.com/milvus-io/milvus/master/scripts/standalone_embed.sh -o standalone_embed.sh
  ```
* 执行以下命令拉取镜像：

  ```bash
  # x86 架构
  docker pull swr.cn-north-4.myhuaweicloud.com/openjiuwen/milvusdb/milvus-amd64:v2.6.2
  ```

  ```bash
  # arm 架构
  docker pull swr.cn-north-4.myhuaweicloud.com/openjiuwen/milvusdb/milvus-arm64:v2.6.2
  ```

* 将 “standalone_embed.sh” 文件内的 milvus 官方镜像名（比如： `milvusdb/milvus:v2.6.7`） 内容修改为 对应的镜像名（X86机器镜像名：`swr.cn-north-4.myhuaweicloud.com/openjiuwen/milvusdb/milvus-amd64:v2.6.2`）。
  
* 修改完成后，执行以下命令运行，将 Milvus 作为 Docker 容器启动：

  ```
  bash standalone_embed.sh start
  ```

* 启动后，输入 `docker ps -a` 命令可查看到名为 Milvus-standalone 的 docker 容器在 `19530` 端口启动。

  > **说明**：若在部署过程中出现问题可参考 <a href="https://milvus.io/docs/zh/install_standalone-docker.md" target="_blank" rel="nofollow noopener noreferrer"> Milvus官方指导文档</a>

* 若要停止 Milvus，请执行以下命令

  ```
  bash standalone_embed.sh stop
  ```

* 若启动之后使用记忆或知识库时出现如下报错信息
    ```text
    ""Milvus 连接失败: <MilvusException: (code=2, message=Fail connecting to server on milvus-standalone:19530, illegal connection params or server unavailable)>"
    ```
    需修改.env中的MILVUS_HOST配置，与启动Milvus服务的IP保持一致

<a id="linux-embed-model"></a>
#### 2. 获取向量模型

记忆及知识库功能的运行依赖向量模型，以下流程以华为云为例，介绍向量模型的获取步骤。

* 点击<a href="https://console.huaweicloud.com/modelarts/?locale=zh-cn&region=cn-southwest-2#/model-studio/square" target="_blank" rel="nofollow noopener noreferrer"> 链接</a> 进入模型广场。 

* 体验记忆及知识库功能请点击 “向量模型”，可根据需要自行选择向量模型，以下内容以 BGE-M3 为例。

  ![找到embedd模型](../images/find_embed.png)

* 找到合适的向量模型后点击推理调用，进入模型信息获取界面。

  ![获取api_base和model_name](../images/embed_api_base_and_model_name.png)

* 记录API地址、model参数。

* 点击 "API Key 管理"，按照官方界面引导获取 API Key。

<a id="linux-sandbox"></a>
### 问题二：如何启用沙箱功能

若要配置代码插件或在工作流中使用代码节点，需开启沙箱服务，需要进行如下操作：

1. 参考 `sandbox_server/python_server/.env.example` 文件，在 `sandbox_server/python_server` 目录下创建 `.env` 文件，示例如下：

   ```env
   HOST=0.0.0.0
   PORT=5001
   ```

   然后启动沙箱 Python 服务，即运行 `sandbox_server/python_server/openjiuwen_sandbox_pyserver/kernel.py` 脚本，其中 `HOST` 和 `PORT` 是沙箱 Python 服务运行的 IP 和端口。

2. 启动沙箱 JS 服务，运行 `sandbox_server/js_server/kernel.js` 脚本，JS 服务的 IP 和端口参考如下代码：

   ```javascript
   const PORT = process.env.PORT || 5002;
   server.listen(PORT, "0.0.0.0", () => {
     console.log(`✅ JS sandbox listening on http://0.0.0.0:${PORT}`);
   });
   ```

3. 参考 `sandbox_server/gateway/.env.example` 文件，在 `sandbox_server/gateway` 目录下创建 `.env` 文件，示例如下：

   ```env
   ENABLE_LINUX_SANDBOX=0
   HOST=0.0.0.0
   PORT=8188
   PYTHON_SANDBOX_URL=http://localhost:5001/run
   JS_SANDBOX_URL=http://localhost:5002/run
   ```

   其中 `ENABLE_LINUX_SANDBOX` 表示是否启动 bwrap 沙箱，`PYTHON_SANDBOX_URL` 和 `JS_SANDBOX_URL` 为前面两步启动的 Python 和 JS 服务 URL。

   如果需要启动 bwrap 沙箱，请将 `ENABLE_LINUX_SANDBOX` 设置为1，并在 `sandbox_server/gateway/openjiuwen_sandbox_gateway/conf/sandbox_config.yaml` 中按需修改安全配置。目前支持 `seccomp` 、`namespace` 、`mount` 文件系统等配置参数。请确保 Python 解释器和 Js 解释器以及相关依赖都包的路径都在 `mount` 配置中，以及 `PATH` 环境变量中包含了 Python 解释器和 Js 解释器所在路径。示例如下：

   ```
   seccomp: # whitelist mode
     allow:
       x86_64: ["epoll_wait", "getcwd", "wait4", "pread64", "set_tid_address", "prlimit64", "capget", "pipe2", "eventfd2", "pkey_alloc", "madvise", "sysinfo", "readlink", "geteuid", "getegid", "statx", "access", "clone", "arch_prctl", "clone3", "execve", "open", "lstat", "stat", "newfstatat", "lseek", "getdents64", "write", "close", "openat", "read", "futex", "mmap", "brk", "mprotect", "munmap", "rt_sigreturn", "mremap", "getgid", "getuid", "getpid", "getppid", "gettid", "exit", "exit_group", "rt_sigaction", "sched_yield", "set_robust_list", "get_robust_list", "rseq", "clock_gettime", "gettimeofday", "nanosleep", "epoll_create1", "epoll_ctl", "clock_nanosleep", "pselect6", "time", "rt_sigprocmask", "sigaltstack", "getrandom", "mkdirat", "mkdir", "socket", "connect", "bind", "listen", "accept", "sendto", "recvfrom", "getsockname", "recvmsg", "getpeername", "ppoll", "uname", "sendmsg", "sendmmsg", "fstat", "fcntl", "fstatfs", "poll", "epoll_pwait", 'ioctl']
       aarch64: ["statx", "getcwd", "readlinkat", "madvise", "sysinfo", "clone", "eventfd2", "pipe2", "fcntl", "prlimit64", "set_tid_address", "faccessat", "execve", "write", "close", "openat", "read", "lseek", "getdents64", "futex", "mmap", "brk", "mprotect", "munmap", "rt_sigreturn", "rt_sigprocmask", "sigaltstack", "mremap", "getuid", "getgid", "geteuid", "getegid", "getpid", "getppid", "gettid", "exit", "exit_group", "rt_sigaction", "sched_yield", "get_robust_list", "set_robust_list", "rseq", "epoll_create1", "clock_gettime", "gettimeofday", "nanosleep", "epoll_ctl", "clock_nanosleep", "pselect6", "timerfd_create", "timerfd_settime", "timerfd_gettime", "getrandom", "mkdirat", "socket", "connect", "bind", "listen", "accept", "sendto", "recvfrom", "recvmsg", "getsockname", "getpeername", "ppoll", "uname", "sendmmsg", "newfstatat", "fstat", "fstatfs", "epoll_pwait", "ioctl"]

   namespace:
     user: False
     net: True
     pid: True
     ipc: True
     uts: True
     cgroup: True

   mount:
     [
       {src: '/lib', dst: '/lib', mode: 'read'},
       {src: '/lib64', dst: '/lib64', mode: 'read'},
       {src: '/usr/bin', dst: '/usr/bin', mode: 'read'},
       {src: '/usr/lib', dst: '/usr/lib', mode: 'read'},
       {src: '/usr/lib64', dst: '/usr/lib64', mode: 'read'},
       {src: '/usr/share/nodejs', dst: '/usr/share/nodejs', mode: 'read'},
     ]

   sandbox:
     type: bubblewrap
     path: bwrap

   # Please ensure that both the Python and JavaScript interpreters
   # are already in the mount directory, and either provide their full
   # paths or add those paths to the PATH environment variable.
   interpreter:
     python_path: python3
     javascript_path: node

   environment:
     PATH: /bin:/usr/bin
   ```

   最后启动沙箱网关服务，即运行 `sandbox_server/gateway/openjiuwen_sandbox_gateway/server.py` 脚本。

4. 启动沙箱服务后请在`.env`文件中配置沙箱服务的路径，例如：`CODE_SANDBOX_URL=http://localhost:8188/run`

<a id="linux-plugin"></a>
### 问题三：如何启用插件服务

若要配置插件，需开启插件服务，需要进行如下操作：

1. 参考 `plugin_server/openjiuwen_plugin_server` 文件，创建所需的插件，然后启动插件服务，即运行 `plugin_server/openjiuwen_plugin_server/run_restful.py` 脚本，其中 `uvicorn.run(app, host="0.0.0.0", port=8185)` 定义了插件服务的 IP 和端口。

2. 启动插件服务后请在`.env`文件中配置插件服务的路径，例如：`VITE_PLUGIN_SERVICE_URL=http://localhost:8185`

<a id="linux-special-char"></a>
### 问题四：特殊字符转义表

| 字符   | URL编码 | 字符   | URL编码 | 字符   | URL编码 | 字符   | URL编码 | 字符   | URL编码 |
|--------|---------|--------|---------|--------|---------|--------|---------|--------|---------|
| 空格 | %20    | "      | %22     | #      | %23     | %      | %25     | &   | %26     |
| (      | %28    | )      | %29     | +      | %2B     | ,      | %2C     | /      | %2F     |
| :      | %3A    | ;      | %3B     | <   | %3C     | =      | %3D     | >   | %3E     |
| ?      | %3F    | @      | %40     | \      | %5C     | \|     | %7C     | -      | -       |

### 问题五：本地安装为何默认使用http协议而非https协议

在本地安装方式下，系统默认通过HTTP协议进行通信。这一设计主要考虑到本地环境通常用于开发与测试，避免强制要求证书配置，从而降低初始使用门槛。
相比之下，Docker安装方式已预置了HTTPS支持，用户无需额外配置即可直接使用安全通信。
如需在本地环境启用HTTPS，开发者需根据实际部署需求自行完成证书生成与配置。