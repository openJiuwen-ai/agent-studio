#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""
LLM Service Base
"""

import importlib.util
import json
import os
import sys
from typing import Callable, Optional

from jiuwen.common.configs.env_constants import DEFAULT_MODELS_KEY, MODEL_DIR_KEY
from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.llm_service.language_model.base import BaseChatModel
from jiuwen.common.log.base import logger
from jiuwen.common.security.util.fileutil import validate_path_traversal
from jiuwen.common.utils.singleton import Singleton


def default_model_resolver(model_type, model_name, **kwargs) -> Optional[dict]:
    """get default model config information"""
    model_dict_str = os.environ.get(DEFAULT_MODELS_KEY, "{}")
    try:
        model_dict = json.loads(model_dict_str)
        return model_dict.get(model_type, {}).get(model_name)
    except Exception as err:
        raise JiuWenBaseException(
            StatusCode.LLM_RESOLVER_DECODER_ERROR.code,
            StatusCode.LLM_RESOLVER_DECODER_ERROR.errmsg.format(
                error_msg=f"default_models error: Decoder error: {err}"
            ),
        ) from err


class ModelFactory(metaclass=Singleton):
    """Model Factory"""

    def __init__(self):
        """init Model Factory"""
        self.model_map = {}
        current_dir = os.path.dirname(os.path.abspath(__file__))
        default_model_dir = os.path.join(current_dir, "language_model")
        self._load_model_dir(default_model_dir)
        custom_model_dir = os.getenv(MODEL_DIR_KEY, None)  # "/path/to/custom/models"
        if custom_model_dir:
            validate_path_traversal(custom_model_dir)
            self._load_model_dir(custom_model_dir)
        self.default_model_resolver = default_model_resolver
        self.model_resolver = None

    @staticmethod
    def _load_models(model_dir):
        """load models from model_dir"""
        try:
            py_files = [
                f
                for f in os.listdir(model_dir)
                if (f.endswith(".py") or f.endswith(".pyc"))
                and f != "base.py"
                and f != "base.pyc"
                and ".." not in f
            ]
            modules_name = [
                os.path.splitext(os.path.basename(item))[0] for item in py_files
            ]
            model_dict = {}
            for module_name, path_name in zip(modules_name, py_files):
                spec = importlib.util.spec_from_file_location(
                    module_name, os.path.join(model_dir, path_name)
                )
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                for obj in module.__dict__.values():
                    if (
                        isinstance(obj, type)
                        and issubclass(obj, BaseChatModel)
                        and obj != BaseChatModel
                    ):
                        model_dict.update({module_name: obj})
        except Exception as e:
            raise JiuWenBaseException(
                StatusCode.LLM_LOAD_ERROR.code,
                StatusCode.LLM_LOAD_ERROR.errmsg.format(
                    error_msg=f"please check model file path: {e}"
                ),
            ) from e

        return model_dict

    def get_model(self, model_type, model_name, temperature=0.5, top_p=0.5, **kwargs):
        """get model instance by model_type and model_name
        Args:
            model_type: consistent with model class type which defined by user or default
            model_name: model real name
            temperature: temperature
            top_p: top_p
            kwargs: other params
        """
        if self.model_resolver:
            model_config = self.model_resolver(
                model_type, model_name, **kwargs
            ) or self.default_model_resolver(model_type, model_name, **kwargs)
        else:
            model_config = self.default_model_resolver(model_type, model_name, **kwargs)
        if not model_config:
            raise JiuWenBaseException(
                StatusCode.LLM_LOAD_ERROR.code,
                StatusCode.LLM_LOAD_ERROR.errmsg.format(
                    error_msg="Unable to obtain the configuration information of the model, please check "
                    "model configuration is correct"
                ),
            )

        model_config["model_name"] = model_name
        model_config["temperature"] = temperature
        model_config["top_p"] = top_p
        model_config.update(kwargs)
        model_cls = self.model_map.get(model_type, None)
        if not model_cls:
            raise JiuWenBaseException(
                StatusCode.LLM_TYPE_ERROR.code,
                StatusCode.LLM_TYPE_ERROR.errmsg.format(error_msg="model type error"),
            )

        model = model_cls(**model_config)

        return model

    def init_resolver(self, model_resolver: Callable = None):
        """init model resolver"""
        self.model_resolver = model_resolver

    def _load_model_dir(self, model_dir=None):
        """load available model"""
        if model_dir:
            model_dict = self._load_models(model_dir)
            self.model_map.update(model_dict)
