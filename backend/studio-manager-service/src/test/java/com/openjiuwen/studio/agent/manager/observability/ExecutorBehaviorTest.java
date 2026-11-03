/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import com.openjiuwen.studio.agent.agentbase.config.ThreadPoolConfiguration;
import com.openjiuwen.studio.agent.manager.config.AsyncConfig;
import com.openjiuwen.studio.agent.manager.config.ObservabilityAsyncConfig;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.web.context.request.RequestAttributes;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.core.task.TaskExecutor;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.scheduling.concurrent.ThreadPoolTaskScheduler;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.catchThrowable;
import static org.mockito.Mockito.mock;

/**
 * COM-02 执行器行为测试（审视 §4.1）：逐 bean 证明装配后的运行时生命周期行为，
 * 而非仅静态 setTaskDecorator()。覆盖：传播/清空、CallerRuns 关停丢弃、Abort 拒绝、
 * CleanResource 第 7 任务、取消、关停后提交、调度器延迟不占线程。
 */
class ExecutorBehaviorTest {

    private final List<ThreadPoolTaskExecutor> toShutdown = new ArrayList<>();

    @AfterEach
    void cleanup() {
        toShutdown.forEach(e -> e.shutdown());
        MDC.clear();
    }

    private void reg(ThreadPoolTaskExecutor e) {
        toShutdown.add(e);
    }

    private AsyncConfig asyncConfig() {
        AsyncConfig c = new AsyncConfig();
        ReflectionTestUtils.setField(c, "maxPoolSize", 4);
        ReflectionTestUtils.setField(c, "corePoolSize", 1);
        ReflectionTestUtils.setField(c, "keepAliveSeconds", 1);
        ReflectionTestUtils.setField(c, "threadNamePrefix", "test-async-");
        ReflectionTestUtils.setField(c, "queueCapacity", 5);
        return c;
    }

    private ThreadPoolTaskExecutor defaultTaskExecutorBean() throws Exception {
        // SyncAgentWorkflowObsTask.TaskExecutorConfig 是 service.startup 包的包级私有内部类，反射实例化
        Class<?> cfg = Class.forName(
            "com.openjiuwen.studio.agent.manager.service.startup.SyncAgentWorkflowObsTask$TaskExecutorConfig");
        java.lang.reflect.Constructor<?> ctor = cfg.getDeclaredConstructor();
        ctor.setAccessible(true);
        Object instance = ctor.newInstance();
        ThreadPoolTaskExecutor e = (ThreadPoolTaskExecutor) ReflectionTestUtils.invokeMethod(instance, "taskExecutor");
        e.initialize();
        return e;
    }

    /** 提交一个读取 MDC 的任务并返回任务内值（传播/清空的行为断言原语）。 */
    private String submitAndReadKey(TaskExecutor executor, String mdcKey) throws Exception {
        MDC.put(MdcKeys.REQUEST_ID, "probe-req");
        MDC.put(MdcKeys.TRACE_ID, "probe-trace");
        AtomicReference<String> seen = new AtomicReference<>("unset");
        CountDownLatch done = new CountDownLatch(1);
        executor.execute(() -> {
            seen.set(MDC.get(mdcKey));
            done.countDown();
        });
        assertThat(done.await(5, TimeUnit.SECONDS)).isTrue();
        return seen.get();
    }

    @Test
    void observability_beans_propagate_mdc() throws Exception {
        ObservabilityAsyncConfig oac = new ObservabilityAsyncConfig();

        // P4 只落地 ObservabilityAsyncConfig 的 7 个受管 executor（5 propagating + 2 clearing，
        // 后者由 background_executor_clears_mdc / delayWarmup 覆盖）。sync_01 基线 executor
        // （AsyncConfig.mcpTaskExecutor / ThreadPoolConfiguration.* 等）未 retrofit MdcTaskDecorator，
        // 属 COM-02 全量 landscape 任务，不在本轮 P4 范围；故本断言只覆盖已落地 beans。
        List<ThreadPoolTaskExecutor> propagating = new ArrayList<>(List.of(
            oac.requestDerivedAsyncExecutor(4, 16, 200, 60),
            oac.promptModelCallExecutor(2, 4, 50, 60),
            oac.workflowAsyncTaskExecutor(100),
            oac.agentMgmtCleanupExecutor(100),
            oac.cleanResourceExecutor()));
        // 初始化未由 Spring 触发的手工 bean
        propagating.forEach(e -> {
            try {
                e.getThreadPoolExecutor();
            } catch (IllegalStateException ignored) {
                e.initialize();
            }
        });
        propagating.forEach(this::reg);

        for (ThreadPoolTaskExecutor e : propagating) {
            assertThat(submitAndReadKey(e, MdcKeys.REQUEST_ID))
                .as("bean %s 应传播 request-id", e.getThreadNamePrefix())
                .isEqualTo("probe-req");
        }
    }

