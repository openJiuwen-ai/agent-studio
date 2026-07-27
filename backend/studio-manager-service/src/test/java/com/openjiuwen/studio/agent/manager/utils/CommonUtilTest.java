/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.utils;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mockStatic;

import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.dto.PageInfoV2;
import com.openjiuwen.studio.agent.manager.enums.NameSplitInfix;

import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.http.HttpHeaders;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@MockitoSettings(strictness = Strictness.LENIENT)
class CommonUtilTest {

    @Test
    void testGenUUID() {
        String uuid = CommonUtil.genUUID();
        assertNotNull(uuid);
        assertTrue(uuid.contains("-"));
        assertEquals(36, uuid.length());
    }

    @Test
    void testGetUUID() {
        String uuid = CommonUtil.getUUID();
        assertNotNull(uuid);
        assertFalse(uuid.contains("-"));
        assertEquals(32, uuid.length());
    }

    @Test
    void testIsValidUUid_Valid() {
        assertTrue(CommonUtil.isValidUUid("550e8400-e29b-41d4-a716-446655440000"));
    }

    @Test
    void testIsValidUUid_Invalid() {
        assertFalse(CommonUtil.isValidUUid("not-a-uuid"));
    }

    @Test
    void testIsValidUUid_Null() {
        assertThrows(NullPointerException.class, () -> CommonUtil.isValidUUid(null));
    }

    @Test
    void testGetDeptCode() {
        assertEquals("system", CommonUtil.getDeptCode());
    }

