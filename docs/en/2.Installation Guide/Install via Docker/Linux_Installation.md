This guide describes how to install openJiuwen on Linux using Docker.

## I. Environment Preparation

Make sure your machine meets the following requirements:

- Hardware:
  - CPU: Minimum 2 cores, 4+ cores recommended
  - RAM: Minimum 4 GB, 8+ GB recommended

- Operating System:
  - Ubuntu: Minimum Ubuntu 20.04, Ubuntu 22.04 (Jammy) or later recommended
    > **Note**: Ubuntu official and mainstream software repositories have stopped supporting Ubuntu 20.04 (Focal) and earlier.
  - EulerOS: Huawei Cloud EulerOS 2.0 or later

- Software:
  - Docker and Docker Compose: Installation methods are described below

> Note: The default path for Docker's core storage—including images, container runtime data, volumes, and network configurations—is /var/lib/docker/. Most Linux distributions (CentOS, Ubuntu, Debian) do not create a separate partition for /var by default. Instead, /var exists as a regular directory under the root partition (/) and shares space with the system disk (root partition). We recommend that you mount /var to a dedicated, high-capacity partition or separate disk to isolate it from the system disk. This ensures that if /var becomes full, core system operations on the root partition will not be affected.

### Install Docker and Docker Compose

- Refer to the <a href="https://docs.docker.com/engine/install/" target="_blank" rel="nofollow noopener noreferrer">Docker official installation guide</a> and the <a href="https://docs.docker.com/compose/install/" target="_blank" rel="nofollow noopener noreferrer">Docker Compose official installation guide</a> to complete the setup.

- Please ensure Docker and Docker Compose meet the following version requirements:
  - Docker: 20.10+
  - Docker Compose: v2.19.1+

- Verify the installation of Docker and Docker Compose:

    ```
    docker version
    docker-compose version
    ```

## II. Installing openJiuwen (Ubuntu 22.04 as an example)

### 1. Download the release package (skip if you already have it)

- Download the version package based on the machine architecture:

  - Download the x86_64 package:
    ```
    wget https://openjiuwen-ci.obs.cn-north-4.myhuaweicloud.com/agentstudio/deployTool_0.1.3_amd64.zip
    ```

  - Download the arm package:
    ```
    wget https://openjiuwen-ci.obs.cn-north-4.myhuaweicloud.com/agentstudio/deployTool_0.1.3_arm64.zip
    ```

### 2. Start openJiuwen

- Place the release package in the installation directory.

- install unzip tool
  ```bash
  sudo apt update && sudo apt install unzip -y
  ```

- Extract the corresponding architecture version package
  - Extract the x86_64 package
    ```
    unzip deployTool_0.1.3_amd64
    ```

  - Extract the arm package
    ```
    unzip deployTool_0.1.3_arm64
    ```

- Enter the *deployTool_0.1.3_xxx64* directory and run the following commands to confirm Docker is running:

  ```bash
  sudo systemctl start docker
  sudo systemctl status docker
  ```
  > **Note**: If the output shows “inactive”, refer to the <a href="https://docs.docker.com/engine/install/" target="_blank" rel="nofollow noopener noreferrer">Docker official installation guide</a> and the <a href="https://docs.docker.com/compose/install/" target="_blank" rel="nofollow noopener noreferrer">Docker Compose official installation guide</a>.

- To modify the port number of the frontend page service, please refer to [here](../../../../scripts/README.md#如何修改前端页面服务的端口号).

- Run the following command to start openJiuwen:

  ```bash
  ./service.sh up
  ```

  > **Note**: You may see “up Plugin + Sandbox Server failed” due to network issues. Please rerun `./service.sh up`.

- Upon successful startup, it will output:

  Local access: *local access address*

  > **Note**: For more details on container deployment, see the [openJiuwen Agent Studio Deployment Tool User Manual](../../../../scripts/README.md).

### 3. Access the system

- For local access, copy the *local access address* above into your browser and press Enter to open the openJiuwen interface.

- For access from another machine, copy the *network access address* above into your browser and press Enter to open the openJiuwen interface.

## III. Frequently Asked Questions (FAQ)

### Question 1: Why does the Milvus container suddenly exit during use?
The current version milvus 2.6.2 requires the AVX instruction set in the CPU. If it’s not available, milvus will exit automatically. You can check the CPU flags via `lscpu | grep Flags`.

### Question 2: Docker deployment fails on openEuler?

On openEuler, Docker deployment may be restricted by the kernel security mechanism seccomp (Secure Computing Model) when creating threads.

Please refer to the <a href="https://docs.openeuler.openatom.cn/zh/docs/24.03_LTS/docs/Container/%E5%AE%89%E5%85%A8%E7%89%B9%E6%80%A7.html" target="_blank" rel="nofollow noopener noreferrer">official guide</a> to adjust the corresponding seccomp security policy. The docker-compose deployment file is *conf/docker-jiuwen.template.yml* in the openJiuwen installation directory.

### Question 3: Docker image list included with openJiuwen

| Image | Version | License | Source Code |
| ------ | ---------------------------- | ------------- | ------------------------------------------------------------ |
| mysql  | 8.4.5                        | GPL 2.0       | <a href="https://github.com/mysql/mysql-server/tree/mysql-8.4.5" target="_blank" rel="nofollow noopener noreferrer"> Source link</a>       |
| minio  | RELEASE.2024-12-18T13-15-44Z | GNU AGPL 3.0      | <a href="https://github.com/minio/minio/tree/RELEASE.2024-12-18T13-15-44Z" target="_blank" rel="nofollow noopener noreferrer"> Source link</a> |
| milvus | 2.6.2                       | Apache 2.0    | -                                                            |
| etcd   | 3.5.18                      | Apache 2.0    | -                                                            |

### Question 4: How to stop openJiuwen

Run the following command to stop openJiuwen:

```
./service.sh down
```