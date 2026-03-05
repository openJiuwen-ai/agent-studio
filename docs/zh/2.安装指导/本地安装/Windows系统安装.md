本指南介绍在 Windows 系统采用本地方式安装 openJiuwen。本地高级安装提供两种方法：

* **方法一：使用一键安装部署脚本**：自动完成大部分安装和配置工作，简化安装流程，适合快速部署。
* **方法二：手动安装全部依赖**：需要手动安装和配置所有依赖服务，适合需要灵活调整配置的开发者。

## 一、环境准备

请确保机器满足以下要求：

* 硬件：
  * CPU：最低 2 核，推荐 4 核及以上
  * RAM：最低 4GB，推荐 8GB 及以上

* 操作系统：Windows10及以上

* 软件（安装方法详见下文）
  * Git 2.40及以上
  * Node.js 20.0及以上
  * npm 9.0及以上
  * Python 3.11.4及以上
  * uv 0.5.0及以上
  * MySQL 8.0及以上
  * Milvus 2.6.2及以上
  * PowerShell 5.1及以上（可运行 `$PSVersionTable.PSVersion` 查看）

## 二、安装方法

### 方法一：使用一键安装部署脚本

一键安装脚本可以自动完成基础工具检查、代码拉取、环境配置和服务启动等步骤，大幅简化安装流程。

#### 1. 获取安装脚本

* 下载 <a href="https://openjiuwen-ci.obs.cn-north-4.myhuaweicloud.com/agentstudio/setup_scripts/setup_scripts_windows_v2.zip" target="_blank" rel="nofollow noopener noreferrer"> 安装包脚本</a>，安装包脚本包含以下文件：
  * `setup.ps1`：主安装脚本，串联整个安装流程
  * `utils.ps1`：公共工具
  * `check_git.ps1`：检查 Git 是否安装，未安装则安装 Git
  * `check_nodejs.ps1`：检查 Node.js 是否安装，未安装则安装 Node.js
  * `check_python.ps1`：检查 Python 是否安装，未安装则安装 Python
  * `check_mysql.ps1`：检查 MySQL 是否安装，未安装则安装 MySQL
  * `config_mysql.ps1`：配置 MySQL（创建数据库、用户等）
  * `fetch_codes.ps1`：克隆 agent-studio 代码仓库（支持指定分支）
  * `user_config.ps1`：用户配置文件（可选，包含代理、pip 源、npm 源配置）

#### 2. 配置代理、pip源和npm源（可选）

如果您的网络环境需要通过代理访问外网，或者需要使用自定义的pip源或npm源，可以在 `user_config.ps1` 文件中进行配置：

* 打开 `user_config.ps1` 文件，修改以下变量：

  ```powershell
  # 用户填写的代理配置
  $HTTP_PROXY=""  # HTTP 代理地址，例如 http://127.0.0.1:7890
  $HTTPS_PROXY=""  # HTTPS 代理地址，例如 http://127.0.0.1:7890
  $SSL_VERIFY=""  # 可选：true/false（对应 git http.sslVerify）

  # pip 源配置（可选）
  $PIP_INDEX_URL=""      # pip 源地址，例如 https://pypi.tuna.tsinghua.edu.cn/simple
  $PIP_TRUSTED_HOST=""   # 信任的主机地址，例如 pypi.tuna.tsinghua.edu.cn

  # npm 源配置（可选）
  $NPM_REGISTRY=""       # npm 源地址，例如 https://registry.npmmirror.com
  ```

* 代理配置说明：
  * **不需要代理**：保持变量为空即可（脚本会自动跳过代理配置）
  * **需要代理**：填写完整代理地址，例如 `http://127.0.0.1:7890`
  * **带认证的代理**：支持用户名密码，例如 `http://user:pass@proxy.example.com:8080`
  * **SSL 验证**：`$SSL_VERIFY` 设置为 `true` 或 `false`，`true`表示开启Git的SSL证书验证，`false`为不开启。

