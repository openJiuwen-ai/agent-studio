/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */

package com.openjiuwen.studio.agent.common.utils;

import com.openjiuwen.studio.agent.common.exception.AgentStudioException;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.net.InetAddress;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

@ExtendWith(MockitoExtension.class)
class UrlCheckUtilsTest {

    private UrlCheckUtils urlCheckUtils;

    @BeforeEach
    void setUp() {
        urlCheckUtils = new UrlCheckUtils();
        ReflectionTestUtils.setField(urlCheckUtils, "enableUrlCheck", true);
        ReflectionTestUtils.setField(urlCheckUtils, "toolUrlBlackListStr", "blocked.com,10.0.0.1");
        ReflectionTestUtils.setField(urlCheckUtils, "toolUrlWhiteListStr", "allowed.com,192.168.1.1");
        ReflectionTestUtils.invokeMethod(urlCheckUtils, "init");
    }

    @Test
    void testCheckUrl_DisabledCheck() {
        ReflectionTestUtils.setField(urlCheckUtils, "enableUrlCheck", false);
        ReflectionTestUtils.invokeMethod(urlCheckUtils, "init");
        assertDoesNotThrow(() -> urlCheckUtils.checkUrl("project1", "http://any-url.com"));
    }

    @Test
    void testCheckUrl_EmptyUrl() {
        assertDoesNotThrow(() -> urlCheckUtils.checkUrl("project1", ""));
    }

    @Test
    void testCheckUrl_NullUrl() {
        assertDoesNotThrow(() -> urlCheckUtils.checkUrl("project1", null));
    }

    @Test
    void testCheckUrl_UrlWithPlaceholder() {
        assertDoesNotThrow(() -> urlCheckUtils.checkUrl("project1", "http://example.com/{id}"));
    }

    @Test
    void testCheckUrl_InvalidUrlSyntax() {
        assertThrows(AgentStudioException.class, () -> urlCheckUtils.checkUrl("project1", "://invalid"));
    }

    @Test
    void testCheckUrl_BlacklistedHost() {
        assertThrows(AgentStudioException.class, () -> urlCheckUtils.checkUrl("project1", "http://blocked.com/path"));
    }

    @Test
    void testCheckUrl_WhitelistedHost() {
        assertDoesNotThrow(() -> urlCheckUtils.checkUrl("project1", "http://allowed.com/path"));
    }

    @Test
    void testCheckUrlInWhiteList_DisabledCheck() {
        ReflectionTestUtils.setField(urlCheckUtils, "enableUrlCheck", false);
        assertDoesNotThrow(() -> urlCheckUtils.checkUrlInWhiteList("http://any-url.com"));
    }

    @Test
    void testCheckUrlInWhiteList_EmptyUrl() {
        assertDoesNotThrow(() -> urlCheckUtils.checkUrlInWhiteList(""));
    }

    @Test
    void testCheckUrlInWhiteList_InvalidUrlSyntax() {
        assertThrows(AgentStudioException.class, () -> urlCheckUtils.checkUrlInWhiteList("://invalid"));
    }

    @Test
    void testCheckUrlInWhiteList_WhitelistedHost() {
        assertDoesNotThrow(() -> urlCheckUtils.checkUrlInWhiteList("http://allowed.com/path"));
    }

    @Test
    void testCheckUrlInWhiteList_NonWhitelistedHost() {
        assertThrows(AgentStudioException.class, () -> urlCheckUtils.checkUrlInWhiteList("http://unknown-host-xyz123.com/path"));
    }

    @Test
    void testIsInternalIp_LoopbackAddress() throws Exception {
        InetAddress loopback = InetAddress.getByName("127.0.0.1");
        assertTrue(urlCheckUtils.isInternalIp(loopback, "project1"));
    }

    @Test
    void testIsInternalIp_SiteLocalAddress() throws Exception {
        InetAddress siteLocal = InetAddress.getByName("192.168.1.100");
        assertTrue(urlCheckUtils.isInternalIp(siteLocal, "project1"));
    }

    @Test
    void testIsInternalIp_LinkLocalAddress() throws Exception {
        InetAddress linkLocal = InetAddress.getByName("169.254.1.1");
        assertTrue(urlCheckUtils.isInternalIp(linkLocal, "project1"));
    }

    @Test
    void testIsInternalIp_AnyLocalAddress() throws Exception {
        InetAddress anyLocal = InetAddress.getByName("0.0.0.0");
        assertTrue(urlCheckUtils.isInternalIp(anyLocal, "project1"));
    }

    @Test
    void testCheckUrl_BlankBlackListConfig() {
        UrlCheckUtils utils = new UrlCheckUtils();
        ReflectionTestUtils.setField(utils, "enableUrlCheck", true);
        ReflectionTestUtils.setField(utils, "toolUrlBlackListStr", "");
        ReflectionTestUtils.setField(utils, "toolUrlWhiteListStr", "");
        ReflectionTestUtils.invokeMethod(utils, "init");
        assertDoesNotThrow(() -> utils.checkUrl("project1", "http://example.com"));
    }

    @Test
    void testCheckUrl_NullBlackListConfig() {
        UrlCheckUtils utils = new UrlCheckUtils();
        ReflectionTestUtils.setField(utils, "enableUrlCheck", true);
        ReflectionTestUtils.setField(utils, "toolUrlBlackListStr", null);
        ReflectionTestUtils.setField(utils, "toolUrlWhiteListStr", null);
        ReflectionTestUtils.invokeMethod(utils, "init");
        assertDoesNotThrow(() -> utils.checkUrl("project1", "http://example.com"));
    }

    // ---------- validateUrlSyntax ----------

