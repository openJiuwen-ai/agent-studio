/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 知识库文档标签信息
 */
@ApiModel(description = "知识库文档标签信息")

@Validated

public class KnowledgeTagInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "标签ID", example = "tag_001", required = true)
    @NotBlank
    @Length(min = 1, max = 64)
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "标签名称", example = "重要文档", required = true)
    @NotBlank
    @Length(min = 1, max = 64)
    private String name = null;

    @JsonProperty("color")
    @Schema(description = "标签颜色", example = "red", required = true)
    @NotBlank
    @Length(min = 1, max = 10)
    private String color = "red";

    @JsonProperty("create_time")
    @Schema(description = "创建时间", example = "1735689600000")
    private Long createTime = null;

    public String getId() {
        return id;
    }

    public KnowledgeTagInfo setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public KnowledgeTagInfo setName(String name) {
        this.name = name;
        return this;
    }

    public String getColor() {
        return color;
    }

    public KnowledgeTagInfo setColor(String color) {
        this.color = color;
        return this;
    }

    public Long getCreateTime() {
        return createTime;
    }

    public KnowledgeTagInfo setCreateTime(Long createTime) {
        this.createTime = createTime;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class KnowledgeTagInfo {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    color: ").append(toIndentedString(color)).append("\n");
        sb.append("    createTime: ").append(toIndentedString(createTime)).append("\n");
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
        KnowledgeTagInfo knowledgeTagInfo = (KnowledgeTagInfo) o;
        return Objects.equals(this.id, knowledgeTagInfo.id) && Objects.equals(this.name, knowledgeTagInfo.name)
            && Objects.equals(this.color, knowledgeTagInfo.color) && Objects.equals(this.createTime,
            knowledgeTagInfo.createTime);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, color, createTime);
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
