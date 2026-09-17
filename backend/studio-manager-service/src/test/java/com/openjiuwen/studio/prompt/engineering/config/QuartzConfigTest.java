/* Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved. */
package com.openjiuwen.studio.prompt.engineering.config;

import org.h2.jdbcx.JdbcDataSource;
import org.junit.jupiter.api.Test;
import org.quartz.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.AutoConfigurations;
import org.springframework.boot.autoconfigure.quartz.QuartzAutoConfiguration;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.jdbc.datasource.init.ResourceDatabasePopulator;
import org.springframework.scheduling.quartz.LocalDataSourceJobStore;
import org.springframework.scheduling.quartz.QuartzJobBean;
import org.springframework.transaction.PlatformTransactionManager;

import javax.sql.DataSource;
import java.util.Date;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;

class QuartzConfigTest {
    @Test
    void bootAppliesJdbcConfigurationAndRestoresJobAcrossContextRestart() {
        JdbcDataSource dataSource = new JdbcDataSource();
        dataSource.setURL("jdbc:h2:mem:" + UUID.randomUUID() + ";DB_CLOSE_DELAY=-1");
        new ResourceDatabasePopulator(new ClassPathResource("org/quartz/impl/jdbcjobstore/tables_h2.sql"))
            .execute(dataSource);
        CountDownLatch executed = new CountDownLatch(1);
        ApplicationContextRunner runner = new ApplicationContextRunner()
            .withConfiguration(AutoConfigurations.of(QuartzAutoConfiguration.class))
            .withUserConfiguration(QuartzConfig.class)
            .withBean(DataSource.class, () -> dataSource)
            .withBean(PlatformTransactionManager.class, () -> new DataSourceTransactionManager(dataSource))
            .withBean(CountDownLatch.class, () -> executed)
            .withPropertyValues("spring.quartz.job-store-type=jdbc", "spring.quartz.jdbc.initialize-schema=never",
                "spring.quartz.auto-startup=false", "spring.quartz.scheduler-name=polling-persistence-test",
                "spring.quartz.properties.org.quartz.threadPool.threadCount=2",
                "spring.quartz.properties.org.quartz.jobStore.isClustered=true");
        JobKey key = new JobKey("persisted-polling-job");
        runner.run(context -> {
            assertNull(context.getStartupFailure());
            Scheduler scheduler = context.getBean(Scheduler.class);
            assertEquals(LocalDataSourceJobStore.class, scheduler.getMetaData().getJobStoreClass());
            assertTrue(scheduler.getMetaData().isJobStoreClustered());
            assertEquals(2, scheduler.getMetaData().getThreadPoolSize());
            JobDetail job = JobBuilder.newJob(InjectedJob.class).withIdentity(key)
                .usingJobData("pollUrl", "https://example.com/feed").build();
            scheduler.scheduleJob(job, TriggerBuilder.newTrigger().withIdentity("persisted-trigger")
                .startAt(new Date(System.currentTimeMillis() + 3600000))
                .withSchedule(SimpleScheduleBuilder.repeatSecondlyForever(60)).build());
        });
        runner.run(context -> {
            assertNull(context.getStartupFailure());
            Scheduler scheduler = context.getBean(Scheduler.class);
            assertEquals("https://example.com/feed", scheduler.getJobDetail(key).getJobDataMap().getString("pollUrl"));
            assertNotNull(scheduler.getTrigger(new TriggerKey("persisted-trigger")));
            scheduler.start();
            scheduler.triggerJob(key);
            assertTrue(executed.await(5, TimeUnit.SECONDS), "Restored jobs must still support Spring injection");
        });
    }

    public static class InjectedJob extends QuartzJobBean {
        @Autowired
        private CountDownLatch executed;

        @Override
        protected void executeInternal(JobExecutionContext context) {
            executed.countDown();
        }
    }
}
