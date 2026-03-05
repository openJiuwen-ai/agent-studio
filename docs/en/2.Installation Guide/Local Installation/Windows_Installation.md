This guide describes how to install openJiuwen locally on Windows. Local advanced installation offers two approaches:

* **Method 1: One-click installation script** – Automates most installation and configuration steps and simplifies the process; suitable for quick deployment.
* **Method 2: Manual installation of all dependencies** – Requires manually installing and configuring all dependent services; suitable for developers who need flexible configuration.

## I. Environment Preparation

Ensure your machine meets the following requirements:

* Hardware:
  * CPU: Minimum 2 cores, 4+ cores recommended
  * RAM: Minimum 4GB, 8GB+ recommended

* Operating system: Windows 10 or later

* Software (installation details below)
  * Git 2.40 or later
  * Node.js 20.0 or later
  * npm 9.0 or later
  * Python 3.11.4 or later
  * uv 0.5.0 or later
  * MySQL 8.0 or later
  * Milvus 2.6.2 or later
  * PowerShell 5.1 or later (run `$PSVersionTable.PSVersion` to check)

## II. Installation Methods

### Method 1: One-Click Installation Script

The one-click script automates tool checks, code fetch, environment setup, and service startup to simplify installation.

#### 1. Get the Installation Script

* Download the <a href="https://openjiuwen-ci.obs.cn-north-4.myhuaweicloud.com/agentstudio/setup_scripts/setup_scripts_windows_v2.zip" target="_blank" rel="nofollow noopener noreferrer">installation script package</a>. The package includes:
  * `setup.ps1` – Main installation script that runs the full flow
  * `utils.ps1` – Common utilities
  * `check_git.ps1` – Check/install Git
  * `check_nodejs.ps1` – Check/install Node.js
  * `check_python.ps1` – Check/install Python
  * `check_mysql.ps1` – Check/install MySQL
  * `config_mysql.ps1` – Configure MySQL (create database, user, etc.)
  * `fetch_codes.ps1` – Clone the agent-studio repository (supports specifying a branch)
  * `user_config.ps1` – User configuration (optional: proxy, pip index, npm registry)

#### 2. Configure Proxy, pip Index, and npm Registry (Optional)

If you need a proxy to access the internet or want to use a custom pip index or npm registry, edit `user_config.ps1`:

* Open `user_config.ps1` and set the following variables as needed:

  ```powershell
  # Proxy (optional)
  $HTTP_PROXY=""   # e.g. http://127.0.0.1:7890
  $HTTPS_PROXY=""  # e.g. http://127.0.0.1:7890
  $SSL_VERIFY=""   # optional: true/false (maps to git http.sslVerify)

  # pip index (optional)
  $PIP_INDEX_URL=""      # e.g. https://pypi.tuna.tsinghua.edu.cn/simple
  $PIP_TRUSTED_HOST=""   # e.g. pypi.tuna.tsinghua.edu.cn

  # npm registry (optional)
  $NPM_REGISTRY=""       # e.g. https://registry.npmmirror.com
  ```

* **Proxy**: Leave variables empty to skip proxy; set full URL (e.g. `http://127.0.0.1:7890`) when needed. Authenticated proxy is supported (e.g. `http://user:pass@proxy.example.com:8080`). `$SSL_VERIFY`: `true` enables Git SSL verification, `false` disables it.
* **pip**: Leave `$PIP_INDEX_URL` and `$PIP_TRUSTED_HOST` empty to use default index; when using a mirror, set both.
* **npm**: Leave `$NPM_REGISTRY` empty to use default; set to your registry URL when needed.

#### 3. Run the Installation Script

* Run PowerShell as Administrator and set the execution policy:

  ```powershell
  Set-ExecutionPolicy Unrestricted -Scope CurrentUser
  ```

* Enter the script directory and run the main installation script:

  ```powershell
  # Use MySQL by default
  .\setup.ps1

  # Or specify SQLite
  .\setup.ps1 -DbType sqlite
  ```

* When the script finishes, it will print backend and frontend PIDs, log paths, and the frontend URL. Open that URL in a browser to use openJiuwen.

![image](../images/一键安装运行完成截图win.png)

