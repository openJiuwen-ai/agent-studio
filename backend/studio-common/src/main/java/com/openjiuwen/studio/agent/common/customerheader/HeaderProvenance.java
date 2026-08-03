/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.customerheader;

/**
 * Header 来源枚举 — 标识 header 值的来源，用于合并优先级判断
 *
 * <p>合并规则（确定性）：
 * <ol>
 *   <li>客户捕获值禁生成平台保留 header（黑名单）</li>
 *   <li>平台生成值覆盖外部同名值（REQUEST_RAW 丢弃）</li>
 *   <li>同一可信级别两不同值→拒绝</li>
 * </ol>
 */
public enum HeaderProvenance {
    /** 平台生成的 header（如 X-Auth-Token、X-Execution-Id），优先级最高 */
    PLATFORM_GENERATED,

    /** 已认证平台 principal 中的 header（如平台 userId/token） */
    AUTHENTICATED_PRINCIPAL,

    /** 客户捕获的 header（如 cust-userid、cust-token），来自入站白名单 */
    CUSTOMER_CAPTURED,

    /** 请求原始 header（最低优先级，可被覆盖） */
    REQUEST_RAW
}
