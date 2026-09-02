/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import lombok.Data;
import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Map;
import java.util.Objects;

/**
 * 导入失败的结构化消息详情
 */
@ApiModel(description = "导入失败的结构化消息详情")
@Data
@Validated

public class FailedStructuredMessage implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "消息ID", example = "msg-001")
    @Length(max = 64)
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "消息名称", example = "用户问候消息")
    private String name = null;

    @JsonProperty("category")
    @Schema(description = "消息分类", example = "greeting")
    @Length(max = 64)
    private String category = null;

    @JsonProperty("content")
    @Schema(description = "消息内容", example = "{\"text\":\"你好\"}")
    @Valid
    @Size()
    private Map<String, Object> content = null;

    @JsonProperty("visibility")
    @Schema(description = "消息可见性", example = "public")
    private String visibility = null;

    @JsonProperty("reason")
    @Schema(description = "导入失败原因", example = "字段格式不正确")
    private String reason = null;

    public String getId() {
        return id;
    }

    public FailedStructuredMessage setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public FailedStructuredMessage setName(String name) {
        this.name = name;
        return this;
    }

    public String getCategory() {
        return category;
    }

    public FailedStructuredMessage setCategory(String category) {
        this.category = category;
        return this;
    }

    public Map<String, Object> getContent() {
        return content;
    }

    public FailedStructuredMessage setContent(Map<String, Object> content) {
        this.content = content;
        return this;
    }

    public String getVisibility() {
        return visibility;
    }

    public FailedStructuredMessage setVisibility(String visibility) {
        this.visibility = visibility;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class FailedStructuredMessage {\n");

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
        FailedStructuredMessage failedStructuredMessage = (FailedStructuredMessage) o;
        return Objects.equals(this.id, failedStructuredMessage.id) && Objects.equals(this.name,
            failedStructuredMessage.name) && Objects.equals(this.category, failedStructuredMessage.category)
            && Objects.equals(this.content, failedStructuredMessage.content) && Objects.equals(this.visibility,
            failedStructuredMessage.visibility);
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
