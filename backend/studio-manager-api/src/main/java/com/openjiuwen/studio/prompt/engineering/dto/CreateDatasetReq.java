/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * CreateDatasetReq
 */

@Validated
public class CreateDatasetReq implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("dataset_name")
    @Schema(description = "数据集名称", example = "示例名称", required = true)
    @Pattern(regexp = "(^$)|^[\\u4e00-\\u9fa5a-zA-Z][\\u4e00-\\u9fa5\\w-]{0,30}[\\u4e00-\\u9fa5a-zA-Z0-9]$")
    @NotBlank
    private String datasetName = null;

    @JsonProperty("dataset_type")
    @Schema(description = "数据集类型", example = "TEXT", required = true)
    @NotBlank
    private String datasetType = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "示例描述")
    @Length(max = 100)
    private String description = null;

    @JsonProperty("obs_path")
    @Schema(description = "OBS路径", example = "obs://bucket/path", required = true)
    @NotBlank
    private String obsPath = null;

    public String getDatasetName() {
        return datasetName;
    }

    public CreateDatasetReq setDatasetName(String datasetName) {
        this.datasetName = datasetName;
        return this;
    }

    public String getDatasetType() {
        return datasetType;
    }

    public CreateDatasetReq setDatasetType(String datasetType) {
        this.datasetType = datasetType;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public CreateDatasetReq setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getObsPath() {
        return obsPath;
    }

    public CreateDatasetReq setObsPath(String obsPath) {
        this.obsPath = obsPath;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CreateDatasetReq {\n");
        sb.append("    datasetName: ").append(toIndentedString(datasetName)).append("\n");
        sb.append("    datasetType: ").append(toIndentedString(datasetType)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    obsPath: ").append(toIndentedString(obsPath)).append("\n");
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
        CreateDatasetReq createDatasetReq = (CreateDatasetReq) o;
        return Objects.equals(this.datasetName, createDatasetReq.datasetName) && Objects.equals(this.datasetType,
            createDatasetReq.datasetType) && Objects.equals(this.description, createDatasetReq.description)
            && Objects.equals(this.obsPath, createDatasetReq.obsPath);
    }

    @Override
    public int hashCode() {
        return Objects.hash(datasetName, datasetType, description, obsPath);
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
