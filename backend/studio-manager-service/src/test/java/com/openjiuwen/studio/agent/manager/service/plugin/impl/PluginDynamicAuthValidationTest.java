/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.plugin.impl;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.common.dto.auth.AuthKeyInfo;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.dto.RequestInfo;
import com.openjiuwen.studio.agent.manager.mapper.DependencyMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.ToolMapper;
import com.openjiuwen.studio.agent.manager.mapper.plugin.PluginMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.IrAdapterService;
import com.openjiuwen.studio.common.service.service.EncryptionAdapter;

import java.util.List;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.MockitoAnnotations;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * FEAT-093 动态鉴权校验的 inputSchema 双形态回归（存量插件行=ToolInputSchema
 * 数组；请求体=单工具对象）——数组按数组解析遍历内层，防存量插件把鉴权
 * 切 DYNAMIC 时对象解析抛错使接口整体失败；同时覆盖回环条目豁免与内层
 * 畸形容错。
 */
class PluginDynamicAuthValidationTest {

    private PluginBaseImpl pluginBase;

    @BeforeEach
    void setUp() {
        MockitoAnnotations.openMocks(this);
        pluginBase = new PluginBaseImpl();
        ReflectionTestUtils.setField(pluginBase, "pluginMapper", org.mockito.Mockito.mock(PluginMapper.class));
        ReflectionTestUtils.setField(pluginBase, "toolMapper", org.mockito.Mockito.mock(ToolMapper.class));
        ReflectionTestUtils.setField(pluginBase, "releaseVersionMapper",
            org.mockito.Mockito.mock(ReleaseVersionMapper.class));
        ReflectionTestUtils.setField(pluginBase, "mgObsService", org.mockito.Mockito.mock(MgObsService.class));
        ReflectionTestUtils.setField(pluginBase, "dependencyMapper",
            org.mockito.Mockito.mock(DependencyMapper.class));
        ReflectionTestUtils.setField(pluginBase, "encryptionAdapter",
            org.mockito.Mockito.mock(EncryptionAdapter.class));
        ReflectionTestUtils.setField(pluginBase, "mcpDomainId", "mcp-service");
        pluginBase.init();
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

    /** 内层对象 schema（Headers 参数所在），转成数组元素里的转义字符串形态。 */
    private static String innerSchemaJson(String paramName, String description) {
        String inner = "{\"type\":\"object\",\"properties\":{\""
            + paramName + "\":{\"type\":\"string\",\"location\":\"Headers\",\"description\":\""
            + description + "\"}}}";
        // 数组元素 input_schema 是内层 JSON 的字符串形态（再转义一层引号）
        return inner.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    @Test
    void testEntityArraySchemaParsesWithoutCrash() {
        // 存量插件行数组形态 + DYNAMIC + 无冲突 → 校验通过不抛错（此前对象
        // 解析数组直接抛 fastjson2 异常）
        String arraySchema = "[{\"tool_id\":\"t1\",\"input_schema\":\""
            + innerSchemaJson("Query", "查询参数") + "\"}]";
        assertDoesNotThrow(() ->
            pluginBase.validPluginDynamicAuthInfo(dynamicAuth("Authorization"), null, arraySchema));
    }

    @Test
    void testEntityArraySchemaConflictInInnerHeaderParamDetected() {
        // 内层 Headers 参数与动态头同名 → 冲突拒绝（数组形态下校验仍生效）
        String arraySchema = "[{\"tool_id\":\"t1\",\"input_schema\":\""
            + innerSchemaJson("Authorization", "已有工具头参数") + "\"}]";
        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> pluginBase.validPluginDynamicAuthInfo(dynamicAuth("Authorization"), null, arraySchema));
        assertEquals(StudioError.TOOL_INPUT_INVALID, ex.getErrorCode());
    }

    @Test
    void testRequestObjectSchemaConflictStillDetected() {
        // 请求体对象形态（旧行为保持）：Headers 参数同名 → 冲突
        String objectSchema = "{\"type\":\"object\",\"properties\":{\"Authorization\":"
            + "{\"type\":\"string\",\"location\":\"Headers\",\"description\":\"已有\"}}}";
        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> pluginBase.validPluginDynamicAuthInfo(dynamicAuth("Authorization"), null, objectSchema));
        assertEquals(StudioError.TOOL_INPUT_INVALID, ex.getErrorCode());
    }

    @Test
    void testEntityArraySchemaRoundtripEntryExempted() {
        // 回环条目（描述=动态鉴权追加标记 且名命中）剥离豁免——数组形态同样生效
        String arraySchema = "[{\"tool_id\":\"t1\",\"input_schema\":\""
            + innerSchemaJson("Authorization", IrAdapterService.DYNAMIC_AUTH_PARAM_DESC) + "\"}]";
        assertDoesNotThrow(() ->
            pluginBase.validPluginDynamicAuthInfo(dynamicAuth("Authorization"), null, arraySchema));
    }

    @Test
    void testEntityArraySchemaMalformedInnerSkipped() {
        // 单个工具内层 schema 畸形 → 告警跳过该条，不阻断整体校验
        String arraySchema = "[{\"tool_id\":\"t1\",\"input_schema\":\"not-a-json-object\"},"
            + "{\"tool_id\":\"t2\",\"input_schema\":\""
            + innerSchemaJson("Query", "正常条目") + "\"}]";
        assertDoesNotThrow(() ->
            pluginBase.validPluginDynamicAuthInfo(dynamicAuth("Authorization"), null, arraySchema));
    }

    @Test
    void testRequestFixedHeaderConflictDetected() {
        // requestInfo 固定头与动态头同名 → 冲突（既有行为保持）
        RequestInfo requestInfo = new RequestInfo();
        requestInfo.setHeaders(java.util.Collections.singletonMap("Authorization", "fixed-value"));
        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> pluginBase.validPluginDynamicAuthInfo(dynamicAuth("Authorization"),
                requestInfo, "{\"type\":\"object\",\"properties\":{}}"));
        assertEquals(StudioError.TOOL_INPUT_INVALID, ex.getErrorCode());
    }
}
