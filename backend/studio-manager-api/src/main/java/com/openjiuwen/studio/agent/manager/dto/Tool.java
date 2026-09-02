/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Date;
import java.util.Objects;

/**
 * 工具定义
 */
@ApiModel(description = "工具定义")

@Validated

public class Tool implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("tool_id")
    @Schema(description = "工具ID", example = "my-tool-001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(max = 84)
    private String toolId = null;

    @JsonProperty("project_id")
    @Schema(description = "项目ID", example = "my-project-001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(max = 64)
    private String projectId = null;

    @JsonProperty("tool_display_name")
    @Schema(description = "工具展示名称", example = "weather_tool")
    @Pattern(regexp = "^[a-zA-Z0-9_]+$")
    @Length(max = 64)
    private String toolDisplayName = null;

    @JsonProperty("tool_chinese_name")
    @Schema(description = "工具中文名称", example = "天气查询工具")
    @Length(min = 1, max = 64)
    private String toolChineseName = null;

    @JsonProperty("tool_desc")
    @Schema(description = "工具描述", example = "查询指定城市的天气信息")
    @Length(max = 256)
    private String toolDesc = null;

    @JsonProperty("icon")
    @Schema(description = "工具图标", example = "icon-weather")
    private String icon = null;

    @JsonProperty("visibility")
    @Schema(description = "可见性", example = "private")
    private String visibility = null;

    @JsonProperty("input_schema")
    @Schema(description = "输入参数Schema", example = "{\"type\":\"object\",\"properties\":{}}")
    @Length(max = 200000)
    private String inputSchema = null;

    @JsonProperty("is_input_list")
    @Schema(description = "输入是否为列表", example = "false")
    private Boolean isInputList = null;

    @JsonProperty("output_schema")
    @Schema(description = "输出参数Schema", example = "{\"type\":\"object\",\"properties\":{}}")
    @Length(max = 200000)
    private String outputSchema = null;

    @JsonProperty("is_output_list")
    @Schema(description = "输出是否为列表", example = "false")
    private Boolean isOutputList = null;

    @JsonProperty("intf_type")
    @Schema(description = "接口类型", example = "rest")
    private String intfType = null;

    @JsonProperty("type")
    @Schema(description = "工具类型", example = "custom")
    @Length(max = 32)
    private String type = null;

    @JsonProperty("score")
    @Schema(description = "评分", example = "0.95")
    private Float score = null;

    @JsonProperty("request_info")
    @Schema(description = "请求信息", example = "{}")
    @Valid
    private RequestInfo requestInfo = null;

    @JsonProperty("auth_info")
    @Schema(description = "认证信息", example = "{}")
    @Valid
    private AuthInfo authInfo = null;

    @JsonProperty("test_status")
    @Schema(description = "测试状态", example = "success")
    private String testStatus = null;

    @JsonProperty("last_version_id")
    @Schema(description = "最新版本ID", example = "v1-0-0")
    private String lastVersionId = null;

    @JsonProperty("metadata")
    @Schema(description = "元数据", example = "{\"key\":\"value\"}")
    @Length(max = 4096)
    private String metadata = null;

    @JsonProperty("creator")
    @Schema(description = "创建者", example = "admin")
    private String creator = null;

    @JsonProperty("creator_id")
    @Schema(description = "创建者ID", example = "user-001")
    private String creatorId = null;

    @JsonProperty("credentials")
    @Schema(description = "凭证信息", example = "{}")
    @Valid
    private ToolCredential credentials = null;

    @JsonProperty("credential_status")
    @Schema(description = "凭证状态", example = "valid")
    @Length(max = 32)
    private String credentialStatus = null;

    @JsonProperty("customize_node")
    @Schema(description = "是否自定义节点", example = "false")
    private Boolean customizeNode = null;

    @JsonProperty("create_time")
    @Schema(description = "创建时间", example = "2024-01-01T00:00:00.000Z")
    private Date createTime = null;

    @JsonProperty("update_time")
    @Schema(description = "更新时间", example = "2024-01-01T00:00:00.000Z")
    private Date updateTime = null;

    @JsonProperty("auth_required")
    @Schema(description = "是否需要认证", example = "false")
    private Boolean authRequired = false;

    public String getToolId() {
        return toolId;
    }

    public Tool setToolId(String toolId) {
        this.toolId = toolId;
        return this;
    }

    public String getProjectId() {
        return projectId;
    }

    public Tool setProjectId(String projectId) {
        this.projectId = projectId;
        return this;
    }

    public String getToolDisplayName() {
        return toolDisplayName;
    }

    public Tool setToolDisplayName(String toolDisplayName) {
        this.toolDisplayName = toolDisplayName;
        return this;
    }

    public String getToolChineseName() {
        return toolChineseName;
    }

    public Tool setToolChineseName(String toolChineseName) {
        this.toolChineseName = toolChineseName;
        return this;
    }

    public String getToolDesc() {
        return toolDesc;
    }

    public Tool setToolDesc(String toolDesc) {
        this.toolDesc = toolDesc;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public Tool setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public String getVisibility() {
        return visibility;
    }

    public Tool setVisibility(String visibility) {
        this.visibility = visibility;
        return this;
    }

    public String getInputSchema() {
        return inputSchema;
    }

    public Tool setInputSchema(String inputSchema) {
        this.inputSchema = inputSchema;
        return this;
    }

    public Tool setIsInputList(Boolean isInputList) {
        this.isInputList = isInputList;
        return this;
    }

    public Boolean isIsInputList() {
        return isInputList;
    }

    public String getOutputSchema() {
        return outputSchema;
    }

    public Tool setOutputSchema(String outputSchema) {
        this.outputSchema = outputSchema;
        return this;
    }

    public Tool setIsOutputList(Boolean isOutputList) {
        this.isOutputList = isOutputList;
        return this;
    }

    public Boolean isIsOutputList() {
        return isOutputList;
    }

    public String getIntfType() {
        return intfType;
    }

    public Tool setIntfType(String intfType) {
        this.intfType = intfType;
        return this;
    }

    public String getType() {
        return type;
    }

    public Tool setType(String type) {
        this.type = type;
        return this;
    }

    public Float getScore() {
        return score;
    }

    public Tool setScore(Float score) {
        this.score = score;
        return this;
    }

    public RequestInfo getRequestInfo() {
        return requestInfo;
    }

    public Tool setRequestInfo(RequestInfo requestInfo) {
        this.requestInfo = requestInfo;
        return this;
    }

    public AuthInfo getAuthInfo() {
        return authInfo;
    }

    public Tool setAuthInfo(AuthInfo authInfo) {
        this.authInfo = authInfo;
        return this;
    }

    public String getTestStatus() {
        return testStatus;
    }

    public Tool setTestStatus(String testStatus) {
        this.testStatus = testStatus;
        return this;
    }

    public String getLastVersionId() {
        return lastVersionId;
    }

    public Tool setLastVersionId(String lastVersionId) {
        this.lastVersionId = lastVersionId;
        return this;
    }

    public String getMetadata() {
        return metadata;
    }

    public Tool setMetadata(String metadata) {
        this.metadata = metadata;
        return this;
    }

    public String getCreator() {
        return creator;
    }

    public Tool setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public String getCreatorId() {
        return creatorId;
    }

    public Tool setCreatorId(String creatorId) {
        this.creatorId = creatorId;
        return this;
    }

    public ToolCredential getCredentials() {
        return credentials;
    }

    public Tool setCredentials(ToolCredential credentials) {
        this.credentials = credentials;
        return this;
    }

    public String getCredentialStatus() {
        return credentialStatus;
    }

    public Tool setCredentialStatus(String credentialStatus) {
        this.credentialStatus = credentialStatus;
        return this;
    }

    public Tool setCustomizeNode(Boolean customizeNode) {
        this.customizeNode = customizeNode;
        return this;
    }

    public Boolean isCustomizeNode() {
        return customizeNode;
    }

    public Date getCreateTime() {
        return createTime;
    }

    public Tool setCreateTime(Date createTime) {
        this.createTime = createTime;
        return this;
    }

    public Date getUpdateTime() {
        return updateTime;
    }

    public Tool setUpdateTime(Date updateTime) {
        this.updateTime = updateTime;
        return this;
    }

    public Tool setAuthRequired(Boolean authRequired) {
        this.authRequired = authRequired;
        return this;
    }

    public Boolean isAuthRequired() {
        return authRequired;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class Tool {\n");

        sb.append("    toolId: ").append(toIndentedString(toolId)).append("\n");
        sb.append("    projectId: ").append(toIndentedString(projectId)).append("\n");
        sb.append("    toolDisplayName: ").append(toIndentedString(toolDisplayName)).append("\n");
        sb.append("    toolChineseName: ").append(toIndentedString(toolChineseName)).append("\n");
        sb.append("    toolDesc: ").append(toIndentedString(toolDesc)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    visibility: ").append(toIndentedString(visibility)).append("\n");
        sb.append("    inputSchema: ").append(toIndentedString(inputSchema)).append("\n");
        sb.append("    isInputList: ").append(toIndentedString(isInputList)).append("\n");
        sb.append("    outputSchema: ").append(toIndentedString(outputSchema)).append("\n");
        sb.append("    isOutputList: ").append(toIndentedString(isOutputList)).append("\n");
        sb.append("    intfType: ").append(toIndentedString(intfType)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    score: ").append(toIndentedString(score)).append("\n");
        sb.append("    requestInfo: ").append(toIndentedString(requestInfo)).append("\n");
        sb.append("    authInfo: ").append(toIndentedString(authInfo)).append("\n");
        sb.append("    testStatus: ").append(toIndentedString(testStatus)).append("\n");
        sb.append("    lastVersionId: ").append(toIndentedString(lastVersionId)).append("\n");
        sb.append("    metadata: ").append(toIndentedString(metadata)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    creatorId: ").append(toIndentedString(creatorId)).append("\n");
        sb.append("    credentials: ").append(toIndentedString(credentials)).append("\n");
        sb.append("    credentialStatus: ").append(toIndentedString(credentialStatus)).append("\n");
        sb.append("    customizeNode: ").append(toIndentedString(customizeNode)).append("\n");
        sb.append("    createTime: ").append(toIndentedString(createTime)).append("\n");
        sb.append("    updateTime: ").append(toIndentedString(updateTime)).append("\n");
        sb.append("    authRequired: ").append(toIndentedString(authRequired)).append("\n");
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
        Tool tool = (Tool) o;
        return Objects.equals(this.toolId, tool.toolId) && Objects.equals(this.projectId, tool.projectId)
            && Objects.equals(this.toolDisplayName, tool.toolDisplayName) && Objects.equals(this.toolChineseName,
            tool.toolChineseName) && Objects.equals(this.toolDesc, tool.toolDesc) && Objects.equals(this.icon,
            tool.icon) && Objects.equals(this.visibility, tool.visibility) && Objects.equals(this.inputSchema,
            tool.inputSchema) && Objects.equals(this.isInputList, tool.isInputList) && Objects.equals(this.outputSchema,
            tool.outputSchema) && Objects.equals(this.isOutputList, tool.isOutputList) && Objects.equals(this.intfType,
            tool.intfType) && Objects.equals(this.type, tool.type) && Objects.equals(this.score, tool.score)
            && Objects.equals(this.requestInfo, tool.requestInfo) && Objects.equals(this.authInfo, tool.authInfo)
            && Objects.equals(this.testStatus, tool.testStatus) && Objects.equals(this.lastVersionId,
            tool.lastVersionId) && Objects.equals(this.metadata, tool.metadata) && Objects.equals(this.creator,
            tool.creator) && Objects.equals(this.creatorId, tool.creatorId) && Objects.equals(this.credentials,
            tool.credentials) && Objects.equals(this.credentialStatus, tool.credentialStatus) && Objects.equals(
            this.customizeNode, tool.customizeNode) && Objects.equals(this.createTime, tool.createTime)
            && Objects.equals(this.updateTime, tool.updateTime) && Objects.equals(this.authRequired, tool.authRequired);
    }

    @Override
    public int hashCode() {
        return Objects.hash(toolId, projectId, toolDisplayName, toolChineseName, toolDesc, icon, visibility,
            inputSchema, isInputList, outputSchema, isOutputList, intfType, type, score, requestInfo, authInfo,
            testStatus, lastVersionId, metadata, creator, creatorId, credentials, credentialStatus, customizeNode,
            createTime, updateTime, authRequired);
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
