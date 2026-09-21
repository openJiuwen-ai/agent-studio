/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * GetDatasetListReq
 */

@Validated
public class GetDatasetListReq implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("dataset_name")
    @Schema(description = "数据集名称", example = "示例名称")
    @Length(max = 32)
    private String datasetName = null;

    @JsonProperty("dataset_type")
    @Schema(description = "数据集类型", example = "TEXT")
    @Pattern(regexp = "variable-data")
    private String datasetType = null;

    @JsonProperty("offset")
    @Schema(description = "偏移量", example = "0")
    @Range(min = 0L, max = 100L)
    private Integer offset = 0;

    @JsonProperty("limit")
    @Schema(description = "每页数量", example = "50")
    @Range(min = 10L, max = 100L)
    private Integer limit = 100;

    public String getDatasetName() {
        return datasetName;
    }

    public GetDatasetListReq setDatasetName(String datasetName) {
        this.datasetName = datasetName;
        return this;
    }

    public String getDatasetType() {
        return datasetType;
    }

    public GetDatasetListReq setDatasetType(String datasetType) {
        this.datasetType = datasetType;
        return this;
    }

    public Integer getOffset() {
        return offset;
    }

    public GetDatasetListReq setOffset(Integer offset) {
        this.offset = offset;
        return this;
    }

    public Integer getLimit() {
        return limit;
    }

    public GetDatasetListReq setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class GetDatasetListReq {\n");
        sb.append("    datasetName: ").append(toIndentedString(datasetName)).append("\n");
        sb.append("    datasetType: ").append(toIndentedString(datasetType)).append("\n");
        sb.append("    offset: ").append(toIndentedString(offset)).append("\n");
        sb.append("    limit: ").append(toIndentedString(limit)).append("\n");
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
        GetDatasetListReq getDatasetListReq = (GetDatasetListReq) o;
        return Objects.equals(this.datasetName, getDatasetListReq.datasetName) && Objects.equals(this.datasetType,
            getDatasetListReq.datasetType) && Objects.equals(this.offset, getDatasetListReq.offset) && Objects.equals(
            this.limit, getDatasetListReq.limit);
    }

    @Override
    public int hashCode() {
        return Objects.hash(datasetName, datasetType, offset, limit);
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
