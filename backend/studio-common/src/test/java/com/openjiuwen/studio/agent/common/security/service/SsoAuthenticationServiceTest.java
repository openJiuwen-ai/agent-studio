/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.security.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.verify;

import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;
import com.openjiuwen.studio.agent.common.security.properties.AuthProperties;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;

import java.lang.reflect.Field;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

/**
 * SsoAuthenticationService 单元测试
 */
@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
public class SsoAuthenticationServiceTest {

    @Mock
    private RestTemplate restTemplate;

    private SsoAuthenticationService service;

    private AuthProperties authProperties;

    private static final String SSO_URL = "http://sso.example.com/validate";

    @BeforeEach
    void setUp() {
        authProperties = new AuthProperties();
        AuthProperties.SsoConfig ssoConfig = new AuthProperties.SsoConfig();
        ssoConfig.setValidateUrl(SSO_URL);
        ssoConfig.setHeader("X-Auth-Token");
        authProperties.setSso(ssoConfig);

        AuthProperties.UserInfoConfig.ClaimsConfig claimsConfig = new AuthProperties.UserInfoConfig.ClaimsConfig();
        claimsConfig.setUserId("user_id");
        claimsConfig.setUserName("user_name");
        claimsConfig.setDomainId("domain_id");
        claimsConfig.setProjectId("project_id");
        AuthProperties.UserInfoConfig userInfoConfig = new AuthProperties.UserInfoConfig();
        userInfoConfig.setClaims(claimsConfig);
        authProperties.setUserInfo(userInfoConfig);

        service = new SsoAuthenticationService(authProperties);
        ReflectionTestUtils.setField(service, "restTemplate", restTemplate);
    }

    private Map<String, Object> buildSsoResponse(String userId, String userName, String domainId, String projectId) {
        Map<String, Object> map = new HashMap<>();
        map.put("user_id", userId);
        map.put("user_name", userName);
        map.put("domain_id", domainId);
        map.put("project_id", projectId);
        return map;
    }

    @SuppressWarnings("unchecked")
    private void mockExchangeReturn(Map<String, Object> body, HttpStatus status) {
        ResponseEntity<Map<String, Object>> responseEntity = new ResponseEntity<>(body, status);
        doReturn(responseEntity).when(restTemplate).exchange(
            eq(SSO_URL),
            eq(HttpMethod.POST),
            any(HttpEntity.class),
            any(ParameterizedTypeReference.class)
        );
    }

    @SuppressWarnings("unchecked")
    private void mockExchangeThrow(Exception e) {
        doThrow(e).when(restTemplate).exchange(
            eq(SSO_URL),
            eq(HttpMethod.POST),
            any(HttpEntity.class),
            any(ParameterizedTypeReference.class)
        );
    }

    @Test
    void authenticate_success_shouldReturnUserInfo() {
        mockExchangeReturn(buildSsoResponse("user1", "Test User", "domain1", "proj1"), HttpStatus.OK);

        Optional<SimpleUser> result = service.authenticate("valid-token");

        assertTrue(result.isPresent());
        assertEquals("user1", result.get().getUserId());
        assertEquals("Test User", result.get().getUserName());
        assertEquals("domain1", result.get().getDomainId());
        assertEquals("proj1", result.get().getProjectId());
    }

    @Test
    void authenticate_2xxStatus_shouldReturnUserInfo() {
        mockExchangeReturn(buildSsoResponse("user2", "User Two", "domain2", "proj2"), HttpStatus.CREATED);

        Optional<SimpleUser> result = service.authenticate("valid-token");

        assertTrue(result.isPresent());
        assertEquals("user2", result.get().getUserId());
    }

    @Test
    void authenticate_nullBody_shouldReturnEmpty() {
        mockExchangeReturn(null, HttpStatus.OK);

        Optional<SimpleUser> result = service.authenticate("valid-token");

        assertTrue(result.isEmpty());
    }

    @Test
    void authenticate_httpClientError401_shouldReturnEmpty() {
        mockExchangeThrow(new HttpClientErrorException(HttpStatus.UNAUTHORIZED));

        Optional<SimpleUser> result = service.authenticate("expired-token");

        assertTrue(result.isEmpty());
    }

    @Test
    void authenticate_httpClientError403_shouldReturnEmpty() {
        mockExchangeThrow(new HttpClientErrorException(HttpStatus.FORBIDDEN));

        Optional<SimpleUser> result = service.authenticate("forbidden-token");

        assertTrue(result.isEmpty());
    }

