# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import List, Dict, Tuple

from agent_builder.agent_evolving.agent_rl.src.runtime_and_sampler_adaptor.base import (
    RolloutWithReward,
)


class RolloutClassifier:
    """
    Provides rollout classification utilities that separate positive and negative
    rollout samples based on their reward values.
    """

    @staticmethod
    def default_classify_rollouts(
        mdp_list: List[RolloutWithReward],
    ) -> Tuple[List[RolloutWithReward], List[RolloutWithReward]]:
        """
        Classify rollout steps into positive and negative lists according to reward values.
        Returns a dictionary keyed by rollout ID containing (pos_list, neg_list).
        """
        pos_rollouts = []
        neg_rollouts = []
        for mdp in mdp_list:
            if mdp.reward > 0:
                pos_rollouts.append(mdp)
            else:
                neg_rollouts.append(mdp)
        return pos_rollouts, neg_rollouts


class RolloutValidator:
    """
    Validation utilities for determining when rollout collection for a prompt
    should stop based on accumulated positive and negative samples.
    """

    @staticmethod
    def default_validate_stop(
        pos_rollout_list: List[RolloutWithReward],
        neg_rollout_list: List[RolloutWithReward],
    ) -> bool:
        """
        Stop when at least two positive samples exist and one of them
        achieves a reward >= 1.0.
        """
        if len(neg_rollout_list) > len(pos_rollout_list):
            return False
        if len(pos_rollout_list) < 2:
            return False
        for rollout in pos_rollout_list:
            if rollout.reward == 1.0:
                return True
        return False

    @staticmethod
    def validate_stop_balanced(
        pos_rollout_list: List[RolloutWithReward],
        neg_rollout_list: List[RolloutWithReward],
        final_keep_per_prompt: int = 8,
    ) -> bool:
        """
        Balanced stopping rule:
        Stop only when both positive and negative rollout counts meet their
        respective target amounts derived from the desired total.
        """
        target_pos = final_keep_per_prompt // 2
        target_neg = final_keep_per_prompt - target_pos

        if len(pos_rollout_list) < target_pos:
            return False
        if len(neg_rollout_list) < target_neg:
            return False
        return True


class RolloutSampling:
    """
    Sampling strategies used to select subsets of rollout samples for downstream
    training, including balanced and default sampling modes.
    """

    @staticmethod
    def default_sampling(
        pos_rollout_dict: Dict[str, List[RolloutWithReward]],
        neg_rollout_dict: Dict[str, List[RolloutWithReward]],
    ) -> Tuple[Dict[str, List[RolloutWithReward]], Dict[str, List[RolloutWithReward]]]:
        """Return the dictionaries unchanged (identity sampling)."""
        return pos_rollout_dict, neg_rollout_dict

    @staticmethod
    def downsample_one_uid(
        pos_list: List[RolloutWithReward],
        neg_list: List[RolloutWithReward],
        target_total: int = 8,
    ) -> Tuple[List[RolloutWithReward], List[RolloutWithReward]]:
        """
        Downsample positive and negative samples for a single UID toward a
        balanced target total. Attempts to approximate a 50/50 split, then fills
        remaining quota from whichever side has surplus.
        """
        target_pos = min(target_total // 2, len(pos_list))
        target_neg = min(target_total - target_pos, len(neg_list))

        if target_pos + target_neg < target_total:
            remaining = target_total - (target_pos + target_neg)

            extra_pos_cap = len(pos_list) - target_pos
            if extra_pos_cap > 0:
                add = min(extra_pos_cap, remaining)
                target_pos += add
                remaining -= add

            if remaining > 0:
                extra_neg_cap = len(neg_list) - target_neg
                if extra_neg_cap > 0:
                    add = min(extra_neg_cap, remaining)
                    target_neg += add
                    remaining -= add

        pos_selected = pos_list[:target_pos]
        neg_selected = neg_list[:target_neg]
        return pos_selected, neg_selected

    @staticmethod
    def sampling_ada(
        pos_rollout_dict: Dict[str, List[RolloutWithReward]],
        neg_rollout_dict: Dict[str, List[RolloutWithReward]],
        final_keep_per_prompt: int = 8,
    ) -> Tuple[
        Dict[str, List[RolloutWithReward]],
        Dict[str, List[RolloutWithReward]],
    ]:
        """
        Perform balanced sampling for each UID by downsampling positive and
        negative rollout lists toward a fixed total target.
        """
        out_pos: Dict[str, List[RolloutWithReward]] = {}
        out_neg: Dict[str, List[RolloutWithReward]] = {}

        all_uids = set(pos_rollout_dict.keys()) | set(neg_rollout_dict.keys())
        for uid in all_uids:
            pos_list = pos_rollout_dict.get(uid, [])
            neg_list = neg_rollout_dict.get(uid, [])

            if not pos_list and not neg_list:
                continue

            pos_sel, neg_sel = RolloutSampling.downsample_one_uid(
                pos_list, neg_list, target_total=final_keep_per_prompt
            )
            out_pos[uid] = pos_sel
            out_neg[uid] = neg_sel

        return out_pos, out_neg
