/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.util.concurrent.Executor;
import java.util.concurrent.ThreadPoolExecutor;

/**
 * 功能描述
 *
 */
@Configuration
@EnableAsync
public class AsyncConfig {
    @Value("${spring.pools.asyncExecutor.maxPoolSize}")
    private int maxPoolSize;

    @Value("${spring.pools.asyncExecutor.corePoolSize}")
    private int corePoolSize;

    @Value("${spring.pools.asyncExecutor.keepAliveSeconds}")
    private int keepAliveSeconds;

    @Value("${spring.pools.asyncExecutor.threadNamePrefix}")
    private String threadNamePrefix;

    @Value("${spring.pools.asyncExecutor.queueCapacity}")
    private int queueCapacity;

    @Value("${spring.pools.pollingCheckExecutor.maxPoolSize}")
    private int pollingCheckMaxPoolSize;

    @Value("${spring.pools.pollingCheckExecutor.corePoolSize}")
    private int pollingCheckCorePoolSize;

    @Value("${spring.pools.pollingCheckExecutor.keepAliveSeconds}")
    private int pollingCheckKeepAliveSeconds;

    @Value("${spring.pools.pollingCheckExecutor.threadNamePrefix}")
    private String pollingCheckThreadNamePrefix;

    @Value("${spring.pools.pollingCheckExecutor.queueCapacity}")
    private int pollingCheckQueueCapacity;

    @Value("${spring.pools.pollingCheckExecutor.awaitTerminationSeconds}")
    private int pollingCheckAwaitTerminationSeconds;

    @Bean
    public ThreadPoolTaskExecutor mcpTaskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();

        // 设置核心线程数
        executor.setCorePoolSize(corePoolSize);
        // 设置最大线程数
        executor.setMaxPoolSize(maxPoolSize);
        // 设置队列容量
        executor.setQueueCapacity(queueCapacity);
        // 设置线程活跃时间（秒）
        executor.setKeepAliveSeconds(keepAliveSeconds);
        // 设置默认线程名称
        executor.setThreadNamePrefix("MCPTaskExecutor-");
        // 设置拒绝策略
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        // 等待所有任务结束后再关闭线程池
        executor.setWaitForTasksToCompleteOnShutdown(true);
        return executor;
    }

    @Bean
    public ThreadPoolTaskExecutor functionSyncExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();

        // 设置核心线程数
        executor.setCorePoolSize(corePoolSize);
        // 设置最大线程数
        executor.setMaxPoolSize(maxPoolSize);
        // 设置队列容量
        executor.setQueueCapacity(queueCapacity);
        // 设置线程活跃时间（秒）
        executor.setKeepAliveSeconds(keepAliveSeconds);
        // 设置默认线程名称
        executor.setThreadNamePrefix("functionSyncExecutor-");
        // 设置拒绝策略
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.DiscardPolicy());
        // 等待所有任务结束后再关闭线程池
        executor.setWaitForTasksToCompleteOnShutdown(true);
        return executor;
    }

    @Bean
    public Executor asyncExecutor() {
        ThreadPoolTaskExecutor taskExecutor = new ThreadPoolTaskExecutor();
        taskExecutor.setCorePoolSize(corePoolSize);
        taskExecutor.setMaxPoolSize(maxPoolSize);
        taskExecutor.setQueueCapacity(queueCapacity);
        taskExecutor.setThreadNamePrefix(threadNamePrefix);
        taskExecutor.setKeepAliveSeconds(keepAliveSeconds);
        taskExecutor.setRejectedExecutionHandler(new ThreadPoolExecutor.AbortPolicy());
        taskExecutor.initialize();
        return taskExecutor;
    }

    /**
     * Creates the executor used to fetch polling URLs and compare content hashes.
     *
     * @return polling check executor
     */
    @Bean
    public ThreadPoolTaskExecutor pollingCheckExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(pollingCheckCorePoolSize);
        executor.setMaxPoolSize(pollingCheckMaxPoolSize);
        executor.setQueueCapacity(pollingCheckQueueCapacity);
        executor.setKeepAliveSeconds(pollingCheckKeepAliveSeconds);
        executor.setAllowCoreThreadTimeOut(true);
        executor.setThreadNamePrefix(pollingCheckThreadNamePrefix);
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.AbortPolicy());
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(pollingCheckAwaitTerminationSeconds);
        return executor;
    }

    @Bean
    public ThreadPoolTaskExecutor mcpUpdateTaskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();

        // 设置核心线程数
        executor.setCorePoolSize(corePoolSize);
        // 设置最大线程数
        executor.setMaxPoolSize(maxPoolSize);
        // 设置队列容量
        executor.setQueueCapacity(queueCapacity);
        // 设置线程活跃时间（秒）
        executor.setKeepAliveSeconds(keepAliveSeconds);
        // 设置默认线程名称
        executor.setThreadNamePrefix("mcpUpdateTaskExecutor-");
        // 设置拒绝策略
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        // 等待所有任务结束后再关闭线程池
        executor.setWaitForTasksToCompleteOnShutdown(true);
        return executor;
    }

    @Bean("codeAgentCreateThreadPool")
    public ThreadPoolTaskExecutor codeAgentCreateTaskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();

        // 设置核心线程数
        executor.setCorePoolSize(corePoolSize);
        // 设置最大线程数
        executor.setMaxPoolSize(maxPoolSize);
        // 设置队列容量
        executor.setQueueCapacity(queueCapacity);
        // 设置线程活跃时间（秒）
        executor.setKeepAliveSeconds(keepAliveSeconds);
        // 设置默认线程名称
        executor.setThreadNamePrefix("codeAgentCreateTaskExecutor-");
        // 设置拒绝策略
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        // 等待所有任务结束后再关闭线程池
        executor.setWaitForTasksToCompleteOnShutdown(true);
        return executor;
    }
}
