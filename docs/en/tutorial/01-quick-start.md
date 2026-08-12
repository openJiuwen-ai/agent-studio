# Local Development Quick Start

This guide is for developers new to AgentStudio development, explaining how to start the complete development environment via containers or local processes, and how to incrementally build, deploy, and debug after modifying a single service.

## 1. Services and Source Directories

The complete environment contains four application services:

| Service | Source directory | Default port | Main responsibilities |
|---|---|---:|---|
| `studio-console` | `frontend/` | 80 | Angular frontend and API reverse proxy |
| `studio-manager` | `backend/studio-manager*` | 31111 | Agent, knowledge base, model, tool, and MCP management |
| `studio-runtime` | `agent-runtime/` | 31014 | Agent/workflow execution, published calls, LLM, MCP, and memory runtime |
| `studio-builder` | `agent_builder/` | 31015 | NL2, Prompt, and model tuning |

> The original Java `studio-service` has been removed; its management agent, execution, and build capabilities have been split into Manager, Runtime, and Builder respectively.

## 2. Requirements

| Tool | Recommended version |
|---|---|
| JDK | 17 |
| Maven | 3.8.8+ |
| Node.js | 22.13+ (consistent with CI) |
| npm | 9+ |
| pnpm | 10 (explicitly activated via Corepack, not using auto-selected latest) |
| Python | 3.11 (current dependency set does not support 3.14) |
| Docker | 20+ |
| Docker Compose | V2, or compatible `docker-compose` |
| Bash | 4+ |

The complete container environment also starts MySQL, Redis, and MinIO. Prepare at least 8 CPU cores, 20 GiB memory, and 50 GiB available disk; with insufficient resources, you can lower service resource limits in Compose, but build and startup speed will be affected.

Check environment:

```bash
java -version
mvn -version
node --version
npm --version
docker --version
docker compose version || docker-compose version
```

## 3. First-Time Complete Environment Startup

All commands below are executed in the project root directory.

### 1. Prepare Deployment Configuration

```bash
cp deploy/.env.template deploy/.env
```

The default configuration uses built-in MySQL, Redis, and MinIO. If ports, passwords, or image repositories need adjustment, modify `deploy/.env` before building and deploying.

### 2. Compile Source and Prepare Docker Artifacts

```bash
bash docker/package.sh
```

This step compiles the Java backend and Angular frontend, and copies the source code needed by runtime into the Docker build context. The current `package.sh` does not support per-service compilation.

### 3. Build Local Images

```bash
bash docker/build.sh
```

Without arguments, builds the complete image set and generates `docker/.last-build.env`. This file records the image names, versions, and architecture of this actual build.

### 4. Deploy This Local Build

```bash
bash deploy/deploy.sh local
```

The first deployment starts both built-in infrastructure and four application services. After completion, access:

```text
http://localhost/openjiuwen/
```

Check status and health endpoints:

```bash
bash deploy/deploy.sh status
bash deploy/deploy.sh verify
```

## 4. Single-Service Incremental Development

`docker/build.sh` supports selective image building; `deploy.sh local <service>` only recreates the specified container, keeping other containers unchanged via `--no-deps`.

### Modify studio-runtime

```bash
bash docker/package.sh
bash docker/build.sh runtime
bash deploy/deploy.sh local studio-runtime
```

### Modify studio-builder

Builder build copies `agent_builder/` and shared packages directly from the repository; no need to run `package.sh` first:

```bash
bash docker/build.sh builder
bash deploy/deploy.sh local studio-builder
```

### Modify studio-manager

```bash
bash docker/package.sh
bash docker/build.sh manager
bash deploy/deploy.sh local studio-manager
```

### Modify studio-console

```bash
bash docker/package.sh
bash docker/build.sh console
bash deploy/deploy.sh local studio-console
```

### Modify Multiple Services Simultaneously

```bash
bash docker/build.sh runtime builder
bash deploy/deploy.sh local studio-runtime studio-builder
```

## 5. Understanding `.last-build.env`

`docker/.last-build.env` only records the images actually built by the most recent `docker/build.sh`. Selective builds overwrite the previous manifest.

For example:

```bash
bash docker/build.sh runtime builder
cat docker/.last-build.env
```

The manifest will only contain runtime and builder. At this point, you should execute:

```bash
bash deploy/deploy.sh local studio-runtime studio-builder
```

You cannot execute `bash deploy/deploy.sh local` without arguments, because no arguments means deploying all four application services, but the manifest does not include the other two services.

