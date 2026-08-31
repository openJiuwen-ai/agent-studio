/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.security.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.doThrow;

import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;
import com.openjiuwen.studio.agent.common.security.properties.AuthProperties;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

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
}
