/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ParsePluginReq
 */

@Validated

public class ParsePluginReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("content")
    @Schema(description = "内容", example = "内容示例")
    private String content = null;

    public String getContent() {
        return content;
    }

    public ParsePluginReq setContent(String content) {
        this.content = content;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ParsePluginReq {\n");

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
        ParsePluginReq parsePluginReq = (ParsePluginReq) o;
        return Objects.equals(this.content, parsePluginReq.content);
    }

    @Override
    public int hashCode() {
        return Objects.hash(content);
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
