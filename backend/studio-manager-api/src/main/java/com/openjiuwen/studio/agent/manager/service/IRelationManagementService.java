/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.manager.dto.ListAppRelationsQo;
import com.openjiuwen.studio.agent.manager.dto.ListDependencyQo;
import com.openjiuwen.studio.agent.manager.dto.ListResourceRelationsQo;
import com.openjiuwen.studio.agent.manager.dto.ListResourcesRelationsQo;
import com.openjiuwen.studio.agent.manager.dto.ListVersionsQo;
import com.openjiuwen.studio.agent.manager.dto.RelationList;
import com.openjiuwen.studio.agent.manager.dto.ResourceDependencyResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ResourceMappingList;
import com.openjiuwen.studio.agent.manager.dto.ResourceVersionResponseBody;
import com.openjiuwen.studio.agent.manager.dto.VersionReferenceListRsp;

/**
 * RelationManagement service
 */

public interface IRelationManagementService {

    /**
     * listAppRelations
     *
     * @param projectId projectId
     * @param appId appId
     * @param listAppRelationsQo listAppRelationsQo
     */
    RelationList listAppRelations(String projectId, String appId, ListAppRelationsQo listAppRelationsQo);

    /**
     * listResourceRelations
     *
     * @param projectId projectId
     * @param resourceId resourceId
     * @param listResourceRelationsQo listResourceRelationsQo
     */
    RelationList listResourceRelations(String projectId, String resourceId,
        ListResourceRelationsQo listResourceRelationsQo);

    /**
     * listResourcesRelations
     *
     * @param projectId projectId
     * @param listResourcesRelationsQo listResourcesRelationsQo
     */
    ResourceMappingList listResourcesRelations(String projectId, ListResourcesRelationsQo listResourcesRelationsQo);

    /**
     * listDependency
     *
     * @param projectId projectId
     * @param resourceId resourceId
     * @param listDependencyQo listDependencyQo
     */
    ResourceDependencyResponseBody listDependency(String projectId, String resourceId,
        ListDependencyQo listDependencyQo);

    /**
     * listVersions
     *
     * @param projectId projectId
     * @param resourceId resourceId
     * @param listVersionsQo listVersionsQo
     */
    ResourceVersionResponseBody listVersions(String projectId, String resourceId, ListVersionsQo listVersionsQo);

    /**
     * listVersionReferences 查询资源各发布版本的引用数量
     * 资源归属校验由调用方完成（agents路径getAgent、workflows路径checkWorkflowExist）
     *
     * @param projectId projectId
     * @param resourceId 资源ID（agentId或workflowId）
     * @param workspaceId 工作空间ID，用于过滤引用方workspace
     * @param versionId 版本ID，传null返回所有版本的引用数量
     */
    VersionReferenceListRsp listVersionReferences(String projectId, String resourceId, String workspaceId,
        String versionId);
}