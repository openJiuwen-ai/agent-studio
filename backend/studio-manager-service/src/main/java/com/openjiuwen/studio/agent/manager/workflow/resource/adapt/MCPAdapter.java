/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.workflow.resource.adapt;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.dto.McpServiceDetailInfoDto;
import com.openjiuwen.studio.agent.manager.entity.McpServiceEntity;
import com.openjiuwen.studio.agent.manager.enums.EnumOrgType;
import com.openjiuwen.studio.agent.manager.enums.ResourceTypeEnum;
import com.openjiuwen.studio.agent.manager.enums.ToolType;
import com.openjiuwen.studio.agent.manager.mapper.McpServiceMapper;
import com.openjiuwen.studio.agent.manager.service.mcp.IMcpInnerService;
import com.openjiuwen.studio.agent.manager.service.mcp.McpServiceManager;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ExportInfo;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ExportResourceUnit;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ExportResp;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ExportResult;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ImportCheckResult;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ImportExportStatusEnum;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ImportInfo;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ImportResourceResult;
import com.openjiuwen.studio.common.service.service.EncryptionAdapter;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.jetbrains.annotations.NotNull;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.TreeSet;
import java.util.UUID;
import java.util.stream.Collectors;

@Slf4j
@Component("MCP")
public class MCPAdapter extends ResourceAdapter {

    @Autowired
    private IMcpInnerService mcpInnerService;

    @Autowired
    private McpServiceManager mcpServiceManager;

    @Autowired
    private McpServiceMapper mcpServiceMapper;

    @Autowired
    private I18nUtil i18nUtil;

    @Autowired
    private EncryptionAdapter encryptionAdapter;

    @Override
    public ExportResp parseExport(List<ExportResourceUnit> exportResources) {
        if (CollectionUtils.isEmpty(exportResources)) {
            log.info("mcp resource input is null");
            return null;
        }
        Map<String, List<String>> parentIdMap = getParentIdMap(exportResources);
        List<String> mcpInputIds = exportResources.stream().map(ExportResourceUnit::getResourceId).toList();

        List<McpServiceEntity> serviceMcpList = mcpInnerService.getMcpByIds(RequestContextUtils.getRequestWorkspaceId(),
            mcpInputIds);
        if (CollectionUtils.isEmpty(serviceMcpList)) {
            log.info("mcp resource output is null");
            return null;
        }
        // 构造导出结果
        ExportResp exportResp = new ExportResp();
        exportResp.setExportResults(getExportResults(exportResources, serviceMcpList));
        // 构造导出数据
        List<ExportInfo> exportInfos = new ArrayList<>();
        for (McpServiceEntity serviceMcpEntity : serviceMcpList) {
            ExportInfo exportInfo = new ExportInfo();
            serviceMcpEntity.setServerConfig(encryptionAdapter.decrypt(serviceMcpEntity.getServerConfig()));
            // 不导出mcp鉴权信息
            if (Objects.nonNull(serviceMcpEntity.getAuthInfo())) {
                serviceMcpEntity.getAuthInfo().setCustomOauth(null);
            }
            exportInfo.setResourceId(serviceMcpEntity.getId());
            exportInfo.setMetadata(serviceMcpEntity);
            exportInfo.setResourceName(serviceMcpEntity.getName());
            exportInfo.setResourceType(ResourceTypeEnum.MCP.toString());
            exportInfo.setParents(parentIdMap.get(serviceMcpEntity.getId()));
            exportInfos.add(exportInfo);
        }
        exportResp.setExportInfos(exportInfos);
        return exportResp;
    }

    @NotNull
    private List<ExportResult> getExportResults(List<ExportResourceUnit> exportResources,
        List<McpServiceEntity> serviceMcpList) {
        List<String> validModelIds = serviceMcpList.stream().map(McpServiceEntity::getId).toList();
        List<ExportResult> exportResults = new ArrayList<>();
        for (ExportResourceUnit exportResourceUnit : exportResources) {
            ExportResult result = new ExportResult();
            result.setResourceId(exportResourceUnit.getResourceId());
            result.setResourceName(exportResourceUnit.getResourceName());
            result.setResourceType(exportResourceUnit.getResourceType());
            result.setStatus(ImportExportStatusEnum.SUCCESS);
            if (!validModelIds.contains(exportResourceUnit.getResourceId())) {
                result.setReason(
                    i18nUtil.getMessage(StudioError.EXPORT_RESOURCE_NOT_EXISTS, ResourceTypeEnum.MCP.toString()));
                result.setStatus(ImportExportStatusEnum.FAILED);
            }
            exportResults.add(result);
        }
        return exportResults;
    }

    @Override
    public void checkBeforeImport(ImportCheckResult importCheckResult, ImportInfo importInfo) {
        checkMetadata(importInfo);
        McpServiceEntity mcp = JsonUtils.objectToClassType(importInfo.getMetadata(), McpServiceEntity.class);
        importCheckResult.setDescription(mcp.getDescription());
        // 预制资源不可导入
        if (ToolType.INNER.type.equals(mcp.getNodeType())) {
            importCheckResult.setProhibited(true);
            importCheckResult.setStatus(true);
        }
        McpServiceEntity mcpEntity = getMcpByTraceId(importInfo.getTargetProjectId(), importInfo.getTargetWorkspaceId(),
            mcp.getTraceId());
        importCheckResult.setStatus(mcpEntity != null);
        importCheckResult.setImportDesc(getImportDescNoVersion(mcpEntity));
    }

