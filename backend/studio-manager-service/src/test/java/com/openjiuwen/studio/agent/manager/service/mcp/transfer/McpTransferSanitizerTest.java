/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.mcp.transfer;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.dto.McpTransferServiceDefinition;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * FEAT-134 McpTransferSanitizer 单元测试。
 *
 * 覆盖 L2 §9.2（凭据防泄露 S-01~S-07）与 §9.3（文件校验 I-04）中
 * 不依赖 Spring 上下文 / 数据库的部分：安全投影（导出侧）与导入安全契约（导入侧）。
 */
@DisplayName("McpTransferSanitizer")
class McpTransferSanitizerTest {

    private McpTransferSanitizer sanitizer;

    @BeforeEach
    void setUp() {
        sanitizer = new McpTransferSanitizer();
    }

    // ================================================================ helpers

    private Map<String, Object> serverConfig(Map<String, Object> node) {
        Map<String, Object> config = new LinkedHashMap<>();
        Map<String, Object> servers = new LinkedHashMap<>();
        servers.put("test-service", node);
        config.put("mcpServers", servers);
        return config;
    }

    private Map<String, Object> node(String url) {
        Map<String, Object> n = new LinkedHashMap<>();
        n.put("url", url);
        return n;
    }

    private Map<String, Object> node(Map<String, Object> headers, Map<String, Object> env) {
        Map<String, Object> n = new LinkedHashMap<>();
        if (headers != null) {
            n.put("headers", headers);
        }
        if (env != null) {
            n.put("env", env);
        }
        return n;
    }

    private McpTransferServiceDefinition definition(String name, String orgType, String deployType,
        String url, Map<String, Object> serverConfig) {
        McpTransferServiceDefinition def = new McpTransferServiceDefinition();
        def.setName(name);
        def.setOrgType(orgType);
        def.setDeployType(deployType);
        def.setUrl(url);
        def.setServerConfig(serverConfig);
        def.setToolsSnapshot(List.of());
        def.setRequiresAuthConfiguration(false);
        def.setRedactedFields(List.of());
        return def;
    }

    // ================================================================ 导出侧：安全投影

    @Nested
    @DisplayName("sanitizeForExport")
    class SanitizeForExport {

        @Test
        @DisplayName("S-02: headers 值全部剔除，头名保留为空串")
        void headersValuesCleared() {
            Map<String, Object> headers = new LinkedHashMap<>();
            headers.put("Authorization", "Bearer secret-token");
            headers.put("X-Custom", "custom-value");
            Map<String, Object> config = serverConfig(node(headers, null));

            McpTransferSanitizer.SanitizeResult result =
                sanitizer.sanitizeForExport("https://example.com/mcp", config, List.of(), false);

            Map<String, Object> node = getNode(result);
            Map<String, Object> outHeaders = (Map<String, Object>) node.get("headers");
            assertEquals("", outHeaders.get("Authorization"));
            assertEquals("", outHeaders.get("X-Custom"));
            // 路径记录包含头名
            assertTrue(result.redactedPaths.stream()
                .anyMatch(p -> p.contains("/headers/Authorization")));
        }

        @Test
        @DisplayName("S-04: env 值全部清空（null），变量名保留")
        void envValuesNulled() {
            Map<String, Object> env = new LinkedHashMap<>();
            env.put("API_KEY", "sk-12345678");
            env.put("SECRET", "super-secret");
            Map<String, Object> config = serverConfig(node(null, env));

            McpTransferSanitizer.SanitizeResult result =
                sanitizer.sanitizeForExport("https://example.com/mcp", config, List.of(), false);

            Map<String, Object> node = getNode(result);
            Map<String, Object> outEnv = (Map<String, Object>) node.get("env");
            assertNull(outEnv.get("API_KEY"));
            assertNull(outEnv.get("SECRET"));
        }

        @Test
        @DisplayName("S-03: URL userinfo 剔除")
        void urlUserinfoRemoved() {
            McpTransferSanitizer.SanitizeResult result =
                sanitizer.sanitizeForExport("https://user:pass@example.com/mcp", null, List.of(), false);
            assertFalse(result.url.contains("user:pass"));
            assertTrue(result.url.contains("example.com"));
        }

        @Test
        @DisplayName("S-03: URL fragment 剔除")
        void urlFragmentRemoved() {
            McpTransferSanitizer.SanitizeResult result =
                sanitizer.sanitizeForExport("https://example.com/mcp#secret", null, List.of(), false);
            assertFalse(result.url.contains("#secret"));
        }

