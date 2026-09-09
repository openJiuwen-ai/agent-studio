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
import java.util.Map;
import java.util.Objects;

/**
 * mcp 服务信息
 */
@ApiModel(description = "mcp 服务信息")

@Validated

public class McpServerRuntimeVo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "MCP服务ID", example = "mcp_001")
    @Length(max = 64)
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "MCP服务名称", example = "天气查询服务")
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "MCP服务描述", example = "提供天气信息查询服务")
    private String description = null;

    @JsonProperty("type")
    @Schema(description = "MCP服务类型", example = "sse")
    private String type = null;

    @JsonProperty("command")
    @Schema(description = "启动命令", example = "npx")
    private String command = null;

    @JsonProperty("baseUrl")
    @Schema(description = "基础URL", example = "https://mcp.example.com")
    private String baseUrl = null;

    @JsonProperty("args")
    @Schema(description = "启动参数列表", example = "[\"--port\", \"8080\"]")
    @Valid
    @Size()
    private List<@Length() String> args = null;

    @JsonProperty("env")
    @Schema(description = "环境变量", example = "{\"API_KEY\": \"xxx\"}")
    @Valid
    @Size()
    private Map<@Length() String, @Length() String> env = null;

    @JsonProperty("headers")
    @Schema(description = "请求头", example = "{\"Authorization\": \"Bearer xxx\"}")
    @Valid
    @Size()
    private Map<@Length() String, @Length() String> headers = null;

    public String getId() {
        return id;
    }

    public McpServerRuntimeVo setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public McpServerRuntimeVo setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public McpServerRuntimeVo setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getType() {
        return type;
    }

    public McpServerRuntimeVo setType(String type) {
        this.type = type;
        return this;
    }

    public String getCommand() {
        return command;
    }

    public McpServerRuntimeVo setCommand(String command) {
        this.command = command;
        return this;
    }

    public String getBaseUrl() {
        return baseUrl;
    }

    public McpServerRuntimeVo setBaseUrl(String baseUrl) {
        this.baseUrl = baseUrl;
        return this;
    }

    public List<String> getArgs() {
        return args;
    }

    public McpServerRuntimeVo setArgs(List<String> args) {
        this.args = args;
        return this;
    }

    public Map<String, String> getEnv() {
        return env;
    }

    public McpServerRuntimeVo setEnv(Map<String, String> env) {
        this.env = env;
        return this;
    }

    public Map<String, String> getHeaders() {
        return headers;
    }

    public McpServerRuntimeVo setHeaders(Map<String, String> headers) {
        this.headers = headers;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpServerRuntimeVo {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    command: ").append(toIndentedString(command)).append("\n");
        sb.append("    baseUrl: ").append(toIndentedString(baseUrl)).append("\n");
        sb.append("    args: ").append(toIndentedString(args)).append("\n");
        sb.append("    env: ").append(toIndentedString(env)).append("\n");
        sb.append("    headers: ").append(toIndentedString(headers)).append("\n");
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
        McpServerRuntimeVo mcpServerRuntimeVo = (McpServerRuntimeVo) o;
        return Objects.equals(this.id, mcpServerRuntimeVo.id) && Objects.equals(this.name, mcpServerRuntimeVo.name)
            && Objects.equals(this.description, mcpServerRuntimeVo.description) && Objects.equals(this.type,
            mcpServerRuntimeVo.type) && Objects.equals(this.command, mcpServerRuntimeVo.command) && Objects.equals(
            this.baseUrl, mcpServerRuntimeVo.baseUrl) && Objects.equals(this.args, mcpServerRuntimeVo.args)
            && Objects.equals(this.env, mcpServerRuntimeVo.env) && Objects.equals(this.headers,
            mcpServerRuntimeVo.headers);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, description, type, command, baseUrl, args, env, headers);
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
