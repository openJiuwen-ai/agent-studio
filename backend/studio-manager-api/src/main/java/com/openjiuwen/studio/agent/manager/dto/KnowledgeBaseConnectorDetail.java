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
 * 第三方知识库连接器信息
 */
@ApiModel(description = "第三方知识库连接器信息")

@Validated

public class KnowledgeBaseConnectorDetail implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "连接器ID", example = "connector-001")
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "连接器名称", example = "Weaviate")
    private String name = null;

    @JsonProperty("icon")
    @Schema(description = "图标地址", example = "https://example.com/icon.png")
    private String icon = null;

    @JsonProperty("description")
    @Schema(description = "连接器描述", example = "向量数据库连接器")
    private String description = null;

    @JsonProperty("deploy_mode")
    @Schema(description = "部署模式", example = "remote")
    private String deployMode = null;

    @JsonProperty("help_text")
    @Schema(description = "帮助文本", example = "请填写连接参数")
    private String helpText = null;

    @JsonProperty("param_definition")
    @Schema(description = "参数定义列表", example = "[]")
    @Valid
    @Size(max = 10)
    private List<ParamDefinitionInfo> paramDefinition = null;

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

    public KnowledgeBaseConnectorDetail setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public KnowledgeBaseConnectorDetail setName(String name) {
        this.name = name;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public KnowledgeBaseConnectorDetail setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public KnowledgeBaseConnectorDetail setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getDeployMode() {
        return deployMode;
    }

    public KnowledgeBaseConnectorDetail setDeployMode(String deployMode) {
        this.deployMode = deployMode;
        return this;
    }

    public String getHelpText() {
        return helpText;
    }

    public KnowledgeBaseConnectorDetail setHelpText(String helpText) {
        this.helpText = helpText;
        return this;
    }

    public List<ParamDefinitionInfo> getParamDefinition() {
        return paramDefinition;
    }

    public KnowledgeBaseConnectorDetail setParamDefinition(List<ParamDefinitionInfo> paramDefinition) {
        this.paramDefinition = paramDefinition;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public KnowledgeBaseConnectorDetail setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getDomainName() {
        return domainName;
    }

    public KnowledgeBaseConnectorDetail setDomainName(String domainName) {
        this.domainName = domainName;
        return this;
    }

    public String getCreateUserId() {
        return createUserId;
    }

    public KnowledgeBaseConnectorDetail setCreateUserId(String createUserId) {
        this.createUserId = createUserId;
        return this;
    }

    public String getCreateUserName() {
        return createUserName;
    }

    public KnowledgeBaseConnectorDetail setCreateUserName(String createUserName) {
        this.createUserName = createUserName;
        return this;
    }

    public Long getCreateTime() {
        return createTime;
    }

    public KnowledgeBaseConnectorDetail setCreateTime(Long createTime) {
        this.createTime = createTime;
        return this;
    }

    public String getUpdateUserId() {
        return updateUserId;
    }

    public KnowledgeBaseConnectorDetail setUpdateUserId(String updateUserId) {
        this.updateUserId = updateUserId;
        return this;
    }

    public String getUpdateUserName() {
        return updateUserName;
    }

    public KnowledgeBaseConnectorDetail setUpdateUserName(String updateUserName) {
        this.updateUserName = updateUserName;
        return this;
    }

    public Long getUpdateTime() {
        return updateTime;
    }

    public KnowledgeBaseConnectorDetail setUpdateTime(Long updateTime) {
        this.updateTime = updateTime;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class KnowledgeBaseConnectorDetail {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    deployMode: ").append(toIndentedString(deployMode)).append("\n");
        sb.append("    helpText: ").append(toIndentedString(helpText)).append("\n");
        sb.append("    paramDefinition: ").append(toIndentedString(paramDefinition)).append("\n");
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
        KnowledgeBaseConnectorDetail knowledgeBaseConnectorDetail = (KnowledgeBaseConnectorDetail) o;
        return Objects.equals(this.id, knowledgeBaseConnectorDetail.id) && Objects.equals(this.name,
            knowledgeBaseConnectorDetail.name) && Objects.equals(this.icon, knowledgeBaseConnectorDetail.icon)
            && Objects.equals(this.description, knowledgeBaseConnectorDetail.description) && Objects.equals(
            this.deployMode, knowledgeBaseConnectorDetail.deployMode) && Objects.equals(this.helpText,
            knowledgeBaseConnectorDetail.helpText) && Objects.equals(this.paramDefinition,
            knowledgeBaseConnectorDetail.paramDefinition) && Objects.equals(this.workspaceId,
            knowledgeBaseConnectorDetail.workspaceId) && Objects.equals(this.domainName,
            knowledgeBaseConnectorDetail.domainName) && Objects.equals(this.createUserId,
            knowledgeBaseConnectorDetail.createUserId) && Objects.equals(this.createUserName,
            knowledgeBaseConnectorDetail.createUserName) && Objects.equals(this.createTime,
            knowledgeBaseConnectorDetail.createTime) && Objects.equals(this.updateUserId,
            knowledgeBaseConnectorDetail.updateUserId) && Objects.equals(this.updateUserName,
            knowledgeBaseConnectorDetail.updateUserName) && Objects.equals(this.updateTime,
            knowledgeBaseConnectorDetail.updateTime);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, icon, description, deployMode, helpText, paramDefinition, workspaceId, domainName,
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
}
