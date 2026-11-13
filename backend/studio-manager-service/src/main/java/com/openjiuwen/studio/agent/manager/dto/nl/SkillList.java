/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto.nl;

import com.fasterxml.jackson.annotation.JsonProperty;

import jakarta.validation.Valid;
import lombok.Getter;
import lombok.Setter;

import org.springframework.validation.annotation.Validated;

import java.util.List;

@Getter
@Setter
@Validated
public class SkillList {
    @JsonProperty("skill_list")
    @Valid
    private List<SkillResource> skillList;
}
