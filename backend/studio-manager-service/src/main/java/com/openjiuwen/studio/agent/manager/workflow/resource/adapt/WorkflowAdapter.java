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
import com.openjiuwen.studio.agent.manager.dto.WorkflowVO;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.enums.AgentStatus;
import com.openjiuwen.studio.agent.manager.enums.ResourceTypeEnum;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.ShareResourceManagerService;
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
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.jetbrains.annotations.NotNull;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeSet;
import java.util.UUID;
import java.util.stream.Collectors;

@Slf4j
@Component("WORKFLOW")
public class WorkflowAdapter extends ResourceAdapter {

    private static final String AGENT_OBS_PATH_TEMPLATE = "%s/%s/%s/%s.json";

    @Value("${front-page.block-nodes}")
    private String blockNodes;

    @Value("${op.svc.project-id}")
    private String opSvcProjectId;

    @Autowired
    private ShareResourceManagerService shareResourceManagerService;

    @Autowired
    private WorkflowMapper workflowMapper;

    @Autowired
    private ReleaseVersionMapper releaseVersionMapper;

    @Autowired
    private I18nUtil i18nUtil;

    @Autowired
    private MgObsService obsService;

    @Override
    public ExportResp parseExport(List<ExportResourceUnit> exportResources) {
        if (CollectionUtils.isEmpty(exportResources)) {
            log.info("workflow resource input is null");
            return null;
        }
        Map<String, List<String>> parentIdMap = getParentIdMap(exportResources);
        List<String> workflowIds = exportResources.stream().map(ExportResourceUnit::getResourceId).toList();
        List<WorkflowEntity> workflowEntities = workflowMapper.selectByWorkflowIds(
            RequestContextUtils.getRequestProjectId(), RequestContextUtils.getRequestWorkspaceId(), workflowIds);
        if (CollectionUtils.isEmpty(workflowEntities)) {
            log.info("workflow resource output is null");
            return null;
        }
        Map<String, WorkflowEntity> workflowIdMap = workflowEntities.stream()
            .collect(Collectors.toMap(WorkflowEntity::getId, p -> p));
        // 构造导出结果
        ExportResp exportResp = new ExportResp();
        List<ExportResult> exportResults = getExportResults(exportResources, workflowEntities);
        exportResp.setExportResults(exportResults);

        List<ReleaseVersion> releaseVersions = getReleaseVersions(exportResults);
        // 构造发布的数据
        List<ExportInfo> exportInfos = new ArrayList<>();
        if (CollectionUtils.isNotEmpty(releaseVersions)) {
            for (ReleaseVersion releaseVersion : releaseVersions) {
                ExportInfo exportInfo = new ExportInfo();
                exportInfo.setResourceId(releaseVersion.getAppId());
                exportInfo.setResourceType(ResourceTypeEnum.WORKFLOW.toString());
                exportInfo.setResourceLevel(2);
                WorkflowVO workflowVO = JSONObject.parseObject(obsService.downloadObsFile(releaseVersion.getDslPath()),
                    WorkflowVO.class);
                exportInfo.setResourceName(workflowVO.getName());
                exportInfo.setDsl(workflowVO);
                exportInfo.setMetadata(workflowIdMap.get(releaseVersion.getAppId()));
                exportInfo.setReleaseVersion(releaseVersion);
                exportInfo.setShareInfo(shareResourceManagerService.exportShareInfo(releaseVersion.getAppId()));
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

        // 构造导出草稿根数据
        List<ExportResourceUnit> latestResources = exportResources.stream()
            .filter(p -> p.getResourceLevel() == 1)
            .toList();
        if (CollectionUtils.isNotEmpty(latestResources)) {
            for (ExportResourceUnit resourceUnit : latestResources) {
                WorkflowEntity latestWorkflow = workflowIdMap.get(resourceUnit.getResourceId());
                // 置空导出的草稿wf的latest
                if (Strings.CS.equals(Constants.LATEST_PUBLISH_VERSION, resourceUnit.getResourceVersion())) {
                    latestWorkflow.setLastVersionId(null);
                    latestWorkflow.setDeployWfVersion(null);
                }
                ExportInfo latestInfo = new ExportInfo();
                String dsl = getDsl(resourceUnit, latestWorkflow.getDslPath(), latestInfo);
                latestInfo.setResourceId(resourceUnit.getResourceId());
                latestInfo.setResourceType(ResourceTypeEnum.WORKFLOW.toString());
                WorkflowVO workflowVO = JSONObject.parseObject(obsService.downloadObsFile(dsl), WorkflowVO.class);
                latestInfo.setResourceName(workflowIdMap.get(resourceUnit.getResourceId()).getName());
                latestInfo.setDsl(workflowVO);
                latestInfo.setMetadata(latestWorkflow);
                latestInfo.setResourceLevel(1);
                latestInfo.setL1Mappings(resourceUnit.getL1Mappings());
                latestInfo.setShareInfo(shareResourceManagerService.exportShareInfo(resourceUnit.getResourceId()));
                latestInfo.setLevel2Resources(resourceUnit.getLevel2Resources());
                exportInfos.add(latestInfo);
            }
        }
        exportResp.setExportInfos(exportInfos);
        return exportResp;
    }


    @NotNull
    private List<ExportResult> getExportResults(List<ExportResourceUnit> exportResources,
        List<WorkflowEntity> workflowEntities) {
        List<String> validWfIds = workflowEntities.stream().map(WorkflowEntity::getId).toList();
        List<ExportResult> exportResults = new ArrayList<>();
        for (ExportResourceUnit exportResourceUnit : exportResources) {
            ExportResult result = new ExportResult();
            result.setResourceId(exportResourceUnit.getResourceId());
            result.setResourceLevel(exportResourceUnit.getResourceLevel());
            result.setResourceName(exportResourceUnit.getResourceName());
            result.setResourceType(exportResourceUnit.getResourceType());
            result.setResourceVersion(exportResourceUnit.getResourceVersion());
            result.setStatus(ImportExportStatusEnum.SUCCESS);
            if (!validWfIds.contains(exportResourceUnit.getResourceId())) {
                result.setReason(
                    i18nUtil.getMessage(StudioError.EXPORT_RESOURCE_NOT_EXISTS, ResourceTypeEnum.WORKFLOW.toString()));
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
        WorkflowEntity workflow = JsonUtils.objectToClassType(importInfo.getMetadata(), WorkflowEntity.class);
        importCheckResult.setDescription(workflow.getDescription());
        WorkflowEntity workflowEntity = getWorkflowByTraceId(importInfo.getTargetProjectId(),
            importInfo.getTargetWorkspaceId(), workflow.getTraceId());
        importCheckResult.setStatus(workflowEntity != null);
        importCheckResult.setImportDesc(getWorkflowImportDesc(workflowEntity, workflow.getLastVersionId()));
    }

    private void checkMetadata(ImportInfo importInfo) {
        if (importInfo.getMetadata() == null || importInfo.getDsl() == null) {
            throw new AgentStudioException(StudioError.FILE_LACKS_SOURCE_DATA);
        }
    }

    private WorkflowEntity getWorkflowByTraceId(String projectId, String workspaceId, String traceId) {
        List<WorkflowEntity> workflowEntities = workflowMapper.selectByTraceId(projectId, workspaceId, traceId);
        if (CollectionUtils.isEmpty(workflowEntities)) {
            return null;
        }
        return workflowEntities.get(0);
    }

    /**
     * 判断当前空间下资源导入状态
     * @param workflow
     * @param versionId
     * @return
     */
    private ImportDescEnum getWorkflowImportDesc(WorkflowEntity workflow, String versionId) {
        // 如果为空则需新增资源
        if (workflow == null) {
            return ImportDescEnum.NEW_RESOURCE;
        }
        // 草稿
        if (StringUtils.isEmpty(versionId)) {
            return ImportDescEnum.UPDATE_RESOURCE;
        }
        // 如果traceId一致,版本不一致则需新增版本
        if (Strings.CS.equals(versionId, workflow.getLastVersionId())) {
            return ImportDescEnum.RESOURCE_EXISTS;
        }
        return ImportDescEnum.NEW_RESOURCE_VERSION;
    }

    @Override
    public void parseImport(ImportResourceResult importResourceResult, ImportInfo importInfo) {
        checkMetadata(importInfo);
        WorkflowEntity workflow = JsonUtils.objectToClassType(importInfo.getMetadata(), WorkflowEntity.class);
        // 初始化返回结果
        setImportResultDesc(importResourceResult, workflow.getLastVersionId(), workflow.getDescription());
        // 校验是否有隐藏节点，包含隐藏节点的工作流不允许导入
        if (!validateBlockNodes(importInfo, importResourceResult)) {
            return;
        }
        try {
            handleWorkflow(importInfo, workflow, importResourceResult);
        } catch (Exception e) {
            log.error("import workflow error, workflowId: {}, workflowName: {}", workflow.getId(), workflow.getName(),
                e);
            throw new AgentStudioException(e.getLocalizedMessage());
        }
    }

    private boolean validateBlockNodes(ImportInfo importInfo, ImportResourceResult importResourceResult) {
        WorkflowVO dsl = JsonUtils.objectToClassType(importInfo.getDsl(), WorkflowVO.class);
        // 校验导入工作流是否包含隐藏节点
        Set<String> blockedNodeTypes = new HashSet<>(Arrays.asList(StringUtils.split(blockNodes, ",")));
        if (dsl.getNodes().stream().anyMatch(node -> blockedNodeTypes.contains(node.getType()))) {
            log.error("workflow validate failed because contains block nodes");
            importResourceResult.setStatus(ImportExportStatusEnum.FAILED.getCode());
            importResourceResult.setErrorMsg(i18nUtil.getMessage(StudioError.WORKFLOW_BLOCK_NODE_EXIST));
            importResourceResult.setSuggestion(i18nUtil.getSuggestion(StudioError.WORKFLOW_BLOCK_NODE_EXIST));
            return false;
        }
        return true;
    }

    private void handleWorkflow(ImportInfo importInfo, WorkflowEntity workflow, ImportResourceResult result) {
        updateMetadata(importInfo, workflow);
        WorkflowEntity existingWorkflow = getWorkflowByTraceId(importInfo.getTargetProjectId(),
            importInfo.getTargetWorkspaceId(), workflow.getTraceId());
        if (existingWorkflow == null) {
            setWorkflowName(importInfo.getTargetProjectId(), importInfo.getTargetWorkspaceId(), workflow);
            result.setNewName(workflow.getName());
            // 若当前空间资源不存在，且该资源id已存在，则更换id
            if (workflowMapper.countWorkflowIdInDb(workflow.getId()) > 0) {
                workflow.setId(UUID.randomUUID().toString());
                result.setNewId(workflow.getId());
            }
            insertWorkflow(workflow, importInfo.getReleaseVersion(), result);
        } else {
            if (!Strings.CS.equals(existingWorkflow.getId(), workflow.getId())) {
                workflow.setId(existingWorkflow.getId());
                result.setNewId(existingWorkflow.getId());
            }
            updateWorkflow(workflow, importInfo.getReleaseVersion(), existingWorkflow.getLastVersionId(), result);
        }
    }

    private void setWorkflowName(String projectId, String workspaceId, WorkflowEntity workflowEntity) {
        String name = workflowEntity.getName();
        List<WorkflowEntity> workflowByWorkspaceId = workflowMapper.getAvailableWorkflowEntityByWorkspaceId(projectId,
                workspaceId);
        if (CollectionUtils.isEmpty(workflowByWorkspaceId)) {
            return;
        }
        Set<String> currentNameSet = workflowByWorkspaceId.stream()
                .map(WorkflowEntity::getName)
                .filter(Objects::nonNull)
                .collect(Collectors.toCollection(() -> new TreeSet<>(String.CASE_INSENSITIVE_ORDER)));

        List<WorkflowEntity> sameNameList = workflowByWorkspaceId.stream()
                .filter(v -> Strings.CS.equals(v.getName(), name))
                .collect(Collectors.toList());

        if (CollectionUtils.isEmpty(sameNameList)) {
            return;
        }
        // 用户在当前环境中已存在该资源，且name未改变，不会冲突
        if (sameNameList.stream().filter(v -> Strings.CS.equals(v.getTraceId(), workflowEntity.getTraceId())).count()
                > 0) {
            return;
        }
        // 设置唯一资源名称
        workflowEntity.setName(getFormatName(name, currentNameSet));
    }

    private void updateMetadata(ImportInfo importInfo, WorkflowEntity workflow) {
        workflow.setProjectId(importInfo.getTargetProjectId());
        workflow.setWorkspaceId(importInfo.getTargetWorkspaceId());
        workflow.setDomainId(importInfo.getTargetDomainId());
        workflow.setCreatedBy(getUserName(importInfo));
        workflow.setCreatorId(importInfo.getCreatorId());
        workflow.setCreatedAt(new Date().getTime());
        workflow.setUpdatedBy(getUserName(importInfo));
        workflow.setUpdaterId(importInfo.getCreatorId());
        workflow.setUpdatedAt(new Date().getTime());
        workflow.setPublishedAt(null);
        workflow.setDeployWfVersion(null);
        workflow.setLastVersionId(null);
        workflow.setDeleted(0);
        workflow.setTestStatus(null);

    }

    private String getUserName(ImportInfo importInfo) {
        if (Strings.CS.equals(opSvcProjectId, importInfo.getTargetProjectId())) {
            return CommonConstant.DEFAULT_USERNAME;
        } else {
            return importInfo.getCreator();
        }
    }

    private void insertWorkflow(WorkflowEntity metadata, ReleaseVersion releaseVersion, ImportResourceResult result) {
        updatePath(metadata);
        result.setAddTag(true);
        metadata.setStatus(releaseVersion == null ? AgentStatus.DRAFT.toString() : AgentStatus.PUBLISHED.toString());
        workflowMapper.createWorkflowEntity(metadata);

        // 创建版本数据
        handleReleaseVersion(metadata, releaseVersion, metadata.getLastVersionId(), result);
    }

    private void updateWorkflow(WorkflowEntity metadata, ReleaseVersion releaseVersion, String lastVersionId,
        ImportResourceResult result) {
        // 草稿态不需要发版本
        if (!Strings.CS.equals(CommonConstant.WORKFLOW_PUBLISHED, metadata.getStatus()) || releaseVersion == null) {
            updatePath(metadata);
            workflowMapper.updateWorkflowEntityByTraceId(metadata.getProjectId(), metadata.getTraceId(),
                metadata.getWorkspaceId(), metadata);
            return;
        }
        ReleaseVersion existVersion = releaseVersionMapper.selectByAppIdAndVersionId(metadata.getId(),
            releaseVersion.getVersionId());
        // 版本已存在，跳过
        if (existVersion != null) {
            return;
        }
        // 处理版本
        handleReleaseVersion(metadata, releaseVersion, lastVersionId, result);
    }

    public void updatePath(WorkflowEntity metadata) {
        String dslPath = String.format(AGENT_OBS_PATH_TEMPLATE, CommonConstant.WORKFLOW, CommonConstant.Workflow.FLOW,
            metadata.getId(), metadata.getId());
        String irPath = String.format(AGENT_OBS_PATH_TEMPLATE, CommonConstant.WORKFLOW, CommonConstant.Workflow.IR,
            metadata.getId(), metadata.getId());
        metadata.setDslPath(dslPath);
        metadata.setIrPath(irPath);
    }

    private void handleReleaseVersion(WorkflowEntity metadata, ReleaseVersion releaseVersion, String lastVersionId,
        ImportResourceResult result) {
        if (releaseVersion == null) {
            return;
        }
        String releaseDslPath = String.format(AGENT_OBS_PATH_TEMPLATE, CommonConstant.WORKFLOW,
            CommonConstant.Workflow.FLOW, metadata.getId(),
            metadata.getId() + Constants.UNDERLINE_STR + releaseVersion.getVersionId());
        String releaseIrPath = String.format(AGENT_OBS_PATH_TEMPLATE, CommonConstant.WORKFLOW,
            CommonConstant.Workflow.IR, metadata.getId(),
            metadata.getId() + Constants.UNDERLINE_STR + releaseVersion.getVersionId());
        // 创建版本数据
        releaseVersion.setId(UUID.randomUUID().toString());
        releaseVersion.setAppId(metadata.getId());
        releaseVersion.setDslPath(releaseDslPath);
        releaseVersion.setIrPath(releaseIrPath);
        releaseVersion.setCreatorId(metadata.getCreatorId());
        releaseVersion.setCreator(metadata.getCreatedBy());
        releaseVersionMapper.insert(releaseVersion);
        result.setVersion(releaseVersion.getVersionId());

        // 刷新工作流更新时间
        WorkflowEntity updateWorkflow = new WorkflowEntity();
        updateWorkflow.setUpdaterId(metadata.getUpdaterId());
        updateWorkflow.setUpdatedAt(metadata.getUpdatedAt());
        String versionId = releaseVersion.getVersionId();
        String newLastVersionId;
        if (versionId == null) {
            newLastVersionId = lastVersionId;
        } else if (lastVersionId == null) {
            newLastVersionId = versionId;
        } else {
            newLastVersionId = versionId.compareTo(lastVersionId) > 0 ? versionId : lastVersionId;
        }
        updateWorkflow.setLastVersionId(newLastVersionId);
        workflowMapper.updateWorkflowEntityByTraceId(metadata.getProjectId(), metadata.getTraceId(),
            metadata.getWorkspaceId(), updateWorkflow);
    }

}
