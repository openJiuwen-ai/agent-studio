/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.config;

import com.openjiuwen.studio.agent.manager.observability.CallerRunsUnlessShutdownPolicy;
import com.openjiuwen.studio.agent.manager.observability.MdcClearingTaskDecorator;
import com.openjiuwen.studio.agent.manager.observability.MdcTaskDecorator;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.scheduling.concurrent.ThreadPoolTaskScheduler;

import java.util.concurrent.ThreadPoolExecutor;

/**
 * COM-02 任务 3A/3B：执行器决策门签定的分类执行器（rev6 §3.4/§3A 表）。
 *
 * <p>分类与 decorator 策略：
 * <ul>
 *   <li>{@code requestDerivedAsyncExecutor} — 请求派生任务（清理幂等 + Environment 缓存回填），
 *       CallerRuns 降级为请求线程同步执行；普通 MDC 传播。</li>
 *   <li>{@code backgroundAsyncExecutor} — 启动后台同步（@PostConstruct），机制上不继承请求 MDC
 *       （MdcClearingTaskDecorator 强制四 key 缺失）；AbortPolicy 拒绝由提交方外层 catch 记告警。</li>
 *   <li>{@code promptModelCallExecutor} — prompt-engineering 限时模型调用专用（60s 超时语义在调用点）。</li>
 *   <li>{@code delayWarmupTaskScheduler} — ModelInterfaceProtocolService 延迟预热，取代占用工作线程的
 *       {@code Thread.sleep(delayTime)}。</li>
 *   <li>三个转受管池（workflowAsync / agentMgmtCleanup / cleanResource）保现状容量与拒绝语义，
 *       仅加 MDC 传播与 Spring 受管生命周期（原自建池从不 shutdown）。</li>
 * </ul>
 */
@Configuration
public class ObservabilityAsyncConfig {

    // ---- 请求派生：清理（幂等）+ Environment 缓存回填 ----

    @Bean("requestDerivedAsyncExecutor")
    public ThreadPoolTaskExecutor requestDerivedAsyncExecutor(
        @Value("${spring.pools.request-derived-async.corePoolSize:4}") int corePoolSize,
        @Value("${spring.pools.request-derived-async.maxPoolSize:16}") int maxPoolSize,
        @Value("${spring.pools.request-derived-async.queueCapacity:200}") int queueCapacity,
        @Value("${spring.pools.request-derived-async.keepAliveSeconds:60}") int keepAliveSeconds) {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(corePoolSize);
        executor.setMaxPoolSize(maxPoolSize);
        executor.setQueueCapacity(queueCapacity);
        executor.setKeepAliveSeconds(keepAliveSeconds);
        executor.setThreadNamePrefix("request-derived-");
        // 清理任务幂等；饱和时退化为请求线程同步执行（可接受降级）；
        // 关停后提交须抛 RejectedExecutionException——否则 CompletableFuture.runAsync 的 Future 永不完成
        executor.setRejectedExecutionHandler(new CallerRunsUnlessShutdownPolicy());
        executor.setTaskDecorator(new MdcTaskDecorator());
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(30);
        executor.initialize();
        return executor;
    }

    // ---- 启动后台同步：不继承请求上下文（机制保证） ----

