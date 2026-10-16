/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.mapper;

import com.openjiuwen.studio.agent.common.dto.TriggerConfig;
import com.openjiuwen.studio.agent.manager.dto.AgentApplicationInfo;
import com.openjiuwen.studio.agent.manager.dto.AgentVersionListItem;
import com.openjiuwen.studio.agent.manager.dto.SearchCriteria;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.AgentBaseInfo;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.Date;
import java.util.List;

/**
 * agent 数据库操作mapper
 *
 */
@Mapper
public interface AgentMapper {
    /**
     * 插入一条agent到数据库
     *
     * @param agent agent
     * @return int
     */
    int insert(Agent agent);

    /**
     * 根据project id和agent_id从数据库查询agent
     *
     * @param projectId projectId
     * @param agentId agentId
     * @return agent
     */
    Agent selectByPrimaryKey(@Param("projectId") String projectId, @Param("agentId") String agentId);

    /**
     * 根据project id和agent_id从数据库查询agent
     *
     * @param projectId projectId
     * @return agent
     */
    int selectByAgentIdAndResourceId(@Param("projectId") String projectId, @Param("workspaceId") String workspaceId,
        @Param("resourceId") String resourceId, @Param("resourceType") String resourceType);

    /**
     * 根据项目ID和工作空间ID选择代理。
     *
     * @param projectId 项目的唯一标识符
     * @param agentId 代理的唯一标识符
     * @return 返回匹配的Agent对象
     */
    Agent selectByProjectIdAndWorkspaceId(@Param("projectId") String projectId,
        @Param("workspaceId") String workspaceId, @Param("agentId") String agentId);

    /**
     * 根据project id和查询条件从数据库获取agent列表
     *
     * @param projectId projectId
     * @param searchCriteria searchCriteria
     * @return agent列表
     */
    List<Agent> selectByProjectIdAndSearchCriteria(@Param("projectId") String projectId,
        @Param("searchCriteria") SearchCriteria searchCriteria);

    /**
     * 根据project id和名称查询已发布的智能体列表（包括工作流应用）
     *
     * @param projectId projectId
     * @return agent列表
     */
    List<AgentApplicationInfo> selectByProjectIdAndSearchKey(@Param("projectId") String projectId,
        @Param("ids") List<String> ids, @Param("name") String name, @Param("status") String status,
        @Param("types") List<String> types, @Param("workspaceId") String workspaceId);

    /**
     * 根据主键更新agent的部分非空字段
     *
     * @param record record
     * @return int
     */
    int updateByPrimaryKeySelective(Agent record);

    int updateTriggerList(@Param("projectId") String projectId, @Param("workspaceId") String workspaceId,
        @Param("agentId") String agentId, @Param("triggerList") List<TriggerConfig> triggerList,
        @Param("updatedOn") Date updatedOn);

    /**
     * 根据主键从数据库删除agent
     *
     * @param agentId agentId
     * @param projectId projectId
     * @return int
     */
    int deleteByPrimaryKey(@Param("agentId") String agentId, @Param("projectId") String projectId);
    int deleteByPrimaryKeys(@Param("agentIds") List<String> agentIds);

    /**
     * 根据主键从数据库软删除agent
     *
     * @param agentId agentId
     * @param projectId projectId
     * @return int
     */
    int softDeleteByPrimaryKey(@Param("agentId") String agentId, @Param("projectId") String projectId);

    List<String> findAgentToBeDeleted(@Param("softDeleteTtl") LocalDateTime softDeleteTtl);

    Agent selectById(@Param("agentId") String agentId);

    /**
     * 根据主键更新agent的部分非空字段
     *
     * @param updateValue agent对象
     * @return int
     */
    int updateOwnerById(@Param("updateValue") Agent updateValue, @Param("id") String id);

    /**
     * 根据搜索条件搜最最新版本发布的agent
     *
     * @param projectId projectId
     * @param searchCriteria searchCriteria
     * @return 最新版本列表
     */
    List<AgentVersionListItem> getAgentLastVersionBySearchCriteria(@Param("projectId") String projectId,
        @Param("searchCriteria") SearchCriteria searchCriteria);

    List<Agent> selectAgentByTraceIdAndWorkspaceId(@Param("projectId") String projectId,
        @Param("workspaceId") String workspaceId, @Param("traceId") String traceId);

    void updateAgentById(@Param("projectId") String projectId, @Param("workspaceId") String workspaceId,
        @Param("agentId") String agentId, @Param("agentInfo") Agent agent);

    void updateAgentByTraceId(@Param("projectId") String projectId, @Param("workspaceId") String workspaceId,
        @Param("traceId") String traceId, @Param("agentInfo") Agent agent);

    int countAgentCountByDomainId(@Param("domainId") String domainId);

    /**
     * 按id搜索agents
     *
     * @param projectId projectId
     * @param agentIds agentIds
     * @return agent列表
     */
    List<Agent> selectByAgentIds(@Param("projectId") String projectId, @Param("type") String type,
        @Param("agentIds") List<String> agentIds);

    /**
     * 根据项目ID和工作空间ID选择代理。
     *
     * @param projectId 项目的唯一标识符
     * @param agentIds 代理ids
     * @return 返回匹配的Agent对象
     */
    List<Agent> selectByIdsAndProjectIdAndWorkspaceId(@Param("projectId") String projectId,
        @Param("workspaceId") String workspaceId, @Param("agentIds") List<String> agentIds);

    List<AgentBaseInfo> queryAgentList(@Param("agentType") String agentType, @Param("limit") int limit,
        @Param("offset") int offset);

    int selectByDomainId(@Param("domainId") String domainId, @Param("status") String status,
        @Param("publishedOn") Timestamp date);

    void updateProjectIdByAgentIds(String opSvcProjectId, List<String> agentIds);

    void updateAgentShareStatus(@Param("agentId") String agentId, @Param("status") int status);

    int countAgentIdInDb(@Param("agentId") String agentId);

    /**
     * 查询绑定了指定记忆库的智能体列表
     *
     * @param memoryRepoId 记忆库ID
     * @return 绑定了该记忆库的智能体列表
     */
    List<Agent> selectByMemoryRepoId(@Param("memoryRepoId") String memoryRepoId);

    /**
     * 清除指定智能体的记忆配置
     *
     * @param agentId 智能体ID
     */
    void clearMemoryConfig(@Param("agentId") String agentId);
}
