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
import java.util.Objects;

/**
 * 修改工具请求体
 */
@ApiModel(description = "修改工具请求体")

@Validated

public class ModifyPluginReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("tool_display_name")
    @Schema(description = "工具展示名称", example = "my_tool")
    @Pattern(regexp = "^[a-zA-Z0-9_]{2,64}$")
    private String toolDisplayName = null;

    @JsonProperty("tool_chinese_name")
    @Schema(description = "工具中文名称", example = "我的工具")
    @Length(min = 1, max = 64)
    private String toolChineseName = null;

    @JsonProperty("tool_desc")
    @Schema(description = "工具描述", example = "这是一个示例工具")
    @Length(max = 600)
    private String toolDesc = null;

    @JsonProperty("icon")
    @Schema(description = "工具图标", example = "icon-url")
    private String icon = null;

    @JsonProperty("request_info")
    @Schema(description = "请求信息", example = "{}")
    @Valid
    private RequestInfo requestInfo = null;

    @JsonProperty("auth_info")
    @Schema(description = "认证信息", example = "{}")
    @Valid
    private AuthInfo authInfo = null;

    @JsonProperty("test_status")
    @Schema(description = "测试状态", example = "SUCCESS")
    private String testStatus = null;

    @JsonProperty("customize_node")
    @Schema(description = "是否自定义节点", example = "false")
    private Boolean customizeNode = null;

    @JsonProperty("call_mode")
    @Schema(description = "调用模式", example = "SYNC")
    private String callMode = null;

    @JsonProperty("metadata")
    @Schema(description = "元数据", example = "{}")
    private String metadata = null;

    @JsonProperty("auth_required")
    @Schema(description = "是否需要认证", example = "false")
    private Boolean authRequired = false;

    public String getToolDisplayName() {
        return toolDisplayName;
    }

    public ModifyPluginReq setToolDisplayName(String toolDisplayName) {
        this.toolDisplayName = toolDisplayName;
        return this;
    }

    public String getToolChineseName() {
        return toolChineseName;
    }

    public ModifyPluginReq setToolChineseName(String toolChineseName) {
        this.toolChineseName = toolChineseName;
        return this;
    }

    public String getToolDesc() {
        return toolDesc;
    }

    public ModifyPluginReq setToolDesc(String toolDesc) {
        this.toolDesc = toolDesc;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public ModifyPluginReq setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public RequestInfo getRequestInfo() {
        return requestInfo;
    }

    public ModifyPluginReq setRequestInfo(RequestInfo requestInfo) {
        this.requestInfo = requestInfo;
        return this;
    }

    public AuthInfo getAuthInfo() {
        return authInfo;
    }

    public ModifyPluginReq setAuthInfo(AuthInfo authInfo) {
        this.authInfo = authInfo;
        return this;
    }

    public String getTestStatus() {
        return testStatus;
    }

    public ModifyPluginReq setTestStatus(String testStatus) {
        this.testStatus = testStatus;
        return this;
    }

    public ModifyPluginReq setCustomizeNode(Boolean customizeNode) {
        this.customizeNode = customizeNode;
        return this;
    }

    public Boolean isCustomizeNode() {
        return customizeNode;
    }

    public String getCallMode() {
        return callMode;
    }

    public ModifyPluginReq setCallMode(String callMode) {
        this.callMode = callMode;
        return this;
    }

    public String getMetadata() {
        return metadata;
    }

    public ModifyPluginReq setMetadata(String metadata) {
        this.metadata = metadata;
        return this;
    }

    public ModifyPluginReq setAuthRequired(Boolean authRequired) {
        this.authRequired = authRequired;
        return this;
    }

    public Boolean isAuthRequired() {
        return authRequired;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ModifyPluginReq {\n");

        sb.append("    toolDisplayName: ").append(toIndentedString(toolDisplayName)).append("\n");
        sb.append("    toolChineseName: ").append(toIndentedString(toolChineseName)).append("\n");
        sb.append("    toolDesc: ").append(toIndentedString(toolDesc)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    requestInfo: ").append(toIndentedString(requestInfo)).append("\n");
        sb.append("    authInfo: ").append(toIndentedString(authInfo)).append("\n");
        sb.append("    testStatus: ").append(toIndentedString(testStatus)).append("\n");
        sb.append("    customizeNode: ").append(toIndentedString(customizeNode)).append("\n");
        sb.append("    callMode: ").append(toIndentedString(callMode)).append("\n");
        sb.append("    metadata: ").append(toIndentedString(metadata)).append("\n");
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
        ModifyPluginReq modifyPluginReq = (ModifyPluginReq) o;
        return Objects.equals(this.toolDisplayName, modifyPluginReq.toolDisplayName) && Objects.equals(
            this.toolChineseName, modifyPluginReq.toolChineseName) && Objects.equals(this.toolDesc,
            modifyPluginReq.toolDesc) && Objects.equals(this.icon, modifyPluginReq.icon) && Objects.equals(
            this.requestInfo, modifyPluginReq.requestInfo) && Objects.equals(this.authInfo, modifyPluginReq.authInfo)
            && Objects.equals(this.testStatus, modifyPluginReq.testStatus) && Objects.equals(this.customizeNode,
            modifyPluginReq.customizeNode) && Objects.equals(this.callMode, modifyPluginReq.callMode) && Objects.equals(
            this.metadata, modifyPluginReq.metadata) && Objects.equals(this.authRequired, modifyPluginReq.authRequired);
    }

    @Override
    public int hashCode() {
        return Objects.hash(toolDisplayName, toolChineseName, toolDesc, icon, requestInfo, authInfo, testStatus,
            customizeNode, callMode, metadata, authRequired);
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