    private void checkMetadata(ImportInfo importInfo) {
        if (importInfo.getMetadata() == null) {
            throw new AgentStudioException(StudioError.FILE_LACKS_SOURCE_DATA);
        }
    }

    private McpServiceEntity getMcpByTraceId(String projectId, String workspaceId, String traceId) {
        return mcpServiceMapper.selectByTraceIdAndWorkspaceId(projectId, workspaceId, traceId);
    }

    @Override
    public void parseImport(ImportResourceResult importResourceResult, ImportInfo importInfo) {
        checkMetadata(importInfo);
        McpServiceEntity mcp = JsonUtils.objectToClassType(importInfo.getMetadata(), McpServiceEntity.class);
        setImportResultDesc(importResourceResult, null, mcp.getDescription());
        // 预置资源不允许导入
        if (ToolType.INNER.type.equals(mcp.getNodeType())) {
            handlePlatformResource(importResourceResult);
        } else {
            // 处理自定义资源
            handleWidgetsMcp(importInfo, mcp, importResourceResult);
        }
    }

    private void handleWidgetsMcp(ImportInfo importInfo, McpServiceEntity mcp, ImportResourceResult result) {
        McpServiceEntity existingMcp = getMcpByTraceId(importInfo.getTargetProjectId(),
            importInfo.getTargetWorkspaceId(), mcp.getTraceId());
        updateMetadata(importInfo, mcp);
        if (existingMcp == null) {
            // 若当前空间资源不存在，且该资源id已存在，则更换id
            if (mcpServiceMapper.selectByIds(Arrays.asList(mcp.getId())).size() > 0) {
                mcp.setId(UUID.randomUUID().toString());
                String functionName = StringUtils.join("agentBuilder-mcp-" + mcp.getId());
                mcp.setFunctionApplicationName(functionName);
                result.setNewId(mcp.getId());
            }
            if (mcp.getAuthInfo() != null && mcp.getAuthInfo().getScope() != null) {
                mcp.setAuthInfo(null);
                result.setConfigDisplay(true);
            }
            setMcpName(mcp);
            result.setNewName(mcp.getName());
            mcpServiceMapper.insert(mcp);
        } else {
            if (!Strings.CS.equals(existingMcp.getId(), mcp.getId())) {
                mcp.setId(existingMcp.getId());
                result.setNewId(existingMcp.getId());
            }
            mcpServiceMapper.updateById(existingMcp.getId(), mcp);
        }
        // 导入后若URL含环境变量占位符，使用目标空间环境变量刷新工具列表
        mcpServiceManager.refreshToolsAfterImport(mcp);
    }

    private void updateMetadata(ImportInfo importInfo, McpServiceEntity mcp) {
        mcp.setProjectId(importInfo.getTargetProjectId());
        mcp.setWorkspaceId(importInfo.getTargetWorkspaceId());
        mcp.setCreatedByUserId(importInfo.getCreatorId());
        mcp.setCreatedDate(new Timestamp(new Date().getTime()));
        mcp.setLastUpdatedByUserId(importInfo.getCreatorId());
        mcp.setLastUpdatedDate(new Timestamp(new Date().getTime()));
        mcp.setDomainId(importInfo.getTargetDomainId());
        mcp.setTenantId(RequestContextUtils.getRequestUserDomainId());
        mcp.setServerConfig(encryptionAdapter.encrypt(mcp.getServerConfig(), mcp.getDomainId()));

    }

    /**
     * 保障mcp名称唯一
     * @param mcp
     */
    private void setMcpName(McpServiceEntity mcp) {
        String serverName = Optional.ofNullable(mcp.getName()).orElse(mcp.getNameEn());
        List<McpServiceEntity> mcpServersByWorkspaceId = mcpServiceMapper.selectByIdsAndWorkspace(null,
            mcp.getProjectId(), mcp.getWorkspaceId());
        if (CollectionUtils.isEmpty(mcpServersByWorkspaceId)) {
            return;
        }
        Set<String> currentNameSet = mcpServersByWorkspaceId.stream()
            .map(McpServiceEntity::getName)
            .filter(Objects::nonNull)
            .collect(Collectors.toCollection(() -> new TreeSet<>(String.CASE_INSENSITIVE_ORDER)));

        List<McpServiceEntity> sameNameList = mcpServersByWorkspaceId.stream()
            .filter(v -> Strings.CS.equals(v.getName(), serverName))
            .collect(Collectors.toList());

        if (CollectionUtils.isEmpty(sameNameList)) {
            return;
        }
        // 用户在当前环境中已存在该MCP服务，且name未改变，不会冲突
        if (sameNameList.stream().filter(v -> Strings.CS.equals(v.getTraceId(), mcp.getTraceId())).count() == 1) {
            return;
        }

        // 设置唯一MCP服务名称
        mcp.setName(getFormatName(serverName, currentNameSet));
    }

}
