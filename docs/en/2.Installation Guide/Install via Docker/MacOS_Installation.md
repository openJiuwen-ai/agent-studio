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
* Please ensure Docker Desktop meets the following built-in component version requirements:
  * Docker Engine: 20.10+
  * Docker Compose: v2.19.1+
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


* To modify the port number of the frontend page service, please refer to [here](../../../../scripts/README.md#如何修改前端页面服务的端口号).

* Open **Terminal**, navigate to the directory where *service.sh* is located, and enter the following command to start openJiuwen: 

  ```bash
  ./service.sh up
  ```

  > **Note**: You may encounter the error message "up Plugin + Sandbox Server failed" due to network issues. Simply rerun `./service.sh up`.

* After a successful startup, the following information will be displayed:

  Local access: *local access address*

  > **Note**: For more details on container deployment, see the [openJiuwen Agent Studio Deployment Tool User Manual](../../../../scripts/README.md).


### 3. Access the System

* To access locally, copy the above *local access address* into your browser's address bar and press "Enter" to see the openJiuwen interface.

* To access on another machine, copy the above *network access address* into your browser's address bar and press "Enter" to see the openJiuwen interface.

## III、Frequently Asked Questions (FAQ) 

### Question 1: What Docker Images are included in openJiuwen
  
| Image Name | Image Version                     | License       | Source Code                                                     |
| ------ | ---------------------------- | ------------- | ------------------------------------------------------------ |
| mysql  | 8.4.5                        | GPL 2.0       | <a href="https://github.com/mysql/mysql-server/tree/mysql-8.4.5" target="_blank" rel="nofollow noopener noreferrer">Source link</a>       |
| minio  | RELEASE.2024-12-18T13-15-44Z | GNU AGPL 3.0      | <a href="https://github.com/minio/minio/tree/RELEASE.2024-12-18T13-15-44Z" target="_blank" rel="nofollow noopener noreferrer">Source link</a> |
| milvus | 2.6.2                       | Apache 2.0    | -                                                            |
| etcd   | 3.5.18                      | Apache 2.0    | -                                                            |

### Question 2: How to stop openJiuwen

Run the following command to stop openJiuwen: 

```
./service.sh down
```
