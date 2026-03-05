#!/usr/bin/env python3

import os
import platform
import shutil
import subprocess
import tempfile
import pyseccomp
import yaml


class SandboxConfig:
    def __init__(self,
                 sandbox_type="bubblewrap",
                 sandbox_path='',
                 interpreter=None,
                 seccomp=None,
                 mounts=None,
                 namespace=None,
                 environment=None,
                 timeout=0):
        interpreter = interpreter or {}
        seccomp = seccomp or []
        mounts = mounts or []
        namespace = namespace or []
        environment = environment or {}
        self._get_platform()
        self.sandbox_type = sandbox_type
        self.sandbox_path = sandbox_path
        self.py_path = interpreter.get('python_path', '')
        self.js_path = interpreter.get('javascript_path', '')
        self.seccomp = seccomp
        self.mounts = mounts
        self.namespace = namespace
        self.envs = environment
        self.timeout = timeout

        self.verify()

        self.allow_syscalls = seccomp.get('allow', {}).get(self.arch, [])
        self.compile_seccomp_bpf()

    @classmethod
    def init_from_file(cls, config_file):
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        sandbox_type = config['sandbox']['type']
        sandbox_path = config['sandbox'].get('path', '')
        interpreter = config.get('interpreter', {})
        seccomp = config.get('seccomp', {})
        mounts = config['mount']
        namespace = config.get('namespace', {})
        envs = config.get('environment', {})
        timeout = config.get('timeout', 0)

        config = cls(sandbox_type, sandbox_path, interpreter, seccomp, mounts, namespace, envs, timeout)
        return config

    def verify(self):
        for mount in self.mounts:
            if not os.path.exists(mount['src']):
                raise Exception(f"mount path {mount['src']} not exists")
        if self.sandbox_type != 'bubblewrap':
            raise Exception(f"Unknown sandbox type {self.sandbox_type}")
        found = shutil.which(self.sandbox_path)
        if not found:
            raise Exception(f"Cannot find {self.sandbox_path}")

    def compile_seccomp_bpf(self):
        if len(self.allow_syscalls) == 0:
            self.seccomp_bpf = None
            return
        self.seccomp_bpf = pyseccomp.SyscallFilter(pyseccomp.KILL)
        for sys in self.allow_syscalls:
            self.seccomp_bpf.add_rule(pyseccomp.ALLOW, sys)

    def export_seccomp_file(self, file):
        self.seccomp_bpf.export_bpf(file)

    def _get_platform(self):
        arch = platform.machine()
        if arch not in ['x86_64', 'aarch64']:
            raise Exception(f"{arch} not supported.")
        self.arch = arch


class ExecutionResult:
    retcode = None
    stdout = None
    stderr = None

    def __init__(self, retcode, stdout, stderr):
        self.retcode = retcode
        self.stdout = stdout
        self.stderr = stderr


def get_sandbox(config: SandboxConfig):
    if config.sandbox_type == 'bubblewrap':
        return BubbleWrapRunner(config)
    raise Exception(f"{config.sandbox_type} not supported.")


