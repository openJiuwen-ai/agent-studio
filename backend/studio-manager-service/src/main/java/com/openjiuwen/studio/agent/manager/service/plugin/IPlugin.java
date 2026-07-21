/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.plugin;

import com.openjiuwen.studio.agent.common.dto.run.RunToolRequestBody;
import com.openjiuwen.studio.agent.common.dto.tool.RunToolResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ToolReference;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.ToolEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowExportEntity;
import com.openjiuwen.studio.agent.manager.entity.plugin.PluginEntity;

import java.util.Collection;
import java.util.List;

public interface IPlugin {
    List<ToolReference> getToolReferences(String projectId, String workspaceId, List<String> pluginIds);

    boolean isNewTool(PluginEntity pluginEntity);

    Collection<String> buildResourceId(PluginEntity pluginEntity);

    ToolEntity getToolEntity(String toolId, String projectId, String opProjectId, String versionId);

    void validTools(String projectId, String workspaceId, List<String> toolIds);

    void updateOldTool(String projectId, String versionId, String toolId);

    void insertByTool(ToolEntity tool);

    void updateByOldTool(ToolEntity tool);
    

    ToolEntity getOldToolEntity(String toolId, String projectId, String opSvcProjectId, String versionId);

    String getPluginId(String toolId);

    void handleAdapterToolId(ToolEntity tool);

    ReleaseVersion releaseToolVersionHandler(String toolId, String versionId, String versionName, String versionNote);

    void handleToolWithoutToolId(WorkflowExportEntity workflowExportEntity);

    void updateName(ToolEntity tool);

    void handleToolReleaseVersionId(WorkflowExportEntity workflowExportEntity);

    List<PluginEntity> getPlugin(String projectId, String workspaceId, List<String> pluginIds);

    PluginEntity getPluginByTraceId(String workspaceId, String traceId);

    String getToolIdFromPlugin(String toolId);

    RunToolResponseBody runTool(String projectId, RunToolRequestBody body);
}
