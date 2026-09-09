/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * PromptBuilder请求体
 */
@ApiModel(description = "PromptBuilder请求体")

@Validated
public class PromptBuilderReq implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("instruct")
    @Schema(description = "instruct", example = "示例文本", required = true)
    @NotBlank
    private String instruct = null;

    @JsonProperty("modelInfo")
    @Schema(description = "模型信息", example = "")
    @Valid
    private ModelProperties modelInfo = null;

    @JsonProperty("stream")
    @Schema(description = "流", example = "true")
    private Boolean stream = true;

    public String getInstruct() {
        return instruct;
    }

    public PromptBuilderReq setInstruct(String instruct) {
        this.instruct = instruct;
        return this;
    }

    public ModelProperties getModelInfo() {
        return modelInfo;
    }

    public PromptBuilderReq setModelInfo(ModelProperties modelInfo) {
        this.modelInfo = modelInfo;
        return this;
    }

    public PromptBuilderReq setStream(Boolean stream) {
        this.stream = stream;
        return this;
    }

    public Boolean isStream() {
        return stream;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PromptBuilderReq {\n");
        sb.append("    instruct: ").append(toIndentedString(instruct)).append("\n");
        sb.append("    modelInfo: ").append(toIndentedString(modelInfo)).append("\n");
        sb.append("    stream: ").append(toIndentedString(stream)).append("\n");
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
        PromptBuilderReq promptBuilderReq = (PromptBuilderReq) o;
        return Objects.equals(this.instruct, promptBuilderReq.instruct) && Objects.equals(this.modelInfo,
            promptBuilderReq.modelInfo) && Objects.equals(this.stream, promptBuilderReq.stream);
    }

    @Override
    public int hashCode() {
        return Objects.hash(instruct, modelInfo, stream);
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
