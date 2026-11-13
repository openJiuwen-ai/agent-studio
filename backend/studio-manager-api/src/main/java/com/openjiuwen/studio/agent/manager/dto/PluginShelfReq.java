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
 * 插件上架到资产广场请求（锚定发布版本）。
 */
@ApiModel(description = "插件上架到资产广场请求")
@Validated
public class PluginShelfReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("version_id")
    @Schema(description = "上架锚定的发布版本ID（缺省取当前最新发布版本；t_release_version.version_id）",
        example = "1728465600000")
    @Size(max = 64)
    private String versionId = null;

    @JsonProperty("category")
    @Schema(description = "行业分类ID（关联 t_pe_industry.id，用于广场展示行业标签；缺省保持插件既有分类）",
        example = "uuid")
    @Size(max = 64)
    private String category = null;

    public String getVersionId() {
        return versionId;
    }

    public PluginShelfReq setVersionId(String versionId) {
        this.versionId = versionId;
        return this;
    }

    public String getCategory() {
        return category;
    }

    public PluginShelfReq setCategory(String category) {
        this.category = category;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PluginShelfReq {\n");
        sb.append("    versionId: ").append(toIndentedString(versionId)).append("\n");
        sb.append("    category: ").append(toIndentedString(category)).append("\n");
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
        PluginShelfReq that = (PluginShelfReq) o;
        return Objects.equals(this.versionId, that.versionId) && Objects.equals(this.category, that.category);
    }

    @Override
    public int hashCode() {
        return Objects.hash(versionId, category);
    }

    private String toIndentedString(Object o) {
        if (o == null) {
            return "null";
        }
        return o.toString().replace("\n", "\n    ");
    }
}