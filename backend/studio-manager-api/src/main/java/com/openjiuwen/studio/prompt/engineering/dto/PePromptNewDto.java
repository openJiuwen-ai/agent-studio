/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 候选模板创建入参
 */
@ApiModel(description = "候选模板创建入参")

@Validated
public class PePromptNewDto implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称")
    @Pattern(regexp = "^[\\u4e00-\\u9fa5a-zA-Z][\\u4e00-\\u9fa5\\w-()（）]{0,32}[\\u4e00-\\u9fa5a-zA-Z0-9()（）]$")
    @Length(max = 256)
    private String name = null;

    @JsonProperty("content")
    @Schema(description = "内容", example = "示例内容")
    private String content = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "示例描述")
    private String description = null;

    @JsonProperty("creator")
    @Schema(description = "创建者", example = "张三")
    private String creator = null;

    @JsonProperty("updater")
    @Schema(description = "更新者", example = "2024-01-01T00:00:00.000Z")
    private String updater = null;

    public String getName() {
        return name;
    }

    public PePromptNewDto setName(String name) {
        this.name = name;
        return this;
    }

    public String getContent() {
        return content;
    }

    public PePromptNewDto setContent(String content) {
        this.content = content;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public PePromptNewDto setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getCreator() {
        return creator;
    }

    public PePromptNewDto setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public String getUpdater() {
        return updater;
    }

    public PePromptNewDto setUpdater(String updater) {
        this.updater = updater;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PePromptNewDto {\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    content: ").append(toIndentedString(content)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    updater: ").append(toIndentedString(updater)).append("\n");
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
        PePromptNewDto pePromptNewDto = (PePromptNewDto) o;
        return Objects.equals(this.name, pePromptNewDto.name) && Objects.equals(this.content, pePromptNewDto.content)
            && Objects.equals(this.description, pePromptNewDto.description) && Objects.equals(this.creator,
            pePromptNewDto.creator) && Objects.equals(this.updater, pePromptNewDto.updater);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, content, description, creator, updater);
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
