/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ModelInvokeDataRsp
 */

@Validated

public class ModelInvokeDataRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("model_type")
    @Schema(description = "模型类型", example = "chat")
    private String modelType = null;

    @JsonProperty("api_url")
    @Schema(description = "API地址", example = "https://api.example.com/v1/chat/completions")
    private String apiUrl = null;

    @JsonProperty("auth_type")
    @Schema(description = "认证类型", example = "bearer")
    private String authType = null;

    @JsonProperty("auth_info")
    @Schema(description = "认证信息", example = "{\"token\":\"xxx\"}")
    @Valid
    private Object authInfo = null;

    @JsonProperty("model_name")
    @Schema(description = "模型名称", example = "gpt-4")
    private String modelName = null;

    @JsonProperty("interface_protocol")
    @Schema(description = "接口协议", example = "OpenAI")
    private String interfaceProtocol = null;

    public String getModelType() {
        return modelType;
    }

    public ModelInvokeDataRsp setModelType(String modelType) {
        this.modelType = modelType;
        return this;
    }

    public String getApiUrl() {
        return apiUrl;
    }

    public ModelInvokeDataRsp setApiUrl(String apiUrl) {
        this.apiUrl = apiUrl;
        return this;
    }

    public String getAuthType() {
        return authType;
    }

    public ModelInvokeDataRsp setAuthType(String authType) {
        this.authType = authType;
        return this;
    }

    public Object getAuthInfo() {
        return authInfo;
    }

    public ModelInvokeDataRsp setAuthInfo(Object authInfo) {
        this.authInfo = authInfo;
        return this;
    }

    public String getModelName() {
        return modelName;
    }

    public ModelInvokeDataRsp setModelName(String modelName) {
        this.modelName = modelName;
        return this;
    }

    public String getInterfaceProtocol() {
        return interfaceProtocol;
    }

    public ModelInvokeDataRsp setInterfaceProtocol(String interfaceProtocol) {
        this.interfaceProtocol = interfaceProtocol;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ModelInvokeDataRsp {\n");

        sb.append("    modelType: ").append(toIndentedString(modelType)).append("\n");
        sb.append("    apiUrl: ").append(toIndentedString(apiUrl)).append("\n");
        sb.append("    authType: ").append(toIndentedString(authType)).append("\n");
        sb.append("    authInfo: ").append(toIndentedString(authInfo)).append("\n");
        sb.append("    modelName: ").append(toIndentedString(modelName)).append("\n");
        sb.append("    interfaceProtocol: ").append(toIndentedString(interfaceProtocol)).append("\n");
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
        ModelInvokeDataRsp modelInvokeDataRsp = (ModelInvokeDataRsp) o;
        return Objects.equals(this.modelType, modelInvokeDataRsp.modelType) && Objects.equals(this.apiUrl,
            modelInvokeDataRsp.apiUrl) && Objects.equals(this.authType, modelInvokeDataRsp.authType) && Objects.equals(
            this.authInfo, modelInvokeDataRsp.authInfo) && Objects.equals(this.modelName, modelInvokeDataRsp.modelName)
            && Objects.equals(this.interfaceProtocol, modelInvokeDataRsp.interfaceProtocol);
    }

    @Override
    public int hashCode() {
        return Objects.hash(modelType, apiUrl, authType, authInfo, modelName, interfaceProtocol);
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
