/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

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

/**
 * ModelServiceMgmt service
 */

public interface IModelServiceMgmtService {

    /**
     * availableModelServices
     *
     * @param projectId projectId
     * @param availableModelServicesQo availableModelServicesQo
     */
    Object availableModelServices(String projectId, AvailableModelServicesQo availableModelServicesQo);

    /**
     * createModelService
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param availableCheck availableCheck
     * @param body body
     */
    String createModelService(String projectId, String workspaceId, Boolean availableCheck, ModelServiceReq body);

    /**
     * deleteModelService
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param id id
     */
    Void deleteModelService(String projectId, String workspaceId, String id);

    /**
     * existsModelName
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param modelName modelName
     */
    ModelNameResp existsModelName(String projectId, String workspaceId, String modelName);

    /**
     * maasModelServiceList
     *
     * @param projectId projectId
     */
    MaasServiceRsp maasModelServiceList(String projectId);

    /**
     * modelServiceDetail
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param id id
     */
    ModelServiceRsp modelServiceDetail(String projectId, String workspaceId, String id);

    /**
     * modelServiceList
     *
     * @param projectId projectId
     * @param modelServiceListQo modelServiceListQo
     */
    ModelServiceListRsp modelServiceList(String projectId, ModelServiceListQo modelServiceListQo);

    /**
     * offlineModelService
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param id id
     */
    Void offlineModelService(String projectId, String workspaceId, String id);

    /**
     * onlineModelService
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param availableCheck availableCheck
     * @param id id
     */
    Void onlineModelService(String projectId, String workspaceId, Boolean availableCheck, String id);

    /**
     * queryModelInvokeData
     *
     * @param projectId projectId
     * @param modelId modelId
     * @param workspaceId workspaceId
     */
    ModelInvokeDataListRsp queryModelInvokeData(String projectId, String modelId, String workspaceId);

    /**
     * syncModelService
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param providerId providerId
     */
    BaseResp syncModelService(String projectId, String workspaceId, String providerId);

    /**
     * updateModelService
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param availableCheck availableCheck
     * @param id id
     * @param body body
     */
    Void updateModelService(String projectId, String workspaceId, Boolean availableCheck, String id,
        ModelServiceReq body);

    /**
     * updateModelStatus
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param body body
     */
    Void updateModelStatus(String projectId, String workspaceId, ModelStatusReq body);
}