    @Bean("backgroundAsyncExecutor")
    public ThreadPoolTaskExecutor backgroundAsyncExecutor(
        @Value("${spring.pools.background-async.corePoolSize:2}") int corePoolSize,
        @Value("${spring.pools.background-async.maxPoolSize:4}") int maxPoolSize,
        @Value("${spring.pools.background-async.queueCapacity:512}") int queueCapacity) {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(corePoolSize);
        executor.setMaxPoolSize(maxPoolSize);
        executor.setQueueCapacity(queueCapacity);
        executor.setThreadNamePrefix("background-async-");
        // AbortPolicy：@PostConstruct 提交方外层 catch RejectedExecutionException 记告警，不阻断启动
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.AbortPolicy());
        executor.setTaskDecorator(new MdcClearingTaskDecorator());
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(30);
        executor.initialize();
        return executor;
    }

    // ---- prompt-engineering 限时模型调用 ----

    @Bean("promptModelCallExecutor")
    public ThreadPoolTaskExecutor promptModelCallExecutor(
        @Value("${spring.pools.prompt-model-call.corePoolSize:2}") int corePoolSize,
        @Value("${spring.pools.prompt-model-call.maxPoolSize:4}") int maxPoolSize,
        @Value("${spring.pools.prompt-model-call.queueCapacity:50}") int queueCapacity,
        @Value("${prompt.model.call.timeout-seconds:60}") int timeoutSeconds) {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(corePoolSize);
        executor.setMaxPoolSize(maxPoolSize);
        executor.setQueueCapacity(queueCapacity);
        executor.setThreadNamePrefix("prompt-model-call-");
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.AbortPolicy());
        executor.setTaskDecorator(new MdcTaskDecorator());
        // rev7 §3.1: 停机等待与模型调用整体超时共用同一参数 prompt.model.call.timeout-seconds，
        // 不硬编码——超时经环境变量调整时执行器等待同步变化（调大参数须同步调大 Pod 宽限期）。
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(timeoutSeconds);
        executor.initialize();
        return executor;
    }

    // ---- 延迟预热调度器（取代 Thread.sleep 占用工作线程） ----

    @Bean("delayWarmupTaskScheduler")
    public ThreadPoolTaskScheduler delayWarmupTaskScheduler() {
        ThreadPoolTaskScheduler scheduler = new ThreadPoolTaskScheduler();
        scheduler.setPoolSize(1);
        scheduler.setThreadNamePrefix("delay-warmup-");
        scheduler.setRemoveOnCancelPolicy(true);
        scheduler.setExecuteExistingDelayedTasksAfterShutdownPolicy(false);
        scheduler.setWaitForTasksToCompleteOnShutdown(true);
        scheduler.setAwaitTerminationSeconds(10);
        // 后台预热不继承请求 MDC
        scheduler.setTaskDecorator(new MdcClearingTaskDecorator());
        scheduler.setErrorHandler(t -> {
            // ErrorHandler：延迟预热异常记日志，不中断调度线程
            org.slf4j.LoggerFactory.getLogger("delayWarmupTaskScheduler")
                .error("delay warmup task failed", t);
        });
        scheduler.initialize();
        return scheduler;
    }

    // ---- 转受管：保现状容量与拒绝语义，加 MDC 传播与受管生命周期 ----

    /**
     * TaskRuntimeService 自建 {@code Executors.newFixedThreadPool(taskAsyncPoolSize)}（默认 100）
     * 转受管。保无界队列（等价 newFixedThreadPool 语义）与默认 Abort；原自建池从不 shutdown，
     * 受管后随容器优雅关闭并等待在途 Workflow 异步任务完成（不可丢）。
     */
    @Bean("workflowAsyncTaskExecutor")
    public ThreadPoolTaskExecutor workflowAsyncTaskExecutor(
        @Value("${task.async.pool-size:100}") int taskAsyncPoolSize) {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(taskAsyncPoolSize);
        executor.setMaxPoolSize(taskAsyncPoolSize);
        // Integer.MAX_VALUE == Executors.newFixedThreadPool 的无界 LinkedBlockingQueue
        executor.setQueueCapacity(Integer.MAX_VALUE);
        executor.setThreadNamePrefix("workflow-async-");
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.AbortPolicy());
        executor.setTaskDecorator(new MdcTaskDecorator());
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(30);
        executor.initialize();
        return executor;
    }

    /**
     * AgentManagementService 自建 {@code Executors.newFixedThreadPool(100)}（Agent 删除 OBS 清理）
     * 转受管。保现状容量与无界队列。
     */
    @Bean("agentMgmtCleanupExecutor")
    public ThreadPoolTaskExecutor agentMgmtCleanupExecutor(
        @Value("${spring.pools.agent-mgmt-cleanup.corePoolSize:100}") int corePoolSize) {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(corePoolSize);
        executor.setMaxPoolSize(corePoolSize);
        executor.setQueueCapacity(Integer.MAX_VALUE);
        executor.setThreadNamePrefix("agent-mgmt-cleanup-");
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.AbortPolicy());
        executor.setTaskDecorator(new MdcTaskDecorator());
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(30);
        executor.initialize();
        return executor;
    }

    /**
     * CleanResourceServiceImpl 自建单线程池（队列 5，默认 AbortPolicy）转受管。
     * 保现状拒绝语义：{@code :82 catch RejectedExecutionException} 是业务依赖
     * （Spring 的 TaskRejectedException 继承 RejectedExecutionException，catch 仍生效）。
     */
    @Bean("cleanResourceExecutor")
    public ThreadPoolTaskExecutor cleanResourceExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(1);
        executor.setMaxPoolSize(1);
        executor.setQueueCapacity(5);
        executor.setThreadNamePrefix("clean-resource-");
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.AbortPolicy());
        executor.setTaskDecorator(new MdcTaskDecorator());
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(30);
        executor.initialize();
        return executor;
    }
}
