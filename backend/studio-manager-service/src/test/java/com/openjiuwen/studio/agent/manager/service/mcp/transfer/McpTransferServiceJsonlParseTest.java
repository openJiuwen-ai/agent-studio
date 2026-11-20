/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.mcp.transfer;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.dto.McpTransferServiceDefinition;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

/**
 * FEAT-134 JSONL 迁移文件解析校验单元测试。
 *
 * 文件格式与插件/工作流/模型导出统一：一个服务一行，
 * 行结构 {"import_type":"MCP_SERVICE","version":1,"payload":{服务定义}}。
 */
@DisplayName("McpTransferService JSONL 解析校验")
@ExtendWith(MockitoExtension.class)
class McpTransferServiceJsonlParseTest {

    @Mock
    private McpTransferSanitizer sanitizer;

    @InjectMocks
    private McpTransferService service;

    private static String line(String payloadJson) {
        return "{\"import_type\":\"MCP_SERVICE\",\"version\":1,\"payload\":" + payloadJson + "}";
    }

    private static String payload(String name) {
        return "{\"name\":\"" + name + "\",\"org_type\":\"STREAMABLE_HTTP\","
            + "\"deploy_type\":\"streamable_http\",\"url\":\"http://127.0.0.1:31099/mcp\","
            + "\"server_config\":{\"url\":\"http://127.0.0.1:31099/mcp\"},"
            + "\"tools_snapshot\":[]}";
    }

    @Test
    @DisplayName("J-01: 合法两行（CRLF 分隔）解析出两个定义")
    void parseTwoLines() {
        String content = line(payload("svc-a")) + "\r\n" + line(payload("svc-b")) + "\r\n";
        java.util.List<McpTransferServiceDefinition> defs = service.parseAndValidateFile(content);
        assertEquals(2, defs.size());
        assertEquals("svc-a", defs.get(0).getName());
        assertEquals("svc-b", defs.get(1).getName());
    }

    @Test
    @DisplayName("J-02: 旧版单 JSON 文件被 import_type 校验拒绝")
    void rejectLegacySingleJson() {
        String legacy = "{\"format\":\"openjiuwen.mcp-services\",\"version\":1,\"services\":[]}";
        AgentStudioException e = assertThrows(AgentStudioException.class,
            () -> service.parseAndValidateFile(legacy));
        assertEquals(StudioError.MCP_TRANSFER_FORMAT_INVALID, e.getErrorCode());
    }

    @Test
    @DisplayName("J-03: 行版本不支持 → 1185")
    void rejectUnsupportedVersion() {
        String content = "{\"import_type\":\"MCP_SERVICE\",\"version\":2,\"payload\":" + payload("svc-a") + "}";
        AgentStudioException e = assertThrows(AgentStudioException.class,
            () -> service.parseAndValidateFile(content));
        assertEquals(StudioError.MCP_TRANSFER_VERSION_UNSUPPORTED, e.getErrorCode());
    }

    @Test
    @DisplayName("J-04: 非法 JSON 行报错带行号")
    void rejectInvalidLineWithLineNumber() {
        String content = line(payload("svc-a")) + "\nnot-a-json\n";
        AgentStudioException e = assertThrows(AgentStudioException.class,
            () -> service.parseAndValidateFile(content));
        assertEquals(StudioError.MCP_TRANSFER_FORMAT_INVALID, e.getErrorCode());
        org.junit.jupiter.api.Assertions.assertTrue(String.valueOf(e.getMessage()).contains("line 2"));
    }

    @Test
    @DisplayName("J-05: 空文件与纯空行文件按空文件拒绝")
    void rejectEmptyContent() {
        AgentStudioException e1 = assertThrows(AgentStudioException.class,
            () -> service.parseAndValidateFile("   \n  \n"));
        assertEquals(StudioError.MCP_TRANSFER_FORMAT_INVALID, e1.getErrorCode());

        AgentStudioException e2 = assertThrows(AgentStudioException.class,
            () -> service.parseAndValidateFile(null));
        assertEquals(StudioError.MCP_TRANSFER_FORMAT_INVALID, e2.getErrorCode());
    }

    @Test
    @DisplayName("J-06: 其他资源类型行（workflow）被 import_type 拒绝")
    void rejectForeignImportType() {
        String foreign = "{\"import_type\":\"workflow\",\"version\":1,\"payload\":{\"id\":\"wf-1\"}}";
        AgentStudioException e = assertThrows(AgentStudioException.class,
            () -> service.parseAndValidateFile(foreign));
        assertEquals(StudioError.MCP_TRANSFER_FORMAT_INVALID, e.getErrorCode());
    }

    @Test
    @DisplayName("J-07: 定义字段缺失报错带行号（name 过短）")
    void fieldInvalidCarriesLineNo() {
        String shortName = "{\"name\":\"s\",\"org_type\":\"STREAMABLE_HTTP\","
            + "\"deploy_type\":\"streamable_http\",\"url\":\"http://x/mcp\","
            + "\"server_config\":{}}";
        String content = line(shortName);
        AgentStudioException e = assertThrows(AgentStudioException.class,
            () -> service.parseAndValidateFile(content));
        assertEquals(StudioError.MCP_TRANSFER_FIELD_INVALID, e.getErrorCode());
        org.junit.jupiter.api.Assertions.assertTrue(String.valueOf(e.getMessage()).contains("line 1"));
    }
}
