/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.agentbase.mapper;

import com.openjiuwen.studio.agent.agentbase.entity.KnowledgeFileEntity;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 知识库文件元数据 Mapper
 *
 * @since 2026-08-12
 */
@Mapper
public interface KnowledgeFileMapper {

    /**
     * 插入文件记录
     */
    int insertFile(KnowledgeFileEntity entity);

    /**
     * 根据文件ID删除
     */
    int deleteByFileId(@Param("fileId") String fileId);

    /**
     * 根据知识库ID删除所有文件记录
     */
    int deleteByKbId(@Param("kbId") String kbId);

    /**
     * 根据文件ID查询单条记录
     */
    KnowledgeFileEntity selectByFileId(@Param("fileId") String fileId);

    /**
     * 分页查询知识库文件列表
     */
    List<KnowledgeFileEntity> selectByKbId(@Param("kbId") String kbId,
        @Param("projectId") String projectId,
        @Param("fileName") String fileName,
        @Param("fileType") String fileType,
        @Param("fileStatus") String fileStatus,
        @Param("offset") int offset,
        @Param("limit") int limit);

    /**
     * 查询知识库文件总数
     */
    int countByKbId(@Param("kbId") String kbId,
        @Param("projectId") String projectId,
        @Param("fileName") String fileName,
        @Param("fileType") String fileType,
        @Param("fileStatus") String fileStatus);

    /**
     * 更新文件状态
     */
    int updateFileStatus(@Param("fileId") String fileId,
        @Param("fileStatus") String fileStatus,
        @Param("docIds") String docIds,
        @Param("updateTime") long updateTime);
}