    @Test
    void authenticate_generalException_shouldReturnEmpty() {
        mockExchangeThrow(new RuntimeException("Connection refused"));

        Optional<SimpleUser> result = service.authenticate("error-token");

        assertTrue(result.isEmpty());
    }

    @Test
    void authenticate_emptyFields_shouldUseDefaults() {
        Map<String, Object> ssoResponse = new HashMap<>();
        ssoResponse.put("user_id", "user1");
        ssoResponse.put("user_name", null);
        ssoResponse.put("domain_id", "");
        ssoResponse.put("project_id", "  ");
        mockExchangeReturn(ssoResponse, HttpStatus.OK);

        Optional<SimpleUser> result = service.authenticate("valid-token");

        assertTrue(result.isPresent());
        assertEquals("user1", result.get().getUserId());
        assertEquals("unknown", result.get().getUserName());
        assertEquals("0", result.get().getDomainId());
        assertEquals("0", result.get().getProjectId());
    }

    @Test
    void authenticate_allFieldsEmpty_shouldUseAllDefaults() {
        Map<String, Object> ssoResponse = new HashMap<>();
        ssoResponse.put("user_id", "");
        ssoResponse.put("user_name", null);
        ssoResponse.put("domain_id", "");
        ssoResponse.put("project_id", null);
        mockExchangeReturn(ssoResponse, HttpStatus.OK);

        Optional<SimpleUser> result = service.authenticate("valid-token");

        assertTrue(result.isPresent());
        assertEquals("0", result.get().getDomainId());
        assertEquals("0", result.get().getProjectId());
        assertEquals("unknown", result.get().getUserName());
    }

    @Test
    void authenticate_customDefaults_shouldUseCustomDefaults() {
        AuthProperties.UserInfoConfig.DefaultsConfig defaultsConfig = new AuthProperties.UserInfoConfig.DefaultsConfig();
        defaultsConfig.setDomainId("custom-domain");
        defaultsConfig.setProjectId("custom-project");
        AuthProperties.UserInfoConfig userInfoConfig = authProperties.getUserInfo();
        userInfoConfig.setDefaults(defaultsConfig);

        Map<String, Object> ssoResponse = new HashMap<>();
        ssoResponse.put("user_id", "user1");
        ssoResponse.put("user_name", "");
        ssoResponse.put("domain_id", "");
        ssoResponse.put("project_id", "");
        mockExchangeReturn(ssoResponse, HttpStatus.OK);

        Optional<SimpleUser> result = service.authenticate("valid-token");

        assertTrue(result.isPresent());
        assertEquals("custom-domain", result.get().getDomainId());
        assertEquals("custom-project", result.get().getProjectId());
        assertEquals("unknown", result.get().getUserName());
    }

    @Test
    void authenticate_customClaims_shouldMapCustomFields() {
        AuthProperties.UserInfoConfig.ClaimsConfig claimsConfig = new AuthProperties.UserInfoConfig.ClaimsConfig();
        claimsConfig.setUserId("uid");
        claimsConfig.setUserName("displayName");
        claimsConfig.setDomainId("tenant");
        claimsConfig.setProjectId("group");
        AuthProperties.UserInfoConfig userInfoConfig = new AuthProperties.UserInfoConfig();
        userInfoConfig.setClaims(claimsConfig);
        authProperties.setUserInfo(userInfoConfig);

        Map<String, Object> ssoResponse = new HashMap<>();
        ssoResponse.put("uid", "custom-user");
        ssoResponse.put("displayName", "Custom Name");
        ssoResponse.put("tenant", "custom-tenant");
        ssoResponse.put("group", "custom-group");
        mockExchangeReturn(ssoResponse, HttpStatus.OK);

        Optional<SimpleUser> result = service.authenticate("valid-token");

        assertTrue(result.isPresent());
        assertEquals("custom-user", result.get().getUserId());
        assertEquals("Custom Name", result.get().getUserName());
        assertEquals("custom-tenant", result.get().getDomainId());
        assertEquals("custom-group", result.get().getProjectId());
    }

    @Test
    void authenticate_numericClaimValues_shouldConvertToString() {
        Map<String, Object> ssoResponse = new HashMap<>();
        ssoResponse.put("user_id", 12345);
        ssoResponse.put("user_name", "Test User");
        ssoResponse.put("domain_id", 100);
        ssoResponse.put("project_id", 200);
        mockExchangeReturn(ssoResponse, HttpStatus.OK);

        Optional<SimpleUser> result = service.authenticate("valid-token");

        assertTrue(result.isPresent());
        assertEquals("12345", result.get().getUserId());
        assertEquals("100", result.get().getDomainId());
        assertEquals("200", result.get().getProjectId());
    }

