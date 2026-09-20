/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 字段取值。
 */
@ApiModel(description = "字段取值。")

@Validated

public class WorkflowFieldVOValue implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("type")
    @Schema(description = "取值类型", example = "literal")
    private TypeEnum type = null;

    @JsonProperty("content")
    @Schema(description = "取值内容", example = "hello world")
    @Valid
    private Object content = null;

    @JsonProperty("operator")
    @Schema(description = "运算符", example = "increment")
    private OperatorEnum operator = null;

    @JsonProperty("hint")
    @Schema(description = "提示信息", example = "请输入内容")
    private String hint = null;

    @JsonProperty("default")
    @Schema(description = "默认值", example = "null")
    @Valid
    private Object _default = null;

    @JsonProperty("display")
    @Schema(description = "显示内容", example = "Hello")
    @Valid
    private Object display = null;

    public TypeEnum getType() {
        return type;
    }

    public WorkflowFieldVOValue setType(TypeEnum type) {
        this.type = type;
        return this;
    }

    public Object getContent() {
        return content;
    }

    public WorkflowFieldVOValue setContent(Object content) {
        this.content = content;
        return this;
    }

    public OperatorEnum getOperator() {
        return operator;
    }

    public WorkflowFieldVOValue setOperator(OperatorEnum operator) {
        this.operator = operator;
        return this;
    }

    public String getHint() {
        return hint;
    }

    public WorkflowFieldVOValue setHint(String hint) {
        this.hint = hint;
        return this;
    }

    public Object getDefault() {
        return _default;
    }

    public WorkflowFieldVOValue setDefault(Object _default) {
        this._default = _default;
        return this;
    }

    public Object getDisplay() {
        return display;
    }

    public WorkflowFieldVOValue setDisplay(Object display) {
        this.display = display;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowFieldVOValue {\n");

        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    content: ").append(toIndentedString(content)).append("\n");
        sb.append("    operator: ").append(toIndentedString(operator)).append("\n");
        sb.append("    hint: ").append(toIndentedString(hint)).append("\n");
        sb.append("    _default: ").append(toIndentedString(_default)).append("\n");
        sb.append("    display: ").append(toIndentedString(display)).append("\n");
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
        WorkflowFieldVOValue workflowFieldVOValue = (WorkflowFieldVOValue) o;
        return Objects.equals(this.type, workflowFieldVOValue.type) && Objects.equals(this.content,
            workflowFieldVOValue.content) && Objects.equals(this.operator, workflowFieldVOValue.operator)
            && Objects.equals(this.hint, workflowFieldVOValue.hint) && Objects.equals(this._default,
            workflowFieldVOValue._default) && Objects.equals(this.display, workflowFieldVOValue.display);
    }

    @Override
    public int hashCode() {
        return Objects.hash(type, content, operator, hint, _default, display);
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
     * 取值类型。
     */
    public enum TypeEnum {
        GENERATED("generated"),

        REF("ref"),

        LITERAL("literal"),

        NESTED("nested");

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

    /**
     * 运算符类型：increment-递增，decrement-递减，empty-null，empty_str-空字符，empty_arr-空列表。
     */
    public enum OperatorEnum {
        INCREMENT("increment"),

        DECREMENT("decrement"),

        EMPTY("empty"),

        EMPTY_STR("empty_str"),

        EMPTY_ARR("empty_arr");

        private String value;

        OperatorEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static OperatorEnum fromValue(String text) {
            for (OperatorEnum b : OperatorEnum.values()) {
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