#### 4. Common Script Parameters

  ```powershell
  # Show status and access URLs
  .\setup.ps1 -Status

  # Stop backend and frontend
  .\setup.ps1 -Stop

  # Start backend and frontend
  .\setup.ps1 -Start

  # Restart backend and frontend
  .\setup.ps1 -Restart

  # List all supported parameters
  .\setup.ps1 -Help
  ```

### Method 2: Manual Installation of All Dependencies

Complete dependency installation first, then perform source retrieval and installation.

#### 1. Install Dependencies

##### 1.1. Install Git

* Download the <a href="https://mirrors.huaweicloud.com/git-for-windows/v2.51.0.windows.1/Git-2.51.0-64-bit.exe" target="_blank" rel="nofollow noopener noreferrer">Git</a> installer. If the download is slow, switch networks and try again.

* After installation, open PowerShell and run: `git --version`. If successful, it will print the Git version.

##### 1.2. Install Node.js and npm

* Download the <a href="https://nodejs.org/dist/v22.21.1/node-v22.21.1-x64.msi" target="_blank" rel="nofollow noopener noreferrer">Node.js</a> installer and follow the prompts. If the download is slow, switch networks and try again.

* After installation, open PowerShell and run: `node -v` and `npm -v`. If successful, both versions will be displayed.

##### 1.3. Install Python and uv

* Download the <a href="https://www.python.org/ftp/python/3.11.4/python-3.11.4-amd64.exe" target="_blank" rel="nofollow noopener noreferrer">Python</a> installer and follow the prompts (it is recommended to check Add Python to PATH). If the download is slow, switch networks and try again.

* After installation, open PowerShell and run: `python --version`. If successful, it will print the Python version.

* Open PowerShell and run: `pip install uv` to install uv.

* After installation, run: `uv --version`. If successful, it will print the uv version.

##### 1.4. Install MySQL (Optional Component)

* **SQLite vs MySQL**:
  * SQLite requires no extra setup and is suitable for development and testing, but it has limitations (e.g., no support for concurrent writes, no user permission management).
  * MySQL offers more robust features and is better suited for complex scenarios, making it the recommended choice for real-world projects and production environments.

###### 1.4.1 SQLite

* **Note**: SQLite is used by default. Simply keep `DB_TYPE` as `sqlite` in `.env.example` to start the backend service directly—no additional installation or configuration is required.

###### 1.4.2 MySQL

* **Note**: If you prefer to use MySQL, change `DB_TYPE` in `.env.example` to `mysql` and follow the steps below to install and configure MySQL.

* Download the <a href="https://dev.mysql.com/get/Downloads/MySQL-8.4/mysql-8.4.7-winx64.msi" target="_blank" rel="nofollow noopener noreferrer">MySQL 8.4</a> installer.

* Double-click the downloaded installer and follow the wizard. Typical mode is recommended.

  > **Note**: If you encounter “This application requires Visual Studio 2019 x64 Redistributable”, download the latest supported Visual C++ x64 installer from Microsoft: <a href="https://aka.ms/vc14/vc_redist.x64.exe" target="_blank" rel="nofollow noopener noreferrer">link</a>.

* After installation, set the root password for MySQL and keep it safe.

* Press Win+R → enter the command below to open the Environment Variables window:

  ```
  rundll32.exe sysdm.cpl,EditEnvironmentVariables
  ```

* Add MySQL’s bin directory to the system PATH (default path: `C:\Program Files\MySQL\MySQL Server 8.4\bin`)

* After installation, open PowerShell and log in to MySQL (enter the root password you set):

  ```bash
  mysql -u root -p
  ```

* In MySQL, create the databases with the following commands:
  > Explanation: Set `your_user_name` and `your_password` yourself; you’ll use them later in the .env file.

  ```sql
  -- Create databases
  CREATE DATABASE openjiuwen_agent;
  CREATE DATABASE openjiuwen_ops;
  -- Create MySQL user
  CREATE USER 'your_user_name'@'localhost' IDENTIFIED BY 'your_password';
  -- Grant privileges and refresh
  GRANT ALL PRIVILEGES ON openjiuwen_agent.* TO 'your_user_name'@'localhost';
  GRANT ALL PRIVILEGES ON openjiuwen_ops.* TO 'your_user_name'@'localhost';
  FLUSH PRIVILEGES;
  ```

