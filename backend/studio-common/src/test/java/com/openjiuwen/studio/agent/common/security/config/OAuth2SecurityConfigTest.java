/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.security.config;

import static org.junit.jupiter.api.Assertions.assertNotNull;

import com.openjiuwen.studio.agent.common.security.filter.SsoAuthenticationFilter;
import com.openjiuwen.studio.agent.common.security.properties.AuthProperties;
import com.openjiuwen.studio.agent.common.security.service.SsoAuthenticationService;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Collections;
import java.util.List;

/**
 * OAuth2SecurityConfig 单元测试
 */
@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
public class OAuth2SecurityConfigTest {

    @Mock
    private SsoAuthenticationService ssoAuthenticationService;

    private AuthProperties authProperties;

    @BeforeEach
    void setUp() {
        authProperties = new AuthProperties();
        AuthProperties.SsoConfig ssoConfig = new AuthProperties.SsoConfig();
        ssoConfig.setHeader("X-Auth-Token");
        ssoConfig.setValidateUrl("http://sso.example.com/validate");
        authProperties.setSso(ssoConfig);

        AuthProperties.PathConfig pathConfig = authProperties.getPath();
        ReflectionTestUtils.setField(pathConfig, "excluded", List.of("/v1/**", "/health"));
    }

    // 场景：OAuth2SecurityConfig构造函数正确初始化
    @Test
    void constructor_shouldInitializeFields() {
        OAuth2SecurityConfig config = new OAuth2SecurityConfig(authProperties, ssoAuthenticationService);

        assertNotNull(config);
    }

    // 场景：ssoAuthenticationFilter Bean正确创建
    @Test
    void ssoAuthenticationFilter_shouldReturnFilter() {
        OAuth2SecurityConfig config = new OAuth2SecurityConfig(authProperties, ssoAuthenticationService);

        SsoAuthenticationFilter filter = config.ssoAuthenticationFilter();

        assertNotNull(filter);
    }

    // 场景：排除路径为空时也能正常工作
    @Test
    void ssoAuthenticationFilter_emptyExcludePaths_shouldNotThrow() {
        AuthProperties.PathConfig pathConfig = authProperties.getPath();
        ReflectionTestUtils.setField(pathConfig, "excluded", Collections.emptyList());

        OAuth2SecurityConfig config = new OAuth2SecurityConfig(authProperties, ssoAuthenticationService);

        SsoAuthenticationFilter filter = config.ssoAuthenticationFilter();
        assertNotNull(filter);
    }
}