    @Test
    void testValidateUrlSyntax_EmptyNull_pass() {
        assertDoesNotThrow(() -> urlCheckUtils.validateUrlSyntax(""));
        assertDoesNotThrow(() -> urlCheckUtils.validateUrlSyntax(null));
    }

    @Test
    void testValidateUrlSyntax_fullPlaceholder_pass() {
        // 整串占位符运行期解析，应放行（形态合法与否由 validateEnvVarPlaceholders 判定）
        assertDoesNotThrow(() -> urlCheckUtils.validateUrlSyntax("${_env.plugin_url_params.MY_VAR}"));
        assertDoesNotThrow(() -> urlCheckUtils.validateUrlSyntax("{}"));
        // 整串 ${...} 但形态非法：URL 语法层放行（是占位符形状，不是 URL 形状），占位符语法由 validateEnvVarPlaceholders 判错
        assertDoesNotThrow(() -> urlCheckUtils.validateUrlSyntax("${evil.var}"));
    }

    @Test
    void testValidateUrlSyntax_httpHttps_pass() {
        assertDoesNotThrow(() -> urlCheckUtils.validateUrlSyntax("http://example.com/v1/chat"));
        assertDoesNotThrow(() -> urlCheckUtils.validateUrlSyntax("https://example.com/v1/chat"));
        assertDoesNotThrow(() -> urlCheckUtils.validateUrlSyntax("https://example.com:8080/path"));
    }

    @Test
    void testValidateUrlSyntax_inlinePlaceholder_throws() {
        // URL 中嵌任何 ${...} 子串（即便是合法 _env.plugin_url_params 形态）均为非法，与前端 USER_URL_PATTERN=[^{}\s]+ 对齐
        assertThrows(AgentStudioException.class, () ->
            urlCheckUtils.validateUrlSyntax("https://${_env.plugin_url_params.MY_VAR}/v1/chat"));
        assertThrows(AgentStudioException.class, () ->
            urlCheckUtils.validateUrlSyntax("https://example.com/${_env.plugin_url_params.VAR}/v1"));
        assertThrows(AgentStudioException.class, () -> urlCheckUtils.validateUrlSyntax("https://example.com/{id}"));
    }

    @Test
    void testValidateUrlSyntax_notAurl_throws() {
        assertThrows(AgentStudioException.class, () -> urlCheckUtils.validateUrlSyntax("not-a-url"));
    }

    @Test
    void testValidateUrlSyntax_ftpScheme_throws() {
        assertThrows(AgentStudioException.class, () -> urlCheckUtils.validateUrlSyntax("ftp://evil.com/file"));
    }

    @Test
    void testValidateUrlSyntax_noScheme_throws() {
        assertThrows(AgentStudioException.class, () -> urlCheckUtils.validateUrlSyntax("example.com/path"));
    }

    @Test
    void testValidateUrlSyntax_noHost_throws() {
        assertThrows(AgentStudioException.class, () -> urlCheckUtils.validateUrlSyntax("http:///path"));
    }

    @Test
    void testValidateUrlSyntax_bareCurly_throws() {
        // 未闭合/裸花括号应拒绝
        assertThrows(AgentStudioException.class, () -> urlCheckUtils.validateUrlSyntax("https://example.com/{id"));
        assertThrows(AgentStudioException.class, () -> urlCheckUtils.validateUrlSyntax("https://example.com/foo}bar"));
    }

    // ---------- validateEnvVarPlaceholders ----------

    @Test
    void testValidateEnvVarPlaceholders_emptyNull_pass() {
        assertDoesNotThrow(() -> urlCheckUtils.validateEnvVarPlaceholders(""));
        assertDoesNotThrow(() -> urlCheckUtils.validateEnvVarPlaceholders(null));
    }

    @Test
    void testValidateEnvVarPlaceholders_plainUrl_pass() {
        assertDoesNotThrow(() -> urlCheckUtils.validateEnvVarPlaceholders("https://example.com/v1/chat"));
    }

    @Test
    void testValidateEnvVarPlaceholders_fullValidPlaceholder_pass() {
        assertDoesNotThrow(() -> urlCheckUtils.validateEnvVarPlaceholders("${_env.plugin_url_params.MY_VAR}"));
        assertDoesNotThrow(() -> urlCheckUtils.validateEnvVarPlaceholders("{}"));
    }

    @Test
    void testValidateEnvVarPlaceholders_fullInvalidPlaceholder_throws() {
        // 整串 ${...} 但形态非法
        assertThrows(AgentStudioException.class, () -> urlCheckUtils.validateEnvVarPlaceholders("${evil.var}"));
        assertThrows(AgentStudioException.class, () -> urlCheckUtils.validateEnvVarPlaceholders("${a.b}"));
        // 用户形态 {VAR}：应在提交前由前端转换为后端格式，后端拒绝
        assertThrows(AgentStudioException.class, () -> urlCheckUtils.validateEnvVarPlaceholders("{MY_VAR}"));
    }

    @Test
    void testValidateEnvVarPlaceholders_inlinePlaceholderOrBraces_throws() {
        // 内联 ${...} 或裸 {/} 一律拒绝（创建页不允许，导入侧对齐）
        assertThrows(AgentStudioException.class, () ->
            urlCheckUtils.validateEnvVarPlaceholders("https://${_env.plugin_url_params.VAR}/v"));
        assertThrows(AgentStudioException.class, () ->
            urlCheckUtils.validateEnvVarPlaceholders("https://example.com/${x"));
        assertThrows(AgentStudioException.class, () ->
            urlCheckUtils.validateEnvVarPlaceholders("https://example.com/foo}bar"));
    }
}
