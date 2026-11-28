/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.agentbase.utils;

import com.openjiuwen.studio.agent.agentbase.config.SSRFStaticConfig;
import com.openjiuwen.studio.agent.foundation.base.exception.AgentBaseException;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

/**
 * SSRFValidator 协议白名单与 SSRF 总开关解耦的回归用例。
 *
 * <p>覆盖三类回归点：
 * <ul>
 *   <li>knowledge.ssrf.validation.enabled=false 时仍拒绝 file://、ftp://、gopher:// 等非白名单协议；</li>
 *   <li>开关关闭时不再追加 URI 严格解析要求，含非 ASCII/空格/花括号的存量 endpoint 不被误拒；</li>
 *   <li>协议比较忽略大小写与首尾空白，白名单配置为空时回退 http,https。</li>
 * </ul>
 */
class SSRFValidatorTest {

    private static final String FILE_URL = "file:///etc/passwd";

    private static final String FTP_URL = "ftp://kb.example.com/dataset";

    private static void configure(boolean validationEnabled, String... allowedProtocols) {
        SSRFStaticConfig config = new SSRFStaticConfig();
        config.setSsrfValidationEnabled(validationEnabled);
        Set<String> protocols = new LinkedHashSet<>(Arrays.asList(allowedProtocols));
        config.setAllowedProtocols(protocols);
        config.setAllowedInternalDomains(Collections.emptySet());
        config.setBlockedInternalDomains(Collections.emptySet());
    }

    @AfterEach
    void resetStaticConfig() {
        // 恢复 SSRFStaticConfig 的字段初始值（false + 空集合），避免静态状态污染同 JVM 的其他用例。
        configure(false);
    }

    @Test
    void testValidationDisabledStillRejectsNonHttpProtocols() {
        configure(false, "http", "https");

        assertThrows(AgentBaseException.class, () -> SSRFValidator.checkSSRF(FILE_URL));
        assertThrows(AgentBaseException.class, () -> SSRFValidator.checkSSRF(FTP_URL));
        assertThrows(AgentBaseException.class, () -> SSRFValidator.checkSSRF("gopher://kb.example.com:70/1"));
        assertThrows(AgentBaseException.class, () -> SSRFValidator.checkSSRF("javascript:alert(1)"));
    }

    @Test
    void testValidationDisabledAcceptsHttpAndHttps() {
        configure(false, "http", "https");

        assertDoesNotThrow(() -> SSRFValidator.checkSSRF("https://kb.example.com/v1/knowledge"));
        assertDoesNotThrow(() -> SSRFValidator.checkSSRF("http://kb.example.com/oceanconnect"));
    }

    @Test
    void testProtocolComparisonIgnoresCaseAndSurroundingWhitespace() {
        configure(false, " HTTPS ", "HTTP");

        assertDoesNotThrow(() -> SSRFValidator.checkSSRF("https://kb.example.com/v1"));
        assertDoesNotThrow(() -> SSRFValidator.checkSSRF("HTTP://kb.example.com/v1"));
        assertThrows(AgentBaseException.class, () -> SSRFValidator.checkSSRF(FTP_URL));
    }

    @Test
    void testValidationDisabledToleratesLegacyUrlCharacters() {
        configure(false, "http", "https");

        // 非 ASCII 域名/路径、未编码空格、未编码花括号：HTTP 客户端可容忍，关闭开关时不应新增语法拒绝。
        assertDoesNotThrow(() -> SSRFValidator.checkSSRF("https://知识库.example.com/数据集/路径?q=1"));
        assertDoesNotThrow(() -> SSRFValidator.checkSSRF("https://kb.example.com/a b/c"));
        assertDoesNotThrow(() -> SSRFValidator.checkSSRF("https://kb.example.com/{tenant}/v1"));
    }

    @Test
    void testValidationDisabledRejectsUrlWithoutScheme() {
        configure(false, "http", "https");

        assertThrows(AgentBaseException.class, () -> SSRFValidator.checkSSRF("example.com/path"));
        assertThrows(AgentBaseException.class, () -> SSRFValidator.checkSSRF("//example.com/path"));
        assertThrows(AgentBaseException.class, () -> SSRFValidator.checkSSRF("/relative/path"));
        assertThrows(AgentBaseException.class, () -> SSRFValidator.checkSSRF("://broken"));
    }

    @Test
    void testBlankUrlIsAccepted() {
        configure(false, "http", "https");

        assertDoesNotThrow(() -> SSRFValidator.checkSSRF(null));
        assertDoesNotThrow(() -> SSRFValidator.checkSSRF(""));
        assertDoesNotThrow(() -> SSRFValidator.checkSSRF("   "));
    }