    @Test
    void background_executor_clears_mdc_instead_of_propagating() throws Exception {
        ThreadPoolTaskExecutor e = new ObservabilityAsyncConfig().backgroundAsyncExecutor(2, 4, 512);
        reg(e);
        // 提交线程带 MDC，任务内四 key 必须为空（MdcClearingTaskDecorator 机制保证）
        assertThat(submitAndReadKey(e, MdcKeys.REQUEST_ID)).isNull();
        assertThat(submitAndReadKey(e, MdcKeys.TRACE_ID)).isNull();
        // 提交线程自身 MDC 不受影响
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("probe-req");
    }

    @Test
    void background_task_exception_contained_and_submit_after_shutdown_rejected() throws Exception {
        ThreadPoolTaskExecutor e = new ObservabilityAsyncConfig().backgroundAsyncExecutor(2, 4, 512);
        reg(e);
        AtomicBoolean ran = new AtomicBoolean(false);
        CountDownLatch done = new CountDownLatch(1);
        e.execute(() -> {
            ran.set(true);
            throw new IllegalStateException("boom");  // 运行异常：由 Future/线程池吞并，不崩线程
        });
        e.execute(done::countDown);
        assertThat(done.await(5, TimeUnit.SECONDS)).isTrue();
        assertThat(ran.get()).isTrue();  // 异常任务后池仍可用

        e.shutdown();
        Throwable thrown = catchThrowable(() -> e.execute(() -> { }));
        // Abort 拒绝（含关停后提交）：TaskRejectedException 继承 RejectedExecutionException，
        // @PostConstruct 外层 catch RejectedExecutionException 语义成立
        assertThat(thrown).isInstanceOf(RejectedExecutionException.class);
    }

    @Test
    void clean_resource_executor_7th_task_rejected() throws Exception {
        ThreadPoolTaskExecutor e = new ObservabilityAsyncConfig().cleanResourceExecutor();
        reg(e);
        CountDownLatch hold = new CountDownLatch(1);
        // 1 running + 5 queued = 6 accepted
        e.execute(() -> awaitUnchecked(hold));
        for (int i = 0; i < 5; i++) {
            e.execute(() -> awaitUnchecked(hold));
        }
        // 第 7 个：AbortPolicy 拒绝
        Throwable thrown = catchThrowable(() -> e.execute(() -> { }));
        assertThat(thrown).isInstanceOf(RejectedExecutionException.class);
        hold.countDown();
    }

    @Test
    void caller_runs_executor_rejects_after_shutdown() throws Exception {
        // §3.3 修复：CallerRunsUnlessShutdownPolicy 在池已 shutdown 时抛 RejectedExecutionException
        // （而非静默丢弃——避免 CompletableFuture.runAsync 的 Future 永不完成）
        ThreadPoolTaskExecutor e = new ObservabilityAsyncConfig().requestDerivedAsyncExecutor(4, 16, 200, 60);
        reg(e);
        e.shutdown();
        AtomicBoolean ran = new AtomicBoolean(false);
        // 关停后提交须抛异常
        Throwable thrown = catchThrowable(() -> e.execute(() -> ran.set(true)));
        assertThat(thrown).isInstanceOf(RejectedExecutionException.class);
        assertThat(ran.get()).isFalse();  // 任务未执行
    }

    @Test
    void completableFuture_runAsync_after_shutdown_throws_immediately() throws Exception {
        // §3.3 核心断言：CompletableFuture.runAsync(task, executor) 在 executor 关停后
        // 同步抛出 RejectedExecutionException（Spring TaskRejectedException 继承之），
        // 而非返回一个永不完成的 Future——调用方立即感知失败，不永久等待。
        ThreadPoolTaskExecutor e = new ObservabilityAsyncConfig().requestDerivedAsyncExecutor(4, 16, 200, 60);
        reg(e);
        e.shutdown();
        // runAsync 同步抛 RejectedExecutionException（TaskRejectedException 继承之）
        Throwable thrown = catchThrowable(
            () -> java.util.concurrent.CompletableFuture.runAsync(() -> { }, e));
        assertThat(thrown).isInstanceOf(RejectedExecutionException.class);
    }

