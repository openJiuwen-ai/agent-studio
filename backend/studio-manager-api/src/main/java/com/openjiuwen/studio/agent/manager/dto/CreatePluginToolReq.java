/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 创建工具请求体
 */
@ApiModel(description = "创建工具请求体")

@Validated

public class CreatePluginToolReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("plugin_id")
    @Schema(description = "插件ID", example = "my-plugin-001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(max = 64)
    private String pluginId = null;

    @JsonProperty("tool_display_name")
    @Schema(description = "工具显示名称", example = "weather_tool")
    @Pattern(regexp = "^[a-zA-Z0-9_]{2,64}$")
    private String toolDisplayName = null;

    @JsonProperty("tool_chinese_name")
    @Schema(description = "工具中文名称", example = "天气查询工具", required = true)
    @NotBlank
    @Length(min = 1, max = 64)
    private String toolChineseName = null;

    @JsonProperty("tool_desc")
    @Schema(description = "工具描述", example = "查询指定城市的天气信息")
    @Length(min = 1, max = 600)
    private String toolDesc = null;

    @JsonProperty("call_mode")
    @Schema(description = "调用模式", example = "sync")
    private String callMode = null;

    @JsonProperty("icon")
    @Schema(description = "图标", example = "icon-weather")
    private String icon = null;

    @JsonProperty("request_info")
    @Schema(description = "请求信息", example = "请求配置信息")
    @Valid
    private RequestInfo requestInfo = null;

    @JsonProperty("auth_info")
    @Schema(description = "认证信息", example = "认证配置信息")
    @Valid
    private AuthInfo authInfo = null;

    @JsonProperty("visibility")
    @Schema(description = "可见性", example = "private")
    @Length(max = 32)
    private String visibility = null;

    @JsonProperty("intf_type")
    @Schema(description = "接口类型", example = "REST")
    private String intfType = null;

    @JsonProperty("input_schema")
    @Schema(description = "输入参数Schema", example = "输入参数JSON Schema")
    @Length(max = 200000)
    private String inputSchema = null;

    @JsonProperty("is_input_list")
    @Schema(description = "是否为输入列表", example = "false")
    private Boolean isInputList = false;

    @JsonProperty("output_schema")
    @Schema(description = "输出参数Schema", example = "输出参数JSON Schema")
    @Length(max = 200000)
    private String outputSchema = null;

    @JsonProperty("is_output_list")
    @Schema(description = "是否为输出列表", example = "false")
    private Boolean isOutputList = false;

    @JsonProperty("metadata")
    @Schema(description = "元数据", example = "元数据信息")
    @Length(max = 4096)
    private String metadata = null;

    @JsonProperty("auth_required")
    @Schema(description = "是否需要认证", example = "false")
    private Boolean authRequired = false;

    @JsonProperty("test_status")
    @Schema(description = "测试状态", example = "passed")
    private String testStatus = null;

    public String getPluginId() {
        return pluginId;
    }

    public CreatePluginToolReq setPluginId(String pluginId) {
        this.pluginId = pluginId;
        return this;
    }

    public String getToolDisplayName() {
        return toolDisplayName;
    }

    public CreatePluginToolReq setToolDisplayName(String toolDisplayName) {
        this.toolDisplayName = toolDisplayName;
        return this;
    }

    public String getToolChineseName() {
        return toolChineseName;
    }

    public CreatePluginToolReq setToolChineseName(String toolChineseName) {
        this.toolChineseName = toolChineseName;
        return this;
    }

    public String getToolDesc() {
        return toolDesc;
    }

    public CreatePluginToolReq setToolDesc(String toolDesc) {
        this.toolDesc = toolDesc;
        return this;
    }

    public String getCallMode() {
        return callMode;
    }

    public CreatePluginToolReq setCallMode(String callMode) {
        this.callMode = callMode;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public CreatePluginToolReq setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public RequestInfo getRequestInfo() {
        return requestInfo;
    }

    public CreatePluginToolReq setRequestInfo(RequestInfo requestInfo) {
        this.requestInfo = requestInfo;
        return this;
    }

    public AuthInfo getAuthInfo() {
        return authInfo;
    }

    public CreatePluginToolReq setAuthInfo(AuthInfo authInfo) {
        this.authInfo = authInfo;
        return this;
    }

    public String getVisibility() {
        return visibility;
    }

    public CreatePluginToolReq setVisibility(String visibility) {
        this.visibility = visibility;
        return this;
    }

    public String getIntfType() {
        return intfType;
    }

    public CreatePluginToolReq setIntfType(String intfType) {
        this.intfType = intfType;
        return this;
    }

    public String getInputSchema() {
        return inputSchema;
    }

    public CreatePluginToolReq setInputSchema(String inputSchema) {
        this.inputSchema = inputSchema;
        return this;
    }

    public CreatePluginToolReq setIsInputList(Boolean isInputList) {
        this.isInputList = isInputList;
        return this;
    }

    public Boolean isIsInputList() {
        return isInputList;
    }

    public String getOutputSchema() {
        return outputSchema;
    }

    public CreatePluginToolReq setOutputSchema(String outputSchema) {
        this.outputSchema = outputSchema;
        return this;
    }

    public CreatePluginToolReq setIsOutputList(Boolean isOutputList) {
        this.isOutputList = isOutputList;
        return this;
    }

    public Boolean isIsOutputList() {
        return isOutputList;
    }

    public String getMetadata() {
        return metadata;
    }

    public CreatePluginToolReq setMetadata(String metadata) {
        this.metadata = metadata;
        return this;
    }

    public CreatePluginToolReq setAuthRequired(Boolean authRequired) {
        this.authRequired = authRequired;
        return this;
    }

    public Boolean isAuthRequired() {
        return authRequired;
    }

    public String getTestStatus() {
        return testStatus;
    }

    public CreatePluginToolReq setTestStatus(String testStatus) {
        this.testStatus = testStatus;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CreatePluginToolReq {\n");

        sb.append("    pluginId: ").append(toIndentedString(pluginId)).append("\n");
        sb.append("    toolDisplayName: ").append(toIndentedString(toolDisplayName)).append("\n");
        sb.append("    toolChineseName: ").append(toIndentedString(toolChineseName)).append("\n");
        sb.append("    toolDesc: ").append(toIndentedString(toolDesc)).append("\n");
        sb.append("    callMode: ").append(toIndentedString(callMode)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    requestInfo: ").append(toIndentedString(requestInfo)).append("\n");
        sb.append("    authInfo: ").append(toIndentedString(authInfo)).append("\n");
        sb.append("    visibility: ").append(toIndentedString(visibility)).append("\n");
        sb.append("    intfType: ").append(toIndentedString(intfType)).append("\n");
        sb.append("    inputSchema: ").append(toIndentedString(inputSchema)).append("\n");
        sb.append("    isInputList: ").append(toIndentedString(isInputList)).append("\n");
        sb.append("    outputSchema: ").append(toIndentedString(outputSchema)).append("\n");
        sb.append("    isOutputList: ").append(toIndentedString(isOutputList)).append("\n");
        sb.append("    metadata: ").append(toIndentedString(metadata)).append("\n");
        sb.append("    authRequired: ").append(toIndentedString(authRequired)).append("\n");
        sb.append("    testStatus: ").append(toIndentedString(testStatus)).append("\n");
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
        CreatePluginToolReq createPluginToolReq = (CreatePluginToolReq) o;
        return Objects.equals(this.pluginId, createPluginToolReq.pluginId) && Objects.equals(this.toolDisplayName,
            createPluginToolReq.toolDisplayName) && Objects.equals(this.toolChineseName,
            createPluginToolReq.toolChineseName) && Objects.equals(this.toolDesc, createPluginToolReq.toolDesc)
            && Objects.equals(this.callMode, createPluginToolReq.callMode) && Objects.equals(this.icon,
            createPluginToolReq.icon) && Objects.equals(this.requestInfo, createPluginToolReq.requestInfo)
            && Objects.equals(this.authInfo, createPluginToolReq.authInfo) && Objects.equals(this.visibility,
            createPluginToolReq.visibility) && Objects.equals(this.intfType, createPluginToolReq.intfType)
            && Objects.equals(this.inputSchema, createPluginToolReq.inputSchema) && Objects.equals(this.isInputList,
            createPluginToolReq.isInputList) && Objects.equals(this.outputSchema, createPluginToolReq.outputSchema)
            && Objects.equals(this.isOutputList, createPluginToolReq.isOutputList) && Objects.equals(this.metadata,
            createPluginToolReq.metadata) && Objects.equals(this.authRequired, createPluginToolReq.authRequired)
            && Objects.equals(this.testStatus, createPluginToolReq.testStatus);
    }

    @Override
    public int hashCode() {
        return Objects.hash(pluginId, toolDisplayName, toolChineseName, toolDesc, callMode, icon, requestInfo, authInfo,
            visibility, intfType, inputSchema, isInputList, outputSchema, isOutputList, metadata, authRequired,
            testStatus);
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
