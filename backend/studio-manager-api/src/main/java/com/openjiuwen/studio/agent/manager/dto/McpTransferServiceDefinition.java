/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

/**
 * FEAT-134 MCP 服务迁移定义（文件内单个服务条目，白名单字段）。
 *
 * org_type 文件统一大写（SSE / STREAMABLE_HTTP / NPX / UVX）；
 * deploy_type 小写（sse / streamable_http / stdio），导入时交叉校验。
 * 不携带源 service ID、traceId、uniqueCode、租户身份、托管 URL、FG/APIG 标识。
 */
public class McpTransferServiceDefinition {

    @JsonProperty("name")
    private String name;

    @JsonProperty("name_en")
    private String nameEn;

    @JsonProperty("description")
    private String description;

    @JsonProperty("description_en")
    private String descriptionEn;

    @JsonProperty("org_type")
    private String orgType;

    @JsonProperty("deploy_type")
    private String deployType;

    @JsonProperty("url")
    private String url;

    @JsonProperty("server_config")
    private Map<String, Object> serverConfig;

    @JsonProperty("tools_snapshot")
    private List<Map<String, Object>> toolsSnapshot;

    @JsonProperty("requires_auth_configuration")
    private Boolean requiresAuthConfiguration;

    @JsonProperty("redacted_fields")
    private List<String> redactedFields;

    public String getName() {
        return name;
    }

    public McpTransferServiceDefinition setName(String name) {
        this.name = name;
        return this;
    }

    public String getNameEn() {
        return nameEn;
    }

    public McpTransferServiceDefinition setNameEn(String nameEn) {
        this.nameEn = nameEn;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public McpTransferServiceDefinition setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getDescriptionEn() {
        return descriptionEn;
    }

    public McpTransferServiceDefinition setDescriptionEn(String descriptionEn) {
        this.descriptionEn = descriptionEn;
        return this;
    }

    public String getOrgType() {
        return orgType;
    }

    public McpTransferServiceDefinition setOrgType(String orgType) {
        this.orgType = orgType;
        return this;
    }

    public String getDeployType() {
        return deployType;
    }

    public McpTransferServiceDefinition setDeployType(String deployType) {
        this.deployType = deployType;
        return this;
    }

    public String getUrl() {
        return url;
    }

    public McpTransferServiceDefinition setUrl(String url) {
        this.url = url;
        return this;
    }

    public Map<String, Object> getServerConfig() {
        return serverConfig;
    }

    public McpTransferServiceDefinition setServerConfig(Map<String, Object> serverConfig) {
        this.serverConfig = serverConfig;
        return this;
    }

    public List<Map<String, Object>> getToolsSnapshot() {
        return toolsSnapshot;
    }

    public McpTransferServiceDefinition setToolsSnapshot(List<Map<String, Object>> toolsSnapshot) {
        this.toolsSnapshot = toolsSnapshot;
        return this;
    }

    public Boolean getRequiresAuthConfiguration() {
        return requiresAuthConfiguration;
    }

    public McpTransferServiceDefinition setRequiresAuthConfiguration(Boolean requiresAuthConfiguration) {
        this.requiresAuthConfiguration = requiresAuthConfiguration;
        return this;
    }

    public List<String> getRedactedFields() {
        return redactedFields;
    }

    public McpTransferServiceDefinition setRedactedFields(List<String> redactedFields) {
        this.redactedFields = redactedFields;
        return this;
    }
}
