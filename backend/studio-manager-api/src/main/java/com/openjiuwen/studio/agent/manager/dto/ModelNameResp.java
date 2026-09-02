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
 * ModelNameResp
 */

@Validated

public class ModelNameResp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("exist_model_name")
    @Schema(description = "模型", example = "true")
    private Boolean existModelName = null;

    public ModelNameResp setExistModelName(Boolean existModelName) {
        this.existModelName = existModelName;
        return this;
    }

    public Boolean isExistModelName() {
        return existModelName;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ModelNameResp {\n");

        sb.append("    existModelName: ").append(toIndentedString(existModelName)).append("\n");
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
        ModelNameResp modelNameResp = (ModelNameResp) o;
        return Objects.equals(this.existModelName, modelNameResp.existModelName);
    }

    @Override
    public int hashCode() {
        return Objects.hash(existModelName);
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
