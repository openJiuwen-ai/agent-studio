# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import importlib
import os
from abc import ABC, abstractmethod
from collections.abc import Sized
from typing import Optional

import torch
from omegaconf import DictConfig
from torch.utils.data import RandomSampler, SequentialSampler, Sampler

PKG_PREFIX = "pkg://"
FILE_PREFIX = "file://"


def load_extern_type(file_path: Optional[str], type_name: Optional[str]) -> type:
    """Load an external data type based on the file path and type name."""
    if not file_path:
        return None

    if file_path.startswith(PKG_PREFIX):
        module_name = file_path[len(PKG_PREFIX) :].replace("/", ".")
        module = importlib.import_module(module_name)
    else:
        if file_path.startswith(FILE_PREFIX):
            file_path = file_path[len(FILE_PREFIX) :]

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Custom type file '{file_path}' not found.")

        spec = importlib.util.spec_from_file_location("custom_module", file_path)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            raise RuntimeError(f"Error loading module from '{file_path}'") from e

    if not hasattr(module, type_name):
        raise AttributeError(f"Custom type '{type_name}' not found in '{file_path}'.")

    return getattr(module, type_name)


class AbstractSampler(Sampler[int], ABC):
    """Abstract interface for custom samplers."""

    @abstractmethod
    def __init__(self, data_source: Sized, data_config: DictConfig):
        pass


def create_rl_sampler(data_config, dataset):
    """Create a sampler for the dataset."""
    if (
        data_config.sampler is not None
        and data_config.sampler.get("class_path", None) is not None
    ):
        curriculum_class = load_extern_type(
            data_config.sampler.class_path, data_config.sampler.class_name
        )
        sampler = curriculum_class(data_source=dataset, data_config=data_config)
        if not isinstance(sampler, AbstractSampler):
            raise TypeError(
                f"Curriculum sampler must inherit from AbstractSampler, "
                f"got {type(sampler)}"
            )
        num_workers = data_config.get("dataloader_num_workers", 8)
        if num_workers != 0:
            raise ValueError(
                "If using curriculum sampler, dataloader_num_workers must be 0. "
                "DataLoader caching would prevent curriculum reordering."
            )
    elif data_config.shuffle:
        train_dataloader_generator = torch.Generator()
        train_dataloader_generator.manual_seed(data_config.get("seed", 1))
        sampler = RandomSampler(
            data_source=dataset, generator=train_dataloader_generator
        )
    else:
        sampler = SequentialSampler(data_source=dataset)
    return sampler
