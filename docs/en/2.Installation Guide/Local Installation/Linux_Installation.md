This guide explains how to install openJiuwen locally on a Linux system. Local advanced installation offers two approaches:

* **Method 1: One-click installation script** – Automates most installation and configuration steps, including frontend, backend, and all dependent services, simplifying the process and suitable for quick deployment.
* **Method 2: Full manual installation** (not recommended) – Requires manually installing and configuring all dependent services; suitable for developers who need flexible configuration.

## I. Environment Preparation

Please ensure the machine meets the following requirements:

- Hardware:
  - CPU: Minimum 2 cores, 4+ cores recommended
  - RAM: Minimum 4GB, 8GB+ recommended

- Operating System:
  - Ubuntu: Minimum Ubuntu 20.04, Ubuntu 22.04 (Jammy) or newer recommended
    > **Note**: Ubuntu official and mainstream software sources have stopped supporting Ubuntu 20.04 (Focal) and older versions.

- Software (installation methods detailed below)
  - Git 2.40 or newer
  - Node.js 20.0 or newer
  - npm 10.0 or newer
  - Python 3.11 or newer
  - uv 0.5.0 or newer
  - MySQL 8.0 or newer
  - Milvus 2.6.2 or newer

## II. Installation Methods

### Method 1: One-Click Installation Script

The one-click script automates tool checks, code fetch, environment setup, and service startup to simplify installation.

#### 1. Get the Installation Script

* Download the <a href="https://openjiuwen-ci.obs.cn-north-4.myhuaweicloud.com/agentstudio/setup_scripts/setup_scripts_linux_v2.zip" target="_blank" rel="nofollow noopener noreferrer">installation script package</a>. The package includes:
  * `setup.sh` – Main installation script that runs the full flow
  * `utils.sh` – Common utilities
  * `check_curl.sh` – Check/install curl
  * `check_git.sh` – Check/install Git
  * `check_nodejs.sh` – Check/install Node.js via NVM
  * `check_python.sh` – Check/install Python
  * `check_mysql.sh` – Check/install MySQL
  * `config_mysql.sh` – Configure MySQL (create database, user, etc.)
  * `fetch_codes.sh` – Clone the agent-studio repository (supports specifying a branch)
  * `user_config.sh` – User configuration (optional: proxy, NVM mirror, pip index, npm registry)

#### 2. Configure Proxy, pip Index, NVM Mirror, and npm Registry (Optional)

If you need a proxy to access the internet or want to use a custom pip index, NVM Node.js mirror, or npm registry, edit `user_config.sh`:

* Open `user_config.sh` and set the following variables as needed:

  ```bash
  # Proxy (optional)
  HTTP_PROXY=""   # e.g. http://127.0.0.1:7890
  HTTPS_PROXY=""  # e.g. http://127.0.0.1:7890
  SSL_VERIFY=""   # optional: true/false (maps to git http.sslVerify)

  # pip index (optional)
  PIP_INDEX_URL=""      # e.g. https://pypi.tuna.tsinghua.edu.cn/simple
  PIP_TRUSTED_HOST=""   # e.g. pypi.tuna.tsinghua.edu.cn

  # NVM Node.js download mirror (optional, used when installing Node.js)
  NVM_NODEJS_ORG_MIRROR=""  # e.g. https://npmmirror.com/mirrors/node

  # npm registry (optional)
  NPM_REGISTRY=""       # e.g. https://registry.npmmirror.com
  ```

* **Proxy**: Leave variables empty to skip proxy; set full URL (e.g. `http://127.0.0.1:7890`) when needed. Authenticated proxy is supported (e.g. `http://user:pass@proxy.example.com:8080`). `SSL_VERIFY`: `true` enables Git SSL verification, `false` disables it.
* **pip**: Leave `PIP_INDEX_URL` and `PIP_TRUSTED_HOST` empty to use default index; when using a mirror, set both.
* **NVM mirror**: Leave `NVM_NODEJS_ORG_MIRROR` empty for default (nodejs.org), or set e.g. `https://npmmirror.com/mirrors/node` for check_nodejs.sh.
* **npm**: Leave `NPM_REGISTRY` empty to use default; set to your registry URL when needed.

