/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * mcp 服务信息
 */
@ApiModel(description = "mcp 服务信息")

@Validated

public class McpServiceDetailInfoDto implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "服务ID", example = "550e8400-e29b-41d4-a716-446655440000")
    @Length(max = 64)
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "服务名称", example = "my-mcp-service")
    private String name = null;

    @JsonProperty("name_en")
    @Schema(description = "服务英文名称", example = "my-mcp-service")
    private String nameEn = null;

    @JsonProperty("description")
    @Schema(description = "服务描述", example = "这是一个MCP服务")
    private String description = null;

    @JsonProperty("description_en")
    @Schema(description = "服务英文描述", example = "This is an MCP service")
    private String descriptionEn = null;

    @JsonProperty("readme")
    @Schema(description = "服务说明文档", example = "服务使用说明")
    private String readme = null;

    @JsonProperty("org_type")
    @Schema(description = "组织类型", example = "enterprise")
    private String orgType = null;

    @JsonProperty("deploy_type")
    @Schema(description = "部署类型", example = "function")
    private String deployType = null;

    @JsonProperty("server_config")
    @Schema(description = "服务端配置", example = "{}")
    private String serverConfig = null;

    @JsonProperty("tools")
    @Schema(description = "工具列表", example = "[]")
    private String tools = null;

    @JsonProperty("fc_instance_url")
    @Schema(description = "函数计算实例URL", example = "https://fc.example.com/instance")
    private String fcInstanceUrl = null;

    @JsonProperty("fc_region")
    @Schema(description = "函数计算区域", example = "cn-north-4")
    private String fcRegion = null;

    @JsonProperty("fc_instance_id")
    @Schema(description = "函数计算实例ID", example = "instance-001")
    private String fcInstanceId = null;

    @JsonProperty("fc_instance_status")
    @Schema(description = "函数计算实例状态", example = "running")
    private String fcInstanceStatus = null;

    @JsonProperty("fail_reason_detail")
    @Schema(description = "失败原因详情", example = "{}")
    @Valid
    private McpFailReasonDetailDto failReasonDetail = null;

    @JsonProperty("apig_group_id")
    @Schema(description = "API网关分组ID", example = "group-001")
    private String apigGroupId = null;

    @JsonProperty("apig_instance_id")
    @Schema(description = "API网关实例ID", example = "instance-001")
    private String apigInstanceId = null;

    @JsonProperty("agency_name")
    @Schema(description = "委托名称", example = "agency-001")
    private String agencyName = null;

    @JsonProperty("enterprise_project_id")
    @Schema(description = "企业项目ID", example = "project-001")
    private String enterpriseProjectId = null;

    @JsonProperty("function_application_name")
    @Schema(description = "函数应用名称", example = "my-function-app")
    private String functionApplicationName = null;

    @JsonProperty("icon")
    @Schema(description = "图标", example = "icon-url")
    private String icon = null;

    @JsonProperty("created_date")
    @Schema(description = "创建时间", example = "1714521600000")
    private Long createdDate = null;

    @JsonProperty("last_updated_date")
    @Schema(description = "最后更新时间", example = "1714521600000")
    private Long lastUpdatedDate = null;

    @JsonProperty("type")
    @Schema(description = "服务类型", example = "mcp")
    private String type = null;

    @JsonProperty("visibility")
    @Schema(description = "可见性", example = "public")
    private String visibility = null;

    @JsonProperty("auth_type")
    @Schema(description = "认证类型", example = "none")
    private String authType = null;

    @JsonProperty("mcp_servers")
    @Schema(description = "MCP服务运行时信息", example = "{}")
    @Valid
    private McpServerRuntimeVo mcpServers = null;

    @JsonProperty("third_resource")
    @Schema(description = "第三方资源标识", example = "third-resource-001")
    private String thirdResource = null;

    @JsonProperty("third_id")
    @Schema(description = "第三方ID", example = "third-001")
    private String thirdId = null;

    @JsonProperty("third_version_id")
    @Schema(description = "第三方版本ID", example = "version-001")
    private String thirdVersionId = null;

    @JsonProperty("auth_info")
    @Schema(description = "认证信息", example = "{}")
    @Valid
    private AuthInfo authInfo = null;

    public String getId() {
        return id;
    }

    public McpServiceDetailInfoDto setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public McpServiceDetailInfoDto setName(String name) {
        this.name = name;
        return this;
    }

    public String getNameEn() {
        return nameEn;
    }

    public McpServiceDetailInfoDto setNameEn(String nameEn) {
        this.nameEn = nameEn;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public McpServiceDetailInfoDto setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getDescriptionEn() {
        return descriptionEn;
    }

    public McpServiceDetailInfoDto setDescriptionEn(String descriptionEn) {
        this.descriptionEn = descriptionEn;
        return this;
    }

    public String getReadme() {
        return readme;
    }

    public McpServiceDetailInfoDto setReadme(String readme) {
        this.readme = readme;
        return this;
    }

    public String getOrgType() {
        return orgType;
    }

    public McpServiceDetailInfoDto setOrgType(String orgType) {
        this.orgType = orgType;
        return this;
    }

    public String getDeployType() {
        return deployType;
    }

    public McpServiceDetailInfoDto setDeployType(String deployType) {
        this.deployType = deployType;
        return this;
    }

    public String getServerConfig() {
        return serverConfig;
    }

    public McpServiceDetailInfoDto setServerConfig(String serverConfig) {
        this.serverConfig = serverConfig;
        return this;
    }

    public String getTools() {
        return tools;
    }

    public McpServiceDetailInfoDto setTools(String tools) {
        this.tools = tools;
        return this;
    }

    public String getFcInstanceUrl() {
        return fcInstanceUrl;
    }

    public McpServiceDetailInfoDto setFcInstanceUrl(String fcInstanceUrl) {
        this.fcInstanceUrl = fcInstanceUrl;
        return this;
    }

    public String getFcRegion() {
        return fcRegion;
    }

    public McpServiceDetailInfoDto setFcRegion(String fcRegion) {
        this.fcRegion = fcRegion;
        return this;
    }

    public String getFcInstanceId() {
        return fcInstanceId;
    }

    public McpServiceDetailInfoDto setFcInstanceId(String fcInstanceId) {
        this.fcInstanceId = fcInstanceId;
        return this;
    }

    public String getFcInstanceStatus() {
        return fcInstanceStatus;
    }

    public McpServiceDetailInfoDto setFcInstanceStatus(String fcInstanceStatus) {
        this.fcInstanceStatus = fcInstanceStatus;
        return this;
    }

    public McpFailReasonDetailDto getFailReasonDetail() {
        return failReasonDetail;
    }

    public McpServiceDetailInfoDto setFailReasonDetail(McpFailReasonDetailDto failReasonDetail) {
        this.failReasonDetail = failReasonDetail;
        return this;
    }

    public String getApigGroupId() {
        return apigGroupId;
    }

    public McpServiceDetailInfoDto setApigGroupId(String apigGroupId) {
        this.apigGroupId = apigGroupId;
        return this;
    }

    public String getApigInstanceId() {
        return apigInstanceId;
    }

    public McpServiceDetailInfoDto setApigInstanceId(String apigInstanceId) {
        this.apigInstanceId = apigInstanceId;
        return this;
    }

    public String getAgencyName() {
        return agencyName;
    }

    public McpServiceDetailInfoDto setAgencyName(String agencyName) {
        this.agencyName = agencyName;
        return this;
    }

    public String getEnterpriseProjectId() {
        return enterpriseProjectId;
    }

    public McpServiceDetailInfoDto setEnterpriseProjectId(String enterpriseProjectId) {
        this.enterpriseProjectId = enterpriseProjectId;
        return this;
    }

    public String getFunctionApplicationName() {
        return functionApplicationName;
    }

    public McpServiceDetailInfoDto setFunctionApplicationName(String functionApplicationName) {
        this.functionApplicationName = functionApplicationName;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public McpServiceDetailInfoDto setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public Long getCreatedDate() {
        return createdDate;
    }

    public McpServiceDetailInfoDto setCreatedDate(Long createdDate) {
        this.createdDate = createdDate;
        return this;
    }

    public Long getLastUpdatedDate() {
        return lastUpdatedDate;
    }

    public McpServiceDetailInfoDto setLastUpdatedDate(Long lastUpdatedDate) {
        this.lastUpdatedDate = lastUpdatedDate;
        return this;
    }

    public String getType() {
        return type;
    }

    public McpServiceDetailInfoDto setType(String type) {
        this.type = type;
        return this;
    }

    public String getVisibility() {
        return visibility;
    }

    public McpServiceDetailInfoDto setVisibility(String visibility) {
        this.visibility = visibility;
        return this;
    }

    public String getAuthType() {
        return authType;
    }

    public McpServiceDetailInfoDto setAuthType(String authType) {
        this.authType = authType;
        return this;
    }

    public McpServerRuntimeVo getMcpServers() {
        return mcpServers;
    }

    public McpServiceDetailInfoDto setMcpServers(McpServerRuntimeVo mcpServers) {
        this.mcpServers = mcpServers;
        return this;
    }

    public String getThirdResource() {
        return thirdResource;
    }

    public McpServiceDetailInfoDto setThirdResource(String thirdResource) {
        this.thirdResource = thirdResource;
        return this;
    }

    public String getThirdId() {
        return thirdId;
    }

    public McpServiceDetailInfoDto setThirdId(String thirdId) {
        this.thirdId = thirdId;
        return this;
    }

    public String getThirdVersionId() {
        return thirdVersionId;
    }

    public McpServiceDetailInfoDto setThirdVersionId(String thirdVersionId) {
        this.thirdVersionId = thirdVersionId;
        return this;
    }

    public AuthInfo getAuthInfo() {
        return authInfo;
    }

    public McpServiceDetailInfoDto setAuthInfo(AuthInfo authInfo) {
        this.authInfo = authInfo;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpServiceDetailInfoDto {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    nameEn: ").append(toIndentedString(nameEn)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    descriptionEn: ").append(toIndentedString(descriptionEn)).append("\n");
        sb.append("    readme: ").append(toIndentedString(readme)).append("\n");
        sb.append("    orgType: ").append(toIndentedString(orgType)).append("\n");
        sb.append("    deployType: ").append(toIndentedString(deployType)).append("\n");
        sb.append("    serverConfig: ").append(toIndentedString(serverConfig)).append("\n");
        sb.append("    tools: ").append(toIndentedString(tools)).append("\n");
        sb.append("    fcInstanceUrl: ").append(toIndentedString(fcInstanceUrl)).append("\n");
        sb.append("    fcRegion: ").append(toIndentedString(fcRegion)).append("\n");
        sb.append("    fcInstanceId: ").append(toIndentedString(fcInstanceId)).append("\n");
        sb.append("    fcInstanceStatus: ").append(toIndentedString(fcInstanceStatus)).append("\n");
        sb.append("    failReasonDetail: ").append(toIndentedString(failReasonDetail)).append("\n");
        sb.append("    apigGroupId: ").append(toIndentedString(apigGroupId)).append("\n");
        sb.append("    apigInstanceId: ").append(toIndentedString(apigInstanceId)).append("\n");
        sb.append("    agencyName: ").append(toIndentedString(agencyName)).append("\n");
        sb.append("    enterpriseProjectId: ").append(toIndentedString(enterpriseProjectId)).append("\n");
        sb.append("    functionApplicationName: ").append(toIndentedString(functionApplicationName)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    createdDate: ").append(toIndentedString(createdDate)).append("\n");
        sb.append("    lastUpdatedDate: ").append(toIndentedString(lastUpdatedDate)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    visibility: ").append(toIndentedString(visibility)).append("\n");
        sb.append("    authType: ").append(toIndentedString(authType)).append("\n");
        sb.append("    mcpServers: ").append(toIndentedString(mcpServers)).append("\n");
        sb.append("    thirdResource: ").append(toIndentedString(thirdResource)).append("\n");
        sb.append("    thirdId: ").append(toIndentedString(thirdId)).append("\n");
        sb.append("    thirdVersionId: ").append(toIndentedString(thirdVersionId)).append("\n");
        sb.append("    authInfo: ").append(toIndentedString(authInfo)).append("\n");
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
        McpServiceDetailInfoDto mcpServiceDetailInfoDto = (McpServiceDetailInfoDto) o;
        return Objects.equals(this.id, mcpServiceDetailInfoDto.id) && Objects.equals(this.name,
            mcpServiceDetailInfoDto.name) && Objects.equals(this.nameEn, mcpServiceDetailInfoDto.nameEn)
            && Objects.equals(this.description, mcpServiceDetailInfoDto.description) && Objects.equals(
            this.descriptionEn, mcpServiceDetailInfoDto.descriptionEn) && Objects.equals(this.readme,
            mcpServiceDetailInfoDto.readme) && Objects.equals(this.orgType, mcpServiceDetailInfoDto.orgType)
            && Objects.equals(this.deployType, mcpServiceDetailInfoDto.deployType) && Objects.equals(this.serverConfig,
            mcpServiceDetailInfoDto.serverConfig) && Objects.equals(this.tools, mcpServiceDetailInfoDto.tools)
            && Objects.equals(this.fcInstanceUrl, mcpServiceDetailInfoDto.fcInstanceUrl) && Objects.equals(
            this.fcRegion, mcpServiceDetailInfoDto.fcRegion) && Objects.equals(this.fcInstanceId,
            mcpServiceDetailInfoDto.fcInstanceId) && Objects.equals(this.fcInstanceStatus,
            mcpServiceDetailInfoDto.fcInstanceStatus) && Objects.equals(this.failReasonDetail,
            mcpServiceDetailInfoDto.failReasonDetail) && Objects.equals(this.apigGroupId,
            mcpServiceDetailInfoDto.apigGroupId) && Objects.equals(this.apigInstanceId,
            mcpServiceDetailInfoDto.apigInstanceId) && Objects.equals(this.agencyName,
            mcpServiceDetailInfoDto.agencyName) && Objects.equals(this.enterpriseProjectId,
            mcpServiceDetailInfoDto.enterpriseProjectId) && Objects.equals(this.functionApplicationName,
            mcpServiceDetailInfoDto.functionApplicationName) && Objects.equals(this.icon, mcpServiceDetailInfoDto.icon)
            && Objects.equals(this.createdDate, mcpServiceDetailInfoDto.createdDate) && Objects.equals(
            this.lastUpdatedDate, mcpServiceDetailInfoDto.lastUpdatedDate) && Objects.equals(this.type,
            mcpServiceDetailInfoDto.type) && Objects.equals(this.visibility, mcpServiceDetailInfoDto.visibility)
            && Objects.equals(this.authType, mcpServiceDetailInfoDto.authType) && Objects.equals(this.mcpServers,
            mcpServiceDetailInfoDto.mcpServers) && Objects.equals(this.thirdResource,
            mcpServiceDetailInfoDto.thirdResource) && Objects.equals(this.thirdId, mcpServiceDetailInfoDto.thirdId)
            && Objects.equals(this.thirdVersionId, mcpServiceDetailInfoDto.thirdVersionId) && Objects.equals(
            this.authInfo, mcpServiceDetailInfoDto.authInfo);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, nameEn, description, descriptionEn, readme, orgType, deployType, serverConfig,
            tools, fcInstanceUrl, fcRegion, fcInstanceId, fcInstanceStatus, failReasonDetail, apigGroupId,
            apigInstanceId, agencyName, enterpriseProjectId, functionApplicationName, icon, createdDate,
            lastUpdatedDate, type, visibility, authType, mcpServers, thirdResource, thirdId, thirdVersionId, authInfo);
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
