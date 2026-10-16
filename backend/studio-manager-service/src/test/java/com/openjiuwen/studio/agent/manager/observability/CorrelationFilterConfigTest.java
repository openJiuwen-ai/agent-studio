/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import jakarta.servlet.DispatcherType;

import org.junit.jupiter.api.Test;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.core.Ordered;
import org.springframework.stereotype.Component;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * COM-05 §11.3：关联 Filter 显式注册——最外层 order、显式 REQUEST/ASYNC/ERROR
 * dispatcher types（排除 FORWARD/INCLUDE）、非 @Component 防双重注册。
 */
class CorrelationFilterConfigTest {

    @Test
    void registration_outermostOrderAndExplicitDispatchers() {
        FilterRegistrationBean<CorrelationContextFilter> registration =
            new CorrelationFilterConfig().correlationContextFilterRegistration();

        // Manager 可控应用 Filter 中的最外层
        assertThat(registration.getOrder()).isEqualTo(Ordered.HIGHEST_PRECEDENCE);
        // 显式 dispatcher types：只含 REQUEST/ASYNC/ERROR（Boot 3.5 对未配置的 OncePerRequestFilter
        // 会默认注册全部派发类型，含 FORWARD/INCLUDE——必须显式排除）
        assertThat(registration.determineDispatcherTypes())
            .containsExactlyInAnyOrder(DispatcherType.REQUEST, DispatcherType.ERROR, DispatcherType.ASYNC);
    }

    @Test
    void filterClassNotComponentAnnotation_noDoubleAutoRegistration() {
        // Filter 由 FilterRegistrationBean 显式注册；若再加 @Component 会被 Boot 自动注册第二份
        assertThat(CorrelationContextFilter.class.getAnnotation(Component.class)).isNull();
    }
}