        @Test
        @DisplayName("S-03: URL query 值清空，参数名保留")
        void urlQueryValuesCleared() {
            McpTransferSanitizer.SanitizeResult result =
                sanitizer.sanitizeForExport("https://example.com/mcp?token=abc&user=xyz", null, List.of(), false);
            assertTrue(result.url.contains("token="));
            assertFalse(result.url.contains("abc"));
            assertFalse(result.url.contains("xyz"));
        }

        @Test
        @DisplayName("S-03: 含 ${_env.} 占位符的 URL 原样保留")
        void envPlaceholderUrlPreserved() {
            String url = "https://${_env.plugin_url_params.MCP_HOST}/mcp";
            McpTransferSanitizer.SanitizeResult result = sanitizer.sanitizeForExport(url, null, List.of(), false);
            assertEquals(url, result.url);
        }

        @Test
        @DisplayName("S-07: 工具 schema default/example/examples 移除")
        void toolSchemaDefaultsRemoved() {
            Map<String, Object> tool = new LinkedHashMap<>();
            tool.put("name", "test_tool");
            tool.put("description", "A test tool");
            tool.put("default", "secret-default");
            tool.put("example", "secret-example");
            tool.put("examples", List.of("ex1", "ex2"));
            tool.put("inputSchema", Map.of("type", "object"));

            McpTransferSanitizer.SanitizeResult result =
                sanitizer.sanitizeForExport("https://example.com", null, List.of(tool), false);

            Map<String, Object> outTool = result.toolsSnapshot.get(0);
            assertEquals("test_tool", outTool.get("name"));
            assertEquals("A test tool", outTool.get("description"));
            assertNull(outTool.get("default"));
            assertNull(outTool.get("example"));
            assertNull(outTool.get("examples"));
            assertNotNull(outTool.get("inputSchema"));
        }

        @Test
        @DisplayName("有鉴权头时 requiresAuth=true")
        void sensitiveHeaderTriggersAuthFlag() {
            Map<String, Object> headers = new LinkedHashMap<>();
            headers.put("Authorization", "Bearer token");
            Map<String, Object> config = serverConfig(node(headers, null));
            McpTransferSanitizer.SanitizeResult result =
                sanitizer.sanitizeForExport("https://example.com", config, List.of(), false);
            assertTrue(result.requiresAuth);
        }

        @Test
        @DisplayName("未知结构节点键不透传（记录路径）")
        void unknownNodeKeyNotPassedThrough() {
            Map<String, Object> n = node("https://example.com/mcp");
            n.put("unknown_custom_field", "some-value");
            Map<String, Object> config = serverConfig(n);

            McpTransferSanitizer.SanitizeResult result =
                sanitizer.sanitizeForExport("https://example.com", config, List.of(), false);

            Map<String, Object> outNode = getNode(result);
            assertFalse(outNode.containsKey("unknown_custom_field"));
        }
    }

    // ================================================================ 导入侧：安全契约

    @Nested
    @DisplayName("validateImportSafety")
    class ValidateImportSafety {

        @Test
        @DisplayName("S-06: 文件携带 authInfo 字段被拒绝")
        void authInfoFieldRejected() {
            Map<String, Object> config = serverConfig(node("https://example.com/mcp"));
            config.put("authInfo", "some-auth-data");
            McpTransferServiceDefinition def =
                definition("test", "SSE", "sse", "https://example.com/mcp", config);
            AgentStudioException e = assertThrows(AgentStudioException.class,
                () -> sanitizer.validateImportSafety(def));
            assertEquals(StudioError.MCP_TRANSFER_UNSAFE_CONFIG, e.getErrorCode());
        }

        @ParameterizedTest
        @ValueSource(strings = {"auth", "token", "password", "secret", "credentials"})
        @DisplayName("S-06: 顶层凭据字段名被拒绝（参数化）")
        void credentialFieldNamesRejected(String fieldName) {
            Map<String, Object> config = serverConfig(node("https://example.com/mcp"));
            config.put(fieldName, "some-value");
            McpTransferServiceDefinition def =
                definition("test", "SSE", "sse", "https://example.com/mcp", config);
            assertThrows(AgentStudioException.class, () -> sanitizer.validateImportSafety(def));
        }

        @Test
        @DisplayName("S-02: 文件携带非空头值被拒绝")
        void nonEmptyHeaderValueRejected() {
            Map<String, Object> headers = new LinkedHashMap<>();
            headers.put("Authorization", "Bearer injected-token");
            Map<String, Object> config = serverConfig(node(headers, null));
            McpTransferServiceDefinition def =
                definition("test", "SSE", "sse", "https://example.com/mcp", config);
            assertThrows(AgentStudioException.class, () -> sanitizer.validateImportSafety(def));
        }

