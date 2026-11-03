/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * Single source of truth for the Manager MDC keys defined by the Studio 2.0 observability
 * protocol (§3.3).
 *
 * <p>The whitelist is the four keys below; nothing else may be propagated or scope-managed by
 * the COM-02 context components. {@code task-id} (historical alias of {@code execution-id}) is
 * intentionally <em>not</em> in the whitelist — it is a DEF-02 migration concern, not a key the
 * new public components touch.
 *
 * <p>{@code trace_id} keeps snake_case to match the cross-service unified log field name; the
 * other three keep Manager's kebab-case convention.
 */
public final class MdcKeys {

    /** MDC key for {@code request_id} (kebab-case Manager convention). */
    public static final String REQUEST_ID = "request-id";

    /** MDC key for {@code trace_id} (snake_case exception, matches unified log field). */
    public static final String TRACE_ID = "trace_id";

    /** MDC key for {@code execution_id} (kebab-case Manager convention). */
    public static final String EXECUTION_ID = "execution-id";

    /** MDC key for {@code conversation_id} (kebab-case Manager convention). */
    public static final String CONVERSATION_ID = "conversation-id";

    private static final List<String> ORDERED_KEYS =
        List.of(REQUEST_ID, TRACE_ID, EXECUTION_ID, CONVERSATION_ID);

    private static final Set<String> WHITELIST =
        Collections.unmodifiableSet(new LinkedHashSet<>(ORDERED_KEYS));

    private MdcKeys() {
    }

    /** Immutable ordered view of the four whitelist keys. */
    public static List<String> orderedKeys() {
        return ORDERED_KEYS;
    }

    /** {@code true} iff {@code key} is one of the four whitelist MDC keys. */
    public static boolean isSupported(String key) {
        return key != null && WHITELIST.contains(key);
    }

    static Set<String> whitelist() {
        return WHITELIST;
    }
}