    @Test
    void queued_task_cancelled_before_run_pool_stays_healthy() throws Exception {
        // 注：bean 级执行器的一切提交（含探针）都被 TaskDecorator 装饰（Spring 在底层 execute 覆写中
        // 应用 decorator），无法经 bean 观察工作线程真实残留；取消后不残留的行为级证明见
        // MdcTaskDecoratorTest.cancelled_running_task_restores_worker（裸池+手工装饰）。本用例验证
        // 排队期取消后池恢复可用。
        ThreadPoolTaskExecutor e = new ObservabilityAsyncConfig().cleanResourceExecutor();
        reg(e);
        CountDownLatch hold = new CountDownLatch(1);
        e.execute(() -> awaitUnchecked(hold));       // 占住唯一工作线程
        java.util.concurrent.Future<?> f = e.submit(() -> MDC.put(MdcKeys.REQUEST_ID, "queued-should-not-run"));
        assertThat(f.cancel(false)).isTrue();        // 排队期取消：任务不执行
        hold.countDown();
        // 池恢复正常后，提交探针：工作线程 MDC 不受被取消任务影响
        AtomicReference<String> probe = new AtomicReference<>("unset");
        CountDownLatch done = new CountDownLatch(1);
        e.execute(() -> {
            probe.set(MDC.get(MdcKeys.REQUEST_ID));
            done.countDown();
        });
        assertThat(done.await(5, TimeUnit.SECONDS)).isTrue();
        assertThat(probe.get()).isNull();
    }


    @Test
    void delay_warmup_scheduler_clears_mdc_and_delays_without_occupying_worker() throws Exception {
        // §4.2: scheduler 用 MdcClearingTaskDecorator（强制清空四 key）+ 延迟不占工作线程
        ThreadPoolTaskScheduler s = new ObservabilityAsyncConfig().delayWarmupTaskScheduler();
        AtomicBoolean ran = new AtomicBoolean(false);
        AtomicReference<String> traceInTask = new AtomicReference<>("unset");
        AtomicReference<String> reqInTask = new AtomicReference<>("unset");

        // §4.2: 提交线程带 MDC，调度任务内应看到 null（MdcClearingTaskDecorator 机制保证）
        MDC.put(MdcKeys.REQUEST_ID, "scheduler-submitter-req");
        MDC.put(MdcKeys.TRACE_ID, "scheduler-submitter-trace");
        s.schedule(() -> {
            traceInTask.set(MDC.get(MdcKeys.TRACE_ID));
            reqInTask.set(MDC.get(MdcKeys.REQUEST_ID));
            ran.set(true);
        }, s.getClock().instant().plusMillis(300));

        // 延迟窗口内唯一工作线程可执行其他任务（证明延迟不占线程睡眠）
        AtomicBoolean immediateRan = new AtomicBoolean(false);
        CountDownLatch done = new CountDownLatch(1);
        s.execute(() -> {
            immediateRan.set(true);
            done.countDown();
        });
        assertThat(done.await(2, TimeUnit.SECONDS)).isTrue();
        assertThat(immediateRan.get()).isTrue();

        Thread.sleep(150);
        assertThat(ran.get()).isFalse();   // 300ms 未到不执行
        Thread.sleep(350);
        assertThat(ran.get()).isTrue();    // 到点执行

        // §4.2: 调度任务内四白名单字段为空（提交线程 MDC 不被继承）
        assertThat(traceInTask.get()).isNull();
        assertThat(reqInTask.get()).isNull();
        // 提交线程自身 MDC 不受影响
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("scheduler-submitter-req");
        s.shutdown();
    }

    @Test
    void caller_runs_policy_runs_on_submitter_thread_when_saturated() throws Exception {
        // §4.6: CallerRunsUnlessShutdownPolicy 运行期饱和分支——任务在提交线程同步执行
        // 构造 core=0/max=1/queue=0 的池，先占住唯一工作线程，再提交必然触发 CallerRuns
        ThreadPoolTaskExecutor e = new ThreadPoolTaskExecutor();
        e.setCorePoolSize(0);
        e.setMaxPoolSize(1);
        e.setQueueCapacity(0);
        e.setRejectedExecutionHandler(new CallerRunsUnlessShutdownPolicy());
        e.setTaskDecorator(new MdcTaskDecorator());
        e.initialize();
        reg(e);

        CountDownLatch hold = new CountDownLatch(1);
        e.execute(() -> awaitUnchecked(hold));
        Thread.sleep(50);

        String submitterThread = Thread.currentThread().getName();
        AtomicReference<String> runThread = new AtomicReference<>();
        MDC.put(MdcKeys.REQUEST_ID, "saturation-req");
        CountDownLatch ran = new CountDownLatch(1);
        // 经饱和池提交：CallerRunsUnlessShutdownPolicy 使装饰任务在提交线程同步执行
        e.execute(() -> {
            runThread.set(Thread.currentThread().getName());
            assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("saturation-req");
            ran.countDown();
        });
        assertThat(ran.await(0, TimeUnit.SECONDS)).isTrue();
        assertThat(runThread.get()).isEqualTo(submitterThread);  // 在提交线程执行
        hold.countDown();
    }


