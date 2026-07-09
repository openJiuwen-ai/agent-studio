/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.workflow.resource.adapt;

import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.enums.ImportDescEnum;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMapper;
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
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

/**
 *
 * 导入导出资源转换
 */
@Slf4j
@Component
public abstract class ResourceAdapter {

    /**
     * 名称冲突时变更模板
     */
    private static final String NAME_FORMAT = "%s_%s";

    @Autowired
    private I18nUtil i18nUtil;

    @Autowired
    private ReleaseVersionMapper releaseVersionMapper;

    @Autowired
    private WorkspaceMapper workspaceMapper;

    public ExportResp parseExport(List<ExportResourceUnit> exportResources) {
        return new ExportResp();
    }

    public void parseImport(ImportResourceResult importResourceResult, ImportInfo importInfo) {

    }

    public void checkBeforeImport(ImportCheckResult importCheckResult, ImportInfo importInfo) {

    }

    public List<ReleaseVersion> getReleaseVersions(List<ExportResult> exportResults) {
        // 查询导出资源版本dsl
        List<ExportResult> successExportResults = exportResults.stream()
            .filter(p -> p.getStatus() == ImportExportStatusEnum.SUCCESS && p.getResourceLevel() == 2)
            .toList();
        if (CollectionUtils.isEmpty(successExportResults)) {
            log.info("all export workflow resource failed");
            return null;
        }
        List<ReleaseVersion> releaseVersions = releaseVersionMapper.queryByWfVersions(
            convert2ReleaseParam(successExportResults));
        return releaseVersions;
    }

    public String getDsl(ExportResourceUnit resourceUnit, String dsl, ExportInfo latestInfo) {
        if (!Strings.CS.equals(resourceUnit.getResourceVersion(), Constants.LATEST_PUBLISH_VERSION)) {
            ReleaseVersion releaseVersion = releaseVersionMapper.selectByAppIdAndVersionId(resourceUnit.getResourceId(),
                resourceUnit.getResourceVersion());
            latestInfo.setReleaseVersion(releaseVersion);
            return releaseVersion.getDslPath();
        }
        return dsl;
    }

    private List<ReleaseVersion> convert2ReleaseParam(List<ExportResult> successExportResults) {
        return successExportResults.stream().map(p -> {
            ReleaseVersion releaseVersion = new ReleaseVersion();
            releaseVersion.setAppId(p.getResourceId());
            releaseVersion.setVersionId(p.getResourceVersion());
            return releaseVersion;
        }).toList();
    }

    public static Map<String, List<String>> getParentIdMap(List<ExportResourceUnit> exportResources) {
        return exportResources.stream()
            .collect(Collectors.groupingBy(ExportResourceUnit::getResourceId,
                Collectors.mapping(ExportResourceUnit::getParentResourceId, Collectors.toList())));
    }

    public void setImportResultDesc(ImportResourceResult result, String version, String description) {
        result.setVersion(version);
        result.setDescription(description);
    }

    /**
     * 判断当前空间下无版本资源导入状态
     * @param obj
     * @return
     */
    public ImportDescEnum getImportDescNoVersion(Object obj) {
        return obj == null ? ImportDescEnum.NEW_RESOURCE : ImportDescEnum.UPDATE_RESOURCE;
    }

    /**
     * 判断当前空间下无需更新资源导入状态
     * @param obj
     * @return
     */
    public ImportDescEnum getImportDescNoUpdate(Object obj) {
        return obj == null ? ImportDescEnum.NEW_RESOURCE : ImportDescEnum.RESOURCE_EXISTS;
    }

    /**
     * 判断当前空间下特殊资源导入状态(skill)
     * @param obj
     * @return
     */
    public ImportDescEnum getImportDescSpecialResource(Object obj) {
        return obj == null ? ImportDescEnum.RESOURCE_NOT_MATCH : ImportDescEnum.RESOURCE_MATCH;
    }

    /**
     * 导入异常封装
     * @param result
     * @param e
     */
    public void handleException(ImportResourceResult result, AgentStudioException e) {
        result.setStatus(ImportExportStatusEnum.FAILED.getCode());
        result.setErrorMsg(i18nUtil.getMessage(e.getErrorCode()));
        result.setSuggestion(i18nUtil.getSuggestion(e.getErrorCode()));
    }

    /**
     * 预制资源不允许导入
     * @param result
     */
    public void handlePlatformResource(ImportResourceResult result) {
        result.setStatus(ImportExportStatusEnum.SUCCESS.getCode());
        result.setErrorMsg(i18nUtil.getMessage(StudioError.NO_IMPORT_PLATFORM));
        result.setSuggestion(i18nUtil.getSuggestion(StudioError.NO_IMPORT_PLATFORM));
    }

    /**
     * 同名时预处理截断name
     *
     * @param name 原始名称
     * @return 截断后的名称
     */
    public String subName(String name, int length) {
        if (name.length() > length) {
            name = name.substring(0, length);
        }
        return name;
    }

    public String getFormatName(String serverName, Set<String> names) {
        int index = 1;
        serverName = subName(serverName, CommonConstant.NAME_MAX_LEN - 2);
        while (names.contains(String.format(NAME_FORMAT, serverName, index))) {
            index++;
        }
        return String.format(NAME_FORMAT, serverName, index);
    }

    public boolean isExistWorkspace(String projectId, String workspaceId) {
        return workspaceMapper.getWorkspaceByWorkspaceId(projectId, workspaceId) != null;
    }
}
