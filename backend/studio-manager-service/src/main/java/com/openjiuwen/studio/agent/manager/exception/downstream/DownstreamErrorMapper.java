/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.downstream;

import com.openjiuwen.studio.agent.common.error.DownstreamService;
import com.openjiuwen.studio.agent.common.error.ErrorDefinition;
import com.openjiuwen.studio.agent.common.error.ErrorDescriptor;
import com.openjiuwen.studio.agent.common.error.PassthroughText;

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
 *   <li>RUNTIME canonical 码形（纵深校验，非仅 parser 信任）且无显式映射时，
 *       按 runtime 原码透传（HTTP 阶段用下游实际状态，SSE 阶段 500——修复
 *       2026-10-27 版本要求 downstreamHttpStatus 非空导致 SSE 错误帧永远进不了
 *       本分支的洞），并附帧内受管三段文案供构建器 i18n 缺失时回退；</li>
 *   <li>未命中、无原码、未知码、响应损坏或 transport failure，
 *       选择 {@code ManagerErrorCatalog.downstreamDependencyFailed()}（02001131/502）；</li>
 *   <li>构造 descriptor 时保留原始 {@code cause}，写入 {@code downstreamService}；
 *       有可信原码时同时写入 {@code downstreamErrorCode}；</li>
 *   <li>{@code httpStatus} 只来自选中的 Manager {@code ErrorDefinition}
 *       （RUNTIME 透传路径为其原码透传状态），绝不来自未经选择的 {@code downstreamHttpStatus}。</li>
 * </ol>
 */
public final class DownstreamErrorMapper {

    /** RUNTIME 透传路径在 SSE 阶段（无下游 HTTP 状态）使用的 ErrorDefinition 状态。 */
    static final int RUNTIME_SSE_PASSTHROUGH_STATUS = 500;

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
        PassthroughText passthrough = null;
        if (trustedCode != null) {
            chosen = catalog.lookupExplicitMapping(service, trustedCode).orElse(null);
        }
        // 1b. RUNTIME 透传（2026-11-02 修订）：可信 Runtime canonical 码形且无显式
        //     映射时按原码透传。码形校验为纵深防御——直接构造的 DownstreamFailure
        //     也不能把 Builder canonical 码（13 头）或任意格式推入透传路径。
        //     HTTP 阶段沿用下游实际状态（2026-10-27 行为）；SSE 阶段（状态为空，
        //     2026-10-27 版本在此处漏过全部 SSE 错误帧）使用 500。Manager i18n
        //     已覆盖的码（8 位 0 头族）由构建器优先解析 i18n，行为不变；i18n 缺失
        //     的码（引擎 6 位族等）由构建器回退到帧内受管三段文案。
        if (chosen == null && trustedCode != null
                && service == DownstreamService.RUNTIME
                && catalog.isRuntimeCanonicalShape(trustedCode)) {
            int passthroughStatus = passthroughHttpStatus(failure.getDownstreamHttpStatus());
            chosen = catalog.resolveByCode(trustedCode, passthroughStatus).orElse(null);
            String message = failure.getDownstreamMessage();
            if (message != null && !message.isBlank()) {
                // 受管文案完整性兜底：reason/suggestion 缺失时用 message 填充——
                // 构建器对 i18n 缺失的码按字段回退，部分缺失若不补齐会在
                // fail-closed 路径抛出，前端将收不到任何错误帧（比兜底码更糟）。
                // 门槛用非空白（与 PassthroughText 构造不变量一致，评审修订
                // 2026-11-03）：message 为空白时视为无可信文案，passthrough 保持
                // null 走 i18n/族文案回退，绝不在 descriptor 构造阶段抛异常。
                String reason = failure.getDownstreamReason() != null
                    && !failure.getDownstreamReason().isBlank()
                    ? failure.getDownstreamReason() : message;
                String suggestion = failure.getDownstreamSuggestion() != null
                    && !failure.getDownstreamSuggestion().isBlank()
                    ? failure.getDownstreamSuggestion() : message;
                passthrough = new PassthroughText(message, reason, suggestion);
            }
        }
        // 2. 未命中/无原码/未知码/transport failure → 默认 02001131/502
        if (chosen == null) {
            chosen = catalog.defaultDownstreamFailure();
        }

