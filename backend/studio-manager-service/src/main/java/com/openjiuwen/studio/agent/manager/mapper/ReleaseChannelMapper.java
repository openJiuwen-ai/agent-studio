/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.mapper;

import com.openjiuwen.studio.agent.manager.entity.ReleaseChannel;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 发布通道 数据库操作mapper
 *
 */
@Mapper
public interface ReleaseChannelMapper {
    /**
     * 插入一条发布通道记录到数据库
     *
     * @param releaseChannel releaseChannel
     * @return int
     */
    int insert(ReleaseChannel releaseChannel);

    /**
     * 根据主键Id从数据库查询发布通道
     *
     * @param id id
     * @return version
     */
    ReleaseChannel selectByPrimaryKey(@Param("id") String id);

    /**
     * 根据提供的id、appId、projectId和workspaceId查询并返回对应的ReleaseChannel对象。
     *
     * @param id         要查询的ReleaseChannel的唯一标识符。
     * @param appId      资源的唯一标识符，用于确定ReleaseChannel所属的资源。
     * @param projectId  项目唯一标识符，用于确定ReleaseChannel所属的项目。
     * @param workspaceId 工作空间的唯一标识符，用于确定ReleaseChannel所属的工作空间。
     * @return 返回匹配给定参数的ReleaseChannel对象。
     */
    ReleaseChannel selectByIdAppIdWorkspaceId(@Param("id") String id, @Param("appId") String appId, @Param("projectId") String projectId, @Param("workspaceId") String workspaceId);

    /**
     * 根据appId和通道类型从数据库查询发布版本通道
     *
     * @param appId appId
     * @return channel
     */
    ReleaseChannel selectByAppIdAndType(@Param("appId") String appId, @Param("channelType") String channelType,
        @Param("creatorId") String creatorId);

    /**
     * 根据应用ID、渠道类型、项目ID和工作空间ID查询发布渠道。
     *
     * @param appId 应用的唯一标识符。
     * @param channelType 渠道的类型，例如：App Store, Google Play等。
     * @param projectId 项目的唯一标识符。
     * @param workspaceId 工作空间的唯一标识符。
     * @return 返回匹配的ReleaseChannel对象，如果没有找到则返回null。
     */
    ReleaseChannel selectByAppIdAndTypeAndWorkspaceId(@Param("appId") String appId, @Param("channelType") String channelType,
        @Param("projectId") String projectId, @Param("workspaceId") String workspaceId);

    /**
     * 根据主键或shortCode从数据库查询发布版本通道
     *
     * @param id id
     * @return channel
     */
    ReleaseChannel selectByChannelIdOrShortCode(@Param("projectId") String projectId, @Param("id") String id,
        @Param("shortCode") String shortCode, @Param("channelType") String channelType);

    /**
     * 根据appId从数据库查询发布通道列表
     *
     * @param appId appId
     * @return version list
     */
    List<ReleaseChannel> selectByAppId(@Param("appId") String appId, @Param("workspaceId") String workspaceId);

    /**
     * 根据应用ID、项目ID和工作空间ID查询发布渠道列表。
     *
     * @param appId 应用的唯一标识符。
     * @param projectId 项目的唯一标识符。
     * @param workspaceId 工作空间的唯一标识符。
     * @return 符合条件的发布渠道列表。
     */
    List<ReleaseChannel> selectByAppIdAndWorkspaceId(@Param("appId") String appId, @Param("projectId") String projectId, @Param("workspaceId") String workspaceId);

    /**
     * 根据appId和versionId从数据库查询发布通道列表
     *
     * @param appId appId
     * @return channel list
     */
    List<ReleaseChannel> selectByAppIdAndVersionId(@Param("appId") String appId, @Param("versionId") String versionId);

    /**
     * 根据主键Id从数据库删除对应版本通道
     *
     * @param id id
     * @return int
     */
    int deleteByPrimaryKey(@Param("id") String id, @Param("creatorId") String creatorId);

    /**
     * 根据主键ID和工作区ID删除记录。
     *
     * @param id          要删除的记录的主键ID
     * @param workspaceId 要删除的记录所属的工作区ID
     * @return 删除的记录数量
     */
    int deleteByPrimaryKeyAndWorkspaceId(@Param("id") String id, @Param("projectId") String projectId, @Param("workspaceId") String workspaceId);

    /**
     * 根据appId从数据库删除对应版本通道
     *
     * @param appId appId
     * @return int
     */
    int deleteByAppId(@Param("appId") String appId);

    /**
     * 根据主键更新发布通道的部分非空字段
     *
     * @param releaseChannel releaseChannel
     * @return int
     */
    int updateByPrimaryKeySelective(ReleaseChannel releaseChannel);

    /**
     * 根据appId和channelType搜索发布通道
     *
     * @param appId appId
     * @param channelType channelType
     * @return channel
     */
    ReleaseChannel selectByAppIdAndChannel(@Param("appId") String appId, @Param("channelType") String channelType);

    /**
     * 根据appId和versionId从数据库删除对应版本通道
     *
     * @param appId appId
     * @param versionId versionId
     * @return int
     */
    int deleteByAppIdAndVersionId(@Param("appId") String appId, @Param("versionId") String versionId);

    void updateProjectIdByIds(@Param("opSvcProjectId") String opSvcProjectId, @Param("releaseChannelIds") List<String> releaseChannelIds);
}