    @Test
    void authenticate_nestedResponse_shouldExtractByDotPath() {
        AuthProperties.UserInfoConfig.ClaimsConfig claimsConfig = new AuthProperties.UserInfoConfig.ClaimsConfig();
        claimsConfig.setUserId("result.user_id");
        claimsConfig.setUserName("result.user_name");
        claimsConfig.setDomainId("result.domain_id");
        claimsConfig.setProjectId("result.project_id");
        authProperties.getUserInfo().setClaims(claimsConfig);

        Map<String, Object> nested = new HashMap<>();
        nested.put("user_id", "nested-user");
        nested.put("user_name", "Nested User");
        nested.put("domain_id", "nested-domain");
        nested.put("project_id", "nested-project");
        Map<String, Object> ssoResponse = new HashMap<>();
        ssoResponse.put("code", "0");
        ssoResponse.put("result", nested);
        mockExchangeReturn(ssoResponse, HttpStatus.OK);

        Optional<SimpleUser> result = service.authenticate("valid-token");

        assertTrue(result.isPresent());
        assertEquals("nested-user", result.get().getUserId());
        assertEquals("Nested User", result.get().getUserName());
        assertEquals("nested-domain", result.get().getDomainId());
        assertEquals("nested-project", result.get().getProjectId());
    }

    @Test
    void authenticate_multiLevelNestedResponse_shouldExtractByDotPath() {
        AuthProperties.UserInfoConfig.ClaimsConfig claimsConfig = new AuthProperties.UserInfoConfig.ClaimsConfig();
        claimsConfig.setUserId("data.user.info.user_id");
        claimsConfig.setUserName("data.user.info.user_name");
        authProperties.getUserInfo().setClaims(claimsConfig);

        Map<String, Object> info = new HashMap<>();
        info.put("user_id", "deep-user");
        info.put("user_name", "Deep User");
        Map<String, Object> user = new HashMap<>();
        user.put("info", info);
        Map<String, Object> data = new HashMap<>();
        data.put("user", user);
        Map<String, Object> ssoResponse = new HashMap<>();
        ssoResponse.put("data", data);
        mockExchangeReturn(ssoResponse, HttpStatus.OK);

        Optional<SimpleUser> result = service.authenticate("valid-token");

        assertTrue(result.isPresent());
        assertEquals("deep-user", result.get().getUserId());
        assertEquals("Deep User", result.get().getUserName());
    }

    @Test
    void authenticate_brokenPath_shouldUseDefaults() {
        AuthProperties.UserInfoConfig.ClaimsConfig claimsConfig = new AuthProperties.UserInfoConfig.ClaimsConfig();
        claimsConfig.setUserId("result.missing.user_id");
        claimsConfig.setUserName("result.user_name");
        authProperties.getUserInfo().setClaims(claimsConfig);

        Map<String, Object> nested = new HashMap<>();
        nested.put("user_name", "Nested User");
        Map<String, Object> ssoResponse = new HashMap<>();
        ssoResponse.put("result", nested);
        mockExchangeReturn(ssoResponse, HttpStatus.OK);

        Optional<SimpleUser> result = service.authenticate("valid-token");

        assertTrue(result.isPresent());
        assertEquals("unknown", result.get().getUserId());
        assertEquals("Nested User", result.get().getUserName());
    }

    @Test
    void authenticate_nonMapMiddleLayer_shouldUseDefaults() {
        AuthProperties.UserInfoConfig.ClaimsConfig claimsConfig = new AuthProperties.UserInfoConfig.ClaimsConfig();
        claimsConfig.setUserId("result.valid.user_id");
        authProperties.getUserInfo().setClaims(claimsConfig);

        Map<String, Object> nested = new HashMap<>();
        nested.put("valid", true);
        Map<String, Object> ssoResponse = new HashMap<>();
        ssoResponse.put("result", nested);
        mockExchangeReturn(ssoResponse, HttpStatus.OK);

        Optional<SimpleUser> result = service.authenticate("valid-token");

        assertTrue(result.isPresent());
        assertEquals("unknown", result.get().getUserId());
    }

