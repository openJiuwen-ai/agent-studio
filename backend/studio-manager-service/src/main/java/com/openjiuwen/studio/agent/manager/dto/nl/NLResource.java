/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto.nl;

import com.fasterxml.jackson.annotation.JsonProperty;

import jakarta.validation.Valid;
import lombok.Getter;
import lombok.Setter;

import org.springframework.validation.annotation.Validated;

@Getter
@Setter
@Validated
public class NLResource {
    @JsonProperty("plugins")
    @Valid
    private PluginList plugins;

    @JsonProperty("workflows")
    @Valid
    private WorkflowList workflows;

    @JsonProperty("knowledge_base")
    @Valid
    private KnowledgeList knowledgeBase;

    @JsonProperty("skills")
    @Valid
    private SkillList skills;
}
