/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * VariableVo
 */

@Validated
public class VariableVo implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "唯一标识", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称")
    private String name = null;

    @JsonProperty("key")
    @Schema(description = "键", example = "示例文本")
    private String key = null;

    @JsonProperty("value")
    @Schema(description = "值", example = "示例文本")
    private String value = null;

    @JsonProperty("pe_task_id")
    @Schema(description = "PE任务标识", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String peTaskId = null;

    public String getId() {
        return id;
    }

    public VariableVo setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public VariableVo setName(String name) {
        this.name = name;
        return this;
    }

    public String getKey() {
        return key;
    }

    public VariableVo setKey(String key) {
        this.key = key;
        return this;
    }

    public String getValue() {
        return value;
    }

    public VariableVo setValue(String value) {
        this.value = value;
        return this;
    }

    public String getPeTaskId() {
        return peTaskId;
    }

    public VariableVo setPeTaskId(String peTaskId) {
        this.peTaskId = peTaskId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class VariableVo {\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    key: ").append(toIndentedString(key)).append("\n");
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
        VariableVo variableVo = (VariableVo) o;
        return Objects.equals(this.id, variableVo.id) && Objects.equals(this.name, variableVo.name) && Objects.equals(
            this.key, variableVo.key) && Objects.equals(this.value, variableVo.value) && Objects.equals(this.peTaskId,
            variableVo.peTaskId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, key, value, peTaskId);
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
