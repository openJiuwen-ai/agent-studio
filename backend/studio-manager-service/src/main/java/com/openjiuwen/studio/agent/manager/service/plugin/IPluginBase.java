/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.plugin;

import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.manager.dto.RequestInfo;
import com.openjiuwen.studio.agent.manager.dto.plugin.PluginDTO;
import com.openjiuwen.studio.agent.manager.dto.plugin.ToolInputSchema;
import com.openjiuwen.studio.agent.manager.dto.plugin.ToolRequestInfo;
import com.openjiuwen.studio.agent.manager.entity.ToolEntity;
import com.openjiuwen.studio.agent.manager.entity.plugin.PluginEntity;
import io.swagger.v3.oas.models.OpenAPI;

import java.util.List;
import java.util.Map;

public interface IPluginBase {
    ToolEntity buildToolByPlugin(String projectId, String workspaceId, String pluginId, String toolId);

    /**
     * FEAT-093 插件动态鉴权校验（scope=DYNAMIC 登记侧 + 工具请求头同名拒绝）。
     * 落位 PluginBaseImpl：PluginService 与 ToolManagementService 均依赖本
     * 接口，避免两者互相注入成环。
     */
    void validPluginDynamicAuthInfo(AuthInfo authInfo, RequestInfo requestInfo, String inputSchemaStr);

    ToolEntity getToolEntityByVersion(String toolId, String versionId);

    PluginEntity getPluginEntityByVersion(String pluginId, String versionId);

    PluginEntity transformTool2Plugin(ToolEntity tool);

    List<ToolInputSchema> buildInputSchemaForOld(String inputSchema, Map<String, String> headers);

    boolean validateAuth(String projectId, String workspaceId, Map<String, Object> configs);

    void validateDuplicateInputSchema(List<ToolInputSchema> toolInputSchemas, ToolRequestInfo requestInfo);

    void adaptToolShareInfo(ToolEntity tool);

    PluginDTO transformOpenAPI2Plugin(OpenAPI openAPI);

    PluginDTO transformEntityToDTO(PluginEntity pluginEntity);

    PluginEntity transformDTOtoNewEntity(PluginDTO pluginDTO);

    String getLastVersion(String pluginId);

    boolean isInnerType(String resourceId);
}
