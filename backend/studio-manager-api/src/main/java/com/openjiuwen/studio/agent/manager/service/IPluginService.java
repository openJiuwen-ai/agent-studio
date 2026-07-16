/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.manager.dto.BaseResp;
import com.openjiuwen.studio.agent.manager.dto.BatchCreatePluginToolReq;
import com.openjiuwen.studio.agent.manager.dto.BatchCreatePluginToolRsp;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.CreatePluginToolReq;
import com.openjiuwen.studio.agent.manager.dto.CreatePluginToolRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateVersionReq;
import com.openjiuwen.studio.agent.manager.dto.ExportParams;
import com.openjiuwen.studio.agent.manager.dto.GetPluginVersionQo;
import com.openjiuwen.studio.agent.manager.dto.ImportRsp;
import com.openjiuwen.studio.agent.manager.dto.ListPluginsQo;
import com.openjiuwen.studio.agent.manager.dto.ListToolsQo;
import com.openjiuwen.studio.agent.manager.dto.ModifyPluginReq;
import com.openjiuwen.studio.agent.manager.dto.ModifyPluginRsp;
import com.openjiuwen.studio.agent.manager.dto.ParsePluginReq;
import com.openjiuwen.studio.agent.manager.dto.PluginAuthUpdateReq;
import com.openjiuwen.studio.agent.manager.dto.PluginAuthUpdateRsp;
import com.openjiuwen.studio.agent.manager.dto.PluginBindFunctionReq;
import com.openjiuwen.studio.agent.manager.dto.PluginListRsp;
import com.openjiuwen.studio.agent.manager.dto.VersionInfo;
import com.openjiuwen.studio.agent.manager.dto.VersionListRsp;

import org.springframework.core.io.Resource;
import org.springframework.web.multipart.MultipartFile;

/**
 * Plugin service
 */

public interface IPluginService {

    /**
     * batchCreateTool
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param body body
     */
    BatchCreatePluginToolRsp batchCreateTool(String projectId, String workspaceId, BatchCreatePluginToolReq body);

    /**
     * createPlugin
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param body body
     */
    CreatePluginToolRsp createPlugin(String projectId, String workspaceId, CreatePluginToolReq body);

    /**
     * createTool
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param body body
     */
    CreatePluginToolRsp createTool(String projectId, String workspaceId, CreatePluginToolReq body);

    /**
     * createToolOpenAPIById
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param pluginId pluginId
     * @param toolId toolId
     */
    BaseResp createToolOpenAPIById(String projectId, String workspaceId, String pluginId, String toolId);

    /**
     * deletePlugin
     *
     * @param projectId projectId
     * @param pluginId pluginId
     * @param workspaceId workspaceId
     */
    CommonDeleteRsp deletePlugin(String projectId, String pluginId, String workspaceId);

    /**
     * deletePluginVersion
     *
     * @param projectId projectId
     * @param versionId versionId
     * @param pluginId pluginId
     * @param workspaceId workspaceId
     */
    CommonDeleteRsp deletePluginVersion(String projectId, String versionId, String pluginId, String workspaceId);

    /**
     * deleteTool
     *
     * @param projectId projectId
     * @param pluginId pluginId
     * @param toolId toolId
     * @param workspaceId workspaceId
     */
    BaseResp deleteTool(String projectId, String pluginId, String toolId, String workspaceId);

    /**
     * exportplugins
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param body body
     */
    Resource exportplugins(String projectId, String workspaceId, ExportParams body);

    /**
     * getPluginVersion
     *
     * @param projectId projectId
     * @param versionId versionId
     * @param pluginId pluginId
     * @param getPluginVersionQo getPluginVersionQo
     */
    BaseResp getPluginVersion(String projectId, String versionId, String pluginId,
        GetPluginVersionQo getPluginVersionQo);

    /**
     * importplugins
     *
     * @param workspaceId workspaceId
     * @param projectId projectId
     * @param file file
     * @param importIds importIds
     */
    ImportRsp importplugins(String workspaceId, String projectId, MultipartFile file, String importIds);

    /**
     * incrementPluginFreeTrialUsageQuota
     *
     * @param projectId projectId
     * @param domainId domainId
     * @param pluginId pluginId
     * @param workspaceId workspaceId
     */
    BaseResp incrementPluginFreeTrialUsageQuota(String projectId, String domainId, String pluginId, String workspaceId);

    /**
     * listPluginVersions
     *
     * @param projectId projectId
     * @param pluginId pluginId
     * @param workspaceId workspaceId
     */
    VersionListRsp listPluginVersions(String projectId, String pluginId, String workspaceId);

    /**
     * listPlugins
     *
     * @param projectId projectId
     * @param listPluginsQo listPluginsQo
     */
    PluginListRsp listPlugins(String projectId, ListPluginsQo listPluginsQo);

    /**
     * listTools
     *
     * @param projectId projectId
     * @param listToolsQo listToolsQo
     */
    BaseResp listTools(String projectId, ListToolsQo listToolsQo);

    /**
     * modifyPlugin
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param pluginId pluginId
     * @param body body
     */
    ModifyPluginRsp modifyPlugin(String projectId, String workspaceId, String pluginId, ModifyPluginReq body);

    /**
     * modifyTool
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param toolId toolId
     * @param body body
     */
    BaseResp modifyTool(String projectId, String workspaceId, String toolId, CreatePluginToolReq body);

    /**
     * parsePlugin
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param body body
     */
    BaseResp parsePlugin(String projectId, String workspaceId, ParsePluginReq body);

    /**
     * releasePluginVersion
     *
     * @param projectId projectId
     * @param pluginId pluginId
     * @param workspaceId workspaceId
     * @param body body
     */
    VersionInfo releasePluginVersion(String projectId, String pluginId, String workspaceId, CreateVersionReq body);

    /**
     * retrievePlugin
     *
     * @param projectId projectId
     * @param pluginId pluginId
     * @param workspaceId workspaceId
     */
    BaseResp retrievePlugin(String projectId, String pluginId, String workspaceId);

    /**
     * updatePluginAuthInfo
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param pluginId pluginId
     * @param body body
     */
    PluginAuthUpdateRsp updatePluginAuthInfo(String projectId, String workspaceId, String pluginId,
        PluginAuthUpdateReq body);

    /**
     * 根据工具id和版本id进行版本还原
     *
     * @param projectId projectId
     * @param pluginId pluginId
     * @param versionId versionId
     * @param workspaceId workspaceId
     * @return BaseResp
     */
    BaseResp updatePluginVersionByVersionId(String projectId, String pluginId, String versionId,
        String workspaceId);
}