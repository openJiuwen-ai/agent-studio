# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import json
import os

import ray
from agent_builder.agent_evolving.agent_rl.config.runtime_config import (
    RolloutConfig,
    TrainingConfig,
)
from agent_builder.agent_evolving.agent_rl.src.rl_trainer_adaptor.coordinator.adaptor import (
    MainTrainer,
)
from agent_builder.agent_evolving.agent_rl.src.rl_trainer_adaptor.verl.dataset import (
    AgentDataset,
)
from agent_builder.agent_evolving.agent_rl.src.rl_trainer_adaptor.verl.training_executor import (
    VerlTrainingExecutor,
)
from agent_builder.agent_evolving.agent_rl.src.utils.logging import get_logger
from hydra import initialize, compose
from omegaconf import OmegaConf
from ray._private.runtime_env.constants import RAY_JOB_CONFIG_JSON_ENV_VAR
from verl.single_controller.ray import RayWorkerGroup
from verl.trainer.main_ppo import create_rl_sampler
from verl.trainer.ppo.ray_trainer import ResourcePoolManager, Role
from verl.trainer.ppo.reward import load_reward_manager
from verl.utils import hf_processor, hf_tokenizer
from verl.utils.fs import copy_to_local
from verl.workers.fsdp_workers import (
    ActorRolloutRefWorker,
    CriticWorker,
    AsyncActorRolloutRefWorker,
)

logger = get_logger(__name__)

PPO_RAY_RUNTIME_ENV = {
    "env_vars": {
        "TOKENIZERS_PARALLELISM": "true",
        "NCCL_DEBUG": "WARN",
        "VLLM_LOGGING_LEVEL": "WARN",
        "VLLM_ALLOW_RUNTIME_LORA_UPDATING": "true",
        "CUDA_DEVICE_MAX_CONNECTIONS": "1",
        "NCCL_CUMEM_ENABLE": "0",
    },
}


def get_ppo_ray_runtime_env():
    """Inherit Ray Job working_dir and merge custom env_vars."""
    working_dir = (
        json.loads(os.environ.get(RAY_JOB_CONFIG_JSON_ENV_VAR, "{}"))
        .get("runtime_env", {})
        .get("working_dir", None)
    )
    runtime_env = {
        "env_vars": PPO_RAY_RUNTIME_ENV["env_vars"].copy(),
        **({"working_dir": None} if working_dir is None else {}),
    }
    # Do not override env vars already set by the caller.
    for key in list(runtime_env["env_vars"].keys()):
        if os.environ.get(key) is not None:
            runtime_env["env_vars"].pop(key, None)
    return runtime_env


