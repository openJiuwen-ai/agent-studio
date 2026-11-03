/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.web.context.request.RequestAttributes;
import org.springframework.web.context.request.RequestContextHolder;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;

class MdcTaskDecoratorTest {

    @AfterEach
    void clearMdc() {
        // 测试清理可用 clear()：覆盖白名单与用例写入的非白名单 key（task-id），避免跨用例污染（审视 §3.3）
        MDC.clear();
        RequestContextHolder.resetRequestAttributes();
    }

    @Test
    void propagate_submitter_mdc_into_worker() throws Exception {
        ThreadPoolExecutor pool = new ThreadPoolExecutor(1, 1, 0, TimeUnit.SECONDS, new LinkedBlockingQueue<>());
        MdcTaskDecorator decorator = new MdcTaskDecorator();
        MDC.put(MdcKeys.REQUEST_ID, "req-1");
        MDC.put(MdcKeys.TRACE_ID, "trace-1");

        AtomicReference<String> seenReq = new AtomicReference<>();
        AtomicReference<String> seenTrace = new AtomicReference<>();
        CountDownLatch latch = new CountDownLatch(1);
        pool.submit(decorator.decorate(() -> {
            seenReq.set(MDC.get(MdcKeys.REQUEST_ID));
            seenTrace.set(MDC.get(MdcKeys.TRACE_ID));
            latch.countDown();
        }));
        assertThat(latch.await(5, TimeUnit.SECONDS)).isTrue();
        assertThat(seenReq.get()).isEqualTo("req-1");
        assertThat(seenTrace.get()).isEqualTo("trace-1");
        pool.shutdownNow();
    }

    @Test
    void empty_submitter_clears_worker_residue() throws Exception {
        ThreadPoolExecutor pool = new ThreadPoolExecutor(1, 1, 0, TimeUnit.SECONDS, new LinkedBlockingQueue<>());
        MdcTaskDecorator decorator = new MdcTaskDecorator();

        // 1) 用【未装饰】任务在真实工作线程上写入残留（不经 decorator，残留在任务后仍留在工作线程）
        CountDownLatch residueDone = new CountDownLatch(1);
        pool.submit(() -> {
            MDC.put(MdcKeys.EXECUTION_ID, "raw-residue");
            MDC.put(MdcKeys.CONVERSATION_ID, "raw-residue-conv");
            residueDone.countDown();
        });
        assertThat(residueDone.await(5, TimeUnit.SECONDS)).isTrue();
        // 等工作线程真正回到空闲（残留此刻确实留在该线程上）
        assertThat(awaitPoolIdle(pool)).isTrue();

        // 2) 提交线程 MDC 为空，提交装饰任务：空快照必须清除工作线程残留
        AtomicReference<String> execDuring = new AtomicReference<>("unset");
        AtomicReference<String> convDuring = new AtomicReference<>("unset");
        CountDownLatch secondDone = new CountDownLatch(1);
        pool.submit(decorator.decorate(() -> {
            execDuring.set(MDC.get(MdcKeys.EXECUTION_ID));
            convDuring.set(MDC.get(MdcKeys.CONVERSATION_ID));
            secondDone.countDown();
        }));
        assertThat(secondDone.await(5, TimeUnit.SECONDS)).isTrue();
        assertThat(execDuring.get()).isNull();   // residue cleared by empty snapshot
        assertThat(convDuring.get()).isNull();

        // 3) 任务结束后工作线程原值恢复（残留回到工作线程——对称恢复语义）
        assertThat(awaitPoolIdle(pool)).isTrue();
        AtomicReference<String> execAfter = new AtomicReference<>("unset");
        CountDownLatch probe = new CountDownLatch(1);
        pool.submit(() -> {  // 未装饰探针：直接读工作线程当前 MDC
            execAfter.set(MDC.get(MdcKeys.EXECUTION_ID));
            probe.countDown();
        });
        assertThat(probe.await(5, TimeUnit.SECONDS)).isTrue();
        assertThat(execAfter.get()).isEqualTo("raw-residue"); // decorator restored worker pre-scope state
        pool.shutdownNow();
    }