#### 3. Run the Installation Script

* Enter the script directory and grant execute permission:

  ```bash
  chmod +x *.sh
  ```

* Run the main installation script:

  ```bash
  # Use MySQL by default
  ./setup.sh

  # Or specify SQLite
  ./setup.sh --db_type=sqlite
  ```

* When the script finishes, it will print backend and frontend PIDs, log paths, and the frontend URL. Open that URL in a browser to use openJiuwen.

 ![image](../images/一键安装运行完成截图linux.png)

#### 4. Common Script Parameters

  ```bash
  # Show status and access URLs
  ./setup.sh --status

  # Start backend and frontend
  ./setup.sh --start

  # Stop backend and frontend
  ./setup.sh --stop

  # Restart backend and frontend
  ./setup.sh --restart

  # List all supported options
  ./setup.sh --help
  ```

### Method 2: Full Manual Installation (Not Recommended)

> **Note**: This method requires manually installing and configuring all dependent services and is more complex. Prefer Method 1 when possible.

Complete dependency installation first, then perform source retrieval and installation.

#### 1. Install Dependencies (Ubuntu 22.04 as an example)

##### 1.1. Install Git

- Run the following commands to install Git:

  ```bash
  sudo apt update
  sudo apt install git
  ```

##### 1.2. Install Node.js and npm

- Run the following commands to install Node.js and npm:

  ```bash
  sudo apt update
  sudo apt install -y nodejs

  # Confirm node and npm versions
  node -v && npm -v
  ```
  > **Note**: In some Linux distributions, the repository-provided nodejs and npm versions are outdated. If node is below 20.0 or npm below 10.0, please refer to the Node.js official website to install a newer version: <a href="https://nodejs.org/zh-cn/download" target="_blank" rel="nofollow noopener noreferrer">Node.js official website</a>.

##### 1.3. Install Python and uv

- Run the following commands to install Python 3.11:

  ```bash
  sudo add-apt-repository ppa:deadsnakes/ppa

  sudo apt update
  sudo apt install python3.11 python3-pip
  ```
  > **Note**: The Deadsnakes PPA has stopped supporting Ubuntu 20.04 (Focal) and older. If your system is one of those versions, please follow the <a href="https://www.anaconda.com/docs/getting-started/miniconda/install" target="_blank" rel="nofollow noopener noreferrer">Miniconda official guide</a> and use conda to create a Python 3.11 environment.

- Run the following command to install uv:

  ```bash
  pip3 install uv
  ```

  > **Note**: If installation fails, please refer to the <a href="https://uv.doczh.com/getting-started/installation/#_1" target="_blank" rel="nofollow noopener noreferrer">uv official guide</a>.

##### 1.4. Install MySQL (Optional Component)

* **SQLite vs MySQL**:
  * SQLite requires no extra setup and is suitable for development and testing, but it has limitations (e.g., no support for concurrent writes, no user permission management).
  * MySQL offers more robust features and is better suited for complex scenarios, making it the recommended choice for real-world projects and production environments.

###### 1.4.1 SQLite

* **Note**: SQLite is used by default. Simply keep `DB_TYPE` as `sqlite` in `.env.example` to start the backend service directly—no additional installation or configuration is required.

###### 1.4.2 MySQL

* **Note**: If you prefer to use MySQL, change `DB_TYPE` in `.env.example` to `mysql` and follow the steps below to install and configure MySQL.

- Run the following commands to install MySQL:

  ```bash
  sudo apt update
  sudo apt install mysql-server
  sudo apt install libmysqlclient-dev pkg-config build-essential python3-dev
  ```

- After installation, run the following command to log in to MySQL:
   
  ```bash
  sudo mysql -u root
  ```

