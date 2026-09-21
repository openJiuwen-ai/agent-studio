/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ThirdPartyKnowledgeBaseConnectionListItem
 */

@Validated

public class ThirdPartyKnowledgeBaseConnectionListItem implements Serializable {
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

    @JsonProperty("name")
    @Schema(description = "连接名称", example = "我的知识库连接")
    private String name = null;

    @JsonProperty("icon")
    @Schema(description = "图标地址", example = "https://example.com/icon.png")
    private String icon = null;

    @JsonProperty("status")
    @Schema(description = "连接状态", example = "OPEN")
    private StatusEnum status = null;

    @JsonProperty("description")
    @Schema(description = "连接描述", example = "知识库连接描述")
    private String description = null;

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

    @JsonProperty("create_time")
    @Schema(description = "创建时间", example = "1700000000000")
    @Range(min = 0L, max = 9223372036854775807L)
    private Long createTime = null;

    @JsonProperty("update_user_id")
    @Schema(description = "更新用户ID", example = "user-002")
    @Length(max = 100)
    private String updateUserId = null;

    @JsonProperty("update_user_name")
    @Schema(description = "更新用户名称", example = "李四")
    @Length(max = 100)
    private String updateUserName = null;

    @JsonProperty("update_time")
    @Schema(description = "更新时间", example = "1700000000000")
    @Range(min = 0L, max = 9223372036854775807L)
    private Long updateTime = null;

    public String getId() {
        return id;
    }

    public ThirdPartyKnowledgeBaseConnectionListItem setId(String id) {
        this.id = id;
        return this;
    }

    public String getConnectorId() {
        return connectorId;
    }

    public ThirdPartyKnowledgeBaseConnectionListItem setConnectorId(String connectorId) {
        this.connectorId = connectorId;
        return this;
    }

    public String getConnectorName() {
        return connectorName;
    }

    public ThirdPartyKnowledgeBaseConnectionListItem setConnectorName(String connectorName) {
        this.connectorName = connectorName;
        return this;
    }

    public String getName() {
        return name;
    }

    public ThirdPartyKnowledgeBaseConnectionListItem setName(String name) {
        this.name = name;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public ThirdPartyKnowledgeBaseConnectionListItem setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public StatusEnum getStatus() {
        return status;
    }

    public ThirdPartyKnowledgeBaseConnectionListItem setStatus(StatusEnum status) {
        this.status = status;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ThirdPartyKnowledgeBaseConnectionListItem setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ThirdPartyKnowledgeBaseConnectionListItem setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getDomainName() {
        return domainName;
    }

    public ThirdPartyKnowledgeBaseConnectionListItem setDomainName(String domainName) {
        this.domainName = domainName;
        return this;
    }

    public String getCreateUserId() {
        return createUserId;
    }

    public ThirdPartyKnowledgeBaseConnectionListItem setCreateUserId(String createUserId) {
        this.createUserId = createUserId;
        return this;
    }

    public String getCreateUserName() {
        return createUserName;
    }

    public ThirdPartyKnowledgeBaseConnectionListItem setCreateUserName(String createUserName) {
        this.createUserName = createUserName;
        return this;
    }

    public Long getCreateTime() {
        return createTime;
    }

    public ThirdPartyKnowledgeBaseConnectionListItem setCreateTime(Long createTime) {
        this.createTime = createTime;
        return this;
    }

    public String getUpdateUserId() {
        return updateUserId;
    }

    public ThirdPartyKnowledgeBaseConnectionListItem setUpdateUserId(String updateUserId) {
        this.updateUserId = updateUserId;
        return this;
    }

    public String getUpdateUserName() {
        return updateUserName;
    }

    public ThirdPartyKnowledgeBaseConnectionListItem setUpdateUserName(String updateUserName) {
        this.updateUserName = updateUserName;
        return this;
    }

    public Long getUpdateTime() {
        return updateTime;
    }

    public ThirdPartyKnowledgeBaseConnectionListItem setUpdateTime(Long updateTime) {
        this.updateTime = updateTime;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ThirdPartyKnowledgeBaseConnectionListItem {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    connectorId: ").append(toIndentedString(connectorId)).append("\n");
        sb.append("    connectorName: ").append(toIndentedString(connectorName)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    domainName: ").append(toIndentedString(domainName)).append("\n");
        sb.append("    createUserId: ").append(toIndentedString(createUserId)).append("\n");
        sb.append("    createUserName: ").append(toIndentedString(createUserName)).append("\n");
        sb.append("    createTime: ").append(toIndentedString(createTime)).append("\n");
        sb.append("    updateUserId: ").append(toIndentedString(updateUserId)).append("\n");
        sb.append("    updateUserName: ").append(toIndentedString(updateUserName)).append("\n");
        sb.append("    updateTime: ").append(toIndentedString(updateTime)).append("\n");
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
        ThirdPartyKnowledgeBaseConnectionListItem thirdPartyKnowledgeBaseConnectionListItem
            = (ThirdPartyKnowledgeBaseConnectionListItem) o;
        return Objects.equals(this.id, thirdPartyKnowledgeBaseConnectionListItem.id) && Objects.equals(this.connectorId,
            thirdPartyKnowledgeBaseConnectionListItem.connectorId) && Objects.equals(this.connectorName,
            thirdPartyKnowledgeBaseConnectionListItem.connectorName) && Objects.equals(this.name,
            thirdPartyKnowledgeBaseConnectionListItem.name) && Objects.equals(this.icon,
            thirdPartyKnowledgeBaseConnectionListItem.icon) && Objects.equals(this.status,
            thirdPartyKnowledgeBaseConnectionListItem.status) && Objects.equals(this.description,
            thirdPartyKnowledgeBaseConnectionListItem.description) && Objects.equals(this.workspaceId,
            thirdPartyKnowledgeBaseConnectionListItem.workspaceId) && Objects.equals(this.domainName,
            thirdPartyKnowledgeBaseConnectionListItem.domainName) && Objects.equals(this.createUserId,
            thirdPartyKnowledgeBaseConnectionListItem.createUserId) && Objects.equals(this.createUserName,
            thirdPartyKnowledgeBaseConnectionListItem.createUserName) && Objects.equals(this.createTime,
            thirdPartyKnowledgeBaseConnectionListItem.createTime) && Objects.equals(this.updateUserId,
            thirdPartyKnowledgeBaseConnectionListItem.updateUserId) && Objects.equals(this.updateUserName,
            thirdPartyKnowledgeBaseConnectionListItem.updateUserName) && Objects.equals(this.updateTime,
            thirdPartyKnowledgeBaseConnectionListItem.updateTime);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, connectorId, connectorName, name, icon, status, description, workspaceId, domainName,
            createUserId, createUserName, createTime, updateUserId, updateUserName, updateTime);
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