    @Test
    void testEmptyAllowedProtocolsFallsBackToHttpAndHttps() {
        configure(false);

        assertDoesNotThrow(() -> SSRFValidator.checkSSRF("https://kb.example.com/v1"));
        assertThrows(AgentBaseException.class, () -> SSRFValidator.checkSSRF(FTP_URL));
    }

    @Test
    void testValidationEnabledRejectsInternalAddresses() {
        configure(true, "http", "https");

        assertThrows(AgentBaseException.class, () -> SSRFValidator.checkSSRF("http://127.0.0.1/v1"));
        assertThrows(AgentBaseException.class, () -> SSRFValidator.checkSSRF("http://10.1.2.3/v1"));
        assertThrows(AgentBaseException.class, () -> SSRFValidator.checkSSRF("http://192.168.1.10/v1"));
        assertThrows(AgentBaseException.class, () -> SSRFValidator.checkSSRF("http://169.254.169.254/latest"));
        assertThrows(AgentBaseException.class, () -> SSRFValidator.checkSSRF("http://0.0.0.0/v1"));
    }

    @Test
    void testValidationEnabledAcceptsPublicAddressProtocol() {
        configure(true, "http", "https");

        // 公网 IP 字面量，不做 DNS 解析即可判定
        assertDoesNotThrow(() -> SSRFValidator.checkSSRF("http://8.8.8.8/v1"));
    }

    @Test
    void testValidationEnabledStillRequiresStrictUriSyntax() {
        configure(true, "http", "https");

        // 开关开启时沿用原有语义：需要严格解析出 host 才能做 IP 判定，解析失败即拒绝
        assertThrows(AgentBaseException.class, () -> SSRFValidator.checkSSRF("http://exa mple.com/path"));
    }

    @Test
    void testMaskUrlHidesUserInfoAndQueryCredentials() {
        String masked = maskUrl("https://kb_user:S3cretPwd@10.1.2.3:8080/v1/chat?access_key=AK123&signature=deadbeef");

        // userinfo 整体替换为 ***，查询串整体替换为 ?***，口令与签名都不应出现在日志里
        assertEquals("https://***@10.1.2.3:8080/v1/chat?***", masked);
        assertFalse(masked.contains("S3cretPwd"));
        assertFalse(masked.contains("kb_user"));
        assertFalse(masked.contains("AK123"));
    }

    @Test
    void testMaskUrlHidesUserInfoWhosePasswordContainsAtSign() {
        // 口令里带 '@' 时，贪婪匹配会回溯到 authority 内最后一个 '@'，不会残留半截口令
        assertEquals("https://***@kb.example.com/v1", maskUrl("https://user:p@ss@kb.example.com/v1"));
    }

    @Test
    void testMaskUrlHidesUserInfoWithoutPassword() {
        assertEquals("https://***@kb.example.com/v1", maskUrl("https://onlyuser@kb.example.com/v1"));
    }

    @Test
    void testMaskUrlKeepsAtSignInsideQuery() {
        // 查询串里的邮箱不是 userinfo，不能把 host/path 一起吃掉
        assertEquals("https://kb.example.com/path?***", maskUrl("https://kb.example.com/path?email=a@b.com"));
    }

    @Test
    void testMaskUrlHidesUserInfoWithoutScheme() {
        // 无 scheme 的地址会被协议白名单直接拒绝，拒绝日志也不能带出 userinfo
        assertEquals("***@10.1.2.3/v1", maskUrl("user:pass@10.1.2.3/v1"));
    }

    @Test
    void testMaskUrlWithoutUserInfoOnlyRedactsQuery() {
        assertEquals("https://kb.example.com/path?***", maskUrl("https://kb.example.com/path?token=t"));
        assertEquals("https://kb.example.com/path", maskUrl("https://kb.example.com/path"));
        assertNull(maskUrl((String) null));
    }

    @Test
    void testInternalAddressRejectionCoversUserInfoUrls() {
        configure(true, "http", "https");

        // 触发拒绝即会走 maskUrl 记日志，确认带 userinfo 的地址同样被拦
        assertThrows(AgentBaseException.class, () -> SSRFValidator.checkSSRF("http://user:pass@10.1.2.3/v1"));
    }

    private static String maskUrl(String url) {
        return ReflectionTestUtils.invokeMethod(SSRFValidator.class, "maskUrl", url);
    }
}
