本指南介绍在 MacOS 系统采用 Docker 方式安装 openJiuwen。

## 一、环境准备

请确保机器满足以下要求：

* 硬件：
  * CPU：最低 2 核，推荐 4 核及以上
  * RAM：最低 4GB，推荐 8GB 及以上

* 操作系统：MacOS14.0（Sonoma）及以上

* 软件
  * Git：运行以下命令进行安装：
    ```
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" # 若未安装Homebrew

    brew install git
    ```

  * Docker：推荐使用 Docker Desktop 进行安装，安装方法详见下文

### 安装 Docker Desktop

* 下载：访问 <a href="https://www.docker.com/products/docker-desktop/" rel="nofollow">Docker Desktop 官网</a>，点击 “Download for Mac” 获取 .dmg 安装包。；
* 双击下载的文件，将 **Docker** 图标 拖拽到 Applications 文件夹；
* 打开 Launchpad，找到并启动 Docker 应用；
* 首次运行时，系统会提示输入 macOS 密码以授权安装虚拟机组件，点击 OK 继续；
* 首次启动需等待 Docker 完成初始化（下载基础镜像，约需几分钟）。

* 至此 Docker Desktop 安装完成。

> **说明**：若安装过程中出现报错，请参考 <a href="https://docs.docker.com/desktop/setup/install/windows-install/" rel="nofollow">Docker Desktop 官方安装指导</a>。


## 二、openJiuwen 安装

### 1. 下载版本包（若已获取版本包跳过此步骤）

* 单击版本下载链接，下载对应版本包至本地。

  x86_64 架构下载链接：<a href="https://openjiuwen-ci.obs.cn-north-4.myhuaweicloud.com/agentstudio/deployTool_0.1.3_amd64.zip" target="_blank" rel="nofollow noopener noreferrer">openJiuwen v0.1.3</a>

  arm 架构下载链接：<a href="https://openjiuwen-ci.obs.cn-north-4.myhuaweicloud.com/agentstudio/deployTool_0.1.3_arm64.zip" target="_blank" rel="nofollow noopener noreferrer">openJiuwen v0.1.3</a>

### 2. 启动 openJiuwen

* 新建 *openJiuwen 安装目录*，将版本包放至安装目录并解压。

* 进入 *openJiuwen 安装目录*。

* 在运行前，请先运行以下命令升级bash：

  ```
  brew install bash
  ```

