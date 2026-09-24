/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.error;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * COM-04 §4.4: ErrorDescriptor 内部诊断字段的安全访问器。
 * <p>
 * {@link ErrorDescriptor} 的下游 getter 保持 package-private，Manager 包无法直接读取。
 * 本类与 ErrorDescriptor 同包，提供只读安全访问；不得改成可被 Jackson 识别的 public
 * bean getter（避免误序列化）。
 *
 * <p>只返回服务枚举和可信原码，不返回 cause message、body、URL、token 或 headers。
 * HTTP/SSE builder 不依赖本类。{@link ErrorDescriptor#toString()}/{@code equals}/
 * {@code hashCode} 继续排除内部字段。
 *
 * <p>用序列化测试证明两个 {@code downstream_*} 字段不会进入 HTTP JSON、SSE data
 * 或 fallback 响应。
 */
public final class ErrorDescriptorDiagnostics {

    private ErrorDescriptorDiagnostics() {
    }

    /** 安全读取下游服务枚举（内部诊断用）。 */
    public static DownstreamService getDownstreamService(ErrorDescriptor descriptor) {
        return descriptor.getDownstreamServiceInternal();
    }

    /** 安全读取可信下游原码（内部诊断用）；无可信原码返回 {@code null}。 */
    public static String getDownstreamErrorCode(ErrorDescriptor descriptor) {
        return descriptor.getDownstreamErrorCodeInternal();
    }

    /**
     * 提取最终责任边界日志所需的安全结构化字段。
     * <p>只含 {@code downstream_service} 和 {@code downstream_error_code?}，
     * 不含 cause message、body、URL、token 或 headers。
     */
    public static Map<String, Object> toSafeLogFields(ErrorDescriptor descriptor) {
        Map<String, Object> fields = new LinkedHashMap<>();
        DownstreamService service = descriptor.getDownstreamServiceInternal();
        if (service != null) {
            fields.put("downstream_service", service.name());
        }
        String code = descriptor.getDownstreamErrorCodeInternal();
        if (code != null && !code.isBlank()) {
            fields.put("downstream_error_code", code);
        }
        return fields;
    }
}
