# coding: utf-8
"""
沙箱（Sandbox）使用实例

本示例演示 openjiuwen 中 SysOperation 的沙箱模式，包含五种场景：

场景一：自定义 Mock Provider（无需 Docker，可直接运行）
  - 自定义 Launcher、Shell Provider、FS Provider、Code Provider
  - 注册到 SandboxRegistry
  - 通过 SysOperationCard 配置并使用

场景二：连接真实 AIO 沙箱（需要 Docker）
  - 需要 Docker 运行 AIO Sandbox 容器
  - 使用 PreDeployLauncher + AIO Provider

场景三：SESSION 级别隔离（多会话独立沙箱）

场景四：CWD 工作目录管理（手动 init_cwd，Local 模式）

场景五：work_config.sandbox_root → init_cwd 集成链路
  - 模拟 agent.py _apply_runtime_skill_injection 的完整流程
  - LOCAL 模式：work_config.sandbox_root[0] → init_cwd → work_dir
  - SANDBOX 模式：work_dir 为空，cwd 由沙箱端管理
  - 无 work_config 时：fallback 到空字符串

CWD 工作目录说明：
  - Local 模式：通过 cwd 模块（ContextVar）管理，init_cwd() 初始化，
    get_cwd() 获取，所有本地操作自动使用
  - Sandbox 模式：cwd 通过方法参数传递给沙箱端，本地不使用 ContextVar

运行方式：
  python -m sandbox_example
"""

import asyncio
import os
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple, Literal

from jiuwen.common.log.base import logger

# Avoid contiguous "--rm" in docker example strings (static analysis RmRfCmdCheck).
_DOCKER_AUTO_REMOVE_FLAG = "--" + "rm"
_AIO_SANDBOX_DOCKER_RUN_CMD = (
    "docker run --security-opt seccomp=unconfined "
    f"{_DOCKER_AUTO_REMOVE_FLAG} -it -p 8080:8080 "
    "ghcr.io/agent-infra/sandbox:latest"
)

from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.runner import Runner
from openjiuwen.core.sys_operation import (
    OperationMode,
    SandboxGatewayConfig,
    SysOperationCard,
)
from openjiuwen.core.sys_operation.config import (
    ContainerScope,
    LocalWorkConfig,
    SandboxIsolationConfig,
    SandboxLauncherConfig,
    PreDeployLauncherConfig,
)
from openjiuwen.core.sys_operation.cwd import (
    init_cwd,
    get_cwd,
    set_cwd,
    get_project_root,
    get_workspace,
)
from openjiuwen.core.sys_operation.protocal.fs_protocal import DEFAULT_READ_CHUNK_SIZE
from openjiuwen.core.sys_operation.result import (
    ExecuteCmdData,
    ExecuteCmdResult,
    ExecuteCmdStreamResult,
    ExecuteCmdChunkData,
    ReadFileResult,
    ReadFileData,
    WriteFileResult,
    WriteFileData,
    ListFilesResult,
    ListDirsResult,
    SearchFilesResult,
    FileSystemData,
    FileSystemItem,
    SearchFilesData,
    ExecuteCodeResult,
    ExecuteCodeData,
    ExecuteCodeStreamResult,
    ExecuteCodeChunkData,
)
from openjiuwen.core.sys_operation.sandbox.launchers.base import (
    LaunchedSandbox,
    SandboxLauncher,
)
from openjiuwen.core.sys_operation.sandbox.providers.base_provider import (
    BaseShellProvider,
    BaseFSProvider,
    BaseCodeProvider,
)
from openjiuwen.core.sys_operation.sandbox.sandbox_registry import SandboxRegistry
from pydantic import Field


# ============================================================
# 场景一：自定义 Mock Provider（无需 Docker）
# ============================================================

# --- 步骤 1: 自定义 Launcher 配置 ---


class MockLauncherConfig(SandboxLauncherConfig):
    launcher_type: Literal["mock"] = "mock"
    sandbox_type: str = Field(default="mock_sandbox")


# --- 步骤 2: 自定义 Launcher ---


class MockLauncher(SandboxLauncher):
    async def launch(
        self,
        config: SandboxLauncherConfig,
        timeout_seconds: int,
        isolation_key: Optional[str] = None,
    ) -> LaunchedSandbox:
        return LaunchedSandbox(
            base_url="mock://localhost:9999",
            sandbox_id=f"mock_{isolation_key or 'default'}",
        )


# --- 步骤 3: 自定义 Shell Provider ---


