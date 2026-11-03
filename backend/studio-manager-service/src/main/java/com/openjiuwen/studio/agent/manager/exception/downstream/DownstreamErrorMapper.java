/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.downstream;

import com.openjiuwen.studio.agent.common.error.DownstreamService;
import com.openjiuwen.studio.agent.common.error.ErrorDefinition;
import com.openjiuwen.studio.agent.common.error.ErrorDescriptor;

/**
 * COM-04 §4.3: 唯一下游映射入口。
 * <p>
 * 唯一职责：{@code DownstreamFailure + request_id -> ErrorDescriptor}。Mapper 调用后，
 * 异常处理器、service、HTTP/SSE builder 不得再次选码。
 *
 * <p>映射顺序冻结：
 * <ol>
 *   <li>以 {@code (service, downstreamErrorCode)} 精确查询显式映射表；</li>
 *   <li>命中且对应 Manager 定义满足约束时，选择该 Manager 定义；</li>
 *   <li>未命中、无原码、未知码、响应损坏或 transport failure，
 *       选择 {@code ManagerErrorCatalog.downstreamDependencyFailed()}（02001131/502）；</li>
 *   <li>构造 descriptor 时保留原始 {@code cause}，写入 {@code downstreamService}；
 *       有可信原码时同时写入 {@code downstreamErrorCode}；</li>
 *   <li>{@code httpStatus} 只来自选中的 Manager {@code ErrorDefinition}，
 *       绝不来自 {@code downstreamHttpStatus}。</li>
 * </ol>
 */
public final class DownstreamErrorMapper {

    private final DownstreamErrorMappingCatalog catalog;

    public DownstreamErrorMapper(DownstreamErrorMappingCatalog catalog) {
        this.catalog = catalog;
    }

    /**
     * 把下游事实映射为 Manager {@link ErrorDescriptor}。每次失败只调用一次。
     *
     * @param failure   下游事实（由 parser 产出）
     * @param requestId 当前请求 ID（caller 显式传入，不在 mapper 生成）
     */
    public ErrorDescriptor map(DownstreamFailure failure, String requestId) {
        DownstreamService service = failure.getService();
        String trustedCode = failure.hasTrustedErrorCode()
            ? failure.getDownstreamErrorCode() : null;

        // 1. 显式 (service, code) 映射 → Manager-owned 定义（初始为空，命中即用）
        ErrorDefinition chosen = null;
        if (trustedCode != null) {
            chosen = catalog.lookupExplicitMapping(service, trustedCode).orElse(null);
        }
        // 2. 未命中/无原码/未知码/transport failure → 默认 02001131/502
        if (chosen == null) {
            chosen = catalog.defaultDownstreamFailure();
        }

        // 3. 构造 descriptor：cause + downstreamService + (可信时) downstreamErrorCode
        //    httpStatus 只来自 chosen Manager ErrorDefinition，绝不来自 downstreamHttpStatus
        return new ErrorDescriptor(
            chosen.getErrorCode(), chosen.getHttpStatus(),
            chosen.getMessageKey(), chosen.getReasonKey(), chosen.getSuggestionKey(),
            requestId, null,
            service,              // 总存在
            trustedCode,          // 可信原码或 null（service-without-code 合法）
            failure.getCause()    // 原始 cause，仅内部日志
        );
    }
}
