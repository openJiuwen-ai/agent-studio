/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.security.config;

import com.openjiuwen.studio.agent.common.security.filter.SsoAuthenticationFilter;
import com.openjiuwen.studio.agent.common.security.properties.AuthProperties;
import com.openjiuwen.studio.agent.common.security.service.SsoAuthenticationService;

import lombok.extern.slf4j.Slf4j;

import org.springframework.boot.autoconfigure.condition.ConditionalOnExpression;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.AuthenticationEntryPoint;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

import jakarta.servlet.http.HttpServletResponse;

/**
 * OAuth2 安全配置
 *
 * <p>当配置了 auth.sso.validate-url 时激活，配置 Spring Security 过滤链，
 * 集成 SSO 远程鉴权过滤器，并定义认证失败和访问拒绝的响应处理。</p>
 */
@Slf4j
@Configuration
@ConditionalOnExpression("!''.equals('${auth.sso.validate-url:}')")
public class OAuth2SecurityConfig {

    private final AuthProperties authProperties;

    private final SsoAuthenticationService ssoAuthenticationService;

    private final AuthenticationEntryPoint authenticationEntryPoint;

    /**
     * 构造 OAuth2 安全配置，初始化认证入口点
     */
    public OAuth2SecurityConfig(AuthProperties authProperties, SsoAuthenticationService ssoAuthenticationService) {
        this.authProperties = authProperties;
        this.ssoAuthenticationService = ssoAuthenticationService;
        this.authenticationEntryPoint = (request, response, authException) -> {
            log.error("Authentication failed: {}", authException.getMessage());
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.setContentType("application/json");
            response.getWriter().write("{\"code\":\"40101\",\"message\":\"" + authException.getMessage() + "\"}");
        };
        log.info("Authentication mode: SSO (auth.sso.validate-url={})", authProperties.getSso().getValidateUrl());
    }

    /**
     * 配置安全过滤链：禁用 CSRF、无状态会话、排除路径放行、注册 SSO 过滤器
     */
    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http.csrf(csrf -> csrf.disable())
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(
                authorize -> authorize.requestMatchers(getExcludedPaths()).permitAll().anyRequest().permitAll())
            .addFilterBefore(ssoAuthenticationFilter(), UsernamePasswordAuthenticationFilter.class)
            .exceptionHandling(exception -> exception.authenticationEntryPoint(authenticationEntryPoint)
                .accessDeniedHandler((request, response, accessDeniedException) -> {
                    response.setStatus(HttpServletResponse.SC_FORBIDDEN);
                    response.setContentType("application/json");
                    response.getWriter().write("{\"code\":\"40301\",\"message\":\"禁止访问\"}");
                }));

        return http.build();
    }

    /**
     * 创建 SSO 认证过滤器 Bean
     */
    @Bean
    public SsoAuthenticationFilter ssoAuthenticationFilter() {
        SsoAuthenticationFilter filter = new SsoAuthenticationFilter(authProperties.getSso().getHeader(),
            ssoAuthenticationService, authProperties);
        filter.setAuthenticationEntryPoint(authenticationEntryPoint);
        return filter;
    }

    /**
     * 获取不需要鉴权的路径列表
     */
    private String[] getExcludedPaths() {
        return authProperties.getPath().getExcluded().toArray(new String[0]);
    }
}
