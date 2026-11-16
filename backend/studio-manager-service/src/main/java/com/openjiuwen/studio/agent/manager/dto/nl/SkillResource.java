/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto.nl;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.Getter;
import lombok.Setter;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

/**
 * NL2Agent 请求体的技能目录条目。
 * 仅包含目录元数据，不包含 SKILL.md 正文与 OBS 存储路径。
 */
@Getter
@Setter
@Validated
public class SkillResource {
    @JsonProperty("skill_id")
    @Length(max = 200)
    private String skillId;

    @JsonProperty("skill_name")
    @Length(max = 200)
    private String skillName;

    @JsonProperty("description")
    @Length(max = 1024)
    private String description;

    @JsonProperty("icon")
    @Length(max = 1024)
    private String icon;

    @JsonProperty("last_version_id")
    @Length(max = 200)
    private String lastVersionId;
}
