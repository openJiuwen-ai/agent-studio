/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.entity;

import com.openjiuwen.studio.prompt.engineering.utils.II18nHandler;

public interface FormConvert<S, T> {
    default T convert(S s) {
        return null;
    }

    default T convert(S s, II18nHandler i18nMap) {
        return null;
    }

}
