/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.workflow.resource.adapt;

import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.enums.ImportDescEnum;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.ControllerVO;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.MemoryRepoEntity;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.enums.AgentStatus;
import com.openjiuwen.studio.agent.manager.enums.ResourceTypeEnum;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.MemoryRepoMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.AgentCommonService;
import com.openjiuwen.studio.agent.manager.service.ShareResourceManagerService;
import com.openjiuwen.studio.agent.manager.utils.DatetimeUtils;
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
import org.apache.commons.lang3.Strings;
import org.apache.commons.lang3.StringUtils;
import org.jetbrains.annotations.NotNull;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import java.util.stream.Collectors;

@Slf4j
@Component("CONTROLLER")
public class ControllerAdapter extends ResourceAdapter {

    @Autowired
    private ShareResourceManagerService shareResourceManagerService;

    @Autowired
    private AgentMapper agentMapper;

    @Autowired
    private I18nUtil i18nUtil;

    @Autowired
    private MgObsService obsService;

    @Autowired
    private AgentCommonService agentCommonService;

    @Autowired
    private ReleaseVersionMapper releaseVersionMapper;

    @Autowired
    private MemoryRepoMapper memoryRepoMapper;

    @Override
    public ExportResp parseExport(List<ExportResourceUnit> exportResources) {
        if (CollectionUtils.isEmpty(exportResources)) {
            log.info("controller resource input is null");
            return null;
        }
        Map<String, List<String>> parentIdMap = getParentIdMap(exportResources);
        List<String> agentIds = exportResources.stream().map(ExportResourceUnit::getResourceId).toList();
        List<Agent> agents = agentMapper.selectByAgentIds(RequestContextUtils.getRequestProjectId(),
            ResourceTypeEnum.CONTROLLER.toString(), agentIds);
        if (CollectionUtils.isEmpty(agents)) {
            log.info("controller resource output is null");
            return null;
        }
        Map<String, Agent> agentMap = agents.stream().collect(Collectors.toMap(Agent::getAgentId, p -> p));
        // 构造导出结果
        ExportResp exportResp = new ExportResp();
        List<ExportResult> exportResults = getExportResults(exportResources, agents);
        exportResp.setExportResults(exportResults);

        // 构造发布的数据
        List<ExportInfo> exportInfos = new ArrayList<>();
        List<ReleaseVersion> releaseVersions = getReleaseVersions(exportResults);

        if (CollectionUtils.isNotEmpty(releaseVersions)) {
            for (ReleaseVersion releaseVersion : releaseVersions) {
                ExportInfo exportInfo = new ExportInfo();
                exportInfo.setResourceId(releaseVersion.getAppId());
                exportInfo.setResourceType(ResourceTypeEnum.CONTROLLER.toString());
                exportInfo.setResourceLevel(2);
                ControllerVO agentDslInfo = JSONObject.parseObject(
                    obsService.downloadObsFile(releaseVersion.getDslPath()), ControllerVO.class);
                exportInfo.setResourceName(agentDslInfo.getName());
                exportInfo.setDsl(agentDslInfo);
                exportInfo.setReleaseVersion(releaseVersion);
                exportInfo.setMetadata(agentMap.get(releaseVersion.getAppId()));
                // 根资源的 parentResourceId 为 null，parentIdMap 会得到 [null]；过滤后为空则设 null，
                // 与草稿分支一致，避免导入时 CollectionUtils.isEmpty([null])=false 导致根资源不被识别为 parent。
                List<String> parents = parentIdMap.get(releaseVersion.getAppId());
                if (parents != null) {
                    parents = parents.stream().filter(StringUtils::isNotEmpty).collect(Collectors.toList());
                }
                exportInfo.setParents(CollectionUtils.isEmpty(parents) ? null : parents);
                exportInfos.add(exportInfo);
            }
        }
        List<ExportResourceUnit> latestResources = exportResources.stream()
            .filter(p -> Strings.CS.equals(p.getResourceVersion(), Constants.LATEST_PUBLISH_VERSION))
            .toList();
        List<ExportResult> successExportResults = exportResults.stream()
            .filter(p -> p.getStatus() == ImportExportStatusEnum.SUCCESS)
            .toList();
        if (CollectionUtils.isNotEmpty(latestResources)) {
            for (ExportResult resourceUnit : successExportResults) {
                Agent agent = agentMap.get(resourceUnit.getResourceId());
                if (Objects.isNull(agent)) {
                    log.info("controller :{} is null", resourceUnit.getResourceId());
                    continue;
                }
                ExportInfo latestInfo = new ExportInfo();
                latestInfo.setResourceId(resourceUnit.getResourceId());
                latestInfo.setResourceType(ResourceTypeEnum.CONTROLLER.toString());
                ControllerVO agentInfo = JSONObject.parseObject(obsService.downloadObsFile(agent.getDslPath()),
                    ControllerVO.class);
                latestInfo.setResourceName(agentInfo.getName());
                latestInfo.setDsl(agentInfo);
                latestInfo.setMetadata(agent);
                latestInfo.setResourceLevel(1);
                latestInfo.setShareInfo(shareResourceManagerService.exportShareInfo(resourceUnit.getResourceId()));
                latestInfo.setLevel2Resources(resourceUnit.getLevel2Resources());
                exportInfos.add(latestInfo);
            }
        }
        exportResp.setExportInfos(exportInfos);
        return exportResp;
    }

