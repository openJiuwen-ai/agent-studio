/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * ModelServiceListRsp
 */

@Validated

public class ModelServiceListRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("total")
    @Schema(description = "总数", example = "100")
    private Integer total = null;

    @JsonProperty("data")
    @Schema(description = "模型服务列表", example = "[]")
    @Valid
    @Size()
    private List<ModelServiceRsp> data = null;

    @JsonProperty("all_model_type")
    @Schema(description = "所有模型类型列表", example = "[\"chat\",\"embedding\"]")
    @Valid
    @Size()
    private List<@Length() String> allModelType = null;

    @JsonProperty("all_model_series")
    @Schema(description = "所有模型系列列表", example = "[\"GPT\",\"Llama\"]")
    @Valid
    @Size()
    private List<@Length() String> allModelSeries = null;

    public Integer getTotal() {
        return total;
    }

    public ModelServiceListRsp setTotal(Integer total) {
        this.total = total;
        return this;
    }

    public List<ModelServiceRsp> getData() {
        return data;
    }

    public ModelServiceListRsp setData(List<ModelServiceRsp> data) {
        this.data = data;
        return this;
    }

    public List<String> getAllModelType() {
        return allModelType;
    }

    public ModelServiceListRsp setAllModelType(List<String> allModelType) {
        this.allModelType = allModelType;
        return this;
    }

    public List<String> getAllModelSeries() {
        return allModelSeries;
    }

    public ModelServiceListRsp setAllModelSeries(List<String> allModelSeries) {
        this.allModelSeries = allModelSeries;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ModelServiceListRsp {\n");

        sb.append("    total: ").append(toIndentedString(total)).append("\n");
        sb.append("    data: ").append(toIndentedString(data)).append("\n");
        sb.append("    allModelType: ").append(toIndentedString(allModelType)).append("\n");
        sb.append("    allModelSeries: ").append(toIndentedString(allModelSeries)).append("\n");
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
        ModelServiceListRsp modelServiceListRsp = (ModelServiceListRsp) o;
        return Objects.equals(this.total, modelServiceListRsp.total) && Objects.equals(this.data,
            modelServiceListRsp.data) && Objects.equals(this.allModelType, modelServiceListRsp.allModelType)
            && Objects.equals(this.allModelSeries, modelServiceListRsp.allModelSeries);
    }

    @Override
    public int hashCode() {
        return Objects.hash(total, data, allModelType, allModelSeries);
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