@ray.remote(concurrency_groups={"task": 1, "status": 10})
class TaskRunner:
    def __init__(self):
        self.main_trainer = None
        self.init_mode = False

    @classmethod
    def _init_model_components(cls, config):
        """Initialize tokenizer and processor from model config."""
        local_path = copy_to_local(config.actor_rollout_ref.model.path)
        trust_remote_code = config.data.get("trust_remote_code", False)
        tokenizer = hf_tokenizer(local_path, trust_remote_code=trust_remote_code)
        processor = hf_processor(local_path, use_fast=True)
        return tokenizer, processor

    @classmethod
    def _init_worker_mapping(cls, config):
        """Select worker implementation and build role-worker mapping."""
        strategy = config.actor_rollout_ref.actor.strategy
        if strategy not in {"fsdp", "fsdp2"}:
            raise NotImplementedError(f"Unknown strategy: {strategy}")
        is_async = config.actor_rollout_ref.rollout.mode == "async"
        actor_rollout_cls = (
            AsyncActorRolloutRefWorker if is_async else ActorRolloutRefWorker
        )
        role_worker_mapping = {
            Role.ActorRollout: ray.remote(actor_rollout_cls),
            Role.Critic: ray.remote(CriticWorker),
        }
        return role_worker_mapping, RayWorkerGroup

    @classmethod
    def _init_resource_pools(cls, config):
        """Initialize Ray resource pools."""
        global_pool_id = "global_pool"
        resource_pool_spec = {
            global_pool_id: [config.trainer.n_gpus_per_node] * config.trainer.nnodes,
        }
        mapping = {
            Role.ActorRollout: global_pool_id,
            Role.Critic: global_pool_id,
        }
        return ResourcePoolManager(
            resource_pool_spec=resource_pool_spec,
            mapping=mapping,
        )

    @classmethod
    def _init_reward_functions(cls, config, tokenizer):
        """Initialize training and validation reward functions."""
        reward_kwargs = config.reward_model.get("reward_kwargs", {})
        reward_fn = load_reward_manager(
            config, tokenizer, num_examine=0, **reward_kwargs
        )
        val_reward_fn = load_reward_manager(
            config, tokenizer, num_examine=1, **reward_kwargs
        )
        return reward_fn, val_reward_fn

    @classmethod
    def _init_datasets_and_sampler(cls, config, tokenizer, processor):
        """Initialize datasets, collate function, and sampler."""
        from verl.utils.dataset.rl_dataset import collate_fn

        train_dataset = AgentDataset(
            data_files=config.data.train_files,
            tokenizer=tokenizer,
            processor=processor,
            config=config.data,
        )
        val_dataset = AgentDataset(
            data_files=config.data.val_files,
            tokenizer=tokenizer,
            processor=processor,
            config=config.data,
        )
        train_sampler = create_rl_sampler(config.data, train_dataset)
        return train_dataset, val_dataset, collate_fn, train_sampler

    @ray.method(concurrency_group="task")
    def init_trainer(self, config):
        """Initialize trainer components and Ray worker configuration."""
        logger.info(OmegaConf.to_container(config, resolve=True))
        OmegaConf.resolve(config)

        tokenizer, processor = self._init_model_components(config)
        role_worker_mapping, ray_worker_group_cls = self._init_worker_mapping(config)
        resource_pool_manager = self._init_resource_pools(config)
        reward_fn, val_reward_fn = self._init_reward_functions(config, tokenizer)
        train_dataset, val_dataset, collate_fn, train_sampler = (
            self._init_datasets_and_sampler(config, tokenizer, processor)
        )

        verl_trainer = VerlTrainingExecutor(
            config=config,
            tokenizer=tokenizer,
            processor=processor,
            role_worker_mapping=role_worker_mapping,
            resource_pool_manager=resource_pool_manager,
            ray_worker_group_cls=ray_worker_group_cls,
            reward_fn=reward_fn,
            val_reward_fn=val_reward_fn,
            train_dataset=train_dataset,
            val_dataset=val_dataset,
            collate_fn=collate_fn,
            train_sampler=train_sampler,
        )
        verl_trainer.init_workers()

        self.main_trainer = MainTrainer(
            rl_trainer=verl_trainer,
            config=config,
            collate_fn=collate_fn,
            train_sampler=train_sampler,
        )

    @ray.method(concurrency_group="task")
    def start_trainer(self, proxy_endpoint, env_info):
        """
        Start the training process with the given environment information.
        """
        if self.main_trainer is None:
            raise RuntimeError("MainTrainer not initialized.")
        if self.init_mode:
            self.main_trainer.rl_trainer.sleep_rollout()
            self.init_mode = False
        self.main_trainer.fit(proxy_endpoint, env_info)

    @ray.method(concurrency_group="task")
    def wake_up_rollout(self):
        """Wake up rollout mode for proxy test."""
        self.init_mode = True
        return self.main_trainer.rl_trainer.wake_up_rollout()

    @ray.method(concurrency_group="status")
    def get_status(self):
        """Get the training status of main trainer."""
        return self.main_trainer.status

    @ray.method(concurrency_group="task")
    def get_error(self):
        """Get the training error during training."""
        return self.main_trainer.error_msg


def bool_str(v: bool) -> str:
    """Convert a boolean value to its string representation."""
    return "True" if v else "False"