    @Test
    void testGetTenantId() {
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestUserDomainId).thenReturn("tenant-123");
            assertEquals("tenant-123", CommonUtil.getTenantId());
        }
    }

    @Test
    void testGetUserId() {
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("user-456");
            assertEquals("user-456", CommonUtil.getUserId());
        }
    }

    @Test
    void testSplitName() {
        String result = CommonUtil.splitName("myConnector_connect_split12345", NameSplitInfix.PRIVATE_CONNECTOR);
        assertEquals("myConnector_", result);
    }

    @Test
    void testSplitName_NoInfix() {
        String result = CommonUtil.splitName("simpleName", NameSplitInfix.PRIVATE_CONNECTOR);
        assertEquals("simpleName", result);
    }

    @Test
    void testSpliceName() {
        String result = CommonUtil.spliceName("myService", NameSplitInfix.PRIVATE_CONNECTOR);
        assertTrue(result.startsWith("myServiceconnect_split"));
        assertEquals("myService".length() + "connect_split".length() + 6, result.length());
    }

    @Test
    void testSplitFunctionExpression() {
        String result = CommonUtil.splitFunctionExpression("myFuncfunction_split123456(arg1)");
        assertEquals("myFunc(arg1)", result);
    }

    @Test
    void testGetExpireTime() {
        String result = CommonUtil.getExpireTime(60000L);
        assertNotNull(result);
        assertTrue(result.matches("\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}"));
    }

    @Test
    void testIsIntegerAndLessThan10_Valid() {
        assertTrue(CommonUtil.isIntegerAndLessThan10("5"));
    }

    @Test
    void testIsIntegerAndLessThan10_Ten() {
        assertTrue(CommonUtil.isIntegerAndLessThan10("10"));
    }

    @Test
    void testIsIntegerAndLessThan10_Eleven() {
        assertFalse(CommonUtil.isIntegerAndLessThan10("11"));
    }

    @Test
    void testIsIntegerAndLessThan10_Negative() {
        assertTrue(CommonUtil.isIntegerAndLessThan10("-5"));
    }

    @Test
    void testIsIntegerAndLessThan10_NotInteger() {
        assertFalse(CommonUtil.isIntegerAndLessThan10("abc"));
    }

    @Test
    void testIsIntegerAndLessThan10_Null() {
        assertFalse(CommonUtil.isIntegerAndLessThan10(null));
    }

    @Test
    void testValidatePageInfo_Null() {
        assertThrows(AgentStudioException.class, () -> CommonUtil.validatePageInfo(null));
    }

    @Test
    void testValidatePageInfo_NegativeLimit() {
        PageInfoV2 pageInfo = new PageInfoV2();
        pageInfo.setLimit(-1);
        pageInfo.setOffset(0);
        assertThrows(AgentStudioException.class, () -> CommonUtil.validatePageInfo(pageInfo));
    }

    @Test
    void testValidatePageInfo_NegativeOffset() {
        PageInfoV2 pageInfo = new PageInfoV2();
        pageInfo.setLimit(10);
        pageInfo.setOffset(-1);
        assertThrows(AgentStudioException.class, () -> CommonUtil.validatePageInfo(pageInfo));
    }

    @Test
    void testValidatePageInfo_Valid() {
        PageInfoV2 pageInfo = new PageInfoV2();
        pageInfo.setLimit(10);
        pageInfo.setOffset(0);
        assertDoesNotThrow(() -> CommonUtil.validatePageInfo(pageInfo));
    }

    @Test
    void testValidateMcpConfigFormat_Valid() {
        assertDoesNotThrow(() -> CommonUtil.validateMcpConfigFormat("{\"key\":\"value\"}"));
    }

    @Test
    void testValidateMcpConfigFormat_Invalid() {
        assertThrows(AgentStudioException.class, () -> CommonUtil.validateMcpConfigFormat("not-json"));
    }

    @Test
    void testGetRawQueryString_Valid() {
        String result = CommonUtil.getRawQueryString("http://example.com/path?key=value&foo=bar");
        assertEquals("key=value&foo=bar", result);
    }

    @Test
    void testGetRawQueryString_NoQuery() {
        String result = CommonUtil.getRawQueryString("http://example.com/path");
        assertNull(result);
    }

    @Test
    void testGetRawQueryString_Null() {
        assertNull(CommonUtil.getRawQueryString(null));
    }

    @Test
    void testGetRawQueryString_Empty() {
        assertNull(CommonUtil.getRawQueryString(""));
    }

    @Test
    void testGetRawQueryString_Blank() {
        assertNull(CommonUtil.getRawQueryString("   "));
    }

    @Test
    void testMaskUrlCredentials_WithCredentials() {
        String input = "Error at http://user:password@127.0.0.1:8080/api";
        String result = CommonUtil.maskUrlCredentials(input);
        assertEquals("Error at http://******@127.0.0.1:8080/api", result);
    }

    @Test
    void testMaskUrlCredentials_NoCredentials() {
        String input = "Error at http://127.0.0.1:8080/api";
        String result = CommonUtil.maskUrlCredentials(input);
        assertEquals(input, result);
    }

    @Test
    void testMaskUrlCredentials_Blank() {
        assertEquals("", CommonUtil.maskUrlCredentials(""));
    }

    @Test
    void testMaskUrlCredentials_Null() {
        assertNull(CommonUtil.maskUrlCredentials(null));
    }

    @Test
    void testList2String() {
        String result = CommonUtil.List2String(List.of("a", "b", "c"));
        assertEquals("[\"a\", \"b\", \"c\"]", result);
    }

    @Test
    void testList2String_Empty() {
        String result = CommonUtil.List2String(List.of());
        assertEquals("[]", result);
    }

    @Test
    void testParseMcpConfigHeaderInfo_WithHeaders() {
        String config = "{\"headers\":{\"X-Key\":\"val1\"},\"nested\":{\"headers\":{\"X-Nested\":\"val2\"}}}";
        Map<String, String> result = CommonUtil.parseMcpConfigHeaderInfo(config);
        assertEquals("val1", result.get("X-Key"));
        assertEquals("val2", result.get("X-Nested"));
    }

    @Test
    void testParseMcpConfigHeaderInfo_NoHeaders() {
        String config = "{\"key\":\"value\"}";
        Map<String, String> result = CommonUtil.parseMcpConfigHeaderInfo(config);
        assertTrue(result.isEmpty());
    }

    @Test
    void testParseMcpConfigHeaderInfo_DepthLimit() {
        Map<String, String> headers = new HashMap<>();
        Map<String, Object> deepMap = new HashMap<>();
        deepMap.put("headers", Map.of("X-Deep", "val"));
        CommonUtil.parseMcpConfigHeaderInfo(deepMap, headers, 10);
        assertTrue(headers.isEmpty());
    }

    @Test
    void testGenerateHeaders() {
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestUserDomainId).thenReturn("tenant-1");
            HttpHeaders headers = CommonUtil.generateHeaders();
            assertEquals("tenant-1", headers.getFirst("tenant-id-w"));
            assertEquals("system", headers.getFirst("dept-code"));
            assertEquals("application/json;charset=UTF-8", headers.getFirst("Content-Type"));
        }
    }

    @Test
    void testGetResourceContent_Empty() {
        assertEquals("", CommonUtil.getResourceContent(""));
    }

    @Test
    void testGetResourceContent_Null() {
        assertEquals("", CommonUtil.getResourceContent(null));
    }

    @Test
    void testGetResourceContent_NotFound() {
        assertEquals("", CommonUtil.getResourceContent("nonexistent-file.txt"));
    }

    @Test
    void testParseUrlFromMcpConfig_WithUrl() {
        com.alibaba.fastjson2.JSONObject config = new com.alibaba.fastjson2.JSONObject();
        config.put("url", "http://example.com/path");
        String result = CommonUtil.parseUrlFromMcpConfig(config, 0);
        assertEquals("http://example.com/path", result);
    }

    @Test
    void testParseUrlFromMcpConfig_UrlWithOnlyIpPort() {
        com.alibaba.fastjson2.JSONObject config = new com.alibaba.fastjson2.JSONObject();
        config.put("url", "http://10.0.0.1:8080");
        String result = CommonUtil.parseUrlFromMcpConfig(config, 0);
        assertEquals("http://10.0.0.1:8080/mcp", result);
    }

    @Test
    void testParseUrlFromMcpConfig_UrlWithOnlyIpPortAndQuery() {
        com.alibaba.fastjson2.JSONObject config = new com.alibaba.fastjson2.JSONObject();
        config.put("url", "http://10.0.0.1:8080?token=abc");
        String result = CommonUtil.parseUrlFromMcpConfig(config, 0);
        assertEquals("http://10.0.0.1:8080/mcp?token=abc", result);
    }

    @Test
    void testParseUrlFromMcpConfig_UrlWithCustomPath() {
        com.alibaba.fastjson2.JSONObject config = new com.alibaba.fastjson2.JSONObject();
        config.put("url", "http://10.0.0.1:8080/custom/path?token=abc");
        String result = CommonUtil.parseUrlFromMcpConfig(config, 0);
        assertEquals("http://10.0.0.1:8080/custom/path?token=abc", result);
    }

    @Test
    void testParseUrlFromMcpConfig_NestedUrl() {
        com.alibaba.fastjson2.JSONObject inner = new com.alibaba.fastjson2.JSONObject();
        inner.put("url", "http://nested.com");
        com.alibaba.fastjson2.JSONObject config = new com.alibaba.fastjson2.JSONObject();
        config.put("server", inner);
        String result = CommonUtil.parseUrlFromMcpConfig(config, 0);
        assertEquals("http://nested.com", result);
    }

    @Test
    void testParseUrlFromMcpConfig_DepthExceeded() {
        com.alibaba.fastjson2.JSONObject config = new com.alibaba.fastjson2.JSONObject();
        config.put("url", "http://example.com");
        String result = CommonUtil.parseUrlFromMcpConfig(config, 6);
        assertEquals("", result);
    }

    @Test
    void testCheckHostValid_Disabled() {
        assertDoesNotThrow(() -> CommonUtil.checkHostValid(false, "anything", "127.0.0.1"));
    }

    @Test
    void testReplaceConnectorName() {
        Map<String, Object> swagger = new HashMap<>();
        Map<String, Object> info = new HashMap<>();
        info.put("title", "oldName");
        swagger.put("info", info);
        CommonUtil.replaceConnectorName(swagger, "newName");
        Map<?, ?> resultInfo = (Map<?, ?>) swagger.get("info");
        assertEquals("newName", resultInfo.get("title"));
    }

    @Test
    void testConvert_NullSource() throws Exception {
        assertNull(CommonUtil.convert(null, Object.class, Map.of()));
    }

    @Test
    void testValidateProjectId() {
        assertDoesNotThrow(() -> CommonUtil.validateProjectId("any-id"));
    }

    @Test
    void testValidateWorkspaceId() {
        assertDoesNotThrow(() -> CommonUtil.validateWorkspaceId("any-id"));
    }

    @Test
    void testValidateProjectAndWorkspaceId() {
        assertDoesNotThrow(() -> CommonUtil.validateProjectAndWorkspaceId("proj", "ws"));
    }
}
