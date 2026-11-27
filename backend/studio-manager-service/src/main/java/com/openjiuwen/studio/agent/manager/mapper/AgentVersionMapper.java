/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.mapper;

import com.openjiuwen.studio.agent.manager.entity.AgentVersion;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * agent版本 数据库操作mapper
 *
 */
@Mapper
public interface AgentVersionMapper {
    /**
     * 插入一条agent版本到数据库
     *
     * @param agentVersion agentVersion
     * @return int
     */
    int insert(AgentVersion agentVersion);

    /**
     * 根据project id和versionId从数据库查询agent版本
     *
     * @param projectId projectId
     * @param versionId versionId
     * @return agent version
     */
    AgentVersion selectByPrimaryKey(@Param("projectId") String projectId, @Param("versionId") String versionId);

    /**
     * 根据agent id从数据库获取agent在线版本
     *
     * @param agentId agentId
     * @return agent version
     */
    AgentVersion selectOnlineVersion(@Param("agentId") String agentId);

    /**
     * 更新agent版本在线状态
     *
     * @param isOnline isOnline
     */
    void updateAgentVersionStatus(@Param("isOnline") boolean isOnline, @Param("versionId") String versionId);

    /**
     * 根据agent ID从数据库删除对应agent版本
     *
     * @param agentId agentId
     * @return int
     */
    int deleteByAgentId(@Param("agentId") String agentId);

    void updateProjectIdByVersionIds(@Param("opSvcProjectId") String opSvcProjectId, @Param("versionIds") List<String> versionIds);
}
