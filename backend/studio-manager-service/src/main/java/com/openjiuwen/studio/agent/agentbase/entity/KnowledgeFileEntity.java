/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.agentbase.entity;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 知识库文件元数据实体
 *
 * @since 2026-08-12
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class KnowledgeFileEntity {

    private String fileId;

    private String kbId;

    private String projectId;

    private String fileName;

    private String fileType;

    private Long fileSize;

    private String fileStatus;

    private String fileTags;

    private String docIds;

    private String obsPath;

    private Long createTime;

    private Long updateTime;
}
