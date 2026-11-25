/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.workflow.resource.adapt;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.bo.SkillDetails;
import com.openjiuwen.studio.agent.manager.entity.SkillEntity;
import com.openjiuwen.studio.agent.manager.enums.ResourceTypeEnum;
import com.openjiuwen.studio.agent.manager.mapper.SkillMapper;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ExportInfo;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ExportResourceUnit;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ExportResp;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ExportResult;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ImportCheckResult;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ImportExportStatusEnum;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ImportInfo;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ImportResourceResult;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;

@Slf4j
@Component("SKILL")
public class SkillAdapter extends ResourceAdapter {

    @Autowired
    private SkillMapper skillMapper;

    @Autowired
    private I18nUtil i18nUtil;

    @Override
    public ExportResp parseExport(List<ExportResourceUnit> exportResources) {
        if (CollectionUtils.isEmpty(exportResources)) {
            log.info("skill resource input is null");
            return null;
        }
        Map<String, List<String>> parentIdMap = getParentIdMap(exportResources);
        List<String> skillIds = exportResources.stream().map(ExportResourceUnit::getResourceId).toList();
        // 导出请求由当前 domain 发起，按"本 domain 全部 + 跨 domain 已上架"过滤（issue #1734 隔离语义，
        // 粒度与 getSkillPackageContent / deleteStudioSkill 对齐：同 domain 内跨 workspace/project 可见）
        String domainId = RequestContextUtils.getRequestUserDomainId();
        List<SkillDetails> skillDetailsList = skillMapper.searchBySkillIds(skillIds, domainId);
        if (CollectionUtils.isEmpty(skillDetailsList)) {
            return null;
        }
        Map<String, SkillDetails> skillDetailsMap = skillDetailsList.stream()
            .filter(Objects::nonNull)
            .collect(Collectors.toMap(SkillDetails::getSkillId, skill -> skill,
                (existing, replacement) -> existing, HashMap::new));
        ExportResp exportResp = new ExportResp();
        // 构造导出结果
        exportResp.setExportResults(getExportResults(exportResources, skillDetailsMap));
        // 构造导出数据
        List<ExportInfo> exportInfos = new ArrayList<>();
        List<SkillDetails> skillDetails = skillDetailsList.stream().toList();
        for (SkillDetails skill : skillDetails) {
            ExportInfo exportInfo = new ExportInfo();
            exportInfo.setResourceId(skill.getSkillId());
            exportInfo.setResourceType(ResourceTypeEnum.SKILL.toString());
            exportInfo.setResourceName(skill.getName());
            exportInfo.setMetadata(skill);
            exportInfo.setParents(parentIdMap.get(skill.getSkillId()));
            exportInfos.add(exportInfo);
        }
        exportResp.setExportInfos(exportInfos);
        return exportResp;
    }

    private List<ExportResult> getExportResults(List<ExportResourceUnit> exportResources,
        Map<String, SkillDetails> skillDetailsMap) {
        List<String> skillIds = skillDetailsMap.keySet().stream().toList();
        List<ExportResult> exportResults = new ArrayList<>();
        for (ExportResourceUnit exportResourceUnit : exportResources) {
            ExportResult result = new ExportResult();
            result.setResourceId(exportResourceUnit.getResourceId());
            result.setResourceName(exportResourceUnit.getResourceName());
            result.setResourceType(exportResourceUnit.getResourceType());
            result.setStatus(ImportExportStatusEnum.SUCCESS);
            exportResults.add(result);
        }
        return exportResults;
    }

    @Override
    public void checkBeforeImport(ImportCheckResult importCheckResult, ImportInfo importInfo) {
        checkMetadata(importInfo);
        SkillEntity skill = JsonUtils.objectToClassType(importInfo.getMetadata(), SkillEntity.class);
        importCheckResult.setDescription(skill.getDescription());
        // 检查用户是否已拥有同名skill
        SkillDetails existingSkill = getSkillByName(importInfo.getTargetProjectId(), importInfo.getTargetWorkspaceId(),
            skill.getName());
        importCheckResult.setStatus(existingSkill != null);
        importCheckResult.setImportDesc(getImportDescSpecialResource(existingSkill));
    }

    private void checkMetadata(ImportInfo importInfo) {
        if (importInfo.getMetadata() == null) {
            throw new AgentStudioException(StudioError.FILE_LACKS_SOURCE_DATA);
        }
    }

    @Override
    public void parseImport(ImportResourceResult importResourceResult, ImportInfo importInfo) {
        checkMetadata(importInfo);
        SkillEntity skill = JsonUtils.objectToClassType(importInfo.getMetadata(), SkillEntity.class);
        setImportResultDesc(importResourceResult, null, skill.getDescription());
        handleSkill(importInfo, skill, importResourceResult);
    }

    private void handleSkill(ImportInfo importInfo, SkillEntity skill, ImportResourceResult result) {
        updateMetadata(importInfo, skill);
        // 1.检查用户是否已拥有同名skill
        SkillDetails existingSkill = getSkillByName(importInfo.getTargetProjectId(), importInfo.getTargetWorkspaceId(),
            skill.getName());
        if (existingSkill != null) {
            // 2.名称匹配成功，引用现有资源
            result.setNewId(existingSkill.getSkillId());
            result.setNewName(existingSkill.getName());
            result.setNewVersion(existingSkill.getUsedVersion());
            log.info("Skill name '{}' already exists, referencing existing skill with id: {}",
                skill.getName(), existingSkill.getSkillId());
        } else {
            // 3.名称匹配不成功，添加原有资源关系
            result.setId(skill.getSkillId());
            result.setName(skill.getName());
            result.setVersion(skill.getUsedVersion());
            // 表明此资源无效，但导入关系
            result.setValid(false);
            log.info("Skill '{}' not found, creating mapping for original skill", skill.getName());
        }
    }

    private SkillDetails getSkillByName(String projectId, String workspaceId, String skillName) {
        List<SkillDetails> results = skillMapper.search(
            new SkillEntity().setProjectId(projectId).setWorkspaceId(workspaceId).setName(skillName), 0, 1, null, null,
            0);
        return CollectionUtils.isNotEmpty(results) ? results.get(0) : null;
    }


    private void updateMetadata(ImportInfo importInfo, SkillEntity skill) {
        skill.setDomainId(importInfo.getTargetDomainId());
        skill.setCreatorId(importInfo.getCreatorId());
        skill.setCreatedAt(System.currentTimeMillis());
        skill.setUpdatedAt(System.currentTimeMillis());
    }
}
