/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.security.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
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

        SimpleUser result = service.authenticate("valid-token");

        assert result != null;
        assertEquals("user1", result.getUserId());
        assertEquals("Test User", result.getUserName());
        assertEquals("domain1", result.getDomainId());
        assertEquals("proj1", result.getProjectId());
    }

    @Test
    void authenticate_2xxStatus_shouldReturnUserInfo() {
        mockExchangeReturn(buildSsoResponse("user2", "User Two", "domain2", "proj2"), HttpStatus.CREATED);

        SimpleUser result = service.authenticate("valid-token");

        assert result != null;
        assertEquals("user2", result.getUserId());
    }

    @Test
    void authenticate_nullBody_shouldReturnNull() {
        mockExchangeReturn(null, HttpStatus.OK);

        SimpleUser result = service.authenticate("valid-token");

        assertNull(result);
    }

    @Test
    void authenticate_httpClientError401_shouldReturnNull() {
        mockExchangeThrow(new HttpClientErrorException(HttpStatus.UNAUTHORIZED));

        SimpleUser result = service.authenticate("expired-token");

        assertNull(result);
    }

    @Test
    void authenticate_httpClientError403_shouldReturnNull() {
        mockExchangeThrow(new HttpClientErrorException(HttpStatus.FORBIDDEN));

        SimpleUser result = service.authenticate("forbidden-token");

        assertNull(result);
    }

    @Test
    void authenticate_generalException_shouldReturnNull() {
        mockExchangeThrow(new RuntimeException("Connection refused"));

        SimpleUser result = service.authenticate("error-token");

        assertNull(result);
    }

    @Test
    void authenticate_emptyFields_shouldUseDefaults() {
        Map<String, Object> ssoResponse = new HashMap<>();
        ssoResponse.put("user_id", "user1");
        ssoResponse.put("user_name", null);
        ssoResponse.put("domain_id", "");
        ssoResponse.put("project_id", "  ");
        mockExchangeReturn(ssoResponse, HttpStatus.OK);

        SimpleUser result = service.authenticate("valid-token");

        assert result != null;
        assertEquals("user1", result.getUserId());
        assertEquals("unknown", result.getUserName());
        assertEquals("0", result.getDomainId());
        assertEquals("0", result.getProjectId());
    }

    @Test
    void authenticate_allFieldsEmpty_shouldUseAllDefaults() {
        Map<String, Object> ssoResponse = new HashMap<>();
        ssoResponse.put("user_id", "");
        ssoResponse.put("user_name", null);
        ssoResponse.put("domain_id", "");
        ssoResponse.put("project_id", null);
        mockExchangeReturn(ssoResponse, HttpStatus.OK);

        SimpleUser result = service.authenticate("valid-token");

        assert result != null;
        assertEquals("0", result.getDomainId());
        assertEquals("0", result.getProjectId());
        assertEquals("unknown", result.getUserName());
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

        SimpleUser result = service.authenticate("valid-token");

        assert result != null;
        assertEquals("custom-domain", result.getDomainId());
        assertEquals("custom-project", result.getProjectId());
        assertEquals("unknown", result.getUserName());
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

        SimpleUser result = service.authenticate("valid-token");

        assert result != null;
        assertEquals("custom-user", result.getUserId());
        assertEquals("Custom Name", result.getUserName());
        assertEquals("custom-tenant", result.getDomainId());
        assertEquals("custom-group", result.getProjectId());
    }

    @Test
    void authenticate_numericClaimValues_shouldConvertToString() {
        Map<String, Object> ssoResponse = new HashMap<>();
        ssoResponse.put("user_id", 12345);
        ssoResponse.put("user_name", "Test User");
        ssoResponse.put("domain_id", 100);
        ssoResponse.put("project_id", 200);
        mockExchangeReturn(ssoResponse, HttpStatus.OK);

        SimpleUser result = service.authenticate("valid-token");

        assert result != null;
        assertEquals("12345", result.getUserId());
        assertEquals("100", result.getDomainId());
        assertEquals("200", result.getProjectId());
    }
}
