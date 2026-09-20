/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 默认知识库连接详情
 */
@ApiModel(description = "默认知识库连接详情")

@Validated

public class DefaultKnowledgeBaseConnectionDetail implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "连接ID", example = "conn_001")
    private String id = null;

    @JsonProperty("connector_id")
    @Schema(description = "连接器ID", example = "connector_001")
    private String connectorId = null;

    @JsonProperty("connector_name")
    @Schema(description = "连接器名称", example = "默认知识库连接器")
    private String connectorName = null;

    @JsonProperty("params")
    @Schema(description = "连接参数列表", example = "[]")
    @Valid
    @Size()
    private List<ConnectionParamInfo> params = null;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws_001")
    @Length(max = 100)
    private String workspaceId = null;

    @JsonProperty("domain_name")
    @Schema(description = "域名", example = "example.com")
    @Length(max = 100)
    private String domainName = null;

    @JsonProperty("create_user_id")
    @Schema(description = "创建者用户ID", example = "user_001")
    @Length(max = 100)
    private String createUserId = null;

    @JsonProperty("create_user_name")
    @Schema(description = "创建者用户名", example = "张三")
    @Length(max = 100)
    private String createUserName = null;

    @JsonProperty("create_time")
    @Schema(description = "创建时间", example = "1700000000000")
    @Range(min = 0L, max = 9223372036854775807L)
    private Long createTime = null;

    @JsonProperty("update_time")
    @Schema(description = "更新时间", example = "1700000000000")
    @Range(min = 0L, max = 9223372036854775807L)
    private Long updateTime = null;

    @JsonProperty("update_user_id")
    @Schema(description = "更新者用户ID", example = "user_002")
    @Length(max = 100)
    private String updateUserId = null;

    @JsonProperty("update_user_name")
    @Schema(description = "更新者用户名", example = "李四")
    @Length(max = 100)
    private String updateUserName = null;

    public String getId() {
        return id;
    }

    public DefaultKnowledgeBaseConnectionDetail setId(String id) {
        this.id = id;
        return this;
    }

    public String getConnectorId() {
        return connectorId;
    }

    public DefaultKnowledgeBaseConnectionDetail setConnectorId(String connectorId) {
        this.connectorId = connectorId;
        return this;
    }

    public String getConnectorName() {
        return connectorName;
    }

    public DefaultKnowledgeBaseConnectionDetail setConnectorName(String connectorName) {
        this.connectorName = connectorName;
        return this;
    }

    public List<ConnectionParamInfo> getParams() {
        return params;
    }

    public DefaultKnowledgeBaseConnectionDetail setParams(List<ConnectionParamInfo> params) {
        this.params = params;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public DefaultKnowledgeBaseConnectionDetail setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getDomainName() {
        return domainName;
    }

    public DefaultKnowledgeBaseConnectionDetail setDomainName(String domainName) {
        this.domainName = domainName;
        return this;
    }

    public String getCreateUserId() {
        return createUserId;
    }

    public DefaultKnowledgeBaseConnectionDetail setCreateUserId(String createUserId) {
        this.createUserId = createUserId;
        return this;
    }

    public String getCreateUserName() {
        return createUserName;
    }

    public DefaultKnowledgeBaseConnectionDetail setCreateUserName(String createUserName) {
        this.createUserName = createUserName;
        return this;
    }

    public Long getCreateTime() {
        return createTime;
    }

    public DefaultKnowledgeBaseConnectionDetail setCreateTime(Long createTime) {
        this.createTime = createTime;
        return this;
    }

    public Long getUpdateTime() {
        return updateTime;
    }

    public DefaultKnowledgeBaseConnectionDetail setUpdateTime(Long updateTime) {
        this.updateTime = updateTime;
        return this;
    }

    public String getUpdateUserId() {
        return updateUserId;
    }

    public DefaultKnowledgeBaseConnectionDetail setUpdateUserId(String updateUserId) {
        this.updateUserId = updateUserId;
        return this;
    }

    public String getUpdateUserName() {
        return updateUserName;
    }

    public DefaultKnowledgeBaseConnectionDetail setUpdateUserName(String updateUserName) {
        this.updateUserName = updateUserName;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class DefaultKnowledgeBaseConnectionDetail {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    connectorId: ").append(toIndentedString(connectorId)).append("\n");
        sb.append("    connectorName: ").append(toIndentedString(connectorName)).append("\n");
        sb.append("    params: ").append(toIndentedString(params)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    domainName: ").append(toIndentedString(domainName)).append("\n");
        sb.append("    createUserId: ").append(toIndentedString(createUserId)).append("\n");
        sb.append("    createUserName: ").append(toIndentedString(createUserName)).append("\n");
        sb.append("    createTime: ").append(toIndentedString(createTime)).append("\n");
        sb.append("    updateTime: ").append(toIndentedString(updateTime)).append("\n");
        sb.append("    updateUserId: ").append(toIndentedString(updateUserId)).append("\n");
        sb.append("    updateUserName: ").append(toIndentedString(updateUserName)).append("\n");
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
        DefaultKnowledgeBaseConnectionDetail defaultKnowledgeBaseConnectionDetail
            = (DefaultKnowledgeBaseConnectionDetail) o;
        return Objects.equals(this.id, defaultKnowledgeBaseConnectionDetail.id) && Objects.equals(this.connectorId,
            defaultKnowledgeBaseConnectionDetail.connectorId) && Objects.equals(this.connectorName,
            defaultKnowledgeBaseConnectionDetail.connectorName) && Objects.equals(this.params,
            defaultKnowledgeBaseConnectionDetail.params) && Objects.equals(this.workspaceId,
            defaultKnowledgeBaseConnectionDetail.workspaceId) && Objects.equals(this.domainName,
            defaultKnowledgeBaseConnectionDetail.domainName) && Objects.equals(this.createUserId,
            defaultKnowledgeBaseConnectionDetail.createUserId) && Objects.equals(this.createUserName,
            defaultKnowledgeBaseConnectionDetail.createUserName) && Objects.equals(this.createTime,
            defaultKnowledgeBaseConnectionDetail.createTime) && Objects.equals(this.updateTime,
            defaultKnowledgeBaseConnectionDetail.updateTime) && Objects.equals(this.updateUserId,
            defaultKnowledgeBaseConnectionDetail.updateUserId) && Objects.equals(this.updateUserName,
            defaultKnowledgeBaseConnectionDetail.updateUserName);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, connectorId, connectorName, params, workspaceId, domainName, createUserId,
            createUserName, createTime, updateTime, updateUserId, updateUserName);
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
