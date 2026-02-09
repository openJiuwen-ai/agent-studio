This guide describes how to install openJiuwen on macOS via Docker.

## I. Environment Preparation

Ensure your machine meets the following requirements:

* Hardware: 
  * CPU: Minimum 2 cores, 4 cores or more recommended
  * RAM: Minimum 4GB, 8GB or more recommended

* Operating System: macOS 14.0 (Sonoma) or later

* Software:
  * Git: Install Git by running the following commands: 
    ```
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" # If Homebrew is not installed

    brew install git
    ```

  * Docker: Docker Desktop is reocmmended. The installation steps are described below.

### Docker Desktop Installation

* Download: Visit the <a href="https://www.docker.com/products/docker-desktop/" rel="nofollow">Docker Desktop official website</a>, and click "Download for Mac" to download the .dmg installer.
* Double-click the installer and drag **Docker** into the Applications folder.
* Find and start the Docker application.
* Upon first opening Docker, the system will prompt you to enter your macOS password to authorize the installation of virtual machine components. Click OK to continue.
* The first startup will require waiting for Docker to complete initialization. (Downloading base images, which may take a few minutes)

* Docker Desktop installation complete.

> **Note**: If you encounter any errors during installation, please refer to the <a href="https://docs.docker.com/desktop/setup/install/mac-install/" rel="nofollow">official Docker Desktop installation guide</a>.


## II. openJiuwen Installation

### 1. Download the release package (Skip this step if already downloaded)

* Click the download link corresponding to your local machine to download the release package:

  x86_64 architecture download link: <a href="https://openjiuwen-ci.obs.cn-north-4.myhuaweicloud.com/agentstudio/deployTool_0.1.3_amd64.zip" target="_blank" rel="nofollow noopener noreferrer">openJiuwen v0.1.3</a>

  arm architecture download link: <a href="https://openjiuwen-ci.obs.cn-north-4.myhuaweicloud.com/agentstudio/deployTool_0.1.3_arm64.zip" target="_blank" rel="nofollow noopener noreferrer">openJiuwen v0.1.3</a>

### 2. Start openJiuwen

* Create a *openJiuwen installation directory*, place the release package in the installation directory and extract it.

* Navigate to the *openJiuwen installation directory*.

* Before running, run the following command to upgrade bash: 

  ```
  brew install bash
  ```

