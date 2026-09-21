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
 * 标签的相关信息。
 */
@ApiModel(description = "标签的相关信息。")

@Validated

public class TagInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("tag_id")
    @Schema(description = "标签ID", example = "example-id-123")
    private String tagId = null;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称")
    private String name = null;

    @JsonProperty("name_en")
    @Schema(description = "英文名称", example = "示例名称")
    private String nameEn = null;

    public String getTagId() {
        return tagId;
    }

    public TagInfo setTagId(String tagId) {
        this.tagId = tagId;
        return this;
    }

    public String getName() {
        return name;
    }

    public TagInfo setName(String name) {
        this.name = name;
        return this;
    }

    public String getNameEn() {
        return nameEn;
    }

    public TagInfo setNameEn(String nameEn) {
        this.nameEn = nameEn;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class TagInfo {\n");

        sb.append("    tagId: ").append(toIndentedString(tagId)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    nameEn: ").append(toIndentedString(nameEn)).append("\n");
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
        TagInfo tagInfo = (TagInfo) o;
        return Objects.equals(this.tagId, tagInfo.tagId) && Objects.equals(this.name, tagInfo.name) && Objects.equals(
            this.nameEn, tagInfo.nameEn);
    }

    @Override
    public int hashCode() {
        return Objects.hash(tagId, name, nameEn);
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