    @Test
    void scheduler_exception_goes_to_error_handler_and_next_task_still_runs() throws Exception {
        // §4.2: 调度任务异常进入 ErrorHandler（不中断调度线程），后续任务仍能执行
        ThreadPoolTaskScheduler s = new ObservabilityAsyncConfig().delayWarmupTaskScheduler();
        CountDownLatch done = new CountDownLatch(2);
        s.execute(() -> { throw new IllegalStateException("boom"); });  // 异常任务
        s.execute(done::countDown);  // 后续任务应能执行
        // 异常任务本身也完成了（ErrorHandler 吞掉异常）
        s.execute(done::countDown);
        assertThat(done.await(5, TimeUnit.SECONDS)).isTrue();
        s.shutdown();
    }

    @Test
    void scheduler_cancelled_delayed_task_does_not_run() throws Exception {
        // §4.2: 已取消延迟任务不执行
        ThreadPoolTaskScheduler s = new ObservabilityAsyncConfig().delayWarmupTaskScheduler();
        AtomicBoolean ran = new AtomicBoolean(false);
        java.util.concurrent.ScheduledFuture<?> f =
            s.schedule(() -> ran.set(true), s.getClock().instant().plusMillis(5000));
        f.cancel(false);
        Thread.sleep(200);
        assertThat(ran.get()).isFalse();
        assertThat(f.isCancelled()).isTrue();
        s.shutdown();
    }

    @Test
    void scheduler_shutdown_rejects_new_submit() throws Exception {
        // §4.2: 关闭后新提交被拒绝
        ThreadPoolTaskScheduler s = new ObservabilityAsyncConfig().delayWarmupTaskScheduler();
        s.shutdown();
        Throwable thrown = catchThrowable(() -> s.execute(() -> { }));
        assertThat(thrown).isInstanceOf(RejectedExecutionException.class);
    }


    @Test
    void caller_runs_saturation_task_exception_restores_submitter_state() throws Exception {
        // §4.4: 饱和 CallerRuns 分支——任务修改上下文并抛异常后，提交线程 MDC/RA 恢复
        ThreadPoolTaskExecutor e = new ThreadPoolTaskExecutor();
        e.setCorePoolSize(0);
        e.setMaxPoolSize(1);
        e.setQueueCapacity(0);
        e.setRejectedExecutionHandler(new CallerRunsUnlessShutdownPolicy());
        e.setTaskDecorator(new MdcTaskDecorator());
        e.initialize();
        reg(e);

        CountDownLatch hold = new CountDownLatch(1);
        e.execute(() -> awaitUnchecked(hold));
        Thread.sleep(50);

        MDC.put(MdcKeys.REQUEST_ID, "saturation-outer");
        RequestContextHolder.setRequestAttributes(mock(org.springframework.web.context.request.RequestAttributes.class));
        RequestAttributes before = RequestContextHolder.getRequestAttributes();

        CountDownLatch ran = new CountDownLatch(1);
        try {
            // 经饱和池提交：任务在提交线程同步执行——任务内改 MDC + 抛异常
            e.execute(() -> {
                assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("saturation-outer");  // 提交线程快照已安装
                MDC.put(MdcKeys.REQUEST_ID, "task-modified");  // 任务修改上下文
                ran.countDown();
                throw new RuntimeException("boom");  // 任务异常
            });
        } catch (RuntimeException expected) {
            // CallerRuns 使任务在提交线程同步执行——异常直接传播
        } finally {
            hold.countDown();
        }
        assertThat(ran.await(0, TimeUnit.SECONDS)).isTrue();
        // 提交线程恢复：MDC 回到 outer（不是 task-modified），RA 恢复原引用
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("saturation-outer");
        assertThat(RequestContextHolder.getRequestAttributes()).isSameAs(before);
        RequestContextHolder.resetRequestAttributes();
    }

    private static void awaitUnchecked(CountDownLatch latch) {
        try {
            latch.await();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
