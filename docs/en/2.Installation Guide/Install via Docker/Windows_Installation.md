This guide explains how to install openJiuwen on Windows using Docker.

## I. Environment Preparation

Make sure your machine meets the following requirements:

* Hardware:
  * CPU: Minimum 2 cores, 4 cores or more recommended
  * RAM: Minimum 4 GB, 8 GB or more recommended

* Operating System: Windows 10 or later

* Software
  * Git: Click <a href="https://mirrors.huaweicloud.com/git-for-windows/v2.51.0.windows.1/Git-2.51.0-64-bit.exe" target="_blank" rel="nofollow noopener noreferrer">Download</a> to download and install
  * Docker: Docker Desktop is recommended. See below for installation steps

### Install Docker Desktop
It is recommended to use WSL 2 (Windows Subsystem for Linux 2) as the virtualization backend when running Docker Desktop on Windows. Compared with LinuxKit, it offers better compatibility and lower resource consumption, and can avoid the known zombie container bugs.

**1. Enable WSL 2**

For eligible Windows systems (Windows 10 version 2004 or later <Build 19041 or higher> or Windows 11), simply running the command `wsl --install` allows one-click configuration, download, and installation of the default Linux distribution.

* Press Windows + S and type PowerShell to search.

* In the search results, right-click Windows PowerShell and select Run as administrator.

* Run the following command in PowerShell, then restart your computer.

  ```
  wsl --install
  ```

Older Windows versions do not support the full automation of this one-click command and may require additional manual steps. For detailed instructions, refer to the official documentation: <a href="https://learn.microsoft.com/en-us/windows/wsl/install" target="_blank" rel="nofollow noopener noreferrer">Install Linux on Windows with WSL</a>.

**2. Install Docker Desktop**

* Download: Go to the <a href="https://www.docker.com/products/docker-desktop/" target="_blank" rel="nofollow noopener noreferrer">Docker website</a> to download the Windows installer (for x86 machines, choose the AMD64 version);
* Run the installer: Select only the “Use WSL 2 instead of Hyper-V” and “Add shortcut to desktop” options, then click “OK” to complete installation;
* Restart your computer after installation;
* After restarting, open Docker Desktop and wait for it to finish loading (the first launch may take 5–10 minutes);
* Once Docker Desktop starts, for a trial you can click “Continue without signing in” on the welcome screen; for long-term use, refer to the <a href="https://docs.docker.com/desktop/setup/sign-in" target="_blank" rel="nofollow noopener noreferrer">official guide</a>.

* Docker Desktop installation is now complete.

> **Note**: If you encounter errors during installation or want to review the official installation steps, refer to the <a href="https://docs.docker.com/desktop/setup/install/windows-install/" target="_blank" rel="nofollow noopener noreferrer">Docker Desktop official installation guide</a>.

## II. Install openJiuwen

### 1. Download the release package (skip if you already have it)

* Click the download link for the version and save it locally.

  x86_64 architecture link: <a href="https://openjiuwen-ci.obs.cn-north-4.myhuaweicloud.com/agentstudio/deployTool_0.1.3_amd64.zip" target="_blank" rel="nofollow noopener noreferrer">openJiuwen v0.1.3</a>

  arm architecture link: <a href="https://openjiuwen-ci.obs.cn-north-4.myhuaweicloud.com/agentstudio/deployTool_0.1.3_arm64.zip" target="_blank" rel="nofollow noopener noreferrer">openJiuwen v0.1.3</a>

### 2. Configure Docker Desktop Virtual file shares

* Create the openJiuwen installation directory.

* Open Docker Desktop and click the ⚙️ icon in the upper-right corner to open settings. 

* In the left-hand sidebar, select “Resources“ to enter the Resources configuration page. 

* Click “File sharing“, type the *openJiuwen installation directory* (e.g., `D:\openJiuwen`) into the text box, and then click the “➕“ button to add it.

* Click “Apply & restart” to restart Docker Desktop.

### 3. Start openJiuwen

* Place the release package in the openJiuwen installation directory and extract it.

