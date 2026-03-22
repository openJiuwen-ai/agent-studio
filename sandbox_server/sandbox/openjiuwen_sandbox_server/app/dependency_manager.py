#!/usr/bin/env python3
from dataclasses import dataclass, field
import os
import sys
import json
from pathlib import Path
import tomllib

IS_WINDOWS = sys.platform == 'win32'

DEFAULT_DEPENDENCY_DIR = (
    os.path.join(os.environ.get('LOCALAPPDATA', r'C:\sandbox'), 'sandbox', 'dependencies')
    if IS_WINDOWS else '/sandbox/dependencies'
)


@dataclass
class DependencyConfig:
    name: str
    interpreter: str
    packages: list | dict
    conf_path: str
    install_path: str
    data: dict = field(default_factory=dict)


class DependencyManager:
    def __init__(self):
        self.dependency_dir = os.environ.get('DEPENDENCY_DIR', DEFAULT_DEPENDENCY_DIR)
        conf_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'conf', 'dependency'))
        self.py_deps: dict[str, DependencyConfig] = {}
        self.js_deps: dict[str, DependencyConfig] = {}

        parsers = {'.toml': self._parse_py_dependency, '.json': self._parse_js_dependency}
        for file in Path(conf_dir).iterdir():
            if file.is_file() and file.suffix in parsers:
                parsers[file.suffix](str(file))

    def _parse_py_dependency(self, conf_file):
        with open(conf_file, 'rb') as f:
            config = tomllib.load(f)
        project = config.get('project', {})
        name = project['name']
        requires_python = project.get('requires-python', '')
        if name in self.py_deps:
            raise ValueError(f'Python dependency "{name}" already exists')
        if not requires_python:
            raise ValueError("requires-python is not specified in pyproject.toml")
        packages = project.get('dependencies', [])
        self.py_deps[name] = DependencyConfig(
            name, requires_python, packages, conf_file,
            os.path.join(self.dependency_dir, name), config,
        )

    def _parse_js_dependency(self, conf_file):
        with open(conf_file, 'rb') as f:
            config = json.load(f)
        name = config['name']
        if name in self.js_deps:
            raise ValueError(f'JavaScript dependency "{name}" already exists')
        dependencies = config.get('dependencies', {})
        node_version = config.get('engines', {}).get('node', '')
        self.js_deps[name] = DependencyConfig(
            name, node_version, dependencies, conf_file,
            os.path.join(self.dependency_dir, name), config,
        )

    def get_py_deps_setting(self, name):
        name = name or next(iter(self.py_deps))
        config = self.py_deps[name]

        if not os.path.exists(config.install_path):
            return {}, []

        venv_scripts = 'Scripts' if IS_WINDOWS else 'bin'
        venv_bin = os.path.join(config.install_path, '.venv', venv_scripts)
        return {'PATH': venv_bin}, [config.install_path]

    def get_js_deps_setting(self, name):
        name = name or next(iter(self.js_deps))
        config = self.js_deps[name]

        if not os.path.exists(config.install_path):
            return {}, []

        if IS_WINDOWS:
            node_path_file = os.path.join(config.install_path, 'node_path')
            with open(node_path_file, 'r') as f:
                node_path = f.read().strip()
        else:
            node_link = os.path.join(config.install_path, 'node')
            node_path = os.path.realpath(node_link)
        return (
            {
                'PATH': node_path,
                'NODE_PATH': os.path.join(config.install_path, 'node_modules'),
            },
            [os.path.dirname(node_path), config.install_path],
        )

    def get_dependency_setting(self, language, dependency_name=None):
        dispatchers = {
            'python': self.get_py_deps_setting,
            'javascript': self.get_js_deps_setting,
        }
        if language not in dispatchers:
            raise ValueError(f'Unsupported language: {language}')
        return dispatchers[language](dependency_name)
