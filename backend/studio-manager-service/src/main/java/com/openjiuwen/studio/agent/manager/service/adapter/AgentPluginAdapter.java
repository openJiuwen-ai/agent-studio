/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.adapter;

import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.manager.dto.AgentInfo;
import com.openjiuwen.studio.agent.manager.dto.ToolReference;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.plugin.PluginEntity;
import com.openjiuwen.studio.agent.manager.enums.ResourceTypeEnum;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.plugin.PluginMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.plugin.IPluginBase;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ExportResourceUnit;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
@Slf4j
public class AgentPluginAdapter {
    @Autowired
    private IPluginBase pluginBaseImpl;

    @Autowired
    private MgObsService obsService;

    @Autowired
    private AgentMapper agentMapper;

    @Autowired
    private PluginMapper pluginMapper;

    public String getToolVersion(String pluginId, String toolVersion) {
        if (StringUtils.isNotEmpty(toolVersion)) {
            return toolVersion;
        }
        // 资产广场上架插件未显式指定版本时锚定上架版本（#1735 测试反馈）：
        // 与运行时 PluginAdapterImpl.getToolEntity 的锚定口径一致，
        // 避免保存/导入等缺省路径静默回退到最新发布版造成版本漂移。
        String plazaAnchorVersionId = resolvePlazaAnchorVersionId(pluginId);
        if (StringUtils.isNotEmpty(plazaAnchorVersionId)) {
            return plazaAnchorVersionId;
        }
        String lastVersion = pluginBaseImpl.getLastVersion(pluginId);
        if (StringUtils.isNotEmpty(lastVersion)) {
            return lastVersion;
        }
        return toolVersion;
    }

    /**
     * 解析资产广场上架锚定版本ID：仅当插件已上架（platform_published=1 且 published=1，
     * 口径与 PluginAdapterImpl.resolvePlazaAnchorVersionId 一致）且锚定版本非空时返回
     * plaza_version_id；否则返回 null。查询异常返回 null，不阻断原最新版回退逻辑。
     */
    private String resolvePlazaAnchorVersionId(String pluginId) {
        if (StringUtils.isEmpty(pluginId)) {
            return null;
        }
        try {
            PluginEntity pluginEntity = pluginMapper.selectByPrimaryKey(pluginId, null);
            if (pluginEntity == null) {
                return null;
            }
            boolean plazaPublished = pluginEntity.getPlatformPublished() != null
                && pluginEntity.getPlatformPublished() == 1
                && pluginEntity.getPublished() != null
                && pluginEntity.getPublished() == 1;
            return plazaPublished ? pluginEntity.getPlazaVersionId() : null;
        } catch (Exception e) {
            log.warn("Failed to resolve plaza anchor version, fallback to last version. pluginId: {}", pluginId, e);
            return null;
        }
    }

    public String getToolVersionFromAgent(ExportResourceUnit exportResourceUnit) {
        // 如果资源版本不为空，直接返回
        String resourceVersion = exportResourceUnit.getResourceVersion();
        if (StringUtils.isNotEmpty(resourceVersion)) {
            return resourceVersion;
        }

        // 检查应用类型是否是 AGENT
        if (Strings.CS.equals(exportResourceUnit.getAppType(), ResourceTypeEnum.AGENT.toString())) {
            // 获取代理信息
            Agent agent = agentMapper.selectById(exportResourceUnit.getAppId());
            AgentInfo agentInfo = JSONObject.parseObject(obsService.downloadObsFile(agent.getDslPath()),
                AgentInfo.class);

            // 查找工具引用
            ToolReference toolReference = agentInfo.getTools()
                .stream()
                .filter(p -> Strings.CS.equals(p.getToolId(), exportResourceUnit.getResourceId()))
                .findFirst()
                .orElse(null);

            // 如果找到工具引用，返回其最后版本ID
            if (toolReference != null) {
                return toolReference.getLastVersionId();
            }
        }

        // 默认返回资源版本
        return resourceVersion;
    }
}
