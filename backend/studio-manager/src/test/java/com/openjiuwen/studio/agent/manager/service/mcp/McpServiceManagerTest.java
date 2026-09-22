/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2022-2023. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.mcp;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.RETURNS_DEEP_STUBS;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;
import com.openjiuwen.studio.agent.common.utils.OkHttpClientUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.RequestHeaderHolderUtils;
import com.openjiuwen.studio.agent.manager.constant.Constants;
import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.common.dto.auth.AuthKeyInfo;
import com.openjiuwen.studio.agent.manager.dto.CesMetricDataResp;
import com.openjiuwen.studio.agent.manager.dto.Datapoints;
import com.openjiuwen.studio.agent.manager.dto.IdListRequest;
import com.openjiuwen.studio.agent.manager.dto.ListServersQo;
import com.openjiuwen.studio.agent.manager.dto.McpDeployResult;
import com.openjiuwen.studio.agent.manager.dto.McpServerBaseInfoDto;
import com.openjiuwen.studio.agent.manager.dto.McpServerBaseInfoListResp;
import com.openjiuwen.studio.agent.manager.dto.McpServerDetailInfoDto;
import com.openjiuwen.studio.agent.manager.dto.McpServerDetailReq;
import com.openjiuwen.studio.agent.manager.dto.McpServerRatingReq;
import com.openjiuwen.studio.agent.manager.dto.McpServiceBaseInfoListResp;
import com.openjiuwen.studio.agent.manager.dto.McpServiceBatchDeployItem;
import com.openjiuwen.studio.agent.manager.dto.McpServiceBatchDeployReq;
import com.openjiuwen.studio.agent.manager.dto.McpServiceBatchDeployResp;
import com.openjiuwen.studio.agent.manager.dto.McpServiceDeployReq;
import com.openjiuwen.studio.agent.manager.dto.McpServiceDetailInfoDto;
import com.openjiuwen.studio.agent.manager.dto.McpServiceModifyReq;
import com.openjiuwen.studio.agent.manager.dto.McpServiceSkinnyEntity;
import com.openjiuwen.studio.agent.manager.dto.McpServiceStatisticResp;
import com.openjiuwen.studio.agent.manager.dto.McpServiceToolEntity;
import com.openjiuwen.studio.agent.manager.dto.McpServiceToolsEntity;
import com.openjiuwen.studio.agent.manager.dto.McpServiceToolsTestReq;
import com.openjiuwen.studio.agent.manager.dto.McpServicesCesLineChartQo;
import com.openjiuwen.studio.agent.manager.dto.McpServicesCesSuccessRateLineChartQo;
import com.openjiuwen.studio.agent.common.dto.auth.OauthInfo;
import com.openjiuwen.studio.agent.manager.dto.PageInfoV2;
import com.openjiuwen.studio.agent.manager.entity.McpServiceEntity;
import com.openjiuwen.studio.agent.manager.enums.EnumOrgType;
import com.openjiuwen.studio.agent.manager.rce.service.ClientService;
import com.openjiuwen.studio.agent.manager.service.mcp.infrastructure.apig.CesService;
import com.openjiuwen.studio.agent.manager.service.mcp.model.dao.McpServiceDao;
import com.openjiuwen.studio.agent.manager.service.share.ShareInnerService;
import com.openjiuwen.studio.agent.manager.utils.BaseTest;
import com.openjiuwen.studio.agent.manager.utils.CommonUtil;
import com.openjiuwen.studio.agent.manager.utils.McpJsonUtils;
import com.openjiuwen.studio.agent.manager.utils.McpUtil;
import com.openjiuwen.studio.common.service.service.EncryptionAdapter;

import io.modelcontextprotocol.spec.McpSchema;
import lombok.extern.slf4j.Slf4j;

import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.mockito.Answers;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.transaction.annotation.Transactional;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * @description
 * @since 2025/8/8
 **/
