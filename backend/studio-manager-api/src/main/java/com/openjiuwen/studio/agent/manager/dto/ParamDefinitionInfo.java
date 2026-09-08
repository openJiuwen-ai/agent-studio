/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 连接器参数定义详情
 */
@ApiModel(description = "连接器参数定义详情")

@Validated

public class ParamDefinitionInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("code")
    @Schema(description = "参数编码", example = "api_key")
    private String code = null;

    @JsonProperty("name")
    @Schema(description = "参数名称", example = "API密钥")
    private String name = null;

    @JsonProperty("need")
    @Schema(description = "是否必填", example = "true")
    private String need = null;

    @JsonProperty("type")
    @Schema(description = "参数类型", example = "STRING")
    private TypeEnum type = null;

    @JsonProperty("remark")
    @Schema(description = "参数备注", example = "用于API认证的密钥")
    @Length(max = 2000)
    private String remark = null;

    @JsonProperty("pattern")
    @Schema(description = "参数校验正则", example = "^[a-zA-Z0-9]+$")
    @Length(max = 200)
    private String pattern = null;

    public String getCode() {
        return code;
    }

    public ParamDefinitionInfo setCode(String code) {
        this.code = code;
        return this;
    }

    public String getName() {
        return name;
    }

    public ParamDefinitionInfo setName(String name) {
        this.name = name;
        return this;
    }

    public String getNeed() {
        return need;
    }

    public ParamDefinitionInfo setNeed(String need) {
        this.need = need;
        return this;
    }

    public TypeEnum getType() {
        return type;
    }

    public ParamDefinitionInfo setType(TypeEnum type) {
        this.type = type;
        return this;
    }

    public String getRemark() {
        return remark;
    }

    public ParamDefinitionInfo setRemark(String remark) {
        this.remark = remark;
        return this;
    }

    public String getPattern() {
        return pattern;
    }

    public ParamDefinitionInfo setPattern(String pattern) {
        this.pattern = pattern;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ParamDefinitionInfo {\n");

        sb.append("    code: ").append(toIndentedString(code)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    need: ").append(toIndentedString(need)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    remark: ").append(toIndentedString(remark)).append("\n");
        sb.append("    pattern: ").append(toIndentedString(pattern)).append("\n");
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
        ParamDefinitionInfo paramDefinitionInfo = (ParamDefinitionInfo) o;
        return Objects.equals(this.code, paramDefinitionInfo.code) && Objects.equals(this.name,
            paramDefinitionInfo.name) && Objects.equals(this.need, paramDefinitionInfo.need) && Objects.equals(
            this.type, paramDefinitionInfo.type) && Objects.equals(this.remark, paramDefinitionInfo.remark)
            && Objects.equals(this.pattern, paramDefinitionInfo.pattern);
    }

    @Override
    public int hashCode() {
        return Objects.hash(code, name, need, type, remark, pattern);
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
     * 参数类型
     */
    public enum TypeEnum {
        STRING("STRING"),

        SECRET("SECRET"),

        BOOLEAN("BOOLEAN"),

        FILE("FILE");

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