        @Test
        @DisplayName("S-04: 文件携带非空 env 值被拒绝")
        void nonEmptyEnvValueRejected() {
            Map<String, Object> env = new LinkedHashMap<>();
            env.put("API_KEY", "injected-key");
            Map<String, Object> config = serverConfig(node(null, env));
            McpTransferServiceDefinition def =
                definition("test", "SSE", "sse", "https://example.com/mcp", config);
            assertThrows(AgentStudioException.class, () -> sanitizer.validateImportSafety(def));
        }

        @Test
        @DisplayName("S-03: 文件 URL 携带 userinfo 被拒绝")
        void urlUserinfoRejected() {
            McpTransferServiceDefinition def =
                definition("test", "SSE", "sse", "https://user:pass@example.com/mcp", null);
            assertThrows(AgentStudioException.class, () -> sanitizer.validateImportSafety(def));
        }

        @Test
        @DisplayName("S-03: 文件 URL 携带非空 query 值被拒绝")
        void nonEmptyUrlQueryRejected() {
            McpTransferServiceDefinition def =
                definition("test", "SSE", "sse", "https://example.com/mcp?token=injected", null);
            assertThrows(AgentStudioException.class, () -> sanitizer.validateImportSafety(def));
        }

        @Test
        @DisplayName("S-03: 空 query 值（token=）不拒绝")
        void emptyUrlQueryAccepted() {
            McpTransferServiceDefinition def =
                definition("test", "SSE", "sse", "https://example.com/mcp?token=", null);
            // validateImportSafety 不抛异常即通过（URL 安全性单独校验）
            assertDoesNotThrow(() -> sanitizer.validateImportSafety(def));
        }

        @Test
        @DisplayName("多个 mcpServers 节点被拒绝（配置歧义）")
        void multipleServiceNodesRejected() {
            Map<String, Object> config = new LinkedHashMap<>();
            Map<String, Object> servers = new LinkedHashMap<>();
            servers.put("node1", node("https://example.com/1"));
            servers.put("node2", node("https://example.com/2"));
            config.put("mcpServers", servers);
            McpTransferServiceDefinition def =
                definition("test", "SSE", "sse", "https://example.com/mcp", config);
            assertThrows(AgentStudioException.class, () -> sanitizer.validateImportSafety(def));
        }

        @Test
        @DisplayName("标准形态（无凭据、空头值）通过校验")
        void cleanDefinitionAccepted() {
            Map<String, Object> headers = new LinkedHashMap<>();
            headers.put("Authorization", "");
            Map<String, Object> env = new LinkedHashMap<>();
            env.put("API_KEY", "");
            Map<String, Object> config = serverConfig(node(headers, env));
            McpTransferServiceDefinition def =
                definition("test", "SSE", "sse", "https://example.com/mcp", config);
            assertDoesNotThrow(() -> sanitizer.validateImportSafety(def));
        }
    }

    // ================================================================ 二次扫描

    @Nested
    @DisplayName("scanForKnownSecrets")
    class ScanForKnownSecrets {

        @Test
        @DisplayName("S-07: 已知秘密值命中即拒绝")
        void knownSecretRejected() {
            String file = "{\"name\":\"test\",\"description\":\"some content with my-secret-value inside\"}";
            assertThrows(AgentStudioException.class,
                () -> sanitizer.scanForKnownSecrets(file, List.of("my-secret-value")));
        }

        @Test
        @DisplayName("已知秘密值未命中则通过")
        void noSecretMatchAccepted() {
            String file = "{\"name\":\"test\"}";
            assertDoesNotThrow(() -> sanitizer.scanForKnownSecrets(file, List.of("not-present-secret")));
        }

        @Test
        @DisplayName("短于 6 字符的秘密不参与扫描")
        void shortSecretsSkipped() {
            String file = "{\"name\":\"abc\"}";
            assertDoesNotThrow(() -> sanitizer.scanForKnownSecrets(file, List.of("abc")));
        }
    }

    // ================================================================ util

    @SuppressWarnings("unchecked")
    private Map<String, Object> getNode(McpTransferSanitizer.SanitizeResult result) {
        Map<String, Object> servers = (Map<String, Object>) result.serverConfig.get("mcpServers");
        return (Map<String, Object>) servers.values().iterator().next();
    }
}
