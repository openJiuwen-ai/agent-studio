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

/**
 * #1728/#1761：试运行透传登录用户统一认证号。
 */
class RuntimeUserIdPropagatorTest {

    @AfterEach
    void tearDown() {
        RequestContextUtils.remove();
    }

    @Test
    void applyLoginUser_setsCustUseridHeaderAndBody() {
        HttpHeaders headers = new HttpHeaders();
        headers.set(Constants.CustomModel.CUSTOM_USER_ID, "static-from-model");
        AtomicReference<String> bodyUserId = new AtomicReference<>();

        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("login-uid-001");
            mocked.when(RequestContextUtils::getCustomerHeaders).thenReturn(java.util.Collections.emptyMap());
            mocked.when(() -> RequestContextUtils.setCustomerHeaders(org.mockito.ArgumentMatchers.anyMap()))
                .thenAnswer(invocation -> null);

            RuntimeUserIdPropagator.applyLoginUser(headers, bodyUserId::set);

            assertThat(headers.getFirst(Constants.CustomModel.CUSTOM_USER_ID)).isEqualTo("login-uid-001");
            assertThat(bodyUserId.get()).isEqualTo("login-uid-001");
            mocked.verify(() -> RequestContextUtils.setCustomerHeaders(org.mockito.ArgumentMatchers.argThat(
                map -> "login-uid-001".equals(map.get("cust-userid")))));
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
            mocked.when(RequestContextUtils::getCustomerHeaders).thenReturn(java.util.Collections.emptyMap());
            mocked.when(() -> RequestContextUtils.setCustomerHeaders(org.mockito.ArgumentMatchers.anyMap()))
                .thenAnswer(invocation -> null);

            RuntimeUserIdPropagator.applyLoginUser(headers);

            assertThat(headers.getFirst(Constants.CustomModel.CUSTOM_USER_ID)).isEqualTo("uid-agent");
        }
    }
}
