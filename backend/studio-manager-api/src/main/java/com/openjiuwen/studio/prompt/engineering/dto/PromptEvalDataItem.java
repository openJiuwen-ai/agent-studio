/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 数据集条目
 */
@ApiModel(description = "数据集条目")

@Validated
public class PromptEvalDataItem implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "唯一标识", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String id = null;

    @JsonProperty("content")
    @Schema(description = "内容", example = "示例内容")
    @Length(max = 40000)
    private String content = null;

    public String getId() {
        return id;
    }

    public PromptEvalDataItem setId(String id) {
        this.id = id;
        return this;
    }

    public String getContent() {
        return content;
    }

    public PromptEvalDataItem setContent(String content) {
        this.content = content;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PromptEvalDataItem {\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    content: ").append(toIndentedString(content)).append("\n");
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
        PromptEvalDataItem promptEvalDataItem = (PromptEvalDataItem) o;
        return Objects.equals(this.id, promptEvalDataItem.id) && Objects.equals(this.content,
            promptEvalDataItem.content);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, content);
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
