/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.runtime.service.md.adapter.req;

import org.springframework.stereotype.Component;

@Component("openApiRequestAdapterRun")
public class OpenApiRequestAdapter extends AbstractRequestAdapter {
    @Override
    public String getName() {
        return "openai";
    }
}