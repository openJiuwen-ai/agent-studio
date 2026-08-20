/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.AvailableModelServicesQo;
import com.openjiuwen.studio.agent.manager.dto.BaseResp;
import com.openjiuwen.studio.agent.manager.dto.MaasServiceRsp;
import com.openjiuwen.studio.agent.manager.dto.ModelInvokeDataListRsp;
import com.openjiuwen.studio.agent.manager.dto.ModelNameResp;
import com.openjiuwen.studio.agent.manager.dto.ModelServiceListQo;
import com.openjiuwen.studio.agent.manager.dto.ModelServiceListRsp;
import com.openjiuwen.studio.agent.manager.dto.ModelServiceReq;
import com.openjiuwen.studio.agent.manager.dto.ModelServiceRsp;
import com.openjiuwen.studio.agent.manager.dto.ModelStatusReq;
import com.openjiuwen.studio.agent.manager.dto.ImportRsp;
import com.openjiuwen.studio.agent.manager.dto.ModelExportReq;
import com.openjiuwen.studio.agent.manager.dto.ModelImportPreviewRsp;
import com.openjiuwen.studio.agent.manager.enums.ModelImportConflictStrategy;
import com.openjiuwen.studio.agent.manager.service.IModelImportExportService;
import com.openjiuwen.studio.agent.manager.service.IModelServiceMgmtService;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;
import com.openjiuwen.studio.agent.common.utils.ResponseModel.TransferResource;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.Resource;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.io.ByteArrayInputStream;

/**
 * ModelServiceMgmt controller
 */
@RestController

public class ModelServiceMgmtApiController implements ModelServiceMgmtApi {
    private static final Logger log = LoggerFactory.getLogger(ModelServiceMgmtApiController.class);

    @Autowired
    private IModelServiceMgmtService modelServiceMgmtService;

    @Autowired
    private IModelImportExportService modelImportExportService;

    @Override
    public ResponseEntity<Object> availableModelServices(String projectId,
        AvailableModelServicesQo availableModelServicesQo) {
        return ResponseModel.success(
            modelServiceMgmtService.availableModelServices(projectId, availableModelServicesQo));
    }

    @Override
    public ResponseEntity<Object> createModelService(String projectId, String workspaceId, Boolean availableCheck,
        ModelServiceReq body) {
        return ResponseModel.success(
            modelServiceMgmtService.createModelService(projectId, workspaceId, availableCheck, body));
    }

    @Override
    public ResponseEntity<Void> deleteModelService(String projectId, String workspaceId, String id) {
        return ResponseModel.success(modelServiceMgmtService.deleteModelService(projectId, workspaceId, id));
    }

    @Override
    public ResponseEntity<ModelNameResp> existsModelName(String projectId, String workspaceId, String modelName) {
        return ResponseModel.success(modelServiceMgmtService.existsModelName(projectId, workspaceId, modelName));
    }

    @Override
    public ResponseEntity<MaasServiceRsp> maasModelServiceList(String projectId) {
        return ResponseModel.success(modelServiceMgmtService.maasModelServiceList(projectId));
    }

    @Override
    public ResponseEntity<ModelServiceRsp> modelServiceDetail(String projectId, String workspaceId, String id) {
        return ResponseModel.success(modelServiceMgmtService.modelServiceDetail(projectId, workspaceId, id));
    }

    @Override
    public ResponseEntity<ModelServiceListRsp> modelServiceList(String projectId,
        ModelServiceListQo modelServiceListQo) {
        return ResponseModel.success(modelServiceMgmtService.modelServiceList(projectId, modelServiceListQo));
    }

    @Override
    public ResponseEntity<Void> offlineModelService(String projectId, String workspaceId, String id) {
        return ResponseModel.success(modelServiceMgmtService.offlineModelService(projectId, workspaceId, id));
    }

    @Override
    public ResponseEntity<Void> onlineModelService(String projectId, String workspaceId, Boolean availableCheck,
        String id) {
        return ResponseModel.success(
            modelServiceMgmtService.onlineModelService(projectId, workspaceId, availableCheck, id));
    }

    @Override
    public ResponseEntity<ModelInvokeDataListRsp> queryModelInvokeData(String projectId, String modelId,
        String workspaceId) {
        return ResponseModel.success(modelServiceMgmtService.queryModelInvokeData(projectId, modelId, workspaceId));
    }

    @Override
    public ResponseEntity<BaseResp> syncModelService(String projectId, String workspaceId, String providerId) {
        return ResponseModel.success(modelServiceMgmtService.syncModelService(projectId, workspaceId, providerId));
    }

    @Override
    public ResponseEntity<Object> updateModelService(String projectId, String workspaceId, Boolean availableCheck,
        String id, ModelServiceReq body) {
        return ResponseModel.success(
            modelServiceMgmtService.updateModelService(projectId, workspaceId, availableCheck, id, body));
    }

    @Override
    public ResponseEntity<Void> updateModelStatus(String projectId, String workspaceId, ModelStatusReq body) {
        return ResponseModel.success(modelServiceMgmtService.updateModelStatus(projectId, workspaceId, body));
    }

    @Override
    public ResponseEntity<Resource> exportModelServices(String projectId, String workspaceId, ModelExportReq body) {
        byte[] jsonl;
        if (body.getProviderId() != null && !body.getProviderId().isEmpty()) {
            // 卡片入口：按供应商导出（供应商+其下全部模型）
            jsonl = modelImportExportService.exportModelsByProvider(projectId, workspaceId, body.getProviderId());
        } else if (body.getModelIds() != null && !body.getModelIds().isEmpty()) {
            // 按模型 id 导出，include_provider 区分供应商+模型 / 只导模型
            jsonl = modelImportExportService.exportModels(projectId, workspaceId, body.getModelIds(),
                body.effectiveIncludeProvider());
        } else {
            throw new AgentStudioException(StudioError.MODEL_IMPORT_FORMAT_INVALID,
                "either model_ids or provider_id is required");
        }
        TransferResource resource = new TransferResource(new ByteArrayInputStream(jsonl));
        resource.setFilename("models.jsonl");
        resource.setContentType("application/x-ndjson");
        resource.setLength((long) jsonl.length);
        return ResponseModel.successDownload(resource);
    }

    @Override
    public ResponseEntity<ModelImportPreviewRsp> previewImportModelServices(String projectId, String workspaceId,
        MultipartFile file, String targetProviderId) {
        return ResponseModel.success(
            modelImportExportService.previewImport(projectId, workspaceId, file, targetProviderId));
    }

    @Override
    public ResponseEntity<ImportRsp> importModelServices(String projectId, String workspaceId, MultipartFile file,
        ModelImportConflictStrategy conflictStrategy, String targetProviderId) {
        return ResponseModel.success(
            modelImportExportService.importModels(projectId, workspaceId, file, conflictStrategy, targetProviderId));
    }
}
