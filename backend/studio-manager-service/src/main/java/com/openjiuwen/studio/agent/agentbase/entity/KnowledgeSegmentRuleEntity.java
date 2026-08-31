/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.agentbase.entity;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.openjiuwen.studio.agent.agentbase.common.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeSegmentRule;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Arrays;
import java.util.Date;

/**
 * 知识文件分层规则实体类
 *
 * @since 2025-04-12
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class KnowledgeSegmentRuleEntity {
    private String id;

    @JsonProperty("project_id")
    private String projectId;

    @JsonProperty("domain_id")
    private String domainId;

    @JsonProperty("domain_name")
    private String domainName;

    private String rule;

    private String creator;

    @JsonProperty("creator_id")
    private String creatorId;

    @JsonProperty("created_on")
    private Date createdOn;

    @JsonProperty("updated_on")
    private Date updatedOn;

    @JsonProperty("workspace_id")
    private String workspaceId;

    @JsonProperty("knowledge_base_connection_id")
    private String knowledgeBaseConnectionId;

    /**
     * 数据库实体类转换成DTO
     *
     * @return KnowledgeSegmentRule
     */
    public KnowledgeSegmentRule convertToDto() {
        KnowledgeSegmentRule segmentRule = new KnowledgeSegmentRule();
        segmentRule.setId(id);
        segmentRule.setProjectId(projectId);
        segmentRule.setRuleRegexs(Arrays.asList(rule.split(CommonConstant.ZERO_SPACE, -1)));
        segmentRule.setCreator(creator);
        segmentRule.setCreatorId(creatorId);
        segmentRule.setCreateTime(createdOn != null ? createdOn.getTime() : null);
        segmentRule.setUpdateTime(updatedOn != null ? updatedOn.getTime() : null);
        return segmentRule;
    }
}