def init_ray_server(train_cfg: TrainingConfig, rollout_cfg: RolloutConfig):
    """
    Initialize the Ray server with training and rollout configuration.
    """
    if train_cfg.algorithm_adv_estimator not in ["grpo"]:
        raise ValueError(
            f"Algorithm '{train_cfg.algorithm_adv_estimator}' is not supported. "
            f"Currently only 'grpo' is supported."
        )
    overrides = [
        f"algorithm.adv_estimator={train_cfg.algorithm_adv_estimator}",
        f"data.train_files={train_cfg.train_data_path}",
        f"data.val_files={train_cfg.val_data_path}",
        "actor_rollout_ref.rollout.tensor_model_parallel_size=1",
        f"data.train_batch_size={train_cfg.train_batch_size}",
        "++actor_rollout_ref.rollout.enforce_eager=true",
        f"actor_rollout_ref.rollout.n={rollout_cfg.rollout_n}",
        f"actor_rollout_ref.actor.ppo_mini_batch_size={train_cfg.ppo_mini_batch_size}",
        f"actor_rollout_ref.actor.ppo_micro_batch_size_per_gpu={train_cfg.micro_batch_size_per_gpu}",
        f"actor_rollout_ref.rollout.log_prob_micro_batch_size_per_gpu={train_cfg.micro_batch_size_per_gpu}",
        "actor_rollout_ref.rollout.multi_turn.format=hermes",
        f"actor_rollout_ref.model.path={train_cfg.model_path}",
        f"data.max_prompt_length={train_cfg.max_prompt_length}",
        f"data.max_response_length={train_cfg.max_response_length}",
        "data.truncation=truncate",
        f"trainer.val_before_train={bool_str(train_cfg.val_before_train)}",
        f"actor_rollout_ref.actor.optim.lr={rollout_cfg.actor_optimizer_lr}",
        "actor_rollout_ref.model.use_remove_padding=True",
        f"actor_rollout_ref.actor.use_kl_loss={bool_str(rollout_cfg.actor_use_kl_loss)}",
        f"actor_rollout_ref.actor.kl_loss_coef={rollout_cfg.actor_kl_loss_coef}",
        f"actor_rollout_ref.actor.entropy_coeff={rollout_cfg.actor_entropy_coef}",
        f"actor_rollout_ref.actor.clip_ratio_low={rollout_cfg.actor_clip_ratio_low}",
        f"actor_rollout_ref.actor.clip_ratio_high={rollout_cfg.actor_clip_ratio_high}",
        "actor_rollout_ref.model.enable_gradient_checkpointing=True",
        "actor_rollout_ref.actor.fsdp_config.param_offload=True",
        "actor_rollout_ref.actor.fsdp_config.optimizer_offload=True",
        "actor_rollout_ref.rollout.name=vllm",
        "actor_rollout_ref.rollout.gpu_memory_utilization=0.7",
        f"actor_rollout_ref.ref.log_prob_micro_batch_size_per_gpu={train_cfg.micro_batch_size_per_gpu}",
        "actor_rollout_ref.ref.fsdp_config.param_offload=True",
        "actor_rollout_ref.rollout.enable_chunked_prefill=False",
        f"algorithm.use_kl_in_reward={bool_str(train_cfg.algorithm_use_kl_in_reward)}",
        "trainer.critic_warmup=0",
        'trainer.logger=["console","tensorboard"]',
        f"trainer.project_name={train_cfg.project_name}",
        f"trainer.experiment_name={train_cfg.experiment_name}",
        f"trainer.nnodes={train_cfg.nnodes}",
        f"trainer.save_freq={train_cfg.save_freq}",
        f"trainer.test_freq={train_cfg.test_freq}",
        f"trainer.default_local_dir={train_cfg.save_path}",
        f"trainer.total_epochs={train_cfg.epoch_num}",
        "trainer.device=npu",
        "+trainer.runtime_parallel_num=10",
        f"+trainer.rollout_max_round={rollout_cfg.rollout_max_round}",
        "reward_model.reward_manager=naive",
        f"trainer.n_gpus_per_node={train_cfg.n_gpus_per_node}",
        "+actor_rollout_ref.rollout.engine_kwargs.vllm.enable_auto_tool_choice=true",
        "+actor_rollout_ref.rollout.engine_kwargs.vllm.tool_call_parser=hermes",
        "+JiuwenRL.custom_fn.classifier=default_classify_rollouts",
        "+JiuwenRL.custom_fn.validator=default_validate_stop",
        "+JiuwenRL.custom_fn.sampler=default_sampling",
    ]
    # Keep config_path/config_name consistent with your hydra entry.
    with initialize(config_path="", version_base=None):
        cfg = compose(config_name="config", overrides=overrides)
    # Keep env vars as-is.
    os.environ["ASCEND_RT_VISIBLE_DEVICES"] = train_cfg.visible_device
    os.environ["HYDRA_FULL_ERROR"] = "1"
    os.environ["VLLM_PREFIX_CACHING"] = "0"
    os.environ["ENABLE_PREFIX_CACHE"] = "false"
    os.environ["TORCHINDUCTOR_COMPILE"] = "0"
    os.environ["TORCHDYNAMO_DISABLE"] = "1"
    os.environ["VLLM_ASCEND_DISABLE_CAMEM"] = "1"
    os.environ["DISABLE_CAMEM_ALLOCATOR"] = "1"
    os.environ["VLLM_DISABLE_COMPILE_CACHE"] = "1"
    os.environ["VLLM_ASCEND_CAMEM_ENABLE"] = "0"
    os.environ["ASCEND_LAUNCHING_BLOCKING"] = "1"
    os.environ["VLLM_USE_V1"] = "1"
    os.environ["VLLM_ASCEND_ENABLE_NZ"] = "0"
    for k in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"]:
        os.environ.pop(k, None)
    os.environ["no_proxy"] = "127.0.0.1,localhost"
    os.environ["NO_PROXY"] = "127.0.0.1,localhost"
    if not ray.is_initialized():
        default_runtime_env = get_ppo_ray_runtime_env()
        ray_init_kwargs = cfg.ray_kwargs.get("ray_init", {})
        runtime_env_kwargs = ray_init_kwargs.get("runtime_env", {})
        runtime_env = OmegaConf.merge(default_runtime_env, runtime_env_kwargs)
        ray_init_kwargs = OmegaConf.create(
            {**ray_init_kwargs, "runtime_env": runtime_env, "namespace": "JiuwenRL"}
        )
        logger.info(f"ray init kwargs: {ray_init_kwargs}")
        ray.init(**OmegaConf.to_container(ray_init_kwargs))
    return cfg


