/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

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
 * 第三方知识库连接详情
 */
@ApiModel(description = "第三方知识库连接详情")

@Validated

public class ThirdPartyKnowledgeBaseConnectionDetail implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "连接ID", example = "conn-001")
    private String id = null;

    @JsonProperty("connector_id")
    @Schema(description = "连接器ID", example = "connector-001")
    private String connectorId = null;

    @JsonProperty("connector_name")
    @Schema(description = "连接器名称", example = "Weaviate")
    private String connectorName = null;

    @JsonProperty("status")
    @Schema(description = "连接状态", example = "OPEN")
    private StatusEnum status = null;

    @JsonProperty("name")
    @Schema(description = "连接名称", example = "我的知识库连接")
    private String name = null;

    @JsonProperty("icon")
    @Schema(description = "图标地址", example = "https://example.com/icon.png")
    private String icon = null;

    @JsonProperty("description")
    @Schema(description = "连接描述", example = "知识库连接描述")
    private String description = null;

    @JsonProperty("params")
    @Schema(description = "连接参数列表", example = "[]")
    @Valid
    @Size()
    private List<ConnectionParamInfo> params = null;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "workspace-001")
    @Length(max = 100)
    private String workspaceId = null;

    @JsonProperty("domain_name")
    @Schema(description = "域名", example = "example.com")
    @Length(max = 100)
    private String domainName = null;

    @JsonProperty("create_user_id")
    @Schema(description = "创建用户ID", example = "user-001")
    @Length(max = 100)
    private String createUserId = null;

    @JsonProperty("create_user_name")
    @Schema(description = "创建用户名称", example = "张三")
    @Length(max = 100)
    private String createUserName = null;

    @JsonProperty("update_time")
    @Schema(description = "更新时间", example = "1700000000000")
    @Range(min = 0L, max = 9223372036854775807L)
    private Long updateTime = null;

    @JsonProperty("update_user_id")
    @Schema(description = "更新用户ID", example = "user-002")
    @Length(max = 100)
    private String updateUserId = null;

    @JsonProperty("update_user_name")
    @Schema(description = "更新用户名称", example = "李四")
    @Length(max = 100)
    private String updateUserName = null;

    public String getId() {
        return id;
    }

    public ThirdPartyKnowledgeBaseConnectionDetail setId(String id) {
        this.id = id;
        return this;
    }

    public String getConnectorId() {
        return connectorId;
    }

    public ThirdPartyKnowledgeBaseConnectionDetail setConnectorId(String connectorId) {
        this.connectorId = connectorId;
        return this;
    }

    public String getConnectorName() {
        return connectorName;
    }

    public ThirdPartyKnowledgeBaseConnectionDetail setConnectorName(String connectorName) {
        this.connectorName = connectorName;
        return this;
    }

    public StatusEnum getStatus() {
        return status;
    }

    public ThirdPartyKnowledgeBaseConnectionDetail setStatus(StatusEnum status) {
        this.status = status;
        return this;
    }

    public String getName() {
        return name;
    }

    public ThirdPartyKnowledgeBaseConnectionDetail setName(String name) {
        this.name = name;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public ThirdPartyKnowledgeBaseConnectionDetail setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ThirdPartyKnowledgeBaseConnectionDetail setDescription(String description) {
        this.description = description;
        return this;
    }

    public List<ConnectionParamInfo> getParams() {
        return params;
    }

    public ThirdPartyKnowledgeBaseConnectionDetail setParams(List<ConnectionParamInfo> params) {
        this.params = params;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ThirdPartyKnowledgeBaseConnectionDetail setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getDomainName() {
        return domainName;
    }

    public ThirdPartyKnowledgeBaseConnectionDetail setDomainName(String domainName) {
        this.domainName = domainName;
        return this;
    }

    public String getCreateUserId() {
        return createUserId;
    }

    public ThirdPartyKnowledgeBaseConnectionDetail setCreateUserId(String createUserId) {
        this.createUserId = createUserId;
        return this;
    }

    public String getCreateUserName() {
        return createUserName;
    }

    public ThirdPartyKnowledgeBaseConnectionDetail setCreateUserName(String createUserName) {
        this.createUserName = createUserName;
        return this;
    }

    public Long getUpdateTime() {
        return updateTime;
    }

    public ThirdPartyKnowledgeBaseConnectionDetail setUpdateTime(Long updateTime) {
        this.updateTime = updateTime;
        return this;
    }

    public String getUpdateUserId() {
        return updateUserId;
    }

    public ThirdPartyKnowledgeBaseConnectionDetail setUpdateUserId(String updateUserId) {
        this.updateUserId = updateUserId;
        return this;
    }

    public String getUpdateUserName() {
        return updateUserName;
    }

    public ThirdPartyKnowledgeBaseConnectionDetail setUpdateUserName(String updateUserName) {
        this.updateUserName = updateUserName;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ThirdPartyKnowledgeBaseConnectionDetail {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    connectorId: ").append(toIndentedString(connectorId)).append("\n");
        sb.append("    connectorName: ").append(toIndentedString(connectorName)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    params: ").append(toIndentedString(params)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    domainName: ").append(toIndentedString(domainName)).append("\n");
        sb.append("    createUserId: ").append(toIndentedString(createUserId)).append("\n");
        sb.append("    createUserName: ").append(toIndentedString(createUserName)).append("\n");
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
        ThirdPartyKnowledgeBaseConnectionDetail thirdPartyKnowledgeBaseConnectionDetail
            = (ThirdPartyKnowledgeBaseConnectionDetail) o;
        return Objects.equals(this.id, thirdPartyKnowledgeBaseConnectionDetail.id) && Objects.equals(this.connectorId,
            thirdPartyKnowledgeBaseConnectionDetail.connectorId) && Objects.equals(this.connectorName,
            thirdPartyKnowledgeBaseConnectionDetail.connectorName) && Objects.equals(this.status,
            thirdPartyKnowledgeBaseConnectionDetail.status) && Objects.equals(this.name,
            thirdPartyKnowledgeBaseConnectionDetail.name) && Objects.equals(this.icon,
            thirdPartyKnowledgeBaseConnectionDetail.icon) && Objects.equals(this.description,
            thirdPartyKnowledgeBaseConnectionDetail.description) && Objects.equals(this.params,
            thirdPartyKnowledgeBaseConnectionDetail.params) && Objects.equals(this.workspaceId,
            thirdPartyKnowledgeBaseConnectionDetail.workspaceId) && Objects.equals(this.domainName,
            thirdPartyKnowledgeBaseConnectionDetail.domainName) && Objects.equals(this.createUserId,
            thirdPartyKnowledgeBaseConnectionDetail.createUserId) && Objects.equals(this.createUserName,
            thirdPartyKnowledgeBaseConnectionDetail.createUserName) && Objects.equals(this.updateTime,
            thirdPartyKnowledgeBaseConnectionDetail.updateTime) && Objects.equals(this.updateUserId,
            thirdPartyKnowledgeBaseConnectionDetail.updateUserId) && Objects.equals(this.updateUserName,
            thirdPartyKnowledgeBaseConnectionDetail.updateUserName);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, connectorId, connectorName, status, name, icon, description, params, workspaceId,
            domainName, createUserId, createUserName, updateTime, updateUserId, updateUserName);
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
     * 状态,OPEN-开启，CLOSE-关闭
     */
    public enum StatusEnum {
        OPEN("OPEN"),

        CLOSE("CLOSE");

        private String value;

        StatusEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static StatusEnum fromValue(String text) {
            for (StatusEnum b : StatusEnum.values()) {
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
