# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""
prompt tuning cases
"""

from agent_builder.prompt.tune.base.constant import TuneConstant


class ApoTuneConstant(TuneConstant):
    """
    A class that contains all the common constants used in the tuning module.
    """

    """ 消息关键字常量 """
    VARIABLE_TYPE_KEY: str = "variable_type"
    IMAGE_TYPE_VAR_KEY: str = "image"
    TEXT_TYPE_VAR_KEY: str = "text"

    """ 优化参数默认值 """
    DEFAULT_MINIBATCH_SIZE = 30
    DEFAULT_SAMPLED_ERROR_NUM = 4
    DEFAULT_GRADIENTS_PER_ERROR = 2
    DEFAULT_N_GRADIENTS = 1
    DEFAULT_BEAM_SIZE = 3
    DEFAULT_NUM_ITER = 10
    DEFAULT_MAX_EXPANSION_FACTOR = 2
    DEFAULT_EVAL_BUDGET = 15
    DEFAULT_MC_SAMPLES_PER_STEP = False
