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
 * ModelStatusReq
 */

@Validated

public class ModelStatusReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("model_id")
    @Schema(description = "模型ID", example = "example-id-123")
    private String modelId = null;

    @JsonProperty("status")
    @Schema(description = "状态", example = "active")
    private String status = null;

    public String getModelId() {
        return modelId;
    }

    public ModelStatusReq setModelId(String modelId) {
        this.modelId = modelId;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public ModelStatusReq setStatus(String status) {
        this.status = status;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ModelStatusReq {\n");

        sb.append("    modelId: ").append(toIndentedString(modelId)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
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
        ModelStatusReq modelStatusReq = (ModelStatusReq) o;
        return Objects.equals(this.modelId, modelStatusReq.modelId) && Objects.equals(this.status,
            modelStatusReq.status);
    }

    @Override
    public int hashCode() {
        return Objects.hash(modelId, status);
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
