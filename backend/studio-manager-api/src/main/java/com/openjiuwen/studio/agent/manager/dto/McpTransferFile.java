/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/**
 * FEAT-134 MCP 服务迁移文件（openjiuwen.mcp-services v1）。
 *
 * 单 JSON 直接下载；字段白名单见 L2 §2.3。导出不含任何鉴权凭据与身份字段；
 * 导入按同白名单解析，多余顶层字段拒绝。
 */
public class McpTransferFile {

    public static final String FORMAT_VALUE = "openjiuwen.mcp-services";
    public static final int CURRENT_VERSION = 1;
    public static final int MAX_SERVICES = 100;
    public static final long MAX_FILE_BYTES = 10L * 1024 * 1024;
    public static final int MAX_JSON_DEPTH = 32;

    @JsonProperty("format")
    private String format;

    @JsonProperty("version")
    private Integer version;

    @JsonProperty("exported_at")
    private String exportedAt;

    @JsonProperty("services")
    private List<McpTransferServiceDefinition> services;

    public String getFormat() {
        return format;
    }

    public McpTransferFile setFormat(String format) {
        this.format = format;
        return this;
    }

    public Integer getVersion() {
        return version;
    }

    public McpTransferFile setVersion(Integer version) {
        this.version = version;
        return this;
    }

    public String getExportedAt() {
        return exportedAt;
    }

    public McpTransferFile setExportedAt(String exportedAt) {
        this.exportedAt = exportedAt;
        return this;
    }

    public List<McpTransferServiceDefinition> getServices() {
        return services;
    }

    public McpTransferFile setServices(List<McpTransferServiceDefinition> services) {
        this.services = services;
        return this;
    }
}
