/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.agentbase.service.clean.pipeline.subtask;

import com.openjiuwen.studio.agent.agentbase.mapper.CommonCleanMapper;
import com.openjiuwen.studio.agent.foundation.base.exception.AgentBaseException;
import com.openjiuwen.studio.agent.foundation.base.exception.ErrorCode;

import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * 租户知识库表清理子任务
 * <p>
 * 负责清理知识库相关的数据表：
 * t_knowledge_test_record, t_knowledge_base_obs_execute_record, t_knowledge_base_obs_config,
 * t_knowledge_segment_rule, t_knowledge_repo, t_knowledge_base
 * <p>
 * 作为独立的 Spring 组件，直接处理所有表操作
 *
 * @since 2025-12-20
 */
@Slf4j
@Component
public class TenantCleanKnowledgeTableSubtask {

    private static final String LOG_CLEAN_TABLE_PROGRESS = "Cleaning knowledge table: {}, domainId: {}";

    private static final String LOG_CLEAN_TABLE_SUCCESS = "Successfully cleaned knowledge table: {}, domainId: {}";

    @Resource
    private CommonCleanMapper commonCleanMapper;

    /**
     * 执行知识库表清理
     * <p>
     * 多张表的 DELETE 在同一事务内执行：任一张表失败则整体回滚，避免租户数据半清理。
     *
     * @param domainId 租户ID
     */
    @Transactional(rollbackFor = Exception.class)
    public void executeCleanup(String domainId) {
        try {
            log.info("Starting knowledge tables cleanup for domainId: {}", domainId);

            // 从配置解析表名
            String[] tables = parseKnowledgeTables();

            // 按配置顺序清理所有表
            for (String table : tables) {
                if (StringUtils.isBlank(table)) {
                    continue;
                }

                log.debug(LOG_CLEAN_TABLE_PROGRESS, table, domainId);

                // 使用通用清理方法
                int deletedRows = commonCleanMapper.deleteDataByDomainId(table, domainId);
                log.debug("Deleted {} rows from table: {}", deletedRows, table);

                log.info(LOG_CLEAN_TABLE_SUCCESS, table, domainId);
            }

            log.info("Knowledge tables cleanup completed successfully for domainId: {}", domainId);

        } catch (Exception e) {
            log.error("Knowledge tables cleanup failed for domainId: {}, error: {}", domainId, e.getMessage());
            throw new AgentBaseException(ErrorCode.SERVER_INTERNAL_ERROR, e);
        }
    }

    /**
     * 解析知识库清理表的配置
     */
    public String[] parseKnowledgeTables() {
        // 默认清理的表顺序（知识库相关表）
        return new String[] {
            "t_knowledge_test_record",                // 测试记录表
            "t_knowledge_base_obs_execute_record",    // obs执行记录表
            "t_knowledge_base_obs_config",            // obs配置表
            "t_knowledge_segment_rule",               // 知识分段规则表
            "t_knowledge_repo",                       // 知识库仓库表
            "t_knowledge_base"                        // 知识库主表
        };
    }
}