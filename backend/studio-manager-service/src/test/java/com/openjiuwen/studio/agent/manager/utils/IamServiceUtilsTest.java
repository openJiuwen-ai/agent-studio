/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.utils;

import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;
import com.openjiuwen.studio.agent.common.utils.OkHttpClientUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.dto.iam.GetIamUserResponse;
import com.openjiuwen.studio.agent.manager.dto.iam.IamUserGroupPermissionRsp;
import com.openjiuwen.studio.agent.manager.dto.iam.IamUserGroupRsp;
import com.openjiuwen.studio.agent.manager.rce.service.ClientService;
import com.openjiuwen.studio.agent.manager.service.mcp.properties.IamProperties;

import okhttp3.Call;
import okhttp3.OkHttpClient;
import okhttp3.Protocol;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.ResponseBody;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.test.util.ReflectionTestUtils;

import com.alibaba.fastjson.JSONObject;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@MockitoSettings(strictness = Strictness.LENIENT)
class IamServiceUtilsTest {

    @Mock
    private OkHttpClientUtils okHttpClientUtils;

    @Mock
    private IamProperties iamProperties;

    @Mock
    private ClientService clientService;

    @Mock
    private OkHttpClient okHttpClient;

    @Mock
    private Call call;

    @InjectMocks
    private IamServiceUtils iamServiceUtils;

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(iamServiceUtils, "iamUrl", "https://iam.test.com");
    }

    @Test
    void testQueryIamUserList_BlankToken() {
        GetIamUserResponse result = iamServiceUtils.queryIamUserList("");

        assertNotNull(result);
    }

    @Test
    void testQueryIamUserList_NullToken() {
        GetIamUserResponse result = iamServiceUtils.queryIamUserList(null);

        assertNotNull(result);
    }

    @Test
    void testQueryIamUserList_Success() throws Exception {
        String responseBody = "{\"users\":[{\"id\":\"user-1\",\"name\":\"test\"}]}";
        Response response = new Response.Builder()
            .request(new Request.Builder().url("https://iam.test.com/v3/users").build())
            .protocol(Protocol.HTTP_1_1)
            .code(200)
            .message("OK")
            .body(ResponseBody.create(responseBody, okhttp3.MediaType.parse("application/json")))
            .build();

        when(okHttpClientUtils.getHttpClient()).thenReturn(okHttpClient);
        when(okHttpClient.newCall(any())).thenReturn(call);
        when(call.execute()).thenReturn(response);

        GetIamUserResponse result = iamServiceUtils.queryIamUserList("valid-token");

        assertNotNull(result);
    }

    @Test
    void testQueryIamUserList_HttpError() throws Exception {
        Response response = new Response.Builder()
            .request(new Request.Builder().url("https://iam.test.com/v3/users").build())
            .protocol(Protocol.HTTP_1_1)
            .code(403)
            .message("Forbidden")
            .body(ResponseBody.create("{}", okhttp3.MediaType.parse("application/json")))
            .build();

        when(okHttpClientUtils.getHttpClient()).thenReturn(okHttpClient);
        when(okHttpClient.newCall(any())).thenReturn(call);
        when(call.execute()).thenReturn(response);

        GetIamUserResponse result = iamServiceUtils.queryIamUserList("valid-token");

        assertNotNull(result);
    }

    @Test
    void testQueryIamUserGroupList_BlankToken() {
        IamUserGroupRsp result = iamServiceUtils.queryIamUserGroupList("");

        assertNotNull(result);
    }

    @Test
    void testQueryIamUserGroupList_NullBody() throws Exception {
        Response response = new Response.Builder()
            .request(new Request.Builder().url("https://iam.test.com").build())
            .protocol(Protocol.HTTP_1_1)
            .code(200)
            .message("OK")
            .build();

        when(okHttpClientUtils.getHttpClient()).thenReturn(okHttpClient);
        when(okHttpClient.newCall(any())).thenReturn(call);
        when(call.execute()).thenReturn(response);

        try (MockedStatic<RequestContextUtils> mockedStatic = mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestUserId).thenReturn("user-1");

            IamUserGroupRsp result = iamServiceUtils.queryIamUserGroupList("token");

            assertNotNull(result);
        }
    }

    @Test
    void testQueryIamUserGroupPermissionList_BlankToken() {
        IamUserGroupPermissionRsp result = iamServiceUtils.queryIamUserGroupPermissionList("", "group-1");

        assertNotNull(result);
    }

    @Test
    void testQueryIamUserGroupPermissionList_NullBody() throws Exception {
        Response response = new Response.Builder()
            .request(new Request.Builder().url("https://iam.test.com").build())
            .protocol(Protocol.HTTP_1_1)
            .code(200)
            .message("OK")
            .build();

        when(okHttpClientUtils.getHttpClient()).thenReturn(okHttpClient);
        when(okHttpClient.newCall(any())).thenReturn(call);
        when(call.execute()).thenReturn(response);

        try (MockedStatic<RequestContextUtils> mockedStatic = mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");

            IamUserGroupPermissionRsp result = iamServiceUtils.queryIamUserGroupPermissionList("token", "group-1");

            assertNotNull(result);
        }
    }

    @Test
    void testQueryDomainToken_Success() throws Exception {
        Response response = new Response.Builder()
            .request(new Request.Builder().url("https://iam.test.com/v3/auth/tokens").build())
            .protocol(Protocol.HTTP_1_1)
            .code(201)
            .message("Created")
            .header("X-Subject-Token", "domain-token-123")
            .body(ResponseBody.create("{}", okhttp3.MediaType.parse("application/json")))
            .build();

        when(okHttpClientUtils.getHttpClient()).thenReturn(okHttpClient);
        when(okHttpClient.newCall(any())).thenReturn(call);
        when(call.execute()).thenReturn(response);

        String result = iamServiceUtils.queryDomainToken("project-token", "test-domain");

        assertEquals("domain-token-123", result);
    }

    @Test
    void testQueryDomainToken_HttpError() throws Exception {
        Response response = new Response.Builder()
            .request(new Request.Builder().url("https://iam.test.com/v3/auth/tokens").build())
            .protocol(Protocol.HTTP_1_1)
            .code(401)
            .message("Unauthorized")
            .body(ResponseBody.create("error", okhttp3.MediaType.parse("application/json")))
            .build();

        when(okHttpClientUtils.getHttpClient()).thenReturn(okHttpClient);
        when(okHttpClient.newCall(any())).thenReturn(call);
        when(call.execute()).thenReturn(response);

        String result = iamServiceUtils.queryDomainToken("bad-token", "test-domain");

        assertEquals("", result);
    }

    @Test
    void testQueryDomainToken_MissingHeader() throws Exception {
        Response response = new Response.Builder()
            .request(new Request.Builder().url("https://iam.test.com/v3/auth/tokens").build())
            .protocol(Protocol.HTTP_1_1)
            .code(201)
            .message("Created")
            .body(ResponseBody.create("{}", okhttp3.MediaType.parse("application/json")))
            .build();

        when(okHttpClientUtils.getHttpClient()).thenReturn(okHttpClient);
        when(okHttpClient.newCall(any())).thenReturn(call);
        when(call.execute()).thenReturn(response);

        String result = iamServiceUtils.queryDomainToken("token", "domain");

        assertEquals("", result);
    }

    @Test
    void testQueryDomainToken_NullDomainName_shouldNotThrow() throws Exception {
        Response response = new Response.Builder()
            .request(new Request.Builder().url("https://iam.test.com/v3/auth/tokens").build())
            .protocol(Protocol.HTTP_1_1)
            .code(201)
            .message("Created")
            .header("X-Subject-Token", "domain-token-123")
            .body(ResponseBody.create("{}", okhttp3.MediaType.parse("application/json")))
            .build();

        when(okHttpClientUtils.getHttpClient()).thenReturn(okHttpClient);
        when(okHttpClient.newCall(any())).thenReturn(call);
        when(call.execute()).thenReturn(response);

        // domainName 为 null 时不得抛空指针（issue #1514）
        String result = iamServiceUtils.queryDomainToken("project-token", null);

        assertEquals("domain-token-123", result);
    }

    @Test
    void testSendPost_Success() throws Exception {
        Response response = new Response.Builder()
            .request(new Request.Builder().url("https://iam.test.com").build())
            .protocol(Protocol.HTTP_1_1)
            .code(200)
            .message("OK")
            .header("X-Subject-Token", "new-token")
            .body(ResponseBody.create("{}", okhttp3.MediaType.parse("application/json")))
            .build();

        when(okHttpClientUtils.getHttpClient()).thenReturn(okHttpClient);
        when(okHttpClient.newCall(any())).thenReturn(call);
        when(call.execute()).thenReturn(response);

        String result = iamServiceUtils.sendPost("https://iam.test.com/v3/auth/tokens",
            new java.util.HashMap<>(), new Object());

        assertEquals("new-token", result);
    }

    @Test
    void testSendPost_Failure() throws Exception {
        Response response = new Response.Builder()
            .request(new Request.Builder().url("https://iam.test.com").build())
            .protocol(Protocol.HTTP_1_1)
            .code(401)
            .message("Unauthorized")
            .body(ResponseBody.create("{}", okhttp3.MediaType.parse("application/json")))
            .build();

        when(okHttpClientUtils.getHttpClient()).thenReturn(okHttpClient);
        when(okHttpClient.newCall(any())).thenReturn(call);
        when(call.execute()).thenReturn(response);

        assertThrows(AgentStudioException.class, () ->
            iamServiceUtils.sendPost("https://iam.test.com/v3/auth/tokens",
                new java.util.HashMap<>(), new Object()));
    }

    @Test
    void testDoAuthorization_Success() {
        try (MockedStatic<RequestContextUtils> mockedStatic = mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");

            ResponseEntity<JSONObject> responseEntity = new ResponseEntity<>(new JSONObject(), HttpStatus.OK);
            when(clientService.agencyAuthorization(anyString(), anyString(), anyString(), anyString()))
                .thenReturn(responseEntity);

            boolean result = iamServiceUtils.doAuthorization("proj-1", "role-1", "agency-1");

            assertTrue(result);
        }
    }

    @Test
    void testDoAuthorization_Failure() {
        try (MockedStatic<RequestContextUtils> mockedStatic = mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");

            ResponseEntity<JSONObject> responseEntity = new ResponseEntity<>(new JSONObject(), HttpStatus.FORBIDDEN);
            when(clientService.agencyAuthorization(anyString(), anyString(), anyString(), anyString()))
                .thenReturn(responseEntity);

            assertThrows(AgentStudioException.class, () ->
                iamServiceUtils.doAuthorization("proj-1", "role-1", "agency-1"));
        }
    }

    @Test
    void testHasAgencyAuthorization_Success() {
        try (MockedStatic<RequestContextUtils> mockedStatic = mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");

            ResponseEntity<JSONObject> responseEntity = new ResponseEntity<>(new JSONObject(), HttpStatus.OK);
            when(clientService.hasAgencyAuthorization(anyString(), anyString(), anyString(), anyString()))
                .thenReturn(responseEntity);

            boolean result = iamServiceUtils.hasAgencyAuthorization("proj-1", "role-1", "agency-1");

            assertTrue(result);
        }
    }

    @Test
    void testHasAgencyAuthorization_Exception() {
        try (MockedStatic<RequestContextUtils> mockedStatic = mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");

            when(clientService.hasAgencyAuthorization(anyString(), anyString(), anyString(), anyString()))
                .thenThrow(new RuntimeException("error"));

            boolean result = iamServiceUtils.hasAgencyAuthorization("proj-1", "role-1", "agency-1");

            assertFalse(result);
        }
    }

    @Test
    void testGetOpAccountAuthToken() throws Exception {
        when(iamProperties.getUser()).thenReturn("op-user");
        when(iamProperties.getPassword()).thenReturn("encrypted-pass");
        when(iamProperties.getAccount()).thenReturn("op-account");
        when(iamProperties.getProjectName()).thenReturn("op-project");

        Response response = new Response.Builder()
            .request(new Request.Builder().url("https://iam.test.com").build())
            .protocol(Protocol.HTTP_1_1)
            .code(200)
            .message("OK")
            .header("X-Subject-Token", "op-token")
            .body(ResponseBody.create("{}", okhttp3.MediaType.parse("application/json")))
            .build();

        when(okHttpClientUtils.getHttpClient()).thenReturn(okHttpClient);
        when(okHttpClient.newCall(any())).thenReturn(call);
        when(call.execute()).thenReturn(response);

        try (MockedStatic<CryptoUtils> cryptoMock = mockStatic(CryptoUtils.class)) {
            cryptoMock.when(() -> CryptoUtils.decrypt("encrypted-pass")).thenReturn("plain-pass");

            String result = iamServiceUtils.getOpAccountAuthToken();

            assertEquals("op-token", result);
        }
    }
}
