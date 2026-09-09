/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * AvailableModelServicesQo: converted from multi query params
 */
@ApiModel(description = "AvailableModelServicesQo: converted from multi query params")

@Validated

public class AvailableModelServicesQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("provider_id")
    @Schema(description = "供应商ID", example = "provider_001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
    @Length(max = 50)
    private String providerId = null;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws_001", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$")
    @NotBlank
    private String workspaceId = null;

    @JsonProperty("service_name")
    @Schema(description = "服务名称", example = "my_service")
    @Length(max = 1000)
    private String serviceName = null;

    @JsonProperty("model_name")
    @Schema(description = "模型名称", example = "gpt-4")
    @Pattern(
        regexp = "^[\\u4e00-\\u9fa5a-zA-Z0-9](?:[\\u4e00-\\u9fa5a-zA-Z0-9_.\\/:| -]{0,62}[\\u4e00-\\u9fa5a-zA-Z0-9_-])?$")
    private String modelName = null;

    @JsonProperty("model_type")
    @Schema(description = "模型类型", example = "llm")
    @Pattern(regexp = "^[a-zA-Z0-9,_-]{1,200}$")
    private String modelType = null;

    @JsonProperty("id")
    @Schema(description = "模型服务ID", example = "model_001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]{1,80}$")
    @Length(max = 80)
    private String id = null;

    @JsonProperty("functioncall")
    @Schema(description = "是否支持函数调用", example = "true")
    private Boolean functioncall = null;

    @JsonProperty("publish_status")
    @Schema(description = "发布状态", example = "all")
    @Pattern(regexp = "^(all|online)$")
    @Length(max = 7)
    private String publishStatus = "all";

    @JsonProperty("groupby")
    @Schema(description = "分组字段", example = "provider")
    private String groupby = null;

    @JsonProperty("only_private")
    @Schema(description = "是否仅查询私有", example = "false")
    private Boolean onlyPrivate = null;

    @JsonProperty("with_router")
    @Schema(description = "是否包含路由", example = "false")
    private Boolean withRouter = false;

    @JsonProperty("intent_recognition")
    @Schema(description = "是否意图识别", example = "false")
    private Boolean intentRecognition = false;

    public String getProviderId() {
        return providerId;
    }

    public AvailableModelServicesQo setProviderId(String providerId) {
        this.providerId = providerId;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public AvailableModelServicesQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getServiceName() {
        return serviceName;
    }

    public AvailableModelServicesQo setServiceName(String serviceName) {
        this.serviceName = serviceName;
        return this;
    }

    public String getModelName() {
        return modelName;
    }

    public AvailableModelServicesQo setModelName(String modelName) {
        this.modelName = modelName;
        return this;
    }

    public String getModelType() {
        return modelType;
    }

    public AvailableModelServicesQo setModelType(String modelType) {
        this.modelType = modelType;
        return this;
    }

    public String getId() {
        return id;
    }

    public AvailableModelServicesQo setId(String id) {
        this.id = id;
        return this;
    }

    public AvailableModelServicesQo setFunctioncall(Boolean functioncall) {
        this.functioncall = functioncall;
        return this;
    }

    public Boolean isFunctioncall() {
        return functioncall;
    }

    public String getPublishStatus() {
        return publishStatus;
    }

    public AvailableModelServicesQo setPublishStatus(String publishStatus) {
        this.publishStatus = publishStatus;
        return this;
    }

    public String getGroupby() {
        return groupby;
    }

    public AvailableModelServicesQo setGroupby(String groupby) {
        this.groupby = groupby;
        return this;
    }

    public AvailableModelServicesQo setOnlyPrivate(Boolean onlyPrivate) {
        this.onlyPrivate = onlyPrivate;
        return this;
    }

    public Boolean isOnlyPrivate() {
        return onlyPrivate;
    }

    public AvailableModelServicesQo setWithRouter(Boolean withRouter) {
        this.withRouter = withRouter;
        return this;
    }

    public Boolean isWithRouter() {
        return withRouter;
    }

    public AvailableModelServicesQo setIntentRecognition(Boolean intentRecognition) {
        this.intentRecognition = intentRecognition;
        return this;
    }

    public Boolean isIntentRecognition() {
        return intentRecognition;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class AvailableModelServicesQo {\n");

        sb.append("    providerId: ").append(toIndentedString(providerId)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    serviceName: ").append(toIndentedString(serviceName)).append("\n");
        sb.append("    modelName: ").append(toIndentedString(modelName)).append("\n");
        sb.append("    modelType: ").append(toIndentedString(modelType)).append("\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    functioncall: ").append(toIndentedString(functioncall)).append("\n");
        sb.append("    publishStatus: ").append(toIndentedString(publishStatus)).append("\n");
        sb.append("    groupby: ").append(toIndentedString(groupby)).append("\n");
        sb.append("    onlyPrivate: ").append(toIndentedString(onlyPrivate)).append("\n");
        sb.append("    withRouter: ").append(toIndentedString(withRouter)).append("\n");
        sb.append("    intentRecognition: ").append(toIndentedString(intentRecognition)).append("\n");
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
        AvailableModelServicesQo availableModelServicesQo = (AvailableModelServicesQo) o;
        return Objects.equals(this.providerId, availableModelServicesQo.providerId) && Objects.equals(this.workspaceId,
            availableModelServicesQo.workspaceId) && Objects.equals(this.serviceName,
            availableModelServicesQo.serviceName) && Objects.equals(this.modelName, availableModelServicesQo.modelName)
            && Objects.equals(this.modelType, availableModelServicesQo.modelType) && Objects.equals(this.id,
            availableModelServicesQo.id) && Objects.equals(this.functioncall, availableModelServicesQo.functioncall)
            && Objects.equals(this.publishStatus, availableModelServicesQo.publishStatus) && Objects.equals(
            this.groupby, availableModelServicesQo.groupby) && Objects.equals(this.onlyPrivate,
            availableModelServicesQo.onlyPrivate) && Objects.equals(this.withRouter,
            availableModelServicesQo.withRouter) && Objects.equals(this.intentRecognition,
            availableModelServicesQo.intentRecognition);
    }

    @Override
    public int hashCode() {
        return Objects.hash(providerId, workspaceId, serviceName, modelName, modelType, id, functioncall, publishStatus,
            groupby, onlyPrivate, withRouter, intentRecognition);
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
