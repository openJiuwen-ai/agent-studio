/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.utils;

import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.Set;

/**
 * 请求线程内的日志敏感值上下文：登记本次请求解析出的敏感值（如加密环境变量明文），
 * 下游（插件适配层、URL 校验等）在打印可能包含该值的日志前调用 {@link #mask(String)} 统一脱敏，
 * 避免明文经日志泄漏。仅在当前线程生效，登记方必须在 finally 中调用 {@link #clear()}，
 * 避免线程复用导致敏感值跨请求残留。
 */
public final class SensitiveLogContext {

    private static final ThreadLocal<Set<String>> SENSITIVE_VALUES = new ThreadLocal<>();

    private SensitiveLogContext() {
    }

    /**
     * 登记当前线程需要脱敏的敏感值；空集合不产生任何效果。
     */
    public static void register(Collection<String> values) {
        if (values == null || values.isEmpty()) {
            return;
        }
        Set<String> current = SENSITIVE_VALUES.get();
        if (current == null) {
            current = new LinkedHashSet<>();
            SENSITIVE_VALUES.set(current);
        }
        for (String value : values) {
            if (value != null && !value.isEmpty()) {
                current.add(value);
            }
        }
    }

    /**
     * 清理当前线程登记的敏感值。请求/调用结束必须调用，避免线程复用导致跨请求泄漏。
     */
    public static void clear() {
        SENSITIVE_VALUES.remove();
    }

    /**
     * 将文本中出现的已登记敏感值替换为固定掩码；未登记敏感值时原样返回。
     */
    public static String mask(String text) {
        Set<String> values = SENSITIVE_VALUES.get();
        if (values == null || values.isEmpty()) {
            return text;
        }
        return SensitiveTextMasker.mask(text, values, false);
    }
}
