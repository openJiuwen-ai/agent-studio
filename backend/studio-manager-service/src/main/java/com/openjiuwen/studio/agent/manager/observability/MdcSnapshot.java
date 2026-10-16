/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import org.slf4j.MDC;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * Immutable snapshot of the four whitelist MDC keys on the capturing thread.
 *
 * <p>Captures each key as <em>present</em> (with its value) or <em>absent</em>. {@link #openScope()}
 * installs the snapshot with <em>whitelist full-replace</em> semantics via
 * {@link MdcScope#replaceWhitelist(MdcSnapshot)}: present keys are {@code put}, absent keys are
 * {@code remove}'d, so a worker thread's residue is cleared to match the snapshot exactly. The
 * scope restores the worker thread's pre-scope state on close.
 *
 * <p>Used by SSE Listener construction (capture on the request thread, open a short scope per
 * callback) and by {@code MdcTaskDecorator} to carry a submitter's MDC into a worker thread.
 */
public final class MdcSnapshot {

    private final Map<String, String> present;
    private final Set<String> absent;

    private MdcSnapshot(Map<String, String> present, Set<String> absent) {
        this.present = present;
        this.absent = absent;
    }

    /**
     * Capture the current state of the four whitelist MDC keys on the calling thread.
     */
    public static MdcSnapshot capture() {
        Map<String, String> present = new LinkedHashMap<>(MdcKeys.orderedKeys().size());
        Set<String> absent = new java.util.LinkedHashSet<>();
        for (String key : MdcKeys.orderedKeys()) {
            String value = MDC.get(key);
            if (value != null) {
                present.put(key, value);
            } else {
                absent.add(key);
            }
        }
        return new MdcSnapshot(
            java.util.Collections.unmodifiableMap(present),
            java.util.Collections.unmodifiableSet(absent)
        );
    }

    /** An empty snapshot — all four keys absent. */
    static MdcSnapshot empty() {
        return new MdcSnapshot(
            java.util.Collections.emptyMap(),
            java.util.Collections.unmodifiableSet(new java.util.LinkedHashSet<>(MdcKeys.orderedKeys()))
        );
    }

    /** {@code true} iff no whitelist key is present in the snapshot. */
    public boolean isEmpty() {
        return present.isEmpty();
    }

    /** Whether {@code key} is present (non-null) in the snapshot. */
    boolean isPresent(String key) {
        return present.containsKey(key);
    }

    /** Value of a present key. */
    String valueOf(String key) {
        return present.get(key);
    }

    /**
     * Open a scope that full-replaces the four whitelist keys with this snapshot's state.
     *
     * <p>Equivalent to {@link MdcScope#replaceWhitelist(MdcSnapshot) replaceWhitelist(this)}.
     * Must be closed (try-with-resources) so the worker thread's pre-scope state is restored.
     */
    public MdcScope openScope() {
        return MdcScope.replaceWhitelist(this);
    }
}
