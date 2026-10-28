/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import java.io.Serializable;
import java.util.Objects;

/**
 * MCP 工具引用方信息
 */
@Schema(description = "MCP 工具引用方信息")
public class McpToolReferenceItem implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("app_id")
    @Schema(description = "引用方ID（智能体/工作流）", example = "agent-001")
    private String appId = null;

    @JsonProperty("app_name")
    @Schema(description = "引用方名称", example = "天气助手")
    private String appName = null;

    @JsonProperty("app_type")
    @Schema(description = "引用方类型", example = "agent")
    private String appType = null;

    public String getAppId() {
        return appId;
    }

    public McpToolReferenceItem setAppId(String appId) {
        this.appId = appId;
        return this;
    }

    public String getAppName() {
        return appName;
    }

    public McpToolReferenceItem setAppName(String appName) {
        this.appName = appName;
        return this;
    }

    public String getAppType() {
        return appType;
    }

    public McpToolReferenceItem setAppType(String appType) {
        this.appType = appType;
        return this;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (o == null || getClass() != o.getClass()) {
            return false;
        }
        McpToolReferenceItem that = (McpToolReferenceItem) o;
        return Objects.equals(appId, that.appId) && Objects.equals(appName, that.appName)
            && Objects.equals(appType, that.appType);
    }

    @Override
    public int hashCode() {
        return Objects.hash(appId, appName, appType);
    }

    @Override
    public String toString() {
        return "McpToolReferenceItem{" + "appId='" + appId + '\'' + ", appName='" + appName + '\''
            + ", appType='" + appType + '\'' + '}';
    }
}
