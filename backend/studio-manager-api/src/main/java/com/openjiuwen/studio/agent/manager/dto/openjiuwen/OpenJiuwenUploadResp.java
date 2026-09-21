/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto.openjiuwen;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.List;

/**
 * 上传文档到 openjiuwen 知识库响应。
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class OpenJiuwenUploadResp implements Serializable {

    private static final long serialVersionUID = 1L;

    @Schema(description = "上传是否成功", example = "true")
    private Boolean success;

    @JsonProperty("doc_count")
    @Schema(description = "文档数量", example = "3")
    private Integer docCount;

    @JsonProperty("doc_ids")
    @Schema(description = "文档ID列表", example = "[\"doc-001\",\"doc-002\"]")
    private List<String> docIds;

    @Schema(description = "响应消息", example = "上传成功")
    private String message;
}