## 6. Frontend Hot-Reload Development

First start the backend containers per Section 3, then run in another terminal:

```bash
cd frontend
pnpm install --ignore-scripts
pnpm exec ng serve --configuration development
```

The Angular dev server listens on `4200` by default; `.staging/proxy.json` connects to the host's manager `31111` and runtime `31014` ports by default. Access `http://localhost:4200/` to use frontend hot reload; no need to stop `studio-console` in Compose — they listen on different ports.

## 7. Starting All Application Services via Local Processes

This approach only uses containers for MySQL, Redis, and MinIO; the four application services start directly from source, suitable for breakpoint debugging and frequent code changes, without building application images.

### 1. Start Infrastructure Containers

For first-time use, prepare the deployment config, then start only infrastructure:

```bash
cp deploy/.env.template deploy/.env
bash deploy/deploy.sh infra
```

If `deploy/.env` already exists, do not overwrite it again. Infrastructure defaults: MySQL `3306`, Redis `6379`, MinIO API `9000`, MinIO Console `9001`.

### 2. Prepare Local Process Environment Variables

Containers use Compose DNS names like `mysql`, `redis`, `minio`; local processes must use `127.0.0.1` instead. Create a personal-use `.vscode/local-dev.env` (`.vscode/` is Git-ignored):

```bash
mkdir -p .vscode
cat > .vscode/local-dev.env <<'EOF'
# Java datasource; also export lowercase vars to match existing Spring placeholders
export SPRING_DATASOURCE_URL='jdbc:mariadb://127.0.0.1:3306/agent-builder?allowMultiQueries=true&useUnicode=true&characterEncoding=UTF-8&autoReconnect=true&allowPublicKeyRetrieval=true'
export SPRING_DATASOURCE_USERNAME=root
export SPRING_DATASOURCE_PASSWORD=123456
export spring_datasource_url='jdbc:mariadb://127.0.0.1:3306/agent-builder?allowMultiQueries=true&useUnicode=true&characterEncoding=UTF-8&autoReconnect=true&allowPublicKeyRetrieval=true'
export spring_datasource_username=root
export spring_datasource_password=123456

export REDIS_HOST=127.0.0.1
export REDIS_PORT=6379
export REDIS_PASSWORD=
export REDIS_MODE=single
export REDIS_DATABASE=0
export redis_host=127.0.0.1
export redis_port=6379
export redis_password=

export OBS_URL=http://127.0.0.1:9000
export OBS_BUCKET=agent-builder
export OBS_AK=minioadmin
export OBS_SK=minioadmin
export obs_url=http://127.0.0.1:9000
export obs_bucket=agent-builder
export obs_ak=minioadmin
export obs_sk=minioadmin
export DATASOURCE_OBS_SERVER=http://127.0.0.1:9000
export DATASOURCE_OBS_BUCKET=agent-builder
export DATASOURCE_OBS_AK=minioadmin
export DATASOURCE_OBS_SK=minioadmin
export DATASOURCE_OBS_ENABLE_SSL=false
export DATASOURCE_OBS_PATH_STYLE=path

export STORE_DB_TYPE=mysql
export STORE_DB_HOST=127.0.0.1
export STORE_DB_PORT=3306
export STORE_DB_USER=root
export STORE_DB_PASSWORD=123456
export STORE_DB_DATABASE=agent-builder
export STORE_DB_SSLMODE=disable

export AGENT_RUNTIME_ENDPOINT=http://127.0.0.1:31014
export USER_AUTH_ENDPOINT=http://127.0.0.1:31111
export AGENT_MANAGER_ENDPOINT=http://127.0.0.1:31111
export AGENT_BUILDER_ENDPOINT=http://127.0.0.1:31015
export agent_runtime_endpoint=http://127.0.0.1:31014
export user_auth_endpoint=http://127.0.0.1:31111
export agent_manager_endpoint=http://127.0.0.1:31111
export agent_builder_endpoint=http://127.0.0.1:31015

# Use single worker for local debugging, easier breakpoint hits
export GUNICORN_WORK_NUM=1
EOF

source .vscode/local-dev.env
```

`.vscode/local-dev.env` contains local passwords and should not be committed to Git. If you modify database, Redis, or MinIO config in `deploy/.env`, you must also sync changes here.

VSCode/TRAE's `envFile` uses standard dotenv format and does not accept Shell's `export` keyword. Generate an IDE-specific file from the same config:

```bash
source .vscode/local-dev.env
for name in $(sed -n 's/^export \([A-Za-z_][A-Za-z0-9_]*\)=.*/\1/p' .vscode/local-dev.env); do
    printf '%s=%s\n' "$name" "${!name}"
done > .vscode/local-dev.ide.env
chmod 600 .vscode/local-dev.ide.env
```

After modifying `.vscode/local-dev.env`, re-run this command to keep CLI and IDE configs consistent. The generation process first expands `$VAR` references via Shell, then writes the final values that the IDE can directly read.

The Manager container pre-creates `/opt/cloud/studio-manager/logs`; local processes don't have this directory. Create a console-only `.vscode/log4j2-local.xml` to avoid local development depending on container directories:

```bash
cat > .vscode/log4j2-local.xml <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<Configuration status="WARN">
    <Appenders>
        <Console name="STDOUT" target="SYSTEM_OUT">
            <PatternLayout pattern="[%d{yyyy-MM-dd HH:mm:ss.SSS}] [%-5level] [%thread] [%logger{36}] - %msg%n"/>
        </Console>
    </Appenders>
    <Loggers>
        <Root level="INFO">
            <AppenderRef ref="STDOUT"/>
        </Root>
    </Loggers>
</Configuration>
EOF
```

### 3. Install Source Dependencies First Time

Java dependencies and local modules:

```bash
cd backend
mvn clean install -Dmaven.test.skip=true
cd ..
```

You must use `-Dmaven.test.skip=true` here. `-DskipTests` only skips test execution but still runs `testCompile`; if test sources have temporary compilation issues, local dependency installation will still fail.

Python runtime and builder can share a virtual environment:

```bash
# Must confirm this outputs Python 3.11.x; do not use unconstrained python3
python3.11 --version
python3.11 -m venv .venv

# Linux & macOS activation
source .venv/bin/activate
# Windows activation
source .venv/Scripts/activate

python --version
python -m pip install --upgrade pip
python -m pip install -r agent-runtime/requirements.txt
python -m pip install -r agent_builder/requirements.txt
```

If the OS doesn't provide `python3.11` (e.g. system default is Python 3.14), you can use `uv` to install and manage a standalone Python 3.11 without replacing system Python:

```bash
# Install uv; can also be pre-installed per team convention
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv --version

# If you accidentally created .venv with another Python, --clear recreates the environment;
# --seed installs pip, setuptools, and wheel
deactivate 2>/dev/null || true
uv python install 3.11
uv venv --python 3.11 --clear --seed .venv
source .venv/bin/activate
python --version
python -m pip --version

python -m pip install --upgrade pip
python -m pip install -r agent-runtime/requirements.txt
python -m pip install -r agent_builder/requirements.txt
```

Expect `python --version` to output `Python 3.11.x`, and `python -m pip --version`'s path to be in the project's `.venv`. `uv venv` does not install pip by default, so `--seed` cannot be omitted; also do not use system `pip` or `--break-system-packages`. Do not install `pg_config` separately just to compile `psycopg2-binary` from source for Python 3.14: even if this one is resolved, other pinned dependencies may not have Python 3.14 wheels or may not yet be compatible.

Frontend dependencies:

```bash
# Must first confirm Node.js version; Node.js 20 cannot run the pnpm 11 downloaded by current Corepack
node --version

cd frontend
corepack enable
corepack prepare pnpm@10 --activate
pnpm --version
pnpm install --ignore-scripts
cd ..
```

Expect `node --version` to be at least `v22.13.0`, `pnpm --version` to output `10.x`. If the system still has Node.js 20, use `nvm` to install Node.js 22 without overwriting system Node.js:

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.5/install.sh | bash
source "$HOME/.nvm/nvm.sh"
nvm install 22
nvm use 22

node --version
corepack enable
corepack prepare pnpm@10 --activate
pnpm --version
```

If the terminal reverts to system Node.js after reopening, run `source "$HOME/.nvm/nvm.sh" && nvm use 22`. Do not continue using Corepack auto-downloaded pnpm 11 under Node.js 20.

### 4. Start via Command Line

Open four terminals; in each, first enter the project root and run `source .vscode/local-dev.env`. Python terminals must also run `source .venv/bin/activate`.

Terminal 1, start manager:

```bash
source .vscode/local-dev.env
cd backend

# Build manager and its dependency modules in the Maven reactor
mvn -pl studio-manager -am package -Dmaven.test.skip=true