* 启用记忆功能(可选)：

    记忆功能开启后，智能体可自动留存对话历史、用户个性化偏好等记忆信息，并支持用户查看与删除记忆内容；交互过程中用户无需重复说明关键信息，智能体回答逻辑可更连贯，交互体验更好。

    若不开启记忆功能，请直接跳过本章节；后续需开启记忆功能，可参考[前期未启用记忆功能，后期如何开启记忆功能](#docker-macos-memory)。

  * 记忆功能的运行依赖向量模型，记忆功能的体验与大模型的参数规模相关。下面以华为云为例，介绍向量模型的获取。

    * 点击<a href="https://console.huaweicloud.com/modelarts/?locale=zh-cn&region=cn-southwest-2#/model-studio/square" target="_blank" rel="nofollow noopener noreferrer"> 链接</a> 进入模型广场。 

    * 点击 “向量模型”，可根据需要自行选择向量模型，以下内容以 BGE-M3 为例。

     ![找到embedd模型](../images/find_embed.png)

    * 找到合适的向量模型后点击推理调用，进入模型信息获取界面。

     ![获取api_base和model_name](../images/embed_api_base_and_model_name.png)

    * 记录API地址（对应 EMBED_API_BASE）、model参数（对应 EMBED_MODEL_NAME）。

    * 点击 “API Key 管理”，按照官方界面引导获取 API Key（对应 EMBED_API_KEY）。

  * 获取向量模型信息后，请在 *openJiuwen 的安装目录* 进行如下配置：

  * 若是初次启动 openJiuwen 平台，请在 .env.custom 中添加 embedding 相关的信息：
  
  | 变量名 | 变量说明                                |
  | --- |-------------------------------------|
  | **EMBED_API_BASE**                    | 向量模型的接口地址                           |            
  | **EMBED_MODEL_NAME**                  | 向量模型的名称                             |
  | **EMBEDDING_MODEL_DIMENTION**         | 向量模型的维度，根据 EMBED_MODEL_NAME 选择的模型确定 |
  | **EMBED_API_KEY**                     | 向量模型的 API 密钥                        |
  | **EMBED_TIMEOUT**                     | 嵌入模型的最大等待时间（单位秒）<br>默认为`60`       |
  | **EMBED_MAX_RETRIES**                 | 嵌入模型请求失败时的最大重试次数<br>默认为`3`        |

* 进入 *service.sh* 所在目录，打开**终端**，输入以下命令启动 openJiuwen：

  ```bash
  ./service.sh up
  ```

  > **注意**：可能会因为网络原因出现 “up Plugin + Sandbox Server failed” 报错，请重新执行 `./service.sh up`。

* 启动成功后会输出 

  Local access: *本地访问地址*

  Network access: *网络访问地址*

### 3. 访问系统

* 若在本地查看，复制上述 *本地访问地址* 到浏览器地址栏，按下“回车键”将看到 openJiuwen 的界面。

* 若在外部机器查看，复制上述 *网络访问地址* 到浏览器地址栏，按下“回车键”将看到 openJiuwen 的界面。

* 连接 openJiuwen 的界面时，可能会弹出页面提示“您的连接不是私密连接”，原因是使用了自签名证书加密 SSL 证书来启用 HTTPS 加密通信。此提示并不表示连接本身存在恶意风险，而是提醒用户当前证书未经第三方权威机构认证。

* 可点击左下方“高级”选择“继续前往”进入 openJiuwen 的界面。

## 三、常见问题（FAQ）

<a id="docker-macos-memory"></a>
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

  | 变量名 | 变量说明                              |
  | --- |-----------------------------------|
  | **EMBED_API_BASE**                    | 嵌入模型的接口地址                         |            
  | **EMBED_MODEL_NAME**                  | 嵌入模型的名称                           |
  | **EMBEDDING_MODEL_DIMENTION**         | 嵌入模型的维度，根据EMBED_MODEL_NAME选择的模型确定 |
  | **EMBED_API_KEY**                     | 嵌入模型的API密钥，换成自己的                  |
  | **EMBED_TIMEOUT**                     | 嵌入模型的最大等待时间（单位秒）<br>默认为`60`       |
  | **EMBED_MAX_RETRIES**                 | 嵌入模型请求失败时的最大重试次数<br>默认为`3`        |

* 在启动 openJiuwen 之后启用记忆功能，直接修改根目录的` .env `文件不会立即生效，运行中的容器读取的是 `.envs/ `目录下的特定实例文件。请按照以下步骤操作：

  由于可能同时运行了多个环境，请通过正在使用的**服务端口号**（例如`3006`）来查找对应的环境后缀：
  ```bash
  # 请将 :3006 替换为实际访问的端口号
  docker ps -a | grep :3006
  # 输出示例: ... 0.0.0.0:3006->8000/tcp ... jiuwen-backend-uz7jb
  # (其中 jiuwen-backend-uz7jb 中的 uz7jb 即为后缀)
  ```
  进入 `.envs` 目录，找到对应后缀的配置文件（例如 `env.uz7jb`）：

  ```bash
  cd .envs
  ls
  # 编辑对应的文件（例如 `env.uz7jb`）
  ```
  请在 *env.uz7jb*（请将 uz7jb 替换为实际的后缀） 中添加 embedding 相关的信息；配置完成后，使用启动脚本指定该配置文件进行重启，使配置生效：
  ```bash
  # 回到项目根目录执行
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
