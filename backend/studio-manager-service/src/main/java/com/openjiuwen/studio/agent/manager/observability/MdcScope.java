/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import org.slf4j.MDC;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/**
 * A closeable MDC scope that restores prior MDC state on close.
 *
 * <p>Two semantics (rev6 §3.2):
 *
 * <ul>
 *   <li>{@link #open(Map)} — <b>partial override</b>: only the keys explicitly passed in are
 *       set; close restores each of those keys to its pre-scope value (or removes it if it was
 *       absent). Use for nested entry/execution scopes that set a subset of the whitelist.</li>
 *   <li>{@link #replaceWhitelist(MdcSnapshot)} — <b>whitelist full-replace</b>: all four
 *       whitelist keys are set to the snapshot's value (present → {@code put}, absent →
 *       {@code remove}), clearing any worker-thread residue for keys the snapshot lacks; close
 *       restores all four keys to their pre-scope state. Used by {@link MdcSnapshot#openScope()}
 *       and {@code MdcTaskDecorator}.</li>
 * </ul>
 *
 * <p>Hard rules (rev6 §3.4): {@link #open(Map)} pre-validates that every key is a whitelist key
 * and every value is non-null before mutating any MDC entry — a validation failure raises
 * {@link IllegalArgumentException} with no partial write. The component never calls
 * {@link MDC#clear()} and never copies the whole MDC map (only the four whitelist keys).
 *
 * <p>{@code close()} is idempotent.
 */
public final class MdcScope implements AutoCloseable {

    /** Saved pre-scope state: key → old value ({@code null} entry = was absent). */
    private final Map<String, String> savedOld;

    /** Keys this scope owns (will be restored/removed on close). */
    private final Set<String> ownedKeys;

    private boolean closed;

    private MdcScope(Map<String, String> savedOld, Set<String> ownedKeys) {
        this.savedOld = savedOld;
        this.ownedKeys = ownedKeys;
    }

    /**
     * Partial-override scope: set only the supplied keys, restore them on close.
     *
     * @throws IllegalArgumentException if any key is outside the whitelist or any value is null
     */
    public static MdcScope open(Map<String, String> values) {
        Objects.requireNonNull(values, "values");
        // Pre-validate the whole batch before any MDC mutation.
        for (Map.Entry<String, String> e : values.entrySet()) {
            String key = e.getKey();
            if (!MdcKeys.isSupported(key)) {
                throw new IllegalArgumentException(
                    "unsupported MDC key (not in whitelist): " + key);
            }
            if (e.getValue() == null) {
                throw new IllegalArgumentException("null value for MDC key: " + key);
            }
        }
        Map<String, String> savedOld = new LinkedHashMap<>(values.size());
        for (String key : values.keySet()) {
            savedOld.put(key, MDC.get(key));
        }
        for (Map.Entry<String, String> e : values.entrySet()) {
            MDC.put(e.getKey(), e.getValue());
        }
        // 防御复制（审视 §4.2）：values.keySet() 是调用方 Map 的动态视图，scope 关闭前调用方修改 Map
        // 会导致已写入的 key 不被恢复或恢复未管理的 key——所有权按打开时字段快照固定
        return new MdcScope(savedOld, Set.copyOf(values.keySet()));
    }

    /**
     * Whitelist full-replace scope: install the snapshot's state across all four whitelist keys
     * (present → put, absent → remove), restoring all four to pre-scope state on close.
     */
    public static MdcScope replaceWhitelist(MdcSnapshot snapshot) {
        Objects.requireNonNull(snapshot, "snapshot");
        Map<String, String> savedOld = new LinkedHashMap<>(MdcKeys.orderedKeys().size());
        // Save pre-scope state for ALL four keys (present or absent).
        for (String key : MdcKeys.orderedKeys()) {
            savedOld.put(key, MDC.get(key));
        }
        // Full-replace: present → put, absent → remove.
        for (String key : MdcKeys.orderedKeys()) {
            if (snapshot.isPresent(key)) {
                MDC.put(key, snapshot.valueOf(key));
            } else {
                MDC.remove(key);
            }
        }
        return new MdcScope(savedOld, MdcKeys.whitelist());
    }

    @Override
    public void close() {
        if (closed) {
            return;
        }
        closed = true;
        for (String key : ownedKeys) {
            String old = savedOld.get(key);
            if (old != null) {
                MDC.put(key, old);
            } else {
                MDC.remove(key);
            }
        }
    }
}
