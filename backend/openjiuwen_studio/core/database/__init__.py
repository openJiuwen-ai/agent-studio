#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import sys
import importlib.util
from pathlib import Path
# Import migration utilities
from .migration_utils import table_exists, column_exists, index_exists

# Import from database.py module to maintain backward compatibility

# Add parent directory to path to import database.py
_db_module_path = Path(__file__).parent.parent / 'database.py'
spec = importlib.util.spec_from_file_location("openjiuwen_studio.core.database._module", _db_module_path)
_db_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_db_module)

# Re-export everything from database.py
for attr in dir(_db_module):
    if not attr.startswith('_'):
        globals()[attr] = getattr(_db_module, attr)

__all__ = ['table_exists', 'column_exists', 'index_exists']
