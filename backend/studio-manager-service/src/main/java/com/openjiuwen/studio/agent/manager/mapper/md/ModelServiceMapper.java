/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.mapper.md;

import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceBase;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceCondition;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceData;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceProviderDetail;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.Collection;
import java.util.List;

@Mapper
public interface ModelServiceMapper {
    List<String> filterProviderIdsByCondition(ModelServiceCondition condition);

    List<ModelServiceBase> queryByName(@Param("projectId") String projectId, @Param("workspaceId") String workspaceId,
        @Param("name") String serviceName, @Param("providerId") String providerId);

    List<ModelServiceBase> queryByModelName(@Param("projectId") String projectId, @Param("workspaceId") String workspaceId,
        @Param("name") String modelName, @Param("providerId") String providerId);

    int countByModelName(@Param("projectId") String projectId, @Param("workspaceId") String workspaceId,
        @Param("name") String modelName);

    List<ModelServiceBase> queryByNames(@Param("projectId") String projectId, @Param("workspaceId") String workspaceId,
        @Param("serviceNames") List<String> serviceNames);

    int insert(ModelServiceBase service);

    void batchInsert(@Param("modelServices") List<ModelServiceBase> modelServices);

    ModelServiceBase queryModelServiceDetail(@Param("id") String id);

    List<ModelServiceData> queryByCondition(@Param("condition") ModelServiceCondition condition,
        @Param("limit") int limit, @Param("offset") int offset);

    int countByCondition(@Param("condition") ModelServiceCondition condition);

    void changePublishStatus(@Param("id") String id, @Param("status") String status, @Param("user") String user,
        @Param("time") long time);

    int updateModelService(ModelServiceBase service);

    List<ModelServiceData> queryAvailableServices(@Param("condition") ModelServiceCondition condition);

    List<ModelServiceData> queryPublicAvailableServices(@Param("condition") ModelServiceCondition condition);

    void deleteById(@Param("id") String id);

    List<ModelServiceBase> queryAllPlatformModels(@Param("providerId")String providerId);

    ModelServiceBase queryById(@Param("id") String id);

    /**
     * 根据模型ids列表，查询所有模型信息
     *
     */
    List<ModelServiceBase> queryAllModelByIds(@Param("modelIds") Collection<String> ids);

    /**
     * 根据模型ID列表查询模型
     *
     * @param modelIds        模型ID
     * @param userProjectId   用户项目ID
     * @param userWorkspaceId 用户空间ID
     * @return 模型信息
     */

    List<ModelServiceData> queryByIds(@Param("modelIds") Collection<String> modelIds,
        @Param("userProjectId") String userProjectId, @Param("userWorkspaceId") String userWorkspaceId);
    List<ModelServiceData> selectByIds(@Param("modelIds") Collection<String> modelIds);

    List<ModelServiceBase> getModelNamesAndProviderIdsByIds(List<String> ids);

    List<ModelServiceProviderDetail> getLogosAndProviderNamesByProviderIds(Collection<String> providerIds);

    int countByProviderId(String providerId);

    List<ModelServiceBase> queryByIdentityId(@Param("projectId") String projectId,
        @Param("workspaceId") String workspaceId, @Param("identityId") String identityId);

    List<ModelServiceBase> queryByProviders(@Param("projectId") String projectId,
        @Param("workspaceId") String workspaceId, @Param("providerId") String providerId);

    List<ModelServiceBase> queryByProvidersExternal(@Param("projectId") String projectId,
        @Param("workspaceId") String workspaceId, @Param("providerId") String providerId);

    List<ModelServiceBase> queryByProvidersInternal(@Param("projectId") String projectId,
        @Param("workspaceId") String workspaceId, @Param("providerId") String providerId);

    List<ModelServiceBase> queryNotSyncModels();

    void updateSyncStatus(@Param("id") String id);

    void updateModelStatus(@Param("id") String id, @Param("status") String status, @Param("projectId") String projectId,
        @Param("workspaceId") String workspaceId);

    void updateModelProvider(@Param("id") String id, @Param("providerId") String providerId,
        @Param("authMetadataId") String authMetadataId);

    /**
     * 数据备份
     */
    void insertBackup(ModelServiceBase service);

    List<ModelServiceBase> queryBackupByUpdateTime(@Param("lastUpdatedDate") Long lastUpdatedDate);

    void deleteBackupByIds(@Param("ids") List<String> ids);

    void batchDeleteByIds(@Param("ids") List<String> ids);

    int updateModelTags(@Param("id") String id, @Param("modelTags") String modelTags);

    void batchInsertBackup(@Param("modelServices") List<ModelServiceBase> modelServices);
}

