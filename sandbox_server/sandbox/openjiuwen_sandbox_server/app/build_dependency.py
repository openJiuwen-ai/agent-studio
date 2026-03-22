#!/usr/bin/env python3
import logging
import os
import re
import sys
import shutil
import subprocess

from .dependency_manager import DependencyManager

IS_WINDOWS = sys.platform == 'win32'
logger = logging.getLogger(__name__)


def _abs_version_distance(v, base):
    """Weighted distance between two version tuples (major > minor > patch)."""
    max_len = max(len(v), len(base))
    v = v + (0,) * (max_len - len(v))
    base = base + (0,) * (max_len - len(base))
    weights = [1_000_000, 1_000, 1]
    return sum(abs(a - b) * w for a, b, w in zip(v, base, weights))


class DependencyBuilder:
    @staticmethod
    def exec_cmd(cmd, envs=None, cwd=None):
        merged_envs = os.environ.copy()
        if envs:
            if IS_WINDOWS:
                # os.environ.copy() returns a case-sensitive dict, but Windows
                # env vars are case-insensitive. Naively updating with a
                # different-cased key (e.g. 'PATH' vs 'Path') creates duplicates
                # and CreateProcess only honours the first occurrence.
                existing_upper = {k.upper(): k for k in merged_envs}
                for key, val in envs.items():
                    merged_envs[existing_upper.get(key.upper(), key)] = val
            else:
                merged_envs.update(envs)
        logger.debug("Executing: %s", cmd)
        p = subprocess.Popen(cmd, env=merged_envs, cwd=cwd)
        p.communicate()
        if p.returncode != 0:
            raise RuntimeError(f"Command failed (exit {p.returncode}): {cmd}")