class BubbleWrapRunner:
    _seccomp_bpf_file_name = 'seccomp.bpf'

    def __init__(self, config):
        self._sandbox_config = config
        self._lang = None
        self._code_dir = None
        self._code_file = None
        self._src_code_dir = None
        self._src_code_file = None
        self._dst_code_dir = None
        self._dst_code_file = None
        self._src_seccomp_file = None
        self._dst_seccomp_file = None

    def _create_sandbox(self):
        if self._lang == "python":
            ext = ".py"
        elif self._lang == "javascript":
            ext = ".js"
        self._code_dir = 'code'
        self._code_file = 'code' + ext
        self._src_code_dir = tempfile.TemporaryDirectory(prefix='bwrap_workdir_', dir='/tmp')
        self._src_code_file = os.path.join(self._src_code_dir.name, self._code_file)
        self._dst_code_dir = os.path.join('/', self._code_dir)
        self._dst_code_file = os.path.join(self._dst_code_dir, self._code_file)

        if self._sandbox_config.seccomp_bpf:
            self._src_seccomp_file = os.path.join(self._src_code_dir.name, BubbleWrapRunner._seccomp_bpf_file_name)
            self._dst_seccomp_file = os.path.join(self._dst_code_dir, BubbleWrapRunner._seccomp_bpf_file_name)
            with open(self._src_seccomp_file, 'wb') as f:
                self._sandbox_config.export_seccomp_file(f)

        os.chmod(self._src_code_dir.name, 0o755)

    def _generate_mount_params(self):
        params = []
        for mount in self._sandbox_config.mounts:
            if mount['mode'] == 'read':
                mode = '--ro-bind'
            elif mount['mode'] == 'write':
                mode = '--bind'
            else:
                raise Exception(f"Unknown mount mode {mount['mode']}")
            params = params + [mode, mount['src'], mount['dst']]
        params = params + ['--ro-bind', self._src_code_dir.name, self._dst_code_dir]

        return params

    def _wrap_py_seccomp_code(self, code):
        seccomp_code = f'''
import struct, ctypes, json
def load_seccomp_filter(bpf_file):
    PR_SET_NO_NEW_PRIVS = 38
    PR_SET_SECCOMP = 22
    SECCOMP_MODE_FILTER = 2
    class SockFilter(ctypes.Structure):
        _fields_ = [
            ("code", ctypes.c_ushort),
            ("jt",   ctypes.c_ubyte),
            ("jf",   ctypes.c_ubyte),
            ("k",    ctypes.c_uint32),
        ]

    class SockFprog(ctypes.Structure):
        _fields_ = [
            ("len",    ctypes.c_ushort),
            ("filter", ctypes.POINTER(SockFilter))
        ]
    with open(bpf_file, 'rb') as f:
        bpf_data = f.read()
    struct_size = ctypes.sizeof(SockFilter)
    inst_cnt = len(bpf_data) // struct_size

    FilterArrayType = SockFilter * inst_cnt
    filter_array = FilterArrayType.from_buffer_copy(bpf_data)
    prog = SockFprog()
    prog.len = inst_cnt
    prog.filter = ctypes.cast(filter_array, ctypes.POINTER(SockFilter))
    libc = ctypes.CDLL(None, use_errno=True)
    ret = libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)
    if ret != 0:
        raise OSError(f"prctl(NO_NEW_PRIVS) failed. Errno: {{ctypes.get_errno()}}")
    ret = libc.prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, ctypes.byref(prog))
    if ret != 0:
        raise OSError(f"prctl(SECCOMP) failed. Errno: {{ctypes.get_errno()}}")
load_seccomp_filter("{self._dst_seccomp_file}")
del load_seccomp_filter
'''
        return seccomp_code + '\n' + code

    def _generate_namespace_params(self):
        param_map = {
            'user': '--unshare-user',
            'ipc': '--unshare-ipc',
            'pid': '--unshare-pid',
            'net': '--unshare-net',
            'uts': '--unshare-uts',
            'cgroup': '--unshare-cgroup'
        }

        params = []
        for ns in param_map.keys():
            if bool(self._sandbox_config.namespace.get(ns, False)):
                params.append(param_map[ns])
        return params

    def run(self, raw_code, base_code, lang, timeout=0):
        self._lang = lang

        self._create_sandbox()

        seccomp_fd = None
        pass_fds = []
        if self._lang == "python":
            if self._sandbox_config.seccomp_bpf:
                base_code = self._wrap_py_seccomp_code(base_code)
            interpreter = self._sandbox_config.py_path
        elif self._lang == "javascript":
            if self._sandbox_config.seccomp_bpf:
                seccomp_fd = os.open(self._src_seccomp_file, os.O_RDONLY)
            pass_fds = [seccomp_fd]
            interpreter = self._sandbox_config.js_path

        with open(self._src_code_file, 'w') as f:
            f.write(base_code)

        cmd = [
            self._sandbox_config.sandbox_path,
            '--die-with-parent'
        ]

        cmd = cmd + self._generate_mount_params()

        cmd = cmd + self._generate_namespace_params()

        if seccomp_fd:
            cmd = cmd + ['--seccomp', str(seccomp_fd)]

        cmd = cmd + [interpreter, self._dst_code_file, raw_code]

        try:
            process = subprocess.Popen(cmd,
                                        env=self._sandbox_config.envs,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        start_new_session=True,
                                        pass_fds=pass_fds,
                                        text=True)
            stdout, stderr = process.communicate(timeout=max(timeout, self._sandbox_config.timeout))
            retcode = process.returncode

        except subprocess.TimeoutExpired as e:
            stdout = ''
            stderr = 'code execution timeout.'
            retcode = -1

        self._src_code_dir.cleanup()

        if seccomp_fd:
            os.close(seccomp_fd)

        return ExecutionResult(retcode, stdout, stderr)
