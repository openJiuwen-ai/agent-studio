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
import com.openjiuwen.studio.agent.manager.dto.AgentInfo;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.enums.AgentStatus;
import com.openjiuwen.studio.agent.manager.enums.ResourceTypeEnum;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.AgentCommonService;
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
@Component("AGENT")
public class AgentAdapter extends ResourceAdapter {

    private static final String AGENT_NAME_REGEX
        = "^[\\u4e00-\\u9fa5a-zA-Z0-9_\\-（）()！!](?:[\\u4e00-\\u9fa5a-zA-Z0-9_\\-（）()！! ]*[\\u4e00-\\u9fa5a-zA-Z0-9_\\-（）()！!])?$";

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


    @Override
    public ExportResp parseExport(List<ExportResourceUnit> exportResources) {
        if (CollectionUtils.isEmpty(exportResources)) {
            log.info("agent resource input is null");
            return null;
        }
        Map<String, List<String>> parentIdMap = getParentIdMap(exportResources);
        List<String> agentIds = exportResources.stream().map(ExportResourceUnit::getResourceId).toList();
        List<Agent> agents = agentMapper.selectByAgentIds(RequestContextUtils.getRequestProjectId(),
            ResourceTypeEnum.AGENT.toString(), agentIds);
        if (CollectionUtils.isEmpty(agents)) {
            log.info("agent resource output is null");
            return null;
        }
        Map<String, Agent> agentIdMap = agents.stream().collect(Collectors.toMap(Agent::getAgentId, p -> p));
        // 构造导出结果
        ExportResp exportResp = new ExportResp();
        List<ExportResult> exportResults = getExportResults(exportResources, agents);
        exportResp.setExportResults(exportResults);

        List<ReleaseVersion> releaseVersions = getReleaseVersions(exportResults);
        // 构造发布的数据
        List<ExportInfo> exportInfos = new ArrayList<>();
        if (CollectionUtils.isNotEmpty(releaseVersions)) {
            for (ReleaseVersion releaseVersion : releaseVersions) {
                ExportInfo exportInfo = new ExportInfo();
                exportInfo.setResourceId(releaseVersion.getAppId());
                exportInfo.setResourceType(ResourceTypeEnum.AGENT.toString());
                exportInfo.setResourceLevel(2);
                AgentInfo agentDslInfo = JSONObject.parseObject(obsService.downloadObsFile(releaseVersion.getDslPath()),
                    AgentInfo.class);
                exportInfo.setResourceName(agentDslInfo.getName());
                exportInfo.setDsl(agentDslInfo);
                exportInfo.setReleaseVersion(releaseVersion);
                exportInfo.setMetadata(agentIdMap.get(releaseVersion.getAppId()));
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

        // 构造导出根数据
        List<ExportResourceUnit> latestResources = exportResources.stream()
            .filter(p -> p.getResourceLevel() == 1)
            .toList();
        if (CollectionUtils.isNotEmpty(latestResources)) {
            for (ExportResourceUnit resourceUnit : latestResources) {
                Agent latestagent = agentIdMap.get(resourceUnit.getResourceId());
                if (Objects.isNull(latestagent)) {
                    log.info("agent :{} is null", resourceUnit.getResourceId());
                    continue;
                }
                ExportInfo latestInfo = new ExportInfo();
                String dsl = getDsl(resourceUnit, latestagent.getDslPath(), latestInfo);
                latestInfo.setResourceId(resourceUnit.getResourceId());
                latestInfo.setResourceType(ResourceTypeEnum.AGENT.toString());
                AgentInfo agentInfo = JSONObject.parseObject(obsService.downloadObsFile(dsl),
                    AgentInfo.class);
                latestInfo.setDsl(agentInfo);
                latestInfo.setResourceName(agentInfo.getName());
                latestInfo.setMetadata(latestagent);
                latestInfo.setResourceLevel(1);
                latestInfo.setLevel2Resources(resourceUnit.getLevel2Resources());
                exportInfos.add(latestInfo);
            }
        }
        exportResp.setExportInfos(exportInfos);
        return exportResp;
    }

    @NotNull
    private List<ExportResult> getExportResults(List<ExportResourceUnit> exportResources, List<Agent> agents) {
        List<String> validAgentIds = agents.stream().map(Agent::getAgentId).toList();
        List<ExportResult> exportResults = new ArrayList<>();
        for (ExportResourceUnit exportResourceUnit : exportResources) {
            ExportResult result = new ExportResult();
            result.setResourceId(exportResourceUnit.getResourceId());
            result.setResourceName(exportResourceUnit.getResourceName());
            result.setResourceType(exportResourceUnit.getResourceType());
            result.setResourceLevel(exportResourceUnit.getResourceLevel());
            result.setResourceVersion(exportResourceUnit.getResourceVersion());
            result.setLevel2Resources(exportResourceUnit.getLevel2Resources());
            result.setResourceLevel(exportResourceUnit.getResourceLevel());
            result.setStatus(ImportExportStatusEnum.SUCCESS);
            if (!validAgentIds.contains(exportResourceUnit.getResourceId())) {
                result.setReason(
                    i18nUtil.getMessage(StudioError.EXPORT_RESOURCE_NOT_EXISTS, ResourceTypeEnum.AGENT.toString()));
                result.setStatus(ImportExportStatusEnum.FAILED);
            }
            exportResults.add(result);
        }
        return exportResults;
    }

    @Override
    public void checkBeforeImport(ImportCheckResult importCheckResult, ImportInfo importInfo) {
        checkMetadata(importInfo);
        Agent agent = JsonUtils.objectToClassType(importInfo.getMetadata(), Agent.class);
        importCheckResult.setDescription(agent.getDescription());
        Agent existingAgent = getAgentByTraceId(importInfo.getTargetProjectId(), importInfo.getTargetWorkspaceId(),
            agent.getTraceId());
        importCheckResult.setStatus(existingAgent != null);
        importCheckResult.setImportDesc(
            getAgentImportDesc(existingAgent, importInfo.getReleaseVersion()));
    }

    private void checkMetadata(ImportInfo importInfo) {
        if (importInfo.getDsl() == null || importInfo.getMetadata() == null) {
            throw new AgentStudioException(StudioError.FILE_LACKS_SOURCE_DATA);
        }
    }

    private Agent getAgentByTraceId(String projectId, String workspaceId, String traceId) {
        List<Agent> agentList = agentMapper.selectAgentByTraceIdAndWorkspaceId(projectId, workspaceId, traceId);
        if (CollectionUtils.isEmpty(agentList)) {
            return null;
        }
        return agentList.get(0);
    }

    private ImportDescEnum getAgentImportDesc(Agent agent, ReleaseVersion releaseVersion) {
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
        Agent existingAgent = getAgentByTraceId(importInfo.getTargetProjectId(), importInfo.getTargetWorkspaceId(),
            agent.getTraceId());
        // 若当前空间agent不存在
        if (existingAgent == null) {
            try {
                createAgent(importInfo, agent, importResourceResult);
            } catch (AgentStudioException e) {
                handleException(importResourceResult, e);
            }
        } else {
            if (!Strings.CS.equals(existingAgent.getAgentId(), agent.getAgentId())) {
                agent.setAgentId(existingAgent.getAgentId());
                importResourceResult.setNewId(existingAgent.getAgentId());
            }
            updateAgent(importInfo, agent, importResourceResult);
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

    private void createAgent(ImportInfo importInfo, Agent agent, ImportResourceResult result) {
        // 此id已存在，则更换id
        if (agentMapper.selectById(agent.getAgentId()) != null) {
            String agentId = UUID.randomUUID().toString();
            agent.setAgentId(agentId);
            result.setNewId(agentId);
        }
        agent.setStatus(
            importInfo.getReleaseVersion() == null ? AgentStatus.DRAFT.toString() : AgentStatus.PUBLISHED.toString());
        agent.setDslPath(agentCommonService.getAgentObsPath(agent.getAgentId(), CommonConstant.DSL_STR));
        agent.setIrPath(agentCommonService.getAgentObsPath(agent.getAgentId(), CommonConstant.Workflow.IR));
        agentMapper.insert(agent);
        handleReleaseVersion(agent, importInfo.getReleaseVersion(), result);
        // 标记首次导入：与 WorkflowAdapter/ControllerAdapter 一致，放在操作成功后
        result.setAddTag(true);
    }

    private void handleReleaseVersion(Agent agent, ReleaseVersion releaseVersion, ImportResourceResult result) {
        if (releaseVersion == null) {
            return;
        }
        String dslPath = agentCommonService.getAgentObsPath(agent.getAgentId(), CommonConstant.DSL_STR, releaseVersion.getVersionId());
        String irPath = agentCommonService.getAgentObsPath(agent.getAgentId(), CommonConstant.Workflow.IR, releaseVersion.getVersionId());
        // 创建版本数据
        releaseVersion.setId(UUID.randomUUID().toString());
        releaseVersion.setAppId(agent.getAgentId());
        releaseVersion.setCreatorId(agent.getCreatorId());
        releaseVersion.setCreator(agent.getCreator());
        releaseVersion.setDslPath(dslPath);
        releaseVersion.setIrPath(irPath);
        releaseVersionMapper.insert(releaseVersion);
        result.setVersion(releaseVersion.getVersionId());
    }

    private void updateAgent(ImportInfo importInfo, Agent agent, ImportResourceResult result) {
        if (importInfo.getReleaseVersion() == null) {
            agentMapper.updateAgentByTraceId(importInfo.getTargetProjectId(), importInfo.getTargetWorkspaceId(),
                agent.getTraceId(), agent);
            return;
        }
        ReleaseVersion existVersion = releaseVersionMapper.selectByAppIdAndVersionId(agent.getAgentId(),
            importInfo.getReleaseVersion().getVersionId());
        // 版本已存在，跳过
        if (existVersion != null) {
            return;
        }
        // 处理版本
        handleReleaseVersion(agent, importInfo.getReleaseVersion(), result);
    }
}