* enable the memory feature (optional)

  After enabling the memory function, the intelligent agent can automatically retain memory information such as conversation history and user personalized preferences, and supports users to view and delete memory content. During the interaction process, users do not need to repeatedly explain key information, and the intelligent agent's response logic can be more coherent, providing a better interaction experience.
  
  If you do not intend to enable the memory function, please skip this section directly; if you need to enable the memory function later, please refer to [If the memory function was not enabled in the early stage of openJiuwen, how can it be activated later](#docker-macos-memory)

  * The memory feature depends on an embedding model. The following steps use Huawei Cloud as an example to obtain an embedding model.

    * Click <a href="https://console.huaweicloud.com/modelarts/?locale=zh-cn&region=cn-southwest-2#/model-studio/square" target="_blank" rel="nofollow noopener noreferrer">this link</a> to enter ModelArts Model Square.

    * To experience the memory feature, please click on "向量模型" (Embedding model) and select a vector model according to your needs. The following content uses BGE-M3 as an example.

      ![Find the embedding model](../images/find_embed.png)

    * After locating the suitable model, click "推理调用" (Inference Call) to enter the model information acquisition page.

      ![Get api_base and model_name](../images/embed_api_base_and_model_name.png)

    * Record the API endpoint (corresponds to EMBED_API_BASE) and the model parameter (corresponds to EMBED_MODEL_NAME).

    * Click “API Key Management” and follow the instructions to obtain an API Key (corresponds to EMBED_API_KEY).

  * After obtaining the embedding model information, configure it in the *openJiuwen installation directory* as follows:

  * If you are starting the openJiuwen platform for the first time, add the embedding-related information to *.env.custom*:

    | Variable Name | Description                                                                         |
    | --- |-------------------------------------------------------------------------------------|
    | EMBED_API_BASE                    | The embedding model API endpoint                                                    |
    | EMBED_MODEL_NAME                  | The embedding model name                                                            |
    | EMBEDDING_MODEL_DIMENTION         | The embedding vector dimension, determined by the model chosen via EMBED_MODEL_NAME |
    | EMBED_API_KEY                     | The embedding model API key                                                         |
    | EMBED_TIMEOUT                     | Maximum wait time for the embedding model(unit: second), default value `60`         |
    | EMBED_MAX_RETRIES                 | Maximum number of retries on embedding request failure, default value `3`           |

* Open **Terminal**, navigate to the directory where *service.sh* is located, and enter the following command to start openJiuwen: 

  ```bash
  ./service.sh up
  ```

  > **Note**: You may encounter the error message "up Plugin + Sandbox Server failed" due to network issues. Simply rerun `./service.sh up`.

* After a successful startup, the following information will be displayed:

  Local access: *local access address*

  Network access: *network access address*

### 3. Access the System

* To access locally, copy the above *local access address* into your browser's address bar and press "Enter" to see the openJiuwen interface.

* To access on another machine, copy the above *network access address* into your browser's address bar and press "Enter" to see the openJiuwen interface.

## III、Frequently Asked Questions (FAQ) 

### <a id="docker-macos-memory"></a>Question 1: If the memory function was not enabled in the early stage of openJiuwen, how can it be activated later

The effectiveness of the memory feature depends on the number of parameters of the LLM.
  
The memory feature relies on an embedding model. The following steps uses Huawei Cloud as an example to illustrate how to obtain an embedding model.


* Click <a href="https://console.huaweicloud.com/modelarts/?locale=zh-cn&region=cn-southwest-2#/model-studio/square" target="_blank" rel="nofollow noopener noreferrer">this link</a> to enter the Model Square. 

* To experience the memory feature, please click on "向量模型" (Embedding model) and select a vector model according to your needs. The following content uses BGE-M3 as an example.

  ![Locate the embedding model](../images/find_embed.png)

* After locating the suitable model, click "推理调用" (Inference Call) to enter the model information acquisition page.

  ![Obtain api_base and model_name](../images/embed_api_base_and_model_name.png)

* Record the API address (corresponding to EMBED_API_BASE) and model parameters (corresponding to EMBED_MODEL_NAME).

* Click "API Key Management" and follow the instructions on the website to obtain an API Key (corresponding to EMBED_API_KEY).

* After obtaining the embedding model information, perform the following configuration in the *openJiuwen installation directory*: 

* After obtaining the vector model information, follow the steps below to locate the corresponding configuration file and add embedding-related information:

  | Variable Name | Description                                                                             |
  | --- |-----------------------------------------------------------------------------------------|
  | **EMBED_API_BASE**                    | API endpoint of the embedding model                                                     |            
  | **EMBED_MODEL_NAME**                  | Name of the embedding model                                                             |
  | **EMBEDDING_MODEL_DIMENTION**         | Dimension of the embedding model, determined by the model specified in EMBED_MODEL_NAME |
  | **EMBED_API_KEY**                     | API key for the embedding model (replace with your own)                                 |
  | **EMBED_TIMEOUT**                     | Maximum wait time for the embedding model<br>Default:`60`                               |
  | **EMBED_MAX_RETRIES**                 | Maximum number of retries when an embedding request fails<br>Default:`3`                |

* To enable the memory function after starting openJiuwen, directly modifying the `.env` file in the root directory will not take effect immediately. Running containers read from specific instance files in the `.envs/` directory. Follow the steps below:

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


> **Note**: Once the memory feature has been enabled after configuring *EMBEDDING_MODEL_DIMENTION*, do not modify this value again, otherwise the memory feature will stop working. It is also not recommended to change other embedding model configurations, as doing so may affect performance or results.

### Question 2: What Docker Images are included in openJiuwen
  
| Image Name | Image Version                     | License       | Source Code                                                     |
| ------ | ---------------------------- | ------------- | ------------------------------------------------------------ |
| mysql  | 8.4.5                        | GPL 2.0       | <a href="https://github.com/mysql/mysql-server/tree/mysql-8.4.5" target="_blank" rel="nofollow noopener noreferrer">Source link</a>       |
| minio  | RELEASE.2024-12-18T13-15-44Z | GNU AGPL 3.0      | <a href="https://github.com/minio/minio/tree/RELEASE.2024-12-18T13-15-44Z" target="_blank" rel="nofollow noopener noreferrer">Source link</a> |
| milvus | 2.6.2                       | Apache 2.0    | -                                                            |
| etcd   | 3.5.18                      | Apache 2.0    | -                                                            |

### Question 3: How to stop openJiuwen

Run the following command to stop openJiuwen: 

```
./service.sh down
```
