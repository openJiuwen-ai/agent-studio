/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.mapper;

import com.openjiuwen.studio.agent.common.a2a.enums.RegistrationStatus;
import com.openjiuwen.studio.agent.manager.entity.AgentRdcRegistrationEntity;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * Agent RDC 注册 Mapper
 *
 * <p>FEAT-131: 注册状态持久化</p>
 */
@Mapper
public interface AgentRdcRegistrationMapper {

    /**
     * 插入注册记录
     */
    int insert(AgentRdcRegistrationEntity entity);

    /**
     * 根据 agentId 查询注册记录
     */
    AgentRdcRegistrationEntity selectByAgentId(@Param("agentId") String agentId);

    /**
     * 查询所有需重试的异常记录
     */
    List<AgentRdcRegistrationEntity> selectByStatus(@Param("status") RegistrationStatus status);

    /**
     * 根据 agentId 更新注册状态（选择性更新非空字段）
     */
    int updateStatusByAgentId(AgentRdcRegistrationEntity entity);

    /**
     * 根据 agentId 删除注册记录
     */
    int deleteByAgentId(@Param("agentId") String agentId);
}