##### 1.5. Milvus (Optional Component)

* **Note**：`.env.example` uses Chroma by default. Simply keep `INDEX_MANAGER_TYPE` set to `chroma` to directly start the backend service without additional installation or configuration. If you need to use Milvus, please change `INDEX_MANAGER_TYPE` in `.env.example` to `milvus` and refer to [How to enable memory and knowledge base features](#windows-memory) to complete the installation and configuration of Milvus.

* **Chroma vs Milvus**：
  * Chroma requires no additional installation and boasts a simple configuration. All you need to do is obtain the vector model, making it ideal for quick experimentation and suitable for development and testing environments. For obtaining the vector model, refer to [How to Obtain the Vector Model](#windows-embed-model).
  * Milvus has more comprehensive functions and can meet the needs of complex scenarios, so it is more recommended for use in practical engineering and production environments.

#### 2. openJiuwen Installation

##### 2.1. Get the Source Code

* Ensure you have access to the <a href="https://gitcode.com/org/openJiuwen" target="_blank" rel="nofollow noopener noreferrer">openJiuwen code repositories</a>. If not, request access.

* In the GitCode repository, follow step 2 in the screenshot to get the global Git config, then set Git with:

  ```bash
  git config --global user.name your_username
  git config --global user.email your_useremail
  ```

  ![image](../images/gitcode-token.png)

* Follow step 3 in the screenshot to obtain a personal access token. You will need to enter your GitCode account and token when cloning.

* Create an openJiuwen directory, open PowerShell in it, then clone the code and go to the project root:

  ```bash
  # You will perform multiple git operations; configuring credential storage helps avoid authentication errors.
  git config --global credential.helper store

  git clone https://gitcode.com/openJiuwen/agent-studio.git
  cd agent-studio
  ```

##### 2.2. Generate an AES Key (Optional)

* If you do not need to encrypt sensitive fields at rest, skip this step.
* In the project root, open GitBash and run:

  ```bash
  cd scripts
  bash build_AES_master_key.sh
  ```

* When the script finishes, it will print the key. Use it as needed. It’s recommended to set it as an environment variable and store it separately.

  ```bash
  # If your installation/deployment is executed in Git Bash
  export SERVER_AES_MASTER_KEY_ENV=your_aes_key
    
  # If your installation/deployment is executed in PowerShell
  # Method 1: Set a temporary environment variable in PowerShell
  $env:SERVER_AES_MASTER_KEY_ENV="your_aes_key"
  # Method 2: Add it as a Windows system environment variable
  """
    1. Press Win + R, type sysdm.cpl, and press Enter.
    2. Click on the 'Advanced' tab, then click 'Environment Variables'.
    3. Under 'System variables' or 'User variables', add:
         Variable name: SERVER_AES_MASTER_KEY_ENV
         Variable value: your_aes_key
  """
  ```

* **Note**: The AES key must remain unchanged. Changing it later will make previously encrypted data impossible to decrypt.

##### 2.3. Start openJiuwen

* Open PowerShell in the project root.

* Copy the .env file:

  ```bash
  copy .env.example .env
  ```

* Open .env in a text editor and update the following variables according to your environment (do not overwrite other variables):

  > **Note**: Replace DB_HOST, DB_PORT, etc. with your actual database information. DB_USER and DB_PASSWORD are the MySQL user and password you created above. If the password contains special characters, see the [Special Character Escape Table](#windows-special-char) to replace them with URL encoding.

  ```env
   # Database config (example)
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

   For variable descriptions, please refer to the table below. If you choose to enable the memory function for Milvus, please refer to [How to Enable the Memory and Knowledge Base Functions](#windows-memory). If you choose to enable the memory function for Chroma, you only need to obtain the vector model. For details, please refer to [How to Obtain the Vector Model](#windows-embed-model).
 
   | Variable Name             | Description                                                         | Example                                                                       |
   |---------------------------|---------------------------------------------------------------------|--------------------------------------------------------------------------------|
   | **DB_HOST**                 | Database host                                                       | `localhost`                                                                    |
   | **DB_PORT**                   | Database port                                                       | `3306`                                                                         |
   | **DB_USER**                   | Database username                                                   | `your_user_name`                                                               |
   | **DB_PASSWORD**               | Database password                                                   | `your_password`                                                                |
   | **INDEX_MANAGER_TYPE**        | Vector database type; optional values: chroma, milvus; default: chroma | `chroma`                              |
   | **MEMORY_DATA_PATH**          | Memory data storage path, default value: memory-data              | `memory-data`                         |
   | **MILVUS_HOST**               | Milvus service host                                                 | `127.0.0.1`                                                                    |
   | **MILVUS_PORT**               | Milvus service port                                                 | `19530`                                                                        |
   | **MILVUS_COLLECTION_NAME**    | Milvus collection name                                              | `memory_vector`                                                                |
   | **CODE_SANDBOX_URL**             | Code Sandbox url                                            | `http://localhost:8188/run`                                                                    |
   | **VITE_PLUGIN_SERVICE_URL**      | Plugin Server url                                           | `http://localhost:8185`                                                                    |
   | **VITE_PLUGIN_CONFIG_PATH**      | Plugin configuration file path for web                      | `/config.json`                                                                    |

* In the project root, open PowerShell and run the following to start the backend. Please wait patiently:

  ```bash
  cd backend
  uv venv
  uv sync
  ```

* Execute database version stamp commands to facilitate subsequent database operations:
  ```bash
  # Agent database
  alembic -n alembic_mysql_agent stamp head
  alembic -n alembic_mysql_ops stamp head

  # SQLite database
  alembic -n alembic_sqlite_agent stamp head
  alembic -n alembic_sqlite_ops stamp head
  ```

  > Description: The above commands are used to mark that the current database is already the latest version, facilitating subsequent database operations. Need to be executed separately for agent and ops databases. If using MySQL, execute `alembic -n alembic_mysql_agent stamp head` and `alembic -n alembic_mysql_ops stamp head`. For alembic usage methods, refer to [DATABASE_MIGRATION_DEVELOPMENT_GUIDE.md](../../../../backend/DATABASE_MIGRATION_DEVELOPMENT_GUIDE_EN.md)

  > **Note**: If it hangs for more than 20 minutes, press Ctrl + C, then try editing the url of [[tool.uv.index]] in pyproject.toml to another available mirror, and re-run uv sync.

  > **Note**: If uv sync fails, try: `uv sync --native-tls` to force using the system native TLS library (fix HTTPS download compatibility issues).

* Create log directory and start backend service
  ```bash
  mkdir logs
  mkdir logs\run

  # Enter the virtual environment. If using Command Prompt, run: .venv\Scripts\activate
  .\.venv\Scripts\Activate.ps1

  # Start
  python main.py
  ```

  When startup succeeds, you will see "Application startup complete".

  > **Tip**: If you need to enable code node or code plugin tool that require the code sandbox service, refer to [How to Enable the Sandbox Feature](#windows-sandbox) to complete the sandbox setup. And if you need to enable plugins that require the plugin server, which refer to [How to Enable the Plugin Server](#windows-plugin).

* Open another PowerShell in the project root and install frontend dependencies:

  ```bash
  cd frontend
  npm install
  ```
  > **Note**: The vulnerability notices shown are known npm advisories and do not affect subsequent operation.

  ![image](../images/npm-error.png)

* Start the frontend:

  ```
  npm run dev
  ```

* On success, it will print Local access: *access URL*.

##### 2.4. Access the System

Copy the *access URL* from above into your browser’s address bar and press Enter. You should see the openJiuwen UI.

## III. Frequently Asked Questions (FAQ)

### <a id="windows-memory"></a> Question 1: How to Enable the Memory and Knowledge Base Features

The effectiveness of memory feature depends on the scale of the LLM used.

The memory and knowledge base function supports two vector databases: Chroma and Milvus. If Milvus is chosen, Docker is recommended for installation on Windows systems. Specific installation steps are provided below.

#### 1. Install Docker Desktop
It is recommended to use WSL 2 (Windows Subsystem for Linux 2) as the virtualization backend when running Docker Desktop on Windows. Compared with LinuxKit, it offers better compatibility and lower resource consumption, and can avoid the known zombie container bugs.

**1.1 Enable WSL 2**

For eligible Windows systems (Windows 10 version 2004 or later <Build 19041 or higher> or Windows 11), simply running the command `wsl --install` allows one-click configuration, download, and installation of the default Linux distribution.

* Press Windows + S and type PowerShell to search.

* In the search results, right-click Windows PowerShell and select Run as administrator.

* Run the following command in PowerShell, then restart your computer.

  ```
  wsl --install
  ```

Older Windows versions do not support the full automation of this one-click command and may require additional manual steps. For detailed instructions, refer to the official documentation: <a href="https://learn.microsoft.com/en-us/windows/wsl/install" target="_blank" rel="nofollow noopener noreferrer">Install Linux on Windows with WSL</a>.

**1.2 Install Docker Desktop**

* Download: Go to the <a href="https://www.docker.com/products/docker-desktop/" target="_blank" rel="nofollow noopener noreferrer">Docker website</a> to download the Windows installer (for x86 machines, choose the AMD64 version);
* Run the installer: Select only the “Use WSL 2 instead of Hyper-V” and “Add shortcut to desktop” options, then click “OK” to complete installation;

* Restart your computer after installation;
* After restarting, open Docker Desktop and wait for it to finish loading (the first launch may take 5–10 minutes);
* Once Docker Desktop starts, for a trial you can click “Continue without signing in” on the welcome screen; for long-term use, refer to the <a href="https://docs.docker.com/desktop/setup/sign-in" target="_blank" rel="nofollow noopener noreferrer">official guide</a>.

* Docker Desktop installation is now complete.

> Note: If you encounter errors during installation, refer to the <a href="https://docs.docker.com/desktop/setup/install/windows-install/" target="_blank" rel="nofollow noopener noreferrer">Docker Desktop official installation guide</a>.

#### 2. Start Milvus

* Create a local Milvus directory (it’s recommended to place it on D:, e.g., *D:\Milvus*).

* Open Docker Desktop and click the ⚙️ icon in the upper-right corner to open settings. 
 	  	 
* In the left-hand sidebar, select “Resources“ to enter the Resources configuration page. 
 	  	 
* Click “File sharing“, type the *Milvus installation directory* (e.g., `D:\Milvus*`) into the text box, and then click the “➕“ button to add it.

* Click Apply & restart to restart Docker Desktop.

* Open PowerShell as Administrator, switch to the Milvus directory, and save the “standalone.bat” script:

  ```bash
  cd D:\Milvus # “D:\Milvus” is your Milvus local directory

  Invoke-WebRequest https://raw.githubusercontent.com/milvus-io/milvus/refs/heads/master/scripts/standalone_embed.bat -OutFile standalone.bat
  ```

* In PowerShell, pull the image:

  ```bash
  # x86 architecture
  docker pull swr.cn-north-4.myhuaweicloud.com/openjiuwen/milvusdb/milvus-amd64:v2.6.2
  ```

  ```bash
  # arm architecture
  docker pull swr.cn-north-4.myhuaweicloud.com/openjiuwen/milvusdb/milvus-arm64:v2.6.2
  ```

* In “standalone.bat”, replace the official milvus image name (e.g., `milvusdb/milvus:v2.6.7`) with the corresponding mirror image (for x86 machines: `swr.cn-north-4.myhuaweicloud.com/openjiuwen/milvusdb/milvus-amd64:v2.6.2`).
  
* After editing, run standalone.bat in PowerShell to start Milvus as a Docker container:

  ```
  ./standalone.bat start
  ```

* After startup, run `docker ps -a` to confirm a container named Milvus-standalone is running on port 19530.

  > **Note**: If issues arise during deployment, refer to the <a href="https://milvus.io/docs/zh/install_standalone-windows.md" target="_blank" rel="nofollow noopener noreferrer">Milvus official guide</a>.

* To stop Milvus, run:

  ```
  ./standalone.bat stop
  ```

* If the following error message appears when using memory or knowledge base after startup:
    ```text
    ""Milvus connection failed: <MilvusException: (code=2, message=Fail connecting to server on milvus-standalone:19530, illegal connection params or server unavailable)>"
    ```
    You need to modify the MILVUS_HOST configuration in the .env file to match the IP address used to start the Milvus service.

<a id="windows-embed-model"></a>
#### 3. Obtain the embedding model

The memory and knowledge base features require an embedding model. The steps below use Huawei Cloud as an example.

* Click <a href="https://console.huaweicloud.com/modelarts/?locale=zh-cn&region=cn-southwest-2#/model-studio/square" target="_blank" rel="nofollow noopener noreferrer">this link</a> to open the ModelArts Model Square. 

* To experience the memory feature and knowledge base feature, please click on "向量模型" (Embedding model) and select a vector model according to your needs. The following content uses BGE-M3 as an example.

  ![Find the embedding model](../images/find_embed.png)

* After locating the suitable model, click "推理调用" (Inference Call) to enter the model information acquisition page.

  ![Get api_base and model_name](../images/embed_api_base_and_model_name.png)

* Record the API endpoint and the model parameter.

* Click “API Key Management” and follow the instructions to obtain an API.

### <a id="windows-sandbox"></a> Question 2: How to enable the sandbox feature

If you need to enable code node or code plugin tool, the sandbox service is required, do the following:

1. Refer to `sandbox_server/python_server/.env.example`, and create a `.env` file under `sandbox_server/python_server`, for example:

   ```env
   HOST=0.0.0.0
   PORT=5001
   ```

   Then start the Python sandbox service by running the `sandbox_server/python_server/openjiuwen_sandbox_pyserver/kernel.py` script. `HOST` and `PORT` are the IP and port for the Python sandbox service.

2. Start the JS sandbox service by running the `sandbox_server/js_server/kernel.js` script. The IP and port can be set as follows:

   ```javascript
   const PORT = process.env.PORT || 5002;
   server.listen(PORT, "0.0.0.0", () => {
     console.log(`✅ JS sandbox listening on http://0.0.0.0:${PORT}`);
   });
   ```

3. Refer to `sandbox_server/gateway/.env.example`, and create a `.env` file under `sandbox_server/gateway`, for example:

   ```env
   HOST=0.0.0.0
   PORT=8188
   PYTHON_SANDBOX_URL=http://localhost:5001/run
   JS_SANDBOX_URL=http://localhost:5002/run
   ```

   `PYTHON_SANDBOX_URL` and `JS_SANDBOX_URL` should point to the Python and JS sandbox services you started earlier. Then start the sandbox gateway service by running the `sandbox_server/gateway/openjiuwen_sandbox_gateway/server.py` script.

4. After running the sandbox service, please configure sandbox's url in `.env`, such as: `CODE_SANDBOX_URL=http://localhost:8188/run`.

### <a id="windows-plugin"></a> Question 3: How to Enable the Plugin Server

If you need plugins, the plugin server is required, please do the following:

1. Refer to `plugin_server/openjiuwen_plugin_server` files, create plugin services as you need. Then start the plugin server by running the script `plugin_server/openjiuwen_plugin_server/run_restful.py`.

2. After running the plugin server, please configure plugin server's url in `.env`, such as: `VITE_PLUGIN_SERVICE_URL=http://localhost:8185`.

### <a id="windows-special-char"></a> Question 4: Special character escape table

| Character | URL Encoding | Character | URL Encoding | Character | URL Encoding | Character | URL Encoding | Character | URL Encoding |
|-----------|--------------|-----------|--------------|-----------|--------------|-----------|--------------|-----------|--------------|
| Space     | %20          | "         | %22          | #         | %23          | %         | %25          | &         | %26          |
| (         | %28          | )         | %29          | +         | %2B          | ,         | %2C          | /         | %2F          |
| :         | %3A          | ;         | %3B          | <         | %3C          | =         | %3D          | >         | %3E          |
| ?         | %3F          | @         | %40          | \         | %5C          | \|        | %7C          | -         | -            |

### Question 5: Why does local installation default to HTTP instead of HTTPS?

In local installation mode, the system defaults to HTTP for communication. This design choice is primarily based on the fact that local environments are typically used for development and testing, and avoiding mandatory TLS certificate setup helps reduce the initial usage barrier.

By contrast, the Docker installation method comes with built-in HTTPS support, allowing users to use secure communication out of the box without additional configuration.

If HTTPS is required in a local environment, developers must manually generate and configure TLS certificates according to their deployment needs.
