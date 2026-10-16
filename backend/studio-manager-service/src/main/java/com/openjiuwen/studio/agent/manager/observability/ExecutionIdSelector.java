/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import java.util.UUID;
import java.util.function.Supplier;

/**
 * Manager 统一 execution ID 选择器（DEF-02 §3.2 / §4.1）。
 *
 * <p>纯组件：无 MDC、无 HTTP、无 Redis 副作用，只接收候选值并返回不可变结果。不抛
 * {@code AgentStudioException}、不依赖 {@code StudioError}；恢复值非空但非法时返回
 * {@link Result.Status#RESTORE_ILLEGAL}，由调用方映射为 {@code CALL_RUNTIME_ERROR}。
 *
 * <p>唯一选择顺序（冻结优先级）：
 * <ol>
 *   <li>恢复值非空：合法 → 使用恢复值（{@link Source#RESTORED}）；非空非法 →
 *       {@link Result.Status#RESTORE_ILLEGAL}，不继续降级、不生成 UUID；</li>
 *   <li>合法的内部 executionId 存在 → 使用内部值（{@link Source#INTERNAL}）；内部值非空非法时跳过；</li>
 *   <li>合法的入站 X-Execution-Id 存在 → 使用 Header 值（{@link Source#HEADER}）；Header 非空非法时跳过；</li>
 *   <li>否则生成新 UUID（{@link Source#GENERATED}）。</li>
 * </ol>
 *
 * <p>空值（{@code null} 或空串）视为"来源不存在"，非空但不合法才是"非法"。内部/Header 非法时
 * 不得截断、修正或回显，只跳过。UUID 生成器允许在单测中注入，避免对随机结果做模糊断言。
 *
 * <p>结果对象不携带非法候选原值，来源/状态只供低基数诊断使用，不得把 execution ID 放入 Metrics 属性。
 */
public final class ExecutionIdSelector {

    /** 选定值的来源（低基数诊断用）。 */
    public enum Source {
        RESTORED,
        INTERNAL,
        HEADER,
        GENERATED
    }

    /**
     * 不可变选择结果。成功结果含 {@code value} 与 {@code source}；失败结果
     * （{@link Status#RESTORE_ILLEGAL}）不含原值。
     */
    public static final class Result {

        /** 结果状态。 */
        public enum Status {
            SELECTED,
            RESTORE_ILLEGAL
        }

        private final Status status;
        private final String value;
        private final Source source;

        private Result(Status status, String value, Source source) {
            this.status = status;
            this.value = value;
            this.source = source;
        }

        static Result selected(String value, Source source) {
            return new Result(Status.SELECTED, value, source);
        }

        static Result restoreIllegal() {
            return new Result(Status.RESTORE_ILLEGAL, null, null);
        }

        public Status getStatus() {
            return status;
        }

        /** 成功结果返回选定值；{@code RESTORE_ILLEGAL} 返回 {@code null}。 */
        public String getValue() {
            return value;
        }

        /** 成功结果返回来源；{@code RESTORE_ILLEGAL} 返回 {@code null}。 */
        public Source getSource() {
            return source;
        }

        public boolean isRestoreIllegal() {
            return status == Status.RESTORE_ILLEGAL;
        }

        public boolean isSelected() {
            return status == Status.SELECTED;
        }
    }

    private final Supplier<String> uuidGenerator;

    /** 默认使用 {@link UUID#randomUUID()}。 */
    public ExecutionIdSelector() {
        this(() -> UUID.randomUUID().toString());
    }

    /**
     * 注入 UUID 生成器供单测固定生成值。
     *
     * @param uuidGenerator 返回合法 UUID 字符串的供应者
     */
    public ExecutionIdSelector(Supplier<String> uuidGenerator) {
        this.uuidGenerator = uuidGenerator;
    }

    /**
     * 按四级优先级选择 execution ID。
     *
     * @param restored  恢复记录值（来自 Redis 查询），空表示记录不存在
     * @param internal  执行参数中已选定的 executionId，空表示无内部值
     * @param header    入站 {@code X-Execution-Id}，空表示无 Header
     * @return 不可变结果；恢复值非空非法时返回 {@code RESTORE_ILLEGAL}，否则返回选定值与来源
     */
    public Result select(String restored, String internal, String header) {
        // 恢复值非空：合法→使用，非法→明确失败，不继续降级
        if (isPresent(restored)) {
            if (!CorrelationIdValidator.isValid(restored)) {
                return Result.restoreIllegal();
            }
            return Result.selected(restored, Source.RESTORED);
        }
        if (isPresent(internal) && CorrelationIdValidator.isValid(internal)) {
            return Result.selected(internal, Source.INTERNAL);
        }
        if (isPresent(header) && CorrelationIdValidator.isValid(header)) {
            return Result.selected(header, Source.HEADER);
        }
        return Result.selected(uuidGenerator.get(), Source.GENERATED);
    }

    private static boolean isPresent(String value) {
        return value != null && !value.isEmpty();
    }
}
