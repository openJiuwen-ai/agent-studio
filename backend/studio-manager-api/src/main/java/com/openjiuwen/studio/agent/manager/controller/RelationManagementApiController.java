/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.ListAppRelationsQo;
import com.openjiuwen.studio.agent.manager.dto.ListDependencyQo;
import com.openjiuwen.studio.agent.manager.dto.ListResourceRelationsQo;
import com.openjiuwen.studio.agent.manager.dto.ListResourcesRelationsQo;
import com.openjiuwen.studio.agent.manager.dto.ListVersionsQo;
import com.openjiuwen.studio.agent.manager.dto.RelationList;
import com.openjiuwen.studio.agent.manager.dto.ResourceDependencyResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ResourceMappingList;
import com.openjiuwen.studio.agent.manager.dto.ResourceVersionResponseBody;
import com.openjiuwen.studio.agent.manager.service.IRelationManagementService;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;

/**
 * RelationManagement controller
 */
@RestController

public class RelationManagementApiController implements RelationManagementApi {
    private static final Logger log = LoggerFactory.getLogger(RelationManagementApiController.class);

    @Autowired
    private IRelationManagementService relationManagementService;

    @Override
    public ResponseEntity<RelationList> listAppRelations(String projectId, String appId,
        ListAppRelationsQo listAppRelationsQo) {
        return ResponseModel.success(relationManagementService.listAppRelations(projectId, appId, listAppRelationsQo));
    }

    @Override
    public ResponseEntity<RelationList> listResourceRelations(String projectId, String resourceId,
        ListResourceRelationsQo listResourceRelationsQo) {
        return ResponseModel.success(
            relationManagementService.listResourceRelations(projectId, resourceId, listResourceRelationsQo));
    }

    @Override
    public ResponseEntity<ResourceMappingList> listResourcesRelations(String projectId,
        ListResourcesRelationsQo listResourcesRelationsQo) {
        return ResponseModel.success(
            relationManagementService.listResourcesRelations(projectId, listResourcesRelationsQo));
    }

    @Override
    public ResponseEntity<ResourceDependencyResponseBody> listDependency(String projectId, String appId,
        String workspaceId, String versionId) {
        ListDependencyQo listDependencyQo = new ListDependencyQo().setWorkspaceId(workspaceId)
            .setVersionId(versionId);
        return ResponseModel.success(relationManagementService.listDependency(projectId, appId, listDependencyQo));
    }

    @Override
    public ResponseEntity<ResourceVersionResponseBody> listVersions(String projectId, String appId, String workspaceId,
        String resourceType) {
        ListVersionsQo listVersionsQo = new ListVersionsQo().setWorkspaceId(workspaceId).setResourceType(resourceType);
        return ResponseModel.success(relationManagementService.listVersions(projectId, appId, listVersionsQo));
    }
}