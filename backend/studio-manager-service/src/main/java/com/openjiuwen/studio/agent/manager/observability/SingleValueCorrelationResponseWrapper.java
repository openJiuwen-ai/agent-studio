/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpServletResponseWrapper;

import java.util.Locale;

/**
 * SUT-01 CD-013：关联 Header 单值幂等 response wrapper。
 *
 * <p>Servlet 边界保证 {@code X-Request-Id} / {@code TraceID} 在 wire 上单值：把这两个
 * 关联 Header 的 {@code addHeader(name, value)} 改为 {@code setHeader(name, value)}
 * （大小写不敏感）。其他 Header 完全委托，尤其不得压平 {@code Set-Cookie}、{@code Allow}
 * 等合法多值 Header。不生成 ID、不读取 MDC、不改值、不记录日志。
 *
 * <p>双写成因：{@link CorrelationContextFilter} 先 {@code setHeader} 写关联 Header，
 * ControllerAdvice 的 {@code ResponseEntity} 经 Spring 渲染时用 {@code addHeader} 追加
 * 同值 → wire 出现两行。wrapper 在 Servlet 边界把 {@code add} 转 {@code set}，无论内部
 * 多少写点、用 {@code add} 还是 {@code set}，最终 wire 单值（§4.2 设计决策）。
 *
 * <p>{@code setHeader()} 保持 Servlet 原语义（替换），不额外干预；{@code addIntHeader}
 * /{@code addDateHeader} 无关，原样委托。
 */
public class SingleValueCorrelationResponseWrapper extends HttpServletResponseWrapper {

    public SingleValueCorrelationResponseWrapper(HttpServletResponse response) {
        super(response);
    }

    /** 是否为需单值幂等的关联 Header（大小写不敏感）。 */
    private static boolean isCorrelationHeader(String name) {
        if (name == null) {
            return false;
        }
        String lower = name.toLowerCase(Locale.ROOT);
        return lower.equals("x-request-id") || lower.equals("traceid");
    }

    @Override
    public void addHeader(String name, String value) {
        if (isCorrelationHeader(name)) {
            // add→set：替换而非追加，保证 wire 单值
            setHeader(name, value);
        } else {
            super.addHeader(name, value);
        }
    }

    // setHeader / addIntHeader / addDateHeader 保持 Servlet 原语义，无需覆盖
}
