/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.mcp.model.dao;

import com.openjiuwen.studio.agent.manager.entity.McpServerEntity;
import com.openjiuwen.studio.agent.manager.mapper.McpServerV2Mapper;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

/**
 * NodeDao
 *
 * @Date: 2024/12/19 15:59
 * @Description:
 */

@Component
public class McpServerDao {
    private final McpServerV2Mapper mcpServerMapper;

    @Autowired
    public McpServerDao(McpServerV2Mapper mcpServerMapper) {
        this.mcpServerMapper = mcpServerMapper;
    }

    public List<McpServerEntity> listMineMcpServerEntities(String serverId, String tenantId, String deptCode) {
        return mcpServerMapper.selectList(serverId, tenantId, deptCode);
    }


    public List<McpServerEntity> selectServerList() {
        return mcpServerMapper.selectList();
    }

    public McpServerEntity selectById(String id) {
        return mcpServerMapper.selectById(id);
    }

    public int updateViewTimes(String serverId) {
        return mcpServerMapper.updateViewTimes(serverId);
    }

    public int insert(McpServerEntity serverEntity) {
        return mcpServerMapper.insert(serverEntity);
    }

    public int updateInstallTimes(String serverId) {
        return mcpServerMapper.updateInstallTimes(serverId);
    }

    public List<McpServerEntity> queryServerWithPage(int offset, int limit, String tenantId, String name, String language, String orgType, String category) {
        if (limit > 100) {
            limit = 10;
        }
        return mcpServerMapper.queryServerWithPage(offset, limit, tenantId, name, language, orgType, category);
    }

    public Long queryServerWithPageCount(String tenantId, String name, String language, String orgType, String catogory) {
        return mcpServerMapper.queryServerWithPageCount(tenantId, name, language, orgType, catogory);
    }

    /**
     * 按上架来源的MCP服务实例ID查询服务目录条目（含已上架快照）。
     */
    public McpServerEntity selectBySourceInstanceId(String sourceInstanceId) {
        return mcpServerMapper.selectBySourceInstanceId(sourceInstanceId);
    }

    /**
     * 上架刷新服务目录条目快照内容。
     */
    public int updateContentById(McpServerEntity serverEntity) {
        return mcpServerMapper.updateContentById(serverEntity);
    }

    /**
     * 下架服务目录条目：软删 + 释放上架来源关联。
     */
    public int updateOffShelfById(String id, String updatedByUserId) {
        return mcpServerMapper.updateOffShelfById(id, updatedByUserId);
    }

    /**
     * 批量查询已上架目录条目的上架来源实例ID映射（source_instance_id → 目录条目 id）。
     */
    public Map<String, String> selectShelfServerIdsBySourceInstanceIds(List<String> sourceInstanceIds) {
        if (sourceInstanceIds == null || sourceInstanceIds.isEmpty()) {
            return Map.of();
        }
        List<Map<String, String>> rows = mcpServerMapper.selectShelfServerIdsBySourceInstanceIds(sourceInstanceIds);
        Map<String, String> result = new java.util.HashMap<>();
        if (rows != null) {
            for (Map<String, String> row : rows) {
                result.put(row.get("source_instance_id"), row.get("id"));
            }
        }
        return result;
    }
}
