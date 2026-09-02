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
 * 意图识别配置。
 */
@ApiModel(description = "意图识别配置。")

@Validated

public class ControllerConfigIRIntentIdentification implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("type")
    @Schema(description = "类型", example = "STRING")
    private TypeEnum type = null;

    @JsonProperty("id")
    @Schema(description = "ID", example = "example-id-123")
    @Length(max = 128)
    private String id = null;

    public TypeEnum getType() {
        return type;
    }

    public ControllerConfigIRIntentIdentification setType(TypeEnum type) {
        this.type = type;
        return this;
    }

    public String getId() {
        return id;
    }

    public ControllerConfigIRIntentIdentification setId(String id) {
        this.id = id;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ControllerConfigIRIntentIdentification {\n");

        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
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
        ControllerConfigIRIntentIdentification controllerConfigIRIntentIdentification
            = (ControllerConfigIRIntentIdentification) o;
        return Objects.equals(this.type, controllerConfigIRIntentIdentification.type) && Objects.equals(this.id,
            controllerConfigIRIntentIdentification.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(type, id);
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
     * 意图类型。
     */
    public enum TypeEnum {
        WORKFLOW("WORKFLOW"),

        PLUGIN("PLUGIN"),

        DEFAULT("DEFAULT");

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
