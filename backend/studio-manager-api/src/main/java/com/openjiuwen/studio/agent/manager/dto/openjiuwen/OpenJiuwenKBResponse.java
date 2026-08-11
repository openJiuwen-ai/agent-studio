/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto.openjiuwen;

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

    private Boolean success;

    private String message;
}
