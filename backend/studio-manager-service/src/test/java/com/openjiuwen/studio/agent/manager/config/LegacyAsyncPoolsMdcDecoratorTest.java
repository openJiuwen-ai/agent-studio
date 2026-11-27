/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.config;

import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import com.openjiuwen.studio.agent.agentbase.config.ThreadPoolConfiguration;
import com.openjiuwen.studio.agent.manager.observability.MdcTaskDecorator;

import org.junit.jupiter.api.Test;
import org.springframework.core.task.TaskDecorator;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.concurrent.Executor;

/**
 * #1652/#1721：存量 AsyncConfig / ThreadPoolConfiguration 池须挂 MdcTaskDecorator。
 */
class LegacyAsyncPoolsMdcDecoratorTest {

    @Test
    void threadPoolConfiguration_all_pools_use_mdc_decorator() {
        ThreadPoolConfiguration config = new ThreadPoolConfiguration();
        assertMdcDecorator(config.instanceInitialExecutor());
        assertMdcDecorator(config.licenseReportTaskExecutor());
        assertMdcDecorator(config.obsTaskExecutor());
        assertMdcDecorator(config.templateRepoMgmtExecutor());
        assertMdcDecorator(config.tenantDataCleanTaskExecutor());
    }

    @Test
    void asyncConfig_pools_use_mdc_decorator() {
        AsyncConfig config = new AsyncConfig();
        ReflectionTestUtils.setField(config, "maxPoolSize", 2);
        ReflectionTestUtils.setField(config, "corePoolSize", 1);
        ReflectionTestUtils.setField(config, "keepAliveSeconds", 30);
        ReflectionTestUtils.setField(config, "threadNamePrefix", "async-");
        ReflectionTestUtils.setField(config, "queueCapacity", 10);
        ReflectionTestUtils.setField(config, "pollingCheckMaxPoolSize", 2);
        ReflectionTestUtils.setField(config, "pollingCheckCorePoolSize", 1);
        ReflectionTestUtils.setField(config, "pollingCheckKeepAliveSeconds", 30);
        ReflectionTestUtils.setField(config, "pollingCheckThreadNamePrefix", "poll-");
        ReflectionTestUtils.setField(config, "pollingCheckQueueCapacity", 10);
        ReflectionTestUtils.setField(config, "pollingCheckAwaitTerminationSeconds", 5);

        assertMdcDecorator(config.mcpTaskExecutor());
        assertMdcDecorator(config.functionSyncExecutor());
        assertMdcDecorator(config.asyncExecutor());
        assertMdcDecorator(config.pollingCheckExecutor());
        assertMdcDecorator(config.mcpUpdateTaskExecutor());
        assertMdcDecorator(config.insightPersistenceExecutor());
        assertMdcDecorator(config.codeAgentCreateTaskExecutor());
    }

    private static void assertMdcDecorator(Executor executor) {
        ThreadPoolTaskExecutor taskExecutor = assertInstanceOf(ThreadPoolTaskExecutor.class, executor);
        TaskDecorator decorator = (TaskDecorator) ReflectionTestUtils.getField(taskExecutor, "taskDecorator");
        assertNotNull(decorator, "taskDecorator must be set");
        assertInstanceOf(MdcTaskDecorator.class, decorator);
    }
}
