/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
 */

package com.openjiuwen.studio.agent.space.app;

import com.baomidou.mybatisplus.annotation.DbType;
import com.baomidou.mybatisplus.extension.plugins.MybatisPlusInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.PaginationInnerInterceptor;
import com.github.pagehelper.PageInterceptor;

import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;
import lombok.extern.slf4j.Slf4j;

import org.hibernate.validator.HibernateValidator;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.beans.factory.config.AutowireCapableBeanFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.scheduling.concurrent.ThreadPoolTaskScheduler;
import org.springframework.validation.beanvalidation.SpringConstraintValidatorFactory;

import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ThreadPoolExecutor;

/**
 * Created by Fang Zhen on 2023/10/27.
 */
@Slf4j
@Configuration
public class SystemConfig {
    @Value("${agent.builder.core.pool.size}")
    private int corePoolSize;

    @Value("${agent.builder.max.pool.size}")
    private int maxPoolSize;

    @Value("${agent.builder.pool.queue.size}")
    private int queueCapacity;

    @Value("${agent.builder.pool.keep.alive.seconds}")
    private int keepAliveSeconds;

    @Value("${mybatis-plus.global-config.db-config.db-type:mysql}")
    private String dbType;

    @Bean
    public ThreadPoolTaskExecutor myTaskExecutor() {
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
        executor.setThreadNamePrefix("TaskExecutor-");
        // 设置拒绝策略
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        // 等待所有任务结束后再关闭线程池
        executor.setWaitForTasksToCompleteOnShutdown(true);
        return executor;
    }

    @Bean
    public ThreadPoolTaskScheduler ssePollScheduler() {
        ThreadPoolTaskScheduler scheduler = new ThreadPoolTaskScheduler();
        scheduler.setPoolSize(maxPoolSize * 2); // 定时任务核心线程数
        scheduler.setThreadNamePrefix("SSE-Poll-"); // 线程名前缀
        scheduler.setWaitForTasksToCompleteOnShutdown(true); // 优雅关闭
        scheduler.setAwaitTerminationSeconds(5); // 关闭等待时间
        scheduler.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy()); // 拒绝策略
        return scheduler;
    }

    @Bean
    public ScheduledExecutorService scheduledExecutorService() {
        // 从 ThreadPoolTaskScheduler 中获取底层的 ScheduledExecutorService
        return ssePollScheduler().getScheduledExecutor();
    }

    @Bean
    public Validator validator(AutowireCapableBeanFactory springFactory) {
        try (ValidatorFactory factory = Validation.byProvider(HibernateValidator.class)
            .configure()
            .failFast(true)
            .constraintValidatorFactory(new SpringConstraintValidatorFactory(springFactory))
            .buildValidatorFactory()) {
            return factory.getValidator();
        }
    }

    @Bean
    public MybatisPlusInterceptor paginationInnerInterceptor() {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();

        interceptor.addInnerInterceptor(new PaginationInnerInterceptor(DbType.valueOf(dbType.toUpperCase())));
        return interceptor;
    }

    // pagehelper分页插件需要配的拦截器
    @Bean
    public PageInterceptor pageInterceptor() {
        return new PageInterceptor();
    }
}
