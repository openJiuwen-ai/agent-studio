/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 智能体关联的Skill详情。
 */
@ApiModel(description = "智能体关联的Skill详情。")

@Validated

public class AgentSkillDetail implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("skill_id")
    @Schema(description = "技能ID", example = "skill_001")
    private String skillId = null;

    @JsonProperty("skill_version")
    @Schema(description = "技能版本", example = "v1.0.0")
    private String skillVersion = null;

    public String getSkillId() {
        return skillId;
    }

    public AgentSkillDetail setSkillId(String skillId) {
        this.skillId = skillId;
        return this;
    }

    public String getSkillVersion() {
        return skillVersion;
    }

    public AgentSkillDetail setSkillVersion(String skillVersion) {
        this.skillVersion = skillVersion;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class AgentSkillDetail {\n");

        sb.append("    skillId: ").append(toIndentedString(skillId)).append("\n");
        sb.append("    skillVersion: ").append(toIndentedString(skillVersion)).append("\n");
        sb.append("}");
        return sb.toString();
    }

    @Override
    public boolean equals(Object obj) {
        if (this == obj) {
            return true;
        }
        if (obj == null || getClass() != obj.getClass()) {
            return false;
        }
        AgentSkillDetail agentSkillDetail = (AgentSkillDetail) obj;
        return Objects.equals(this.skillId, agentSkillDetail.skillId) && Objects.equals(this.skillVersion,
            agentSkillDetail.skillVersion);
    }

    @Override
    public int hashCode() {
        return Objects.hash(skillId, skillVersion);
    }

    private String toIndentedString(Object obj) {
        if (obj == null) {
            return "null";
        }
        return obj.toString().replace("\n", "\n    ");
    }
}
