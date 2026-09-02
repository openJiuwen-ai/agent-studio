/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.constraints.NotBlank;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * Message
 */

@Validated

public class Message implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("role")
    @Schema(description = "角色", example = "admin")
    @Length(min = 1, max = 64)
    private String role = null;

    @JsonProperty("content")
    @Schema(description = "内容", example = "内容示例", required = true)
    @NotBlank
    @Length(min = 1)
    private String content = null;

    public String getRole() {
        return role;
    }

    public Message setRole(String role) {
        this.role = role;
        return this;
    }

    public String getContent() {
        return content;
    }

    public Message setContent(String content) {
        this.content = content;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class Message {\n");

        sb.append("    role: ").append(toIndentedString(role)).append("\n");
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
        Message message = (Message) o;
        return Objects.equals(this.role, message.role) && Objects.equals(this.content, message.content);
    }

    @Override
    public int hashCode() {
        return Objects.hash(role, content);
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
