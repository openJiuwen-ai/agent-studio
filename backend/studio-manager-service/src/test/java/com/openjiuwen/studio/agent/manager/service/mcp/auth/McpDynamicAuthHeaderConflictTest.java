/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.mcp.auth;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.common.dto.auth.AuthKeyInfo;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.service.mcp.model.dao.McpServiceDao;
import com.openjiuwen.studio.agent.manager.utils.CommonUtil;
import com.openjiuwen.studio.common.service.service.EncryptionAdapter;

import java.util.List;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.MockitoAnnotations;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * FEAT-093 MCP 服务动态鉴权头 vs serverConfig 固定请求头同名拒绝回归：
 * 创建（deploy）/编辑（modifyService）MCP 服务时，serverConfig headers
 * 与 auth_keys[].target_name 同名（大小写不敏感）必须报
 * MCP_AUTH_DATA_INVALID——固定头先注入、动态凭证头按绑定值注入，
 * 同名互相覆盖会造成凭证值被固定头顶掉。
 */
class McpDynamicAuthHeaderConflictTest {

    private McpBaseImpl mcpBase;

    @BeforeEach
    void setUp() {
        MockitoAnnotations.openMocks(this);
        mcpBase = new McpBaseImpl();
        ReflectionTestUtils.setField(mcpBase, "mappingMapper", org.mockito.Mockito.mock(MappingMapper.class));
        ReflectionTestUtils.setField(mcpBase, "serviceDao", org.mockito.Mockito.mock(McpServiceDao.class));
        ReflectionTestUtils.setField(mcpBase, "encryptionAdapter", org.mockito.Mockito.mock(EncryptionAdapter.class));
    }

    private static AuthInfo dynamicAuth(String targetName) {
        AuthInfo authInfo = new AuthInfo();
        authInfo.setScope(AuthInfo.ScopeEnum.DYNAMIC);
        authInfo.setDomain(AuthInfo.DomainEnum.HEADERS);
        AuthKeyInfo keyInfo = new AuthKeyInfo();
        keyInfo.setTargetName(targetName);
        keyInfo.setSourceName("userToken");
        authInfo.setAuthKeys(List.of(keyInfo));
        return authInfo;
    }

    @Test
    void sameNameExactCase_throwsConflict() {
        // serverConfig 固定头与动态头完全同名 → 拒绝
        String serverConfig = "{\"url\":\"https://mcp.example.com\",\"headers\":"
            + "{\"Authorization\":\"Bearer fixed-token\"}}";
        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> mcpBase.validDynamicAuthHeaderConflict(dynamicAuth("Authorization"), serverConfig));
        assertEquals(StudioError.MCP_AUTH_DATA_INVALID, ex.getErrorCode());
    }

    @Test
    void sameNameDifferentCase_throwsConflict() {
        // 大小写不敏感：X-Custom-Token vs x-custom-token → 拒绝
        String serverConfig = "{\"url\":\"https://mcp.example.com\",\"headers\":"
            + "{\"x-custom-token\":\"fixed\"}}";
        assertThrows(AgentStudioException.class,
            () -> mcpBase.validDynamicAuthHeaderConflict(dynamicAuth("X-Custom-Token"), serverConfig));
    }

    @Test
    void nestedHeadersLocation_throwsConflict() {
        // headers 在 serverConfig 嵌套层（streamable_http 形态的 security_headers 层级）
        String serverConfig = "{\"servers\":{\"mcp\":{\"url\":\"https://mcp.example.com\","
            + "\"headers\":{\"Authorization\":\"Bearer fixed\"}}}}";
        assertThrows(AgentStudioException.class,
            () -> mcpBase.validDynamicAuthHeaderConflict(dynamicAuth("Authorization"), serverConfig));
    }

    @Test
    void differentNames_passes() {
        // 无同名 → 通过（固定头与动态头各走各的注入通道）
        String serverConfig = "{\"url\":\"https://mcp.example.com\",\"headers\":"
            + "{\"X-Api-Key\":\"fixed\",\"Accept\":\"application/json\"}}";
        assertDoesNotThrow(() ->
            mcpBase.validDynamicAuthHeaderConflict(dynamicAuth("Authorization"), serverConfig));
    }

    @Test
    void nonDynamicScope_skipsCheck() {
        // 非 DYNAMIC（SERVICE/API Key）→ 跳过（固定头与鉴权头语义本就共存）
        String serverConfig = "{\"url\":\"https://mcp.example.com\",\"headers\":"
            + "{\"Authorization\":\"Bearer fixed\"}}";
        AuthInfo serviceAuth = new AuthInfo();
        serviceAuth.setScope(AuthInfo.ScopeEnum.SERVICE);
        assertDoesNotThrow(() ->
            mcpBase.validDynamicAuthHeaderConflict(serviceAuth, serverConfig));
        assertDoesNotThrow(() ->
            mcpBase.validDynamicAuthHeaderConflict(null, serverConfig));
    }

    @Test
    void blankServerConfigOrNoHeaders_skipsCheck() {
        // serverConfig 空 / 无 headers 键 → 跳过（无可比对项）
        assertDoesNotThrow(() ->
            mcpBase.validDynamicAuthHeaderConflict(dynamicAuth("Authorization"), null));
        assertDoesNotThrow(() ->
            mcpBase.validDynamicAuthHeaderConflict(dynamicAuth("Authorization"), ""));
        assertDoesNotThrow(() ->
            mcpBase.validDynamicAuthHeaderConflict(dynamicAuth("Authorization"), "{\"url\":\"https://mcp.example.com\"}"));
    }

    @Test
    void malformedServerConfig_skipsWithoutError() {
        // serverConfig 非法 JSON → 跳过（格式错误由调用方各自的
        // validateMcpConfigFormat 报具体错误码，不在此重复报）
        assertDoesNotThrow(() ->
            mcpBase.validDynamicAuthHeaderConflict(dynamicAuth("Authorization"), "not-a-json{"));
    }

    @Test
    void commonUtilParseHeaders_extractsNestedHeaders() {
        // 依赖面核验：CommonUtil.parseMcpConfigHeaderInfo 递归提取嵌套 headers
        String serverConfig = "{\"servers\":{\"mcp\":{\"url\":\"https://mcp.example.com\","
            + "\"headers\":{\"Authorization\":\"Bearer fixed\"}}}}";
        var headers = CommonUtil.parseMcpConfigHeaderInfo(serverConfig);
        assertEquals("Bearer fixed", headers.get("Authorization"));
    }
}