* pip 源配置说明：
  * **不需要配置 pip 源**：保持 `$PIP_INDEX_URL` 和 `$PIP_TRUSTED_HOST` 为空即可（脚本会自动跳过 pip 源配置，使用默认源）
  * **需要配置 pip 源**：必须同时设置 `$PIP_INDEX_URL` 和 `$PIP_TRUSTED_HOST` 两个参数
  * **常用国内镜像源示例**：
    * 清华大学：`https://pypi.tuna.tsinghua.edu.cn/simple`，信任主机：`pypi.tuna.tsinghua.edu.cn`
    * 阿里云：`https://mirrors.aliyun.com/pypi/simple/`，信任主机：`mirrors.aliyun.com`
    * 中科大：`https://pypi.mirrors.ustc.edu.cn/simple/`，信任主机：`pypi.mirrors.ustc.edu.cn`

* npm 源配置说明：
  * **不需要配置 npm 源**：保持 `$NPM_REGISTRY` 为空即可（脚本会自动跳过 npm 源配置，使用默认源）
  * **需要配置 npm 源**：设置 `$NPM_REGISTRY` 为所需的 npm 源地址
  * **常用国内镜像源示例**：
    * 淘宝镜像：`https://registry.npmmirror.com`
    * 腾讯云：`https://mirrors.cloud.tencent.com/npm/`
    * 华为云：`https://repo.huaweicloud.com/repository/npm/`

#### 3. 运行安装脚本
* 以管理员身份运行 PowerShell，设置执行策略：

  ```powershell
  Set-ExecutionPolicy Unrestricted -Scope CurrentUser
  ```

* 进入脚本目录，运行主安装脚本：

  ```powershell
  # 默认使用 MySQL 数据库
  .\setup.ps1

  # 或指定使用 SQLite 数据库
  .\setup.ps1 -DbType sqlite
  ```


* 脚本执行完成后，会输出后端和前端服务的PID、日志文件路径、前端页面访问地址，在浏览器中访问输出的页面访问地址即可进入openJiuwen界面。

![image](../images/一键安装运行完成截图win.png)

#### 4. 脚本常用参数说明

  ```powershell
  # 查看前后端服务状态和访问地址
  .\setup.ps1 -Status
  
  # 停止后端和前端服务
  .\setup.ps1 -Stop

  # 启动后端和前端服务
  .\setup.ps1 -Start

  # 重启后端和前端服务
  .\setup.ps1 -Restart

  # 查看脚本支持的所有参数
  .\setup.ps1 -Help
  ```

### 方法二：手动安装全部依赖

进行正式安装前需先完成依赖的安装，再执行源码获取和安装等后续步骤。

#### 1. 安装依赖

进行正式安装前需先完成依赖的安装，再执行源码获取和安装等后续步骤。

##### 1.1. 安装 Git

* 下载 <a href="https://mirrors.huaweicloud.com/git-for-windows/v2.51.0.windows.1/Git-2.51.0-64-bit.exe" target="_blank" rel="nofollow noopener noreferrer"> Git</a> 安装包，若下载耗时较长，请切换网络后重试。

* 安装完成后，打开 “PowerShell”，输入：`git --version`，若安装成功会输出 git 版本号。

##### 1.2. 安装 Node.js 和 npm

* 下载 <a href="https://nodejs.org/dist/v22.21.1/node-v22.21.1-x64.msi" target="_blank" rel="nofollow noopener noreferrer"> Node.js</a> 安装包，按照提示完成安装。若下载耗时较长，请切换网络后重试。

* 安装完成后，打开 “PowerShell”，分别输入：`node -v` 与 `npm -v`，若安装成功会输出 node 与 npm 版本号。

##### 1.3. 安装 Python 和 uv

* 下载 <a href="https://www.python.org/ftp/python/3.11.4/python-3.11.4-amd64.exe" target="_blank" rel="nofollow noopener noreferrer"> Python</a> 安装包，按照提示完成安装（建议勾选 **Add Python to PATH**）。若下载耗时较长，请切换网络后重试。

* 安装完成后，打开 “PowerShell”，输入：`python --version`，若安装成功会输出 python 版本号。

* 打开 “PowerShell”，输入：`pip install uv` 安装 uv。

* 安装完成后，输入：`uv --version`，若安装成功会输出 uv 版本号。

##### 1.4. 安装 MySQL（可选组件）

* **SQLite vs MySQL**：
  * SQLite 无需额外安装和配置，适合开发和测试环境，但功能受限（如不支持高并发写入、无用户权限管理等）。
  * MySQL 功能更完善，能够满足复杂场景的需求，因此在实际工程和生产环境中更推荐使用。

