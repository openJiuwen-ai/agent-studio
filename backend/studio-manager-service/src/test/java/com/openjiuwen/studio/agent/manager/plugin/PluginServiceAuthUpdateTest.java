/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.plugin;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.common.dto.auth.AuthKeyInfo;
import com.openjiuwen.studio.agent.manager.dto.PluginAuthUpdateReq;
import com.openjiuwen.studio.agent.manager.dto.PluginAuthUpdateRsp;
import com.openjiuwen.studio.agent.manager.dto.RequestInfo;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.plugin.PluginEntity;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.plugin.PluginMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.plugin.IPluginBase;
import com.openjiuwen.studio.agent.manager.service.plugin.PluginService;

import java.util.List;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

/**
 * 插件更新鉴权接口的单元测试
 */
@ExtendWith(MockitoExtension.class)
public class PluginServiceAuthUpdateTest {

    @Mock
    private PluginMapper pluginMapper;

    @Mock
    ReleaseVersionMapper releaseVersionMapper;

    @Mock
    private MgObsService obsService;

    // FEAT-093 动态鉴权校验依赖（updatePluginAuthInfo 无条件调用
    // pluginBase.validPluginDynamicAuthInfo——此前缺 mock，NPE 预存在失败）
    @Mock
    private IPluginBase pluginBase;

    // 使用 Spy 部分 Mock PluginService，以便跳过内部耗时的 OBS/加密 逻辑
    @InjectMocks
    @Spy
    private PluginService pluginService;

    private static final String PROJECT_ID = "test_project_id";

    private static final String WORKSPACE_ID = "test_workspace_id";

    private static final String PLUGIN_ID = "test_plugin_id";

    private PluginAuthUpdateReq req;

    private AuthInfo mockAuthInfo;

    @BeforeEach
    public void setUp() {
        req = new PluginAuthUpdateReq();
        mockAuthInfo = new AuthInfo();
        // 模拟前端传来的最新鉴权信息
        req.setAuthInfo(mockAuthInfo);
    }

