/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.workflow.resource.adapt;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.entity.ModelExportEntity;
import com.openjiuwen.studio.agent.manager.entity.ProviderExportMetadata;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceBase;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceData;
import com.openjiuwen.studio.agent.manager.enums.ResourceTypeEnum;
import com.openjiuwen.studio.agent.manager.mapper.md.ModelServiceMapper;
import com.openjiuwen.studio.agent.manager.service.md.ModelServiceMgmtService;
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
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Collectors;

@Component("MODEL")
@Slf4j
public class ModelAdapter extends ResourceAdapter {

    @Autowired
    private ModelServiceMgmtService modelServiceMgmtService;

    @Autowired
    private ModelServiceMapper modelServiceMapper;

    @Autowired
    private I18nUtil i18nUtil;


    @Override
    public ExportResp parseExport(List<ExportResourceUnit> exportResources) {
        if (CollectionUtils.isEmpty(exportResources)) {
            log.info("model resource input is null");
            return null;
        }
        Map<String, List<String>> parentIdMap = getParentIdMap(exportResources);
        ExportResp exportResp = new ExportResp();
        List<String> modelIds = exportResources.stream().map(ExportResourceUnit::getResourceId).toList();
        List<ModelExportEntity> modelExportEntities = modelServiceMgmtService.buildModelExportEntity(
            RequestContextUtils.getRequestProjectId(), RequestContextUtils.getRequestWorkspaceId(), modelIds);
        List<ModelServiceBase> modelServiceBases = buildModelProviderInfos(parentIdMap, exportResp, modelExportEntities);
        // 构造导出结果
        exportResp.getExportResults().addAll(getExportModelResults(exportResources, modelServiceBases));
        return exportResp;
    }

    public static List<ModelServiceBase> buildModelProviderInfos(Map<String, List<String>> parentIdMap,
        ExportResp exportResp, List<ModelExportEntity> modelExportEntities) {
        modelExportEntities = CollectionUtils.isEmpty(modelExportEntities) ? new ArrayList<>() : modelExportEntities;
        List<ModelServiceBase> modelServiceBases = modelExportEntities.stream()
            .map(ModelExportEntity::getModelMetadata)
            .filter(CollectionUtils::isNotEmpty)
            .flatMap(List::stream)
            .collect(Collectors.toList());

        // 构造导出数据
        List<ProviderExportMetadata> providerMetadatas = modelExportEntities.stream()
            .map(ModelExportEntity::getProviderMetadata)
            .toList();
        List<ExportInfo> exportInfos = new ArrayList<>();
        List<ExportResult> exportResults = new ArrayList<>();
        for (ModelServiceBase modelServiceBase : modelServiceBases) {
            ExportInfo exportInfo = new ExportInfo();
            exportInfo.setMetadata(modelServiceBase);
            exportInfo.setResourceId(modelServiceBase.getId());
            exportInfo.setResourceType(ResourceTypeEnum.MODEL.toString());
            exportInfo.setResourceName(modelServiceBase.getModelName());
            exportInfo.setParents(parentIdMap.get(modelServiceBase.getId()));
            exportInfos.add(exportInfo);
        }
        for (ProviderExportMetadata providerExportMetadata : providerMetadatas) {
            ExportInfo exportInfo = new ExportInfo();
            exportInfo.setMetadata(providerExportMetadata);
            exportInfo.setResourceId(providerExportMetadata.getModelServiceProviderMetadata().getId());
            exportInfo.setResourceType(ResourceTypeEnum.PROVIDER.toString());
            exportInfo.setResourceName(providerExportMetadata.getModelServiceProviderMetadata().getProviderName());
            exportInfos.add(exportInfo);
            exportResults.add(buildModelProviderResult(providerExportMetadata));
        }
        exportResp.setExportInfos(exportInfos);
        exportResp.setExportResults(exportResults);
        return modelServiceBases;
    }

    private static ExportResult buildModelProviderResult(ProviderExportMetadata providerExportMetadata) {
        ExportResult result = new ExportResult();
        result.setResourceId(providerExportMetadata.getModelServiceProviderMetadata().getId());
        result.setResourceName(providerExportMetadata.getModelServiceProviderMetadata().getProviderName());
        result.setResourceType(ResourceTypeEnum.PROVIDER.toString());
        result.setStatus(ImportExportStatusEnum.SUCCESS);
        result.setResourceDesc(providerExportMetadata.getModelServiceProviderMetadata().getDescription());
        return result;
    }