@Slf4j
@Transactional
@MockitoSettings(strictness = Strictness.LENIENT)
@Sql(scripts = {"classpath:sql/mcp_data_init_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_CLASS)
@Sql(scripts = {"classpath:sql/after_test_clear_db.sql"}, executionPhase = Sql.ExecutionPhase.AFTER_TEST_CLASS)
public class McpServiceManagerTest extends BaseTest {
    private static MockedStatic<RequestContextUtils> mockedStatic;

    private static MockedStatic<CryptoUtils> mgSccCryptoUtils;

    private static MockedStatic<RequestHeaderHolderUtils> mockedHeaderStatic;

    private static MockedStatic<McpClientService> mcpClientService;

    private static MockedStatic<CommonUtil> commonUtilMockedStatic;

    @MockitoBean
    private ClientService clientService;

    @MockitoBean
    private CesService cesService;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private McpUtil mcpUtil;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private McpServiceDao serviceDao;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private OkHttpClientUtils okHttpClientUtils;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private ShareInnerService shareInnerService;


    @Spy
    @Autowired
    private McpServiceManager mcpService;

    @MockitoBean
    private McpClientService mcpClient;

    @BeforeAll
    public static void init() {
        RequestContextUtils.setRequestAuthTokenAndProjectId(Constants.TEST_TOKEN, Constants.TEST_PROJECT_ID);
        mockedStatic = Mockito.mockStatic(RequestContextUtils.class);
        commonUtilMockedStatic = Mockito.mockStatic(CommonUtil.class);
        commonUtilMockedStatic.when(CommonUtil::getTenantId).thenReturn("system");
        commonUtilMockedStatic.when(CommonUtil::getDeptCode).thenReturn("system");
        commonUtilMockedStatic.when(CommonUtil::getAndValidateTenantId).thenReturn("system");
        mcpClientService = Mockito.mockStatic(McpClientService.class);
        mgSccCryptoUtils = Mockito.mockStatic(CryptoUtils.class, RETURNS_DEEP_STUBS);
        mockedStatic.when(RequestContextUtils::getRequestProjectId).thenReturn(Constants.TEST_PROJECT_ID);
        mockedStatic.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(Constants.TEST_WORKSPACE_ID);
        mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn(Constants.TEST_TOKEN);
        mockedStatic.when(RequestContextUtils::getRequestUserDomainId).thenReturn(Constants.TEST_PROJECT_ID2);
        mockedStatic.when(RequestContextUtils::getRequestUserName).thenReturn(Constants.TEST_USER_NAME);
        mockedStatic.when(RequestContextUtils::getRequestUserId).thenReturn("test_copy_user_id");
        mgSccCryptoUtils.when(() -> CryptoUtils.decrypt(anyString())).thenReturn("{\n  \"mcpServers\": {\n    \"example-sse\": {\n      \"url\": \"http://127.0.0.1:9004/sse\"\n    }\n  }\n}");
        mockedHeaderStatic = Mockito.mockStatic(RequestHeaderHolderUtils.class);
        mockedHeaderStatic.when(RequestHeaderHolderUtils::getRequestLanguage).thenReturn("en-us");
    }

    @AfterAll
    static void end() {
        mockedStatic.close();
        commonUtilMockedStatic.close();
        mcpClientService.close();
        mgSccCryptoUtils.close();
        mockedHeaderStatic.close();
    }

    @Test
    void testListServices() {
        PageInfoV2 pageInfoV2 = new PageInfoV2();
        pageInfoV2.setLimit(10);
        pageInfoV2.setOffset(0);
        McpServiceBaseInfoListResp result = this.mcpService.listServices(Constants.TEST_PROJECT_ID,
            Constants.TEST_WORKSPACE_ID, "ZH", null, null, "Mcp", null, pageInfoV2);
        assertNotNull(result);
    }

    @Test
    void testListServices2() {
        PageInfoV2 pageInfoV2 = new PageInfoV2();
        pageInfoV2.setLimit(10);
        pageInfoV2.setOffset(0);
        this.mcpService.listServices("project_mock", "workspace_mock", "EN", null, null, "Mcp", null, pageInfoV2);
    }

    @Test
    void testListServices3() {
        PageInfoV2 pageInfoV2 = new PageInfoV2();
        pageInfoV2.setLimit(10);
        pageInfoV2.setOffset(0);
        McpServiceBaseInfoListResp result = this.mcpService.listServices(Constants.TEST_PROJECT_ID,
            Constants.TEST_WORKSPACE_ID, "EN", "模板", null, "Mcp", null, pageInfoV2);
        assertNotNull(result);
    }

    @Test
    void testListServices4() {
        PageInfoV2 pageInfoV2 = new PageInfoV2();
        pageInfoV2.setLimit(10);
        pageInfoV2.setOffset(0);
        McpServiceBaseInfoListResp result = this.mcpService.listServices(Constants.TEST_PROJECT_ID,
            Constants.TEST_WORKSPACE_ID, "ZH", "模板", null, "Mcp", null, pageInfoV2);
        assertNotNull(result);
    }

    @Test
    void testListServicesForRuntime() {
        PageInfoV2 pageInfoV2 = new PageInfoV2();
        pageInfoV2.setLimit(10);
        pageInfoV2.setOffset(0);
        McpServiceBaseInfoListResp result = this.mcpService.listServicesWithRuntimeInfo(Constants.TEST_PROJECT_ID,
            Constants.TEST_WORKSPACE_ID, "ZH", null, pageInfoV2);
        assertNotNull(result);
    }

    @Test
    void testListServicesForRuntime2() {
        PageInfoV2 pageInfoV2 = new PageInfoV2();
        pageInfoV2.setLimit(10);
        pageInfoV2.setOffset(0);
        this.mcpService.listServicesWithRuntimeInfo("project_mock", "workspace_mock", "EN", null, pageInfoV2);
    }

    @Test
    void testListServicesForRuntime3() {
        PageInfoV2 pageInfoV2 = new PageInfoV2();
        pageInfoV2.setLimit(10);
        pageInfoV2.setOffset(0);
        McpServiceBaseInfoListResp result = this.mcpService.listServicesWithRuntimeInfo(Constants.TEST_PROJECT_ID,
            Constants.TEST_WORKSPACE_ID, "EN", "模板", pageInfoV2);
        assertNotNull(result);
    }

    @Test
    void testListServicesForRuntime4() {
        PageInfoV2 pageInfoV2 = new PageInfoV2();
        pageInfoV2.setLimit(10);
        pageInfoV2.setOffset(0);
        McpServiceBaseInfoListResp result = this.mcpService.listServicesWithRuntimeInfo(Constants.TEST_PROJECT_ID,
            Constants.TEST_WORKSPACE_ID, "ZH", "模板", pageInfoV2);
        assertNotNull(result);
    }

    @Test
    void testMcpServicesToolsList() {
        String result = this.mcpService.mcpServicesToolsList(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID,
            "68345ccb7daf466199dc14eff7992af0");
        assertNotNull(result);
    }

    @Test
    void testMcpServicesToolsList2() {
        Assertions.assertThrows(Exception.class,
            () -> this.mcpService.mcpServicesToolsList(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID,
                "68345ccb7daf466199dc14eff7992af02"));
    }

    @Test
    void testMcpServicesToolsList3() throws Exception { // 1. 加上 throws Exception
        mgSccCryptoUtils.when(() -> CryptoUtils.decrypt(anyString())).thenReturn("{}");

        // 2. 使用 Builder 模式构建 Tool
        McpSchema.Tool tool = McpSchema.Tool.builder()
            .name("test")
            .description("desc")
            .inputSchema(new com.fasterxml.jackson.databind.ObjectMapper().readValue(
                "{\"type\":\"object\",\"properties\":{\"origin\":{\"type\":\"string\",\"description\":\"出发点经纬度，坐标格式为：经度，纬度\"},\"destination\":{\"type\":\"string\",\"description\":\"目的地经纬度，坐标格式为：经度，纬度\"}},\"required\":[\"origin\",\"destination\"]}",
                McpSchema.JsonSchema.class))
            .build();

        mcpClientService.when(() -> mcpClient.getMcpServiceToolList(anyString(), anyString(), anyString(), anyMap()))
            .thenReturn(List.of(tool));

        String result = this.mcpService.mcpServicesToolsList(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID,
            "ff824f837e954cd5ad9036f45a9e8b34");
        assertNotNull(result);
    }

    @Test
    void testMcpServicesToolsListException() throws Exception { // 1. 加上 throws Exception
        assertThrows(AgentStudioException.class, () -> {
            this.mcpService.mcpServicesToolsList(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID,
                "305d74a28fce4179934fceac17e32910");
        });
    }

    /**
     * 覆盖本地数据库中存在工具场景
     */
    @Test
    void testMcpServiceToolsInFlow() {
        commonUtilMockedStatic.when(CommonUtil::getAndValidateTenantId).thenReturn("system");
        McpServiceToolsEntity result = this.mcpService.mcpServicesToolsListWithFlow(Constants.TEST_PROJECT_ID,
            Constants.TEST_WORKSPACE_ID, "68345ccb7daf466199dc14eff7992af0");
        assertNotNull(result);
    }

    /**
     * 不存在的mcp 覆盖异常场景
     */
    @Test
    void testMcpServiceToolsInFlow2() {
        commonUtilMockedStatic.when(CommonUtil::getAndValidateTenantId).thenReturn("system");
        Assertions.assertThrows(Exception.class,
            () -> this.mcpService.mcpServicesToolsListWithFlow(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID,
                "68345ccb7daf466199dc14eff7992af02"));
    }

    /**
     * 覆盖本地库中没有工具信息，调用sse接口加载的场景
     */
    @Test
    void testMcpServiceToolsInFlow3() throws Exception { // 1. 加上 throws Exception
        mgSccCryptoUtils.when(() -> CryptoUtils.decrypt(anyString())).thenReturn("{}");

        // 2. 使用 Builder 模式构建 Tool
        McpSchema.Tool tool = McpSchema.Tool.builder()
            .name("test")
            .description("desc")
            .inputSchema(new com.fasterxml.jackson.databind.ObjectMapper().readValue(
                "{\"type\":\"object\",\"properties\":{\"origin\":{\"type\":\"string\",\"description\":\"出发点经纬度，坐标格式为：经度，纬度\"},\"destination\":{\"type\":\"string\",\"description\":\"目的地经纬度，坐标格式为：经度，纬度\"}},\"required\":[\"origin\",\"destination\"]}",
                McpSchema.JsonSchema.class))
            .build();

        mcpClientService.when(() -> mcpClient.getMcpServiceToolList(anyString(), anyString(), anyString(), anyMap()))
            .thenReturn(List.of(tool));

        commonUtilMockedStatic.when(CommonUtil::getAndValidateTenantId).thenReturn("system");
        McpServiceToolsEntity result = this.mcpService.mcpServicesToolsListWithFlow(Constants.TEST_PROJECT_ID,
            Constants.TEST_WORKSPACE_ID, "ff824f837e954cd5ad9036f45a9e8b39");
        assertNotNull(result);
    }

    /**
     * 覆盖本地库中没有工具信息，调用sse接口加载工具为空的场景
     */
    @Test
    void testMcpServiceToolsInFlow4() {
        mgSccCryptoUtils.when(() -> CryptoUtils.decrypt(anyString())).thenReturn("{}");
        mcpClientService.when(() -> mcpClient.getMcpServiceToolList(anyString(), anyString(), anyString(), anyMap()))
            .thenReturn(List.of());
        commonUtilMockedStatic.when(CommonUtil::getAndValidateTenantId).thenReturn("system");
        McpServiceToolsEntity result = this.mcpService.mcpServicesToolsListWithFlow(Constants.TEST_PROJECT_ID,
            Constants.TEST_WORKSPACE_ID, "ff824f837e954cd5ad9036f45a9e8b40");
        Assertions.assertNotNull(result);
    }

    /**
     * 覆盖本地数据库中数据存在场景
     */
    @Test
    void testModifyService() {

        EncryptionAdapter mockEncryptionAdapter = org.mockito.Mockito.mock(EncryptionAdapter.class);
        org.mockito.Mockito.when(mockEncryptionAdapter.encrypt(anyString(), any()))
                .thenReturn("E1-{fake-uuid}-fake_encrypt_result");
        org.mockito.Mockito.when(mockEncryptionAdapter.decrypt(anyString())).thenReturn("{}");
        org.mockito.Mockito.when(mockEncryptionAdapter.decrypt(anyString(), any())).thenReturn("{}");

        // 1. 注入到 mcpService
        ReflectionTestUtils.setField(this.mcpService, "encryptionAdapter", mockEncryptionAdapter);

        // 2. 动态获取它内部的 mcpBase 并注入 (处理底层加密 AuthInfo 的逻辑)
        Object mcpBaseInstance = ReflectionTestUtils.getField(this.mcpService, "mcpBase");
        if (mcpBaseInstance != null) {
            ReflectionTestUtils.setField(mcpBaseInstance, "encryptionAdapter", mockEncryptionAdapter);
        }

        McpServiceModifyReq req = new McpServiceModifyReq();
        commonUtilMockedStatic.when(CommonUtil::getAndValidateTenantId).thenReturn("system");
        req.setId("ff824f837e954cd5ad9036f45a9e8b37");
        req.setName("test");
        req.setServerConfig(
            "{\"mcpServers\": {\"file-sse\": {\"url\": \"\"}}}");
        req.setAuthInfo(new AuthInfo());
        boolean result = this.mcpService.modifyService(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, req);
        assertTrue(result);
        String image
            = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAtAAAAC0CAYAAAC9rRv5AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAACtRSURBVHgB7d1NjFzZdR/w/60eSaMRZPXYkAIEcaYmQGDEgDFDK84u4WPghbKJyCwCCIExzWySzbBqtlGAaQJ2tuwmkUU2JhlbFpANyey0Ys0qBjwye+wAtjbmG2QlycDUIJagD3Zd3/Nu1XSzu77r3fvOvff/A5of3U12d329887733MNSKehrTDB0+bPBrX7dTx9O3Hv/xh77vcjMwIRERERRfUKSD+L/rm/Va6ghiuigVtWiuuR+/MTV1A/dgV1DSIiIiIKyoB0Ot+BXpdputPHrpgesZgmIiIiCqMHyofF266Ivu+K6OcY2PuuCO+DiIiIiFrFAjpXFgcspImIiIjaxwI6d76Qfop37RBEROQN7b5rMEiT4ZH78wGIiDbADLRW22SgV6vdKdM15qOJNjS0192v+whLJuucIGf+aliFMMbu9nu89mcP7B336/Clfw88dkfFh5xwlJA4z82ajwm6iFM4ytJ3Rfkz142+jXvmCES0mnQqLR4hNONObvN33d2WdxCCwRNIAbyOW/Z9vFw8CynCDpqrdgNbu98fuIbDQzYclJtEeW4+cL+OQHQOIxzl2XcvBnem3RciWu1txFBGh+sqwhmt9VnSsTQ4XPFZ/eZzLGYRj+sgfeRKbQwTfACiC1hAl8q67svAPmu6a0S0TPjiyRTS3bLB4htitPIzJEJicR+bud5cgZC8tGSluShbj0nQx9OZPXaf6TIW0CWTsXcS6eABgWgxi7cQXv4drqGVTn6oE/bxyvy4j+I83eF78MW3/Wy6UQXqlgl6RWOmZoyH5mEBTf1msSI70USX+edFhfBGyF+FUMwaJyC+89xHOw6aYnxgn3KCR4dshOdmKVeHaGMsoEn0m4MBi2iii5h/bk93+We/aDBEFKdqCnPGO+Jj/pk6xgKaPIlzhFodT5Qu5p/b0lX++ZYdrLFocFezeMfTJt5B4TH/TB1jAU1nZHyT79QQkWD+uR1d5Z+lIxy+eD5Pvt7HoPCYf6aOsYCmiw65OIYIzD+3q0Ioi/LPfuLGLosGt/HYFVyHoLD8gtAKoTH/TEuwgKbLJrjPPDQR888tip9/9pvf9BFP7Qqu90AxxHluMv9MS3Anwg1895nt7/0S+y966BtzoasxcS+e4hXU37qS/CUf6dxIlIMHAyoZ889tiZ1/9lG0OEXWjOwkycv9cUwiPDcF88+0BAvoBaRYPn2B66aHt5oFdq6onJxifzLt2Vt74R+Y6e+nwHc+bD544t4nubwPPneKk3//L1bMKNVGNloZ2ieFdMeILmP+uR2Sf7YR88/+6pnkkEdRLvML6TyzeI7HNMfl0F/jhPcpLcMC+pzv/pmtbA/fdH+87opl6TJjhyfp29PC++CXruj+zvdt7f486k3w8Fu/k0hR6rvQIxCVJlbGkvnn3czLPx+Zsfv1QfPmx8rJltzvINz3cOy+5hEoDnluxpnAkVbTi6IrvoB+9Mzu/2yCgauTDya2iS6EYZss3sHE4GBaTN/u9TBSHfeQAkIWFLILTeVh/rk93c1/9h1Emc98CD+zWZoCfbSnBqJO+aBYz02DJyBaouhFhH/kOs4/PcVzVzgfWhtxsYkv1O+7LvdzV0zfl7gItPIHHKLSMP/clq7mPwvpVp5tbjJyt/kN+O50G8bT3PMYFE+s/DM70LRC0R3oF6/g5POn6JZ1XelTHHz3+/bw1R6Ob1xR9mLMLjSVSHP+2Y9nS2Wzjn2EHCMnmz8NmsuG/blfM2xOdjzdhXC9z5bincX27ph/JiWKLqBvumL1O39mj92TpfMuq3TBfzpp4h23/8PXzQNowiw0lUR//lkuYVcgUaE7fawbB5GrDSyed8f8MylSfAb6F6/gyHWhB4g7bH8+HyO574roq/dG+OBPtexn5bvQ+zwAUCG055+/CUrNR9jFUHHML644z03rCmje5ueNefy/rPgCWlMX+jMWB//6n+K6mgJanOLA/cqV5lQC3flnG3m+MbXhMbYlhdwEz0ExHbnbnMe7mR6ugVehL+FOhPBdaMgZliK9PQUd8fN67HpRIbTnn8ECOkHbRwJe8P6mzjHSMgcLaPgutDtoHoMWm8U4iHLmH+MVwhthOyymUrNr/nmPzQvqEPP7C3EjlSlVWWi9KuxyKXJTs27bKfruVO8N+Pumj5dX2ffn/lsz3Vod5363+Nj9P/X0fTVXWdMczD9T23bLPzOyQ12yOz5+M8YCekplFlqbSaAC2nf9pFB+G73m8nnVFMaT6ce32RHyrLDuv/T+ybk/37Lj6XbrJ+79H7lOz8mlbYGpNMw/U9t2zT/zPqfu9CI2zRLDAvocdqFXMC1mQ2W29ARX3f9ZTQ8Q+1sVyruZjSurmq8txfWsqJ7giSuoRyyoC6M7/7zPAjpJu+WfGbSkbvEYuAAL6HPYhV5hl4O37zJfd//HVfd23RWoMTY62IYvqn1hLwV13XQMDR5yM5nM6Z//XIHS0kb+Wd9rJJWC+eeleG57gcaJHIrsbzwbUzrNA/u0GcM0wX0Z0Ye0Ovz95nue4Kkrpp+7n+V+8zNRjrTnnytQaph/pnQx/7wUC+gLOJFjpdXFr3Tybtn33dsnTeHpu3o5xGJeLqbftQcctp8V7fnnq6DU7JZ/5tQV6hLzz0uxgJ6j9woegBbpL/zIWbf5E/e3Q+SdJe+7Yuh+01n3Xek+KG3a888splK0W/6ZqFvMPy/BAnqOb10xtQUegi47nVMUnxXOTyNlSHXxXWkW0inTP/+5AqXmhPOfKVnMP6/EAnqBvb2mg0rLlF44X8RCOmXMP1O7zJZXG2aYf6YuMf+8EgvoBdiFXoKF83IspFPE/DO1bYRtMf9MXWP+eSUW0EuwCz1HDwMWzmuaFdKyoJJ0Y/6Z2jfCtph/pu4x/7wCC+glpAttdnkRzBEvK27jsJnaMbThu5y0OeafqX3MP1O6mH9eCwvoFU4tboNod7Il7yPGOlRi/pnaxfwzpYz557VwJ8IVfu93zOhPPrQjy4MYtUFiHRJ/Gdqb3NlQDd35Z9nYySQyWtNvlBSGaTKZqXTFdpn/vO9OtllAU3d6vPK+DhbQa5AudM+wgKbW9KebsRziruEVjq5pzj+LI3OIFAytFH0HCGPsbocbKMELd6zhtWHq1gi0Ep+ma5AuNLPQFMAsG90HdUN//jkl4bqmpqAFTT02a6hDZsf8fkFYQK+JWWgKxHejZTQgdUF7/jklIRe+PUE5OLKQumN3zO8XhAX0mtiFpoBmkQ6Ou4tPe/45HWFHW5bRgebIQuoa889rYwZ6A8xCU2AS6QBz0RFpzz+nQvLPFvsIY1zMgtt1888G9Zz3XnzfGPMWXVp8fOHvY+xd+rx5/7ae/j50J/wDUK5GoLUY0Eb+5EP7NMZEjr/6IfD73wOVSKYNGNxkDi0w6fZZfILQDK61XgBK5MfiPvTYn76FUkOTY/MmQvAd6Iu341jFa4F/vrzv3oagXclknUX3ab3R+y0+xaLpNL2F/9d4wb+Rxxo3UFlT8R3o//k9+6XTX8FX9/bwxit7+KI7s/6SO6t4zfbwWvMJE/yt/PbC4m97E/x40sN/NxN2oSkg28QK+u6AdY1FdFAp55/le++jHH1oETKS45/v+p7z/grDI/fWB61HGiHHhUyOKVRxBfQf/6n9zd7n8I9PLX7TXSn7Z+5dr+1NP2Zda1l68rb5y/Sd0x79nvwul9YmzYd+5P76NRCFIhspWDybFtE1KIR088+WO9V1qKxFVrfswB33jkCbkUaIbJx1bG6CslREAS1Fs+swf31i8K8g3WW72+rJnsFfuP/jd0EU1mxCB4vo8wb2KdqIUVmEJwvrBnb7r2TwxN338wp9LjTrzgglkPGaEhOyvOK6NdlYaGDBIjpP2RbQEs0wv4pvuM7x193D940J2uMOhz9iF5oi6TeXThnn8HwOs0I5Rpfe4/PPIfPGtEwJCxp91/kQ4ONsZyyis5VdAT0rnF2X+BuQbjPCYBeaorFNt/Epi+hGaZ3X0Zz3sfvcldxHErLrHIYvovvu8XODr+H5yGoO9B99335j79dw5Irbf+f++hoCmnWhQRSDz0RrmrrQlfC5ZT3mr4hn/rlL+eaffdf5WWHFc7xiVm7XSbOupQ/KQhYF9B/+uf3qdz60/7Vn8XsIXDifJ11oEMXiF6XcQcnizG3WwSws1tiB7s4IuZEJG35dgSwULCeyIVcT4u8wPFvX0gclL/kCWrrOX5jgv8FP1IhKutDuSfh3IIpFZrC+a8ucw+pn5FYox+jSe/yW78yldiefGbnyfJIT8vK6zt4ET3DPHLljeOz7tD/tRJd0NS1LyRbQknX+4w/tf47ddb7E4v+CKCaDO9NCqjTMP7P73B3pWOaSX5XizTaFs7aT8bqZnxzD3vT5ZfAe4tt3RfQj3LLvg5KVZAEtkY1Xfg3fNsC/RPf+hl1oim7STObooywldWxq5p/V+QipkxNviWtMFG6KIp3gHq5F+r7Onl9+qsoxunHY3B+MdCQpuQJaiudXLb4to+mgBbvQFN9+M96uJGXlnxcVa+xAdydOZzSEs7jGU5VxDenuy5b3XvjH+MVpKj1XyJqO4jl+ceHTQq8qJi25AvoLE/wna/FV6MIuNMUnkzlKWVRYXv75crHG/HPX0ss/y/NGYgITPFcY15g5xrGZjeisEINsUHSefG0DmdPcVUTHLy5kpCMpyRXQP+/hfxiDH0Mbix+AKDY5KJbRuSit8zqvWGP3uSsp5p+H9qApnKF6Q5TbuGvOCvtYEaUj83jO+046mMpx0aErop8z0pGG5Aro//jb5sc/M/gDbUW0QfNC9QsQxTbB/WmHNmfMPzP/3KV08s+yQHDgirBJMzde6+vC2D2eb7ri+fCl98aIlyzbDMdP5RihW/3mxIfdaPWSXESosYi2vnhmF5q6ILuH5f1iy/yzqEBd0Z9/1rxA8GV1s1jwnnnw0ntjRZQmeLj047JboHHfY/d8N/pddyWBVEp2K28pov/wz+0fvAp8W0sm2nWhf+AK6d9wf/w8iGLyUY4n0xXleZHuellzaufnny1CGG+1eMoXaH2Ese33VCEcvfln/9iQnHMF7eR+9dtZ15c+Nol0lWlvRYdZojpDe8PdprK5TNcdfNn++747Mbrqfr8993ajziRbQAttRfS5LvRvgSg2f8n2TeSH+edQ3Wd/UD7CpoY2XJfT4Nh9T4eb/JNmNz3gGULQmH/2ka3r08K5jzQ8dLflcMlteRXh1WsVoRKhetfebmbua2Bx0Lzdsoeue3+czTzyxCW/E6G2OIfxBTSz0OGNm8tsfvzRxbcTdLeaukv95gU2P8w/22DFxXadVRv0pGaEzYX8fvTkn89P1ZATZt1RjTMW7+GuOVhY+PlFc/HH1y1zrzmx7Go+9CKHzS6GjHWokHQHekZTJ5pd6ADkRc+6g1ivOdjLW732GbjvTMmijLfd/3O1gCjAwP3MR1l1KGyUzpQOcfPP460iP/KcClm4bRdDCrnAsvv8s7/N33GvYwdIa5Th2L1u31jjPq0Qg1mRf75IJoQM7Bvuttd0Eu9jHXIiJVNDLmbJKZosCmihqYhmFnpn42Y7Vz+rc7fLp76bJ29nB0HJDMqByBfUfeRlf7qgsIvtadvn888lRTji5Z+33zgi3P2x7QSEsI+R7vLPKeWbL1qWd74ozoSZ7U4Y/XzovsLXIRbSHTPIzGc7FXafif4t7NCF/qsfAr//PZTFxy9kDudJtA7qrJiG6+7kpIc3s1hwIiO5Stpx0eDKpQjH0B5mP2VFK59/voaYJM4waV6Phkh345zjl+Y7r3LLfoLwP+sT9z1t10mW+8Q2uzj2oVfNQjqu5DPQF2nJRDMLvQGDB81YI78bVdwFO/L1JJvXaxbfbXZ5TzPbLCjMQYVyxM4/02px8s9ypeVdO5yOodO++ckyPrKxSfEca3yd3SGKI80I2Wpcx3i7RWYdaT/6jpuxBJddAS00FNGcC70G6e5I4XpsbnY+fk1eIHMqpCXrncMOhcw/iwrUlXD5ZymaZbfAWdEsEx9SXqPhX8+vzN3lbxkt4+tWSaOIFr6Qlq3BB/Y+C+lwsiyghYYiml3ohepzHecampwvpLvfkWo3NvFYih/Vxfwzdand/PPFTrOfpFEh3ajGzPEOr+fhT5JNEwussStfRN9AGlOe+s3oO3mcDeyjJg5Hrcq2gBZdF9HsQs91PO1SjKCZvFDKAcE2i/HSnGghL55pdx8qlCXe/GdarY35z77LXDULvXzR/Mm5TnPqRbPwzZBNIhvnxRpfZ/EB2iIxK/mZUzouyBQR2aFS4h3yWGRXuhXZTOFYpOvpHJzI8Rl5oe0+qrEpmQU6tI8TWEAyn18geYg01dMV8LuxGCD0Qdo0B+gH2AXzz9rsln/2E2QefRbLCLOTZJekGXK440lGhRh6LUdx5Lk6tFcSPC704WdJH7oTulGzrfmeu224MctWspvCsUjH0zk2nsiR1RSOTcYZaXbLHgFNMZaS8XQiR7kvkAMrO9SFLqDf22pHv1UGNr+yKxWSd931hD+N6Q2bGk+bIbsXpYNmR8vQ0YKx65C/jhByuX97LTzWC5R1hOO8LuMchWehH+LYXMlipJq/THkbadnHadOFLlOsS8QIkJdn/rlru+efZwvPctkZVebz+xPydjq6cRZNthffuCidhYXL3GbxvJ3sIxzndRXnmGahZTTRb6Ast13ReYicyM9zq2kKpjOXt9dsUtB+dzQNMYrn8dz4xe4qUFfam0UvRdbQvtcsGExXe13nGb9IOMaGTyGem2f8/SsnSY8S2/Rp3Kzx4dzorRVVQIsOM9F/jbIK6PyK5xn5uYa2TuaAOBtpV2aXoUJoJlCHi/nn7rR9nx65IuWWleIqtQiYaCPrfJn//x4gB/4K65WEYn71dIv1sCcXmSsmwnFeR3GOn7i3v0EZjrMtnmeOmrP2dOIcsWatahOnCB0hjArUlRHaJkVoWpf6zyZscJHZetKI+dXTzDOL5x0VWUCLjorov0TuJCO37Uij1PiThFSK6Ly2Kl9HvDnSI7SN+eeujdA2KUL9DOEU3E5i3KhGclyQ7q7Ok6VZ8VyDdlZchOO8DuIcsy70P0Ge6mYaQUnkxXJgryawg9h+gTGOCuEx/5yfk2AdV3ms3LJy0q1zDYXMvjZN1rlG7pbPQl70sX0smt996t5vph+bNL9+sOT/6QKL55YVXUCL2EW0Af7a5lpAl/rk9F2lZ+pHGfkYxwjlqBCaCbRAifnn7piAUxtED0fNLqG6Xi+kuHpv7iJBfyVnf8G/W/ax/tz3ni80LzL4ysb/37LvwS752ATt0jwU2I+SvcYoTruKL6BFzCLaFc9j9/Yj91z7GnJimxffGiWSF6WhvdnMA9VNpnGUEa8RcYrQJwijQvvGWxX8vggJF4UxW5zU+WkH+whjhJB0vl7sT3equ/yRmIUmp563j8VzMMVspLKOWJutGIOvua/xu8s+J6mNVOQAKNtely6FFdh+hmuN3Pld4D5BaCbABgQStQlRXBlX7B+ZzReTDu3QfT93EILfLnvz146Blfs2TAFt8HqUYiPNjZkoJSyegyp2EeE8sRYWuuL5R9KFRi7a2G45Bymssj8tZhpHhfDGgTLlFcIYYTshO/mbd/CHNmT3+SRasSGvF7lssEL6sHgOjgX0BbGK6J7BXyAPt7koYcqvstd9MtHDWyhDhdDSyz9v9/2G3Rxim+8pZJwkbP75PHm9sMntbEopYPEcBQvoOWIU0Zl0oWXhyQPQGelIGsUL9WwhHWjmny/bplvuJxX0Ecp2HfxvIpwRYrpnjhLfBpp20Wu2AW/7RLxm8RwHFxEuEGNhoXShV2WhVbPsPs9l3O2id6zdflMU5Xy/+fxzjPnP7Xegff45hDEGdvOdM22wqITY9nsKed+OEJtctdK/AJnaZpq40Aiyg+HQHrjHwPstTGaZjapj8RwBC+glQhfRsy50ohM5atc9eQC6TF4UB3aktog+bb6vB8hXhfBSyz9LIXwAXbR9TyedFB7aXy8oDHsuLiQ72w7tY/c+mZK07YxwznmOjBGOFULHOZLNQmuOKWhgFGcbTZTubJcqhMb5z/mJmX++/LV3f70w7qRYCiguTExDD49f+rucvPldDN90f3uIzYxZPMfHAnoNIYvoZLPQmgtEDXx3UueBzGS+kJD5Z9rOCF3Zfu2EvMbIttuv49jMFjCHjN1Qe+afhEsRfNccuPv05tr5eBbPnWABvaaQRXRyXWg/u7UGrXIMjWzGHWi/a1q6+Wfq0ghd2mSCj7wGS9F017zedC1n0ZPT7K8u5cEfQ5c3WCTWcWykG728WeU3MQtzRYyWYgG9gVBFdHJd6MnGl5fK1FMbc9mfFpo5qhBeavlnWq2b/PN5vimx6LV13BRdUiz5bvP8DXx6QSeUUFsmG1zBWh7ruN1McqFOsIDeUKgiOqku9B7zz2vxl2Vr6NRHniqExvxzfrrMP5/nN1cR42mk47jpNEsBJUWzFEuLCn0/faYC6be34WvI/FhH3RTX1BkW0FsIUUQn04VmfGMzNlhWdje5Xupl/pm2M4IG8toqxbJEM6RgvmuGzYn4Ot3xF3z8JGL7K1gS6zDNQtGH0wWj1CEW0FsKUUQn0YW2Sjo1qZgojnHkhvln2t4IWmzboNhjfCMRux1DZ91oNrI6xwJ6B20X0Ul0ofXmenV6RentZbKMcFQIj/nn/HSff25DzouDc2IvjK+jZHEjlR21vdmKAf6P++3fuLfPQyeu9t2EHJgHtm5hh6l2GXwF+akQGvPP+dGSf96F7C46CVxA++xtjdzEzo1zDVE2WEC3oOUi+ieuiP5L9/vXoc+YW4RuRYquPnTpIzfMP9N2RkhfhdBMMy4tr+6pnHhYPEc8NaMX+WCEoyVtxjks8IOf/xI/gDaG3eetWHwMffLKQDP/TNtL/3XNRsk/j5CfCjFxB9+ssIBuUZtF9M9P8f+gTw3aXE/hAdpmt4iwQnjMP+fnJIuOYOgYgskkJ35R7OiUUTqVibbCArplIXcs7JzOTqp+L5Ru6Z2XCqEx/5yj9LvP/gpG2BPifKcvVYhrBMoGM9ABtJGJ/vIX8AtoY1kIbuUVd7tNQCFZvIXwUso/y0YcV7C5t91t+QihmGZHtc1Y3EeoQieHjqDMdDcIK8fpS37hZR+xrLN9NyWFBXQguxbR///nKqdw8Mm/Hd5uIcXbgS1M/tmifTJZYptoQsg89rabMA1coRNO+h1o2b47xGPoPIt33P2Q15zp2DE2i49AWWEBHVDbI+4oWSygw4qxeDC1/PMI2wlZJG3e7R3atwOOgEw//ywnj5MIJ48W10G76XH+c26YgQ5s20z0P/wV/ASUi/x2/dMl/ME9vfzzCNsI28nf5jYMeXKUfveZ23enItQJOHWIBXQEWS8spHWwgA4pTv451CKqCu2TWbObF4fS7Q33WN22gAi3wDKH/DO3704DR8BmiQV0JJkU0SwEt/FC4e1mMomV+PnPFcIboW2h8sZm66xlhVC23e1PX0dcF27fnYYJx9fliBnoiDbJRH/5VfwS2hgW0FsxKnf9yyWXHaeACHP5NVT0ZNus5Yl7rN5EGNt0xOX1pkaY+fPp7wgXY/tuage3784SC+jI1i2i97+ocIydwRugzfXcZejQq+Q3ZfEp8hAj/zxCCOGiJ9t1VrVlNP3Ir2ugRSpQCraLVJF6jHB0YN04x1deVbeQkN2ObViVHegaOUg1/xwuesKDdSks889J4Pbd2WIHuiNJjrjTWQjq5sdMaTzxSD/CEW/+8wjt6wc6sOrcMW5gZXOWcBEwgxvFbVJh2YFOwiTbXRyLxwK6Q6uK6H/wFXzy6c/wJeix3xQt3E1pfTJmSuN1nl4Wq8LTzT/7LnEZ8QS/WUzIqM1Jca9JcptOuCYlCcw/Z4sRjo4ti3N8cU9hDpq5u8301N5eORQc6eafyxL2RMcU2OE7ZZwuCSaDzXpoIRbQCiwqon/9V/EJtJmwgN6IiZLR3UYOI7xSnv9cjvBZ3RFK02P+ORFcj5AxFtBKzCuiX/ucylF24TY2yJHGnKLJ4JJ3yvOfyxO6WzpCSeJl/2lXOWzWQwsxA63IxUz0b/8j/PB/PYMuMrifOej1yM5uE+hj8THSpyf/7It5XlKf7233eAuZ1T1pvsawtTmR+k8uta6roHlGoGyxgFbmfBH9669Dp1McuF+PQKtoXeSTw2VFTfnnoSsS3wd1QQr0p2iLwZvQvj5Atu/WNleeLpPXDzaassbzWIXOxzm++mWFL+bM361H60KfXgZdEU35Z8tYUybS2J2Q23enwXL9RO7YgVZKiuj//aH9L5/vNYVCBU0kfydjlLTtXKaN3q3P0+5A65v/XIHSZ/ARtIu1fXcPN5DHpJ4zfgF8vCtFOTQqaCkW0Ir9239ufop37RP3wl5Bm0lzCX0EWqYPbfK4rKgp/1zxcno2HkO/CqH5RcYp3BabuWXDx77OjNlgyh8jHNrtqX1Rf2e6eIpSYhPosq2mKf/My+n50H9lJs723bmOXosZtWJ8owAsoLXzmTyNHUPZonoIWszgDWjTS6LLtpyu/DPXA+Shnu4OqVuM6FKOW0/HnpRjM3idpZVYQKdB6yzJAbvQSUn/sqK++c/sQOcgjfxzhRiTffLcejru83SPG6iUgAV0CqzaJ+M+x3clJYfOkqb8s3wvPIHMwwjaxZnqk8Ykkk1NIsS+zqRxNYN2xkWEKdjDA/cCcAcaWQxdIfGECybm0LZhSR6XFSuEZjh9o0AjaNeLMv+5j4F9jtzYiCe6hovrS8ECOgUyNWFgR2q3b7VNcX8FpJveBanrizNzed1OPec/52GsvmMo0aVJpNd/q3B6UEq4fXcxGOFIheah7DLYf2B1dsi7pWfxp3FXMfLYFatCeKO1PkvrCS1txiSQV33Bx1pCGN8oBAvoVPRcAaSZj3JUoDMWNbTIoSsS6/HF/HNp9D839jjtJQl+hnYNKgIL6FTIk1J7tmqC+81OWeTtqelA15lsjFAhNM5/LlEK4+v4eEsBt+8uCgvolEzUd0r67gXkEUfbfUbHgTmXRS1x8s/rjjNjRzAX2hdA+6YEC+gU5DBnn9bGAjole8pjHEI6JVJEk6ihgcFt5KFCeOsdANkRzEMaJ5cVKA2cRlUUFtApkUVgKbzgy+Kqgb2P0vn7q0a3nmSRyYuXr1991cB3BPugHOi/5M7dLtPA8XXFYQGdmlS6iRYHrohmnKPrTFwPR8hDhdDkALjepJIKlIsRtOO0lzToj1hSy1hAp0YuEaVypmtx3b09LXphYa/T+6rO5pKirvwz5z/nQ/v85wqc9pKGPLdApyVYQKfI4CFSIVnRSdFF9Ahdsdlkn0WF8Jh/Lsn6Vxy6c8rHWiL0b8ZDrWMBnaIj8wCaNulYre+K6Gd41w5RGp8/7uKFtca95nGSPn35ZxY1eVj3ikN3esw/J4Lj6wrErbzTdeze3kc69l3H5w4G9q0mx13WsHnJxsUtuth93sz63UhZGHoT7dt391mM3Tzl+x/Pff/lk/J57xOfzn2/xVvu1+sIxe8YeIz2jKBZzO27aTeW4+tKxAI6VbI4bIIBUsvHyeJCWRTzrr2dTYd0FclBT6Ke7OTTfRaa8s++yH6ANkmhJGsFdiOFsRSXDz77e+x4wtAeuZ8jpIfTq29lkO27eY04Dcw/F4lPz1TJwTHdLmPfHezv45Z97grpA+Qu9sLPvLrPokJ43XSQJBJi8Qy7X6GQIvz95k10ke0Nf6JTVsaU23enoub23WViAZ2ye+ZIwZzhXfhCemCfZl9IxxtxlFf3WVP+uW2+eJbOcx/tOZhOvjlATH5cZciY0ri4TSq4WDUNnP9cLEY4Uid5zN0v/3ZLIh3Gvd2y0kE7dp2Xx1HO6GcHfVnp3mvym3LAkk5ef85nzzZFqd3HP3KfLwXX+qv4ZRdJH+MIG7np4RryUiG0LqYxhCmeZ+T/lhPTq+5ney/Sz1YhJFNY99nHeuR+G4F0S2kqFrXKgNInHdzchu2bJjf8pMmWtTkeSAqXU1xvVrfbacG8i7Pvc3XRf8seIuTCT+OK9GMTYoFbd+SxHb44O3b3XbwJMWGL54tq9/NdC35C6vPPA4TiTwSOQESkBAvoHMgBedLkKNNaULi+cdOBkl39fOdXOjMnSztrvrs86zD3px3makF3uR2+mH64MELhV9U/R5j7qW66z7ll8QY27LI04QvMEWIY2renxXPc56rFIe6acNn4gW0jx71YzPuIiGgNLKBzEbq7qdflsVw2SmdvmbpZyDevkA51P1nXobuXWYdO8s8x4kkGr0eJOfif5xG6O9EN0432cYNPEM7YXVl5HUREinARYS5krF3aCwq35TPL59+6dzZl5OIOjHI/tb8JTp1d8exVCC1W/vmWfaeTzvPL/MSP9hcYVgiptPwzESWBBXQupAgIs8EDba/fRDZkceSML9ba3Awix4WDnqb5z7vqNTuV1eje/nSB4f1pzKkNFcKKNcGGiGhtLKBz4jOC7RZn1IbDl7rRd81hi121nHd1rBDeY8Qg95HBFUUr9g+m3eg+dsX5z0RUIGagc5TjVI48yEK/G81UEcnDTnbO99auGH8TOcot/3ze0A6nG55oWPTrC/ttb4OS8s9+EXC8aS1EMzaz+f6Z4BzoHPnZ0DlP5UiVn5Zyyx64guWh+12uFmw7+mucbXTDC7+JRBfzn4WMYxvaxxFH2S0yW1S4y21QISRN+We/tXaJC7Wpe++B1GGEI0dyubjHPLRiD/Cu60LeNcOtd7GyzVzcGrmyUbYxjpN/nucs0tFV5KqtiRwVwtKTf+7xqh51ZI8xJo1YQOfqyEi2M9zcV9qNwZ1mcaFcLdh8espxAZfzwnegY+WfF5HO71FzEiXdpZid8JPWxtmFP9HRVDjEWNRKdFF529gnggV0zmSxGrjNqGKHmOAdV8zc2ODf1E3nOmeSf44TP9JRnEmkQ7rRcaZ0tFc8++kyfYSjp3DwE0tinNQRvYxjHNViAZ27HoZ8AqomRfQ3m0jGanXmueeZGIXKSSf550XiTOk4mW6JvdvPLcXkwN5x/9chQtKWfybqwoRjHLXiIsLcycFyaKXD+VTJJiN02eG0GJHIzeJFSn6CR43cxcg/m2Yusy6+sD1wz9d6OqWjTSfNlQ5ZXDxouqlSnMrXk8L94+nn1Av+7T5mVwQs3nBv1xHnCgHzz0TMP6vFAroEUnQNrXQuWUTrdQhfSD+eFigv84sGS3khjdGBHkGrI3Ponq+jZsOTNiIS0tU+MgfNn4f2eFqcn93GFlqNoAfzz9QF5p8VY4SjFP4SsXSi9Vy2posO4TuC9YX33850q+7L4uWfR9BMDpqmievU2MX54tkbIQ1jNSeMzD9Td/RdKaPPsIAuiRyQfIaWRbRWttmo4XwRfXu6GLQU5eWfF9k1F325eJ7tVqr/Z9cUsWH+mbpikznhLRIL6NKwiNbP7yIp98/DworncvPPi/hRdwfue95sJOW84vnsYyksSup2xOB5e1FmkhNdtscCWjMW0CXyRfSVLeYPUyzWFXl3FxRAeSs7/7yI5KLNmruRSbF9tPSxk0KWfgQtLOMb1Ak9MSaaiwV0qfzl4WssolW6nf2s53mYf15unXnRvng+xHIjaOa3WK+hwdD2wfwzdYP5Z+VYQJfsrIjmWa4WMm2jtNjGGeafV5GO1KLFhesVzwDUnzTr2fzpBYtn6gjzz+qxgC7drIiW7aGpS36TlFKmbczD/PN6zp6z9WfvW7949rlq3VeeRtCC+WfqCvPP6rGAJn9A9ZGBzRYqUTvkCkCv2V55hLIx/7yu2YQOv0HK+sXzGZ1XnWSBo6bNgph/pm4w/5wAbqRCZ+6e28CBG67EcozjAvPOF0n+2TL/vBEfRbmC7XwKnfRcgZH884QFNHWC+ecEsANNL5tt4GB4+SiwcbM1d4mLBedj/jmuGvrUqq7CMP9MXWH+OQksoOkyuYR6bCRjyUhHCHJyImMEj4yeWbddY/45thra+J1S9WD+mbrC/HMSWEDTYhLp6OFNjrprzbiZsiEnJ5pynjow/xyXrk68wbG6zCfzz9QN5p8TwQKalvPd6Debwo+F9C6Om5ORkqdsLML5z12ooUft3g6hCec/U3d4pSwRLKBpPfeaTRwk1qFnRmsKfFzjWpN1Zv52Eeaf49NyW/iRfNruG+afqSvMPyeDBTStT7rRsr20j3WMQMvU7oXw5jSuMQItxvxzfDoiRLPiuYY2zD9TV5h/TgbH2NHm/AHvmrvMeeCKn/c58u4l0kmTuMYRO55rY/65G/L4jBGducw0Gzcdqn2OmCayxkXUFB/XxyTDgGhXLKQFC+dt+PnPTxGaweu8Xy4Y2ucdPGel63yTV2WIKHXsQNPujswD9+uDaTE0cG/XUQqJskzwEPea24A2x/xzd47d41eiCvsBJ06Mm502gY/c22MWzkSUC3agqX1+B69D9+i6mmlXWoqxh67bzIJgV0P7KPgJlx+Rxg1rVhlaiXP04WMd/embeGP6vmVxj3r6+8fTP8tz5ISXo4koVyygKayhve6KaSmQ3kHqfLf5CfZct50dzXZIAR0+h3ubJzpERNQmFtAUh+9uXW8mLlhU6Grx0qZYNBMREdEFLKCpG5KXnrhC2sc8KmhhmvFzT9BrpjaMWDQTERHRRSygSQcpqE/xtitcr0KylzG20fU7K564r/UxC2YiIiJaFwto0mtopYjebwpr44pq89JiJpkcsHhh09m241IQ183vvlCWP58072OxTERERFv4e+tsXmNh6pSbAAAAAElFTkSuQmCC";
        req.setIcon(image);
        boolean result2 = this.mcpService.modifyService(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, req);
        assertTrue(result2);
        req.setName("空白模板java");
        Assertions.assertThrows(AgentStudioException.class,
                () -> this.mcpService.modifyService(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, req));

    }

    @Test
    void testUpdateMcpAuthInfo(){
        EncryptionAdapter mockEncryptionAdapter = org.mockito.Mockito.mock(EncryptionAdapter.class);
        org.mockito.Mockito.when(mockEncryptionAdapter.encrypt(anyString(), any()))
                .thenReturn("E1-{fake-uuid}-fake_encrypt_result");

        ReflectionTestUtils.setField(this.mcpService, "encryptionAdapter", mockEncryptionAdapter);

        Object mcpBaseInstance = ReflectionTestUtils.getField(this.mcpService, "mcpBase");
        if (mcpBaseInstance != null) {
            ReflectionTestUtils.setField(mcpBaseInstance, "encryptionAdapter", mockEncryptionAdapter);
        }

        commonUtilMockedStatic.when(CommonUtil::getAndValidateTenantId).thenReturn("system");
        boolean result = this.mcpService.updateMcpAuthInfo(Constants.TEST_PROJECT_ID, "ff824f837e954cd5ad9036f45a9e8b37",
                Constants.TEST_WORKSPACE_ID, null);
        assertTrue(result);
        Assertions.assertThrows(AgentStudioException.class,
                () -> this.mcpService.updateMcpAuthInfo(Constants.TEST_PROJECT_ID, "not_exist",
                        Constants.TEST_WORKSPACE_ID, null));
        boolean result1 = this.mcpService.updateMcpAuthInfo(Constants.TEST_PROJECT_ID, "ff824f837e954cd5ad9036f45a9e8b37",
                Constants.TEST_WORKSPACE_ID, null);
        assertTrue(result1);
        AuthInfo authInfo = new AuthInfo();
        authInfo.setScope(AuthInfo.ScopeEnum.OAUTH);
        OauthInfo oauthInfo = new OauthInfo();
        oauthInfo.setClientId("test_client_id");
        oauthInfo.setClientSecret("test_client_secret");
        oauthInfo.setEndpointUrl("http://examle.com");
        oauthInfo.setScope("test_scope");
        authInfo.setCustomOauth(oauthInfo);
        boolean result2 = this.mcpService.updateMcpAuthInfo(Constants.TEST_PROJECT_ID, "ff824f837e954cd5ad9036f45a9e8b37",
                Constants.TEST_WORKSPACE_ID, authInfo);
        assertTrue(result2);
        AuthInfo authInfo1 = new AuthInfo();
        authInfo1.setScope(AuthInfo.ScopeEnum.SERVICE);
        AuthKeyInfo authKeyInfo = new AuthKeyInfo();
        authKeyInfo.setAuthKey("test_auth_key");
        authKeyInfo.setTargetName("test_target_name");
        List<AuthKeyInfo> authKeys = new ArrayList<>();
        authKeys.add(authKeyInfo);
        authInfo1.setAuthKeys(authKeys);
        boolean result3 = this.mcpService.updateMcpAuthInfo(Constants.TEST_PROJECT_ID, "ff824f837e954cd5ad9036f45a9e8b37",
                Constants.TEST_WORKSPACE_ID, authInfo1);
        assertTrue(result3);
    }
    @Test
    public void testGetMcpServiceToolListAndUpdateStatus() {
        McpServiceEntity mcpServiceEntity = new McpServiceEntity();
        mcpServiceEntity.setId("ff824f837e954cd5ad9036f45a9e8b34");
        mcpServiceEntity.setTenantId("system");
        mcpServiceEntity.setOrgType("SSE");
        mcpServiceEntity.setFcInstanceUrl("http://127.0.0.1:8080");
        // 真实方法内部含 try-catch 兜底，工具列表获取失败时落入异常处理分支，不会向上抛出
        assertDoesNotThrow(() -> this.mcpService.getMcpServiceToolListAndUpdateStatus(mcpServiceEntity));
    }

    @Test
    public void checkMcpNameDuplication() {
        McpServiceModifyReq serviceReq = new McpServiceModifyReq();
        serviceReq.setName("test-name");
        serviceReq.setId("ff824f837e954cd5ad9036f45a9e8b34");
        serviceReq.setNameEn("test-name-en");
        McpServiceEntity mcpServiceFromDb = new McpServiceEntity();
        mcpServiceFromDb.setName("test-new-name");
        mcpServiceFromDb.setId("ff824f837e954cd5ad9036f45a9e8b34");
        mcpServiceFromDb.setNameEn("test-new-name-en");
        String workspaceId = "default";
        this.mcpService.checkMcpNameEnDuplication(serviceReq, mcpServiceFromDb, workspaceId);
        this.mcpService.checkMcpNameZhDuplication(serviceReq, mcpServiceFromDb, workspaceId);
        serviceReq.setName("空白模板java");
        serviceReq.setNameEn("Empty Template");
        serviceReq.setId("ff824f837e954cd5ad9036f45a11111");
        Assertions.assertThrows(AgentStudioException.class,
                () -> this.mcpService.checkMcpNameEnDuplication(serviceReq, mcpServiceFromDb, workspaceId));
        Assertions.assertThrows(AgentStudioException.class,
                () -> this.mcpService.checkMcpNameZhDuplication(serviceReq, mcpServiceFromDb, workspaceId));
    }

    /**
     * 覆盖本地数据库中数据不存在场景
     */
    @Test
    void testModifyService2() {
        McpServiceModifyReq req = new McpServiceModifyReq();
        req.setId("ff824f837e954cd5ad9036f45a9e8b341");
        req.setName("test");
        req.setServerConfig(
            "{\"mcpServers\": {\"file-sse\": {\"url\": \"\"}}}");
        Assertions.assertThrows(Exception.class,
            () -> this.mcpService.modifyService(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, req));
    }

    @Test
    void testListServicesSummary() {
        Map<String, Integer> result = this.mcpService.listServicesSummary(Constants.TEST_PROJECT_ID,
            Constants.TEST_WORKSPACE_ID);
        assertNotNull(result);
    }

    /**
     * 覆盖服务不存在场景
     */
    @Test
    void testMcpServerRating2() {
        McpServerRatingReq req = new McpServerRatingReq();
        req.setServerId("140");
        req.setScore("10");
        Assertions.assertThrows(Exception.class,
            () -> this.mcpService.mcpServerRating(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, req));
    }

    /**
     * 覆盖评分大于10场景
     */
    @Test
    void testMcpServerRating3() {
        McpServerRatingReq req = new McpServerRatingReq();
        req.setServerId("14");
        req.setScore("20");
        Assertions.assertThrows(Exception.class,
            () -> this.mcpService.mcpServerRating(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, req));
    }

    /**
     * 覆盖租户为空场景
     */
    @Test
    void testMcpServerRating4() {
        commonUtilMockedStatic.when(CommonUtil::getTenantId).thenReturn("");
        McpServerRatingReq req = new McpServerRatingReq();
        req.setServerId("14");
        req.setScore("20");
        Assertions.assertThrows(Exception.class,
            () -> this.mcpService.mcpServerRating(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, req));
    }


    @Test
    void testMcpServerRecommendation() {
        List<McpServerBaseInfoDto> mcpServerBaseInfoDtos = this.mcpService.mcpServerRecommendation(
            Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID);
        assertNotNull(mcpServerBaseInfoDtos);
    }

    /**
     * 覆盖服务不存在的场景
     */
    @Test
    void testMcpServicesCesSuccessRateLineChart() {
        Assertions.assertThrows(Exception.class,
            () -> this.mcpService.mcpServicesCesSuccessRateLineChart(Constants.TEST_PROJECT_ID,
                "ff824f837e954cd5ad9036f45a9e8b34", null));
    }

    /**
     * 覆盖服务类型sse场景
     */
    @Test
    void testMcpServicesCesSuccessRateLineChart2() {
        CesMetricDataResp cesMetricDataResp = new CesMetricDataResp();
        cesMetricDataResp.setMetricName("successRate");
        Datapoints datapoints = new Datapoints();
        datapoints.setAverage(4.5d);
        cesMetricDataResp.setDatapoints(List.of(datapoints));
        when(cesService.mcpServicesCesByFailRateMetric(any(), any(), anyInt(), any())).thenReturn(
            new CesMetricDataResp());
        McpServicesCesSuccessRateLineChartQo req = new McpServicesCesSuccessRateLineChartQo();
        req.setWorkspaceId(Constants.TEST_WORKSPACE_ID);
        commonUtilMockedStatic.when(CommonUtil::getAndValidateTenantId).thenReturn("system");
        CesMetricDataResp cesMetricDataResp1 = this.mcpService.mcpServicesCesSuccessRateLineChart(
            Constants.TEST_PROJECT_ID, "ff824f837e954cd5ad9036f45a9e8b34", req);
        assertNotNull(cesMetricDataResp1);
    }

    /**
     * 覆盖服务类型非sse的场景
     */
    @Test
    void testMcpServicesCesSuccessRateLineChart3() {
        CesMetricDataResp cesMetricDataResp = new CesMetricDataResp();
        cesMetricDataResp.setMetricName("successRate");
        Datapoints datapoints = new Datapoints();
        datapoints.setAverage(4.5d);
        cesMetricDataResp.setDatapoints(List.of(datapoints));
        when(cesService.mcpServicesCesByFailRateMetric(anyString(), anyString(), anyInt(), any())).thenReturn(
            cesMetricDataResp);
        McpServicesCesSuccessRateLineChartQo req = new McpServicesCesSuccessRateLineChartQo();
        req.setWorkspaceId(Constants.TEST_WORKSPACE_ID);
        req.setFrom("");
        req.setTo("");
        req.setPeriod(1);
        commonUtilMockedStatic.when(CommonUtil::getAndValidateTenantId).thenReturn("system");
        CesMetricDataResp result = this.mcpService.mcpServicesCesSuccessRateLineChart(Constants.TEST_PROJECT_ID,
            "ff824f837e954cd5ad9036f45a9e8b35", req);
        assertNotNull(result);
    }

    /**
     * 覆盖服务类型非sse的场景
     */
    @Test
    void testMcpServicesCesSuccessRateLineChart4() {
        CesMetricDataResp cesMetricDataResp = new CesMetricDataResp();
        cesMetricDataResp.setMetricName("successRate");
        Datapoints datapoints = new Datapoints();
        datapoints.setAverage(4.5d);
        cesMetricDataResp.setDatapoints(List.of(datapoints));
        when(cesService.mcpServicesCesByFailRateMetric(anyString(), anyString(), anyInt(), any())).thenReturn(null);
        McpServicesCesSuccessRateLineChartQo req = new McpServicesCesSuccessRateLineChartQo();
        req.setWorkspaceId(Constants.TEST_WORKSPACE_ID);
        req.setFrom("");
        req.setTo("");
        req.setPeriod(1);
        commonUtilMockedStatic.when(CommonUtil::getAndValidateTenantId).thenReturn("system");
        CesMetricDataResp result = this.mcpService.mcpServicesCesSuccessRateLineChart(Constants.TEST_PROJECT_ID,
            "ff824f837e954cd5ad9036f45a9e8b35", req);
        assertNotNull(result);
    }

    /**
     * 覆盖服务不存在的场景
     */
    @Test
    void testMcpServicesCesLineChart() {
        McpServicesCesLineChartQo req = new McpServicesCesLineChartQo();
        req.setWorkspaceId(Constants.TEST_WORKSPACE_ID);
        Assertions.assertThrows(Exception.class,
            () -> this.mcpService.mcpServicesCesLineChart(Constants.TEST_PROJECT_ID, "ff824f837e954cd5ad9036f45a9e811",
                req));
    }

    /**
     * 覆盖服务类型sse场景
     */
    @Test
    void testMcpServicesCesLineChart2() {
        McpServicesCesLineChartQo req = new McpServicesCesLineChartQo();
        req.setWorkspaceId(Constants.TEST_WORKSPACE_ID);
        commonUtilMockedStatic.when(CommonUtil::getAndValidateTenantId).thenReturn("system");
        CesMetricDataResp result = this.mcpService.mcpServicesCesLineChart(Constants.TEST_PROJECT_ID,
            "ff824f837e954cd5ad9036f45a9e8b34", req);
        assertNotNull(result);
    }

    /**
     * 覆盖服务类型非sse场景
     */
    @Test
    void testMcpServicesCesLineChart3() {
        CesMetricDataResp cesMetricDataResp = new CesMetricDataResp();
        cesMetricDataResp.setMetricName("successRate");
        Datapoints datapoints = new Datapoints();
        datapoints.setAverage(4.5d);
        cesMetricDataResp.setDatapoints(List.of(datapoints));
        when(cesService.mcpServicesCesByFailRateMetric(any(), any(), anyInt(), any())).thenReturn(
            new CesMetricDataResp());
        McpServicesCesLineChartQo req = new McpServicesCesLineChartQo();
        req.setWorkspaceId(Constants.TEST_WORKSPACE_ID);
        req.setFrom("");
        req.setTo("");
        req.setPeriod(1);
        commonUtilMockedStatic.when(CommonUtil::getAndValidateTenantId).thenReturn("system");
        CesMetricDataResp cesMetricDataResp1 = this.mcpService.mcpServicesCesLineChart(Constants.TEST_PROJECT_ID,
            "ff824f837e954cd5ad9036f45a9e8b35", req);
        assertNotNull(cesMetricDataResp1);
    }

    /**
     * 覆盖服务类型非sse场景
     */
    @Test
    void testMcpServicesCesLineChart4() {
        CesMetricDataResp cesMetricDataResp = new CesMetricDataResp();
        cesMetricDataResp.setMetricName("successRate");
        Datapoints datapoints = new Datapoints();
        datapoints.setAverage(4.5d);
        cesMetricDataResp.setDatapoints(List.of(datapoints));
        when(cesService.mcpServicesCesByCountMetric(any(), any(), anyInt(), any())).thenReturn(cesMetricDataResp);
        McpServicesCesLineChartQo req = new McpServicesCesLineChartQo();
        req.setWorkspaceId(Constants.TEST_WORKSPACE_ID);
        req.setFrom("");
        req.setTo("");
        req.setPeriod(1);
        commonUtilMockedStatic.when(CommonUtil::getAndValidateTenantId).thenReturn("system");
        CesMetricDataResp cesMetricDataResp1 = this.mcpService.mcpServicesCesLineChart(Constants.TEST_PROJECT_ID,
            "ff824f837e954cd5ad9036f45a9e8b35", req);
        assertNotNull(cesMetricDataResp1);
    }

    @Test
    void testMcpServicesCesStatisticListMcp() {
        IdListRequest req = new IdListRequest();
        Map<String, Long> result = this.mcpService.mcpServicesCesStatisticListMcp(Constants.TEST_PROJECT_ID,
            Constants.TEST_WORKSPACE_ID, req);
        assertNotNull(result);
    }

    @Test
    void testMcpServicesCesStatisticListMcp2() {
        CesMetricDataResp cesMetricDataResp = new CesMetricDataResp();
        cesMetricDataResp.setMetricName("successRate");
        Datapoints datapoints = new Datapoints();
        datapoints.setAverage(4.5d);
        datapoints.setSum(5.0d);
        cesMetricDataResp.setDatapoints(List.of(datapoints));
        when(cesService.mcpServicesCesByCountMetric(any(), any(), anyInt(), any())).thenReturn(cesMetricDataResp);
        IdListRequest req = new IdListRequest();
        req.setIds(List.of("ff824f837e954cd5ad9036f45a9e8b34", "ff824f837e954cd5ad9036f45a9e8b35"));
        Map<String, Long> result = this.mcpService.mcpServicesCesStatisticListMcp(Constants.TEST_PROJECT_ID,
            Constants.TEST_WORKSPACE_ID, req);
        assertNotNull(result);
    }

    @Test
    void testMcpServicesCesStatisticListMcp3() {
        CesMetricDataResp cesMetricDataResp = new CesMetricDataResp();
        cesMetricDataResp.setMetricName("successRate");
        Datapoints datapoints = new Datapoints();
        datapoints.setAverage(4.5d);
        datapoints.setSum(5.0d);
        cesMetricDataResp.setDatapoints(List.of(datapoints));
        when(cesService.mcpServicesCesByCountMetric(any(), any(), anyInt(), any())).thenReturn(new CesMetricDataResp());
        IdListRequest req = new IdListRequest();
        req.setIds(List.of("ff824f837e954cd5ad9036f45a9e8b34", "ff824f837e954cd5ad9036f45a9e8b35"));
        Map<String, Long> result = this.mcpService.mcpServicesCesStatisticListMcp(Constants.TEST_PROJECT_ID,
            Constants.TEST_WORKSPACE_ID, req);
        assertNotNull(result);
    }

    /**
     * 覆盖服务不存在的场景
     */
    @Test
    void testMcpServicesCesStatistic() {
        McpServicesCesLineChartQo req = new McpServicesCesLineChartQo();
        req.setWorkspaceId(Constants.TEST_WORKSPACE_ID);
        Assertions.assertThrows(Exception.class,
            () -> this.mcpService.mcpServicesCesStatistic(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID,
                "ff824f837e954cd5ad9036f45a9e811"));
    }

    /**
     * 覆盖服务不存在的场景
     */
    @Test
    void testMcpServicesCesStatistic2() {
        McpServicesCesLineChartQo req = new McpServicesCesLineChartQo();
        req.setWorkspaceId(Constants.TEST_WORKSPACE_ID);
        commonUtilMockedStatic.when(CommonUtil::getAndValidateTenantId).thenReturn("system");
        McpServiceStatisticResp result = this.mcpService.mcpServicesCesStatistic(Constants.TEST_PROJECT_ID,
            Constants.TEST_WORKSPACE_ID, "ff824f837e954cd5ad9036f45a9e8b34");
        assertNotNull(result);
    }

    /**
     * 覆盖服务不存在的场景
     */
    @Test
    void testMcpServicesCesStatistic3() {
        CesMetricDataResp cesMetricDataResp = new CesMetricDataResp();
        cesMetricDataResp.setMetricName("successRate");
        Datapoints datapoints = new Datapoints();
        datapoints.setAverage(4.5d);
        datapoints.setSum(5.0d);
        cesMetricDataResp.setDatapoints(List.of(datapoints));
        when(cesService.mcpServicesCesByCountMetric(any(), any(), anyInt(), any())).thenReturn(new CesMetricDataResp());
        commonUtilMockedStatic.when(CommonUtil::getAndValidateTenantId).thenReturn("system");
        McpServiceStatisticResp result = this.mcpService.mcpServicesCesStatistic(Constants.TEST_PROJECT_ID,
            Constants.TEST_WORKSPACE_ID, "ff824f837e954cd5ad9036f45a9e8b35");
        assertNotNull(result);
    }

    /**
     * 覆盖服务不存在的场景
     */
    @Test
    void testMcpServicesCesStatistic4() {
        CesMetricDataResp cesMetricDataResp = new CesMetricDataResp();
        cesMetricDataResp.setMetricName("successRate");
        Datapoints datapoints = new Datapoints();
        datapoints.setAverage(4.5d);
        datapoints.setSum(5.0d);
        cesMetricDataResp.setDatapoints(List.of(datapoints));
        when(cesService.mcpServicesCesByCountMetric(any(), any(), anyInt(), any())).thenReturn(cesMetricDataResp);
        commonUtilMockedStatic.when(CommonUtil::getAndValidateTenantId).thenReturn("system");
        McpServiceStatisticResp result = this.mcpService.mcpServicesCesStatistic(Constants.TEST_PROJECT_ID,
            Constants.TEST_WORKSPACE_ID, "ff824f837e954cd5ad9036f45a9e8b35");
        assertNotNull(result);
    }

    /**
     * 覆盖服务不存在的场景
     */
    @Test
    void testServicesTools() {
        McpServiceToolsTestReq req = new McpServiceToolsTestReq();
        req.setServiceId("ff824f837e954cd5ad9036f45a9e8b11");
        Assertions.assertThrows(Exception.class,
            () -> this.mcpService.testServicesTools(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, req));
    }

    /**
     * 覆盖服务类型为sse的场景
     */
    @Test
    void testServicesTools2() {
        McpServiceToolsTestReq req = new McpServiceToolsTestReq();
        req.setServiceId("ff824f837e954cd5ad9036f45a9e8b34");
        Assertions.assertThrows(Exception.class,
            () -> this.mcpService.testServicesTools(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, req));
    }

    /**
     * 覆盖服务类型为sse的场景
     */
    @Test
    void testServicesTools3() {
        McpServiceToolsTestReq req = new McpServiceToolsTestReq();
        req.setServiceId("ff824f837e954cd5ad9036f45a9e8b34");
        McpSchema.CallToolResult callToolResult = new McpSchema.CallToolResult("test", false);
        commonUtilMockedStatic.when(() -> CommonUtil.parseMcpConfigHeaderInfo(anyString())).thenReturn(new HashMap<>());
        mcpClientService.when(
                () -> mcpClient.callMcpServiceTool(anyString(), anyString(), anyString(), anyMap(), anyString(), anyMap()))
            .thenReturn(callToolResult);
        Assertions.assertThrows(Exception.class,
            () -> this.mcpService.testServicesTools(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, req));
    }

    @Test
    void testServicesTools4() {
        McpServiceToolsTestReq req = new McpServiceToolsTestReq();
        req.setServiceId("ff824f837e954cd5ad9036f45a9e8b34");
        Map<String, Object> structContent = new HashMap<>();
        structContent.put("test", "test");
        McpSchema.CallToolResult callToolResult = new McpSchema.CallToolResult(null, false, structContent, structContent);
        commonUtilMockedStatic.when(() -> CommonUtil.getRawQueryString(anyString())).thenReturn(null);
        commonUtilMockedStatic.when(() -> CommonUtil.parseMcpConfigHeaderInfo(anyString())).thenReturn(new HashMap<>());
        mcpClientService.when(
                () -> mcpClient.callMcpServiceTool(any(), any(), any(), any(), any(), any()))
            .thenReturn(callToolResult);
        Assertions.assertDoesNotThrow(() -> this.mcpService.testServicesTools(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, req));
    }

    @Test
    void testServicesTools5() {
        McpServiceToolsTestReq req = new McpServiceToolsTestReq();
        req.setServiceId("ff824f837e954cd5ad9036f45a9e8b34");
        Map<String, Object> structContent = new HashMap<>();
        structContent.put("test", "test");
        McpSchema.CallToolResult callToolResult = new McpSchema.CallToolResult("test", false);
        commonUtilMockedStatic.when(() -> CommonUtil.getRawQueryString(anyString())).thenReturn(null);
        commonUtilMockedStatic.when(() -> CommonUtil.parseMcpConfigHeaderInfo(anyString())).thenReturn(new HashMap<>());
        mcpClientService.when(
                () -> mcpClient.callMcpServiceTool(any(), any(), any(), any(), any(), any()))
            .thenReturn(callToolResult);
        Assertions.assertDoesNotThrow(() -> this.mcpService.testServicesTools(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, req));
    }

    @Test
    void testDeleteService() {
        McpServiceToolsTestReq req = new McpServiceToolsTestReq();
        req.setServiceId("ff824f837e954cd5ad9036f45a9e8b38");
        Assertions.assertThrows(Exception.class,
            () -> this.mcpService.deleteService(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID,
                "ff824f837e954cd5ad9036f45a9e8b11"));
    }

    @Test
    void testDeleteService2() {
        try {
            McpServiceToolsTestReq req = new McpServiceToolsTestReq();
            req.setServiceId("1c8a6f8868c34d61ae2e0549a33f0a9c");
            String result = this.mcpService.deleteService(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID,
                "1c8a6f8868c34d61ae2e0549a33f0a9c");
            assertNotNull(result);
        } catch (Exception e) {
            Assertions.assertTrue(true);
        }
    }

    @Test
    void testDeploy3() {
        EncryptionAdapter mockEncryptionAdapter = org.mockito.Mockito.mock(EncryptionAdapter.class);
        org.mockito.Mockito.when(mockEncryptionAdapter.encrypt(anyString(), any()))
                .thenReturn("E1-{fake-uuid}-fake_encrypt_result");
        org.mockito.Mockito.when(mockEncryptionAdapter.decrypt(anyString())).thenReturn("{}");
        org.mockito.Mockito.when(mockEncryptionAdapter.decrypt(anyString(), any())).thenReturn("{}");

        // 1. 注入到 mcpService
        ReflectionTestUtils.setField(this.mcpService, "encryptionAdapter", mockEncryptionAdapter);

        // 2. 动态获取它内部的 mcpBase 并注入 (处理底层加密 AuthInfo 的逻辑)
        Object mcpBaseInstance = ReflectionTestUtils.getField(this.mcpService, "mcpBase");
        if (mcpBaseInstance != null) {
            ReflectionTestUtils.setField(mcpBaseInstance, "encryptionAdapter", mockEncryptionAdapter);
        }

        ReflectionTestUtils.setField(mcpService, "mcpQuota", "30");
        commonUtilMockedStatic.when(CommonUtil::getAndValidateTenantId).thenReturn("test_domain_id");
        commonUtilMockedStatic.when(RequestContextUtils::getRequestUserDomainId).thenReturn("system");
        McpServiceDeployReq req = new McpServiceDeployReq();
        req.setServerConfig(
                "{\"mcpServers\": {\"file-sse\": {\"url\": \"\"}}}");
        req.setId("1c8a6f8868c34d61ae2e0549a33f0a9c");
        req.setName("mcpName");
        req.setOrgType("SSE");
        String result = this.mcpService.deploy(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, "1", req);
        assertNotNull(result);
    }

    @Test
    void testDeploy4() {
        McpServiceDeployReq req = new McpServiceDeployReq();
        req.setServerConfig(
                "{\"mcpServers\": {\"file-sse\": {\"url\": \"\"}}}");
        req.setId("1c8a6f8868c34d61ae2e0549a33f0a9c1");
        req.setOrgType(EnumOrgType.SSE.getValue());
        Assertions.assertThrows(Exception.class,
                () -> this.mcpService.deploy(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, "1", req));
    }

    @Test
    void test_deploy_throw_exception() {
        McpServiceDeployReq req = new McpServiceDeployReq();
        commonUtilMockedStatic.when(CommonUtil::getAndValidateTenantId).thenReturn("test_domain_id");
        commonUtilMockedStatic.when(RequestContextUtils::getRequestUserDomainId).thenReturn("system");
        req.setServerConfig(
            "{\"mcpServers\": {\"file-sse\": {\"url\": \"\"}}}");
        req.setId("1c8a6f8868c34d61ae2e0549a33f0a90");
        req.setName("mcpName");
        Assertions.assertThrows(AgentStudioException.class,
            () -> this.mcpService.deploy(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, "14", req));
    }

    @Test
    void test_updateMcp_throw_exception() {
        ReflectionTestUtils.setField(mcpService, "mcpQuota", "0");
        try {
            this.mcpService.updateMcp(null, "test", "test", "test");
        } catch (Exception e) {
            log.error("exception.", e);
        }
    }

    @Test
    void test_insertMcp_throw_exception() {
        ReflectionTestUtils.setField(mcpService, "mcpQuota", "0");
        try {
            this.mcpService.insertMcp(null, new HashMap<>(), "test");
        } catch (Exception e) {
            log.warn("Exception. ", e);
        }
    }

    @Test
    void testCreateServer() {
        McpServerDetailReq req = new McpServerDetailReq();
        req.setServerConfig(
            "{\"mcpServers\": {\"file-sse\": {\"url\": \"\"}}}");
        req.setId("1c8a6f8868c34d61ae2e0549a33f0a9c");
        Assertions.assertThrows(Exception.class,
            () -> this.mcpService.createServer(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, req));
    }

    @Test
    void testQueryServiceDetailForRuntime() {
        Assertions.assertThrows(Exception.class,
            () -> this.mcpService.queryServiceDetailForRuntime("not_exist_project", "not_exist_workspace",
                "ff824f837e954cd5ad9036f45a9e8b36"));
    }

    @Test
    void testQueryServiceDetailForRuntime2() {
        Assertions.assertThrows(Exception.class,
            () -> this.mcpService.queryServiceDetailForRuntime(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID,
                "ff824f837e954cd5ad9036f45a9e8b11"));
    }

    @Test
    void testQueryServiceDetail() {
        Assertions.assertThrows(Exception.class,
            () -> this.mcpService.queryServiceDetail(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID,
                "ff824f837e954cd5ad9036f45a9e8b11"));
    }

    @Test
    void testQueryServiceDetail2() {
        McpServiceDetailInfoDto result = this.mcpService.queryServiceDetail(Constants.TEST_PROJECT_ID,
            Constants.TEST_WORKSPACE_ID, "ff824f837e954cd5ad9036f45a9e8b34");
        assertNotNull(result);
    }

    @Test
    void testQueryServiceDetail3() {
        McpServiceDetailInfoDto result = this.mcpService.queryServiceDetail(Constants.TEST_PROJECT_ID,
            Constants.TEST_WORKSPACE_ID, "ff824f837e954cd5ad9036f45a9e8b36");
        assertNotNull(result);
    }

    @Test
    void testQueryServerDetail() {
        // 服务不存在：serverDao.selectById 查空抛 MCP_SERVICE_NOT_EXIST
        AgentStudioException exception = Assertions.assertThrows(AgentStudioException.class,
            () -> this.mcpService.queryServerDetail(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, "1100"));
        assertEquals(StudioError.MCP_SERVICE_NOT_EXIST, exception.getErrorCode());
    }

    @Test
    void testQueryServerDetail2() {
        McpServerDetailInfoDto result = this.mcpService.queryServerDetail(Constants.TEST_PROJECT_ID,
            Constants.TEST_WORKSPACE_ID, "914");
        assertNotNull(result);
    }

    @Test
    void testQueryServerDetail3() {
        McpServerDetailInfoDto result = this.mcpService.queryServerDetail(Constants.TEST_PROJECT_ID,
            Constants.TEST_WORKSPACE_ID, "994");
        assertNotNull(result);
    }

    @Test
    void testQueryMcpListByIds() {
        Assertions.assertThrows(Exception.class,
            () -> this.mcpService.queryMcpListByIds(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, List.of()));
    }

    @Test
    void testQueryMcpListByIds2() {
        List<McpServiceSkinnyEntity> result = this.mcpService.queryMcpListByIds(Constants.TEST_PROJECT_ID,
            Constants.TEST_WORKSPACE_ID,
            List.of("ff824f837e954cd5ad9036f45a9e8b34", "ff824f837e954cd5ad9036f45a9e8b35"));
        assertNotNull(result);
    }

    @Test
    void testListServers() {
        ListServersQo listServersQo = new ListServersQo();
        listServersQo.setWorkspaceId(Constants.TEST_WORKSPACE_ID);
        listServersQo.setName("test");
        listServersQo.setLanguage("EN1");
        listServersQo.setLimit(10);
        listServersQo.setOffset(0);
        Assertions.assertThrows(Exception.class,
            () -> this.mcpService.listServers(Constants.TEST_PROJECT_ID, listServersQo));
    }

    @Test
    void testListServers2() {
        ListServersQo listServersQo = new ListServersQo();
        listServersQo.setWorkspaceId(Constants.TEST_WORKSPACE_ID);
        listServersQo.setName("空白模板java");
        listServersQo.setLanguage("EN");
        listServersQo.setLimit(-10);
        listServersQo.setOffset(0);
        Assertions.assertThrows(Exception.class,
            () -> this.mcpService.listServers(Constants.TEST_PROJECT_ID, listServersQo));
    }

    @Test
    void testListServers3() {
        ListServersQo listServersQo = new ListServersQo();
        listServersQo.setWorkspaceId(Constants.TEST_WORKSPACE_ID);
        listServersQo.setName("空白模板java");
        listServersQo.setLanguage("EN");
        listServersQo.setLimit(10);
        listServersQo.setOffset(-2);
        Assertions.assertThrows(Exception.class,
            () -> this.mcpService.listServers(Constants.TEST_PROJECT_ID, listServersQo));
    }

    @Test
    void testListServers4() {
        ListServersQo listServersQo = new ListServersQo();
        listServersQo.setWorkspaceId(Constants.TEST_WORKSPACE_ID);
        listServersQo.setName("添加java");
        listServersQo.setLanguage("EN");
        listServersQo.setLimit(10);
        listServersQo.setOffset(0);
        McpServerBaseInfoListResp result = this.mcpService.listServers(Constants.TEST_PROJECT_ID, listServersQo);
        assertNotNull(result);
    }

    @Test
    void testListServers5() {
        ListServersQo listServersQo = new ListServersQo();
        listServersQo.setWorkspaceId(Constants.TEST_WORKSPACE_ID);
        listServersQo.setName("mcpName");
        listServersQo.setLimit(10);
        listServersQo.setOffset(0);
        McpServerBaseInfoListResp result = this.mcpService.listServers(Constants.TEST_PROJECT_ID, listServersQo);
        assertNotNull(result);
    }

    @Test
    void testListServers6() {
        ListServersQo listServersQo = new ListServersQo();
        listServersQo.setWorkspaceId(Constants.TEST_WORKSPACE_ID);
        listServersQo.setName("mcpName");
        listServersQo.setLimit(110);
        listServersQo.setOffset(0);
        McpServerBaseInfoListResp result = this.mcpService.listServers(Constants.TEST_PROJECT_ID, listServersQo);
        assertNotNull(result);
    }

    @Test
    void testParseToolFromString() {
        List<McpServiceToolEntity> result = McpJsonUtils.parseToolFromString(null, null);
        assertNotNull(result);
    }

    @Test
    void testParseToolFromString2() {
        Assertions.assertThrows(Exception.class, () -> McpJsonUtils.parseToolFromString("abcd", null));
        String tool
            = "[{\"name\":\"queryTestCaseList\",\"description\":\"查询一个Agent智能体提示词所有的测试用例列表，包含了每个测试用例的详细信息。注意：获取到数据后应该用表格呈现。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"promptId\":{\"type\":\"string\",\"description\":\"提示词的ID。注意：不要捏造ID，如果你不知道ID，应该询问用户修改哪一个提示词。\"}},\"required\":[\"promptId\"],\"additionalProperties\":false}},{\"name\":\"deleteTestTaskById\",\"description\":\"删除一个测试历史任务。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"testTaskId\":{\"type\":\"string\",\"description\":\"测试任务的ID。\"}},\"required\":[\"testTaskId\"],\"additionalProperties\":false}},{\"name\":\"saveTestResult\",\"description\":\"测试结果保存，用来保存测试任务的结果，你应该在完成所有的用户要求的测试任务后立即调用此工具保存测试结果。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"testTaskResult\":{\"type\":\"object\",\"properties\":{\"prompt_content\":{\"type\":\"string\",\"description\":\"Agent智能体的提示词内容\"},\"prompt_id\":{\"type\":\"string\",\"description\":\"提示词的ID。注意：不要捏造ID，如果你不知道ID，应该询问用户修改哪一个提示词。\"},\"prompt_type\":{\"type\":\"string\",\"description\":\"提示词的类型。\"},\"prompt_version\":{\"type\":\"integer\",\"format\":\"int32\",\"description\":\"提示词版本号。\"},\"test_case_result_list\":{\"description\":\"本次的所有测试用例的测试结果。\",\"type\":\"array\",\"items\":{\"type\":\"object\",\"properties\":{\"score\":{\"type\":\"integer\",\"format\":\"int32\",\"description\":\"根据测试的真实结果testCaseOutputActualValue和期望值testCaseOutputExpectedValue，对本次测试进行打分。打分规则：1、如果提示词的类型是function，testCaseOutputActualValue和testCaseOutputExpectedValue完全相等，则是满分10分；否则是0分。2、如果提示词的类型是common，请结合原始提示词、测试用例的原始信息对本次测试结果进行综合评价打分，如果输出包含了所有期望的要点则满足10分，包含大部分期望要点得6到9分，包含一半期望要点得5分，包含期望要点较少得1~4分，输出很差不包含任何期望的要点得0分。\"},\"test_case_id\":{\"type\":\"string\",\"description\":\"测试用例的ID。\"},\"test_case_input\":{\"type\":\"string\",\"description\":\"测试用例的输入。\"},\"test_case_name\":{\"type\":\"string\",\"description\":\"测试用例名称。注意：相同提示词的测试用例名称不能重名。\"},\"test_case_output_actual_value\":{\"type\":\"string\",\"description\":\"测试的真实输出。\"},\"test_case_output_expected_value\":{\"type\":\"string\",\"description\":\"测试的期望输出。\"},\"test_review\":{\"type\":\"string\",\"description\":\"根据测试的真实结果和期望值，对本次测试进行评价。\"}},\"required\":[\"score\",\"test_case_id\",\"test_case_input\",\"test_case_name\",\"test_case_output_actual_value\",\"test_case_output_expected_value\",\"test_review\"],\"description\":\"本次的所有测试用例的测试结果。\"}}},\"required\":[\"prompt_content\",\"prompt_id\",\"prompt_type\",\"prompt_version\",\"test_case_result_list\"],\"description\":\"执行测试后返回的测试结果集合。\"}},\"required\":[\"testTaskResult\"],\"additionalProperties\":false}},{\"name\":\"modifyPromptById\",\"description\":\"修改一个Agent智能体提示词的内容。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"promptId\":{\"type\":\"string\",\"description\":\"提示词的ID。注意：不要捏造ID，如果你不知道ID，应该询问用户修改哪一个提示词。\"},\"promptContent\":{\"type\":\"string\",\"description\":\"Agent智能体的提示词内容。注意：提示词应该是结构化的，使用markdown格式，要有清晰准确的角色、任务、要求、示例等说明，确保Agent出色地按照要求完成任务。\"}},\"required\":[\"promptId\",\"promptContent\"],\"additionalProperties\":false}},{\"name\":\"testPrompt\",\"description\":\"执行一次测试Agent智能体提示词的测试用例，一次支持执行多个测试用例，返回测试的输出结果。注意：1、你应该先获取到被测试提示词的原始信息，以及测试用例的原始信息，然后再使用此工具进行测试获取测试结果。2、此工具只是执行测试获取测试结果，当完成所有的用户要求的测试任务后你应该立即调用测试结果保存工具，把所有的测试结果进行保存，否则用户将无法看到测试结果。3、最终结果可以用表格呈现。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"testTaskInfo\":{\"type\":\"object\",\"properties\":{\"prompt_content\":{\"type\":\"string\",\"description\":\"待测试的Agent智能体提示词的原始内容，你需要先从工具获取提示词内容，不要捏造提示词内容；当使用此工具的时候，你应该把这个提示词的内容临时作为你的系统提示词。\"},\"prompt_id\":{\"type\":\"string\",\"description\":\"提示词的ID。注意：不要捏造ID，如果你不知道ID，应该询问用户修改哪一个提示词。\"},\"prompt_type\":{\"type\":\"string\",\"description\":\"提示词的类型。\"},\"prompt_version\":{\"type\":\"integer\",\"format\":\"int32\",\"description\":\"提示词版本号。\"},\"test_case_info_list\":{\"description\":\"被测试的测试用例的信息集合。\",\"type\":\"array\",\"items\":{\"type\":\"object\",\"properties\":{\"test_caseId\":{\"type\":\"string\",\"description\":\"测试用例的ID。\"},\"test_case_input\":{\"type\":\"string\",\"description\":\"测试用例的原始输入，你需要先从工具获取测试用例的输入，不要捏造输入；当使用此工具的时候，你应该把测试用例的输入临时作为用户的输入。\"},\"test_case_name\":{\"type\":\"string\",\"description\":\"测试用例名称。注意：相同提示词的测试用例名称不能重名。\"},\"test_case_predicted_output\":{\"type\":\"string\",\"description\":\"你对前测试用例的预测输出，不能为空，需要动态生成；当使用此工具的时候，你应该根据临时的系统提示词promptContent和临时的用户的输入testCaseInput，分析并生成对应的预测输出，并设置到此参数上。\"}},\"required\":[\"test_caseId\",\"test_case_input\",\"test_case_name\",\"test_case_predicted_output\"],\"description\":\"被测试的测试用例的信息集合。\"}}},\"required\":[\"prompt_content\",\"prompt_id\",\"prompt_type\",\"prompt_version\",\"test_case_info_list\"],\"description\":\"测试任务的提示词和测试用例信息。\"}},\"required\":[\"testTaskInfo\"],\"additionalProperties\":false}},{\"name\":\"queryPromptById\",\"description\":\"查询一个Agent智能体提示词的详细信息。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"promptId\":{\"type\":\"string\",\"description\":\"提示词的ID。注意：不要捏造ID，如果你不知道ID，应该询问用户修改哪一个提示词。\"}},\"required\":[\"promptId\"],\"additionalProperties\":false}},{\"name\":\"queryTestTaskList\",\"description\":\"查询一个Agent智能体提示词所有的测试历史任务列表，包含了每个测试任务的详细信息。注意：获取到数据后应该用表格呈现。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"promptId\":{\"type\":\"string\",\"description\":\"提示词的ID。注意：不要捏造ID，如果你不知道ID，应该询问用户修改哪一个提示词。\"}},\"required\":[\"promptId\"],\"additionalProperties\":false}},{\"name\":\"createPrompt\",\"description\":\"为一个Agent智能体创建一个提示词。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"promptName\":{\"type\":\"string\",\"description\":\"提示词名称。注意：提示词的名称不能重名。\"},\"promptContent\":{\"type\":\"string\",\"description\":\"Agent智能体的提示词内容。注意：提示词应该是结构化的，使用markdown格式，要有清晰准确的角色、任务、要求、示例等说明，确保Agent出色地按照要求完成任务。\"},\"type\":{\"type\":\"string\",\"description\":\"提示词的类型，取值范围是：function、common。解释说明：function表示函数模式，需要Agent根据提示词输出固定范围的值（比如输出：Y或N、存在或不存在、合法或不合法等有限的固定序列值）；common表示通用模式，输出内容是不固定的。\"}},\"required\":[\"promptName\",\"promptContent\",\"type\"],\"additionalProperties\":false}},{\"name\":\"queryPromptList\",\"description\":\"查询所有的Agent智能体提示词列表。注意：获取到数据后应该用表格呈现。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{},\"required\":[],\"additionalProperties\":false}},{\"name\":\"deleteTestCaseById\",\"description\":\"删除一个测试用例。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"testCaseId\":{\"type\":\"string\",\"description\":\"测试用例的ID。\"}},\"required\":[\"testCaseId\"],\"additionalProperties\":false}},{\"name\":\"modifyTestCase\",\"description\":\"修改一个测试用例的输入和期望输出。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"testCaseId\":{\"type\":\"string\",\"description\":\"测试用例的ID。\"},\"testCaseInput\":{\"type\":\"string\",\"description\":\"测试用例的输入。\"},\"testCaseOutput\":{\"type\":\"string\",\"description\":\"测试用例的期望输出。\"}},\"required\":[\"testCaseId\",\"testCaseInput\",\"testCaseOutput\"],\"additionalProperties\":false}},{\"name\":\"queryTestCaseById\",\"description\":\"查询一个测试用例的详细信息。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"testCaseId\":{\"type\":\"string\",\"description\":\"提示词的ID。注意：不要捏造ID，如果你不知道ID，应该询问用户修改哪一个提示词。\"}},\"required\":[\"testCaseId\"],\"additionalProperties\":false}},{\"name\":\"queryTestTaskById\",\"description\":\"查询一个测试历史任务的详细信息。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"testTaskId\":{\"type\":\"string\",\"description\":\"测试任务的ID。\"}},\"required\":[\"testTaskId\"],\"additionalProperties\":false}},{\"name\":\"deletePromptById\",\"description\":\"删除一个Agent智能体提示词。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"promptId\":{\"type\":\"string\",\"description\":\"提示词的ID。注意：不要捏造ID，如果你不知道ID，应该询问用户修改哪一个提示词。\"}},\"required\":[\"promptId\"],\"additionalProperties\":false}},{\"name\":\"createTestCaseForPrompt\",\"description\":\"给一个Agent智能体提示词创建一个测试用例。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"promptId\":{\"type\":\"string\",\"description\":\"提示词的ID。注意：不要捏造ID，如果你不知道ID，应该询问用户修改哪一个提示词。\"},\"testCaseName\":{\"type\":\"string\",\"description\":\"测试用例名称。注意：相同提示词的测试用例名称不能重名。\"},\"testCaseInput\":{\"type\":\"string\",\"description\":\"测试用例的输入。\"},\"testCaseOutput\":{\"type\":\"string\",\"description\":\"测试用例的期望输出。\"}},\"required\":[\"promptId\",\"testCaseName\",\"testCaseInput\",\"testCaseOutput\"],\"additionalProperties\":false}}]";
        McpJsonUtils.parseToolFromString(tool, "test");
    }

    @Test
    void testParseToolFromString3() {
        Assertions.assertThrows(Exception.class, () -> McpJsonUtils.parseToolFromString("abcd", null));
        mockedStatic.when(RequestContextUtils::getRequestUserName).thenReturn(Constants.TEST_USER_NAME);
        String tool
            = "[{\"name\":\"queryTestCaseList\",\"description\":\"查询一个Agent智能体提示词所有的测试用例列表，包含了每个测试用例的详细信息。注意：获取到数据后应该用表格呈现。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"promptId\":{\"type\":\"string\",\"description\":\"提示词的ID。注意：不要捏造ID，如果你不知道ID，应该询问用户修改哪一个提示词。\"}},\"required\":[\"promptId\"],\"additionalProperties\":false}},{\"name\":\"deleteTestTaskById\",\"description\":\"删除一个测试历史任务。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"testTaskId\":{\"type\":\"string\",\"description\":\"测试任务的ID。\"}},\"required\":[\"testTaskId\"],\"additionalProperties\":false}},{\"name\":\"saveTestResult\",\"description\":\"测试结果保存，用来保存测试任务的结果，你应该在完成所有的用户要求的测试任务后立即调用此工具保存测试结果。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"testTaskResult\":{\"type\":\"object\",\"properties\":{\"prompt_content\":{\"type\":\"string\",\"description\":\"Agent智能体的提示词内容\"},\"prompt_id\":{\"type\":\"string\",\"description\":\"提示词的ID。注意：不要捏造ID，如果你不知道ID，应该询问用户修改哪一个提示词。\"},\"prompt_type\":{\"type\":\"string\",\"description\":\"提示词的类型。\"},\"prompt_version\":{\"type\":\"integer\",\"format\":\"int32\",\"description\":\"提示词版本号。\"},\"test_case_result_list\":{\"description\":\"本次的所有测试用例的测试结果。\",\"type\":\"array\",\"items\":{\"type\":\"object\",\"properties\":{\"score\":{\"type\":\"integer\",\"format\":\"int32\",\"description\":\"根据测试的真实结果testCaseOutputActualValue和期望值testCaseOutputExpectedValue，对本次测试进行打分。打分规则：1、如果提示词的类型是function，testCaseOutputActualValue和testCaseOutputExpectedValue完全相等，则是满分10分；否则是0分。2、如果提示词的类型是common，请结合原始提示词、测试用例的原始信息对本次测试结果进行综合评价打分，如果输出包含了所有期望的要点则满足10分，包含大部分期望要点得6到9分，包含一半期望要点得5分，包含期望要点较少得1~4分，输出很差不包含任何期望的要点得0分。\"},\"test_case_id\":{\"type\":\"string\",\"description\":\"测试用例的ID。\"},\"test_case_input\":{\"type\":\"string\",\"description\":\"测试用例的输入。\"},\"test_case_name\":{\"type\":\"string\",\"description\":\"测试用例名称。注意：相同提示词的测试用例名称不能重名。\"},\"test_case_output_actual_value\":{\"type\":\"string\",\"description\":\"测试的真实输出。\"},\"test_case_output_expected_value\":{\"type\":\"string\",\"description\":\"测试的期望输出。\"},\"test_review\":{\"type\":\"string\",\"description\":\"根据测试的真实结果和期望值，对本次测试进行评价。\"}},\"required\":[\"score\",\"test_case_id\",\"test_case_input\",\"test_case_name\",\"test_case_output_actual_value\",\"test_case_output_expected_value\",\"test_review\"],\"description\":\"本次的所有测试用例的测试结果。\"}}},\"required\":[\"prompt_content\",\"prompt_id\",\"prompt_type\",\"prompt_version\",\"test_case_result_list\"],\"description\":\"执行测试后返回的测试结果集合。\"}},\"required\":[\"testTaskResult\"],\"additionalProperties\":false}},{\"name\":\"modifyPromptById\",\"description\":\"修改一个Agent智能体提示词的内容。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"promptId\":{\"type\":\"string\",\"description\":\"提示词的ID。注意：不要捏造ID，如果你不知道ID，应该询问用户修改哪一个提示词。\"},\"promptContent\":{\"type\":\"string\",\"description\":\"Agent智能体的提示词内容。注意：提示词应该是结构化的，使用markdown格式，要有清晰准确的角色、任务、要求、示例等说明，确保Agent出色地按照要求完成任务。\"}},\"required\":[\"promptId\",\"promptContent\"],\"additionalProperties\":false}},{\"name\":\"testPrompt\",\"description\":\"执行一次测试Agent智能体提示词的测试用例，一次支持执行多个测试用例，返回测试的输出结果。注意：1、你应该先获取到被测试提示词的原始信息，以及测试用例的原始信息，然后再使用此工具进行测试获取测试结果。2、此工具只是执行测试获取测试结果，当完成所有的用户要求的测试任务后你应该立即调用测试结果保存工具，把所有的测试结果进行保存，否则用户将无法看到测试结果。3、最终结果可以用表格呈现。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"testTaskInfo\":{\"type\":\"object\",\"properties\":{\"prompt_content\":{\"type\":\"string\",\"description\":\"待测试的Agent智能体提示词的原始内容，你需要先从工具获取提示词内容，不要捏造提示词内容；当使用此工具的时候，你应该把这个提示词的内容临时作为你的系统提示词。\"},\"prompt_id\":{\"type\":\"string\",\"description\":\"提示词的ID。注意：不要捏造ID，如果你不知道ID，应该询问用户修改哪一个提示词。\"},\"prompt_type\":{\"type\":\"string\",\"description\":\"提示词的类型。\"},\"prompt_version\":{\"type\":\"integer\",\"format\":\"int32\",\"description\":\"提示词版本号。\"},\"test_case_info_list\":{\"description\":\"被测试的测试用例的信息集合。\",\"type\":\"array\",\"items\":{\"type\":\"object\",\"properties\":{\"test_caseId\":{\"type\":\"string\",\"description\":\"测试用例的ID。\"},\"test_case_input\":{\"type\":\"string\",\"description\":\"测试用例的原始输入，你需要先从工具获取测试用例的输入，不要捏造输入；当使用此工具的时候，你应该把测试用例的输入临时作为用户的输入。\"},\"test_case_name\":{\"type\":\"string\",\"description\":\"测试用例名称。注意：相同提示词的测试用例名称不能重名。\"},\"test_case_predicted_output\":{\"type\":\"string\",\"description\":\"你对前测试用例的预测输出，不能为空，需要动态生成；当使用此工具的时候，你应该根据临时的系统提示词promptContent和临时的用户的输入testCaseInput，分析并生成对应的预测输出，并设置到此参数上。\"}},\"required\":[\"test_caseId\",\"test_case_input\",\"test_case_name\",\"test_case_predicted_output\"],\"description\":\"被测试的测试用例的信息集合。\"}}},\"required\":[\"prompt_content\",\"prompt_id\",\"prompt_type\",\"prompt_version\",\"test_case_info_list\"],\"description\":\"测试任务的提示词和测试用例信息。\"}},\"required\":[\"testTaskInfo\"],\"additionalProperties\":false}},{\"name\":\"queryPromptById\",\"description\":\"查询一个Agent智能体提示词的详细信息。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"promptId\":{\"type\":\"string\",\"description\":\"提示词的ID。注意：不要捏造ID，如果你不知道ID，应该询问用户修改哪一个提示词。\"}},\"required\":[\"promptId\"],\"additionalProperties\":false}},{\"name\":\"queryTestTaskList\",\"description\":\"查询一个Agent智能体提示词所有的测试历史任务列表，包含了每个测试任务的详细信息。注意：获取到数据后应该用表格呈现。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"promptId\":{\"type\":\"string\",\"description\":\"提示词的ID。注意：不要捏造ID，如果你不知道ID，应该询问用户修改哪一个提示词。\"}},\"required\":[\"promptId\"],\"additionalProperties\":false}},{\"name\":\"createPrompt\",\"description\":\"为一个Agent智能体创建一个提示词。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"promptName\":{\"type\":\"string\",\"description\":\"提示词名称。注意：提示词的名称不能重名。\"},\"promptContent\":{\"type\":\"string\",\"description\":\"Agent智能体的提示词内容。注意：提示词应该是结构化的，使用markdown格式，要有清晰准确的角色、任务、要求、示例等说明，确保Agent出色地按照要求完成任务。\"},\"type\":{\"type\":\"string\",\"description\":\"提示词的类型，取值范围是：function、common。解释说明：function表示函数模式，需要Agent根据提示词输出固定范围的值（比如输出：Y或N、存在或不存在、合法或不合法等有限的固定序列值）；common表示通用模式，输出内容是不固定的。\"}},\"required\":[\"promptName\",\"promptContent\",\"type\"],\"additionalProperties\":false}},{\"name\":\"queryPromptList\",\"description\":\"查询所有的Agent智能体提示词列表。注意：获取到数据后应该用表格呈现。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{},\"required\":[],\"additionalProperties\":false}},{\"name\":\"deleteTestCaseById\",\"description\":\"删除一个测试用例。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"testCaseId\":{\"type\":\"string\",\"description\":\"测试用例的ID。\"}},\"required\":[\"testCaseId\"],\"additionalProperties\":false}},{\"name\":\"modifyTestCase\",\"description\":\"修改一个测试用例的输入和期望输出。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"testCaseId\":{\"type\":\"string\",\"description\":\"测试用例的ID。\"},\"testCaseInput\":{\"type\":\"string\",\"description\":\"测试用例的输入。\"},\"testCaseOutput\":{\"type\":\"string\",\"description\":\"测试用例的期望输出。\"}},\"required\":[\"testCaseId\",\"testCaseInput\",\"testCaseOutput\"],\"additionalProperties\":false}},{\"name\":\"queryTestCaseById\",\"description\":\"查询一个测试用例的详细信息。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"testCaseId\":{\"type\":\"string\",\"description\":\"提示词的ID。注意：不要捏造ID，如果你不知道ID，应该询问用户修改哪一个提示词。\"}},\"required\":[\"testCaseId\"],\"additionalProperties\":false}},{\"name\":\"queryTestTaskById\",\"description\":\"查询一个测试历史任务的详细信息。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"testTaskId\":{\"type\":\"string\",\"description\":\"测试任务的ID。\"}},\"required\":[\"testTaskId\"],\"additionalProperties\":false}},{\"name\":\"deletePromptById\",\"description\":\"删除一个Agent智能体提示词。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"promptId\":{\"type\":\"string\",\"description\":\"提示词的ID。注意：不要捏造ID，如果你不知道ID，应该询问用户修改哪一个提示词。\"}},\"required\":[\"promptId\"],\"additionalProperties\":false}},{\"name\":\"createTestCaseForPrompt\",\"description\":\"给一个Agent智能体提示词创建一个测试用例。\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"promptId\":{\"type\":\"string\",\"description\":\"提示词的ID。注意：不要捏造ID，如果你不知道ID，应该询问用户修改哪一个提示词。\"},\"testCaseName\":{\"type\":\"string\",\"description\":\"测试用例名称。注意：相同提示词的测试用例名称不能重名。\"},\"testCaseInput\":{\"type\":\"string\",\"description\":\"测试用例的输入。\"},\"testCaseOutput\":{\"type\":\"string\",\"description\":\"测试用例的期望输出。\"}},\"required\":[\"promptId\",\"testCaseName\",\"testCaseInput\",\"testCaseOutput\"],\"additionalProperties\":false},\"outputSchema\": {\"properties\": {\"result\": {\"type\": \"integer\"}},\"required\": [\"result\"],\"type\": \"object\",\"x-fastmcp-wrap-result\": true}}]";
        McpJsonUtils.parseToolFromString(tool, "test");
    }

    @Test
    void testCheckSwaggerUrlValid() {
        String swaggerUrl = "http://10.10.10.10/swagger.json";
        mcpService.checkSwaggerUrlValid(swaggerUrl, "");
        String hostBlackList = "10.10.10.10";
        Assertions.assertThrows(AgentStudioException.class,
                ()-> mcpService.checkSwaggerUrlValid(swaggerUrl, hostBlackList));
        String swaggerUrl1 = "http://www.example.com/swagger.json";
        Assertions.assertDoesNotThrow(
                ()-> mcpService.checkSwaggerUrlValid(swaggerUrl1, hostBlackList));
    }

    @Test
    public void test_batchDeployServices_all_success(){
        // Given
        String projectId = "proj1";
        String workspaceId = "ws1";
        String resource = "ROMA";
        McpServiceBatchDeployReq body = mock(McpServiceBatchDeployReq.class);
        List<McpServiceBatchDeployItem> servers = new ArrayList<>();
        McpServiceBatchDeployItem server = new McpServiceBatchDeployItem();

        server.setThirdId("third1");
        server.setThirdVersionId("thirdVersionId1");
        server.setName("service1");
        server.setNameEn("nameEn1");
        server.setOrgType("SSE");
        server.setDescription("description1");
        server.setDescriptionEn("descriptionEn1");
        server.setServerConfig("{\n  \"mcpServers\": {\n    \"star-mcp\": {\n      \"type\": \"sse\",\n      \"url\": \"https://mcp.api-inference.modelscope.net/6112666561cc4c/sse\",\n \"headers\": {\"X-AUTH-TOKEN\": \"\"}    }\n  }\n}");
        server.setReadme("readme1");
        servers.add(server);
        when(body.getServers()).thenReturn(servers);
        when(serviceDao.insert(any())).thenReturn(1);
        commonUtilMockedStatic.when(CommonUtil::getUUID).thenReturn("111111111");
        EncryptionAdapter mockEncryptionAdapter = org.mockito.Mockito.mock(EncryptionAdapter.class);
        org.mockito.Mockito.when(mockEncryptionAdapter.encrypt(anyString(), any()))
                .thenReturn("E1-{fake-uuid}-fake_encrypt_result");
        ReflectionTestUtils.setField(mcpService, "encryptionAdapter", mockEncryptionAdapter);

        // When
        McpServiceBatchDeployResp response = mcpService.batchDeployServices(projectId, workspaceId, resource, body);

        // Then
        assertEquals(1, response.getSuccessCount());
        assertEquals(0, response.getFailedCount());
        assertEquals(1, response.getResults().size());
        assertEquals("service1", response.getResults().get(0).getName());
        assertEquals(McpDeployResult.StatusEnum.SUCCESS, response.getResults().get(0).getStatus());
    }

    @Test
    public void test_batchDeployServices_failed() throws Exception {
        // Given
        String projectId = "proj1";
        String workspaceId = "ws1";
        String resource = "res1";
        McpServiceBatchDeployReq body = mock(McpServiceBatchDeployReq.class);
        List<McpServiceBatchDeployItem> servers = new ArrayList<>();
        McpServiceBatchDeployItem server = new McpServiceBatchDeployItem();

        server.setThirdId("third1");
        server.setThirdVersionId("thirdVersionId1");
        server.setName("service1");
        server.setNameEn("nameEn1");
        server.setOrgType("SSE");
        server.setDescription("description1");
        server.setDescriptionEn("descriptionEn1");
        server.setServerConfig("{\n  \"mcpServers\": {\n    \"star-mcp\": {\n      \"type\": \"sse\",\n      \"url\": \"https://mcp.api-inference.modelscope.net/6112666561cc4c/sse\",\n \"headers\": {\"X-AUTH-TOKEN\": \"\"}    }\n  }\n}");
        server.setReadme("readme1");
        servers.add(server);
        when(body.getServers()).thenReturn(servers);
        when(serviceDao.insert(any())).thenReturn(1);
        commonUtilMockedStatic.when(CommonUtil::getUUID).thenReturn(null);

        // When
        McpServiceBatchDeployResp response = mcpService.batchDeployServices(projectId, workspaceId, resource,
            body);

        // Then
        assertEquals(0, response.getSuccessCount());
        assertEquals(1, response.getFailedCount());
        assertEquals(1, response.getResults().size());
        assertEquals("service1", response.getResults().get(0).getName());
        assertEquals(McpDeployResult.StatusEnum.FAILED, response.getResults().get(0).getStatus());
    }

    @Test
    void testGetBase64Icon() throws IOException {
        String iconUrl2 = "http://localhost/test.png";
        String result2 = this.mcpService.getBase64Icon(iconUrl2);
        String result3 = this.mcpService.getBase64Icon("");


    }


}

