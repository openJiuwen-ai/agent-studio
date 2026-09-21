/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 关联的skill对象。
 */
@ApiModel(description = "关联的skill对象。")

@Validated

public class SkillReference implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("skill_id")
    @Schema(description = "技能ID", example = "skill_001")
    private String skillId = null;

    @JsonProperty("skill_name")
    @Schema(description = "技能名称", example = "天气查询")
    private String skillName = null;

    @JsonProperty("description")
    @Schema(description = "技能描述", example = "查询指定城市的天气信息")
    @Length(min = 1, max = 1024)
    private String description = null;

    @JsonProperty("icon")
    @Schema(description = "技能图标", example = "icon_url")
    private String icon = null;

    @JsonProperty("last_version_id")
    @Schema(description = "最新版本ID", example = "v1.0.0")
    private String lastVersionId = null;

    public String getSkillId() {
        return skillId;
    }

    public SkillReference setSkillId(String skillId) {
        this.skillId = skillId;
        return this;
    }

    public String getSkillName() {
        return skillName;
    }

    public SkillReference setSkillName(String skillName) {
        this.skillName = skillName;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public SkillReference setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public SkillReference setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public String getLastVersionId() {
        return lastVersionId;
    }

    public SkillReference setLastVersionId(String lastVersionId) {
        this.lastVersionId = lastVersionId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class SkillReference {\n");

        sb.append("    skillId: ").append(toIndentedString(skillId)).append("\n");
        sb.append("    skillName: ").append(toIndentedString(skillName)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    lastVersionId: ").append(toIndentedString(lastVersionId)).append("\n");
        sb.append("}");
        return sb.toString();
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (o == null || getClass() != o.getClass()) {
            return false;
        }
        SkillReference skillReference = (SkillReference) o;
        return Objects.equals(this.skillId, skillReference.skillId) && Objects.equals(this.skillName,
            skillReference.skillName) && Objects.equals(this.description, skillReference.description) && Objects.equals(
            this.icon, skillReference.icon) && Objects.equals(this.lastVersionId, skillReference.lastVersionId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(skillId, skillName, description, icon, lastVersionId);
    }

    /**
     * Convert the given object to string with each line indented by 4 spaces
     * (except the first line).
     */
    private String toIndentedString(Object o) {
        if (o == null) {
            return "null";
        }
        return o.toString().replace("\n", "\n    ");
    }
}
