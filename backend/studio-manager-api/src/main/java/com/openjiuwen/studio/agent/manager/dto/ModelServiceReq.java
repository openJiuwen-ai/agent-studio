/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ModelServiceReq
 */

@Validated

public class ModelServiceReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("provider_id")
    @Schema(description = "供应商ID", example = "provider_001")
    @Length(max = 40)
    private String providerId = null;

    @JsonProperty("service_name")
    @Schema(description = "服务名称", example = "my-service")
    @Pattern(
        regexp = "^[\\u4e00-\\u9fa5a-zA-Z0-9](?:[\\u4e00-\\u9fa5a-zA-Z0-9_.\\\\\\/:| -]{0,62}[\\u4e00-\\u9fa5a-zA-Z0-9_-])?$")
    private String serviceName = null;

    @JsonProperty("model_name")
    @Schema(description = "模型名称", example = "gpt-4")
    @Pattern(
        regexp = "^[\\u4e00-\\u9fa5a-zA-Z0-9](?:[\\u4e00-\\u9fa5a-zA-Z0-9_.\\\\\\/:| -@]{0,62}[\\u4e00-\\u9fa5a-zA-Z0-9_-])?$")
    private String modelName = null;

    @JsonProperty("model_type")
    @Schema(description = "模型类型", example = "LLM")
    @Pattern(regexp = "(LLM|Text-Embedding|RERANK|IMAGE-TO-TEXT)")
    private String modelType = null;

    @JsonProperty("model_tags")
    @Schema(description = "模型标签", example = "tag1,tag2")
    @Length(max = 1024)
    private String modelTags = null;

    @JsonProperty("model_description")
    @Schema(description = "模型描述", example = "这是一个大语言模型")
    @Length(max = 1024)
    private String modelDescription = null;

    @JsonProperty("api_url")
    @Schema(description = "API地址", example = "https://api.example.com/v1")
    @Length(max = 255)
    private String apiUrl = null;

    @JsonProperty("is_support_function")
    @Schema(description = "是否支持函数调用", example = "true")
    private Boolean isSupportFunction = null;

    @JsonProperty("logo")
    @Schema(description = "图标", example = "logo.png")
    private String logo = null;

    @JsonProperty("is_public")
    @Schema(description = "是否公开", example = "false")
    private Boolean isPublic = null;

    @JsonProperty("is_network")
    @Schema(description = "是否联网", example = "true")
    private Boolean isNetwork = null;

    @JsonProperty("is_reasoning")
    @Schema(description = "是否支持推理", example = "true")
    private Boolean isReasoning = null;

    @JsonProperty("is_support_close_reasoning")
    @Schema(description = "是否支持关闭推理", example = "false")
    private Boolean isSupportCloseReasoning = null;

    @JsonProperty("interface_protocol")
    @Schema(description = "接口协议", example = "OpenAI")
    private String interfaceProtocol = null;

    @JsonProperty("is_support_stream")
    @Schema(description = "是否支持流式输出", example = "true")
    private Boolean isSupportStream = null;

    @JsonProperty("model_size")
    @Schema(description = "模型大小", example = "7.0")
    @Range(min = 0L)
    private Float modelSize = null;

    @JsonProperty("context_length")
    @Schema(description = "上下文长度", example = "4096")
    private Integer contextLength = null;

    @JsonProperty("throttling_policy")
    @Schema(description = "限流策略", example = "10")
    private ThrottlingPolicyEnum throttlingPolicy = null;

    public String getProviderId() {
        return providerId;
    }

    public ModelServiceReq setProviderId(String providerId) {
        this.providerId = providerId;
        return this;
    }

    public String getServiceName() {
        return serviceName;
    }

    public ModelServiceReq setServiceName(String serviceName) {
        this.serviceName = serviceName;
        return this;
    }

    public String getModelName() {
        return modelName;
    }

    public ModelServiceReq setModelName(String modelName) {
        this.modelName = modelName;
        return this;
    }

    public String getModelType() {
        return modelType;
    }

    public ModelServiceReq setModelType(String modelType) {
        this.modelType = modelType;
        return this;
    }

    public String getModelTags() {
        return modelTags;
    }

    public ModelServiceReq setModelTags(String modelTags) {
        this.modelTags = modelTags;
        return this;
    }

    public String getModelDescription() {
        return modelDescription;
    }

    public ModelServiceReq setModelDescription(String modelDescription) {
        this.modelDescription = modelDescription;
        return this;
    }

    public String getApiUrl() {
        return apiUrl;
    }

    public ModelServiceReq setApiUrl(String apiUrl) {
        this.apiUrl = apiUrl;
        return this;
    }

    public ModelServiceReq setIsSupportFunction(Boolean isSupportFunction) {
        this.isSupportFunction = isSupportFunction;
        return this;
    }

    public Boolean isIsSupportFunction() {
        return isSupportFunction;
    }

    public String getLogo() {
        return logo;
    }

    public ModelServiceReq setLogo(String logo) {
        this.logo = logo;
        return this;
    }

    public ModelServiceReq setIsPublic(Boolean isPublic) {
        this.isPublic = isPublic;
        return this;
    }

    public Boolean isIsPublic() {
        return isPublic;
    }

    public ModelServiceReq setIsNetwork(Boolean isNetwork) {
        this.isNetwork = isNetwork;
        return this;
    }

    public Boolean isIsNetwork() {
        return isNetwork;
    }

    public ModelServiceReq setIsReasoning(Boolean isReasoning) {
        this.isReasoning = isReasoning;
        return this;
    }

    public Boolean isIsReasoning() {
        return isReasoning;
    }

    public ModelServiceReq setIsSupportCloseReasoning(Boolean isSupportCloseReasoning) {
        this.isSupportCloseReasoning = isSupportCloseReasoning;
        return this;
    }

    public Boolean isIsSupportCloseReasoning() {
        return isSupportCloseReasoning;
    }

    public String getInterfaceProtocol() {
        return interfaceProtocol;
    }

    public ModelServiceReq setInterfaceProtocol(String interfaceProtocol) {
        this.interfaceProtocol = interfaceProtocol;
        return this;
    }

    public ModelServiceReq setIsSupportStream(Boolean isSupportStream) {
        this.isSupportStream = isSupportStream;
        return this;
    }

    public Boolean isIsSupportStream() {
        return isSupportStream;
    }

    public Float getModelSize() {
        return modelSize;
    }

    public ModelServiceReq setModelSize(Float modelSize) {
        this.modelSize = modelSize;
        return this;
    }

    public Integer getContextLength() {
        return contextLength;
    }

    public ModelServiceReq setContextLength(Integer contextLength) {
        this.contextLength = contextLength;
        return this;
    }

    public ThrottlingPolicyEnum getThrottlingPolicy() {
        return throttlingPolicy;
    }

    public ModelServiceReq setThrottlingPolicy(ThrottlingPolicyEnum throttlingPolicy) {
        this.throttlingPolicy = throttlingPolicy;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ModelServiceReq {\n");

        sb.append("    providerId: ").append(toIndentedString(providerId)).append("\n");
        sb.append("    serviceName: ").append(toIndentedString(serviceName)).append("\n");
        sb.append("    modelName: ").append(toIndentedString(modelName)).append("\n");
        sb.append("    modelType: ").append(toIndentedString(modelType)).append("\n");
        sb.append("    modelTags: ").append(toIndentedString(modelTags)).append("\n");
        sb.append("    modelDescription: ").append(toIndentedString(modelDescription)).append("\n");
        sb.append("    apiUrl: ").append(toIndentedString(apiUrl)).append("\n");
        sb.append("    isSupportFunction: ").append(toIndentedString(isSupportFunction)).append("\n");
        sb.append("    logo: ").append(toIndentedString(logo)).append("\n");
        sb.append("    isPublic: ").append(toIndentedString(isPublic)).append("\n");
        sb.append("    isNetwork: ").append(toIndentedString(isNetwork)).append("\n");
        sb.append("    isReasoning: ").append(toIndentedString(isReasoning)).append("\n");
        sb.append("    isSupportCloseReasoning: ").append(toIndentedString(isSupportCloseReasoning)).append("\n");
        sb.append("    interfaceProtocol: ").append(toIndentedString(interfaceProtocol)).append("\n");
        sb.append("    isSupportStream: ").append(toIndentedString(isSupportStream)).append("\n");
        sb.append("    modelSize: ").append(toIndentedString(modelSize)).append("\n");
        sb.append("    contextLength: ").append(toIndentedString(contextLength)).append("\n");
        sb.append("    throttlingPolicy: ").append(toIndentedString(throttlingPolicy)).append("\n");
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
        ModelServiceReq modelServiceReq = (ModelServiceReq) o;
        return Objects.equals(this.providerId, modelServiceReq.providerId) && Objects.equals(this.serviceName,
            modelServiceReq.serviceName) && Objects.equals(this.modelName, modelServiceReq.modelName) && Objects.equals(
            this.modelType, modelServiceReq.modelType) && Objects.equals(this.modelTags, modelServiceReq.modelTags)
            && Objects.equals(this.modelDescription, modelServiceReq.modelDescription) && Objects.equals(this.apiUrl,
            modelServiceReq.apiUrl) && Objects.equals(this.isSupportFunction, modelServiceReq.isSupportFunction)
            && Objects.equals(this.logo, modelServiceReq.logo) && Objects.equals(this.isPublic,
            modelServiceReq.isPublic) && Objects.equals(this.isNetwork, modelServiceReq.isNetwork) && Objects.equals(
            this.isReasoning, modelServiceReq.isReasoning) && Objects.equals(this.isSupportCloseReasoning,
            modelServiceReq.isSupportCloseReasoning) && Objects.equals(this.interfaceProtocol,
            modelServiceReq.interfaceProtocol) && Objects.equals(this.isSupportStream, modelServiceReq.isSupportStream)
            && Objects.equals(this.modelSize, modelServiceReq.modelSize) && Objects.equals(this.contextLength,
            modelServiceReq.contextLength) && Objects.equals(this.throttlingPolicy, modelServiceReq.throttlingPolicy);
    }

    @Override
    public int hashCode() {
        return Objects.hash(providerId, serviceName, modelName, modelType, modelTags, modelDescription, apiUrl,
            isSupportFunction, logo, isPublic, isNetwork, isReasoning, isSupportCloseReasoning, interfaceProtocol,
            isSupportStream, modelSize, contextLength, throttlingPolicy);
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

    /**
     * Gets or Sets throttlingPolicy
     */
    public enum ThrottlingPolicyEnum {
        _10("10"),

        _50("50"),

        _100("100"),

        _200("200"),

        EMPTY("");

        private String value;

        ThrottlingPolicyEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static ThrottlingPolicyEnum fromValue(String text) {
            for (ThrottlingPolicyEnum b : ThrottlingPolicyEnum.values()) {
                if (String.valueOf(b.value).equals(text)) {
                    return b;
                }
            }
            return null;
        }

        @Override
        @JsonValue
        public String toString() {
            return String.valueOf(value);
        }
    }
}
