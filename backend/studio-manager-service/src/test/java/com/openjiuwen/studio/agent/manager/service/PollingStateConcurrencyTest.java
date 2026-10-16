/* Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.mapper.PollingTriggerStateMapper;
import org.apache.ibatis.builder.xml.XMLMapperBuilder;
import org.apache.ibatis.mapping.Environment;
import org.apache.ibatis.session.SqlSessionFactoryBuilder;
import org.h2.jdbcx.JdbcDataSource;
import org.junit.jupiter.api.Test;
import org.mybatis.spring.SqlSessionTemplate;
import org.mybatis.spring.transaction.SpringManagedTransactionFactory;
import org.quartz.*;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.EnableTransactionManagement;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.UUID;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class PollingStateConcurrencyTest {
    @Test
    void completedDownloadWaitsForEditCommitThenDiscardsOldConfiguration() throws Exception {
        JdbcDataSource dataSource = new JdbcDataSource();
        dataSource.setURL("jdbc:h2:mem:" + UUID.randomUUID() + ";DB_CLOSE_DELAY=-1;LOCK_TIMEOUT=5000");
        JdbcTemplate jdbc = new JdbcTemplate(dataSource);
        jdbc.execute("CREATE TABLE t_polling_trigger_state (trigger_id VARCHAR PRIMARY KEY, last_seen_hash CHAR(64), "
            + "last_checked_at TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP)");
        jdbc.update("INSERT INTO t_polling_trigger_state (trigger_id, last_seen_hash) VALUES ('poll-1', 'before')");
        var configuration = new org.apache.ibatis.session.Configuration(
            new Environment("test", new SpringManagedTransactionFactory(), dataSource));
        try (var xml = getClass().getResourceAsStream("/mapper/PollingTriggerStateMapper.xml")) {
            new XMLMapperBuilder(xml, configuration, "mapper/PollingTriggerStateMapper.xml",
                configuration.getSqlFragments()).parse();
        }
        var mapper = new SqlSessionTemplate(new SqlSessionFactoryBuilder().build(configuration))
            .getMapper(PollingTriggerStateMapper.class);
        var manager = new DataSourceTransactionManager(dataSource);
        Scheduler scheduler = mock(Scheduler.class);
        AgentTriggerService target = mock(AgentTriggerService.class);
        AtomicReference<JobDetail> currentJob = new AtomicReference<>(job("https://example.com/old-feed"));
        when(scheduler.getJobDetail(any())).thenAnswer(invocation -> currentJob.get());
        ExecutorService workers = Executors.newFixedThreadPool(2);
        CountDownLatch locked = new CountDownLatch(1);
        CountDownLatch release = new CountDownLatch(1);
        try (var context = new AnnotationConfigApplicationContext()) {
            context.register(Transactions.class);
            context.registerBean(PlatformTransactionManager.class, () -> manager);
            context.registerBean(Scheduler.class, () -> scheduler);
            context.getBeanFactory().registerSingleton("agentTriggerService", target);
            context.registerBean(PollingStateService.class, () -> new PollingStateService(mapper));
            context.refresh();
            PollingStateService service = context.getBean(PollingStateService.class);
            JobDataMap oldSnapshot = new JobDataMap(currentJob.get().getJobDataMap());
            Future<?> editing = workers.submit(() -> new TransactionTemplate(manager).executeWithoutResult(status -> {
                service.lockState("poll-1");
                locked.countDown();
                try {
                    if (!release.await(5, TimeUnit.SECONDS)) {
                        throw new IllegalStateException("Timed out waiting for test check");
                    }
                } catch (InterruptedException exception) {
                    Thread.currentThread().interrupt();
                    throw new IllegalStateException(exception);
                }
                currentJob.set(job("https://example.com/new-feed"));
            }));
            assertTrue(locked.await(5, TimeUnit.SECONDS));
            Future<?> checking = workers.submit(() -> service.completeCheck(new JobKey("poll-1"), oldSnapshot, "after"));
            assertThrows(TimeoutException.class, () -> checking.get(150, TimeUnit.MILLISECONDS));
            release.countDown();
            editing.get(5, TimeUnit.SECONDS);
            checking.get(5, TimeUnit.SECONDS);
            verifyNoInteractions(target);
            assertEquals("before", jdbc.queryForObject(
                "SELECT TRIM(last_seen_hash) FROM t_polling_trigger_state WHERE trigger_id = 'poll-1'", String.class));
            assertNull(jdbc.queryForObject(
                "SELECT last_checked_at FROM t_polling_trigger_state WHERE trigger_id = 'poll-1'", java.sql.Timestamp.class));
        } finally {
            release.countDown();
            workers.shutdownNow();
            assertTrue(workers.awaitTermination(5, TimeUnit.SECONDS));
        }
    }

    private static JobDetail job(String pollUrl) {
        return JobBuilder.newJob(PollingTriggerService.class).withIdentity("poll-1")
            .usingJobData(CommonConstant.TRIGGER_ID, "poll-1")
            .usingJobData(CommonConstant.POLL_URL, pollUrl).build();
    }

    @Configuration(proxyBeanMethods = false)
    @EnableTransactionManagement
    static class Transactions {
    }
}
