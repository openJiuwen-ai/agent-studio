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

public class ModifyToolReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("tool_display_name")
    @Schema(description = "工具显示名称", example = "my_tool")
    @Pattern(regexp = "^[a-zA-Z0-9_]+$")
    @Length(max = 64)
    private String toolDisplayName = null;

    @JsonProperty("tool_chinese_name")
    @Schema(description = "工具中文名称", example = "我的工具")
    @Length(min = 1, max = 64)
    private String toolChineseName = null;

    @JsonProperty("tool_desc")
    @Schema(description = "工具描述", example = "用于数据处理的工具")
    @Length(max = 600)
    private String toolDesc = null;

    @JsonProperty("icon")
    @Schema(description = "图标", example = "https://example.com/icon.png")
    private String icon = null;

    @JsonProperty("intf_type")
    @Schema(description = "接口类型", example = "rest")
    @Length(max = 64)
    private String intfType = null;

    @JsonProperty("request_info")
    @Schema(description = "请求信息")
    @Valid
    private RequestInfo requestInfo = null;

    @JsonProperty("auth_info")
    @Schema(description = "认证信息")
    @Valid
    private AuthInfo authInfo = null;

    @JsonProperty("input_schema")
    @Schema(description = "输入Schema", example = "{}")
    @Length(max = 200000)
    private String inputSchema = null;

    @JsonProperty("is_input_list")
    @Schema(description = "输入是否为列表", example = "false")
    private Boolean isInputList = null;

    @JsonProperty("output_schema")
    @Schema(description = "输出Schema", example = "{}")
    @Length(max = 200000)
    private String outputSchema = null;

    @JsonProperty("is_output_list")
    @Schema(description = "输出是否为列表", example = "false")
    private Boolean isOutputList = null;

    @JsonProperty("test_status")
    @Schema(description = "测试状态", example = "success")
    private String testStatus = null;

    @JsonProperty("metadata")
    @Schema(description = "元数据", example = "{}")
    @Length(max = 4096)
    private String metadata = null;

    @JsonProperty("customize_node")
    @Schema(description = "是否自定义节点", example = "false")
    private Boolean customizeNode = null;

    public String getToolDisplayName() {
        return toolDisplayName;
    }

    public ModifyToolReq setToolDisplayName(String toolDisplayName) {
        this.toolDisplayName = toolDisplayName;
        return this;
    }

    public String getToolChineseName() {
        return toolChineseName;
    }

    public ModifyToolReq setToolChineseName(String toolChineseName) {
        this.toolChineseName = toolChineseName;
        return this;
    }

    public String getToolDesc() {
        return toolDesc;
    }

    public ModifyToolReq setToolDesc(String toolDesc) {
        this.toolDesc = toolDesc;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public ModifyToolReq setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public String getIntfType() {
        return intfType;
    }

    public ModifyToolReq setIntfType(String intfType) {
        this.intfType = intfType;
        return this;
    }

    public RequestInfo getRequestInfo() {
        return requestInfo;
    }

    public ModifyToolReq setRequestInfo(RequestInfo requestInfo) {
        this.requestInfo = requestInfo;
        return this;
    }

    public AuthInfo getAuthInfo() {
        return authInfo;
    }

    public ModifyToolReq setAuthInfo(AuthInfo authInfo) {
        this.authInfo = authInfo;
        return this;
    }

    public String getInputSchema() {
        return inputSchema;
    }

    public ModifyToolReq setInputSchema(String inputSchema) {
        this.inputSchema = inputSchema;
        return this;
    }

    public ModifyToolReq setIsInputList(Boolean isInputList) {
        this.isInputList = isInputList;
        return this;
    }

    public Boolean isIsInputList() {
        return isInputList;
    }

    public String getOutputSchema() {
        return outputSchema;
    }

    public ModifyToolReq setOutputSchema(String outputSchema) {
        this.outputSchema = outputSchema;
        return this;
    }

    public ModifyToolReq setIsOutputList(Boolean isOutputList) {
        this.isOutputList = isOutputList;
        return this;
    }

    public Boolean isIsOutputList() {
        return isOutputList;
    }

    public String getTestStatus() {
        return testStatus;
    }

    public ModifyToolReq setTestStatus(String testStatus) {
        this.testStatus = testStatus;
        return this;
    }

    public String getMetadata() {
        return metadata;
    }

    public ModifyToolReq setMetadata(String metadata) {
        this.metadata = metadata;
        return this;
    }

    public ModifyToolReq setCustomizeNode(Boolean customizeNode) {
        this.customizeNode = customizeNode;
        return this;
    }

    public Boolean isCustomizeNode() {
        return customizeNode;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ModifyToolReq {\n");

        sb.append("    toolDisplayName: ").append(toIndentedString(toolDisplayName)).append("\n");
        sb.append("    toolChineseName: ").append(toIndentedString(toolChineseName)).append("\n");
        sb.append("    toolDesc: ").append(toIndentedString(toolDesc)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    intfType: ").append(toIndentedString(intfType)).append("\n");
        sb.append("    requestInfo: ").append(toIndentedString(requestInfo)).append("\n");
        sb.append("    authInfo: ").append(toIndentedString(authInfo)).append("\n");
        sb.append("    inputSchema: ").append(toIndentedString(inputSchema)).append("\n");
        sb.append("    isInputList: ").append(toIndentedString(isInputList)).append("\n");
        sb.append("    outputSchema: ").append(toIndentedString(outputSchema)).append("\n");
        sb.append("    isOutputList: ").append(toIndentedString(isOutputList)).append("\n");
        sb.append("    testStatus: ").append(toIndentedString(testStatus)).append("\n");
        sb.append("    metadata: ").append(toIndentedString(metadata)).append("\n");
        sb.append("    customizeNode: ").append(toIndentedString(customizeNode)).append("\n");
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
        ModifyToolReq modifyToolReq = (ModifyToolReq) o;
        return Objects.equals(this.toolDisplayName, modifyToolReq.toolDisplayName) && Objects.equals(
            this.toolChineseName, modifyToolReq.toolChineseName) && Objects.equals(this.toolDesc,
            modifyToolReq.toolDesc) && Objects.equals(this.icon, modifyToolReq.icon) && Objects.equals(this.intfType,
            modifyToolReq.intfType) && Objects.equals(this.requestInfo, modifyToolReq.requestInfo) && Objects.equals(
            this.authInfo, modifyToolReq.authInfo) && Objects.equals(this.inputSchema, modifyToolReq.inputSchema)
            && Objects.equals(this.isInputList, modifyToolReq.isInputList) && Objects.equals(this.outputSchema,
            modifyToolReq.outputSchema) && Objects.equals(this.isOutputList, modifyToolReq.isOutputList)
            && Objects.equals(this.testStatus, modifyToolReq.testStatus) && Objects.equals(this.metadata,
            modifyToolReq.metadata) && Objects.equals(this.customizeNode, modifyToolReq.customizeNode);
    }

    @Override
    public int hashCode() {
        return Objects.hash(toolDisplayName, toolChineseName, toolDesc, icon, intfType, requestInfo, authInfo,
            inputSchema, isInputList, outputSchema, isOutputList, testStatus, metadata, customizeNode);
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
