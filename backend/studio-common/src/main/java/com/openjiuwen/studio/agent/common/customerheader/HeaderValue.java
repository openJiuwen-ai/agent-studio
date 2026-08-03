/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.customerheader;

/**
 * 不可变 Header 值记录 — 携带来源信息，用于投影引擎合并判断
 *
 * <p>字段与 Python 侧 {@code customer_header.types.HeaderValue} 保持一致（Schema 一致性）。
 *
 * @param normalizedName 规范化后的 header 名（小写）
 * @param value          header 值
 * @param provenance     值来源
 */
public record HeaderValue(String normalizedName, String value, HeaderProvenance provenance) {

    /**
     * 创建客户捕获的 HeaderValue
     *
     * @param name   header 名（会被规范化为小写）
     * @param value  header 值
     * @return 客户捕获来源的 HeaderValue
     */
    public static HeaderValue customerCaptured(String name, String value) {
        return new HeaderValue(name.toLowerCase(), value, HeaderProvenance.CUSTOMER_CAPTURED);
    }

    /**
     * 创建平台生成的 HeaderValue
     *
     * @param name   header 名
     * @param value  header 值
     * @return 平台生成来源的 HeaderValue
     */
    public static HeaderValue platformGenerated(String name, String value) {
        return new HeaderValue(name.toLowerCase(), value, HeaderProvenance.PLATFORM_GENERATED);
    }
}