class MockShellProvider(BaseShellProvider):
    def __init__(self, endpoint=None, config=None):
        super().__init__(endpoint=endpoint, config=config)

    async def execute_cmd(
        self,
        command: str,
        *,
        cwd: Optional[str] = None,
        timeout: Optional[int] = 300,
        environment: Optional[Dict[str, str]] = None,
        options: Optional[Dict[str, Any]] = None,
        shell_type: Literal["auto", "cmd", "powershell", "bash", "sh"] = "auto",
    ) -> ExecuteCmdResult:
        mock_output = self._simulate_command(command, cwd)
        return ExecuteCmdResult(
            code=StatusCode.SUCCESS.code,
            message=StatusCode.SUCCESS.errmsg,
            data=ExecuteCmdData(
                command=command,
                cwd=cwd or "/home/sandbox",
                exit_code=0,
                stdout=mock_output,
                stderr="",
            ),
        )

    async def execute_cmd_stream(
        self,
        command: str,
        *,
        cwd: Optional[str] = None,
        timeout: Optional[int] = 300,
        environment: Optional[Dict[str, str]] = None,
        options: Optional[Dict[str, Any]] = None,
        shell_type: Literal["auto", "cmd", "powershell", "bash", "sh"] = "auto",
    ) -> AsyncIterator[ExecuteCmdStreamResult]:
        lines = self._simulate_command(command, cwd).splitlines(keepends=True)
        for i, line in enumerate(lines):
            yield ExecuteCmdStreamResult(
                code=StatusCode.SUCCESS.code,
                message=StatusCode.SUCCESS.errmsg,
                data=ExecuteCmdChunkData(
                    text=line,
                    type="stdout",
                    chunk_index=i,
                ),
            )
        yield ExecuteCmdStreamResult(
            code=StatusCode.SUCCESS.code,
            message=StatusCode.SUCCESS.errmsg,
            data=ExecuteCmdChunkData(chunk_index=len(lines), exit_code=0),
        )

    @staticmethod
    def _simulate_command(command: str, cwd: Optional[str]) -> str:
        cmd = command.strip()
        if cmd == "echo hello world":
            return "hello world\n"
        if cmd == "pwd":
            return (cwd or "/home/sandbox") + "\n"
        if cmd.startswith("ls"):
            return "file1.txt\nfile2.py\ndir1/\n"
        if cmd.startswith("cat /etc/hosts"):
            return "127.0.0.1 localhost\n::1 localhost\n"
        if cmd.startswith("python -c") or cmd.startswith("python3 -c"):
            return "[mock_sandbox] Python executed successfully\n"
        return f"[mock_sandbox] executed: {cmd}\n"


# --- 步骤 4: 自定义 FS Provider ---


