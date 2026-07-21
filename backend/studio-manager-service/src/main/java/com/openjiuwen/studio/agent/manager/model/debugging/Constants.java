/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.model.debugging;

import lombok.AccessLevel;
import lombok.NoArgsConstructor;

@NoArgsConstructor(access = AccessLevel.PRIVATE)
public final class Constants {
    public static final String CHAIN_INVOKE_TYPE = "chain";

    public static final String LLM_INVOKE_TYPE = "llm";

    public static final String PLUGIN_INVOKE_TYPE = "plugin";

    public static final String KNOWLEDGE_INVOKE_TYPE = "knowledge";

    public static final String MCP_INVOKE_TYPE = "mcp";

    public static final String COMPOSITE = "composite";

    public static final String PARAM_EXTRACTION = "ParamExtraction";
}
