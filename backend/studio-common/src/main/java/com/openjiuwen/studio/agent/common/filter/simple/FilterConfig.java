/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.filter.simple;

import org.springframework.boot.autoconfigure.condition.ConditionalOnExpression;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.web.SecurityFilterChain;

/**
 * filter注册类
 * 注意：顺序不能换
 *
 */
@Configuration
@ConditionalOnExpression("'simple'.equals('${env.type:}') && ''.equals('${auth.sso.validate-url:}')")
public class FilterConfig {
    @Bean
    public FilterRegistrationBean<SimpleAuthFilter> simpleAuthFilter() {
        FilterRegistrationBean<SimpleAuthFilter> filterRegistrationBean =
            new FilterRegistrationBean<SimpleAuthFilter>();
        filterRegistrationBean.setFilter(new SimpleAuthFilter());
        filterRegistrationBean.addUrlPatterns("/*");
        filterRegistrationBean.setOrder(Integer.MIN_VALUE); // order的数值越小 则优先级越高
        return filterRegistrationBean;
    }

    @Bean
    public FilterRegistrationBean<SidToTokenFilter> filter() {
        FilterRegistrationBean<SidToTokenFilter> filterRegistrationBean =
            new FilterRegistrationBean<SidToTokenFilter>();
        filterRegistrationBean.setFilter(new SidToTokenFilter());
        filterRegistrationBean.addUrlPatterns("/*");
        filterRegistrationBean.setOrder(Integer.MIN_VALUE); // order的数值越小 则优先级越高
        return filterRegistrationBean;
    }

    @Bean
    public FilterRegistrationBean<SimpleUserContextFilter> simpleUserContextFilter() {
        FilterRegistrationBean<SimpleUserContextFilter> filterRegistrationBean =
            new FilterRegistrationBean<SimpleUserContextFilter>();
        filterRegistrationBean.setFilter(new SimpleUserContextFilter());
        filterRegistrationBean.addUrlPatterns("/*");
        filterRegistrationBean.setOrder(Integer.MIN_VALUE + 1); // 在SidToTokenFilter之后执行
        return filterRegistrationBean;
    }

    @Bean
    public SecurityFilterChain simpleSecurityFilterChain(HttpSecurity http) throws Exception {
        http.csrf(csrf -> csrf.disable())
            .authorizeHttpRequests(auth -> auth.anyRequest().permitAll());
        return http.build();
    }
}
