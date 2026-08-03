/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.customerheader;

/**
 * 异步任务上下文单信封— 一次写入，provenance 不丢
 *
 * <p>单 key {@code agent:runtime:async:context:{taskId}}（替代旧 {@code async:header:{taskId}} 全量 Map）。
 * 字段分区：{@code schemaVersion}（升级兼容，旧/不符 → FAILED 不回退）+ {@code identity}
 * （平台 Token + effective userId）+ {@code execution}（客户 header）。
 *
 * @param schemaVersion schema 版本
 * @param identity       身份快照（平台 Token + effective userId）
 * @param execution      执行快照（客户 header）
 */
public record AsyncTaskContextSnapshot(String schemaVersion, AsyncIdentitySnapshot identity,
                                       AsyncExecutionSnapshot execution) {
}
