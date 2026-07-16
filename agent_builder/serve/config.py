#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.

"""parse config file"""

import yaml


def load_config(config):
    """load config from the setting file"""
    try:
        with open(config, "r", encoding="utf-8") as config_file:
            config_dict = yaml.safe_load(config_file)
        return config_dict
    except Exception as e:
        raise ValueError("load yaml file failed") from e
