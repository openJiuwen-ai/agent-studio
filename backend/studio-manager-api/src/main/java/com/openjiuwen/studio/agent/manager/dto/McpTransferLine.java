/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * FEAT-134 MCP 服务迁移文件 JSONL 行 DTO。
 *
 * 文件格式与插件/工作流/模型导出统一为 jsonl：一个服务一行，行结构
 * {@code {"import_type":"MCP_SERVICE","version":1,"payload":{服务定义}}}。
 *
 * <p>{@code import_type} 用于跨类型导入防串（同平台约定：模型行为 MODEL_SERVICE、
 * 工作流为 workflow）；{@code version} 供导入端版本拒绝（1185）。
 *
 * <p>白名单字段见 L2 §2.3。导出不含任何鉴权凭据与身份字段；
 * 导入按同白名单解析，多余行字段忽略（前向兼容）。
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class McpTransferLine {

    /** 行类型标识：导入端拒绝非 MCP_SERVICE 行（防其他资源文件误导入）。 */
    public static final String IMPORT_TYPE_VALUE = "MCP_SERVICE";

    public static final int CURRENT_VERSION = 1;

    public static final int MAX_SERVICES = 100;

    public static final long MAX_FILE_BYTES = 10L * 1024 * 1024;

    @JsonProperty("import_type")
    private String importType;

    @JsonProperty("version")
    private Integer version;

    @JsonProperty("payload")
    private McpTransferServiceDefinition payload;

    public String getImportType() {
        return importType;
    }

    public McpTransferLine setImportType(String importType) {
        this.importType = importType;
        return this;
    }

    public Integer getVersion() {
        return version;
    }

    public McpTransferLine setVersion(Integer version) {
        this.version = version;
        return this;
    }

    public McpTransferServiceDefinition getPayload() {
        return payload;
    }

    public McpTransferLine setPayload(McpTransferServiceDefinition payload) {
        this.payload = payload;
        return this;
    }
}