###### 1.4.1 SQLite

* **说明**：默认使用 SQLite，只需 `.env.example` 保持 `DB_TYPE` 为 `sqlite` 即可直接启动后端服务，无需额外安装或配置。

###### 1.4.2 MySQL

* **说明**：若需使用 MySQL，请将 `.env.example` 中的 `DB_TYPE` 改为 `mysql`，并按照下列步骤完成 MySQL 的安装与配置。

* 下载 <a href="https://dev.mysql.com/get/Downloads/MySQL-8.4/mysql-8.4.7-winx64.msi" target="_blank" rel="nofollow noopener noreferrer"> MySQL 8.4</a> 安装包。

* 双击下载完成的安装包，跟随安装向导完成安装流程；建议选择 Typical 模式。

  > **注意**：在安装 MySQL 时如遇到 “This application requires Visual Studio 2019 x64 Redistributable”，请下载 Microsoft Visual C++ 官网 <a href="https://aka.ms/vc14/vc_redist.x64.exe" target="_blank" rel="nofollow noopener noreferrer">最新受支持的 Visual C++ x64 版本安装包</a>。

* 安装完成后，配置 MySQL 的 root 密码，请记住该密码。

* 按下 `Win+R` → 输入以下命令，打开「环境变量」窗口：

  ```
  rundll32.exe sysdm.cpl,EditEnvironmentVariables
  ```

* 将 MySQL 的 bin 目录添加至系统环境变量（MySQL 的默认 bin 路径：`C:\Program Files\MySQL\MySQL Server 8.4\bin`）

