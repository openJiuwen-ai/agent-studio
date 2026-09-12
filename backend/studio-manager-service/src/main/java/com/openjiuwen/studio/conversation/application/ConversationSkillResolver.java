/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.conversation.application;

import com.openjiuwen.studio.agent.manager.bo.SkillDetails;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.dto.SkillStatus;
import com.openjiuwen.studio.agent.manager.entity.SkillEntity;
import com.openjiuwen.studio.agent.manager.mapper.SkillMapper;
import com.openjiuwen.studio.conversation.application.dto.ConversationSkillContext;
import com.openjiuwen.studio.conversation.application.dto.ConversationSkillDescriptor;
import com.openjiuwen.studio.conversation.application.dto.ConversationSkillVo;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;

import lombok.extern.slf4j.Slf4j;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;

@Service
@Slf4j
public class ConversationSkillResolver {
    private static final int PAGE_SIZE = 1000;

    private final SkillMapper skillMapper;

    public ConversationSkillResolver(SkillMapper skillMapper) {
        this.skillMapper = skillMapper;
    }

    public List<ConversationSkillVo> listAvailable(String projectId, String workspaceId, String domainId) {
        return loadCatalog(projectId, workspaceId, domainId).stream()
            .map(item -> ConversationSkillVo.builder()
                .skillId(item.getSkillId())
                .name(item.getName())
                .description(item.getDescription())
                .build())
            .toList();
    }

    public ConversationSkillContext resolveForRun(String projectId, String workspaceId, String domainId,
                                                  List<String> requestedIds) {
        List<String> recommendedSkillIds = new ArrayList<>(new LinkedHashSet<>(
            requestedIds == null ? List.of() : requestedIds));
        List<ConversationSkillDescriptor> catalog;
        try {
            catalog = loadCatalog(projectId, workspaceId, domainId);
        } catch (RuntimeException e) {
            if (recommendedSkillIds.isEmpty()) {
                log.warn("Failed to load conversation skill catalog without recommendations, using empty catalog: "
                    + "projectId={}, workspaceId={}, domainId={}", projectId, workspaceId, domainId, e);
                return ConversationSkillContext.empty();
            }
            log.warn("Failed to load conversation skill catalog with recommendations: projectId={}, workspaceId={}, "
                + "domainId={}", projectId, workspaceId, domainId, e);
            throw new AgentStudioException(StudioError.METHOD_ARGUMENT_NOT_VALID,
                List.of("recommended skills are unavailable"));
        }
        Set<String> availableIds = catalog.stream()
            .map(ConversationSkillDescriptor::getSkillId)
            .collect(Collectors.toSet());
        if (!availableIds.containsAll(recommendedSkillIds)) {
            throw new AgentStudioException(StudioError.METHOD_ARGUMENT_NOT_VALID,
                List.of("recommended skill is unavailable"));
        }
        return new ConversationSkillContext(catalog, recommendedSkillIds);
    }

    private List<ConversationSkillDescriptor> loadCatalog(String projectId, String workspaceId, String domainId) {
        SkillEntity condition = new SkillEntity()
            .setProjectId(projectId)
            .setWorkspaceId(workspaceId)
            .setDomainId(domainId)
            .setStatus(SkillStatus.DEVELOPED.getValue());
        List<ConversationSkillDescriptor> result = new ArrayList<>();
        for (int offset = 0; ; offset += PAGE_SIZE) {
            List<SkillDetails> page = skillMapper.search(condition, offset, PAGE_SIZE, null, null, 0);
            page.stream()
                .filter(item -> Objects.equals(domainId, item.getDomainId()))
                .filter(item -> Objects.equals(projectId, item.getProjectId()))
                .filter(item -> Objects.equals(workspaceId, item.getWorkspaceId()))
                .filter(item -> Objects.equals(SkillStatus.DEVELOPED.getValue(), item.getStatus()))
                .filter(item -> StringUtils.isNotBlank(item.getSkillId()))
                .filter(item -> StringUtils.isNotBlank(item.getLatestVersion()))
                .filter(item -> StringUtils.isNotBlank(item.getObsPath()))
                .map(this::toDescriptor)
                .forEach(result::add);
            if (page.size() < PAGE_SIZE) {
                return result;
            }
        }
    }

    private ConversationSkillDescriptor toDescriptor(SkillDetails skill) {
        return ConversationSkillDescriptor.builder()
            .skillId(skill.getSkillId())
            .versionId(skill.getLatestVersion())
            .name(skill.getName())
            .description(skill.getDescription())
            .objectKey(skill.getObsPath())
            .build();
    }
}
