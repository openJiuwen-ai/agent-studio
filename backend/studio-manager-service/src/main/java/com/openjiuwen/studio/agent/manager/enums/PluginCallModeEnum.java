/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.enums;

import lombok.Getter;

public enum PluginCallModeEnum {

    API("api", "api类型插件"),

    CUSTOM("custom", "自定义插件");

    @Getter
    private String code;

    @Getter
    private String desc;

    PluginCallModeEnum(String code, String desc) {
        this.code = code;
        this.desc = desc;
    }
}
