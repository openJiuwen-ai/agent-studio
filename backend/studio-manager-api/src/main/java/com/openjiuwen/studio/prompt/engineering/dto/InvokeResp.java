/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * agentBuilder模型调优返回体
 */
@ApiModel(description = "agentBuilder模型调优返回体")

@Validated
public class InvokeResp implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("result")
    @Schema(description = "结果", example = "示例文本")
    private String result = null;

    @JsonProperty("model")
    @Schema(description = "模型名称", example = "gpt-4")
    private String model = null;

    @JsonProperty("model_type")
    @Schema(description = "模型类型", example = "LLM")
    private String modelType = null;

    @JsonProperty("token")
    @Schema(description = "Token数量", example = "1024")
    private Integer token = null;

    @JsonProperty("time")
    @Schema(description = "时间", example = "1.5")
    private Double time = null;

    @JsonProperty("file_info")
    @Schema(description = "文件信息", example = "")
    @Valid
    private FileInfoVo fileInfo = null;

    public String getResult() {
        return result;
    }

    public InvokeResp setResult(String result) {
        this.result = result;
        return this;
    }

    public String getModel() {
        return model;
    }

    public InvokeResp setModel(String model) {
        this.model = model;
        return this;
    }

    public String getModelType() {
        return modelType;
    }

    public InvokeResp setModelType(String modelType) {
        this.modelType = modelType;
        return this;
    }

    public Integer getToken() {
        return token;
    }

    public InvokeResp setToken(Integer token) {
        this.token = token;
        return this;
    }

    public Double getTime() {
        return time;
    }

    public InvokeResp setTime(Double time) {
        this.time = time;
        return this;
    }

    public FileInfoVo getFileInfo() {
        return fileInfo;
    }

    public InvokeResp setFileInfo(FileInfoVo fileInfo) {
        this.fileInfo = fileInfo;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class InvokeResp {\n");
        sb.append("    result: ").append(toIndentedString(result)).append("\n");
        sb.append("    model: ").append(toIndentedString(model)).append("\n");
        sb.append("    modelType: ").append(toIndentedString(modelType)).append("\n");
        sb.append("    token: ").append(toIndentedString(token)).append("\n");
        sb.append("    time: ").append(toIndentedString(time)).append("\n");
        sb.append("    fileInfo: ").append(toIndentedString(fileInfo)).append("\n");
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
        InvokeResp invokeResp = (InvokeResp) o;
        return Objects.equals(this.result, invokeResp.result) && Objects.equals(this.model, invokeResp.model)
            && Objects.equals(this.modelType, invokeResp.modelType) && Objects.equals(this.token, invokeResp.token)
            && Objects.equals(this.time, invokeResp.time) && Objects.equals(this.fileInfo, invokeResp.fileInfo);
    }

    @Override
    public int hashCode() {
        return Objects.hash(result, model, modelType, token, time, fileInfo);
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
