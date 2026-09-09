/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * ProviderModelList
 */

@Validated

public class ProviderModelList implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "供应商ID", example = "provider-001")
    private String id = null;

    @JsonProperty("provider_name")
    @Schema(description = "供应商名称", example = "华为云")
    private String providerName = null;

    @JsonProperty("logo")
    @Schema(description = "供应商Logo", example = "https://example.com/logo.png")
    private String logo = null;

    @JsonProperty("source")
    @Schema(description = "供应商来源", example = "huawei")
    private String source = null;

    @JsonProperty("type")
    @Schema(description = "供应商类型", example = "cloud")
    private String type = null;

    @JsonProperty("models")
    @Schema(description = "模型列表", example = "[{\"id\":\"model-001\"}]")
    @Valid
    @Size()
    private List<ModelServiceRsp> models = null;

    public String getId() {
        return id;
    }

    public ProviderModelList setId(String id) {
        this.id = id;
        return this;
    }

    public String getProviderName() {
        return providerName;
    }

    public ProviderModelList setProviderName(String providerName) {
        this.providerName = providerName;
        return this;
    }

    public String getLogo() {
        return logo;
    }

    public ProviderModelList setLogo(String logo) {
        this.logo = logo;
        return this;
    }

    public String getSource() {
        return source;
    }

    public ProviderModelList setSource(String source) {
        this.source = source;
        return this;
    }

    public String getType() {
        return type;
    }

    public ProviderModelList setType(String type) {
        this.type = type;
        return this;
    }

    public List<ModelServiceRsp> getModels() {
        return models;
    }

    public ProviderModelList setModels(List<ModelServiceRsp> models) {
        this.models = models;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ProviderModelList {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    providerName: ").append(toIndentedString(providerName)).append("\n");
        sb.append("    logo: ").append(toIndentedString(logo)).append("\n");
        sb.append("    source: ").append(toIndentedString(source)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    models: ").append(toIndentedString(models)).append("\n");
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
        ProviderModelList providerModelList = (ProviderModelList) o;
        return Objects.equals(this.id, providerModelList.id) && Objects.equals(this.providerName,
            providerModelList.providerName) && Objects.equals(this.logo, providerModelList.logo) && Objects.equals(
            this.source, providerModelList.source) && Objects.equals(this.type, providerModelList.type)
            && Objects.equals(this.models, providerModelList.models);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, providerName, logo, source, type, models);
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
