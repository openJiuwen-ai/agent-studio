/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.proxy;

import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.Constant;

import org.apache.commons.lang3.StringUtils;
import org.springframework.http.HttpHeaders;

import java.util.Optional;
import java.util.function.Consumer;

/**
 * 画布试运行调用 Runtime 时，把登录用户统一认证号写入出站参数。
 *
 * <p>替代模型鉴权里写死的 {@code cust-userid}，支撑模型网关按用户维度统计 token。
 * 对应 GitHub #1728 / GitCode #1761。仅 {@code X-Invoke-Mode=debug} 的画布试运行
 * （及单节点试运行等专用入口）应调用；百宝箱试用 / PUBLISHED / 网页短链勿用。
 *
 * <p>出站方式：
 * <ul>
 *   <li>流式 OkHttp：写入 {@link HttpHeaders}，由 stream 调用直接转发</li>
 *   <li>非流式 Feign：调用方把 {@link #custUserIdHeaderValueForCanvasTrial} 作为
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
     * 是否画布试运行/调试：{@code X-Invoke-Mode=debug}（大小写不敏感）。
     */
    public static boolean isCanvasTrialInvoke(HttpHeaders headers) {
        if (headers == null) {
            return false;
        }
        String mode = headers.getFirst(Constant.Agent.INVOKE_HEADER_KEY);
        return Constant.Common.INVOKE_MOD_DEBUG.equalsIgnoreCase(mode);
    }

    /**
     * 当前登录用户统一认证号；无 IAM 上下文或空白时返回 {@code null}
     * （Feign {@code required=false} 时省略 header）。
     *
     * <p>使用 {@link RequestContextUtils#getRequestIamCtxOptional()}，避免
     * {@code getRequestUserId()} 在无上下文时抛未捕获异常。
     */
    public static String custUserIdHeaderValue() {
        Optional<SimpleUser> ctx = RequestContextUtils.getRequestIamCtxOptional();
        if (ctx == null || ctx.isEmpty()) {
            return null;
        }
        String userId = ctx.get().getUserId();
        return StringUtils.isBlank(userId) ? null : userId;
    }

    /**
     * 仅画布试运行时返回登录用户；否则 {@code null}（不改正式/试用发布口径）。
     */
    public static String custUserIdHeaderValueForCanvasTrial(HttpHeaders headers) {
        return isCanvasTrialInvoke(headers) ? custUserIdHeaderValue() : null;
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

    /**
     * 仅在 {@code X-Invoke-Mode=debug} 时写入登录用户；正式 / 百宝箱试用等跳过。
     */
    public static void applyLoginUserForCanvasTrial(HttpHeaders headers, Consumer<String> setBodyUserId) {
        if (!isCanvasTrialInvoke(headers)) {
            return;
        }
        applyLoginUser(headers, setBodyUserId);
    }

    /** {@link #applyLoginUserForCanvasTrial(HttpHeaders, Consumer)} 仅 Header 重载。 */
    public static void applyLoginUserForCanvasTrial(HttpHeaders headers) {
        applyLoginUserForCanvasTrial(headers, null);
    }
}
