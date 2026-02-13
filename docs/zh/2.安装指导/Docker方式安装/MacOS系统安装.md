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
* 请确保 Docker Desktop 满足以下内置组件版本要求：
  * Docker Engine：20.10 版本及以上
  * Docker Compose：v2.19.1 及以上版本
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

* 如需修改前端页面服务的端口号，请参考[这里](../../../../scripts/README.md#如何修改前端页面服务的端口号)。

* 进入 *service.sh* 所在目录，打开**终端**，输入以下命令启动 openJiuwen：

  ```bash
  ./service.sh up
  ```

  > **注意**：可能会因为网络原因出现 “up Plugin + Sandbox Server failed” 报错，请重新执行 `./service.sh up`。

* 启动成功后会输出 

  Local access: *本地访问地址*

  > **注意**：关于容器部署的更多使用细节，可参考[openjiuwen-agent-studio-部署工具使用手册](../../../../scripts/README.md#openjiuwen-agent-studio-部署工具使用手册)

### 3. 访问系统

* 若在本地查看，复制上述 *本地访问地址* 到浏览器地址栏，按下“回车键”将看到 openJiuwen 的界面。

* 若在外部机器查看，复制上述 *网络访问地址* 到浏览器地址栏，按下“回车键”将看到 openJiuwen 的界面。

* 连接 openJiuwen 的界面时，可能会弹出页面提示“您的连接不是私密连接”，原因是使用了自签名证书加密 SSL 证书来启用 HTTPS 加密通信。此提示并不表示连接本身存在恶意风险，而是提醒用户当前证书未经第三方权威机构认证。

* 可点击左下方“高级”选择“继续前往”进入 openJiuwen 的界面。

## 三、常见问题（FAQ）

### 问题一：openJiuwen 包含的 Docker 镜像清单
  
| 镜像名 | 镜像版本                     | license       | 源码地址                                                     |
| ------ | ---------------------------- | ------------- | ------------------------------------------------------------ |
| mysql  | 8.4.5                        | GPL 2.0       | <a href="https://github.com/mysql/mysql-server/tree/mysql-8.4.5" target="_blank" rel="nofollow noopener noreferrer"> 源码链接</a>       |
| minio  | RELEASE.2024-12-18T13-15-44Z | GNU AGPL 3.0      | <a href="https://github.com/minio/minio/tree/RELEASE.2024-12-18T13-15-44Z" target="_blank" rel="nofollow noopener noreferrer"> 源码链接</a> |
| milvus | 2.6.2                       | Apache 2.0    | -                                                            |
| etcd   | 3.5.18                      | Apache 2.0    | -                                                            |

### 问题二：如何停止 openJiuwen

输入以下命令停止 openJiuwen：

```
./service.sh down
```
