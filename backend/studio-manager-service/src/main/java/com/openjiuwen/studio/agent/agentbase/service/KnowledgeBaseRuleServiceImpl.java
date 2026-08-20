/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.agentbase.service;

import com.openjiuwen.studio.agent.agentbase.common.constant.CommonConstant;
import com.openjiuwen.studio.agent.agentbase.entity.KnowledgeBaseEntity;
import com.openjiuwen.studio.agent.agentbase.entity.KnowledgeSegmentRuleEntity;
import com.openjiuwen.studio.agent.agentbase.mapper.KnowledgeBaseMapper;
import com.openjiuwen.studio.agent.agentbase.mapper.KnowledgeSegmentRuleMapper;
import com.openjiuwen.studio.agent.agentbase.model.KnowledgeSegRuleInfo;
import com.openjiuwen.studio.agent.agentbase.service.knowledgerepo.KnowledgeConnectionRouterService;
import com.openjiuwen.studio.agent.agentbase.service.knowledgerepo.KnowledgeRepoContext;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.foundation.base.exception.AgentBaseException;
import com.openjiuwen.studio.agent.foundation.base.exception.ErrorCode;
import com.openjiuwen.studio.agent.manager.dto.CreateKnowledgeSegmentRuleRequestBody;
import com.openjiuwen.studio.agent.manager.dto.CreateKnowledgeSegmentRuleResponseBody;
import com.openjiuwen.studio.agent.manager.dto.DeleteOneResponseBody;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeSegmentRule;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeSegmentRulesResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ModifyKnowledgeSegmentRuleRequestBody;
import com.openjiuwen.studio.agent.manager.dto.ModifyKnowledgeSegmentRuleResponseBody;
import com.openjiuwen.studio.agent.manager.service.IKnowledgeRuleManagementService;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.List;
import java.util.Objects;

@Slf4j
@Service
public class KnowledgeBaseRuleServiceImpl implements IKnowledgeRuleManagementService {

    private static final String DEFAULT_RULE_ID = "default-rule-1";

    private static final List<String> DEFAULT_RULE = Arrays.asList("^第([零〇一二三四五六七八九十百千万1-9]{1,7})章",
        "^第([零〇一二三四五六七八九十百千万1-9]{1,7})节", "^第([零〇一二三四五六七八九十百千万1-9]{1,7})条");

    private final KnowledgeRepoContext knowledgeRepoContext;

    private final KnowledgeSegmentRuleMapper segmentRuleMapper;

    private final KnowledgeBaseMapper knowledgeBaseMapper;

    private final KnowledgeConnectionRouterService knowledgeConnectionRouterService;

    @Value("${knowledge.source}")
    private String knowledgeSource;

    public KnowledgeBaseRuleServiceImpl(KnowledgeRepoContext knowledgeRepoContext,
        KnowledgeSegmentRuleMapper segmentRuleMapper, KnowledgeBaseMapper knowledgeBaseMapper,
        KnowledgeConnectionRouterService knowledgeConnectionRouterService) {
        this.knowledgeRepoContext = knowledgeRepoContext;
        this.segmentRuleMapper = segmentRuleMapper;
        this.knowledgeBaseMapper = knowledgeBaseMapper;
        this.knowledgeConnectionRouterService = knowledgeConnectionRouterService;
    }

    @Override
    public CreateKnowledgeSegmentRuleResponseBody createKnowledgeSegmentRule(String projectId, String workspaceId,
        CreateKnowledgeSegmentRuleRequestBody body) {
        log.info("operation log projectId: {}, userId:{}, createSegmentRule", projectId,
            RequestContextUtils.getRequestUserId());
        // 调用知识库平台接口创建知识分层规则
        KnowledgeSegmentRule segmentRule = new KnowledgeSegmentRule();
        segmentRule.setRuleRegexs(body.getRuleRegexs());
        String repoId = StringUtils.isBlank(body.getRepoId())
            ? null
            : knowledgeBaseMapper.selectById(projectId, body.getRepoId()).getExternalId();
        KnowledgeSegRuleInfo knowledgeSegRuleInfo = knowledgeRepoContext.getService(knowledgeSource)
            .createSegmentRule(segmentRule, repoId);

        // 知识分层规则入库
        KnowledgeSegmentRuleEntity ruleEntity = new KnowledgeSegmentRuleEntity();
        ruleEntity.setId(knowledgeSegRuleInfo.getRuleId());
        ruleEntity.setProjectId(projectId);
        ruleEntity.setDomainId(RequestContextUtils.getRequestUserDomainId());
        ruleEntity.setDomainName(RequestContextUtils.getRequestUserDomainName());
        ruleEntity.setRule(String.join(CommonConstant.ZERO_SPACE, segmentRule.getRuleRegexs()));
        ruleEntity.setCreator(RequestContextUtils.getRequestUserName());
        ruleEntity.setCreatorId(RequestContextUtils.getRequestUserId());
        ruleEntity.setWorkspaceId(workspaceId);
        ruleEntity.setKnowledgeBaseConnectionId(knowledgeSegRuleInfo.getKnowledgeBaseConnectionId());
        ruleEntity.setCreatedOn(new Date());
        ruleEntity.setUpdatedOn(new Date());
        segmentRuleMapper.insert(ruleEntity);
        return new CreateKnowledgeSegmentRuleResponseBody().setId(knowledgeSegRuleInfo.getRuleId());
    }

