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
import java.util.Objects;

/**
 * 模型列表信息
 */
@ApiModel(description = "模型列表信息")

@Validated
public class ModelListVo implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("model_service_info_list")
    @Schema(description = "模型Service信息列表", example = "")
    @Valid
    private List<ModelServiceInfo> modelServiceInfoList = null;

    public List<ModelServiceInfo> getModelServiceInfoList() {
        return modelServiceInfoList;
    }

    public ModelListVo setModelServiceInfoList(List<ModelServiceInfo> modelServiceInfoList) {
        this.modelServiceInfoList = modelServiceInfoList;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ModelListVo {\n");
        sb.append("    modelServiceInfoList: ").append(toIndentedString(modelServiceInfoList)).append("\n");
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
        ModelListVo modelListVo = (ModelListVo) o;
        return Objects.equals(this.modelServiceInfoList, modelListVo.modelServiceInfoList);
    }

    @Override
    public int hashCode() {
        return Objects.hash(modelServiceInfoList);
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