# target/lib corresponds to dependencies copied alongside the main JAR in the Docker image; other params match the container startup script
java -Dloader.path=studio-manager/target/lib \
  -Dlog4j.configurationFile=../.vscode/log4j2-local.xml \
  -jar studio-manager/target/studio-manager-*.jar \
  --spring.config.additional-location=file:$PWD/studio-manager-service/src/main/resources/ \
  --spring.profiles.active=manager
```

You cannot directly use `mvn -pl studio-manager spring-boot:run` in this project. After sub-module dependencies are installed to `~/.m2`, their POMs still retain the parent version `${revision}`; resolving outside the reactor would erroneously look for `com.openjiuwen:studio:${revision}`. `-am package` keeps related modules in the same reactor, then uses `loader.path` to load Maven-copied external dependencies, equivalent to Docker's `app/` artifact layout.

Terminal 2, start Python runtime:

```bash
source .vscode/local-dev.env
source .venv/bin/activate
export PYTHONPATH="$PWD/agent-runtime:$PWD/agent-runtime/agent_runtime:$PWD/packages/storage:$PWD/packages/model_service:$PWD/packages/common_utils"
cd agent-runtime
python -m agent_runtime.EIStart --host 0.0.0.0 --port 31014
```

Terminal 3, start builder:

```bash
source .vscode/local-dev.env
source .venv/bin/activate
export PYTHONPATH="$PWD:$PWD/packages/model_service:$PWD/packages/storage:$PWD/packages/common_utils"
python -m agent_builder.EIBuilder --host 0.0.0.0 --port 31015
```

Terminal 4, start frontend dev server:

```bash
cd frontend
pnpm exec ng serve --configuration development
```

Access `http://localhost:4200/`. Recommended startup order: "infrastructure → manager → runtime → builder → frontend"; after each backend service is ready, check:

```bash
curl -f http://127.0.0.1:31111/health
curl -f http://127.0.0.1:31014/v1/health
curl -f http://127.0.0.1:31015/v1/health
```

## 8. Starting and Debugging via VSCode or TRAE

Both VSCode and TRAE can read the workspace's `.vscode/launch.json`. Before starting with IDE, in addition to completing JDK, Maven, Python, and Node.js dependency installation from Section 7, you also need to install the corresponding debug extensions in the IDE you're using. Having `java` and `mvn` installed on the system does not mean the IDE already supports `"type": "java"` in `.vscode/launch.json`.

Recommended extensions:

| Purpose | Extension name | Extension ID | Required? |
| --- | --- | --- | --- |
| Java language support | Language Support for Java(TM) by Red Hat | `redhat.java` | Required for Java debugging |
| Java debugging | Debugger for Java | `vscjava.vscode-java-debug` | Required for Java debugging |
| Maven project support | Maven for Java | `vscjava.vscode-maven` | Recommended |
| Python language support | Python | `ms-python.python` | Required for Python debugging |
| Python debugging | Python Debugger | `ms-python.debugpy` | Required for Python debugging |

You can also directly install `Extension Pack for Java` (extension ID: `vscjava.vscode-java-pack`), which includes Java language, debugging, and Maven common extensions. Frontend JavaScript/TypeScript debugging is typically built into VSCode/TRAE, no extra installation needed.

> `Java Platform Extension for Visual Studio Code` (extension ID: `oracle.oracle-java`) cannot replace the `Debugger for Java` required by this project's `launch.json`. If only this extension is installed, pressing F5 may still show "Configured type `java` is not supported". In this case, install `redhat.java` and `vscjava.vscode-java-debug`; if the two Java language services conflict, disable `oracle.oracle-java` in the current workspace.

After installation, run "Developer: Reload Window", then open "Run and Debug" and press F5. When installing via command line, use the IDE command that actually launches the project, e.g.:

```bash
# VSCode: install Java extension pack and Python debug extensions
code --install-extension vscjava.vscode-java-pack
code --install-extension ms-python.python
code --install-extension ms-python.debugpy

# TRAE CN: use the same extension IDs when commands are available
trae-cn --install-extension redhat.java
trae-cn --install-extension vscjava.vscode-java-debug
trae-cn --install-extension vscjava.vscode-maven
trae-cn --install-extension ms-python.python
trae-cn --install-extension ms-python.debugpy
```

Extensions are installed in each IDE's independent extension directory. Having installed in VSCode does not mean they're also installed in TRAE/TRAE-CN; please confirm extensions are enabled in the IDE you use to open this project.

