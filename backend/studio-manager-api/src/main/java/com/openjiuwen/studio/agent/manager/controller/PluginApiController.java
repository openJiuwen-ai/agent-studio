/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.controller;

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
import com.openjiuwen.studio.agent.manager.dto.PluginListRsp;
import com.openjiuwen.studio.agent.manager.dto.VersionInfo;
import com.openjiuwen.studio.agent.manager.dto.VersionListRsp;
import com.openjiuwen.studio.agent.manager.service.IPluginService;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.Resource;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

/**
 * Plugin controller
 */
@RestController

public class PluginApiController implements PluginApi {
    private static final Logger log = LoggerFactory.getLogger(PluginApiController.class);

    @Autowired
    private IPluginService pluginService;

    @Override
    public ResponseEntity<BatchCreatePluginToolRsp> batchCreateTool(String projectId, String workspaceId,
        BatchCreatePluginToolReq body) {
        return ResponseModel.success(pluginService.batchCreateTool(projectId, workspaceId, body));
    }

    @Override
    public ResponseEntity<CreatePluginToolRsp> createPlugin(String projectId, String workspaceId,
        CreatePluginToolReq body) {
        return ResponseModel.success(pluginService.createPlugin(projectId, workspaceId, body));
    }

    @Override
    public ResponseEntity<CreatePluginToolRsp> createTool(String projectId, String workspaceId,
        CreatePluginToolReq body) {
        return ResponseModel.success(pluginService.createTool(projectId, workspaceId, body));
    }

    @Override
    public ResponseEntity<BaseResp> createToolOpenAPIById(String projectId, String workspaceId, String pluginId,
        String toolId) {
        return ResponseModel.success(pluginService.createToolOpenAPIById(projectId, workspaceId, pluginId, toolId));
    }

    @Override
    public ResponseEntity<CommonDeleteRsp> deletePlugin(String projectId, String pluginId, String workspaceId) {
        return ResponseModel.success(pluginService.deletePlugin(projectId, pluginId, workspaceId));
    }

    @Override
    public ResponseEntity<CommonDeleteRsp> deletePluginVersion(String projectId, String versionId, String pluginId,
        String workspaceId) {
        return ResponseModel.success(pluginService.deletePluginVersion(projectId, versionId, pluginId, workspaceId));
    }

    @Override
    public ResponseEntity<BaseResp> deleteTool(String projectId, String pluginId, String toolId, String workspaceId) {
        return ResponseModel.success(pluginService.deleteTool(projectId, pluginId, toolId, workspaceId));
    }

    @Override
    public ResponseEntity<Resource> exportplugins(String projectId, String workspaceId, ExportParams body) {
        return ResponseModel.successDownload(pluginService.exportplugins(projectId, workspaceId, body));
    }

    @Override
    public ResponseEntity<BaseResp> getPluginVersion(String projectId, String versionId, String pluginId,
        GetPluginVersionQo getPluginVersionQo) {
        return ResponseModel.success(
            pluginService.getPluginVersion(projectId, versionId, pluginId, getPluginVersionQo));
    }

    @Override
    public ResponseEntity<ImportRsp> importplugins(String workspaceId, String projectId, MultipartFile file,
        String importIds) {
        return ResponseModel.success(pluginService.importplugins(workspaceId, projectId, file, importIds));
    }

    @Override
    public ResponseEntity<BaseResp> incrementPluginFreeTrialUsageQuota(String projectId, String domainId,
        String pluginId, String workspaceId) {
        return ResponseModel.success(
            pluginService.incrementPluginFreeTrialUsageQuota(projectId, domainId, pluginId, workspaceId));
    }

    @Override
    public ResponseEntity<VersionListRsp> listPluginVersions(String projectId, String pluginId, String workspaceId) {
        return ResponseModel.success(pluginService.listPluginVersions(projectId, pluginId, workspaceId));
    }

    @Override
    public ResponseEntity<PluginListRsp> listPlugins(String projectId, ListPluginsQo listPluginsQo) {
        return ResponseModel.success(pluginService.listPlugins(projectId, listPluginsQo));
    }

    @Override
    public ResponseEntity<BaseResp> listTools(String projectId, ListToolsQo listToolsQo) {
        return ResponseModel.success(pluginService.listTools(projectId, listToolsQo));
    }

    @Override
    public ResponseEntity<ModifyPluginRsp> modifyPlugin(String projectId, String workspaceId, String pluginId,
        ModifyPluginReq body) {
        return ResponseModel.success(pluginService.modifyPlugin(projectId, workspaceId, pluginId, body));
    }

    @Override
    public ResponseEntity<BaseResp> modifyTool(String projectId, String workspaceId, String toolId,
        CreatePluginToolReq body) {
        return ResponseModel.success(pluginService.modifyTool(projectId, workspaceId, toolId, body));
    }

    @Override
    public ResponseEntity<BaseResp> parsePlugin(String projectId, String workspaceId, ParsePluginReq body) {
        return ResponseModel.success(pluginService.parsePlugin(projectId, workspaceId, body));
    }

    @Override
    public ResponseEntity<VersionInfo> releasePluginVersion(String projectId, String pluginId, String workspaceId,
        CreateVersionReq body) {
        return ResponseModel.success(pluginService.releasePluginVersion(projectId, pluginId, workspaceId, body));
    }

    @Override
    public ResponseEntity<BaseResp> retrievePlugin(String projectId, String pluginId, String workspaceId) {
        return ResponseModel.success(pluginService.retrievePlugin(projectId, pluginId, workspaceId));
    }

    @Override
    public ResponseEntity<PluginAuthUpdateRsp> updatePluginAuthInfo(String projectId, String workspaceId,
        String pluginId, PluginAuthUpdateReq body) {
        return ResponseModel.success(pluginService.updatePluginAuthInfo(projectId, workspaceId, pluginId, body));
    }

    @Override
    public ResponseEntity<BaseResp> updatePluginVersionByVersionId(String projectId, String pluginId,
        String versionId, String workspaceId) {
        return ResponseModel.success(
            pluginService.updatePluginVersionByVersionId(projectId, pluginId, versionId, workspaceId));
    }
}