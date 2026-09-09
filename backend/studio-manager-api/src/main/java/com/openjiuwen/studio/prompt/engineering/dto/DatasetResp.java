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
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * 数据集响应体
 */
@ApiModel(description = "数据集响应体")

@Validated
public class DatasetResp implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("datasets")
    @Schema(description = "datasets", example = "")
    @Valid
    private List<DatasetVo> datasets = null;

    @JsonProperty("dataset_id")
    @Schema(description = "数据集ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String datasetId = null;

    @JsonProperty("dataset_values")
    @Schema(description = "数据集Values", example = "")
    @Valid
    private List<Map<String, String>> datasetValues = null;

    @JsonProperty("count")
    @Schema(description = "数量", example = "10")
    private Integer count = null;

    public List<DatasetVo> getDatasets() {
        return datasets;
    }

    public DatasetResp setDatasets(List<DatasetVo> datasets) {
        this.datasets = datasets;
        return this;
    }

    public String getDatasetId() {
        return datasetId;
    }

    public DatasetResp setDatasetId(String datasetId) {
        this.datasetId = datasetId;
        return this;
    }

    public List<Map<String, String>> getDatasetValues() {
        return datasetValues;
    }

    public DatasetResp setDatasetValues(List<Map<String, String>> datasetValues) {
        this.datasetValues = datasetValues;
        return this;
    }

    public Integer getCount() {
        return count;
    }

    public DatasetResp setCount(Integer count) {
        this.count = count;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class DatasetResp {\n");
        sb.append("    datasets: ").append(toIndentedString(datasets)).append("\n");
        sb.append("    datasetId: ").append(toIndentedString(datasetId)).append("\n");
        sb.append("    datasetValues: ").append(toIndentedString(datasetValues)).append("\n");
        sb.append("    count: ").append(toIndentedString(count)).append("\n");
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
        DatasetResp datasetResp = (DatasetResp) o;
        return Objects.equals(this.datasets, datasetResp.datasets) && Objects.equals(this.datasetId,
            datasetResp.datasetId) && Objects.equals(this.datasetValues, datasetResp.datasetValues) && Objects.equals(
            this.count, datasetResp.count);
    }

    @Override
    public int hashCode() {
        return Objects.hash(datasets, datasetId, datasetValues, count);
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
