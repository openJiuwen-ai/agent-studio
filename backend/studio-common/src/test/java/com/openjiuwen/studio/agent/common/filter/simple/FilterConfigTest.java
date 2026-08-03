/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.common.filter.simple;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.boot.web.servlet.FilterRegistrationBean;

import com.openjiuwen.studio.agent.common.customerheader.CustomerHeaderProfile;
import com.openjiuwen.studio.agent.common.customerheader.PlatformPrincipalResolver;

public class FilterConfigTest {

    private FilterConfig filterConfig;
    private PlatformPrincipalResolver mockResolver;
    private CustomerHeaderProfile mockProfile;

    @BeforeEach
    void setUp() {
        filterConfig = new FilterConfig();
        mockResolver = Mockito.mock(PlatformPrincipalResolver.class);
        mockProfile = new CustomerHeaderProfile();
    }

    @Test
    void testSimpleAuthFilter_ReturnsRegistrationBean() {
        FilterRegistrationBean<SimpleAuthFilter> result = filterConfig.simpleAuthFilter();

        assertNotNull(result);
        assertNotNull(result.getFilter());
        assertTrue(result.getFilter() instanceof SimpleAuthFilter);
        assertEquals(Integer.MIN_VALUE, result.getOrder());
        assertTrue(result.getUrlPatterns().contains("/*"));
    }

    @Test
    void testFilter_ReturnsRegistrationBean() {
        FilterRegistrationBean<SidToTokenFilter> result = filterConfig.filter();

        assertNotNull(result);
        assertNotNull(result.getFilter());
        assertTrue(result.getFilter() instanceof SidToTokenFilter);
        assertEquals(Integer.MIN_VALUE, result.getOrder());
        assertTrue(result.getUrlPatterns().contains("/*"));
    }

    @Test
    void testSimpleUserContextFilter_ReturnsRegistrationBean() {
        FilterRegistrationBean<SimpleUserContextFilter> result = filterConfig.simpleUserContextFilter(
            mockResolver, mockProfile);

        assertNotNull(result);
        assertNotNull(result.getFilter());
        assertTrue(result.getFilter() instanceof SimpleUserContextFilter);
        assertEquals(Integer.MIN_VALUE + 1, result.getOrder());
        assertTrue(result.getUrlPatterns().contains("/*"));
    }

    @Test
    void testSimpleAuthFilter_OrderLessThanUserContextFilter() {
        FilterRegistrationBean<SimpleAuthFilter> authFilter = filterConfig.simpleAuthFilter();
        FilterRegistrationBean<SimpleUserContextFilter> userContextFilter = filterConfig.simpleUserContextFilter(
            mockResolver, mockProfile);

        assertTrue(authFilter.getOrder() < userContextFilter.getOrder());
    }

    @Test
    void testSidToTokenFilter_OrderLessThanUserContextFilter() {
        FilterRegistrationBean<SidToTokenFilter> sidFilter = filterConfig.filter();
        FilterRegistrationBean<SimpleUserContextFilter> userContextFilter = filterConfig.simpleUserContextFilter(
            mockResolver, mockProfile);

        assertTrue(sidFilter.getOrder() < userContextFilter.getOrder());
    }
}