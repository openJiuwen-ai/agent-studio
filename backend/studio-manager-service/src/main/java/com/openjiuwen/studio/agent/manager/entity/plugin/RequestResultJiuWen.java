/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.entity.plugin;

import lombok.Data;

import java.util.Map;

@Data
public class RequestResultJiuWen {
    private boolean success;

    private Integer code;

    private String response;

    private Map<String, String> headers;

    private String exceptionMessage;
}