* 安装完成后，打开 “PowerShell”，登录 MySQL（输入安装时设置的 root 密码）：
   
  ```bash
  mysql -u root -p
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
* **说明**：`.env.example` 默认使用 Chroma，只需保持 `INDEX_MANAGER_TYPE` 为 `chroma` 即可直接启动后端服务，无需额外安装或配置；若需使用 Milvus，请将 `.env.example` 中的 `INDEX_MANAGER_TYPE` 改为 `milvus`，并参考 [如何启用记忆及知识库功能](#windows-memory) 完成 Milvus 的安装配置。

* **Chroma vs Milvus**：
  * Chroma 无需额外安装，配置简单，只需要获取向量模型，适合快速体验，适合开发和测试环境。 向量模型的获取可参考 [如何获取向量模型](#windows-embed-model)。
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

* 新建 openJiuwen 目录，在 openJiuwen 目录打开 “PowerShell”，执行以下命令克隆源码并进入源码根目录：

  ```bash
  # 安装过程需要多次 git 操作，建议配置凭证存储，避免认证错误。
  git config --global credential.helper store

  git clone https://gitcode.com/openJiuwen/agent-studio.git
  cd agent-studio
  ```

##### 2.2. 生成 AES 密钥（可选）

* 如果不需要对关键字段加密存储，可跳过当前步骤
* 在源码根目录打开 “Git Bash”，运行以下命令生成密钥：

  ```bash
  cd scripts
  bash build_AES_master_key.sh
  ```

* 脚本执行完，会将密钥打屏输出，可按需使用，推荐作为环境变量使用并另行保存。

  ```bash
  # 如果你的安装部署在git bash中执行
  export SERVER_AES_MASTER_KEY_ENV=your_aes_key
  
  # 如果你的安装部署在power shell中执行
  # 方法1：打开power shell设置临时环境变量
  $env:SERVER_AES_MASTER_KEY_ENV="your_aes_key"
  # 方法2：添加到 Windows 系统环境变量
  """
    1、按 Win + R，输入 sysdm.cpl
    2、点击‘高级’，然后点击‘环境变量’
    3、在‘系统变量’或‘用户变量’中添加：
      变量名：SERVER_AES_MASTER_KEY_ENV
      变量值：your_aes_key
  """
  ```

* 注意，AES密钥需要保持稳定，中途更换密钥会导致已加密数据无法解密。

##### 2.3. 启动 openJiuwen

* 在源码根目录打开 “PowerShell”；

* 复制 *.env* 文件：

  ```bash
  copy .env.example .env
  ```

* 使用文本编辑器打开 *.env* 文件，请根据实际情况修改文件中以下变量的值（勿覆盖其他变量）：

  > **说明**：DB_HOST、DB_PORT 等变量的值可替换为实际数据库信息，DB_USER、DB_PASSWORD 为上文新建的 MySQL 用户与密码。如果密码中包含特殊字符，可参考 [特殊字符转义表](#windows-special-char) 将特殊字符替换为 URL 编码。

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

   # 配置Milvus（样例）
   MILVUS_HOST=127.0.0.1
   MILVUS_PORT=19530
   MILVUS_COLLECTION_NAME=memory_vector

   # 配置代码沙箱服务（样例，启动代码执行沙箱服务详情请见[问题二：如何启用沙箱功能]）
   CODE_SANDBOX_URL=http://localhost:8188/run

   # 配置插件服务（样例，启动插件服务详情请见[问题三：如何启用插件服务]）
   VITE_PLUGIN_SERVICE_URL=http://localhost:8185
   VITE_PLUGIN_CONFIG_PATH=/config.json
   ```

  变量说明可参考如下表格，如需选择 Milvus 启用记忆功能，请参考 [如何启用记忆及知识库功能](#windows-memory)，如果选择 Chroma 启用记忆功能，只需要获取向量模型，可参考 [如何获取向量模型](#windows-embed-model)。
 
   | 变量名                                   | 变量说明                                                               | 配置样例                                                                      |
   |---------------------------------------|--------------------------------------------------------------------|---------------------------------------------------------------------------|
   | **DB_HOST**                           | 数据库的主机地址                                                           | `localhost`                                                               |
   | **DB_PORT**                           | 数据库的端口号                                                            | `3306`                                                                    |
   | **DB_USER**                           | 数据库的用户名                                                            | `your_user_name`                                                             |
   | **DB_PASSWORD**                       | 数据库的密码                                                             | `your_password`                                                         |
   | **INDEX_MANAGER_TYPE**        | 向量数据库类型，可选值：chroma、milvus，默认值：chroma | `chroma`                              |
   | **MEMORY_DATA_PATH**          | 记忆数据存储路径,默认值：memory-data             | `memory-data`                         |
   | **MILVUS_HOST**                 | Milvus服务的主机地址                                                | `127.0.0.1`                                                                    |
   | **MILVUS_PORT**                 | Milvus服务的端口                                                | `19530`                                                                    |
   | **MILVUS_COLLECTION_NAME**                | Milvus服务的数据库名                                                | `memory_vector`
   | **CODE_SANDBOX_URL**                 | 代码沙箱服务地址                          | `http://localhost:8188/run`                                                                    |
   | **VITE_PLUGIN_SERVICE_URL**                 | 插件服务地址                            | `http://localhost:8185`                                                                    |
   | **VITE_PLUGIN_CONFIG_PATH**                 | 前端使用的插件服务配置文件                     | `/config.json`                                                                    |

* 在源码根目录下打开 “PowerShell”，运行以下命令启动后端服务，并耐心等待：
   
  ```bash
  cd backend
  uv venv
  uv sync
  ```
* 执行数据库版本标识命令，方便后续数据库操作：
  ```bash
  # Agent数据库
  alembic -n alembic_mysql_agent stamp head
  alembic -n alembic_mysql_ops stamp head

  # SQLite数据库
  alembic -n alembic_sqlite_agent stamp head
  alembic -n alembic_sqlite_ops stamp head
  ```

  > 说明：以上命令用于标识当前数据库已是最新版本，方便后续进行数据库操作。需要分别对agent和ops数据库执行。如使用MySQL需执行alembic -n alembic_mysql_agent stamp head和alembic -n alembic_mysql_ops stamp head，关于alembic的使用方法参考[DATABASE_MIGRATION_DEVELOPMENT_GUIDE.md](../../../../backend/DATABASE_MIGRATION_DEVELOPMENT_GUIDE.md)

  > **注意**：如果持续卡死超过 20 分钟，请按下 “Ctrl + C”，尝试修改本目录下 “pyproject.toml” 文件中 [[tool.uv.index]] 的 url 值，切换成其他可用源后，再重新执行 “uv sync”。

  > **注意**：若执行 `uv sync` 失败，可尝试：`uv sync --native-tls`  强制使用系统原生TLS库（解决HTTPS下载兼容问题）
* 创建日志目录并启动后端服务
  ```bash
  mkdir logs
  mkdir logs\run

  # 进入虚拟环境，如在 “命令提示符” 中请执行: .venv\Scripts\activate
  .\.venv\Scripts\Activate.ps1

  # 启动
  python main.py
  ```

  启动成功后，会输出 "Application startup complete"。

  > **说明**：若需代码执行沙箱服务，可参考 [如何启用沙箱功能](#windows-sandbox) 完成沙箱服务启动和配置。若需插件服务，可参考 [如何启用插件服务](#windows-plugin) 完成插件服务启动和配置。

* 在源码根目录下再打开一个 "PowerShell"，运行以下命令安装依赖：

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

* 启动成功后会输出 Local access：*访问地址*。

##### 2.4. 访问系统

复制上述 *访问地址* 到浏览器地址栏，按下 “回车键” 将看到 openJiuwen 的界面。

## 三、常见问题（FAQ）

<a id="windows-memory"></a>
### 问题一：如何启用记忆及知识库功能

记忆功能的体验与大模型的参数规模相关。

记忆及知识库功能支持 Chroma 和 Milvus 两种向量数据库，如果选择 Milvus，Windows 系统推荐使用 Docker 安装，具体安装步骤可参考下文。

#### 1. 安装Docker Desktop
Windows 上运行 Docker Desktop 推荐使用 WSL 2（Windows Subsystem for Linux 2） 作为虚拟化后端，相比 LinuxKit 兼容性更好、资源占用更低，且能避免已知的僵尸容器 Bug。

**1.1 启用 WSL 2**

对于符合条件的 Windows 系统（Windows 10 版本 2004 及更高版本<内部版本 19041 及更高版本>或 Windows 11），仅运行 `wsl --install`就能一键配置、下载并安装默认的 Linux 发行版。

* 按下 Windows + S，输入 PowerShell 进行搜索。

* 在搜索结果中，右键点击 Windows PowerShell，选择 以管理员身份运行。

* 在 PowerShell 执行如下命令，然后重新启动计算机。

  ```
  wsl --install
  ```

而旧版本 Windows 不支持这个一键命令的完整自动化功能，可能需要补充操作，具体请参考<a href="https://learn.microsoft.com/zh-cn/windows/wsl/install" target="_blank" rel="nofollow noopener noreferrer"> 如何使用 WSL 在 Windows 上安装 Linux</a>

**1.2 安装 Docker Desktop**

* 下载：前往 <a href="https://www.docker.com/products/docker-desktop/" target="_blank" rel="nofollow noopener noreferrer"> Docker 官网</a> 下载 Windows 版本安装包（X86 机器请选择 AMD64 版本）；
 * 运行安装包：​**仅勾选​「Use WSL 2 instead of Hyper-V」、​「Add shortcut to desktop」选项**，点击​「OK」开始安装；


* 安装完成后，请重启电脑；
* 重启后，打开 Docker Desktop，等待加载完成（首次启动可能需要 5 ~ 10 分钟）；
* Docker Desktop 启动后，若临时试用，可点击欢迎界面的 `Continue without signing in` 直接进入；长期使用请参考 <a href="https://docs.docker.com/desktop/setup/sign-in" target="_blank" rel="nofollow noopener noreferrer"> 官方指导</a>。

* 至此 Docker Desktop 安装完成。

> **说明**：若安装过程中出现报错，请参考 <a href="https://docs.docker.com/desktop/setup/install/windows-install/" target="_blank" rel="nofollow noopener noreferrer"> Docker Desktop 官方安装指导</a>。

#### 2. 启动 Milvus

* 新建 Milvus 本地安装目录（建议存放至 D 盘，示例路径：*D:\Milvus*）；

 * 打开 Docker Desktop，单击右上方 ⚙ 进入设置界面；
 	  	 
 	 * 单击左侧竖列导航栏​「Resources」，进入 Resources 配置界面；
 	  	 
 	 * 单击​「File sharing」，并在输入框中填写 *Milvus 的安装目录*（例如：*D:\Milvus*），最后单击右侧 ➕ 进行添加；


* 点击 “Apply & restart” 重启 Docker Desktop。



* 以管理员身份打开 PowerShell，先切换至 Milvus 本地安装目录，再执行以下命令保存 “standalone.bat” 脚本：

  ```bash
  cd D:\Milvus # “D:\Milvus” 是 Milvus 本地安装目录

  Invoke-WebRequest https://raw.githubusercontent.com/milvus-io/milvus/refs/heads/master/scripts/standalone_embed.bat -OutFile standalone.bat
  ```

* 在 “PowerShell” 执行以下命令拉取镜像：

  ```bash
  # x86 架构
  docker pull swr.cn-north-4.myhuaweicloud.com/openjiuwen/milvusdb/milvus-amd64:v2.6.2
  ```

  ```bash
  # arm 架构
  docker pull swr.cn-north-4.myhuaweicloud.com/openjiuwen/milvusdb/milvus-arm64:v2.6.2
  ```

* 将 “standalone.bat” 文件内的 milvus 官方镜像名（比如： `milvusdb/milvus:v2.6.7`） 内容修改为 对应的镜像名（X86机器镜像名：`swr.cn-north-4.myhuaweicloud.com/openjiuwen/milvusdb/milvus-amd64:v2.6.2`）。
  
* 修改完成后，在 “PowerShell” 执行以下命令运行 standalone.bat，将 Milvus 作为 Docker 容器启动：

  ```
  ./standalone.bat start
  ```

* 启动后，输入 `docker ps -a` 命令可查看到名为 Milvus-standalone 的 docker 容器在 `19530` 端口启动。

  > **说明**：若在部署过程中出现问题可参考 <a href="https://milvus.io/docs/zh/install_standalone-windows.md" target="_blank" rel="nofollow noopener noreferrer"> Milvus官方指导文档</a>

* 若要停止 Milvus，请执行以下命令

  ```
  ./standalone.bat stop
  ```

* 若启动之后使用记忆或知识库时出现如下报错信息
    ```text
    ""Milvus 连接失败: <MilvusException: (code=2, message=Fail connecting to server on milvus-standalone:19530, illegal connection params or server unavailable)>"
    ```
    需修改.env中的MILVUS_HOST配置，与启动Milvus服务的IP保持一致

<a id="windows-embed-model"></a>
#### 3. 获取向量模型

记忆及知识库功能的运行依赖向量模型，以下流程以华为云为例，介绍向量模型的获取步骤。

* 点击<a href="https://console.huaweicloud.com/modelarts/?locale=zh-cn&region=cn-southwest-2#/model-studio/square" target="_blank" rel="nofollow noopener noreferrer"> 链接</a> 进入模型广场。 

* 体验记忆及知识库功能请点击 “向量模型”，可根据需要自行选择向量模型，以下内容以 BGE-M3 为例。

  ![找到embedd模型](../images/find_embed.png)

* 找到合适的向量模型后点击推理调用，进入模型信息获取界面。

  ![获取api_base和model_name](../images/embed_api_base_and_model_name.png)

* 记录API地址、model参数。

* 点击 "API Key 管理"，按照官方界面引导获取 API Key。

<a id="windows-sandbox"></a>
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
   HOST=0.0.0.0
   PORT=8188
   PYTHON_SANDBOX_URL=http://localhost:5001/run
   JS_SANDBOX_URL=http://localhost:5002/run
   ```

   其中 `PYTHON_SANDBOX_URL` 和 `JS_SANDBOX_URL` 为前面两步启动的 Python 和 JS 服务 URL，然后启动沙箱网关服务，即运行 `sandbox_server/gateway/openjiuwen_sandbox_gateway/server.py` 脚本。

4. 启动沙箱服务后请在`.env`文件中配置沙箱服务的路径，例如：`CODE_SANDBOX_URL=http://localhost:8188/run`

<a id="windows-plugin"></a>
### 问题三：如何启用插件服务

若要配置插件，需开启插件服务，需要进行如下操作：

1. 参考 `plugin_server/openjiuwen_plugin_server` 文件，创建所需的插件，然后启动插件服务，即运行 `plugin_server/openjiuwen_plugin_server/run_restful.py` 脚本，其中 `uvicorn.run(app, host="0.0.0.0", port=8185)` 定义了插件服务的 IP 和端口。

2. 启动插件服务后请在`.env`文件中配置插件服务的路径，例如：`VITE_PLUGIN_SERVICE_URL=http://localhost:8185`


<a id="windows-special-char"></a>
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