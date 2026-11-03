/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.config;

import org.quartz.spi.JobFactory;
import org.springframework.boot.autoconfigure.quartz.SchedulerFactoryBeanCustomizer;
import org.springframework.context.ApplicationContext;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.quartz.SpringBeanJobFactory;

@Configuration
public class QuartzConfig {

    // 配置JobFactory，让Quartz使用Spring的Bean
    @Bean
    public JobFactory jobFactory(ApplicationContext applicationContext) {
        SpringBeanJobFactory jobFactory = new SpringBeanJobFactory();
        jobFactory.setApplicationContext(applicationContext);
        return jobFactory;
    }

    // Let Boot apply the configured JDBC store, data source and cluster properties.
    @Bean
    public SchedulerFactoryBeanCustomizer quartzJobFactoryCustomizer(JobFactory jobFactory) {
        return schedulerFactory -> schedulerFactory.setJobFactory(jobFactory);
    }
}
