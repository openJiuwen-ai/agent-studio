# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, ConfigDict


class TrainingConfig(BaseModel):
    project_name: str = Field(default="JiuwenAgentRL")
    experiment_name: str = Field(default="agentBuilder_calx")
    train_data_path: str = Field(...)
    val_data_path: str = Field(...)
    model_path: str = Field(...)
    save_path: str = Field(...)
    s3_model_path: str = Field(...)
    s3_save_path: str = Field(...)
    algorithm_adv_estimator: str = "grpo"
    algorithm_use_kl_in_reward: bool = False
    epoch_num: int = Field(2, gt=0)
    save_freq: int = Field(25, gt=0)
    test_freq: int = Field(25, gt=0)
    train_batch_size: int = Field(16, gt=0)
    visible_device: str = "4,5,6,7"
    nnodes: int = Field(1, gt=0)
    n_gpus_per_node: int = Field(4, gt=0)
    micro_batch_size_per_gpu: int = Field(4, gt=0)
    max_prompt_length: int = Field(2048, gt=0)
    max_response_length: int = Field(1536, gt=0)
    val_before_train: bool = True
    ppo_mini_batch_size: int = Field(8, gt=0)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("model_path")
    @classmethod
    def validate_hf_model_dir(cls, dir_path: str):
        """Validate that the given path is a local HuggingFace model directory."""
        path = Path(dir_path)
        if not path.exists():
            raise ValueError(f"Model path does not exist: {dir_path}.")
        if not path.is_dir():
            raise ValueError(f"Model path is not a directory: {dir_path}.")
        # Required files
        if not (path / "config.json").exists():
            raise ValueError("Missing config.json (not a valid HF model directory).")
        weight_files = ["model.safetensors", "pytorch_model.bin"]
        if not any((path / file).exists() for file in weight_files):
            raise ValueError("Missing model weight file (.safetensors or .bin).")
        tokenizer_files = ["tokenizer.json", "tokenizer.model", "vocab.txt"]
        if not any((path / file).exists() for file in tokenizer_files):
            raise ValueError("Missing tokenizer files.")
        return dir_path


class RolloutConfig(BaseModel):
    actor_optimizer_lr: float = 1e-6
    actor_use_kl_loss: bool = False
    actor_kl_loss_coef: float = 0.0
    actor_entropy_coef: float = 0.0
    actor_clip_ratio_low: float = 0.2
    actor_clip_ratio_high: float = 0.3
    rollout_n: int = Field(4, gt=1)
    rollout_max_round: int = Field(1, gt=0)

    model_config = ConfigDict(validate_assignment=True)
