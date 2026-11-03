# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""卷挂载 .py 注入示例（REDIS_PROVIDER=/opt/plugins/demo.py:AcmeDemoProvider）。

运维只挂载这一个文件即可启用 demo Provider——演示"文件路径注入"形态：
工厂从 .py 定位类（须继承 redis_spi.RedisProvider）并实例化。
类本体来自已安装的 redis_demo_provider 包；企业场景把这个文件换成
自研实现的单文件版（或薄壳 re-export）。
"""

from redis_demo_provider.provider import AcmeDemoProvider

__all__ = ["AcmeDemoProvider"]