    @Test
    void task_exception_restores_worker_state() {
        MdcTaskDecorator decorator = new MdcTaskDecorator();
        // pre-scope: request-id set, execution-id absent
        MDC.put(MdcKeys.REQUEST_ID, "outer");

        Runnable throwing = decorator.decorate(() -> {
            // snapshot (captured from this thread) installed: request-id=outer
            assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("outer");
            // mutate an extra whitelist key inside the task
            MDC.put(MdcKeys.EXECUTION_ID, "task-set");
            assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isEqualTo("task-set");
            throw new IllegalStateException("boom");
        });

        assertThatThrownBy(throwing::run)
            .isInstanceOf(IllegalStateException.class);

        // scope.close() ran in finally despite the throw: task-set execution-id removed
        assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isNull();
        // request-id restored to pre-scope value
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("outer");
    }

    @Test
    void non_whitelist_key_not_propagated() throws Exception {
        ThreadPoolExecutor pool = new ThreadPoolExecutor(1, 1, 0, TimeUnit.SECONDS, new LinkedBlockingQueue<>());
        MdcTaskDecorator decorator = new MdcTaskDecorator();
        MDC.put("task-id", "should-not-propagate");
        MDC.put(MdcKeys.REQUEST_ID, "r");

        AtomicReference<String> seenTask = new AtomicReference<>();
        AtomicReference<String> seenReq = new AtomicReference<>();
        CountDownLatch latch = new CountDownLatch(1);
        pool.submit(decorator.decorate(() -> {
            seenTask.set(MDC.get("task-id"));
            seenReq.set(MDC.get(MdcKeys.REQUEST_ID));
            latch.countDown();
        }));
        assertThat(latch.await(5, TimeUnit.SECONDS)).isTrue();
        assertThat(seenReq.get()).isEqualTo("r");
        assertThat(seenTask.get()).isNull(); // non-whitelist never propagated
        pool.shutdownNow();
    }

    @Test
    void cancelled_running_task_restores_worker() throws Exception {
        // 审视 §4.1：运行中任务被 cancel(true) 中断后，decorator finally 仍恢复工作线程原值。
        // 用裸 JDK 池 + 手工装饰（不经 bean），探针才能真正观察工作线程残留。
        ThreadPoolExecutor pool = new ThreadPoolExecutor(1, 1, 0, TimeUnit.SECONDS, new LinkedBlockingQueue<>());
        MdcTaskDecorator decorator = new MdcTaskDecorator();
        MDC.put(MdcKeys.REQUEST_ID, "outer-req");

        CountDownLatch started = new CountDownLatch(1);
        CountDownLatch bodyDone = new CountDownLatch(1);
        java.util.concurrent.Future<?> f = pool.submit(decorator.decorate(() -> {
            started.countDown();
            try {
                Thread.sleep(10_000);
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
            }
            bodyDone.countDown();
        }));
        assertThat(started.await(5, TimeUnit.SECONDS)).isTrue();
        f.cancel(true);
        assertThat(bodyDone.await(5, TimeUnit.SECONDS)).isTrue();
        Thread.sleep(100);  // 等 decorator finally 收尾

        // 裸探针（未被装饰）：工作线程真实 MDC 已恢复，无 outer-req 残留
        AtomicReference<String> seen = new AtomicReference<>("unset");
        CountDownLatch probe = new CountDownLatch(1);
        pool.submit(() -> {
            seen.set(MDC.get(MdcKeys.REQUEST_ID));
            probe.countDown();
        });
        assertThat(probe.await(5, TimeUnit.SECONDS)).isTrue();
        assertThat(seen.get()).isNull();
        pool.shutdownNow();
    }

