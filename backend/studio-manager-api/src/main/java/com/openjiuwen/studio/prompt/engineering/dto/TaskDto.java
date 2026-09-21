/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * TaskDto
 */

@Validated
public class TaskDto implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "唯一标识", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称")
    @Pattern(regexp = "^[\\u4e00-\\u9fa5a-zA-Z][\\u4e00-\\u9fa5\\w-]{0,32}[\\u4e00-\\u9fa5a-zA-Z0-9]$")
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "示例描述")
    @Length(max = 100)
    private String description = null;

    @JsonProperty("tag_ids")
    @Schema(description = "标签Ids", example = "")
    @Valid
    @Size(max = 500)
    private List<@Length() String> tagIds = null;

    @JsonProperty("industry_id")
    @Schema(description = "行业ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    @Pattern(regexp = "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    private String industryId = null;

    public String getId() {
        return id;
    }

    public TaskDto setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public TaskDto setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public TaskDto setDescription(String description) {
        this.description = description;
        return this;
    }

    public List<String> getTagIds() {
        return tagIds;
    }

    public TaskDto setTagIds(List<String> tagIds) {
        this.tagIds = tagIds;
        return this;
    }

    public String getIndustryId() {
        return industryId;
    }

    public TaskDto setIndustryId(String industryId) {
        this.industryId = industryId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class TaskDto {\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    tagIds: ").append(toIndentedString(tagIds)).append("\n");
        sb.append("    industryId: ").append(toIndentedString(industryId)).append("\n");
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
        TaskDto taskDto = (TaskDto) o;
        return Objects.equals(this.id, taskDto.id) && Objects.equals(this.name, taskDto.name) && Objects.equals(
            this.description, taskDto.description) && Objects.equals(this.tagIds, taskDto.tagIds) && Objects.equals(
            this.industryId, taskDto.industryId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, description, tagIds, industryId);
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
