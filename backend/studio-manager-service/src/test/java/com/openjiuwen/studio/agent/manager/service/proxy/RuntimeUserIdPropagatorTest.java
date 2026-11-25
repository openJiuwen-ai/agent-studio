/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.proxy;

import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;
import org.springframework.http.HttpHeaders;

import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.never;

/**
 * #1728/#1761：试运行透传登录用户统一认证号。
 *
 * <p>覆盖：流式 OkHttp 用的 header/body 写入；Feign 用的显式 header 值；
 * 不写入 customer-header ThreadLocal（默认 profile 关闭时拦截器不透传）。
 */
class RuntimeUserIdPropagatorTest {

    @AfterEach
    void tearDown() {
        RequestContextUtils.remove();
    }

    @Test
    void applyLoginUser_setsCustUseridHeaderAndBody_withoutTouchingThreadLocal() {
        HttpHeaders headers = new HttpHeaders();
        headers.set(Constants.CustomModel.CUSTOM_USER_ID, "static-from-model");
        AtomicReference<String> bodyUserId = new AtomicReference<>();

        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("login-uid-001");

            RuntimeUserIdPropagator.applyLoginUser(headers, bodyUserId::set);

            assertThat(headers.getFirst(Constants.CustomModel.CUSTOM_USER_ID)).isEqualTo("login-uid-001");
            assertThat(bodyUserId.get()).isEqualTo("login-uid-001");
            mocked.verify(RequestContextUtils::getCustomerHeaders, never());
            mocked.verify(() -> RequestContextUtils.setCustomerHeaders(org.mockito.ArgumentMatchers.anyMap()), never());
        }
    }

    @Test
    void applyLoginUser_skipsWhenUserIdBlank() {
        HttpHeaders headers = new HttpHeaders();
        AtomicReference<String> bodyUserId = new AtomicReference<>("unchanged");

        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("  ");

            RuntimeUserIdPropagator.applyLoginUser(headers, bodyUserId::set);

            assertThat(headers.containsKey(Constants.CustomModel.CUSTOM_USER_ID)).isFalse();
            assertThat(bodyUserId.get()).isEqualTo("unchanged");
        }
    }

    @Test
    void applyLoginUser_headerOnlyOverload() {
        HttpHeaders headers = new HttpHeaders();

        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("uid-agent");

            RuntimeUserIdPropagator.applyLoginUser(headers);

            assertThat(headers.getFirst(Constants.CustomModel.CUSTOM_USER_ID)).isEqualTo("uid-agent");
        }
    }

    @Test
    void custUserIdHeaderValue_returnsNullWhenBlank_forFeignOmit() {
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("");
            assertThat(RuntimeUserIdPropagator.custUserIdHeaderValue()).isNull();

            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("feign-uid");
            assertThat(RuntimeUserIdPropagator.custUserIdHeaderValue()).isEqualTo("feign-uid");
        }
    }

    @Test
    void applyLoginUser_nullHeaders_stillSetsBody_forNonStreamWorkflow() {
        AtomicReference<String> bodyUserId = new AtomicReference<>();

        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("body-only-uid");

            RuntimeUserIdPropagator.applyLoginUser(null, bodyUserId::set);

            assertThat(bodyUserId.get()).isEqualTo("body-only-uid");
        }
    }
}