class PythonDependencyBuilder(DependencyBuilder):
    @staticmethod
    def _parse_version(version_str):
        return tuple(int(x) for x in version_str.split('.'))

    @staticmethod
    def _check_specifier(version_tuple, op, spec_tuple):
        max_len = max(len(version_tuple), len(spec_tuple))
        v = version_tuple + (0,) * (max_len - len(version_tuple))
        s = spec_tuple + (0,) * (max_len - len(spec_tuple))

        ops = {
            '>=': lambda: v >= s,
            '<=': lambda: v <= s,
            '>': lambda: v > s,
            '<': lambda: v < s,
            '==': lambda: v == s,
            '!=': lambda: v != s,
        }
        if op in ops:
            return ops[op]()

        if op == '~=':
            if v < s:
                return False
            upper = list(s[:-1])
            upper[-1] += 1
            return v < tuple(upper) + (0,) * (max_len - len(upper))

        raise ValueError(f"Unknown operator: {op}")

    @classmethod
    def _satisfies_requires_python(cls, version_str, requires_python):
        version_tuple = cls._parse_version(version_str)
        for spec in requires_python.split(','):
            spec = spec.strip()
            if not spec:
                continue
            match = re.match(r'(~=|==|!=|>=|<=|>|<)\s*(\d+(?:\.\d+)*)', spec)
            if not match:
                raise ValueError(f"Cannot parse version specifier: {spec}")
            if not cls._check_specifier(version_tuple, match.group(1), cls._parse_version(match.group(2))):
                return False
        return True

    def _list_available_pythons(self, envs):
        merged_envs = os.environ.copy()
        if envs:
            merged_envs.update(envs)
        cmd = ['uv', 'python', 'list', '--all-versions']
        result = subprocess.run(
            cmd, env=merged_envs, capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to list Python versions: {result.stderr}")

        versions = set()
        for line in result.stdout.strip().split('\n'):
            match = re.match(r'cpython-(\d+\.\d+\.\d+)', line.strip())
            if match:
                versions.add(match.group(1))
        return sorted(versions, key=lambda v: self._parse_version(v), reverse=True)

    @staticmethod
    def _extract_base_version(requires_python):
        """Extract the version number from the first specifier as the preference anchor."""
        match = re.search(r'(\d+(?:\.\d+)*)', requires_python)
        if not match:
            return (0,)
        return tuple(int(x) for x in match.group(1).split('.'))

    def _resolve_python_version(self, requires_python, envs):
        available = self._list_available_pythons(envs)
        candidates = [v for v in available if self._satisfies_requires_python(v, requires_python)]
        if not candidates:
            raise RuntimeError(
                f"No available Python version satisfies '{requires_python}'. "
                f"Available: {available[:10]}"
            )

        base = self._extract_base_version(requires_python)
        candidates.sort(key=lambda v: _abs_version_distance(self._parse_version(v), base))
        chosen = candidates[0]
        return chosen

    def build(self, config):
        requires_python = config.interpreter
        if not requires_python:
            raise ValueError("requires-python is not specified in pyproject.toml")

        py_dir = config.install_path
        interpreter_dir = os.path.join(py_dir, 'python')
        venv_dir = os.path.join(py_dir, '.venv')
        os.makedirs(interpreter_dir, exist_ok=True)

        shutil.copy2(config.conf_path, py_dir)

        uv_config = config.data.get('tool', {}).get('uv', {})
        envs = {'UV_PYTHON_INSTALL_DIR': interpreter_dir}
        if 'python-install-mirror' in uv_config:
            envs['UV_PYTHON_INSTALL_MIRROR'] = uv_config['python-install-mirror']
        index_list = uv_config.get('index', [])
        if index_list and isinstance(index_list, list) and 'url' in index_list[0]:
            envs['UV_DEFAULT_INDEX'] = index_list[0]['url']

        py_version = self._resolve_python_version(requires_python, envs)

        logger.info("Installing Python %s ...", py_version)
        self.exec_cmd(['uv', 'python', 'install', py_version], envs)

        logger.info("Creating virtual environment at %s ...", venv_dir)
        self.exec_cmd(['uv', 'venv', venv_dir], envs)

        if config.packages:
            logger.info("Installing Python packages: %s", config.packages)
            if IS_WINDOWS:
                self.exec_cmd(['uv', 'sync'], envs, cwd=py_dir)
            else:
                self.exec_cmd(
                    ['/bin/bash', '-c', f'cd {py_dir} && source {venv_dir}/bin/activate && uv sync'],
                    envs,
                )


class JavascriptDependencyBuilder(DependencyBuilder):
    def build(self, config):
        node_version = config.interpreter
        match = re.search(r'(\d+)', node_version)
        if not match:
            raise ValueError(f"Cannot parse Node.js version from engines.node: {node_version}")
        node_version = match.group(1)

        js_dir = config.install_path
        os.makedirs(js_dir, exist_ok=True)

        envs = {}
        npm_mirror = os.environ.get('NPM_CONFIG_REGISTRY')
        if npm_mirror:
            envs['NPM_CONFIG_REGISTRY'] = npm_mirror

        if IS_WINDOWS:
            self._build_windows(config, node_version, js_dir, envs)
        else:
            self._build_linux(config, node_version, js_dir, envs)

    @staticmethod
    def _find_node_dir_windows():
        """Locate the directory containing node.exe on Windows."""
        node_path = shutil.which('node')
        if node_path:
            return os.path.dirname(node_path)

        nvm_symlink = os.environ.get('NVM_SYMLINK', '')
        if nvm_symlink and os.path.isfile(os.path.join(nvm_symlink, 'node.exe')):
            return nvm_symlink

        candidates = [
            os.path.join(os.environ.get('ProgramFiles', r'C:\Program Files'), 'nodejs'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'nodejs'),
        ]
        for path in candidates:
            if path and os.path.isfile(os.path.join(path, 'node.exe')):
                return path

        nvm_home = os.environ.get('NVM_HOME', '')
        if nvm_home and os.path.isdir(nvm_home):
            for entry in sorted(os.listdir(nvm_home), reverse=True):
                if os.path.isfile(os.path.join(nvm_home, entry, 'node.exe')):
                    return os.path.join(nvm_home, entry)

        return None

    def _build_windows(self, config, node_version, js_dir, envs):
        nvm_exe = shutil.which('nvm')
        if nvm_exe:
            logger.info("Installing Node.js %s via nvm ...", node_version)
            self.exec_cmd([nvm_exe, 'install', node_version], envs)
            self.exec_cmd([nvm_exe, 'use', node_version], envs)

        node_dir = self._find_node_dir_windows()
        if not node_dir:
            raise RuntimeError(
                "Cannot find Node.js installation directory. "
                "Please ensure Node.js is installed or nvm-windows is configured."
            )
        logger.info("Using Node.js from: %s", node_dir)

        envs = dict(envs)
        envs['PATH'] = node_dir + ';' + os.environ.get('PATH', '')

        # npm ships as npm.cmd on Windows; Popen without shell=True
        # cannot resolve .cmd/.bat extensions, so use the full path.
        npm_exe = shutil.which('npm', path=envs['PATH'])
        if not npm_exe:
            raise RuntimeError(
                f"Cannot find npm in {node_dir}. "
                "Please verify your Node.js installation."
            )

        shutil.copy2(config.conf_path, js_dir)
        logger.info("Installing Node.js packages ...")
        self.exec_cmd([npm_exe, 'install'], envs, js_dir)

        logger.info("Saving node directory path: %s", node_dir)
        node_path_file = os.path.join(js_dir, 'node_path')
        with open(node_path_file, 'w') as f:
            f.write(node_dir)

    def _build_linux(self, config, node_version, js_dir, envs):
        nvm_dir = os.environ.get('NVM_DIR', os.path.join(os.environ['HOME'], '.nvm'))
        if not os.path.exists(nvm_dir):
            raise RuntimeError(f"Cannot find nvm directory: {nvm_dir}")

        logger.info("Installing Node.js %s ...", node_version)
        self.exec_cmd(
            ['/bin/bash', '-c', f'source {nvm_dir}/nvm.sh && nvm install {node_version}'],
            envs,
        )

        shutil.copy2(config.conf_path, js_dir)
        logger.info("Installing Node.js packages ...")
        self.exec_cmd(
            ['/bin/bash', '-c', f'cd {js_dir} && source {nvm_dir}/nvm.sh && nvm use {node_version} && npm install'],
            envs,
            js_dir,
        )

        logger.info("Creating node symlink ...")
        bash_script = (
            f'cd {js_dir} && source {nvm_dir}/nvm.sh'
            f' && nvm use {node_version}'
            f' && ln -s $(dirname $(which node)) node'
        )
        self.exec_cmd(['/bin/bash', '-c', bash_script], envs, js_dir)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

    dependency_manager = DependencyManager()

    for config in dependency_manager.py_deps.values():
        PythonDependencyBuilder().build(config)
    for config in dependency_manager.js_deps.values():
        JavascriptDependencyBuilder().build(config)

    logger.info("Done")
