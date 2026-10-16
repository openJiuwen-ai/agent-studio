/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import org.slf4j.MDC;
import org.springframework.core.task.TaskDecorator;
import org.springframework.web.context.request.RequestAttributes;
import org.springframework.web.context.request.RequestContextHolder;

/**
 * {@link TaskDecorator} that propagates the four whitelist MDC keys across thread-pool handoffs
 * and keeps {@link RequestContextHolder} state symmetric (save → run → restore) so a
 * CallerRuns fallback never clears a request thread's in-use {@link RequestAttributes}.
 *
 * <p>On {@link #decorate(Runnable)} the submitter's MDC snapshot is captured. On the worker
 * thread the snapshot is installed with <em>whitelist full-replace</em> semantics
 * ({@link MdcScope#replaceWhitelist(MdcSnapshot)}): present keys are {@code put}, absent keys
 * are {@code remove}'d — so a worker thread's residue for a key the submitter lacks is cleared.
 * On completion the worker's pre-scope MDC and {@link RequestAttributes} are restored.
 *
 * <p>Scope (rev6 §3.2): COM-02 only guarantees the decorator does not destroy the calling /
 * worker thread's prior state. It does <em>not</em> install the submitter's
 * {@link RequestAttributes} on the worker (no Servlet request object crosses threads), and it
 * does <em>not</em> guarantee a task sees no worker-thread historical request attributes —
 * clearing those is a caller concern. Only the four whitelist MDC keys are touched;
 * {@link MDC#clear()} is never called.
 *
 * <p>This replaces the legacy {@code RequestContextTaskDecorator}, which only reset request
 * attributes without saving them — under a {@code CallerRunsPolicy} that cleared the request
 * thread's own attributes.
 */
public class MdcTaskDecorator implements TaskDecorator {

    @Override
    public Runnable decorate(Runnable runnable) {
        // Capture on the submitter thread so the worker installs the submitter's values.
        MdcSnapshot submitterSnapshot = MdcSnapshot.capture();
        return wrap(runnable, () -> MdcScope.replaceWhitelist(submitterSnapshot));
    }

    /**
     * Worker-side wrapper shared with subclasses: open the supplied MDC scope, run, then close
     * the scope and restore the worker's prior {@link RequestAttributes}.
     *
     * <p>{@link RequestAttributes} is saved before the task and restored after — no submitter
     * request object is installed. For a pool worker with no request attributes this is a
     * no-op; for a CallerRuns fallback on the submitter thread it saves and restores the
     * submitter's in-use attributes instead of clearing them.
     */
    protected final Runnable wrap(Runnable runnable, java.util.function.Supplier<MdcScope> scopeSupplier) {
        return () -> {
            RequestAttributes savedRequestAttributes = RequestContextHolder.getRequestAttributes();
            MdcScope scope = scopeSupplier.get();
            try {
                runnable.run();
            } finally {
                scope.close();
                RequestContextHolder.setRequestAttributes(savedRequestAttributes);
            }
        };
    }
}
