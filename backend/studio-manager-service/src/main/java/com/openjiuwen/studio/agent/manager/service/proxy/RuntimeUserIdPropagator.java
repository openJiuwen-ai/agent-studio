/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.proxy;

import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;

import org.apache.commons.lang3.StringUtils;
import org.springframework.http.HttpHeaders;

import java.util.function.Consumer;

/**
 * 试运行调用 Runtime 时，把登录用户统一认证号写入出站参数。
 *
 * <p>替代模型鉴权里写死的 {@code cust-userid}，支撑模型网关按用户维度统计 token。
 * 对应 GitHub #1728 / GitCode #1761。
 *
 * <p>出站方式：
 * <ul>
 *   <li>流式 OkHttp：写入 {@link HttpHeaders}，由 stream 调用直接转发</li>
 *   <li>非流式 Feign：调用方把 {@link #custUserIdHeaderValue()} 作为
 *       {@code @RequestHeader(cust-userid)} 显式传入（不依赖
 *       CustomerHeaderFeignInterceptor / ThreadLocal；默认
 *       {@code customer-header.enabled=false} 时拦截器不会透传）</li>
 *   <li>工作流请求体：可选写入 {@code body.userId}</li>
 * </ul>
 */
public final class RuntimeUserIdPropagator {

    private RuntimeUserIdPropagator() {
    }

    /**
     * 当前登录用户统一认证号；空白时返回 {@code null}（Feign required=false 时省略 header）。
     */
    public static String custUserIdHeaderValue() {
        String userId = RequestContextUtils.getRequestUserId();
        return StringUtils.isBlank(userId) ? null : userId;
    }

    /**
     * 将当前登录用户写入出站 Header（及可选 body.userId）。
     *
     * <p>不写入 customer-header ThreadLocal：非流式 Feign 须显式传
     * {@link #custUserIdHeaderValue()}，避免默认 profile 关闭时透传失效，
     * 以及请求结束后 ThreadLocal 未清理导致串用户。
     *
     * @param headers 转发给 Runtime 的 HTTP headers（OkHttp 流式路径）
     * @param setBodyUserId 可选：写入请求体 userId（如工作流试运行）
     */
    public static void applyLoginUser(HttpHeaders headers, Consumer<String> setBodyUserId) {
        String userId = custUserIdHeaderValue();
        if (userId == null) {
            return;
        }

        if (headers != null) {
            // 出站 header：动态登录用户覆盖固定 / 缺失的 cust-userid
            headers.set(Constants.CustomModel.CUSTOM_USER_ID, userId);
        }

        if (setBodyUserId != null) {
            setBodyUserId.accept(userId);
        }
    }

    /** 仅写入 Header（Agent 试运行等无 body.userId 字段的场景）。 */
    public static void applyLoginUser(HttpHeaders headers) {
        applyLoginUser(headers, null);
    }
}
