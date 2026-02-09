本指南介绍在 Windows 系统采用 Docker 方式安装 openJiuwen。

## 一、环境准备

请确保机器满足以下要求：

* 硬件：
  * CPU：最低 2 核，推荐 4 核及以上
  * RAM：最低 4GB，推荐 8GB 及以上

* 操作系统：Windows10及以上

* 软件
  * Git：点击 <a href="https://mirrors.huaweicloud.com/git-for-windows/v2.51.0.windows.1/Git-2.51.0-64-bit.exe" target="_blank" rel="nofollow noopener noreferrer"> 下载</a> 进行下载并安装
  * Docker：推荐使用 Docker Desktop 进行安装，安装方法详见下文

### 安装Docker Desktop
Windows 上运行 Docker Desktop 推荐使用 WSL 2（Windows Subsystem for Linux 2） 作为虚拟化后端，相比 LinuxKit 兼容性更好、资源占用更低，且能避免已知的僵尸容器 Bug。

**1. 启用 WSL 2**

对于符合条件的 Windows 系统（Windows 10 版本 2004 及更高版本<内部版本 19041 及更高版本>或 Windows 11），仅运行 `wsl --install`就能一键配置、下载并安装默认的 Linux 发行版。

* 按下 Windows + S，输入 PowerShell 进行搜索。

* 在搜索结果中，右键点击 Windows PowerShell，选择 以管理员身份运行。

* 在 PowerShell 执行如下命令，然后重新启动计算机。

  ```
  wsl --install
  ```

而旧版本 Windows 不支持这个一键命令的完整自动化功能，可能需要补充操作，具体请参考<a href="https://learn.microsoft.com/zh-cn/windows/wsl/install" target="_blank" rel="nofollow noopener noreferrer"> 如何使用 WSL 在 Windows 上安装 Linux</a>

**2. 安装 Docker Desktop**

* 下载：前往 <a href="https://www.docker.com/products/docker-desktop/" target="_blank" rel="nofollow noopener noreferrer"> Docker 官网</a> 下载 Windows 版本安装包（X86 机器请选择 AMD64 版本）；
* 运行安装包：​**仅勾选​「Use WSL 2 instead of Hyper-V」、​「Add shortcut to desktop」选项**，点击​「OK」开始安装；
* 安装完成后，请重启电脑；
* 重启后，打开 Docker Desktop，等待加载完成（首次启动可能需要 5 ~ 10 分钟）；
* Docker Desktop 启动后，若临时试用，可点击欢迎界面的 `Continue without signing in` 直接进入；长期使用请参考 <a href="https://docs.docker.com/desktop/setup/sign-in" target="_blank" rel="nofollow noopener noreferrer"> 官方指导</a>。

* 至此 Docker Desktop 安装完成。

> **说明**：若安装过程中出现报错，或了解官方安装过程，请参考 <a href="https://docs.docker.com/desktop/setup/install/windows-install/" target="_blank" rel="nofollow noopener noreferrer"> Docker Desktop 官方安装指导</a>。


## 二、openJiuwen 安装

### 1. 下载版本包（若已获取版本包跳过此步骤）

* 单击版本下载链接，下载对应版本包至本地。

  x86_64 架构下载链接：<a href="https://openjiuwen-ci.obs.cn-north-4.myhuaweicloud.com/agentstudio/deployTool_0.1.3_amd64.zip" target="_blank" rel="nofollow noopener noreferrer">openJiuwen v0.1.3</a>

  arm 架构下载链接：<a href="https://openjiuwen-ci.obs.cn-north-4.myhuaweicloud.com/agentstudio/deployTool_0.1.3_arm64.zip" target="_blank" rel="nofollow noopener noreferrer">openJiuwen v0.1.3</a>

### 2. Docker Desktop 设置 Virtual file shares

* 新建 *openJiuwen 安装目录*。

* 打开 Docker Desktop，单击右上方 ⚙ 进入设置界面；

* 单击左侧竖列导航栏​「Resources」，进入 Resources 配置界面；

* 单击​「File sharing」，并在输入框中填写 *openJiuwen 的安装目录*（例如：`D:\openJiuwen`），最后单击右侧 ➕ 进行添加；

* 点击 “Apply & restart” 重启 Docker Desktop。

### 3. 启动 openJiuwen

* 将版本包放至 *openJiuwen 安装目录* 并解压。

* 进入 *service.sh* 所在目录，在空白处右键打开 Git Bash，输入以下命令确认 Docker Desktop 已启动：

  ```bash
  docker info >nul 2>&1 && (echo Docker Desktop 已启动) || (echo Docker Desktop 未启动)
  ```
  > **说明**：若提示 “Docker Desktop 未启动”，请参考 <a href="https://docs.docker.com/desktop/setup/install/windows-install/" target="_blank" rel="nofollow noopener noreferrer"> Docker Desktop 官方指导</a>。