- In MySQL, execute the following commands to create databases:
  > **Note**: Set your own values for `your_user_name` and `your_password`. You will use them later when configuring the .env file.

  ```sql
  -- Create databases
  CREATE DATABASE openjiuwen_agent;
  CREATE DATABASE openjiuwen_ops;
  -- Create MySQL user
  CREATE USER 'your_user_name'@'localhost' IDENTIFIED BY 'your_password';
  -- Grant privileges and flush
  GRANT ALL PRIVILEGES ON openjiuwen_agent.* TO 'your_user_name'@'localhost';
  GRANT ALL PRIVILEGES ON openjiuwen_ops.* TO 'your_user_name'@'localhost';
  FLUSH PRIVILEGES;
  ```

##### 1.5. Milvus (Optional Component)

* **Note**：`.env.example` uses Chroma by default. Simply keep `INDEX_MANAGER_TYPE` set to `chroma` to directly start the backend service without additional installation or configuration. If you need to use Milvus, please change `INDEX_MANAGER_TYPE` in `.env.example` to `milvus` and refer to [How to enable memory and knowledge base features](#linux-memory) to complete the installation and configuration of Milvus.

* **Chroma vs Milvus**：
  * Chroma requires no additional installation and boasts a simple configuration. All you need to do is obtain the vector model, making it ideal for quick experimentation and suitable for development and testing environments. For obtaining the vector model, refer to [How to Obtain the Vector Model](#linux-embed-model).
  * Milvus has more comprehensive functions and can meet the needs of complex scenarios, so it is more recommended for use in practical engineering and production environments.


#### 2. openJiuwen Installation

##### 2.1. Get the Source Code

- Make sure you have access to the <a href="https://gitcode.com/org/openJiuwen" target="_blank" rel="nofollow noopener noreferrer">openJiuwen code repositories</a>. If not, please request access promptly.

- In the gitcode repository, follow the steps shown in the illustration (Step 2) to obtain the global Git configuration, then run:

  ```bash
  git config --global user.name your_username
  git config --global user.email your_useremail
  ```

  ![image](../images/gitcode-token.png)

- Follow the illustration (Step 3) to obtain a personal access token. When cloning the code, you will need to enter your gitcode account and personal access token.

- Run the following commands to clone the source code and enter the project root directory:

  ```bash
  # Multiple git operations are needed during installation; it is recommended to configure credential storage to avoid authentication errors.
  git config --global credential.helper store

  git clone https://gitcode.com/openJiuwen/agent-studio.git
  cd agent-studio
  ```

##### 2.2. Generate an AES Key (Optional)

- If you do not need to encrypt critical fields for storage, you can skip this step.
- Run the following commands to generate a key:
  ```bash
  cd scripts
    
  bash build_AES_master_key.sh
  ```
- After the script finishes, it will print the key to the console. Use it as needed; it is recommended to export it as an environment variable and save it elsewhere.
  ```bash
  export SERVER_AES_MASTER_KEY_ENV=your_aes_key
  ```
- **Note**: the AES key must remain unchanged. Changing the key later will make previously encrypted data undecipherable.

##### 2.3. Start openJiuwen

- Go to the project root directory.

- Copy the .env file:
  ```bash
  cp .env.example .env
  ```

- In the .env file, modify the following variables according to your actual environment (do not overwrite other variables):

  > **Tip**: You may replace values such as DB_HOST and DB_PORT with your actual database info. DB_USER and DB_PASSWORD should be the MySQL user and password you created earlier. If the password contains special characters, refer to the [Special Character Escape Table](#linux-special-char) to replace special characters with URL encoding.

  ```env
   # Database configuration (example)
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=your_user_name
   DB_PASSWORD=your_password
  
   # Vector index type configuration (example, optional values: chroma, milvus, default: chroma)
   INDEX_MANAGER_TYPE=chroma
  
   # Memory data storage path (example, default value: memory-data, can be modified according to actual situation)
   MEMORY_DATA_PATH=memory-data

   # Milvus configuration (example, only when INDEX_MANAGER_TYPE=milvus)
   MILVUS_HOST=127.0.0.1
   MILVUS_PORT=19530
   MILVUS_COLLECTION_NAME=memory_vector
  
   # Code sandbox configuration (example, please see [Question 2: How to Enable the Sandbox Feature] to learn more)
   CODE_SANDBOX_URL=http://localhost:8188/run

   # Plugin server configuration (example, please see [Question 3: How to Enable the Plugin Server] to learn more)
   VITE_PLUGIN_SERVICE_URL=http://localhost:8185
   VITE_PLUGIN_CONFIG_PATH=/config.json
   ```

  For variable descriptions, please refer to the table below. If you choose to enable the memory function for Milvus, please refer to [How to Enable the Memory and Knowledge Base Functions](#linux-memory). If you choose to enable the memory function for Chroma, you only need to obtain the vector model. For details, please refer to [How to Obtain the Vector Model](#linux-embed-model).

   | Variable Name                | Description                                                 | Example                                                                      |
   |------------------------------|-------------------------------------------------------------|------------------------------------------------------------------------------|
   | **DB_HOST**                      | Database host address                                       | `localhost`                                                                  |
   | **DB_PORT**                      | Database port                                               | `3306`                                                                       |
   | **DB_USER**                      | Database username                                           | `your_user_name`                                                             |
   | **DB_PASSWORD**                  | Database password                                           | `your_password`                                                              |
   | **INDEX_MANAGER_TYPE**        | Vector database type; optional values: chroma, milvus; default: chroma | `chroma`                              |
   | **MEMORY_DATA_PATH**          | Memory data storage path, default value: memory-data        | `memory-data`                         |
   | **MILVUS_HOST**                  | Milvus service host                                         | `127.0.0.1`                                                                  |
   | **MILVUS_PORT**                  | Milvus service port                                         | `19530`                                                                      |
   | **MILVUS_COLLECTION_NAME**       | Milvus collection name                                      | `memory_vector`                                                              |
   | **CODE_SANDBOX_URL**             | Code Sandbox url                                            | `http://localhost:8188/run`                                                                    |
   | **VITE_PLUGIN_SERVICE_URL**      | Plugin Server url                                           | `http://localhost:8185`                                                                    |
   | **VITE_PLUGIN_CONFIG_PATH**      | Plugin configuration file path for web                      | `/config.json`                                                                    |

- In the project root directory, run the following commands to start the backend service and wait patiently:
   
  ```bash
  cd backend
  uv venv
  uv sync
  ```

* Execute database version stamp commands to confirm current database version:
  ```bash
  # Agent database
  alembic -n alembic_mysql_agent stamp head
  alembic -n alembic_mysql_ops stamp head

  # SQLite database
  alembic -n alembic_sqlite_agent stamp head
  alembic -n alembic_sqlite_ops stamp head
  ```

  > Detailed description: The above commands are used to mark that the current database is already the latest version, facilitating subsequent database operations. Need to be executed separately for agent and ops databases. If using MySQL, execute `alembic -n alembic_mysql_agent stamp head` and `alembic -n alembic_mysql_ops stamp head`. For alembic usage methods, refer to [DATABASE_MIGRATION_DEVELOPMENT_GUIDE.md](../../../../backend/DATABASE_MIGRATION_DEVELOPMENT_GUIDE_EN.md)

  > **Note**: If it stalls for more than 20 minutes, press "Ctrl + C", try changing the url value of [[tool.uv.index]] in "pyproject.toml" in this directory to another available source, then re-run "uv sync".

  > **Note**: If `uv sync` fails, try: `uv sync --native-tls` to force using the system native TLS library (to resolve HTTPS download compatibility issues)

* Create log directory and start backend service
  ```bash
  mkdir -p logs/run
  source .venv/bin/activate
  python main.py
  ```

  After a successful start, you will see "Application startup complete".

  > **Tip**: If you need to enable code node or code plugin tool that require the code sandbox service, refer to [How to Enable the Sandbox Feature](#linux-sandbox) to complete the sandbox setup. And if you need to enable plugins that require the plugin server, which refer to [How to Enable the Plugin Server](#linux-plugin).

- Open a new terminal window, go to the project root directory, then run the following commands to install frontend dependencies:

  ```bash
  cd frontend
  npm install
  ```
  > **Note**: The vulnerabilities shown are known issues by npm and do not affect running the application.

  ![image](../images/npm-error.png)

- Run the following command to start the frontend service:

  ```
  npm run dev
  ```

- Upon successful startup, it will output:

  Local: *local access URL*

  Network: *network access URL*

##### 2.4. Access the System

  - For local viewing, Ctrl + left-click the *local access URL* to open openJiuwen in your browser; or copy the *local access URL* into the browser address bar and press Enter to view openJiuwen.
  
  - For external machines, copy the *network access URL* into the browser address bar and press Enter to view openJiuwen.

## III. Frequently Asked Questions (FAQ)

### <a id="linux-memory"></a> Question 1: How to Enable the Memory and Knowledge Base Features

The effectiveness of the memory feature is related to the parameter scale of the large language model.

The memory and knowledge base function supports two vector databases: Chroma and Milvus. If Milvus is chosen, refer to the following text for specific installation steps.

#### 1. Start Milvus

- It is recommended to start Milvus using Docker. Please follow the <a href="https://docs.docker.com/engine/install/" target="_blank" rel="nofollow noopener noreferrer">Docker official installation guide</a> and the <a href="https://docs.docker.com/compose/install/" target="_blank" rel="nofollow noopener noreferrer">Docker Compose official installation guide</a> to complete the setup.
- After installation, start Docker with: `sudo systemctl start docker`.

- Run the following command to save the “standalone_embed.sh” script in the current directory:

  ```
  curl -sfL https://raw.githubusercontent.com/milvus-io/milvus/master/scripts/standalone_embed.sh -o standalone_embed.sh
  ```
- Run the following commands to pull the image:

  ```bash
  # x86 architecture
  docker pull swr.cn-north-4.myhuaweicloud.com/openjiuwen/milvusdb/milvus-amd64:v2.6.2
  ```

  ```bash
  # ARM architecture
  docker pull swr.cn-north-4.myhuaweicloud.com/openjiuwen/milvusdb/milvus-arm64:v2.6.2
  ```

- In the “standalone_embed.sh” file, replace the Milvus official image name (e.g., `milvusdb/milvus:v2.6.7`) with the corresponding image name (e.g. x86 image: `swr.cn-north-4.myhuaweicloud.com/openjiuwen/milvusdb/milvus-amd64:v2.6.2`).
  
- After modifying, run the command below to start Milvus as a Docker container:

  ```
  bash standalone_embed.sh start
  ```

- After startup, run `docker ps -a` and you should see a container named Milvus-standalone running on port `19530`.

  > **Tip**: If issues occur during deployment, refer to the <a href="https://milvus.io/docs/zh/install_standalone-docker.md" target="_blank" rel="nofollow noopener noreferrer">Milvus official documentation</a>.

- To stop Milvus, run:

  ```
  bash standalone_embed.sh stop
  ```

- If the following error message appears when using memory or knowledge base after startup:
    ```text
    ""Milvus connection failed: <MilvusException: (code=2, message=Fail connecting to server on milvus-standalone:19530, illegal connection params or server unavailable)>"
    ```
    You need to modify the MILVUS_HOST configuration in the .env file to match the IP address used to start the Milvus service.

 <a id="linux-embed-model"></a>
#### 2. Obtain the embedding model

The memory and knowledge base features rely on an embedding model. The following steps use Huawei Cloud as an example.

- Click the <a href="https://console.huaweicloud.com/modelarts/?locale=zh-cn&region=cn-southwest-2#/model-studio/square" target="_blank" rel="nofollow noopener noreferrer">link</a> to enter ModelArts Model Square.

- To experience the memory feature and knowledge base feature, please click on "向量模型" (Embedding model) and select a vector model according to your needs. The following content uses BGE-M3 as an example.

  ![Find embedding model](../images/find_embed.png)

- After locating the suitable model, click "推理调用" (Inference Call) to enter the model information acquisition page.

  ![Get api_base and model_name](../images/embed_api_base_and_model_name.png)

- Record the API address and the model parameter.

- Click "API Key Management" and follow the official instructions to obtain an API Key.

### <a id="linux-sandbox"></a> Question 2: How to Enable the Sandbox Feature

If you need to enable code node or code plugin tool, the sandbox service is required, do the following:

1. Refer to `sandbox_server/python_server/.env.example` to create a `.env` file in `sandbox_server/python_server`. For example:

   ```env
   HOST=0.0.0.0
   PORT=5001
   ```

   Then, start the Python sandbox service by running the script `sandbox_server/python_server/openjiuwen_sandbox_pyserver/kernel.py`. `HOST` and `PORT` are the IP and port the Python sandbox will use.

2. Start the JS sandbox service by running the script `sandbox_server/js_server/kernel.js`. Its IP and port follow the code below:

   ```javascript
   const PORT = process.env.PORT || 5002;
   server.listen(PORT, "0.0.0.0", () => {
     console.log(`✅ JS sandbox listening on http://0.0.0.0:${PORT}`);
   });
   ```

3. Refer to `sandbox_server/gateway/.env.example` to create a `.env` file in `sandbox_server/gateway`. For example:

   ```env
   ENABLE_LINUX_SANDBOX=0
   HOST=0.0.0.0
   PORT=8188
   PYTHON_SANDBOX_URL=http://localhost:5001/run
   JS_SANDBOX_URL=http://localhost:5002/run
   ```

   `ENABLE_LINUX_SANDBOX` controls whether to enable the bwrap sandbox. `PYTHON_SANDBOX_URL` and `JS_SANDBOX_URL` are the URLs of the Python and JS services started in the previous steps.

   To enable the bwrap sandbox, set `ENABLE_LINUX_SANDBOX` to 1 and edit `sandbox_server/gateway/openjiuwen_sandbox_gateway/conf/sandbox_config.yaml` as needed. Currently supported configuration parameters include `seccomp`, `namespace`, `mount` filesystem, etc. Please ensure the Python and Node interpreters and their dependencies are listed under `mount`, and that `PATH` includes the interpreter paths. Example:

   ```
   seccomp: # whitelist mode
     allow:
       x86_64: ["epoll_wait", "getcwd", "wait4", "pread64", "set_tid_address", "prlimit64", "capget", "pipe2", "eventfd2", "pkey_alloc", "madvise", "sysinfo", "readlink", "geteuid", "getegid", "statx", "access", "clone", "arch_prctl", "clone3", "execve", "open", "lstat", "stat", "newfstatat", "lseek", "getdents64", "write", "close", "openat", "read", "futex", "mmap", "brk", "mprotect", "munmap", "rt_sigreturn", "mremap", "getgid", "getuid", "getpid", "getppid", "gettid", "exit", "exit_group", "rt_sigaction", "sched_yield", "set_robust_list", "get_robust_list", "rseq", "clock_gettime", "gettimeofday", "nanosleep", "epoll_create1", "epoll_ctl", "clock_nanosleep", "pselect6", "time", "rt_sigprocmask", "sigaltstack", "getrandom", "mkdirat", "mkdir", "socket", "connect", "bind", "listen", "accept", "sendto", "recvfrom", "getsockname", "recvmsg", "getpeername", "ppoll", "uname", "sendmsg", "sendmmsg", "fstat", "fcntl", "fstatfs", "poll", "epoll_pwait", 'ioctl']
       aarch64: ["statx", "getcwd", "readlinkat", "madvise", "sysinfo", "clone", "eventfd2", "pipe2", "fcntl", "prlimit64", "set_tid_address", "faccessat", "execve", "write", "close", "openat", "read", "lseek", "getdents64", "futex", "mmap", "brk", "mprotect", "munmap", "rt_sigreturn", "rt_sigprocmask", "sigaltstack", "mremap", "getuid", "getgid", "geteuid", "getegid", "getpid", "getppid", "gettid", "exit", "exit_group", "rt_sigaction", "sched_yield", "get_robust_list", "set_robust_list", "rseq", "epoll_create1", "clock_gettime", "gettimeofday", "nanosleep", "epoll_ctl", "clock_nanosleep", "pselect6", "timerfd_create", "timerfd_settime", "timerfd_gettime", "getrandom", "mkdirat", "socket", "connect", "bind", "listen", "accept", "sendto", "recvfrom", "recvmsg", "getsockname", "getpeername", "ppoll", "uname", "sendmmsg", "newfstatat", "fstat", "fstatfs", "epoll_pwait", "ioctl"]

   namespace:
     user: False
     net: True
     pid: True
     ipc: True
     uts: True
     cgroup: True

   mount:
     [
       {src: '/lib', dst: '/lib', mode: 'read'},
       {src: '/lib64', dst: '/lib64', mode: 'read'},
       {src: '/usr/bin', dst: '/usr/bin', mode: 'read'},
       {src: '/usr/lib', dst: '/usr/lib', mode: 'read'},
       {src: '/usr/lib64', dst: '/usr/lib64', mode: 'read'},
       {src: '/usr/share/nodejs', dst: '/usr/share/nodejs', mode: 'read'},
     ]

   sandbox:
     type: bubblewrap
     path: bwrap

   # Please ensure that both the Python and JavaScript interpreters
   # are already in the mount directory, and either provide their full
   # paths or add those paths to the PATH environment variable.
   interpreter:
     python_path: python3
     javascript_path: node

   environment:
     PATH: /bin:/usr/bin
   ```

   Then start the sandbox gateway by running `sandbox_server/gateway/openjiuwen_sandbox_gateway/server.py`.

4. After running the sandbox service, please configure sandbox's url in `.env`, such as: `CODE_SANDBOX_URL=http://localhost:8188/run`.

### <a id="linux-plugin"></a> Question 3: How to Enable the Plugin Server

If you need plugins, the plugin server is required, please do the following:

1. Refer to `plugin_server/openjiuwen_plugin_server` files, create plugin services as you need. Then start the plugin server by running the script `plugin_server/openjiuwen_plugin_server/run_restful.py`.

2. After running the plugin server, please configure plugin server's url in `.env`, such as: `VITE_PLUGIN_SERVICE_URL=http://localhost:8185`.

### <a id="linux-special-char"></a> Question 4: Special Character Escape Table

| Character | URL Encoding | Character | URL Encoding | Character | URL Encoding | Character | URL Encoding | Character | URL Encoding |
|----------|---------------|-----------|--------------|-----------|--------------|-----------|--------------|-----------|--------------|
| Space    | %20           | "         | %22          | #         | %23          | %         | %25          | &         | %26          |
| (        | %28           | )         | %29          | +         | %2B          | ,         | %2C          | /         | %2F          |
| :        | %3A           | ;         | %3B          | <         | %3C          | =         | %3D          | >         | %3E          |
| ?        | %3F           | @         | %40          | \         | %5C          | \|        | %7C          | -         | -            |

### Question 5: Why does local installation default to HTTP instead of HTTPS?

In local installation mode, the system defaults to HTTP for communication. This design choice is primarily based on the fact that local environments are typically used for development and testing, and avoiding mandatory TLS certificate setup helps reduce the initial usage barrier.

By contrast, the Docker installation method comes with built-in HTTPS support, allowing users to use secure communication out of the box without additional configuration.

If HTTPS is required in a local environment, developers must manually generate and configure TLS certificates according to their deployment needs.
