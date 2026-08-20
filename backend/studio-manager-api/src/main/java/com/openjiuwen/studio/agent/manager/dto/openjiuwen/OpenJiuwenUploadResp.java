/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto.openjiuwen;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

/**
 * 上传文档到 openjiuwen 知识库响应。
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class OpenJiuwenUploadResp implements Serializable {

    private static final long serialVersionUID = 1L;

    private Boolean success;

    @JsonProperty("doc_count")
    private Integer docCount;

    private String message;
}
