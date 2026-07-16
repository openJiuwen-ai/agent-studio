package com.openjiuwen.studio.agent.manager.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

/**
 * 导出模式枚举
 *
 * @author w30009177
 * @since 2025-11-19
 */
@AllArgsConstructor
@Getter
public enum ExportModeEnum {
    STRICT("STRICT", "严格模式"),
    SPACIOUS("SPACIOUS", "宽松模式");

    @Getter
    private final String code;

    @Getter
    private final String desc;

}
