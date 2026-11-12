package com.openjiuwen.studio.agent.manager.mapper;/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2020-2025. All rights reserved.
 */

import com.openjiuwen.studio.agent.manager.entity.McpServerEntity;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Map;

/**
 * ws_mcp_server_def 表操作类
 *
 */
@Mapper
public interface McpServerV2Mapper {
    List<McpServerEntity> queryServerWithPage(@Param("offset") int offset, @Param("limit") int limit,
          @Param("tenantId") String tenantId, @Param("name") String name, @Param("language") String language,
                                              @Param("orgType") String orgType, @Param("category") String category);

    Long queryServerWithPageCount(@Param("tenantId") String tenantId, @Param("name") String name, @Param("language") String language, @Param("orgType") String orgType, @Param("category") String category);

    List<McpServerEntity> selectList();

    McpServerEntity selectById(String id);

    List<McpServerEntity> selectList(String serverId, String tenantId, String deptCode);

    int insert(McpServerEntity serverEntity);

    int updateViewTimes(String serverId);

    int updateInstallTimes(String serverId);

    /**
     * 按上架来源的MCP服务实例ID查询服务目录条目（含已上架快照）。
     *
     * @param sourceInstanceId MCP服务实例ID（ws_mcp_service_def.id）
     * @return 服务目录条目，不存在返回 null
     */
    McpServerEntity selectBySourceInstanceId(@Param("sourceInstanceId") String sourceInstanceId);

    /**
     * 上架刷新服务目录条目快照内容（重复上架同一实例时使用）。
     *
     * @param serverEntity 待更新的目录条目（按 id 定位）
     * @return 更新的行数
     */
    int updateContentById(McpServerEntity serverEntity);

    /**
     * 下架服务目录条目：软删 + 释放上架来源关联（保证唯一索引可复用）。
     *
     * @param id 目录条目ID
     * @param updatedByUserId 操作人ID
     * @return 更新的行数
     */
    int updateOffShelfById(@Param("id") String id, @Param("updatedByUserId") String updatedByUserId);

    /**
     * 批量查询已上架（platform_published=1 且未删除）目录条目的上架来源实例ID映射。
     *
     * <p>用于组件库 MCP 实例列表标注"已上架到资产广场"状态（source_instance_id → 目录条目 id）。</p>
     *
     * @param sourceInstanceIds MCP服务实例ID集合（ws_mcp_service_def.id）
     * @return Map：source_instance_id → 目录条目 id
     */
    List<Map<String, String>> selectShelfServerIdsBySourceInstanceIds(
        @Param("sourceInstanceIds") List<String> sourceInstanceIds);
}
