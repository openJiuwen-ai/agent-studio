/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * Skill 上架到资产广场请求（补充广场分类标签）。
 */
@ApiModel(description = "Skill 上架到资产广场请求")
@Validated
public class SkillShelfReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("tag_id")
    @Schema(description = "Skill 分类标签ID（资源分类 config 的 id，用于广场分类展示；缺省沿用 Skill 既有 tag_id）",
        example = "uuid")
    @Size(max = 64)
    private String tagId = null;

    public String getTagId() {
        return tagId;
    }

    public SkillShelfReq setTagId(String tagId) {
        this.tagId = tagId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class SkillShelfReq {\n");
        sb.append("    tagId: ").append(toIndentedString(tagId)).append("\n");
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
        SkillShelfReq that = (SkillShelfReq) o;
        return Objects.equals(this.tagId, that.tagId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(tagId);
    }

    private String toIndentedString(Object o) {
        if (o == null) {
            return "null";
        }
        return o.toString().replace("\n", "\n    ");
    }
}