# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import importlib
import inspect

from agent_builder.agent_evolving.agent_rl.src.utils.logging import get_logger

logger = get_logger(__name__)


class ProcessorsRegistry:
    """A registry for managing classifier, validator, and sampler processing
    functions used throughout the rollout and RL training pipeline.

    This registry supports:
    - Manual function registration via decorators (`register_classifier`,
      `register_validator`, `register_sampler`)
    - Automatic discovery of processing functions from the
      `extensions.processors` module
    - Retrieval of registered functions by name
    - Listing available classifier/validator/sampler functions

    It serves as a central plugin-like mechanism that allows users to extend
    rollout classification, validation, and sampling strategies without
    modifying core training code.
    """

    def __init__(self):
        """Initialize registries and automatically load predefined processors."""
        self._classifiers = {}
        self._validators = {}
        self._samplers = {}
        self._load_predefined_functions()

    def register_classifier(self, name=None):
        """Decorator for registering a classifier function with an optional custom name."""

        def decorator(func):
            classifier_name = name or func.__name__
            if classifier_name in self._classifiers:
                raise ValueError(
                    f"Classifier function '{classifier_name}' already exists"
                )
            self._classifiers[classifier_name] = func
            return func

        return decorator

    def register_validator(self, name=None):
        """Decorator for registering a validator function with an optional custom name."""

        def decorator(func):
            validator_name = name or func.__name__
            if validator_name in self._validators:
                raise ValueError(
                    f"Validator function '{validator_name}' already exists"
                )
            self._validators[validator_name] = func
            return func

        return decorator

    def register_sampler(self, name=None):
        """Decorator for registering a sampler function with an optional custom name."""

        def decorator(func):
            sampler_name = name or func.__name__
            if sampler_name in self._samplers:
                raise ValueError(f"Sampler function '{sampler_name}' already exists")
            self._samplers[sampler_name] = func
            return func

        return decorator

    def get_classifier(self, name):
        """Retrieve a classifier function by name, raising an error if not found."""
        if name in self._classifiers:
            return self._classifiers[name]
        raise ValueError(f"Classifier function '{name}' not found")

    def get_validator(self, name):
        """Retrieve a validator function by name, raising an error if not found."""
        if name in self._validators:
            return self._validators[name]
        raise ValueError(f"Validator function '{name}' not found")

    def get_sampler(self, name):
        """Retrieve a sampler function by name, raising an error if not found."""
        if name in self._samplers:
            return self._samplers[name]
        raise ValueError(f"Sampler function '{name}' not found")

    def list_classifiers(self):
        """Return a list of all registered classifier function names."""
        return list(self._classifiers.keys())

    def list_validators(self):
        """Return a list of all registered validator function names."""
        return list(self._validators.keys())

    def list_samplers(self):
        """Return a list of all registered sampler function names."""
        return list(self._samplers.keys())

    def classify_rollouts(self, classifier_name, rollouts):
        """Execute the classifier function specified by name on the given rollouts."""
        classifier_fn = self.get_classifier(classifier_name)
        return classifier_fn(rollouts)

    def validate_rollout(self, validator_name, pos_rollout_list, neg_rollout_list):
        """Execute the validator function specified by name on positive and negative rollouts."""
        validator_fn = self.get_validator(validator_name)
        return validator_fn(pos_rollout_list, neg_rollout_list)

    def sample_rollouts(self, sampler_name, pos_rollout_list, neg_rollout_list):
        """Execute the sampler function specified by name on rollout lists."""
        sampler_fn = self.get_sampler(sampler_name)
        return sampler_fn(pos_rollout_list, neg_rollout_list)

    def _load_predefined_functions(self):
        """Automatically load processing functions from `extensions.processors`
        by scanning public methods of RolloutClassifier, RolloutValidator, and
        RolloutSampling classes.
        """
        try:
            module = importlib.import_module(
                "agent_builder.agent_evolving.agent_rl.extensions.processors"
            )

            if hasattr(module, "RolloutClassifier"):
                for method_name, method in inspect.getmembers(
                    module.RolloutClassifier, predicate=inspect.isfunction
                ):
                    if not method_name.startswith("_"):
                        self._classifiers[method_name] = method

            if hasattr(module, "RolloutValidator"):
                for method_name, method in inspect.getmembers(
                    module.RolloutValidator, predicate=inspect.isfunction
                ):
                    if not method_name.startswith("_"):
                        self._validators[method_name] = method

            if hasattr(module, "RolloutSampling"):
                for method_name, method in inspect.getmembers(
                    module.RolloutSampling, predicate=inspect.isfunction
                ):
                    if not method_name.startswith("_"):
                        self._samplers[method_name] = method

        except ImportError:
            logger.error("Failed to import extensions.processors module")
            raise
