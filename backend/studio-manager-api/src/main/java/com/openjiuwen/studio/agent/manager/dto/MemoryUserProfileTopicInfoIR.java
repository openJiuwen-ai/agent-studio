/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 用户画像的topic信息。
 */
@ApiModel(description = "用户画像的topic信息。")

@Validated

public class MemoryUserProfileTopicInfoIR implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称")
    private String name = null;

    @JsonProperty("tags")
    @Schema(description = "标签列表", example = "[]")
    @Valid
    @Size()
    private List<MemoryUserProfileTagInfoIR> tags = null;

    public String getName() {
        return name;
    }

    public MemoryUserProfileTopicInfoIR setName(String name) {
        this.name = name;
        return this;
    }

    public List<MemoryUserProfileTagInfoIR> getTags() {
        return tags;
    }

    public MemoryUserProfileTopicInfoIR setTags(List<MemoryUserProfileTagInfoIR> tags) {
        this.tags = tags;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class MemoryUserProfileTopicInfoIR {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    tags: ").append(toIndentedString(tags)).append("\n");
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
        MemoryUserProfileTopicInfoIR memoryUserProfileTopicInfoIR = (MemoryUserProfileTopicInfoIR) o;
        return Objects.equals(this.name, memoryUserProfileTopicInfoIR.name) && Objects.equals(this.tags,
            memoryUserProfileTopicInfoIR.tags);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, tags);
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