After confirming `.vscode/local-dev.ide.env` has been generated, you can open the IDE from the desktop icon or via command:

```bash
# Open project with VSCode
code .
# With TRAE
trae .
# Or TRAE CN
trae-cn .
```

Create `.vscode/launch.json` locally:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "type": "java",
      "name": "Local: studio-manager",
      "request": "launch",
      "mainClass": "com.openjiuwen.studio.agent.manager.Application",
      "cwd": "${workspaceFolder}/backend",
      "envFile": "${workspaceFolder}/.vscode/local-dev.ide.env",
      "vmArgs": "-Dlog4j.configurationFile=${workspaceFolder}/.vscode/log4j2-local.xml",
      "args": "--spring.config.additional-location=file:${workspaceFolder}/backend/studio-manager-service/src/main/resources/ --spring.profiles.active=manager"
    },
    {
      "type": "debugpy",
      "name": "Local: studio-runtime",
      "request": "launch",
      "module": "agent_runtime.EIStart",
      "cwd": "${workspaceFolder}/agent-runtime",
      "python": "${workspaceFolder}/.venv/bin/python",
      "envFile": "${workspaceFolder}/.vscode/local-dev.ide.env",
      "args": ["--host", "0.0.0.0", "--port", "31014"],
      "env": {
        "PYTHONPATH": "${workspaceFolder}/agent-runtime:${workspaceFolder}/agent-runtime/agent_runtime:${workspaceFolder}/packages/storage:${workspaceFolder}/packages/model_service:${workspaceFolder}/packages/common_utils"
      }
    },
    {
      "type": "debugpy",
      "name": "Local: studio-builder",
      "request": "launch",
      "module": "agent_builder.EIBuilder",
      "cwd": "${workspaceFolder}",
      "python": "${workspaceFolder}/.venv/bin/python",
      "envFile": "${workspaceFolder}/.vscode/local-dev.ide.env",
      "args": ["--host", "0.0.0.0", "--port", "31015"],
      "env": {
        "PYTHONPATH": "${workspaceFolder}:${workspaceFolder}/packages/model_service:${workspaceFolder}/packages/storage:${workspaceFolder}/packages/common_utils"
      }
    }
  ],
  "compounds": [
    {
      "name": "Local: Start All Backends",
      "configurations": [
        "Local: studio-manager",
        "Local: studio-runtime",
        "Local: studio-builder"
      ],
      "stopAll": true
    }
  ]
}
```

Then in "Run and Debug", select a single service or choose "Local: Start All Backends". Frontend is recommended to run in the IDE's integrated terminal:

```bash
cd frontend
pnpm exec ng serve --configuration development
```

`.vscode/` is currently personal IDE config and Git-ignored; the above files won't be committed. All four configs load `.vscode/local-dev.ide.env` directly via `envFile`, so you can open VSCode/TRAE from the desktop icon without requiring the IDE to inherit the terminal environment. If environment config changes, regenerate the IDE env file before starting debugging.

## 9. Common Troubleshooting Commands

```bash
# View service status
bash deploy/deploy.sh status

# View specific service logs
bash deploy/deploy.sh logs studio-builder
docker compose -f deploy/docker-compose.yml --env-file deploy/.env logs -f studio-builder

# Verify HTTP health endpoints
bash deploy/deploy.sh verify

# Stop all services and retain data volumes
bash deploy/deploy.sh stop
```

Common issues:

- Image not in the most recent local build: build that service first, then explicitly deploy with `local <service>`.
- `studio-builder` startup failure: check Redis, `STORE_DB_*`, OBS/MinIO, and `MODEL_CONFIG_STRATEGY` config.
- Port conflicts: check `80`, `31111`, `31014`, `31015`, `3306`, `6379`, and `9000-9001`.
- Docker build base image pull failure: first confirm Docker daemon's proxy or mirror accelerator config, not just the current Shell's network.
- Local processes still trying to connect to `mysql`, `redis`, or `minio`: `.vscode/local-dev.env` not loaded, or still using Compose container DNS names.
- IDE starts fine but API calls fail: confirm `.vscode/local-dev.ide.env` is generated and content doesn't contain unexpanded references like `$OBS_URL`, then check Manager, Runtime, and Builder health endpoints.

## 10. Further Reading

- [Build from Source](../../docker/源码编译构建指导.md)
- [Deployment Guide](../how-to/deploy-service.md)
- [Observability Guide](../../deploy/config/observability-readme.md)
- [Development Extension Guide](../how-to/development-guide.md)
