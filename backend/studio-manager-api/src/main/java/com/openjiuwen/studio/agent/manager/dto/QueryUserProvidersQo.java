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
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * QueryUserProvidersQo: converted from multi query params
 */
@ApiModel(description = "QueryUserProvidersQo: converted from multi query params")

@Validated

public class QueryUserProvidersQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws_001", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$")
    @NotBlank
    private String workspaceId = null;

    @JsonProperty("query")
    @Schema(description = "查询关键词", example = "gpt")
    @Pattern(regexp = "^[\\u4e00-\\u9fa5a-zA-Z0-9_ :./\\\\|-]{1,64}$")
    @Length(max = 64)
    private String query = null;

    @JsonProperty("page_num")
    @Schema(description = "页码", example = "1")
    @Range(min = 1L)
    private Integer pageNum = 1;

    @JsonProperty("page_size")
    @Schema(description = "每页数量", example = "12")
    @Range(min = 1L, max = 500L)
    private Integer pageSize = 12;

    @JsonProperty("auth_config_status")
    @Schema(description = "鉴权配置状态", example = "available")
    @Pattern(regexp = "(available|no_exist|part_available)")
    private String authConfigStatus = null;

    @JsonProperty("model_type")
    @Schema(description = "模型类型", example = "LLM")
    @Pattern(
        regexp = "(LLM|Text-Embedding|RERANK|TEXT-TO-IMAGE|IMAGE-TO-TEXT|AUDIO-TO-TEXT|TEXT-TO-AUDIO|TEXT-IMAGE-EMBEDDING)")
    private String modelType = null;

    @JsonProperty("model_name")
    @Schema(description = "模型名称", example = "gpt-4")
    @Pattern(
        regexp = "^[\\u4e00-\\u9fa5a-zA-Z0-9](?:[\\u4e00-\\u9fa5a-zA-Z0-9_.\\/:|\\ -]{0,62}[\\u4e00-\\u9fa5a-zA-Z0-9_-])?$")
    @Length(max = 64)
    private String modelName = null;

    @JsonProperty("id")
    @Schema(description = "供应商ID", example = "provider_001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]{1,80}$")
    @Length(max = 80)
    private String id = null;

    @JsonProperty("functioncall")
    @Schema(description = "是否支持函数调用", example = "true")
    private Boolean functioncall = null;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public QueryUserProvidersQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getQuery() {
        return query;
    }

    public QueryUserProvidersQo setQuery(String query) {
        this.query = query;
        return this;
    }

    public Integer getPageNum() {
        return pageNum;
    }

    public QueryUserProvidersQo setPageNum(Integer pageNum) {
        this.pageNum = pageNum;
        return this;
    }

    public Integer getPageSize() {
        return pageSize;
    }

    public QueryUserProvidersQo setPageSize(Integer pageSize) {
        this.pageSize = pageSize;
        return this;
    }

    public String getAuthConfigStatus() {
        return authConfigStatus;
    }

    public QueryUserProvidersQo setAuthConfigStatus(String authConfigStatus) {
        this.authConfigStatus = authConfigStatus;
        return this;
    }

    public String getModelType() {
        return modelType;
    }

    public QueryUserProvidersQo setModelType(String modelType) {
        this.modelType = modelType;
        return this;
    }

    public String getModelName() {
        return modelName;
    }

    public QueryUserProvidersQo setModelName(String modelName) {
        this.modelName = modelName;
        return this;
    }

    public String getId() {
        return id;
    }

    public QueryUserProvidersQo setId(String id) {
        this.id = id;
        return this;
    }

    public QueryUserProvidersQo setFunctioncall(Boolean functioncall) {
        this.functioncall = functioncall;
        return this;
    }

    public Boolean isFunctioncall() {
        return functioncall;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class QueryUserProvidersQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    query: ").append(toIndentedString(query)).append("\n");
        sb.append("    pageNum: ").append(toIndentedString(pageNum)).append("\n");
        sb.append("    pageSize: ").append(toIndentedString(pageSize)).append("\n");
        sb.append("    authConfigStatus: ").append(toIndentedString(authConfigStatus)).append("\n");
        sb.append("    modelType: ").append(toIndentedString(modelType)).append("\n");
        sb.append("    modelName: ").append(toIndentedString(modelName)).append("\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    functioncall: ").append(toIndentedString(functioncall)).append("\n");
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
        QueryUserProvidersQo queryUserProvidersQo = (QueryUserProvidersQo) o;
        return Objects.equals(this.workspaceId, queryUserProvidersQo.workspaceId) && Objects.equals(this.query,
            queryUserProvidersQo.query) && Objects.equals(this.pageNum, queryUserProvidersQo.pageNum) && Objects.equals(
            this.pageSize, queryUserProvidersQo.pageSize) && Objects.equals(this.authConfigStatus,
            queryUserProvidersQo.authConfigStatus) && Objects.equals(this.modelType, queryUserProvidersQo.modelType)
            && Objects.equals(this.modelName, queryUserProvidersQo.modelName) && Objects.equals(this.id,
            queryUserProvidersQo.id) && Objects.equals(this.functioncall, queryUserProvidersQo.functioncall);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, query, pageNum, pageSize, authConfigStatus, modelType, modelName, id,
            functioncall);
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
