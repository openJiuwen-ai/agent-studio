/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Map;
import java.util.Objects;

/**
 * 结构化信息返回实体
 */
@ApiModel(description = "结构化信息返回实体")

@Validated

public class StructMessage implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "结构化信息ID", example = "msg001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(max = 64)
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "结构化信息名称", example = "问候语")
    @Length(max = 500)
    private String name = null;

    @JsonProperty("category")
    @Schema(description = "分类", example = "greeting")
    @Length(max = 500)
    private String category = null;

    @JsonProperty("content")
    @Schema(description = "内容", example = "{\"key\":\"value\"}")
    @Valid
    @Size()
    private Map<String, Object> content = null;

    @JsonProperty("visibility")
    @Schema(description = "可见范围", example = "personal")
    @Length(max = 500)
    private String visibility = null;

    public String getId() {
        return id;
    }

    public StructMessage setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public StructMessage setName(String name) {
        this.name = name;
        return this;
    }

    public String getCategory() {
        return category;
    }

    public StructMessage setCategory(String category) {
        this.category = category;
        return this;
    }

    public Map<String, Object> getContent() {
        return content;
    }

    public StructMessage setContent(Map<String, Object> content) {
        this.content = content;
        return this;
    }

    public String getVisibility() {
        return visibility;
    }

    public StructMessage setVisibility(String visibility) {
        this.visibility = visibility;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class StructMessage {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    category: ").append(toIndentedString(category)).append("\n");
        sb.append("    content: ").append(toIndentedString(content)).append("\n");
        sb.append("    visibility: ").append(toIndentedString(visibility)).append("\n");
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
        StructMessage structMessage = (StructMessage) o;
        return Objects.equals(this.id, structMessage.id) && Objects.equals(this.name, structMessage.name)
            && Objects.equals(this.category, structMessage.category) && Objects.equals(this.content,
            structMessage.content) && Objects.equals(this.visibility, structMessage.visibility);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, category, content, visibility);
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