        // 3. 构造 descriptor：cause + downstreamService + (可信时) downstreamErrorCode
        //    httpStatus 只来自 chosen Manager ErrorDefinition，绝不来自 downstreamHttpStatus
        //    统一族格式（2026-11-02 二期）：组件标签由本 mapper 唯一判定（runtime/builder/
        //    external——RUNTIME 访问 OBS/DB 是其内部依赖，不细分到具体依赖，用户裁定）；
        //    manager 自身直接访问 OBS/SQL 的码族标签由 DependencyComponentLabels 判定
        return new ErrorDescriptor(
            chosen.getErrorCode(), chosen.getHttpStatus(),
            chosen.getMessageKey(), chosen.getReasonKey(), chosen.getSuggestionKey(),
            safeRequestId(requestId), null,
            service,              // 总存在
            trustedCode,          // 可信原码或 null（service-without-code 合法）
            failure.getCause(),   // 原始 cause，仅内部日志
            passthrough,          // 受管三段文案，构建器 i18n 缺失时回退；可空
            resolveComponentLabel(service, trustedCode, failure.getDownstreamMessage())
        );
    }

    /**
     * 透传 ErrorDefinition 状态（评审修订 2026-11-03）：
     * null（SSE 阶段，无下游 HTTP 状态）→ 500；4xx/5xx 原样透传；
     * 非错误区间（1xx/2xx/3xx——直接构造的 DownstreamFailure 或异常网关形态）
     * → 502。ErrorDefinition 只接受 4xx-5xx，原样透传越界状态会在 descriptor
     * 构造阶段抛 IllegalArgumentException，打穿错误处理路径自身。
     */
    private static int passthroughHttpStatus(Integer downstreamStatus) {
        if (downstreamStatus == null) {
            return RUNTIME_SSE_PASSTHROUGH_STATUS;
        }
        if (downstreamStatus >= 400 && downstreamStatus <= 599) {
            return downstreamStatus;
        }
        return 502;
    }

    /**
     * requestId 非空守卫（评审修订 2026-11-03）：调用方 MDC 未写入时回退
     * unknown——ErrorDescriptor 要求非空，null 直传会抛 IllegalArgumentException，
     * 把本应返回的下游失败错误体升级为未知异常。
     */
    private static String safeRequestId(String requestId) {
        return requestId != null && !requestId.isBlank() ? requestId : "unknown";
    }

    /**
     * 统一族格式的组件标签（2026-11-02 二期）：识别"哪个下游组件失败"。
     * <p>
     * 用户裁定：RUNTIME 访问 OBS/数据库是 RUNTIME 自己的内部依赖，**不细分**
     * ——下游视角的组件只有服务本身：
     * <ul>
     *   <li>BUILDER → {@code builder}；</li>
     *   <li>RUNTIME（含其 OBS/DB 内部依赖失败）→ {@code runtime}；</li>
     *   <li>其余服务 → 枚举名小写（如 {@code external}），无服务时 null。</li>
     * </ul>
     * manager 自身直接访问 OBS/SQL 的失败标签见
     * {@code contract.DependencyComponentLabels}（码族精确匹配 obs/mysql）。
     */
    private static String resolveComponentLabel(DownstreamService service, String trustedCode,
                                                String managedMessage) {
        if (service == null) {
            return null;
        }
        if (service == DownstreamService.BUILDER) {
            return "builder";
        }
        if (service == DownstreamService.RUNTIME) {
            return "runtime";
        }
        return service.name().toLowerCase(java.util.Locale.ROOT);
    }
}
