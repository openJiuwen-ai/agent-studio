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
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 关联的Mcp服务对象。
 */
@ApiModel(description = "关联的Mcp服务对象。")

@Validated

public class McpServerReference implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("mcp_server_id")
    @Schema(description = "MCP服务ID", example = "mcp_server_001")
    private String mcpServerId = null;

    @JsonProperty("mcp_server_name")
    @Schema(description = "MCP服务名称", example = "文件检索服务")
    private String mcpServerName = null;

    @JsonProperty("mcp_server_icon")
    @Schema(description = "MCP服务图标", example = "icon-url-001")
    private String mcpServerIcon = null;

    @JsonProperty("valid")
    @Schema(description = "是否有效", example = "true")
    private Boolean valid = null;

    @JsonProperty("desc")
    @Schema(description = "描述信息", example = "这是一个MCP服务")
    private String desc = null;

    @JsonProperty("mcp_choose_tools")
    @Schema(description = "已选工具列表", example = "[\"tool1\",\"tool2\"]")
    @Valid
    @Size()
    private List<@Length() String> mcpChooseTools = null;

    @JsonProperty("tools_num")
    @Schema(description = "工具数量", example = "5")
    private Integer toolsNum = null;

    @JsonProperty("mcp_parameter")
    @Schema(description = "MCP参数", example = "{\"key\":\"value\"}")
    private String mcpParameter = null;

    public String getMcpServerId() {
        return mcpServerId;
    }

    public McpServerReference setMcpServerId(String mcpServerId) {
        this.mcpServerId = mcpServerId;
        return this;
    }

    public String getMcpServerName() {
        return mcpServerName;
    }

    public McpServerReference setMcpServerName(String mcpServerName) {
        this.mcpServerName = mcpServerName;
        return this;
    }

    public String getMcpServerIcon() {
        return mcpServerIcon;
    }

    public McpServerReference setMcpServerIcon(String mcpServerIcon) {
        this.mcpServerIcon = mcpServerIcon;
        return this;
    }

    public McpServerReference setValid(Boolean valid) {
        this.valid = valid;
        return this;
    }

    public Boolean isValid() {
        return valid;
    }

    public String getDesc() {
        return desc;
    }

    public McpServerReference setDesc(String desc) {
        this.desc = desc;
        return this;
    }

    public List<String> getMcpChooseTools() {
        return mcpChooseTools;
    }

    public McpServerReference setMcpChooseTools(List<String> mcpChooseTools) {
        this.mcpChooseTools = mcpChooseTools;
        return this;
    }

    public Integer getToolsNum() {
        return toolsNum;
    }

    public McpServerReference setToolsNum(Integer toolsNum) {
        this.toolsNum = toolsNum;
        return this;
    }

    public String getMcpParameter() {
        return mcpParameter;
    }

    public McpServerReference setMcpParameter(String mcpParameter) {
        this.mcpParameter = mcpParameter;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpServerReference {\n");

        sb.append("    mcpServerId: ").append(toIndentedString(mcpServerId)).append("\n");
        sb.append("    mcpServerName: ").append(toIndentedString(mcpServerName)).append("\n");
        sb.append("    mcpServerIcon: ").append(toIndentedString(mcpServerIcon)).append("\n");
        sb.append("    valid: ").append(toIndentedString(valid)).append("\n");
        sb.append("    desc: ").append(toIndentedString(desc)).append("\n");
        sb.append("    mcpChooseTools: ").append(toIndentedString(mcpChooseTools)).append("\n");
        sb.append("    toolsNum: ").append(toIndentedString(toolsNum)).append("\n");
        sb.append("    mcpParameter: ").append(toIndentedString(mcpParameter)).append("\n");
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
        McpServerReference mcpServerReference = (McpServerReference) o;
        return Objects.equals(this.mcpServerId, mcpServerReference.mcpServerId) && Objects.equals(this.mcpServerName,
            mcpServerReference.mcpServerName) && Objects.equals(this.mcpServerIcon, mcpServerReference.mcpServerIcon)
            && Objects.equals(this.valid, mcpServerReference.valid) && Objects.equals(this.desc,
            mcpServerReference.desc) && Objects.equals(this.mcpChooseTools, mcpServerReference.mcpChooseTools)
            && Objects.equals(this.toolsNum, mcpServerReference.toolsNum) && Objects.equals(this.mcpParameter,
            mcpServerReference.mcpParameter);
    }

    @Override
    public int hashCode() {
        return Objects.hash(mcpServerId, mcpServerName, mcpServerIcon, valid, desc, mcpChooseTools, toolsNum,
            mcpParameter);
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
