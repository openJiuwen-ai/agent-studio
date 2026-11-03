/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import java.util.concurrent.RejectedExecutionHandler;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ThreadPoolExecutor;

/**
 * {@link RejectedExecutionHandler} that delegates to CallerRunsPolicy semantics while the
 * executor is running, but throws {@link RejectedExecutionException} once the executor has
 * been shut down.
 *
 * <p>The stock {@code CallerRunsPolicy} silently returns (drops the task) when the executor
 * is shut down. For {@code CompletableFuture.runAsync(task, executor)} callers this means the
 * returned Future never completes, causing permanent hangs. This policy avoids that: when
 * the executor is still active, a saturated pool falls back to the caller thread (degraded
 * synchronous execution); when the executor is shut down, it throws so the Future completes
 * exceptionally and callers waiting on {@code .get()} surface the failure.
 */
public class CallerRunsUnlessShutdownPolicy implements RejectedExecutionHandler {

    @Override
    public void rejectedExecution(Runnable r, ThreadPoolExecutor executor) {
        if (!executor.isShutdown()) {
            // Executor still running: fall back to the caller thread (CallerRuns semantics)
            r.run();
        } else {
            // Executor shut down: throw so CompletableFuture completes exceptionally (no hang)
            throw new RejectedExecutionException("Executor has been shut down; task not accepted");
        }
    }
}
