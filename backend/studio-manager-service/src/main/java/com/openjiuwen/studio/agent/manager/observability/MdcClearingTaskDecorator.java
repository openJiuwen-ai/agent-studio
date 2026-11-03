/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import org.springframework.core.task.TaskDecorator;

/**
 * {@link TaskDecorator} variant that <em>forces</em> the four whitelist MDC keys to be absent
 * during the task, regardless of the submitter's MDC state.
 *
 * <p>Unlike {@link MdcTaskDecorator} (which propagates the submitter's snapshot), this
 * decorator captures nothing from the submitter and installs an all-absent snapshot
 * ({@link MdcSnapshot#empty()}) so a background task cannot inherit a request MDC that
 * happens to be set on the submitter thread (e.g. a {@code @PostConstruct} starter whose
 * submitter is the startup thread, not a request thread).
 *
 * <p>Used by the COM-02 background executors (rev6 §3.4) to make "does not inherit request
 * context" a code contract enforced by the decorator rather than a calling convention. The
 * worker's pre-scope MDC and {@link RequestAttributes} are still restored on completion
 * (inherited from {@link MdcTaskDecorator#wrap}).
 */
public class MdcClearingTaskDecorator extends MdcTaskDecorator implements TaskDecorator {

    @Override
    public Runnable decorate(Runnable runnable) {
        // No submitter snapshot; force all four whitelist keys absent on the worker.
        return wrap(runnable, () -> MdcSnapshot.empty().openScope());
    }
}