    /**
     * 测试分支 1：插件不存在时，抛出业务异常
     */
    @Test
    public void testUpdatePluginAuthInfo_PluginNotExist() {
        // Arrange：模拟数据库查不到插件
        when(pluginMapper.selectByPrimaryKeyAndWorkspace(PLUGIN_ID, PROJECT_ID, WORKSPACE_ID)).thenReturn(null);

        // Act & Assert：断言抛出了指定的异常
        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            pluginService.updatePluginAuthInfo(PROJECT_ID, WORKSPACE_ID, PLUGIN_ID, req);
        });
        assertEquals(StudioError.TOOL_NOT_EXIST, exception.getErrorCode());
    }

    /**
     * 测试分支 2：插件【已发布】时，仅更新鉴权，不改变版本号
     */
    @Test
    public void testUpdatePluginAuthInfo_AlreadyPublished() {
        // Arrange：准备一个状态为“已发布 (1)”的插件
        PluginEntity existPlugin = new PluginEntity();
        existPlugin.setPluginId(PLUGIN_ID);
        existPlugin.setPublished(1); // 1 代表已发布
        existPlugin.setLastVersionId("v123456");

        ReleaseVersion releaseVersion = new ReleaseVersion();
        releaseVersion.setId("v123456");

        when(pluginMapper.selectByPrimaryKeyAndWorkspace(PLUGIN_ID, PROJECT_ID, WORKSPACE_ID)).thenReturn(existPlugin);
        when(releaseVersionMapper.selectByAppIdAndVersionId(PLUGIN_ID, "v123456")).thenReturn(releaseVersion);
        when(obsService.uploadObsFile(any(), any(), any(), any(), any())).thenReturn("test_dsl_path");
        // Mock 掉内部的加密方法，直接返回 mock 对象
        doReturn(mockAuthInfo).when(pluginService).encryptedAuthInfo(any(AuthInfo.class));

        // Act：执行核心方法
        PluginAuthUpdateRsp rsp = pluginService.updatePluginAuthInfo(PROJECT_ID, WORKSPACE_ID, PLUGIN_ID, req);

        // Assert：校验响应结果
        assertNotNull(rsp);
        assertEquals(PLUGIN_ID, rsp.getPluginId());
        assertFalse(rsp.isIsNewlyPublished(), "已发布插件不应该触发新发布");
        assertEquals("v123456", rsp.getVersionId(), "版本号应当保持不变");

        // 验证动作：数据库 update 被调用了 1 次 (仅静默更新鉴权)
        verify(pluginMapper, times(1)).updateByPrimaryKeySelective(any(PluginEntity.class));
        // 验证动作：发布逻辑不能被调用
        verify(pluginService, never()).releasePluginVersionHandler(any(), any(), anyString(), anyString());
    }

    @Test
    public void testUpdatePluginAuthInfo_throw_exception() {
        // Arrange：准备一个状态为“已发布 (1)”的插件
        PluginEntity existPlugin = new PluginEntity();
        existPlugin.setPluginId(PLUGIN_ID);
        existPlugin.setPublished(1); // 1 代表已发布
        existPlugin.setLastVersionId("v123456");

        ReleaseVersion releaseVersion = new ReleaseVersion();
        releaseVersion.setId("v123456");

        when(pluginMapper.selectByPrimaryKeyAndWorkspace(PLUGIN_ID, PROJECT_ID, WORKSPACE_ID)).thenReturn(existPlugin);
        when(releaseVersionMapper.selectByAppIdAndVersionId(PLUGIN_ID, "v123456")).thenReturn(null);
        // Mock 掉内部的加密方法，直接返回 mock 对象
        doReturn(mockAuthInfo).when(pluginService).encryptedAuthInfo(any(AuthInfo.class));
        // Act & Assert
        assertThrows(AgentStudioException.class,
            () -> pluginService.updatePluginAuthInfo(PROJECT_ID, WORKSPACE_ID, PLUGIN_ID, req));
    }

    /**
     * FEAT-093 回归：存量插件（实体行 requestInfo=新版 ToolRequestInfo、
     * inputSchema=ToolInputSchema 数组）把鉴权切换为 DYNAMIC——接线验证：
     * 新版 tool_info[*].headers 须被合并进传给校验器的 RequestInfo（按旧
     * RequestInfo 形态解析会漏检工具头）；数组 inputSchema 原样透传由
     * PluginDynamicAuthValidationTest 的真实现用例覆盖。
     */
    @Test
    public void testUpdatePluginAuthInfo_DynamicConflictWithNewFormToolHeader() {
        PluginEntity existPlugin = new PluginEntity();
        existPlugin.setPluginId(PLUGIN_ID);
        existPlugin.setPublished(1);
        existPlugin.setLastVersionId("v123456");
        // 新版插件行形态：requestInfo=ToolRequestInfo（工具固定头在 tool_info 里），
        // inputSchema=ToolInputSchema 数组（元素 input_schema 为内层对象串）
        existPlugin.setRequestInfo("{\"basic_info\":{\"protocol\":\"https\",\"host\":\"h\"},"
            + "\"tool_info\":[{\"tool_id\":\"t1\",\"headers\":{\"X-Fixed\":\"v\"}}]}");
        String arraySchema = "[{\"tool_id\":\"t1\",\"input_schema\":\"{\\\"type\\\":\\\"object\\\"}\"}]";
        existPlugin.setInputSchema(arraySchema);

        when(pluginMapper.selectByPrimaryKeyAndWorkspace(PLUGIN_ID, PROJECT_ID, WORKSPACE_ID)).thenReturn(existPlugin);
        when(releaseVersionMapper.selectByAppIdAndVersionId(PLUGIN_ID, "v123456")).thenReturn(new ReleaseVersion());
        when(obsService.uploadObsFile(any(), any(), any(), any(), any())).thenReturn("test_dsl_path");
        doReturn(mockAuthInfo).when(pluginService).encryptedAuthInfo(any(AuthInfo.class));

        AuthInfo dynamicAuth = new AuthInfo();
        dynamicAuth.setScope(AuthInfo.ScopeEnum.DYNAMIC);
        dynamicAuth.setDomain(AuthInfo.DomainEnum.HEADERS);
        AuthKeyInfo keyInfo = new AuthKeyInfo();
        keyInfo.setTargetName("X-Fixed");
        dynamicAuth.setAuthKeys(List.of(keyInfo));
        req.setAuthInfo(dynamicAuth);

        PluginAuthUpdateRsp rsp = pluginService.updatePluginAuthInfo(PROJECT_ID, WORKSPACE_ID, PLUGIN_ID, req);
        assertNotNull(rsp);

        org.mockito.ArgumentCaptor<RequestInfo> requestInfoCaptor =
            org.mockito.ArgumentCaptor.forClass(RequestInfo.class);
        verify(pluginBase).validPluginDynamicAuthInfo(
            org.mockito.ArgumentMatchers.eq(dynamicAuth), requestInfoCaptor.capture(),
            org.mockito.ArgumentMatchers.eq(arraySchema));
        // 新版 tool_info 的固定头已合并进校验入参（冲突校验可见）
        assertEquals("v", requestInfoCaptor.getValue().getHeaders().get("X-Fixed"));
    }
}
