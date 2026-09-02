/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * DefaultKnowledgeBaseConnectionListItem
 */

@Validated

public class DefaultKnowledgeBaseConnectionListItem implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "连接ID", example = "conn_001")
    private String id = null;

    @JsonProperty("connector_id")
    @Schema(description = "连接器ID", example = "connector_001")
    private String connectorId = null;

    @JsonProperty("description")
    @Schema(description = "连接描述", example = "知识库连接")
    private String description = null;

    @JsonProperty("domain_name")
    @Schema(description = "域名", example = "example.com")
    @Length(max = 100)
    private String domainName = null;

    @JsonProperty("create_user_id")
    @Schema(description = "创建用户ID", example = "user001")
    @Length(max = 100)
    private String createUserId = null;

    @JsonProperty("create_user_name")
    @Schema(description = "创建用户名称", example = "张三")
    @Length(max = 100)
    private String createUserName = null;

    @JsonProperty("create_time")
    @Schema(description = "创建时间", example = "1717200000000")
    @Range(min = 0L, max = 9223372036854775807L)
    private Long createTime = null;

    @JsonProperty("update_user_id")
    @Schema(description = "更新用户ID", example = "user002")
    @Length(max = 100)
    private String updateUserId = null;

    @JsonProperty("update_user_name")
    @Schema(description = "更新用户名称", example = "李四")
    @Length(max = 100)
    private String updateUserName = null;

    @JsonProperty("update_time")
    @Schema(description = "更新时间", example = "1717200000000")
    @Range(min = 0L, max = 9223372036854775807L)
    private Long updateTime = null;

    public String getId() {
        return id;
    }

    public DefaultKnowledgeBaseConnectionListItem setId(String id) {
        this.id = id;
        return this;
    }

    public String getConnectorId() {
        return connectorId;
    }

    public DefaultKnowledgeBaseConnectionListItem setConnectorId(String connectorId) {
        this.connectorId = connectorId;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public DefaultKnowledgeBaseConnectionListItem setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getDomainName() {
        return domainName;
    }

    public DefaultKnowledgeBaseConnectionListItem setDomainName(String domainName) {
        this.domainName = domainName;
        return this;
    }

    public String getCreateUserId() {
        return createUserId;
    }

    public DefaultKnowledgeBaseConnectionListItem setCreateUserId(String createUserId) {
        this.createUserId = createUserId;
        return this;
    }

    public String getCreateUserName() {
        return createUserName;
    }

    public DefaultKnowledgeBaseConnectionListItem setCreateUserName(String createUserName) {
        this.createUserName = createUserName;
        return this;
    }

    public Long getCreateTime() {
        return createTime;
    }

    public DefaultKnowledgeBaseConnectionListItem setCreateTime(Long createTime) {
        this.createTime = createTime;
        return this;
    }

    public String getUpdateUserId() {
        return updateUserId;
    }

    public DefaultKnowledgeBaseConnectionListItem setUpdateUserId(String updateUserId) {
        this.updateUserId = updateUserId;
        return this;
    }

    public String getUpdateUserName() {
        return updateUserName;
    }

    public DefaultKnowledgeBaseConnectionListItem setUpdateUserName(String updateUserName) {
        this.updateUserName = updateUserName;
        return this;
    }

    public Long getUpdateTime() {
        return updateTime;
    }

    public DefaultKnowledgeBaseConnectionListItem setUpdateTime(Long updateTime) {
        this.updateTime = updateTime;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class DefaultKnowledgeBaseConnectionListItem {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    connectorId: ").append(toIndentedString(connectorId)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
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
        DefaultKnowledgeBaseConnectionListItem defaultKnowledgeBaseConnectionListItem
            = (DefaultKnowledgeBaseConnectionListItem) o;
        return Objects.equals(this.id, defaultKnowledgeBaseConnectionListItem.id) && Objects.equals(this.connectorId,
            defaultKnowledgeBaseConnectionListItem.connectorId) && Objects.equals(this.description,
            defaultKnowledgeBaseConnectionListItem.description) && Objects.equals(this.domainName,
            defaultKnowledgeBaseConnectionListItem.domainName) && Objects.equals(this.createUserId,
            defaultKnowledgeBaseConnectionListItem.createUserId) && Objects.equals(this.createUserName,
            defaultKnowledgeBaseConnectionListItem.createUserName) && Objects.equals(this.createTime,
            defaultKnowledgeBaseConnectionListItem.createTime) && Objects.equals(this.updateUserId,
            defaultKnowledgeBaseConnectionListItem.updateUserId) && Objects.equals(this.updateUserName,
            defaultKnowledgeBaseConnectionListItem.updateUserName) && Objects.equals(this.updateTime,
            defaultKnowledgeBaseConnectionListItem.updateTime);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, connectorId, description, domainName, createUserId, createUserName, createTime,
            updateUserId, updateUserName, updateTime);
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
