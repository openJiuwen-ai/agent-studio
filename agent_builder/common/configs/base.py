#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""Class for reading the config.yaml configuration file"""

import os

import yaml


class SingletonConfig:
    """Reading the config.yaml configuration file"""

    __instance: yaml.constructor = None

    def __init__(self):
        if SingletonConfig.__instance is not None:
            raise Exception("This class is a singleton!")

        log_config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "../../config.yaml"
        )
        with open(log_config_path, encoding="utf-8") as file:
            # 加载配置文件
            SingletonConfig.__instance = yaml.safe_load(file)

    @staticmethod
    def get_config():
        """Obtaining Configuration Instances"""
        if SingletonConfig.__instance is None:
            SingletonConfig()
        return SingletonConfig.__instance


config = SingletonConfig.get_config()
