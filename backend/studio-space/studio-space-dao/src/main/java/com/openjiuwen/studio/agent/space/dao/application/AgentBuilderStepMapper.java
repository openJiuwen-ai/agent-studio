/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2020-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.space.dao.application;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.openjiuwen.studio.agent.space.dao.entity.AgentBuilderStepEntity;

import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Update;

import java.util.List;

/**
 * 步骤表操作类
 */
@Mapper
public interface AgentBuilderStepMapper extends BaseMapper<AgentBuilderStepEntity> {
    @Insert({
        """
        <script>
            <if test='_databaseId == "postgres"'>
                INSERT INTO ws_agent_builder_step_def (id, agent_name, message_id, finished, domain_id, dept_code, created_date, created_by_user_id, last_updated_date, last_updated_by_user_id, deleted)
                VALUES (#{id}, #{agentName}, #{messageId}, #{finished}, #{domainId}, #{deptCode}, #{createdDate}, #{createdByUserId}, #{lastUpdatedDate}, #{lastUpdatedByUserId}, #{deleted})
                ON CONFLICT (id) DO NOTHING
            </if>
            <if test='_databaseId != "postgres"'>
                INSERT IGNORE INTO ws_agent_builder_step_def (id, agent_name, message_id, finished, domain_id, dept_code, created_date, created_by_user_id, last_updated_date, last_updated_by_user_id, deleted)
                VALUES (#{id}, #{agentName}, #{messageId}, #{finished}, #{domainId}, #{deptCode}, #{createdDate}, #{createdByUserId}, #{lastUpdatedDate}, #{lastUpdatedByUserId}, #{deleted})
            </if>
        </script>
        """
    })
    int insertIfNotExists(AgentBuilderStepEntity entity);

    @Update(
        "UPDATE ws_agent_builder_step_def SET finished = #{finished}, last_updated_date = #{lastUpdatedDate} WHERE id = #{id}")
    int updateStepFinishedById(AgentBuilderStepEntity entity);

    @Insert({
        """
                <script>
                    INSERT INTO ws_agent_builder_step_def (id, agent_name, message_id, finished, domain_id, dept_code, created_date, created_by_user_id, last_updated_date,last_updated_by_user_id, deleted)
                    VALUES
                    <foreach collection='list' item='item' separator=','>
                        (#{item.id}, #{item.agentName}, #{item.messageId}, #{item.finished}, #{item.domainId}, #{item.deptCode}, #{item.createdDate}, #{item.createdByUserId}, #{item.lastUpdatedDate}, #{item.lastUpdatedByUserId}, #{item.deleted})
                    </foreach>
                </script>
            """
    })
    void batchInsert(List<AgentBuilderStepEntity> stepEntities);
}
