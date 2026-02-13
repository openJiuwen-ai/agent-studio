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
* Please ensure Docker Desktop meets the following built-in component version requirements:
  * Docker Engine: 20.10+
  * Docker Compose: v2.19.1+
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

* To modify the port number of the frontend page service, please refer to [here](../../../../scripts/README.md#如何修改前端页面服务的端口号).

* Run the following command to start openJiuwen:

  ```bash
  ./service.sh up
  ```

  >   **Note**: You may see an “up Plugin + Sandbox Server failed” error due to network issues. Please run `./service.sh up` again.

* After a successful start, it will output Local access: access URL.

  > **Note**: For more details on container deployment, see the [openJiuwen Agent Studio Deployment Tool User Manual](../../../../scripts/README.md).

### 4. Access the system

Copy the access URL above into your browser’s address bar and press Enter to see the openJiuwen interface.


## III. Frequently Asked Questions (FAQ)

### Question 1: Docker images included in openJiuwen

| Image | Version                     | License       | Source Repository |
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

### Question 3: How to avoid the Error `tried to kill container, but did not receive an exit event`

When the backend container fails to restart or even get deleted, and it encounters the following error:

```
Error response from daemon: Cannot restart container 6e0fa44910e0: tried to kill container, but did not receive an exit event
```

This indicates that the process corresponding to the container has entered the D state (uninterruptible sleep state). This is a common issue with the LinuxKit kernel, a lightweight, minimalist Linux virtual kernel developed by Docker in its early days for Windows and macOS platforms.This kernel lacks robust process resource management and recycling mechanisms, and does not implement a self-healing logic for processes in D state. Once a process enters D state, it will become permanently unresponsive, and the kernel is unable to perform effective management on it. In addition, the kernel features extremely low I/O forwarding efficiency. When performing host file read/write operations or network interactions, it will inherently significantly increase the probability of processes entering D state.In the event of such a scenario, the affected process will continuously occupy PID resources. Neither the kill -9 command nor the docker rm command can terminate or remove the container. The only viable solution to restore the normal operation of backend containers is to restart the entire virtual machine (i.e., restart Docker Desktop).

To fundamentally avoid such issues, it is recommended to use WSL 2 as the virtualization backend for Docker on Windows. Built on a full-fledged Linux kernel, WSL 2 provides more sophisticated handling logic and comprehensive resource recycling mechanisms for Linux processes in D state. Even if a process occasionally enters D state, the WSL 2 kernel will automatically trigger kernel-level resource recycling within 30–60 seconds, forcefully waking the blocked process from D state and preventing permanent process zombification. This represents the optimal operation mode for Docker Desktop on Windows.