    @Override
    public DeleteOneResponseBody deleteKnowledgeSegmentRule(String projectId, String id, String workspaceId) {
        log.info("operation log projectId: {}, userId:{}, deleteSegmentRule", projectId,
            RequestContextUtils.getRequestUserId());
        KnowledgeSegmentRuleEntity ruleEntity = segmentRuleMapper.selectByPrimaryKey(id, projectId);
        if (Objects.isNull(ruleEntity)) {
            return null;
        }
        // 调用知识库平台接口删除知识分层规则
        knowledgeRepoContext.getService(knowledgeSource).deleteSegmentRule(id);

        // 删除库中记录
        segmentRuleMapper.deleteByPrimaryKey(id, projectId);
        return new DeleteOneResponseBody().setId(id);
    }

    @Override
    public ListKnowledgeSegmentRulesResponseBody listKnowledgeSegmentRules(String projectId, String workspaceId,
        String repoId) {
        // 默认规则
        KnowledgeSegmentRule defaultRule = new KnowledgeSegmentRule();
        defaultRule.setId(DEFAULT_RULE_ID);
        defaultRule.setRuleRegexs(DEFAULT_RULE);
        defaultRule.setProjectId("");
        List<KnowledgeSegmentRule> ruleList = new ArrayList<>();
        ruleList.add(defaultRule);
        List<KnowledgeSegmentRuleEntity> segmentRuleEntities;
        if (StringUtils.isNotEmpty(repoId)) {
            KnowledgeBaseEntity knowledgeBaseEntity = knowledgeBaseMapper.selectByIdAndWorkspaceId(workspaceId, repoId);
            // 用户创建的规则
            segmentRuleEntities = segmentRuleMapper.selectByDomainId(projectId, workspaceId,
                knowledgeBaseEntity.getKnowledgeBaseConnectionId());
        } else {
            String connectionId = knowledgeConnectionRouterService.findConnectionIdByContext();
            segmentRuleEntities = segmentRuleMapper.selectByDomainId(projectId, workspaceId, connectionId);

        }
        if (!CollectionUtils.isEmpty(segmentRuleEntities)) {
            ruleList.addAll(segmentRuleEntities.stream().map(KnowledgeSegmentRuleEntity::convertToDto).toList());
        }
        return new ListKnowledgeSegmentRulesResponseBody().setCount(ruleList.size()).setRuleList(ruleList);
    }

    @Override
    public ModifyKnowledgeSegmentRuleResponseBody modifyKnowledgeSegmentRule(String projectId, String workspaceId,
        String id, ModifyKnowledgeSegmentRuleRequestBody body) {
        log.info("operation log projectId: {}, userId:{}, modifySegmentRule", projectId,
            RequestContextUtils.getRequestUserId());
        // 存在性校验
        KnowledgeSegmentRuleEntity ruleEntity = segmentRuleMapper.selectByPrimaryKey(id, projectId);
        if (Objects.isNull(ruleEntity)) {
            log.error("rule entity [{}] is not exist", id);
            throw new AgentBaseException(ErrorCode.KNOWLEDGE_SEGMENT_RULE_NOT_EXIST);
        }
        // 调用知识库平台接口修改知识分层规则
        knowledgeRepoContext.getService(knowledgeSource)
            .modifySegmentRule(new KnowledgeSegmentRule().setId(id).setRuleRegexs(body.getRuleRegexs()));

        // 修改库中记录
        ruleEntity.setRule(String.join(CommonConstant.ZERO_SPACE, body.getRuleRegexs()));
        ruleEntity.setUpdatedOn(new Date());
        segmentRuleMapper.updateByPrimaryKeySelective(ruleEntity);
        return new ModifyKnowledgeSegmentRuleResponseBody().setId(id);
    }

    public boolean isExistedSegmentRule(String id, String workspaceId) {
        KnowledgeSegmentRuleEntity knowledgeBase = segmentRuleMapper.selectByIdAndWorkspaceId(workspaceId, id);
        return Objects.nonNull(knowledgeBase);
    }
}
