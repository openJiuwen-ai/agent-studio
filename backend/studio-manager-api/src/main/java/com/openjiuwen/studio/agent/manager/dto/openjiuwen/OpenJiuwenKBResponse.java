/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto.openjiuwen;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

/**
 * openjiuwen 知识库通用操作响应。
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class OpenJiuwenKBResponse implements Serializable {

    private static final long serialVersionUID = 1L;

    @Schema(description = "操作是否成功", example = "true")
    private Boolean success;

    @Schema(description = "响应消息", example = "操作成功")
    private String message;
}
