#!/usr/bin/env python3
import os

import yaml


class SandboxConfig:
    """Proxy object that loads sandbox_config.yaml and exposes keys as attributes."""

    def __init__(self, config_file=None):
        config_file = config_file or os.path.join(
            os.path.dirname(__file__), '..', 'conf', 'sandbox_config.yaml'
        )
        with open(config_file, 'r') as f:
            object.__setattr__(self, '_config', yaml.safe_load(f))

    def __getattr__(self, key):
        try:
            return self._config[key]
        except KeyError as e:
            raise AttributeError(f"Sandbox config has no key: '{key}'") from e

    def __setattr__(self, key, value):
        self._config[key] = value