    /**
     * 用例描述：SSO 校验请求需携带空 JSON 请求体（{}），且请求头保持不变
     * 预制条件：restTemplate.exchange 模拟返回 200 与合法用户信息
     * 输入参数：accessToken = "valid-token"
     * 预期结果：authenticate 返回用户信息；exchange 收到的 HttpEntity body 为 "{}"，
     *           Content-Type 为 application/json，ssoHeaderName（X-Auth-Token）为 token 值
     */
    @Test
    void testAuthenticateShouldSendEmptyJsonBodyAndKeepHeaders() {
        mockExchangeReturn(buildSsoResponse("user1", "Test User", "domain1", "proj1"), HttpStatus.OK);

        Optional<SimpleUser> result = service.authenticate("valid-token");

        assertTrue(result.isPresent());
        assertEquals("user1", result.get().getUserId());

        @SuppressWarnings("unchecked")
        ArgumentCaptor<HttpEntity<String>> captor = ArgumentCaptor.forClass(HttpEntity.class);
        verify(restTemplate).exchange(eq(SSO_URL), eq(HttpMethod.POST), captor.capture(),
            any(ParameterizedTypeReference.class));
        HttpEntity<String> capturedEntity = captor.getValue();
        assertEquals("{}", capturedEntity.getBody());
        assertEquals("application/json", capturedEntity.getHeaders().getFirst(HttpHeaders.CONTENT_TYPE));
        assertEquals("valid-token", capturedEntity.getHeaders().getFirst("X-Auth-Token"));
    }

    /**
     * 用例描述：SSO 服务不可用（ResourceAccessException）时降级使用未过期缓存中的用户信息
     * 预制条件：先成功认证一次将用户信息写入缓存；随后 exchange 抛出 ResourceAccessException
     * 输入参数：accessToken = "cache-token"
     * 预期结果：authenticate 返回缓存中的用户信息
     */
    @Test
    void testAuthenticateShouldUseCachedUserWhenSsoServiceUnavailable() {
        mockExchangeReturn(buildSsoResponse("cached-user", "Cached User", "domain-cache", "proj-cache"),
            HttpStatus.OK);
        assertTrue(service.authenticate("cache-token").isPresent());

        mockExchangeThrow(new ResourceAccessException("Connection refused"));
        Optional<SimpleUser> result = service.authenticate("cache-token");

        assertTrue(result.isPresent());
        assertEquals("cached-user", result.get().getUserId());
        assertEquals("Cached User", result.get().getUserName());
    }

    /**
     * 用例描述：SSO 服务不可用且缓存已过期时返回 empty，请求被拒绝
     * 预制条件：先成功认证写入缓存，随后将缓存条目的 cachedAt 改为过期时间；exchange 抛出 ResourceAccessException
     * 输入参数：accessToken = "expired-cache-token"
     * 预期结果：authenticate 返回 empty
     */
    @Test
    void testAuthenticateShouldReturnEmptyWhenSsoUnavailableAndCacheExpired() throws Exception {
        mockExchangeReturn(buildSsoResponse("old-user", "Old User", "domain-old", "proj-old"), HttpStatus.OK);
        service.authenticate("expired-cache-token");

        @SuppressWarnings("unchecked")
        ConcurrentHashMap<String, Object> cache =
            (ConcurrentHashMap<String, Object>) ReflectionTestUtils.getField(service, "tokenCache");
        Object cachedEntry = cache.get("expired-cache-token");
        Field cachedAtField = cachedEntry.getClass().getDeclaredField("cachedAt");
        cachedAtField.setAccessible(true);
        cachedAtField.setLong(cachedEntry, System.currentTimeMillis() - TimeUnit.SECONDS.toMillis(301));

        mockExchangeThrow(new ResourceAccessException("Connection refused"));
        Optional<SimpleUser> result = service.authenticate("expired-cache-token");

        assertTrue(result.isEmpty());
    }

    /**
     * 用例描述：SSO 返回 401 时从 tokenCache 中移除该 token 的缓存条目
     * 预制条件：先成功认证将用户信息写入缓存；随后 exchange 抛出 401 HttpClientErrorException
     * 输入参数：accessToken = "revoked-token"
     * 预期结果：authenticate 返回 empty，且 tokenCache 中不再包含该 token（缓存状态转移被验证）
     */
    @Test
    void testAuthenticateShouldEvictTokenCacheOn401() {
        mockExchangeReturn(buildSsoResponse("revoked-user", "Revoked User", "domain-revoked", "proj-revoked"),
            HttpStatus.OK);
        assertTrue(service.authenticate("revoked-token").isPresent());

        @SuppressWarnings("unchecked")
        ConcurrentHashMap<String, Object> cache =
            (ConcurrentHashMap<String, Object>) ReflectionTestUtils.getField(service, "tokenCache");
        assertTrue(cache.containsKey("revoked-token"));

        mockExchangeThrow(new HttpClientErrorException(HttpStatus.UNAUTHORIZED));
        Optional<SimpleUser> result = service.authenticate("revoked-token");

        assertTrue(result.isEmpty());
        assertFalse(cache.containsKey("revoked-token"));
    }
}
