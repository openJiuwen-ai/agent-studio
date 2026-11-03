/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.mapper;

import com.openjiuwen.studio.prompt.engineering.dto.DatasetDto;

import org.apache.ibatis.annotations.Param;
import org.springframework.stereotype.Repository;

import java.util.List;


/**
 * 功能描述
 *
 */
@Repository
public interface DatasetMapper {
    /**
     * 获取数据集列表
     *
     * @param dto
     * @return
     */
    List<DatasetDto> getDatasetRecords(@Param("dto") DatasetDto dto);

    /**
     * 根据ID获取数据集
     *
     * @param projectId
     * @param datasetId
     * @return
     */
    DatasetDto getDatasetById(@Param("projectId") String projectId, @Param("datasetId") String datasetId, @Param("workspaceId") String workspaceId);

    /**
     * 通过名称获取数据集
     *
     * @param projectId
     * @param datasetName
     * @return
     */
    DatasetDto getDatasetByName(@Param("projectId") String projectId, @Param("datasetName") String datasetName, @Param("workspaceId") String workspaceId);

    /**
     * 创建数据集
     *
     * @param req
     * @return
     */
    int createDataset(@Param("dto") DatasetDto req);

    /**
     * 删除数据集
     *
     * @param datasetId
     * @return
     */
    int deleteDataset(@Param("datasetId") String datasetId, @Param("workspaceId") String workspaceId);

    /**
     * 根据id判断数据集是否存在
     * @param id 数据集id
     */
    Boolean isIdExist(@Param("id") String id, @Param("workspaceId") String workspaceId);

    /**
     * 根据projectId查询数据集数目
     *
     * @param projectId projectId
     * @param datasetType 数据集类型
     */
    int queryDatasetCountByProjectId(@Param("projectId") String projectId, @Param("datasetType") String datasetType, @Param("workspaceId") String workspaceId);
}