    @NotNull
    private List<ExportResult> getExportResults(List<ExportResourceUnit> exportResources, List<Agent> agents) {
        List<String> validWfIds = agents.stream().map(Agent::getAgentId).toList();
        List<ExportResult> exportResults = new ArrayList<>();
        for (ExportResourceUnit exportResourceUnit : exportResources) {
            ExportResult result = new ExportResult();
            result.setResourceId(exportResourceUnit.getResourceId());
            result.setResourceName(exportResourceUnit.getResourceName());
            result.setResourceType(exportResourceUnit.getResourceType());
            result.setResourceVersion(exportResourceUnit.getResourceVersion());
            result.setStatus(ImportExportStatusEnum.SUCCESS);
            if (!validWfIds.contains(exportResourceUnit.getResourceId())) {
                result.setReason(i18nUtil.getMessage(StudioError.EXPORT_RESOURCE_NOT_EXISTS,
                    ResourceTypeEnum.CONTROLLER.toString()));
                result.setStatus(ImportExportStatusEnum.FAILED);
            }
            result.setLevel2Resources(exportResourceUnit.getLevel2Resources());
            result.setResourceLevel(exportResourceUnit.getResourceLevel());
            exportResults.add(result);
        }
        return exportResults;
    }

    @Override
    public void checkBeforeImport(ImportCheckResult importCheckResult, ImportInfo importInfo) {
        checkMetadata(importInfo);
        Agent agent = JsonUtils.objectToClassType(importInfo.getMetadata(), Agent.class);
        importCheckResult.setDescription(agent.getDescription());
        Agent existingAgent = getControllerByTraceId(importInfo.getTargetProjectId(), importInfo.getTargetWorkspaceId(),
            agent.getTraceId());
        importCheckResult.setStatus(existingAgent != null);
        importCheckResult.setImportDesc(getControllerImportDesc(existingAgent, importInfo.getReleaseVersion()));
    }

    private void checkMetadata(ImportInfo importInfo) {
        if (importInfo.getDsl() == null || importInfo.getMetadata() == null) {
            throw new AgentStudioException(StudioError.FILE_LACKS_SOURCE_DATA);
        }
    }

    private Agent getControllerByTraceId(String projectId, String workspaceId, String traceId) {
        List<Agent> agentList = agentMapper.selectAgentByTraceIdAndWorkspaceId(projectId, workspaceId, traceId);
        if (CollectionUtils.isEmpty(agentList)) {
            return null;
        }
        return agentList.get(0);
    }

    private ImportDescEnum getControllerImportDesc(Agent agent, ReleaseVersion releaseVersion) {
        // 如果为空则需新增资源
        if (agent == null) {
            return ImportDescEnum.NEW_RESOURCE;
        }
        // 草稿无版本
        if (releaseVersion == null) {
            return ImportDescEnum.UPDATE_RESOURCE;
        }
        // 如果traceId一致,版本号一致则跳过，不一致则需新增版本（agent数据缺少版本号）
        ReleaseVersion existVersion = releaseVersionMapper.selectByAppIdAndVersionId(agent.getAgentId(),
            releaseVersion.getVersionId());
        if (existVersion != null) {
            return ImportDescEnum.RESOURCE_EXISTS;
        }
        return ImportDescEnum.NEW_RESOURCE_VERSION;
    }

    @Override
    public void parseImport(ImportResourceResult importResourceResult, ImportInfo importInfo) {
        checkMetadata(importInfo);
        Agent agent = JsonUtils.objectToClassType(importInfo.getMetadata(), Agent.class);
        String version = importInfo.getReleaseVersion() != null ? importInfo.getReleaseVersion().getVersionId() : null;
        setImportResultDesc(importResourceResult, version, agent.getDescription());
        updateMetadata(importInfo, agent);
        Agent existingAgent = getControllerByTraceId(importInfo.getTargetProjectId(), importInfo.getTargetWorkspaceId(),
            agent.getTraceId());
        // 若当前空间资源不存在
        if (existingAgent == null) {
            try {
                createController(importInfo, agent, importResourceResult);
            } catch (AgentStudioException e) {
                handleException(importResourceResult, e);
            }
        } else {
            if (!Strings.CS.equals(existingAgent.getAgentId(), agent.getAgentId())) {
                agent.setAgentId(existingAgent.getAgentId());
                importResourceResult.setNewId(existingAgent.getAgentId());
            }
            updateController(importInfo, agent, importResourceResult);
        }
    }