    @Test
    void caller_runs_restores_request_attributes() throws Exception {
        // 真实触发 CallerRunsPolicy：池 core=0/max=1/queue=0，先占住唯一工作线程，
        // 再经 executor 提交装饰任务——池满回落到提交（请求）线程同步执行。
        ThreadPoolExecutor pool = new ThreadPoolExecutor(
            0, 1, 0, TimeUnit.SECONDS, new java.util.concurrent.SynchronousQueue<>(),
            new ThreadPoolExecutor.CallerRunsPolicy());
        MdcTaskDecorator decorator = new MdcTaskDecorator();

        RequestAttributes ra = mock(RequestAttributes.class);
        RequestContextHolder.setRequestAttributes(ra);

        // 占住唯一工作线程
        CountDownLatch hold = new CountDownLatch(1);
        pool.submit(() -> {
            try {
                hold.await();
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        });
        Thread.sleep(50);

        String submitterThread = Thread.currentThread().getName();
        AtomicReference<String> runThread = new AtomicReference<>();
        AtomicReference<RequestAttributes> seenDuring = new AtomicReference<>();
        CountDownLatch ran = new CountDownLatch(1);
        try {
            // 经饱和池提交：CallerRuns 使装饰任务在本（提交/请求）线程同步执行
            pool.submit(decorator.decorate(() -> {
                runThread.set(Thread.currentThread().getName());
                seenDuring.set(RequestContextHolder.getRequestAttributes());
                ran.countDown();
            })).get(5, TimeUnit.SECONDS);
        } finally {
            hold.countDown();
            pool.shutdownNow();
        }
        RequestAttributes seenAfter = RequestContextHolder.getRequestAttributes();

        assertThat(ran.await(0, TimeUnit.SECONDS)).isTrue();
        // 任务确在提交线程执行（CallerRuns 真实触发）
        assertThat(runThread.get()).isEqualTo(submitterThread);
        // 提交线程在用的 RA 在任务期间可见，任务后恢复——不被旧 resetRequestAttributes 缺陷清掉
        assertThat(seenDuring.get()).isSameAs(ra);
        assertThat(seenAfter).isSameAs(ra);
    }

    /** 等待池中在途任务归零（工作线程回到空闲），用于确认残留确实留在工作线程上。 */
    private static boolean awaitPoolIdle(ThreadPoolExecutor pool) throws InterruptedException {
        for (int i = 0; i < 100; i++) {
            if (pool.getActiveCount() == 0) {
                return true;
            }
            Thread.sleep(20);
        }
        return false;
    }

    @Test
    void clearing_decorator_forces_keys_absent_even_when_submitter_has_mdc() throws Exception {
        ThreadPoolExecutor pool = new ThreadPoolExecutor(1, 1, 0, TimeUnit.SECONDS, new LinkedBlockingQueue<>());
        MdcClearingTaskDecorator decorator = new MdcClearingTaskDecorator();
        MDC.put(MdcKeys.REQUEST_ID, "submitter-has-it");
        MDC.put(MdcKeys.TRACE_ID, "submitter-trace");

        AtomicReference<String> seenReq = new AtomicReference<>();
        AtomicReference<String> seenTrace = new AtomicReference<>();
        CountDownLatch latch = new CountDownLatch(1);
        pool.submit(decorator.decorate(() -> {
            seenReq.set(MDC.get(MdcKeys.REQUEST_ID));
            seenTrace.set(MDC.get(MdcKeys.TRACE_ID));
            latch.countDown();
        }));
        assertThat(latch.await(5, TimeUnit.SECONDS)).isTrue();
        // clearing decorator forces all four absent regardless of submitter
        assertThat(seenReq.get()).isNull();
        assertThat(seenTrace.get()).isNull();
        // submitter's own MDC untouched (decorator only affects worker scope)
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("submitter-has-it");
        pool.shutdownNow();
    }
}
