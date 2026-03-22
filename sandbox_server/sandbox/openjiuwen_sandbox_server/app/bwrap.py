#!/usr/bin/env python3
import os
import platform
import tempfile

import pyseccomp

from .base import BaseSandbox
from .util import ExecutionResult, generate_eval_command, merge_environments

SECCOMP_BPF_FILENAME = 'seccomp.bpf'

MOUNT_MODES = {
    'read': '--ro-bind',
    'write': '--bind',
    'dev': '--dev-bind',
}

NAMESPACE_FLAGS = {
    'user': '--unshare-user',
    'ipc': '--unshare-ipc',
    'pid': '--unshare-pid',
    'net': '--unshare-net',
    'uts': '--unshare-uts',
    'cgroup': '--unshare-cgroup',
}


def _build_py_seccomp_loader(bpf_path):
    """Generate Python code that loads a seccomp BPF filter at runtime."""
    return f'''
import struct, ctypes, json
def _load_seccomp(bpf_file):
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
_load_seccomp("{bpf_path}")
del _load_seccomp
'''


class BubbleWrapRunner(BaseSandbox, sandbox_type='bubblewrap'):

    def __init__(self, sandbox_config, dependency_manager=None):
        super().__init__(sandbox_config, dependency_manager)
        self._sandbox_config = sandbox_config
        self._dep_mngr = dependency_manager

    @staticmethod
    def pre_init(sandbox_config):
        arch = platform.machine()
        if arch not in ('x86_64', 'aarch64'):
            raise RuntimeError(f"Unsupported architecture: {arch}")

        allowed = sandbox_config.seccomp['allow'].get(arch, [])
        if not allowed:
            sandbox_config.seccomp_bpf = None
            return

        bpf = pyseccomp.SyscallFilter(pyseccomp.KILL)
        for syscall in allowed:
            bpf.add_rule(pyseccomp.ALLOW, syscall)
        sandbox_config.seccomp_bpf = bpf

    def run(self, raw_code, base_code, lang, timeout=0, dep_name=None):
        with tempfile.TemporaryDirectory(prefix='bwrap_workdir_', dir='/tmp') as workdir:
            os.chmod(workdir, 0o755)
            dst_code_dir = '/code'

            seccomp_fd = None
            try:
                seccomp_fd = self._apply_seccomp(workdir, dst_code_dir, lang)
                if lang == 'python' and self._sandbox_config.seccomp_bpf:
                    dst_bpf = os.path.join(dst_code_dir, SECCOMP_BPF_FILENAME)
                    base_code = _build_py_seccomp_loader(dst_bpf) + '\n' + base_code

                envs = self._sandbox_config.environment.copy()

                dep_paths = []
                if self._dep_mngr:
                    dep_envs, dep_paths = self._dep_mngr.get_dependency_setting(lang, dep_name)
                    envs = merge_environments(envs, dep_envs)

                cmd = [self._sandbox_config.sandbox['path'], '--die-with-parent']
                cmd += self._mount_params(workdir, dst_code_dir, dep_paths)
                cmd += self._namespace_params()
                if self._sandbox_config.options:
                    cmd += self._sandbox_config.options
                if seccomp_fd is not None:
                    cmd += ['--seccomp', str(seccomp_fd)]
                cmd += generate_eval_command(lang, None, base_code, raw_code)

                pass_fds = (seccomp_fd,) if seccomp_fd is not None else ()
                effective_timeout = max(timeout, int(self._sandbox_config.timeout))
                result = self._execute_process(cmd, envs, effective_timeout, pass_fds)

                if result.retcode == 159:
                    result = ExecutionResult(
                        result.retcode, result.stdout,
                        result.stderr + '\nBad syscall detected.',
                    )
                return result
            finally:
                if seccomp_fd is not None:
                    os.close(seccomp_fd)

    def _apply_seccomp(self, workdir, dst_code_dir, lang):
        """Write seccomp BPF and return an fd for JS, or None."""
        if not self._sandbox_config.seccomp_bpf:
            return None

        src_bpf = os.path.join(workdir, SECCOMP_BPF_FILENAME)
        with open(src_bpf, 'wb') as f:
            self._sandbox_config.seccomp_bpf.export_bpf(f)

        if lang == 'javascript':
            return os.open(src_bpf, os.O_RDONLY)
        return None

    def _mount_params(self, workdir, dst_code_dir, extra_paths):
        params = []
        for mount in self._sandbox_config.mount:
            flag = MOUNT_MODES.get(mount['mode'])
            if not flag:
                raise ValueError(f"Unknown mount mode: {mount['mode']}")
            params += [flag, mount['src'], mount['dst']]

        params += ['--ro-bind', workdir, dst_code_dir]

        for path in extra_paths:
            params += ['--ro-bind', path, path]

        return params

    def _namespace_params(self):
        return [
            flag for ns, flag in NAMESPACE_FLAGS.items()
            if self._sandbox_config.namespace.get(ns, False)
        ]
