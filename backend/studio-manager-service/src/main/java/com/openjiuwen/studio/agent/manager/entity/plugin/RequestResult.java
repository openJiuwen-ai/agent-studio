/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.entity.plugin;

import lombok.Data;
import okhttp3.Headers;

@Data
public class RequestResult {
    private boolean success;

    private Integer code;

    private String response;

    private Headers headers;

    private String exceptionMessage;
}
