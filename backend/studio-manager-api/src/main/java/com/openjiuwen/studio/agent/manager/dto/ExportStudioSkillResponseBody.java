/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 导出Skill响应体
 */
@ApiModel(description = "导出Skill响应体")

@Validated

public class ExportStudioSkillResponseBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("obs_url")
    @Schema(description = "OBS下载地址", example = "https://obs.example.com/skill.zip", required = true)
    @NotBlank
    @Length(min = 1, max = 1024)
    private String obsUrl = null;

    @JsonProperty("skill_name")
    @Schema(description = "技能名称", example = "导出技能", required = true)
    @NotBlank
    @Length(min = 1, max = 64)
    private String skillName = null;

    @JsonProperty("version_name")
    @Schema(description = "版本名称", example = "1.0.0")
    @Length(min = 1, max = 32)
    private String versionName = null;

    @JsonProperty("skill_id")
    @Schema(description = "技能ID", example = "550e8400-e29b-41d4-a716-446655440000", required = true)
    @Pattern(regexp = "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    @NotBlank
    private String skillId = null;

    public String getObsUrl() {
        return obsUrl;
    }

    public ExportStudioSkillResponseBody setObsUrl(String obsUrl) {
        this.obsUrl = obsUrl;
        return this;
    }

    public String getSkillName() {
        return skillName;
    }

    public ExportStudioSkillResponseBody setSkillName(String skillName) {
        this.skillName = skillName;
        return this;
    }

    public String getVersionName() {
        return versionName;
    }

    public ExportStudioSkillResponseBody setVersionName(String versionName) {
        this.versionName = versionName;
        return this;
    }

    public String getSkillId() {
        return skillId;
    }

    public ExportStudioSkillResponseBody setSkillId(String skillId) {
        this.skillId = skillId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ExportStudioSkillResponseBody {\n");

        sb.append("    obsUrl: ").append(toIndentedString(obsUrl)).append("\n");
        sb.append("    skillName: ").append(toIndentedString(skillName)).append("\n");
        sb.append("    versionName: ").append(toIndentedString(versionName)).append("\n");
        sb.append("    skillId: ").append(toIndentedString(skillId)).append("\n");
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
        ExportStudioSkillResponseBody exportStudioSkillResponseBody = (ExportStudioSkillResponseBody) o;
        return Objects.equals(this.obsUrl, exportStudioSkillResponseBody.obsUrl) && Objects.equals(this.skillName,
            exportStudioSkillResponseBody.skillName) && Objects.equals(this.versionName,
            exportStudioSkillResponseBody.versionName) && Objects.equals(this.skillId,
            exportStudioSkillResponseBody.skillId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(obsUrl, skillName, versionName, skillId);
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
