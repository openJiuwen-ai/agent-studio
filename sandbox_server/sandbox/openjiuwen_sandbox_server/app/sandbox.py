#!/usr/bin/env python3
import sys

from .base import BaseSandbox
from .local import LocalRunner  # noqa: F401 — registers 'local'

if sys.platform == 'linux':
    from .bwrap import BubbleWrapRunner  # noqa: F401 — registers 'bubblewrap'


def get_sandbox_class(sandbox_type, config):
    """Resolve sandbox type string to the corresponding class."""
    sandbox_type = sandbox_type or config.sandbox['type']
    return BaseSandbox.get_class(sandbox_type)
