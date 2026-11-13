/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.utils;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mockStatic;

import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.Constants;
import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.common.dto.auth.AuthKeyInfo;
import com.openjiuwen.studio.agent.common.dto.auth.OauthInfo;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.AuthServiceConfig;

import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;

import java.util.Collections;
import java.util.Map;

@MockitoSettings(strictness = Strictness.LENIENT)
class WorkflowUtilsTest extends BaseTest {
    @InjectMocks
    private WorkflowUtils workflowUtils;

    private static MockedStatic<RequestContextUtils> mockedRequestContextUtils;

    @BeforeAll
    public static void init() {
        RequestContextUtils.setRequestAuthTokenAndProjectId(Constants.TEST_TOKEN, Constants.TEST_PROJECT_ID);
        mockedRequestContextUtils = mockStatic(RequestContextUtils.class);
    }

    @BeforeEach
    void setUp() throws Exception {
    }

    @AfterAll
    static void end() {
        mockedRequestContextUtils.close();
    }

    @Test
    public void test_parseAuthInfo() {
        // Given
        String orgType = "SSE";
        String serverConfig = """
              {
              "mcpServers": {
                "example-npx": {
                  "url":"https://xxxxx/apiexplorer/openapi/APIG/doc?api=CreateAuthorizingAppsV2",
                  "command": "npx",
                  "args":
                  [
                    "-y",
                    "@dandeliongold/mcp-time"
                  ],
                  "headers":{
                    "key":"value"
                  }
                }
              }
            }
            """;
        AuthInfo authInfo = new AuthInfo();

        WorkflowUtils.parseAuthInfo(orgType, serverConfig, authInfo);
    }

    @Test
    public void test_parseAuthInfo_empty() {
        // Given
        String orgType = "SSE";
        String serverConfig = """
              {
              "mcpServers": {
                "example-npx": {
                  "url":"https://xxxxx/apiexplorer/openapi/APIG/doc",
                  "command": "npx",
                  "args":
                  [
                    "-y",
                    "@dandeliongold/mcp-time"
                  ]
                }
              }
            }
            """;
        AuthInfo authInfo = new AuthInfo();
        var authServiceConfig = WorkflowUtils.parseAuthInfo(orgType, serverConfig, authInfo);
        assertEquals("{}", authServiceConfig.toString());
    }

    @Test
    public void test_removeQueryParamsFromUrl() {
        // Given
        String orgType = "SSE";
        String url = "https://xxxxx/apiexplorer/openapi/APIG/doc?api=CreateAuthorizingAppsV2";
        String urlNew = WorkflowUtils.removeQueryParamsFromUrl(url);
        assertEquals("https://xxxxx/apiexplorer/openapi/APIG/doc", urlNew);
        String url2 ="https://xxxxx/apiexplorer/openapi/APIG/doc?api=CreateAuthorizingAppsV2#1234";
        String urlNew2 = WorkflowUtils.removeQueryParamsFromUrl(url2);
        assertEquals("https://xxxxx/apiexplorer/openapi/APIG/doc#1234", urlNew2);
        String url3 ="not-a-url";
        WorkflowUtils.removeQueryParamsFromUrl(url3);
    }

    @Test
    public void test_extractQueryParamsFromUrl() {
        // Given
        String url = "https://xxxxx/apiexplorer/openapi/APIG/doc?api=CreateAuthorizingAppsV2";
        Map<String, String> mapData = WorkflowUtils.extractQueryParamsFromUrl(url);
        assertTrue(mapData.containsKey("api"));
    }

    @Test
    public void test_parseAuthInfo_OAUTH() {
        // Given
        String orgType = "SSE";
        String serverConfig = """
              {
              "mcpServers": {
                "example-npx": {
                  "url":"https://xxxxx/apiexplorer/openapi/APIG/doc",
                  "command": "npx",
                  "args":
                  [
                    "-y",
                    "@dandeliongold/mcp-time"
                  ]
                }
              }
            }
            """;
        OauthInfo oauthConfig = new OauthInfo();
        oauthConfig.setClientId("clientId");
        oauthConfig.setClientSecret("clientSecret");
        oauthConfig.setEndpointUrl("https://example.com/oauth/token");

        AuthInfo authInfo = new AuthInfo();
        authInfo.setScope(AuthInfo.ScopeEnum.OAUTH);
        authInfo.setCustomOauth(oauthConfig);
        WorkflowUtils.parseAuthInfo(orgType, serverConfig, authInfo);
    }

    @Test
    public void test_parseAuthInfo_apikey() {
        // Given
        String orgType = "SSE";
        AuthKeyInfo authKeyInfo = new AuthKeyInfo();
        authKeyInfo.setAuthKey("authKey");
        authKeyInfo.setTargetName("targetName");

        AuthInfo authInfo = new AuthInfo();
        authInfo.setAuthKeys(Collections.singletonList(authKeyInfo));
        authInfo.setScope(AuthInfo.ScopeEnum.SERVICE);
        authInfo.setDomain(AuthInfo.DomainEnum.HEADERS);
        WorkflowUtils.parseAuthInfo(orgType, "serverConfig", authInfo);
    }

    @Test
    public void test_parseAuthInfo_dynamic_scope_preserved() {
        // FEAT-093：IR 保留 DYNAMIC scope 身份（值经 arguments 注入，headers/query 恒空），
        // 使运行期可区分 DYNAMIC 与无鉴权（三参与单参两个重载同构）
        AuthKeyInfo authKeyInfo = new AuthKeyInfo();
        authKeyInfo.setTargetName("Authorization");
        AuthInfo authInfo = new AuthInfo();
        authInfo.setAuthKeys(Collections.singletonList(authKeyInfo));
        authInfo.setScope(AuthInfo.ScopeEnum.DYNAMIC);
        authInfo.setDomain(AuthInfo.DomainEnum.HEADERS);

        Object threeArg = WorkflowUtils.parseAuthInfo("SSE", "serverConfig", authInfo);
        assertTrue(threeArg instanceof AuthServiceConfig, "three-arg should return AuthServiceConfig");
        AuthServiceConfig config = (AuthServiceConfig) threeArg;
        assertEquals("DYNAMIC", config.getScope());
        assertTrue(config.getHeaders().isEmpty());
        assertTrue(config.getQuery().isEmpty());

        Object oneArg = WorkflowUtils.parseAuthInfo(authInfo);
        assertTrue(oneArg instanceof AuthServiceConfig, "one-arg should return AuthServiceConfig");
        AuthServiceConfig config1 = (AuthServiceConfig) oneArg;
        assertEquals("DYNAMIC", config1.getScope());
        assertTrue(config1.getHeaders().isEmpty());
        assertTrue(config1.getQuery().isEmpty());
    }
}
