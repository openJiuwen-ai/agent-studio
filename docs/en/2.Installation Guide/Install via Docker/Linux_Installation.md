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

- enable the memory feature (optional)

  After enabling the memory function, the intelligent agent can automatically retain memory information such as conversation history and user personalized preferences, and supports users to view and delete memory content. During the interaction process, users do not need to repeatedly explain key information, and the intelligent agent's response logic can be more coherent, providing a better interaction experience.
  
  If you do not intend to enable the memory function, please skip this section directly; if you need to enable the memory function later, please refer to [If the memory function was not enabled in the early stage of openJiuwen, how can it be activated later](#docker-linux-memory)

  - The memory feature depends on an embedding model. The following steps use Huawei Cloud as an example to obtain an embedding model.

    - Click <a href="https://console.huaweicloud.com/modelarts/?locale=zh-cn&region=cn-southwest-2#/model-studio/square" target="_blank" rel="nofollow noopener noreferrer">this link</a> to go to the ModelArts Model Square.

    - To experience the memory feature, please click on "向量模型" (Embedding model) and select a vector model according to your needs. The following content uses BGE-M3 as an example.

      ![Find the embedding model](../images/find_embed.png)

    - After locating the suitable model, click "推理调用" (Inference Call) to enter the model information acquisition page.

      ![Get api_base and model_name](../images/embed_api_base_and_model_name.png)

    - Record the API address (corresponds to EMBED_API_BASE) and the model parameter (corresponds to EMBED_MODEL_NAME).

    - Click “API Key Management” and follow the official instructions to obtain an API Key (corresponds to EMBED_API_KEY).

  - After obtaining the embedding model information, configure it in the openJiuwen installation directory as follows:

  - If this is the first time starting the openJiuwen platform, add the embedding-related information to .env.custom:

    | Variable Name | Description |
    | --- | --- |
    | **EMBED_API_BASE** | The endpoint of the embedding model |
    | **EMBED_MODEL_NAME** | The name of the embedding model |
    | **EMBEDDING_MODEL_DIMENTION** | The dimension of the embedding model, determined by the selected EMBED_MODEL_NAME |
    | **EMBED_API_KEY** | The API key for the embedding model |
    | **EMBED_TIMEOUT** | The maximum wait time for embedding model requests(unit: second), default value `60` |
    | **EMBED_MAX_RETRIES** | The maximum number of retries when an embedding model request fails, default value `3` |
  
- To modify the port number of the frontend page service, please refer to [here](../../../../scripts/README.md#如何修改前端页面服务的端口号).

- Run the following command to start openJiuwen:

  ```bash
  ./service.sh up
  ```

  > **Note**: You may see “up Plugin + Sandbox Server failed” due to network issues. Please rerun `./service.sh up`.

- Upon successful startup, it will output:

  Local access: *local access address*

> For more details on container deployment, see the [OpenJiuwen Agent Studio Deployment Tool User Manual](../../../../scripts/README.md#openjiuwen-agent-studio-部署工具使用手册).

### 3. Access the system

- For local access, copy the *local access address* above into your browser and press Enter to open the openJiuwen interface.

- For access from another machine, copy the *network access address* above into your browser and press Enter to open the openJiuwen interface.

## III. Frequently Asked Questions (FAQ)

### Question 1: Why does the Milvus container suddenly exit during use?

The current version milvus 2.6.2 requires the AVX instruction set in the CPU. If it’s not available, milvus will exit automatically. You can check the CPU flags via `lscpu | grep Flags`.

### <a id="docker-linux-memory"></a>Question 2: If the memory function was not enabled in the early stage of openJiuwen, how can it be activated later.

The effectiveness of the memory feature depends on the parameter scale of the large language model.

The memory feature depends on an embedding model. The following steps use Huawei Cloud as an example to obtain an embedding model.

- Click <a href="https://console.huaweicloud.com/modelarts/?locale=zh-cn&region=cn-southwest-2#/model-studio/square" target="_blank" rel="nofollow noopener noreferrer">this link</a> to go to the ModelArts Model Square.

- To experience the memory feature, please click on "向量模型" (Embedding model) and select a vector model according to your needs. The following content uses BGE-M3 as an example.

  ![Find the embedding model](../images/find_embed.png)

- After locating the suitable model, click "推理调用" (Inference Call) to enter the model information acquisition page.

  ![Get api_base and model_name](../images/embed_api_base_and_model_name.png)

- Record the API address (corresponds to EMBED_API_BASE) and the model parameter (corresponds to EMBED_MODEL_NAME).

- Click “API Key Management” and follow the official instructions to obtain an API Key (corresponds to EMBED_API_KEY).

- After obtaining the embedding model information, configure it in the openJiuwen installation directory as follows:

- If this is the first time starting the openJiuwen platform, add the embedding-related information to .env.custom:

  | Variable Name | Description |
  | --- | --- |
  | **EMBED_API_BASE** | The endpoint of the embedding model |
  | **EMBED_MODEL_NAME** | The name of the embedding model |
  | **EMBEDDING_MODEL_DIMENTION** | The dimension of the embedding model, determined by the selected EMBED_MODEL_NAME |
  | **EMBED_API_KEY** | The API key for the embedding model |
  | **EMBED_TIMEOUT** | The maximum wait time for embedding model requests(unit: second), default value `60` |
  | **EMBED_MAX_RETRIES** | The maximum number of retries when an embedding model request fails, default value `3` |

- To enable the memory function after starting openJiuwen, directly modifying the `.env` file in the root directory will not take effect immediately. Running containers read from specific instance files in the `.envs/` directory. Follow the steps below:

  For multiple environment deployments, identify the corresponding environment suffix using the **service port** currently in use (e.g., `3006`):
  ```bash
  # Replace :3006 with the actual access port
  docker ps -a | grep :3006
  # Output example: ... 0.0.0.0:3006->8000/tcp ... jiuwen-backend-uz7jb
  # (Where uz7jb in jiuwen-backend-uz7jb is the suffix)
  ```
  Enter the `.envs` directory and find the configuration file with the corresponding suffix (e.g., `env.uz7jb`):

  ```bash
  cd .envs
  ls
  # Edit the corresponding file (e.g., `env.uz7jb`)
  ```
  Add embedding-related information in *env.uz7jb* (replace uz7jb with the actual suffix); after configuration is complete, restart using the service script specifying this configuration file to apply changes:
  ```bash
  # Return to the project root directory to execute
  cd ..
  ./service.sh up -f .envs/env.uz7jb
  ```

> **Note**: After configuring EMBEDDING_MODEL_DIMENTION and enabling the memory feature, do not modify it again, otherwise the memory feature will not work. It is also not recommended to modify other embedding model configurations, as they may affect quality.

### Question 3: Docker deployment fails on openEuler?

On openEuler, Docker deployment may be restricted by the kernel security mechanism seccomp (Secure Computing Model) when creating threads.

Please refer to the <a href="https://docs.openeuler.openatom.cn/zh/docs/24.03_LTS/docs/Container/%E5%AE%89%E5%85%A8%E7%89%B9%E6%80%A7.html" target="_blank" rel="nofollow noopener noreferrer">official guide</a> to adjust the corresponding seccomp security policy. The docker-compose deployment file is *conf/docker-jiuwen.template.yml* in the openJiuwen installation directory.

### Question 4: Docker image list included with openJiuwen

| Image | Version | License | Source Code |
| ------ | ---------------------------- | ------------- | ------------------------------------------------------------ |
| mysql  | 8.4.5                        | GPL 2.0       | <a href="https://github.com/mysql/mysql-server/tree/mysql-8.4.5" target="_blank" rel="nofollow noopener noreferrer"> Source link</a>       |
| minio  | RELEASE.2024-12-18T13-15-44Z | GNU AGPL 3.0      | <a href="https://github.com/minio/minio/tree/RELEASE.2024-12-18T13-15-44Z" target="_blank" rel="nofollow noopener noreferrer"> Source link</a> |
| milvus | 2.6.2                       | Apache 2.0    | -                                                            |
| etcd   | 3.5.18                      | Apache 2.0    | -                                                            |

### Question 5: How to stop openJiuwen

Run the following command to stop openJiuwen:

```
./service.sh down
```