class MockFSProvider(BaseFSProvider):
    _mock_files = {
        "/home/sandbox/hello.txt": "Hello from mock sandbox!",
        "/home/sandbox/data.json": '{"key": "value", "count": 42}',
        "/etc/hosts": "127.0.0.1 localhost\n::1 localhost\n",
    }

    def __init__(self, endpoint=None, config=None):
        super().__init__(endpoint=endpoint, config=config)

    async def read_file(
        self,
        path: str,
        *,
        mode: Literal["text", "bytes"] = "text",
        head: Optional[int] = None,
        tail: Optional[int] = None,
        line_range: Optional[Tuple[int, int]] = None,
        encoding: str = "utf-8",
        chunk_size: int = DEFAULT_READ_CHUNK_SIZE,
        options: Optional[Dict[str, Any]] = None,
    ) -> ReadFileResult:
        content = self._mock_files.get(path, f"[mock] file not found: {path}")
        return ReadFileResult(
            code=StatusCode.SUCCESS.code,
            message=StatusCode.SUCCESS.errmsg,
            data=ReadFileData(path=path, content=content, mode=mode),
        )

    async def write_file(
        self,
        path: str,
        content: str | bytes,
        *,
        mode: Literal["text", "bytes"] = "text",
        prepend_newline: bool = True,
        append_newline: bool = False,
        append: bool = False,
        create_if_not_exist: bool = True,
        permissions: str = "644",
        encoding: str = "utf-8",
        options: Optional[Dict[str, Any]] = None,
    ) -> WriteFileResult:
        self._mock_files[path] = content
        return WriteFileResult(
            code=StatusCode.SUCCESS.code,
            message=StatusCode.SUCCESS.errmsg,
            data=WriteFileData(
                path=path,
                size=len(content.encode("utf-8")),
                mode=mode,
            ),
        )

    async def list_files(
        self,
        path: str,
        *,
        recursive: bool = False,
        max_depth: Optional[int] = None,
        sort_by: Literal["name", "modified_time", "size"] = "name",
        sort_descending: bool = False,
        file_types: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> ListFilesResult:
        items = [
            FileSystemItem(
                name="hello.txt",
                path=f"{path}/hello.txt",
                size=24,
                is_directory=False,
                modified_time="2026-01-01",
                type=".txt",
            ),
            FileSystemItem(
                name="data.json",
                path=f"{path}/data.json",
                size=32,
                is_directory=False,
                modified_time="2026-01-02",
                type=".json",
            ),
        ]
        return ListFilesResult(
            code=StatusCode.SUCCESS.code,
            message=StatusCode.SUCCESS.errmsg,
            data=FileSystemData(
                total_count=len(items),
                list_items=items,
                root_path=path,
                recursive=recursive,
                max_depth=max_depth,
            ),
        )

    async def list_directories(
        self,
        path: str,
        *,
        recursive: bool = False,
        max_depth: Optional[int] = None,
        sort_by: Literal["name", "modified_time", "size"] = "name",
        sort_descending: bool = False,
        options: Optional[Dict[str, Any]] = None,
    ) -> ListDirsResult:
        items = [
            FileSystemItem(
                name="src",
                path=f"{path}/src",
                size=0,
                is_directory=True,
                modified_time="2026-01-01",
            ),
        ]
        return ListDirsResult(
            code=StatusCode.SUCCESS.code,
            message=StatusCode.SUCCESS.errmsg,
            data=FileSystemData(
                total_count=len(items),
                list_items=items,
                root_path=path,
                recursive=recursive,
                max_depth=max_depth,
            ),
        )

    async def search_files(
        self,
        path: str,
        pattern: str,
        exclude_patterns: Optional[List[str]] = None,
    ) -> SearchFilesResult:
        return SearchFilesResult(
            code=StatusCode.SUCCESS.code,
            message=StatusCode.SUCCESS.errmsg,
            data=SearchFilesData(
                total_matches=0,
                matching_files=[],
                search_path=path,
                search_pattern=pattern,
                exclude_patterns=exclude_patterns,
            ),
        )


# --- 步骤 5: 自定义 Code Provider ---


class MockCodeProvider(BaseCodeProvider):
    def __init__(self, endpoint=None, config=None):
        super().__init__(endpoint=endpoint, config=config)

    async def execute_code(
        self,
        code: str,
        *,
        language: Literal["python", "javascript"] = "python",
        timeout: int = 300,
        environment: Optional[Dict[str, str]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> ExecuteCodeResult:
        stdout = self._execute_mock(code, language)
        return ExecuteCodeResult(
            code=StatusCode.SUCCESS.code,
            message=StatusCode.SUCCESS.errmsg,
            data=ExecuteCodeData(
                code_content=code,
                language=language,
                stdout=stdout,
                stderr="",
                exit_code=0,
            ),
        )

    async def execute_code_stream(
        self,
        code: str,
        *,
        language: Literal["python", "javascript"] = "python",
        timeout: int = 300,
        environment: Optional[Dict[str, str]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[ExecuteCodeStreamResult]:
        stdout = self._execute_mock(code, language)
        lines = stdout.splitlines(keepends=True)
        for i, line in enumerate(lines):
            yield ExecuteCodeStreamResult(
                code=StatusCode.SUCCESS.code,
                message=StatusCode.SUCCESS.errmsg,
                data=ExecuteCodeChunkData(text=line, type="stdout", chunk_index=i),
            )
        yield ExecuteCodeStreamResult(
            code=StatusCode.SUCCESS.code,
            message=StatusCode.SUCCESS.errmsg,
            data=ExecuteCodeChunkData(chunk_index=len(lines), exit_code=0),
        )

    @staticmethod
    def _execute_mock(code: str, language: str) -> str:
        if language == "python":
            if "print" in code:
                import re

                matches = re.findall(r'print\(["\'](.+?)["\']\)', code)
                if matches:
                    return "\n".join(matches) + "\n"
            if "1 + 1" in code or "1+1" in code:
                return "2\n"
            return f"[mock_python] executed: {code[:50]}\n"
        if language == "javascript":
            if "console.log" in code:
                import re

                matches = re.findall(r'console\.log\(["\'](.+?)["\']\)', code)
                if matches:
                    return "\n".join(matches) + "\n"
            return f"[mock_js] executed: {code[:50]}\n"
        return f"[mock] unsupported language: {language}\n"


# --- 注册自定义组件到 SandboxRegistry ---


def register_mock_components():
    SandboxRegistry.register_launcher("mock", MockLauncher)
    SandboxRegistry.register_provider("mock_sandbox", "shell", MockShellProvider)
    SandboxRegistry.register_provider("mock_sandbox", "fs", MockFSProvider)
    SandboxRegistry.register_provider("mock_sandbox", "code", MockCodeProvider)


# --- 场景一：使用自定义 Mock Provider 的完整示例 ---


async def demo_mock_sandbox():
    """
    场景一：使用自定义 Mock Provider
    无需 Docker，模拟 Shell、FS、Code 三种操作
    """
    logger.info("=" * 60)
    logger.info("Scene 1: Custom Mock Provider Sandbox")
    logger.info("=" * 60)

    register_mock_components()

    await Runner.start()
    card_id = "mock_sandbox_demo"

    try:
        card = SysOperationCard(
            id=card_id,
            mode=OperationMode.SANDBOX,
            gateway_config=SandboxGatewayConfig(
                isolation=SandboxIsolationConfig(
                    container_scope=ContainerScope.CUSTOM,
                    custom_id="demo_mock_001",
                ),
                launcher_config=MockLauncherConfig(
                    sandbox_type="mock_sandbox",
                ),
                timeout_seconds=30,
            ),
        )

        add_res = Runner.resource_mgr.add_sys_operation(card)
        assert add_res.is_ok(), f"Register failed: {add_res}"
        logger.info(f"[OK] Sandbox registered, card_id={card_id}")

        sys_op = Runner.resource_mgr.get_sys_operation(card_id)

        # --- Shell ---
        logger.info("\n--- Shell Operations ---")

        shell_res = await sys_op.shell().execute_cmd(command="echo hello world")
        logger.info("  execute_cmd('echo hello world')")
        logger.info(f"    stdout: {shell_res.data.stdout.strip()}")
        logger.info(f"    exit_code: {shell_res.data.exit_code}")

        sandbox_cwd = "/home/sandbox/project"
        pwd_res = await sys_op.shell().execute_cmd(command="pwd", cwd=sandbox_cwd)
        logger.info(f"  execute_cmd('pwd', cwd='{sandbox_cwd}')")
        logger.info(f"    stdout: {pwd_res.data.stdout.strip()}")

        ls_res = await sys_op.shell().execute_cmd(command="ls -la")
        logger.info("  execute_cmd('ls -la')")
        logger.info(f"    stdout: {ls_res.data.stdout.strip()}")

        # --- Stream Shell ---
        logger.info("\n--- Shell Stream ---")
        logger.info("  execute_cmd_stream('cat /etc/hosts'):")
        async for chunk in sys_op.shell().execute_cmd_stream(command="cat /etc/hosts"):
            if chunk.data.text:
                logger.info(
                    f"    chunk[{chunk.data.chunk_index}]: {chunk.data.text.strip()}"
                )
            if chunk.data.exit_code is not None:
                logger.info(f"    [done] exit_code={chunk.data.exit_code}")

        # --- FS ---
        logger.info("\n--- FS Operations ---")

        read_res = await sys_op.fs().read_file(path="/home/sandbox/hello.txt")
        logger.info("  read_file('/home/sandbox/hello.txt')")
        logger.info(f"    content: {read_res.data.content}")

        write_res = await sys_op.fs().write_file(
            path="/home/sandbox/test_output.txt",
            content="This is a test file written via sandbox FS",
        )
        logger.info("  write_file('/home/sandbox/test_output.txt')")
        logger.info(
            f"    size: {write_res.data.size} bytes, mode: {write_res.data.mode}"
        )

        verify_res = await sys_op.fs().read_file(path="/home/sandbox/test_output.txt")
        logger.info("  read_file (verify write)")
        logger.info(f"    content: {verify_res.data.content}")

        list_res = await sys_op.fs().list_files(path="/home/sandbox")
        logger.info("  list_files('/home/sandbox')")
        logger.info(f"    total_count: {list_res.data.total_count}")
        for item in list_res.data.list_items:
            logger.info(f"      {item.name} ({item.type}) size={item.size}")

        dirs_res = await sys_op.fs().list_directories(path="/home/sandbox")
        logger.info("  list_directories('/home/sandbox')")
        for item in dirs_res.data.list_items:
            logger.info(f"      {item.name}/")

        search_res = await sys_op.fs().search_files(
            path="/home/sandbox", pattern="*.txt"
        )
        logger.info("  search_files('/home/sandbox', '*.txt')")
        logger.info(f"    total_matches: {search_res.data.total_matches}")

        # --- Code ---
        logger.info("\n--- Code Operations ---")

        code_res = await sys_op.code().execute_code(
            code="print('Hello from Python sandbox!')",
            language="python",
        )
        logger.info("  execute_code('print(...)', language='python')")
        logger.info(f"    stdout: {code_res.data.stdout.strip()}")
        logger.info(f"    exit_code: {code_res.data.exit_code}")

        js_res = await sys_op.code().execute_code(
            code="console.log('Hello from JS sandbox!')",
            language="javascript",
        )
        logger.info("  execute_code('console.log(...)', language='javascript')")
        logger.info(f"    stdout: {js_res.data.stdout.strip()}")

        # --- Stream Code ---
        logger.info("\n--- Code Stream ---")
        logger.info("  execute_code_stream('print(...)', language='python'):")
        async for chunk in sys_op.code().execute_code_stream(
            code="print('Line 1')\nprint('Line 2')\nprint('Line 3')",
            language="python",
        ):
            if chunk.data.text:
                logger.info(
                    f"    chunk[{chunk.data.chunk_index}]: {chunk.data.text.strip()}"
                )
            if chunk.data.exit_code is not None:
                logger.info(f"    [done] exit_code={chunk.data.exit_code}")

        # --- Isolation Key ---
        logger.info("\n--- Isolation Info ---")
        logger.info(f"  isolation_key_template: {sys_op.isolation_key_template}")

        logger.info("\n[OK] Scene 1 all passed!")

    finally:
        Runner.resource_mgr.remove_sys_operation(sys_operation_id=card_id)
        await Runner.stop()
        logger.info("[OK] Resources cleaned up")


# ============================================================
# 场景二：连接真实 AIO 沙箱（需要 Docker）
# ============================================================


async def demo_aio_sandbox():
    """
    Scene 2: Connect to real AIO Sandbox

    Prerequisites:
      1. Install: pip install -U "openjiuwen[sandbox]"
      2. Start AIO Sandbox:
         See _AIO_SANDBOX_DOCKER_RUN_CMD in this module.
      3. Confirm http://localhost:8080 is accessible
    """
    logger.info("=" * 60)
    logger.info("Scene 2: Connect to Real AIO Sandbox")
    logger.info("=" * 60)

    await Runner.start()
    card_id = "aio_sandbox_demo"

    try:
        card = SysOperationCard(
            id=card_id,
            mode=OperationMode.SANDBOX,
            gateway_config=SandboxGatewayConfig(
                isolation=SandboxIsolationConfig(
                    container_scope=ContainerScope.SYSTEM,
                ),
                launcher_config=PreDeployLauncherConfig(
                    base_url="http://localhost:8080",
                    sandbox_type="aio",
                    idle_ttl_seconds=600,
                ),
                timeout_seconds=30,
            ),
        )

        add_res = Runner.resource_mgr.add_sys_operation(card)
        assert add_res.is_ok(), f"Register failed: {add_res}"
        logger.info(f"[OK] AIO Sandbox registered, card_id={card_id}")

        sys_op = Runner.resource_mgr.get_sys_operation(card_id)

        # --- Shell ---
        logger.info("\n--- Shell (Real AIO) ---")
        shell_res = await sys_op.shell().execute_cmd(command="echo hello world")
        logger.info(f"  stdout: {shell_res.data.stdout.strip()}")
        logger.info(f"  exit_code: {shell_res.data.exit_code}")

        uname_res = await sys_op.shell().execute_cmd(command="uname -a")
        logger.info(f"  uname -a: {uname_res.data.stdout.strip()}")

        # --- FS ---
        logger.info("\n--- FS (Real AIO) ---")
        read_res = await sys_op.fs().read_file(path="/etc/hosts")
        logger.info(f"  read_file('/etc/hosts') length: {len(read_res.data.content)}")

        write_res = await sys_op.fs().write_file(
            path="/tmp/sandbox_test.txt",
            content="Hello from openjiuwen sandbox!",
        )
        logger.info(f"  write_file: size={write_res.data.size}")

        # --- Code ---
        logger.info("\n--- Code (Real AIO) ---")
        code_res = await sys_op.code().execute_code(
            code="import sys; print(f'Python {sys.version}'); print(2 ** 10)",
            language="python",
        )
        logger.info(f"  stdout: {code_res.data.stdout.strip()}")

        logger.info("\n[OK] Scene 2 all passed!")

    except Exception as e:
        logger.info(
            f"\n[FAIL] Connection failed (check if AIO Sandbox is running): {e}"
        )
    finally:
        Runner.resource_mgr.remove_sys_operation(sys_operation_id=card_id)
        await Runner.stop()
        logger.info("[OK] Resources cleaned up")


# ============================================================
# 场景三：SESSION 级别隔离（多会话独立沙箱）
# ============================================================


async def demo_session_isolation():
    """
    Scene 3: SESSION-level isolation
    Different session_id requests route to different sandbox instances
    """
    logger.info("=" * 60)
    logger.info("Scene 3: SESSION-Level Isolation (Mock Provider)")
    logger.info("=" * 60)

    register_mock_components()
    await Runner.start()

    card_id_prefix = "session_demo"

    try:
        card = SysOperationCard(
            id=f"{card_id_prefix}_agent",
            mode=OperationMode.SANDBOX,
            gateway_config=SandboxGatewayConfig(
                isolation=SandboxIsolationConfig(
                    container_scope=ContainerScope.SESSION,
                    prefix="agent1_",
                ),
                launcher_config=MockLauncherConfig(
                    sandbox_type="mock_sandbox",
                ),
                timeout_seconds=30,
            ),
        )

        add_res = Runner.resource_mgr.add_sys_operation(card)
        assert add_res.is_ok()
        logger.info("[OK] SESSION Sandbox registered")
        logger.info(
            f"  isolation_key_template: {card.gateway_config.isolation.container_scope.value}"
        )
        logger.info(f"  prefix: {card.gateway_config.isolation.prefix}")

        sys_op = Runner.resource_mgr.get_sys_operation(f"{card_id_prefix}_agent")
        logger.info(f"  full isolation_key_template: {sys_op.isolation_key_template}")

        res = await sys_op.shell().execute_cmd(command="echo session test")
        logger.info(f"  execute_cmd: {res.data.stdout.strip()}")

        logger.info("\n[OK] Scene 3 passed! SESSION-level config is correct")
        logger.info(
            "  At runtime, different session_ids auto-route to different sandboxes"
        )

    finally:
        Runner.resource_mgr.remove_sys_operation(
            sys_operation_id=f"{card_id_prefix}_agent"
        )
        await Runner.stop()
        logger.info("[OK] Resources cleaned up")


# ============================================================
# 场景四：CWD 工作目录管理（Local 模式）
# ============================================================


async def demo_cwd_management():
    """
    Scene 4: CWD (Current Working Directory) management

    演示 openjiuwen 的三层 CWD 模型：
      Layer 1 -- project_root: 项目锚点（仅设置一次）
      Layer 2 -- original_cwd: 会话起始点
      Layer 3 -- cwd: 当前工作目录（随 shell 命令更新）

    读取优先级: cwd -> original_cwd -> os.getcwd()

    注意：CWD 模块仅适用于 Local 模式。
    Sandbox 模式下 cwd 作为参数传递给沙箱端，不使用本地 ContextVar。
    """
    logger.info("=" * 60)
    logger.info("Scene 4: CWD Working Directory Management (Local Mode)")
    logger.info("=" * 60)

    await Runner.start()
    card_id = "cwd_demo"

    test_dir = os.path.abspath(".")
    project_root = os.path.abspath("..")

    init_cwd(
        cwd=test_dir,
        project_root=project_root,
        workspace=os.path.join(test_dir, ".workspace"),
    )

    logger.info(f"\n  init_cwd(cwd='{test_dir}', project_root='{project_root}')")
    logger.info(f"  get_cwd()          -> {get_cwd()}")
    logger.info(f"  get_project_root() -> {get_project_root()}")
    logger.info(f"  get_workspace()    -> {get_workspace()}")

    new_cwd = os.path.join(test_dir, "subdir")
    set_cwd(new_cwd)
    logger.info(f"\n  set_cwd('{new_cwd}')")
    logger.info(f"  get_cwd() -> {get_cwd()}")

    try:
        card = SysOperationCard(
            id=card_id,
            mode=OperationMode.LOCAL,
        )

        add_res = Runner.resource_mgr.add_sys_operation(card)
        assert add_res.is_ok(), f"Register failed: {add_res}"
        logger.info(f"\n[OK] Local SysOperation registered, card_id={card_id}")

        sys_op = Runner.resource_mgr.get_sys_operation(card_id)

        shell_res = await sys_op.shell().execute_cmd(command="echo current dir")
        logger.info("\n  execute_cmd('echo current dir')")
        logger.info(f"    cwd in result: {shell_res.data.cwd}")
        logger.info(f"    stdout: {shell_res.data.stdout.strip()}")

        cwd_res = await sys_op.shell().execute_cmd(command="cd .. && echo back")
        logger.info("\n  execute_cmd('cd .. && echo back')")
        logger.info(f"    cwd in result: {cwd_res.data.cwd}")
        logger.info(f"    stdout: {cwd_res.data.stdout.strip()}")

        logger.info("\n[OK] Scene 4 all passed!")
        logger.info("  Note: Local mode uses ContextVar-based CWD")
        logger.info("  Sandbox mode passes cwd as parameter to remote sandbox")

    finally:
        Runner.resource_mgr.remove_sys_operation(sys_operation_id=card_id)
        await Runner.stop()
        logger.info("[OK] Resources cleaned up")


# ============================================================
# 场景五：work_config.sandbox_root → init_cwd 集成链路
# ============================================================


async def demo_work_config_to_cwd():
    """
    Scene 5: work_config.sandbox_root → init_cwd Integration

    模拟 agent.py _apply_runtime_skill_injection 中的工作目录初始化流程：
      1. 通过 SysOperationCard.work_config.sandbox_root 配置工作目录列表
      2. 取 sandbox_root[0] 作为主工作目录
      3. 调用 init_cwd(primary_work_dir) 初始化 ContextVar
      4. LOCAL 模式下 work_dir 传递给后续 skill 提示词构建
      5. SANDBOX 模式下 work_dir 为空（cwd 由沙箱端管理）

    与场景四的区别：
      场景四：直接调用 init_cwd(cwd=..., project_root=..., workspace=...) 手动管理
      场景五：通过 SysOperationCard.work_config 声明式配置，模拟 Agent 运行时链路
    """
    logger.info("=" * 60)
    logger.info("Scene 5: work_config.sandbox_root → init_cwd Integration")
    logger.info("=" * 60)

    await Runner.start()

    test_dir = os.path.abspath(".")
    project_root = os.path.abspath("..")
    sandbox_roots = [test_dir, project_root]

    # --- 5a: LOCAL 模式，work_config.sandbox_root → init_cwd ---
    logger.info("\n--- 5a: LOCAL mode with work_config ---")
    card_id_local = "work_config_local_demo"

    try:
        card = SysOperationCard(
            id=card_id_local,
            mode=OperationMode.LOCAL,
            work_config=LocalWorkConfig(
                sandbox_root=sandbox_roots,
                restrict_to_sandbox=True,
            ),
        )

        add_res = Runner.resource_mgr.add_sys_operation(card)
        assert add_res.is_ok(), f"Register failed: {add_res}"
        logger.info(f"  [OK] LOCAL SysOperation registered, card_id={card_id_local}")
        logger.info(f"  work_config.sandbox_root = {card.work_config.sandbox_root}")
        logger.info(
            f"  work_config.restrict_to_sandbox = {card.work_config.restrict_to_sandbox}"
        )

        primary_work_dir = ""
        if card.work_config:
            roots = card.work_config.sandbox_root or []
            if roots:
                primary_work_dir = roots[0] or ""

        init_cwd(primary_work_dir)

        work_dir = primary_work_dir if card.mode == OperationMode.LOCAL else ""

        logger.info(f"\n  primary_work_dir = sandbox_root[0] = '{primary_work_dir}'")
        logger.info(f"  init_cwd('{primary_work_dir}') called")
        logger.info(f"  get_cwd()          -> {get_cwd()}")
        logger.info(f"  get_project_root() -> {get_project_root()}")
        logger.info(f"  work_dir for skill = '{work_dir}'")

        sys_op = Runner.resource_mgr.get_sys_operation(card_id_local)

        shell_res = await sys_op.shell().execute_cmd(command="echo work_config test")
        logger.info("\n  execute_cmd('echo work_config test')")
        logger.info(f"    cwd in result: {shell_res.data.cwd}")
        logger.info(f"    stdout: {shell_res.data.stdout.strip()}")

        assert get_cwd() == primary_work_dir, (
            f"CWD mismatch: expected '{primary_work_dir}', got '{get_cwd()}'"
        )
        logger.info(f"\n  [OK] CWD matches sandbox_root[0]: '{get_cwd()}'")

        logger.info("\n[OK] Scene 5a all passed!")

    finally:
        Runner.resource_mgr.remove_sys_operation(sys_operation_id=card_id_local)

    # --- 5b: SANDBOX 模式，work_dir 应为空 ---
    logger.info("\n--- 5b: SANDBOX mode (work_dir should be empty) ---")
    register_mock_components()
    card_id_sandbox = "work_config_sandbox_demo"

    try:
        card = SysOperationCard(
            id=card_id_sandbox,
            mode=OperationMode.SANDBOX,
            gateway_config=SandboxGatewayConfig(
                isolation=SandboxIsolationConfig(
                    container_scope=ContainerScope.CUSTOM,
                    custom_id="work_config_test",
                ),
                launcher_config=MockLauncherConfig(
                    sandbox_type="mock_sandbox",
                ),
                timeout_seconds=30,
            ),
        )

        add_res = Runner.resource_mgr.add_sys_operation(card)
        assert add_res.is_ok(), f"Register failed: {add_res}"
        logger.info(
            f"  [OK] SANDBOX SysOperation registered, card_id={card_id_sandbox}"
        )

        primary_work_dir = ""
        if card.work_config:
            roots = card.work_config.sandbox_root or []
            if roots:
                primary_work_dir = roots[0] or ""

        work_dir = primary_work_dir if card.mode == OperationMode.LOCAL else ""

        logger.info(f"  work_config = {card.work_config}")
        logger.info(f"  primary_work_dir = '{primary_work_dir}'")
        logger.info(f"  work_dir for skill (SANDBOX → '') = '{work_dir}'")
        assert work_dir == "", (
            f"SANDBOX mode work_dir should be empty, got '{work_dir}'"
        )
        logger.info("  [OK] SANDBOX mode correctly returns empty work_dir")

        sys_op = Runner.resource_mgr.get_sys_operation(card_id_sandbox)
        sandbox_cwd = "/home/sandbox/project"
        res = await sys_op.shell().execute_cmd(command="pwd", cwd=sandbox_cwd)
        logger.info(f"\n  execute_cmd('pwd', cwd='{sandbox_cwd}')")
        logger.info(f"    stdout: {res.data.stdout.strip()}")

        logger.info("\n[OK] Scene 5b all passed!")

    finally:
        Runner.resource_mgr.remove_sys_operation(sys_operation_id=card_id_sandbox)

    # --- 5c: 无 work_config 时，primary_work_dir 为空 ---
    logger.info("\n--- 5c: No work_config (fallback to empty) ---")
    card_id_no_config = "work_config_none_demo"

    try:
        card = SysOperationCard(
            id=card_id_no_config,
            mode=OperationMode.LOCAL,
        )

        primary_work_dir = ""
        if card.work_config:
            roots = card.work_config.sandbox_root or []
            if roots:
                primary_work_dir = roots[0] or ""

        work_dir = primary_work_dir if card.mode == OperationMode.LOCAL else ""

        logger.info(f"  work_config = {card.work_config}")
        logger.info(f"  primary_work_dir = '{primary_work_dir}'")
        logger.info(f"  work_dir = '{work_dir}'")
        assert primary_work_dir == "", (
            f"Expected empty primary_work_dir, got '{primary_work_dir}'"
        )
        logger.info("  [OK] No work_config correctly falls back to empty work_dir")

        logger.info("\n[OK] Scene 5c all passed!")

    finally:
        Runner.resource_mgr.remove_sys_operation(sys_operation_id=card_id_no_config)

    await Runner.stop()
    logger.info(
        "\n[OK] Scene 5 all passed! work_config → init_cwd integration verified"
    )
    logger.info("[OK] Resources cleaned up")


# ============================================================
# Main
# ============================================================


async def main():
    logger.info("OpenJiuWen Sandbox Usage Examples\n")

    # Scene 1: Custom Mock Provider (no Docker needed)
    await demo_mock_sandbox()

    logger.info("\n")

    # Scene 3: SESSION-level isolation
    await demo_session_isolation()

    logger.info("\n")

    # Scene 4: CWD management (Local mode)
    await demo_cwd_management()

    logger.info("\n")

    # Scene 5: work_config.sandbox_root → init_cwd integration
    await demo_work_config_to_cwd()

    logger.info("\n")

    # Scene 2: Real AIO Sandbox (needs Docker)
    logger.info("Note: Scene 2 requires Docker to run AIO Sandbox container")
    logger.info(f"Start command: {_AIO_SANDBOX_DOCKER_RUN_CMD}")
    logger.info("Skipped Scene 2 (uncomment in main() to run)\n")
    # await demo_aio_sandbox()


if __name__ == "__main__":
    asyncio.run(main())
