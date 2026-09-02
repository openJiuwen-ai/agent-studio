/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 更新候选模板名称或者人工打分
 */
@ApiModel(description = "更新候选模板名称或者人工打分")

@Validated
public class SmallPromptDto implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "唯一标识", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890", required = true)
    @Pattern(regexp = "(^$)|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    @NotBlank
    private String id = null;

    @JsonProperty("manual_score")
    @Schema(description = "人工评分", example = "4")
    @Range(min = 0L, max = 5L)
    private Integer manualScore = null;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称")
    @Pattern(regexp = "^[\\u4e00-\\u9fa5a-zA-Z][\\u4e00-\\u9fa5\\w-]{0,18}[\\u4e00-\\u9fa5a-zA-Z0-9]$")
    private String name = null;

    public String getId() {
        return id;
    }

    public SmallPromptDto setId(String id) {
        this.id = id;
        return this;
    }

    public Integer getManualScore() {
        return manualScore;
    }

    public SmallPromptDto setManualScore(Integer manualScore) {
        this.manualScore = manualScore;
        return this;
    }

    public String getName() {
        return name;
    }

    public SmallPromptDto setName(String name) {
        this.name = name;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class SmallPromptDto {\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    manualScore: ").append(toIndentedString(manualScore)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
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
        SmallPromptDto smallPromptDto = (SmallPromptDto) o;
        return Objects.equals(this.id, smallPromptDto.id) && Objects.equals(this.manualScore,
            smallPromptDto.manualScore) && Objects.equals(this.name, smallPromptDto.name);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, manualScore, name);
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