    private void updateMetadata(ImportInfo importInfo, Agent agent) {
        agent.setProjectId(importInfo.getTargetProjectId());
        agent.setWorkspaceId(importInfo.getTargetWorkspaceId());
        agent.setDomainId(importInfo.getTargetDomainId());
        agent.setCreator(importInfo.getCreator());
        agent.setCreatorId(importInfo.getCreatorId());
        agent.setCreatedOn(new Timestamp(new Date().getTime()));
        agent.setUpdatedOn(new Timestamp(new Date().getTime()));
    }

    private void createController(ImportInfo importInfo, Agent agent, ImportResourceResult result) {
        // 此id已存在，则更换id
        if (agentMapper.selectById(agent.getAgentId()) != null) {
            String agentId = UUID.randomUUID().toString();
            agent.setAgentId(agentId);
            result.setNewId(agentId);
        }
        verifyingAndReplaceResourceInfo(agent);
        String dslPath = agentCommonService.getAgentObsPath(agent.getAgentId(), CommonConstant.Workflow.FLOW);
        String irPath = agentCommonService.getAgentObsPath(agent.getAgentId(), CommonConstant.Workflow.IR);
        agent.setDslPath(dslPath);
        agent.setIrPath(irPath);
        agent.setStatus(
            importInfo.getReleaseVersion() == null ? AgentStatus.DRAFT.toString() : AgentStatus.PUBLISHED.toString());
        agentMapper.insert(agent);

        handleReleaseVersion(agent, importInfo.getReleaseVersion());
        // 标记首次导入：放在所有操作成功之后，避免中途异常时 addTag=true 导致 FAILED 结果仍触发草稿 DSL 上传
        result.setAddTag(true);
    }

    private void handleReleaseVersion(Agent agent, ReleaseVersion releaseVersion) {
        if (releaseVersion == null) {
            return;
        }
        String dslPath = agentCommonService.getAgentObsPath(agent.getAgentId(), CommonConstant.Workflow.FLOW, releaseVersion.getVersionId());
        String irPath = agentCommonService.getAgentObsPath(agent.getAgentId(), CommonConstant.Workflow.IR, releaseVersion.getVersionId());
        // 创建版本数据
        releaseVersion.setId(UUID.randomUUID().toString());
        releaseVersion.setAppId(agent.getAgentId());
        releaseVersion.setDslPath(dslPath);
        releaseVersion.setIrPath(irPath);
        releaseVersion.setCreatorId(agent.getCreatorId());
        releaseVersion.setCreator(agent.getCreator());
        releaseVersionMapper.insert(releaseVersion);
    }

    private void verifyingAndReplaceResourceInfo(Agent agent) {
        if (Objects.nonNull(agent.getMemoryConfig())) {
            MemoryRepoEntity memoryRepoEntity = memoryRepoMapper.selectByIdAndWorkspaceId(
                agent.getMemoryConfig().getMemoryRepoId(), RequestContextUtils.getRequestWorkspaceId());
            if (Objects.isNull(memoryRepoEntity)) {
                agent.setMemoryConfig(null);
            }
        }
    }

    private void updateController(ImportInfo importInfo, Agent agent, ImportResourceResult result) {

        if (importInfo.getReleaseVersion() == null) {
            return;
        }
        ReleaseVersion existVersion = releaseVersionMapper.selectByAppIdAndVersionId(agent.getAgentId(),
            importInfo.getReleaseVersion().getVersionId());
        // 版本已存在，跳过
        if (existVersion != null) {
            return;
        }
        // 发布新版本
        ReleaseVersion releaseVersion = importInfo.getReleaseVersion();
        releaseVersion.setVersionId(String.valueOf(System.currentTimeMillis()));
        String defaultVersionName = "v" + DatetimeUtils.dateFormat(new Date(),
            DatetimeUtils.DATE_FORMAT_YYYYMMDDHHMMSS);
        releaseVersion.setVersionName(defaultVersionName);
        handleReleaseVersion(agent, importInfo.getReleaseVersion());
        result.setNewVersion(releaseVersion.getVersionId());
    }

}
