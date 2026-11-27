/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.proxy;

import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.Constant;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;
import org.springframework.http.HttpHeaders;

import java.util.Optional;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.never;

/**
 * #1728/#1761：试运行透传登录用户统一认证号。
 *
 * <p>覆盖：流式 OkHttp 用的 header/body 写入；Feign 用的显式 header 值；
 * 无 IAM 上下文安全返回 null；不写入 customer-header ThreadLocal。
 */
class RuntimeUserIdPropagatorTest {

    @AfterEach
    void tearDown() {
        RequestContextUtils.remove();
    }

    private static void stubUserId(MockedStatic<RequestContextUtils> mocked, String userId) {
        if (userId == null) {
            mocked.when(RequestContextUtils::getRequestIamCtxOptional).thenReturn(Optional.empty());
            return;
        }
        SimpleUser user = new SimpleUser();
        user.setUserId(userId);
        mocked.when(RequestContextUtils::getRequestIamCtxOptional).thenReturn(Optional.of(user));
    }

    @Test
    void applyLoginUser_setsCustUseridHeaderAndBody_withoutTouchingThreadLocal() {
        HttpHeaders headers = new HttpHeaders();
        headers.set(Constants.CustomModel.CUSTOM_USER_ID, "static-from-model");
        AtomicReference<String> bodyUserId = new AtomicReference<>();

        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class)) {
            stubUserId(mocked, "login-uid-001");

            RuntimeUserIdPropagator.applyLoginUser(headers, bodyUserId::set);

            assertThat(headers.getFirst(Constants.CustomModel.CUSTOM_USER_ID)).isEqualTo("login-uid-001");
            assertThat(bodyUserId.get()).isEqualTo("login-uid-001");
            mocked.verify(RequestContextUtils::getCustomerHeaders, never());
            mocked.verify(() -> RequestContextUtils.setCustomerHeaders(org.mockito.ArgumentMatchers.anyMap()), never());
            mocked.verify(RequestContextUtils::getRequestUserId, never());
        }
    }

    @Test
    void applyLoginUser_skipsWhenUserIdBlank() {
        HttpHeaders headers = new HttpHeaders();
        AtomicReference<String> bodyUserId = new AtomicReference<>("unchanged");

        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class)) {
            stubUserId(mocked, "  ");

            RuntimeUserIdPropagator.applyLoginUser(headers, bodyUserId::set);

            assertThat(headers.containsKey(Constants.CustomModel.CUSTOM_USER_ID)).isFalse();
            assertThat(bodyUserId.get()).isEqualTo("unchanged");
        }
    }

    @Test
    void applyLoginUser_headerOnlyOverload() {
        HttpHeaders headers = new HttpHeaders();

        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class)) {
            stubUserId(mocked, "uid-agent");

            RuntimeUserIdPropagator.applyLoginUser(headers);

            assertThat(headers.getFirst(Constants.CustomModel.CUSTOM_USER_ID)).isEqualTo("uid-agent");
        }
    }

    @Test
    void custUserIdHeaderValue_returnsNullWhenBlank_forFeignOmit() {
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class)) {
            stubUserId(mocked, "");
            assertThat(RuntimeUserIdPropagator.custUserIdHeaderValue()).isNull();

            stubUserId(mocked, "feign-uid");
            assertThat(RuntimeUserIdPropagator.custUserIdHeaderValue()).isEqualTo("feign-uid");
        }
    }

    @Test
    void custUserIdHeaderValue_returnsNullWhenNoIamContext_withoutThrowing() {
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class)) {
            stubUserId(mocked, null);

            assertThatCode(RuntimeUserIdPropagator::custUserIdHeaderValue).doesNotThrowAnyException();
            assertThat(RuntimeUserIdPropagator.custUserIdHeaderValue()).isNull();

            HttpHeaders headers = new HttpHeaders();
            AtomicReference<String> bodyUserId = new AtomicReference<>("unchanged");
            assertThatCode(() -> RuntimeUserIdPropagator.applyLoginUser(headers, bodyUserId::set))
                .doesNotThrowAnyException();
            assertThat(headers.containsKey(Constants.CustomModel.CUSTOM_USER_ID)).isFalse();
            assertThat(bodyUserId.get()).isEqualTo("unchanged");
            mocked.verify(RequestContextUtils::getRequestUserId, never());
        }
    }

    @Test
    void applyLoginUser_nullHeaders_stillSetsBody_forNonStreamWorkflow() {
        AtomicReference<String> bodyUserId = new AtomicReference<>();

        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class)) {
            stubUserId(mocked, "body-only-uid");

            RuntimeUserIdPropagator.applyLoginUser(null, bodyUserId::set);

            assertThat(bodyUserId.get()).isEqualTo("body-only-uid");
        }
    }

    @Test
    void canvasTrialGate_onlyAppliesWhenInvokeModeDebug() {
        HttpHeaders debugHeaders = new HttpHeaders();
        debugHeaders.set(Constant.Agent.INVOKE_HEADER_KEY, Constant.Common.INVOKE_MOD_DEBUG);
        HttpHeaders publishedHeaders = new HttpHeaders();
        publishedHeaders.set(Constant.Agent.INVOKE_HEADER_KEY, "PUBLISHED");
        AtomicReference<String> bodyUserId = new AtomicReference<>("unchanged");

        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class)) {
            stubUserId(mocked, "login-uid");

            assertThat(RuntimeUserIdPropagator.isCanvasTrialInvoke(debugHeaders)).isTrue();
            assertThat(RuntimeUserIdPropagator.custUserIdHeaderValueForCanvasTrial(debugHeaders))
                .isEqualTo("login-uid");
            RuntimeUserIdPropagator.applyLoginUserForCanvasTrial(debugHeaders, bodyUserId::set);
            assertThat(debugHeaders.getFirst(Constants.CustomModel.CUSTOM_USER_ID)).isEqualTo("login-uid");
            assertThat(bodyUserId.get()).isEqualTo("login-uid");

            bodyUserId.set("unchanged");
            assertThat(RuntimeUserIdPropagator.isCanvasTrialInvoke(publishedHeaders)).isFalse();
            assertThat(RuntimeUserIdPropagator.custUserIdHeaderValueForCanvasTrial(publishedHeaders)).isNull();
            RuntimeUserIdPropagator.applyLoginUserForCanvasTrial(publishedHeaders, bodyUserId::set);
            assertThat(publishedHeaders.containsKey(Constants.CustomModel.CUSTOM_USER_ID)).isFalse();
            assertThat(bodyUserId.get()).isEqualTo("unchanged");
        }
    }
}