* Go to the directory where service.sh is located, right-click in a blank area to open Git Bash, and run the following command to confirm Docker Desktop is running:

  ```bash
  docker info >nul 2>&1 && (echo Docker Desktop is running) || (echo Docker Desktop is not running)
  ```
  > **Note**: If it shows “Docker Desktop is not running,” refer to the <a href="https://docs.docker.com/desktop/setup/install/windows-install/" target="_blank" rel="nofollow noopener noreferrer">Docker Desktop official guide</a>.

* enable the memory feature (optional)

  After enabling the memory function, the intelligent agent can automatically retain memory information such as conversation history and user personalized preferences, and supports users to view and delete memory content. During the interaction process, users do not need to repeatedly explain key information, and the intelligent agent's response logic can be more coherent, providing a better interaction experience.
  
  If you do not intend to enable the memory function, please skip this section directly; if you need to enable the memory function later, please refer to [If the memory function was not enabled in the early stage of openJiuwen, how can it be activated later](#docker-windows-memory)

  * The memory feature depends on an embedding model. The following steps use Huawei Cloud as an example to obtain an embedding model.

    * Click <a href="https://console.huaweicloud.com/modelarts/?locale=zh-cn&region=cn-southwest-2#/model-studio/square" target="_blank" rel="nofollow noopener noreferrer">this link</a> to enter ModelArts Model Square.

    * To experience the memory feature, please click on "向量模型" (Embedding model) and select a vector model according to your needs. The following content uses BGE-M3 as an example.

      ![Find the embedding model](../images/find_embed.png)

    * After locating the suitable model, click "推理调用" (Inference Call) to enter the model information acquisition page.

      ![Get api_base and model_name](../images/embed_api_base_and_model_name.png)

    * Record the API endpoint (corresponds to EMBED_API_BASE) and the model parameter (corresponds to EMBED_MODEL_NAME).

    * Click “API Key Management” and follow the instructions to obtain an API Key (corresponds to EMBED_API_KEY).

  * After obtaining the embedding model information, configure it in the *openJiuwen installation directory* as follows:

   If you are starting the openJiuwen platform for the first time, add the embedding-related information to *.env.custom*:

    | Variable Name | Description                                                                         |
    | --- |-------------------------------------------------------------------------------------|
    | EMBED_API_BASE                    | The embedding model API endpoint                                                    |
    | EMBED_MODEL_NAME                  | The embedding model name                                                            |
    | EMBEDDING_MODEL_DIMENTION         | The embedding vector dimension, determined by the model chosen via EMBED_MODEL_NAME |
    | EMBED_API_KEY                     | The embedding model API key                                                         |
    | EMBED_TIMEOUT                     | Maximum wait time for the embedding model(unit: second), default value `60`         |
    | EMBED_MAX_RETRIES                 | Maximum number of retries on embedding request failure, default value `3`           |

  * Run the following command to start openJiuwen:

    ```bash
    ./service.sh up
    ```

  >   **Note**: You may see an “up Plugin + Sandbox Server failed” error due to network issues. Please run `./service.sh up` again.

* After a successful start, it will output Local access: access URL.

### 4. Access the system

Copy the access URL above into your browser’s address bar and press Enter to see the openJiuwen interface.

## III. Frequently Asked Questions (FAQ)

### <a id="docker-windows-memory"></a>Question 1: If the memory function was not enabled in the early stage of openJiuwen, how can it be activated later

The effectiveness of the memory feature relates to the parameter size of the large language model.
  
The memory feature depends on an embedding model. The following steps use Huawei Cloud as an example to obtain an embedding model.

* Click <a href="https://console.huaweicloud.com/modelarts/?locale=zh-cn&region=cn-southwest-2#/model-studio/square" target="_blank" rel="nofollow noopener noreferrer">this link</a> to enter ModelArts Model Square.

* To experience the memory feature, please click on "向量模型" (Embedding model) and select a vector model according to your needs. The following content uses BGE-M3 as an example.

  ![Find the embedding model](../images/find_embed.png)

* After locating the suitable model, click "推理调用" (Inference Call) to enter the model information acquisition page.

  ![Get api_base and model_name](../images/embed_api_base_and_model_name.png)

* Record the API endpoint (corresponds to EMBED_API_BASE) and the model parameter (corresponds to EMBED_MODEL_NAME).

* Click “API Key Management” and follow the instructions to obtain an API Key (corresponds to EMBED_API_KEY).

* After obtaining the embedding model information, configure it in the *openJiuwen installation directory* as follows:

* After obtaining the vector model information, follow the steps below to locate the corresponding configuration file and add embedding-related information:

  | Variable Name | Description |
  | --- | --- |
  | EMBED_API_BASE                    | The embedding model API endpoint |
  | EMBED_MODEL_NAME                  | The embedding model name |
  | EMBED_API_KEY                     | The embedding model API key |
  | EMBEDDING_MODEL_DIMENTION         | The embedding vector dimension, determined by the model chosen via EMBED_MODEL_NAME |
  | EMBED_TIMEOUT                     | Maximum wait time for the embedding model(unit: second), default value `60`         |
  | EMBED_MAX_RETRIES                 | Maximum number of retries on embedding request failure, default value `3`           |

* To enable the memory function after starting openJiuwen, directly modifying the `.env` file in the root directory will not take effect immediately. Running containers read from specific instance files in the `.envs/` directory. Follow the steps below:

  For multiple environment deployments, identify the corresponding environment suffix using the **service port** currently in use (e.g., `3006`):
  ```powershell
  # Replace :3006 with the actual access port
  docker ps -a | findstr :3006
  # Output example: ... 0.0.0.0:3006->8000/tcp ... jiuwen-backend-uz7jb
  # (Where uz7jb in jiuwen-backend-uz7jb is the suffix)
  ```
  Enter the `.envs` directory and find the configuration file with the corresponding suffix (e.g., `env.uz7jb`):

  ```powershell
  cd .envs
  dir
  # Edit the corresponding file (e.g., `env.uz7jb`)
  ```
  Add embedding-related information in *env.uz7jb* (replace uz7jb with the actual suffix); after configuration is complete, restart using the service script specifying this configuration file to apply changes:
  ```powershell
  # Return to the project root directory to execute (Run in Git Bash or a terminal supporting .sh)
  cd ..
  ./service.sh up -f .envs/env.uz7jb
  ```

> **Note**: After configuring EMBEDDING_MODEL_DIMENTION and enabling the memory feature, do not modify this value again, or the memory feature will stop working. It is also not recommended to change other embedding model configurations, as it may affect performance.

### Question 2: Docker images included in openJiuwen

| Image | Version                     | License       | Source Repository |
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

### Question 4: How to avoid the Error `tried to kill container, but did not receive an exit event`

When the backend container fails to restart or even get deleted, and it encounters the following error:

```
Error response from daemon: Cannot restart container 6e0fa44910e0: tried to kill container, but did not receive an exit event
```

This indicates that the process corresponding to the container has entered the D state (uninterruptible sleep state). This is a common issue with the LinuxKit kernel, a lightweight, minimalist Linux virtual kernel developed by Docker in its early days for Windows and macOS platforms.This kernel lacks robust process resource management and recycling mechanisms, and does not implement a self-healing logic for processes in D state. Once a process enters D state, it will become permanently unresponsive, and the kernel is unable to perform effective management on it. In addition, the kernel features extremely low I/O forwarding efficiency. When performing host file read/write operations or network interactions, it will inherently significantly increase the probability of processes entering D state.In the event of such a scenario, the affected process will continuously occupy PID resources. Neither the kill -9 command nor the docker rm command can terminate or remove the container. The only viable solution to restore the normal operation of backend containers is to restart the entire virtual machine (i.e., restart Docker Desktop).

To fundamentally avoid such issues, it is recommended to use WSL 2 as the virtualization backend for Docker on Windows. Built on a full-fledged Linux kernel, WSL 2 provides more sophisticated handling logic and comprehensive resource recycling mechanisms for Linux processes in D state. Even if a process occasionally enters D state, the WSL 2 kernel will automatically trigger kernel-level resource recycling within 30–60 seconds, forcefully waking the blocked process from D state and preventing permanent process zombification. This represents the optimal operation mode for Docker Desktop on Windows.