* 启用记忆功能(可选)：

    记忆功能开启后，智能体可自动留存对话历史、用户个性化偏好等记忆信息，并支持用户查看与删除记忆内容；交互过程中用户无需重复说明关键信息，智能体回答逻辑可更连贯，交互体验更好。

    若不开启记忆功能，请直接跳过本章节；后续需开启记忆功能，可参考[前期未启用记忆功能，后期如何开启记忆功能](#docker-windows-memory)。

  * 记忆功能的运行依赖向量模型，记忆功能的体验与向量模型的参数规模相关。下面以华为云为例，介绍向量模型的获取。

    * 点击<a href="https://console.huaweicloud.com/modelarts/?locale=zh-cn&region=cn-southwest-2#/model-studio/square" target="_blank" rel="nofollow noopener noreferrer"> 链接</a> 进入模型广场。 

    * 点击 “向量模型”，可根据需要自行选择向量模型，以下内容以 BGE-M3 为例。

      ![找到embedd模型](../images/find_embed.png)

    * 找到合适的向量模型后点击推理调用，进入模型信息获取界面。

      ![获取api_base和model_name](../images/embed_api_base_and_model_name.png)

    * 记录API地址（对应 EMBED_API_BASE）、model参数（对应 EMBED_MODEL_NAME）。

    * 点击 “API Key 管理”，按照官方界面引导获取 API Key（对应 EMBED_API_KEY）。

  * 获取向量模型信息后，请在 *openJiuwen 的安装目录* 进行如下配置：

  * 若是初次启动 openJiuwen 平台，请在 .env.custom 中添加 embedding 相关的信息：
  
  | 变量名 | 变量说明                              |
  | --- |-----------------------------------|
  | **EMBED_API_BASE**                    | 向量模型的接口地址                         |            
  | **EMBED_MODEL_NAME**                  | 向量模型的名称                           |
  | **EMBEDDING_MODEL_DIMENTION**         | 向量模型的维度，根据 EMBED_MODEL_NAME 选择的模型确定 |
  | **EMBED_API_KEY**                     | 向量模型的 API 密钥                      |
  | **EMBED_TIMEOUT**                     | 向量模型的最大等待时间（单位秒），默认值`60`          |
  | **EMBED_MAX_RETRIES**                 | 向量模型请求失败时的最大重试次数,默认值`3`           |

* 输入以下命令启动 openJiuwen：

  ```bash
  ./service.sh up
  ```

  > **注意**：可能会因为网络原因出现 “up Plugin + Sandbox Server failed” 报错，请重新执行 `./service.sh up`。

* 启动成功后会输出 Local access：*访问地址*。

### 4. 访问系统

复制上述 *访问地址* 到浏览器地址栏，按下“回车键”将看到 openJiuwen 的界面。

* 连接 openJiuwen 的界面时，可能会弹出页面提示“您的连接不是私密连接”，原因是使用了自签名证书加密 SSL 证书来启用 HTTPS 加密通信。此提示并不表示连接本身存在恶意风险，而是提醒用户当前证书未经第三方权威机构认证。

* 可点击左下方“高级”选择“继续前往”进入 openJiuwen 的界面。

## 三、常见问题（FAQ）

<a id="docker-windows-memory"></a>
### 问题一：前期未启用记忆功能，后期如何开启记忆功能

记忆功能的体验与大模型的参数规模相关。
  
记忆功能的运行依赖向量模型，以下流程以华为云为例，介绍向量模型的获取步骤。

* 点击<a href="https://console.huaweicloud.com/modelarts/?locale=zh-cn&region=cn-southwest-2#/model-studio/square" target="_blank" rel="nofollow noopener noreferrer"> 链接</a> 进入模型广场。 

* 体验记忆功能请点击 “向量模型”，可根据需要自行选择向量模型，以下内容以 BGE-M3 为例。

  ![找到embedd模型](../images/find_embed.png)

* 找到合适的向量模型后点击推理调用，进入模型信息获取界面。

  ![获取api_base和model_name](../images/embed_api_base_and_model_name.png)

* 记录API地址（对应 EMBED_API_BASE）、model参数（对应 EMBED_MODEL_NAME）。

* 点击 “API Key 管理”，按照官方界面引导获取 API Key（对应 EMBED_API_KEY）。

* 获取向量模型信息后，请在 *openJiuwen 的安装目录* 进行如下配置：

* 获取向量模型信息后，按照下面的步骤找到对应的配置文件，添加 embedding 相关的信息：

  | 变量名 | 变量说明                               |
  | --- |------------------------------------|
  | **EMBED_API_BASE**                    | 向量模型的接口地址                          |            
  | **EMBED_MODEL_NAME**                  | 向量模型的名称                            |
  | **EMBEDDING_MODEL_DIMENTION**         | 向量模型的维度，根据 EMBED_MODEL_NAME 选择的模型确定 |
  | **EMBED_API_KEY**                     | 向量模型的 API 密钥                       |
  | **EMBED_TIMEOUT**                     | 向量模型的最大等待时间（单位秒），默认值`60`          |
  | **EMBED_MAX_RETRIES**                 | 向量模型请求失败时的最大重试次数,默认值`3`           |

* 在启动 openJiuwen 之后启用记忆功能，直接修改根目录的` .env `文件不会立即生效，运行中的容器读取的是 `.envs/ `目录下的特定实例文件。请按照以下步骤操作：

  由于可能同时运行了多个环境，请通过正在使用的**服务端口号**（例如`3006`）来查找对应的环境后缀：
  ```powershell
  # 请将 :3006 替换为实际访问的端口号
  docker ps -a | findstr :3006
  # 输出示例: ... 0.0.0.0:3006->8000/tcp ... jiuwen-backend-uz7jb
  # (其中 jiuwen-backend-uz7jb 中的 uz7jb 即为后缀)
  ```
  进入 `.envs` 目录，找到对应后缀的配置文件（例如 `env.uz7jb`）：

  ```powershell
  cd .envs
  dir
  # 编辑对应的文件（例如 `env.uz7jb`）
  ```
  请在 *env.uz7jb*（请将 uz7jb 替换为实际的后缀） 中添加 embedding 相关的信息；配置完成后，使用启动脚本指定该配置文件进行重启，使配置生效：
  ```powershell
  # 回到项目根目录执行（需要在 Git Bash 或支持 .sh 的终端中运行）
  cd ..
  ./service.sh up -f .envs/env.uz7jb
  ```


> **注意**：在配置 *EMBEDDING_MODEL_DIMENTION* 之后，请不要再次修改，否则记忆功能会无法使用。embedding模型的其他配置也不建议修改，可能会影响效果。

### 问题二：openJiuwen 包含的 Docker 镜像清单

| 镜像名 | 镜像版本                     | license       | 源码地址                                                     |
| ------ | ---------------------------- | ------------- | ------------------------------------------------------------ |
| mysql  | 8.4.5                        | GPL 2.0       | <a href="https://github.com/mysql/mysql-server/tree/mysql-8.4.5" target="_blank" rel="nofollow noopener noreferrer"> 源码链接</a>       |
| minio  | RELEASE.2024-12-18T13-15-44Z | GNU AGPL 3.0      | <a href="https://github.com/minio/minio/tree/RELEASE.2024-12-18T13-15-44Z" target="_blank" rel="nofollow noopener noreferrer"> 源码链接</a> |
| milvus | 2.6.2                       | Apache 2.0    | -                                                            |
| etcd   | 3.5.18                      | Apache 2.0    | -                                                            |

### 问题三：如何停止 openJiuwen

输入以下命令停止 openJiuwen：

```
./service.sh down
```

### 问题四：遇到 tried to kill container, but did not receive an exit event 错误，如何处理

当你的后端容器，无法重启，甚至无法删除，报如下错误：
Error response from daemon: Cannot restart container 6e0fa44910e0: tried to kill container, but did not receive an exit event

这是容器对应的进程进入了 D 状态（不可中断睡眠状态）。这是 Linux Kit 内核的常见问题，该内核是 Docker 早期为 Windows/macOS 开发的轻量化极简 Linux 虚拟内核，缺乏完善的进程资源管理及回收机制，未实现 D 状态进程的自愈逻辑。进程一旦进入 D 状态，将陷入永久僵死状态，内核无法对其进行有效管理；加之该内核的 IO 转发效率极低，在执行宿主机文件读写或网络交互操作时，本身就会显著提升进程进入 D 状态的概率。一旦出现此类情况，该进程将持续占用 PID 资源，kill -9 命令无法终止，docker rm 命令亦无法移除容器，仅能通过重启整个虚拟机（即重启 Docker Desktop）使后端容器恢复正常。

为从根本上规避此类问题，建议采用 WSL 2 作为 Windows Docker 的虚拟化后端，其基于完整 Linux 内核，对于 Linux 进程的 D 状态有更完善的处理逻辑和更完备的资源回收机制，即使进程偶尔进入 D 状态，WSL 2 内核会在 30~60 秒内自动触发内核级资源回收，强制把 D 状态进程从阻塞中唤醒，不会让进程永久僵死。这是 Docker Desktop 在 Windows 上的最优运行模式。
