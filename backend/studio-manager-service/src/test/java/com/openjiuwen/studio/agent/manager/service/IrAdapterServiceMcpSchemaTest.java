package com.openjiuwen.studio.agent.manager.service;

import com.alibaba.fastjson2.JSON;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.entity.McpServiceEntity;
import com.openjiuwen.studio.agent.manager.service.mcp.McpServiceManager;
import com.openjiuwen.studio.agent.manager.service.mcp.model.dao.McpServiceDao;
import com.openjiuwen.studio.common.service.service.EncryptionAdapter;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.when;

/** Exercises persisted MCP tools through the public workflow IR adapter, without a server. */
class IrAdapterServiceMcpSchemaTest {
    private IrAdapterService adapter;
    private McpServiceEntity server;

    @BeforeEach
    void setUp() {
        server = new McpServiceEntity();
        server.setName("schema-repro");
        server.setVisibility("private");
        server.setDeployType("remote");
        server.setOrgType("streamable-http");
        server.setServerConfig("{\"mcpServers\":{\"repro\":{\"url\":\"https://example.invalid/mcp\"}}}");

        McpServiceDao dao = mock(McpServiceDao.class);
        when(dao.selectById(any(), any(), any(), any())).thenReturn(server);
        EncryptionAdapter encryption = mock(EncryptionAdapter.class);
        when(encryption.decrypt(server.getServerConfig())).thenReturn(server.getServerConfig());
        adapter = new IrAdapterService();
        ReflectionTestUtils.setField(adapter, "serviceDao", dao);
        ReflectionTestUtils.setField(adapter, "encryptionAdapter", encryption);
        ReflectionTestUtils.setField(adapter, "mcpServiceManager", mock(McpServiceManager.class));
    }

    @Test
    void nullableIntegerInputProducesIntegerDefaultAndPreservesRequired() {
        Map<String, Object> result = adapt("""
            {"type":"object","required":["task_id"],"properties":{
              "task_id":{"type":"string"},
              "wait_seconds":{"type":["null","integer"],"default":0}
            }}
            """, "{\"type\":\"object\",\"properties\":{}}");
        Map<String, Object> wait = find(result.get("arguments"), "wait_seconds");
        assertEquals("integer", wait.get("type"));
        assertEquals(0, wait.get("default_value"));
        assertEquals(false, wait.get("required"));
        assertEquals(true, find(result.get("arguments"), "task_id").get("required"));
    }

    @Test
    void nullableArrayInputAndOutputKeepObjectItemSchemas() {
        String schema = """
            {"type":"object","required":["files"],"properties":{
              "files":{"type":["array","null"],"items":{
                "type":["null","object"],"required":["name"],"properties":{
                  "name":{"type":["null","string"]},
                  "size":{"type":["integer","null"]}
                }
              }}
            }}
            """;
        Map<String, Object> result = adapt(schema, schema);
        for (String key : List.of("arguments", "response")) {
            Map<String, Object> files = find(result.get(key), "files");
            assertEquals("array", files.get("type"));
            assertEquals(true, files.get("required"));
            Map<?, ?> items = (Map<?, ?>) files.get("schema");
            assertEquals("object", items.get("type"));
            assertEquals("string", find(items.get("schema"), "name").get("type"));
            assertEquals(true, find(items.get("schema"), "name").get("required"));
            assertEquals("integer", find(items.get("schema"), "size").get("type"));
            assertEquals(false, find(items.get("schema"), "size").get("required"));
        }
    }

    private Map<String, Object> adapt(String input, String output) {
        server.setTools(JSON.toJSONString(List.of(Map.of("name", "schema_probe", "description", "Schema probe",
            "inputSchema", JSON.parseObject(input), "outputSchema", JSON.parseObject(output)))));
        try (MockedStatic<RequestContextUtils> context = mockStatic(RequestContextUtils.class)) {
            context.when(RequestContextUtils::getRequestUserDomainId).thenReturn("tenant-id");
            return adapter.parseMcpConfigForWorkflow("server-id", "schema_probe", "project-id", "user-id", "workspace-id");
        }
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> find(Object fields, String name) {
        return ((List<Map<String, Object>>) fields).stream()
            .filter(field -> name.equals(field.get("name")))
            .findFirst().orElseThrow();
    }
}
