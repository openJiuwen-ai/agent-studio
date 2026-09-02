/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;

import io.swagger.v3.oas.annotations.media.Schema;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class KnowledgeBaseFileInfo {

    @Schema(description = "知识库ID", example = "kb-001")
    private String knowledgeBaseId;

    @Schema(description = "文件ID", example = "file-001")
    private String fileId;

    @Schema(description = "文件类型", example = "pdf")
    private String type;

    @Schema(description = "文件名称", example = "产品手册.pdf")
    private String fileName;

    @Schema(description = "知识库类型", example = "internal")
    private String knowledgeBaseType;

    @Schema(description = "节点名称", example = "node-1")
    private String nodeName;
}
