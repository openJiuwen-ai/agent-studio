/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.enums;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public enum ParamExtractionType {
    START,
    LLM,
    EXTENSION_BEFORE_ENTRY,
    CYCLE_BEGIN,
    DOMAIN_OBJECTS,
    EXTENSION_BEFORE_JUDGE_QUIT,
    EXTENSION_AFTER_EXTRACTION,
    END_EXCEPTION,
    END;

    private static final List<String> PARAM_EXTRACT_TYPES;

    static {
        List<String> types = new ArrayList<>();
        for (ParamExtractionType type : ParamExtractionType.values()) {
            types.add(type.name().toLowerCase(Locale.ROOT));
        }
        PARAM_EXTRACT_TYPES = types;
    }

    public static List<String> obtainParamExtractTypes() {
        return PARAM_EXTRACT_TYPES;
    }
}
