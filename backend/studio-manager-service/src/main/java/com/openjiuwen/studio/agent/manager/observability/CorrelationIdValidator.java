/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import java.util.regex.Pattern;

/**
 * Manager 统一关联 ID 合法性规则（DEF-02 §3.1）。
 *
 * <p>候选值必须满足：长度 1 至 64，只允许 {@code [A-Za-z0-9._:-]}，不得包含空白、换行或控制字符。
 * 锚定正则同时保证字符集、长度和不含未列字符——非白名单字符（含所有空白与控制字符）一律不匹配。
 *
 * <p>本类只做纯校验，不区分"来源不存在"与"非法"：调用方先用空值判断来源是否存在，
 * 再对本类返回 {@code false} 的非空候选按非法处理（恢复值非空非法 → {@link ExecutionIdSelector} 返回
 * {@code RESTORE_ILLEGAL}；内部值/入站 Header 非法 → 跳过并继续下一来源）。
 *
 * <p>供 DEF-02 选择器及后续 COM-05 Manager 入口校验复用，不在 Controller/Service/Listener 中复制规则。
 */
public final class CorrelationIdValidator {

    /** 合法字符集：字母、数字、{@code .} {@code _} {@code :} {@code -}。 */
    private static final String CHARSET = "[A-Za-z0-9._:-]";

    /** 锚定正则：整串必须由合法字符组成，长度 1 至 64。 */
    private static final Pattern PATTERN = Pattern.compile("^" + CHARSET + "{1,64}$");

    private CorrelationIdValidator() {
    }

    /**
     * 校验候选值是否为合法关联 ID。
     *
     * @param value 候选值，{@code null} 视为"来源不存在"返回 {@code false}（非"非法"）
     * @return 合法返回 {@code true}；{@code null}、空串或任何不合法值返回 {@code false}
     */
    public static boolean isValid(String value) {
        if (value == null || value.isEmpty()) {
            return false;
        }
        return PATTERN.matcher(value).matches();
    }
}
