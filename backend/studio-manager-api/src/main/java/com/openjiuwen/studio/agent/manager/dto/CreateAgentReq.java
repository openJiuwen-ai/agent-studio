/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 创建智能体请求体。
 */
@ApiModel(description = "创建智能体请求体。")

@Validated

public class CreateAgentReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Pattern(
        regexp = "^[\\u4e00-\\u9fa5a-zA-Z0-9_\\-（）()！!，。、？：；\"\"''《》【】,.?:;\"\"''<>\\[\\]@#$%&*+= \\n](?:[\\s\\S]*[\\u4e00-\\u9fa5a-zA-Z0-9_\\-（）()！!，。、？：；\"\"''《》【】,.?:;\"\"''<>\\[\\]@#$%&*+= \\n])?$")
    @NotBlank
    @Length(min = 1, max = 64)
    @Schema(description = "智能体名称，1~64 个字符", example = "我的助手", required = true)
    private String name = null;

    @JsonProperty("description")
    @NotBlank
    @Length(min = 1, max = 256)
    @Schema(description = "智能体描述，1~256 个字符", example = "一个帮助回答问题的助手", required = true)
    private String description = null;

    @JsonProperty("icon")
    @Length(min = 1, max = 64)
    @Schema(description = "智能体图标，支持 base64 或 URL，1~64 个字符", example = "data:image/png;base64,...")
    private String icon = null;

    @JsonProperty("type")
    @Schema(description = "智能体类型：agent-单智能体，controller-多智能体", example = "agent")
    private TypeEnum type = null;

    public String getName() {
        return name;
    }

    public CreateAgentReq setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public CreateAgentReq setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public CreateAgentReq setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public TypeEnum getType() {
        return type;
    }

    public CreateAgentReq setType(TypeEnum type) {
        this.type = type;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CreateAgentReq {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
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
        CreateAgentReq createAgentReq = (CreateAgentReq) o;
        return Objects.equals(this.name, createAgentReq.name) && Objects.equals(this.description,
            createAgentReq.description) && Objects.equals(this.icon, createAgentReq.icon) && Objects.equals(this.type,
            createAgentReq.type);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, description, icon, type);
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

    /**
     * 智能体类型，取值：agent-单智能体，controller-多智能体。
     */
    public enum TypeEnum {
        AGENT("agent"),

        CONTROLLER("controller");

        private String value;

        TypeEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static TypeEnum fromValue(String text) {
            for (TypeEnum b : TypeEnum.values()) {
                if (String.valueOf(b.value).equals(text)) {
                    return b;
                }
            }
            return null;
        }

        @Override
        @JsonValue
        public String toString() {
            return String.valueOf(value);
        }
    }
}
