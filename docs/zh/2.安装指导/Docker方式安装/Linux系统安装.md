本指南介绍在 Linux 系统采用 Docker 方式安装 openJiuwen

## 一、环境准备

请确保机器满足以下要求：

* 硬件：
  * CPU：最低 2 核，推荐 4 核及以上
  * RAM：最低 4GB，推荐 8GB 及以上

* 操作系统：
  * Ubuntu：最低 Ubuntu 20.04，推荐 Ubuntu 22.04 (Jammy) 及以上
    > **注意**：Ubuntu 官方与主流软件源已停止支持 Ubuntu 20.04 (Focal) 及以下版本系统。
  * EulerOS：Huawei Cloud EulerOS 2.0及以上

* 软件
  * Docker 和 Docker Compose：安装方法详见下文

  > 注意：Docker 的镜像、容器运行时数据、数据卷、网络配置等核心存储，默认路径是：/var/lib/docker/， 而多数 Linux 发行版（CentOS、Ubuntu、Debian）默认不单独划分 /var 分区，/var 只是根分区 / 下的普通目录，共用 ** 系统盘（根分区）** 的空间。建议客户把 /var 单独挂载到空间充足的独立分区 / 独立数据盘，和系统盘隔离，即便 /var 占满，也不会影响根分区的系统核心运行。

### 安装 Docker 和 Docker Compose

* 请参照 <a href="https://docs.docker.com/engine/install/" target="_blank" rel="nofollow noopener noreferrer">Docker 官方安装指南</a> 以及 <a href="https://docs.docker.com/compose/install/" target="_blank" rel="nofollow noopener noreferrer">Docker Compose 官方安装指南</a> 完成配置。

* 请确保 Docker 和 Docker Compose 满足以下版本要求：
  * Docker：20.10 版本及以上
  * Docker Compose：v2.19.1 及以上版本

* 验证 Docker 和 Docker Compose 安装:

    ```
    docker version
    docker-compose version
    ```

## 二、openJiuwen 安装（以下以 Ubuntu 22.04 为例）

### 1. 下载版本包（若已获取版本包跳过此步骤）

* 根据机器架构下载版本包：

  - 下载 x86_64 架构版本包
    ```
    wget https://openjiuwen-ci.obs.cn-north-4.myhuaweicloud.com/agentstudio/deployTool_0.1.3_amd64.zip
    ```

  - 下载 arm 架构版本包：
    ```
    wget https://openjiuwen-ci.obs.cn-north-4.myhuaweicloud.com/agentstudio/deployTool_0.1.3_arm64.zip
    ```

### 2. 启动 openJiuwen

* 将版本包放至安装目录。

* 安装 unzip 工具
  ```bash
  sudo apt update && sudo apt install unzip -y
  ```

* 解压对应的架构版本包。
  - 解压 x86_64 架构版本包
    ```
    unzip deployTool_0.1.3_amd64.zip
    ```

  - 解压 arm 架构版本包
    ```
    unzip deployTool_0.1.3_arm64.zip
    ```

* 进入 *deployTool_0.1.3_xxx64* 目录，输入以下命令确认 Docker 已启动：

  ```bash
  sudo systemctl start docker
  sudo systemctl status docker
  ```
  > **说明**：若输出 “inactive” ，请参考 <a href="https://docs.docker.com/engine/install/" target="_blank" rel="nofollow noopener noreferrer">Docker 官方安装指南</a> 以及 <a href="https://docs.docker.com/compose/install/" target="_blank" rel="nofollow noopener noreferrer"> Docker Compose 官方安装指南</a>。

* 如需修改前端页面服务的端口号，请参考[这里](../../../../scripts/README.md#如何修改前端页面服务的端口号)。

* 输入以下命令启动 openJiuwen：

  ```bash
  ./service.sh up
  ```

  > **注意**：可能会因为网络原因出现 “up Plugin + Sandbox Server failed” 报错，请重新执行 `./service.sh up`。

* 启动成功后会输出 

  Local access: *本地访问地址*

  > **注意**：关于容器部署的更多使用细节，可参考[openjiuwen-agent-studio-部署工具使用手册](../../../../scripts/README.md#openjiuwen-agent-studio-部署工具使用手册)


### 3. 访问系统

* 若在本地查看，复制上述 *本地访问地址* 到浏览器地址栏，按下“回车键”将看到 openJiuwen 的界面。

* 若在外部机器查看，复制上述 *网络访问地址* 到浏览器地址栏，按下 “回车键” 将看到 openJiuwen 的界面。

* 连接 openJiuwen 的界面时，可能会弹出页面提示“您的连接不是私密连接”，原因是使用了自签名证书加密 SSL 证书来启用 HTTPS 加密通信。此提示并不表示连接本身存在恶意风险，而是提醒用户当前证书未经第三方权威机构认证。

* 可点击左下方“高级”选择“继续前往”进入 openJiuwen 的界面。

## 三、常见问题（FAQ）

### 问题一：在使用过程中出现 milvus 容器突然退出是什么原因？

目前使用的 milvus2.6.2 需要 CPU 中存在 AVX 指令，如果不存在 milvus 会自动退出。可以通过 `lscpu | grep Flags` 查看 cpu 指令。

### 问题二：openEuler 环境中，Docker 部署失败？

openEuler 环境中，Docker 部署时创建线程会收到 seccomp(Secure Computing Model)内核安全机制的限制。

请参考 <a href="https://docs.openeuler.openatom.cn/zh/docs/24.03_LTS/docs/Container/%E5%AE%89%E5%85%A8%E7%89%B9%E6%80%A7.html" target="_blank" rel="nofollow noopener noreferrer"> 官方指导</a>，调整相应的 seccomp 安全策略，对应的 docker-compose 部署文件是 openJiuwen 安装目录下：*conf/docker-jiuwen.template.yml* 文件。

### 问题三：openJiuwen 包含的 Docker 镜像清单

| 镜像名 | 镜像版本                     | license       | 源码地址                                                     |
| ------ | ---------------------------- | ------------- | ------------------------------------------------------------ |
| mysql  | 8.4.5                        | GPL 2.0       | <a href="https://github.com/mysql/mysql-server/tree/mysql-8.4.5" target="_blank" rel="nofollow noopener noreferrer"> 源码链接</a>       |
| minio  | RELEASE.2024-12-18T13-15-44Z | GNU AGPL 3.0      | <a href="https://github.com/minio/minio/tree/RELEASE.2024-12-18T13-15-44Z" target="_blank" rel="nofollow noopener noreferrer"> 源码链接</a> |
| milvus | 2.6.2                       | Apache 2.0    | -                                                            |
| etcd   | 3.5.18                      | Apache 2.0    | -                                                            |

### 问题四：如何停止 openJiuwen

输入以下命令停止 openJiuwen：

```
./service.sh down
```