def init_trainer(task_id: str, train_cfg: TrainingConfig, rollout_cfg: RolloutConfig):
    """
    Initialize the training TaskRunner and its trainer components.
    """

    cfg = init_ray_server(train_cfg, rollout_cfg)
    runner = TaskRunner.options(name=task_id, lifetime="detached").remote()
    ray.get(runner.init_trainer.remote(cfg))


def init_inf(task_id: str, train_cfg: TrainingConfig, rollout_cfg: RolloutConfig):
    """
    Initialize TaskRunner for inference and start the rollout service.
    """
    cfg = init_ray_server(train_cfg, rollout_cfg)
    runner = TaskRunner.options(name=task_id, lifetime="detached").remote()
    ray.get(runner.init_trainer.remote(cfg))
    server_address = ray.get(runner.wake_up_rollout.remote())
    return server_address


def start_trainer(task_id, proxy_endpoint, env_info):
    """
    Start the training process on the remote TaskRunner.
    """
    try:
        runner = ray.get_actor(task_id)
    except ValueError as e:
        raise RuntimeError("TaskRunner actor not found. Run init_trainer first.") from e
    runner.start_trainer.remote(proxy_endpoint, env_info)
    return runner


def stop_ray_service(task_id):
    """Kill the detached TaskRunner actor and shutdown Ray."""
    try:
        actor = ray.get_actor(task_id)
        ray.kill(actor, no_restart=True)
    except ValueError:
        logger.info(f"No Ray actor named {task_id} running.")
    logger.info("Ray shutdown complete")


def get_trainer_status(task_id):
    """Get the training status of main trainer."""
    try:
        runner = ray.get_actor(task_id)
    except ValueError as e:
        raise RuntimeError("TaskRunner actor not found. Run init_trainer first.") from e
    status = ray.get(runner.get_status.remote())
    return status


def get_trainer_error(task_id):
    """Get the training error during training."""
    try:
        runner = ray.get_actor(task_id)
    except ValueError as e:
        raise RuntimeError("TaskRunner actor not found. Run init_trainer first.") from e
    error_msg = ray.get(runner.get_error.remote())
    return error_msg
