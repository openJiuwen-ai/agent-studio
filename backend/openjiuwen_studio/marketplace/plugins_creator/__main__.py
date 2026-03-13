#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Allow running the plugin generator as a module:
python -m openjiuwen_studio.marketplace.plugins_creator.plugins_creator
"""

from .plugins_creator import main

if __name__ == "__main__":
    main()
