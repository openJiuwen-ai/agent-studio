/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.customerheader;

import java.util.Map;

/**
 * 异步执行快照— 客户 header 快照
 *
 * <p>恢复后传 runtime/下游 Target。与 {@link AsyncIdentitySnapshot} 分离对象存储
 * （不塞回同一 Map，否则 provenance 丢失）。
 *
 * @param customerHeaders 客户 header（白名单 cust-*，不含 x-auth-token；key 为规范化小写名）
 */
public record AsyncExecutionSnapshot(Map<String, HeaderValue> customerHeaders) {
}
