#!/usr/bin/env python3
import os
import sys

from .base import BaseSandbox
from .util import generate_eval_command, merge_environments

_INTERPRETER_EXE = {
    'python': 'python.exe' if sys.platform == 'win32' else 'python',
    'javascript': 'node.exe' if sys.platform == 'win32' else 'node',
}


class LocalRunner(BaseSandbox, sandbox_type='local'):
    def __init__(self, sandbox_config, dependency_manager=None):
        super().__init__(sandbox_config, dependency_manager)
        self._sandbox_config = sandbox_config
        self._dep_mngr = dependency_manager

    def run(self, raw_code, base_code, lang, timeout=0, dep_name=None):
        interpreter = None
        envs = os.environ.copy()
        if self._dep_mngr:
            dep_envs, _ = self._dep_mngr.get_dependency_setting(lang, dep_name)
            envs = merge_environments(envs, dep_envs)
            # On Windows, CreateProcess searches the calling process's
            # directory before PATH, so a bare 'python'/'node' may resolve
            # to the server's own interpreter. Use the full path instead.
            dep_path = dep_envs.get('PATH', '')
            if sys.platform == 'win32' and dep_path and lang in _INTERPRETER_EXE:
                full_path = os.path.join(dep_path, _INTERPRETER_EXE[lang])
                if os.path.isfile(full_path):
                    interpreter = full_path

        cmd = generate_eval_command(lang, interpreter, base_code, raw_code)
        return self._execute_process(cmd, envs, timeout)