    /**
     * 模型资源导出校验
     * @param exportResources 待导出资源
     * @param modelServiceBases 有效资源
     * @return
     */
    public List<ExportResult> getExportModelResults(List<ExportResourceUnit> exportResources,
        List<ModelServiceBase> modelServiceBases) {
        List<String> validModelIds = modelServiceBases.stream().map(ModelServiceBase::getId).toList();
        Map<String, ModelServiceBase> serviceBaseMap = modelServiceBases.stream()
            .collect(Collectors.toMap(ModelServiceBase::getId, p -> p));
        List<ExportResult> exportResults = new ArrayList<>();
        for (ExportResourceUnit exportResourceUnit : exportResources) {
            ExportResult result = new ExportResult();
            result.setResourceId(exportResourceUnit.getResourceId());
            result.setResourceName(exportResourceUnit.getResourceName());
            result.setResourceType(exportResourceUnit.getResourceType());
            result.setStatus(ImportExportStatusEnum.SUCCESS);
            if (!validModelIds.contains(exportResourceUnit.getResourceId())) {
                result.setReason(i18nUtil.getMessage(StudioError.EXPORT_RESOURCE_NOT_EXISTS, ResourceTypeEnum.MODEL.toString()));
                result.setStatus(ImportExportStatusEnum.FAILED);
            }
            result.setResourceDesc(Optional.ofNullable(serviceBaseMap.get(exportResourceUnit.getResourceId()))
                .map(p -> p.getModelDescription()).orElse(null));
            exportResults.add(result);
        }
        return exportResults;
    }

    @Override
    public void checkBeforeImport(ImportCheckResult importCheckResult, ImportInfo importInfo) {
        checkMetadata(importInfo);
        ModelServiceData model = JsonUtils.objectToClassType(importInfo.getMetadata(), ModelServiceData.class);
        importCheckResult.setDescription(model.getModelDescription());

        // 预制资源不可导入
        if (isPlatformModel(model.getProjectId(), model.getWorkspaceId())) {
            importCheckResult.setProhibited(true);
            importCheckResult.setStatus(true);
        }
        ModelServiceBase modelBase = getModelByTraceId(importInfo.getTargetProjectId(),
            importInfo.getTargetWorkspaceId(), model.getIdentityId());
        importCheckResult.setStatus(modelBase != null);
        importCheckResult.setImportDesc(getImportDescNoUpdate(modelBase));
    }

    private void checkMetadata(ImportInfo importInfo) {
        if (importInfo.getMetadata() == null) {
            throw new AgentStudioException(StudioError.FILE_LACKS_SOURCE_DATA);
        }
    }

    private boolean isPlatformModel(String projectId, String workspaceId) {
        return Strings.CS.equals(CommonConstant.SYSTEM_DEFAULT, projectId) && Strings.CS.equals(
            CommonConstant.SYSTEM_DEFAULT, workspaceId);
    }

    private ModelServiceBase getModelByTraceId(String projectId, String workspaceId,
        String traceId) {
        List<ModelServiceBase> modelBaseList = modelServiceMapper.queryByIdentityId(projectId, workspaceId, traceId);
        return modelBaseList.stream().findFirst().orElse(null);
    }

    @Override
    public void parseImport(ImportResourceResult importResourceResult, ImportInfo importInfo) {
        checkMetadata(importInfo);
        ModelServiceData model = JsonUtils.objectToClassType(importInfo.getMetadata(), ModelServiceData.class);
        // 初始化返回结果
        setImportResultDesc(importResourceResult, null, model.getModelDescription());

        // 预置资源不允许导入
        if (isPlatformModel(model.getProjectId(), model.getWorkspaceId())) {
            handlePlatformResource(importResourceResult);
        } else {
            // 处理自定义资源
            handleWidgetsModel(importInfo, model, importResourceResult);
        }
    }
    private void handleWidgetsModel(ImportInfo importInfo, ModelServiceData model, ImportResourceResult result) {
        updateMetadata(importInfo, model);
        ModelServiceBase modelBase = getModelByTraceId(importInfo.getTargetProjectId(),
            importInfo.getTargetWorkspaceId(), model.getIdentityId());
        // 若当前空间资源不存在，则更换id并创建（防止其他空间下id已存在）
        if (modelBase == null) {
            try {
                // id已存在,需要更换id
                boolean globalExists = modelServiceMapper.queryModelServiceDetail(model.getId()) != null;
                if (globalExists) {
                    String newId = UUID.randomUUID().toString();
                    model.setId(newId);
                    result.setNewId(newId);
                }
                modelServiceMgmtService.importModels(importInfo.getTargetProjectId(), importInfo.getTargetWorkspaceId(),
                    Arrays.asList(model), false);
            } catch (AgentStudioException e) {
                handleException(result, e);
            } catch (Exception e) {
                log.warn("Failed to import model. modelId:{}", model.getId(), e);
            }
        } else {
            if (!Strings.CS.equals(model.getId(), modelBase.getId())) {
                model.setId(modelBase.getId());
                result.setNewId(model.getId());
            }
        }
    }

    private void updateMetadata(ImportInfo importInfo, ModelServiceData model) {
        model.setProjectId(importInfo.getTargetProjectId());
        model.setWorkspaceId(importInfo.getTargetWorkspaceId());
        model.setDomainId(importInfo.getTargetDomainId());
        model.setCreatedByUser(importInfo.getCreator());
        model.setCreatedDate(new Date().getTime());
        model.setLastUpdatedByUser(importInfo.getCreator());
        model.setLastUpdatedDate(new Date().getTime());
    }

}
