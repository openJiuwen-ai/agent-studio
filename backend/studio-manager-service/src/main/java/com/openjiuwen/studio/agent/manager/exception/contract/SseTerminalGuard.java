/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.contract;

import java.util.concurrent.atomic.AtomicReference;

/**
 * COM-03 §6.2 + 复审6 §3: SseEmitter 唯一原子状态守卫。
 * <p>
 * 合并"是否已打开"与"谁获得终态"为单一原子状态机，消除 listener 中
 * 普通 boolean 的竞态窗口。
 * <ul>
 *   <li>NOT_STARTED ──onOpen──→ STREAMING ──failure──→ TERMINATED</li>
 *   <li>NOT_STARTED ──failure(pre-frame)──→ HTTP_FAILED (terminal)</li>
 *   <li>NOT_STARTED/STREAMING ──cancel──→ CANCELLED (terminal)</li>
 * </ul>
 * 终态（HTTP_FAILED / TERMINATED / CANCELLED）不可逆，后续回调只清理不输出。
 */
public class SseTerminalGuard {

    public enum State {
        NOT_STARTED,
        STREAMING,
        TERMINATED,
        CANCELLED,
        HTTP_FAILED
    }

    private final AtomicReference<State> state = new AtomicReference<>(State.NOT_STARTED);

    public State getState() {
        return state.get();
    }

    /**
     * NOT_STARTED → STREAMING（原子 CAS）。
     * 已进入任何终态时返回 false——onOpen 在 HTTP_FAILED/CANCELLED 后到达时只清理。
     */
    public boolean beginStreaming() {
        return state.compareAndSet(State.NOT_STARTED, State.STREAMING);
    }

    /**
     * NOT_STARTED → HTTP_FAILED（原子 CAS）。
     * 首帧前 HTTP 失败路径：只有赢家（返回 true）允许构建 HTTP error + 记录一次完整栈。
     */
    public boolean tryHttpFailure() {
        return state.compareAndSet(State.NOT_STARTED, State.HTTP_FAILED);
    }

    /**
     * STREAMING → TERMINATED（原子 CAS）。
     * 首帧后 SSE 失败路径：只有赢家（返回 true）允许写 SSE error + 记录一次完整栈。
     */
    public boolean trySendError() {
        return state.compareAndSet(State.STREAMING, State.TERMINATED);
    }

    /**
     * 消息是否允许发送——仅在 STREAMING 时为 true。
     * TERMINATED/HTTP_FAILED/CANCELLED 后均拒绝。
     */
    public boolean allowMessage() {
        return state.get() == State.STREAMING;
    }

    /**
     * 客户端取消/正常断开。NOT_STARTED 和 STREAMING 转为 CANCELLED；
     * 终态（HTTP_FAILED / TERMINATED）不被覆盖。
     */
    public void cancel() {
        state.compareAndSet(State.NOT_STARTED, State.CANCELLED);
        state.compareAndSet(State.STREAMING, State.CANCELLED);
    }

    /**
     * COM-03 复审9 §4.2: 原子取消——只有赢家（返回 true）负责释放等待线程。
     * NOT_STARTED 或 STREAMING 首次进入 CANCELLED 的调用者得到 true；
     * 已是终态（含 HTTP_FAILED）时返回 false，不干扰失败赢家发布结果。
     */
    public boolean tryCancel() {
        return state.compareAndSet(State.NOT_STARTED, State.CANCELLED)
            || state.compareAndSet(State.STREAMING, State.CANCELLED);
    }

    /**
     * COM-03 复审10 §3.2: 等待超时抢占——仅从 NOT_STARTED 原子转为 CANCELLED。
     * 不覆盖已打开的 STREAMING（onOpen 赢家继续持有流）；
     * 已终态（HTTP_FAILED/TERMINATED/CANCELLED）返回 false，由对应赢家负责结果。
     */
    public boolean tryAbortBeforeOpen() {
        return state.compareAndSet(State.NOT_STARTED, State.CANCELLED);
    }

    /**
     * 是否已进入任何终态。
     */
    public boolean isTerminal() {
        State s = state.get();
        return s == State.HTTP_FAILED || s == State.TERMINATED || s == State.CANCELLED;
    }
}
