#!/usr/bin/env python3
import sys
from abc import ABC, abstractmethod
import subprocess

from .util import ExecutionResult


class BaseSandbox(ABC):
    """Base class for all sandbox implementations.

    New sandbox types register automatically via subclassing:

        class MyRunner(BaseSandbox, sandbox_type='my_sandbox'):
            ...

    Then 'my_sandbox' becomes available through BaseSandbox.get_class().
    """

    _registry: dict[str, type['BaseSandbox']] = {}

    def __init_subclass__(cls, sandbox_type: str | None = None, **kwargs):
        super().__init_subclass__(**kwargs)
        if sandbox_type is not None:
            BaseSandbox._registry[sandbox_type] = cls

    @classmethod
    def get_class(cls, sandbox_type: str) -> type['BaseSandbox']:
        if sandbox_type not in cls._registry:
            available = list(cls._registry.keys())
            raise ValueError(
                f"Unknown sandbox type: '{sandbox_type}'. Available: {available}"
            )
        return cls._registry[sandbox_type]

    @abstractmethod
    def __init__(self, sandbox_config, dependency_manager=None):
        ...

    @abstractmethod
    def run(self, raw_code, base_code, lang, timeout=0, dep_name=None) -> ExecutionResult:
        ...

    @staticmethod
    def pre_init(sandbox_config):
        """Optional one-time class-level initialization. Override if needed."""
        pass

    @staticmethod
    def _execute_process(cmd, envs, timeout, pass_fds=()):
        """Run a subprocess with timeout, returning ExecutionResult."""
        try:
            popen_kwargs = dict(
                env=envs,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True,
            )
            if sys.platform == 'win32':
                popen_kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                popen_kwargs['start_new_session'] = True
                popen_kwargs['pass_fds'] = pass_fds
            process = subprocess.Popen(cmd, **popen_kwargs)
            stdout, stderr = process.communicate(timeout=timeout)
            return ExecutionResult(process.returncode, stdout, stderr)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            return ExecutionResult(-1, '', 'code execution timeout.')
