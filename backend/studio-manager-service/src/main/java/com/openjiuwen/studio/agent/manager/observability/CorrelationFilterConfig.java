/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import jakarta.servlet.DispatcherType;

import java.util.EnumSet;

import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.Ordered;

/**
 * 关联 Filter 显式注册配置（COM-05 §11.3）。
 *
 * <p>order 取 {@link Ordered#HIGHEST_PRECEDENCE}，使关联 Filter 位于 Manager 可控应用
 * Filter 的最外层（SAML 双 Filter 由 AuthFilterConfig 顺延为 +1/+2，License @Order(0)
 * 保持在后）。dispatcher types 显式为 REQUEST/ASYNC/ERROR——Boot 对未显式配置的
 * OncePerRequestFilter 会注册全部派发类型（含 FORWARD/INCLUDE），不得依赖该默认值。
 * 与 Spring Boot 内建 {@code OrderedCharacterEncodingFilter} 的同序为已知良性情况
 * （编码 Filter 不读写 MDC/关联 Header）。
 */
@Configuration
public class CorrelationFilterConfig {

    /** 注册名（显式命名，避免依赖 Filter 类型推断）。 */
    public static final String FILTER_NAME = "correlationContextFilter";

    @Bean
    public FilterRegistrationBean<CorrelationContextFilter> correlationContextFilterRegistration() {
        FilterRegistrationBean<CorrelationContextFilter> registration =
            new FilterRegistrationBean<>(new CorrelationContextFilter());
        registration.setOrder(Ordered.HIGHEST_PRECEDENCE);
        registration.setDispatcherTypes(EnumSet.of(DispatcherType.REQUEST, DispatcherType.ERROR,
            DispatcherType.ASYNC));
        registration.addUrlPatterns("/*");
        registration.setName(FILTER_NAME);
        return registration;
    }
}
