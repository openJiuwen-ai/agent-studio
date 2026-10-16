/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import org.springframework.core.env.MapPropertySource;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ThreadPoolExecutor;

class AsyncConfigTest {
    @Test
    void shouldCreateDedicatedPollingCheckExecutor() {
        try (AnnotationConfigApplicationContext context = new AnnotationConfigApplicationContext()) {
            context.getEnvironment().getPropertySources().addFirst(new MapPropertySource("test", properties()));
            context.register(AsyncConfig.class);
            context.refresh();

            ThreadPoolTaskExecutor checkExecutor =
                context.getBean("pollingCheckExecutor", ThreadPoolTaskExecutor.class);
            assertEquals(2, checkExecutor.getCorePoolSize());
            assertEquals(2, checkExecutor.getMaxPoolSize());
            assertEquals(4, checkExecutor.getQueueCapacity());
            assertEquals("polling-check-", checkExecutor.getThreadNamePrefix());
            assertTrue(checkExecutor.getThreadPoolExecutor().allowsCoreThreadTimeOut());
            assertInstanceOf(ThreadPoolExecutor.AbortPolicy.class,
                checkExecutor.getThreadPoolExecutor().getRejectedExecutionHandler());
            assertFalse(context.containsBean("pollingTargetExecutor"));
        }
    }

    private static Map<String, Object> properties() {
        Map<String, Object> properties = new HashMap<>();
        properties.put("spring.pools.asyncExecutor.corePoolSize", 1);
        properties.put("spring.pools.asyncExecutor.maxPoolSize", 1);
        properties.put("spring.pools.asyncExecutor.queueCapacity", 1);
        properties.put("spring.pools.asyncExecutor.threadNamePrefix", "async-test-");
        properties.put("spring.pools.asyncExecutor.keepAliveSeconds", 10);
        properties.put("spring.pools.pollingCheckExecutor.corePoolSize", 2);
        properties.put("spring.pools.pollingCheckExecutor.maxPoolSize", 2);
        properties.put("spring.pools.pollingCheckExecutor.queueCapacity", 4);
        properties.put("spring.pools.pollingCheckExecutor.threadNamePrefix", "polling-check-");
        properties.put("spring.pools.pollingCheckExecutor.keepAliveSeconds", 10);
        properties.put("spring.pools.pollingCheckExecutor.awaitTerminationSeconds", 5);
        return properties;
    }
}
