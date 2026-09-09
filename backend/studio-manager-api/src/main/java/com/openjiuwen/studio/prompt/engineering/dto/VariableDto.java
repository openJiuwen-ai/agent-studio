/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * playground调优返回体
 */
@ApiModel(description = "playground调优返回体")

@Validated
public class VariableDto implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "唯一标识", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    @Pattern(regexp = "(^$)|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    private String id = null;

    @JsonProperty("key")
    @Schema(description = "键", example = "示例文本")
    @Pattern(regexp = "^[a-zA-Z][a-zA-Z0-9_]{0,9}$")
    private String key = null;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称")
    @Pattern(regexp = "^[A-Za-z\\u4E00-\\u9FA5](?:[\\w\\u4E00-\\u9FA5-]{0,8}[\\dA-Za-z\\u4E00-\\u9FA5])?$")
    private String name = null;

    @JsonProperty("value")
    @Schema(description = "值", example = "示例文本")
    @Length(max = 1000)
    private String value = null;

    @JsonProperty("pe_task_id")
    @Schema(description = "PE任务标识", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    @Pattern(regexp = "(^$)|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    private String peTaskId = null;

    public String getId() {
        return id;
    }

    public VariableDto setId(String id) {
        this.id = id;
        return this;
    }

    public String getKey() {
        return key;
    }

    public VariableDto setKey(String key) {
        this.key = key;
        return this;
    }

    public String getName() {
        return name;
    }

    public VariableDto setName(String name) {
        this.name = name;
        return this;
    }

    public String getValue() {
        return value;
    }

    public VariableDto setValue(String value) {
        this.value = value;
        return this;
    }

    public String getPeTaskId() {
        return peTaskId;
    }

    public VariableDto setPeTaskId(String peTaskId) {
        this.peTaskId = peTaskId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class VariableDto {\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    key: ").append(toIndentedString(key)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    value: ").append(toIndentedString(value)).append("\n");
        sb.append("    peTaskId: ").append(toIndentedString(peTaskId)).append("\n");
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
        VariableDto variableDto = (VariableDto) o;
        return Objects.equals(this.id, variableDto.id) && Objects.equals(this.key, variableDto.key) && Objects.equals(
            this.name, variableDto.name) && Objects.equals(this.value, variableDto.value) && Objects.equals(
            this.peTaskId, variableDto.peTaskId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, key, name, value, peTaskId);
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
