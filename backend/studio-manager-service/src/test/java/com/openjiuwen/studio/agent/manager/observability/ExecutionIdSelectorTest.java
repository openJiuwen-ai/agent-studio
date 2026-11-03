/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import org.junit.jupiter.api.Test;

import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * DEF-02 §3.2 / §6.1：execution ID 选择器四级优先级、边界与恢复非法失败测试。
 */
class ExecutionIdSelectorTest {

    private static final String LEGAL = "exec-1.2_3:4-5";
    private static final String ILLEGAL = "bad value"; // 含空格
    private static final String FIXED_UUID = "gen-uuid-fixed";

    private final ExecutionIdSelector selector = new ExecutionIdSelector(() -> FIXED_UUID);

    // ---- 四个来源分别命中 ----

    @Test
    void restoredLegal_usesRestored() {
        ExecutionIdSelector.Result r = selector.select(LEGAL, "internal-x", "header-x");
        assertThat(r.isSelected()).isTrue();
        assertThat(r.getValue()).isEqualTo(LEGAL);
        assertThat(r.getSource()).isEqualTo(ExecutionIdSelector.Source.RESTORED);
    }

    @Test
    void restoredAbsent_internalLegal_usesInternal() {
        ExecutionIdSelector.Result r = selector.select(null, LEGAL, "header-x");
        assertThat(r.getSource()).isEqualTo(ExecutionIdSelector.Source.INTERNAL);
        assertThat(r.getValue()).isEqualTo(LEGAL);
    }

    @Test
    void restoredAndInternalAbsent_headerLegal_usesHeader() {
        ExecutionIdSelector.Result r = selector.select(null, null, LEGAL);
        assertThat(r.getSource()).isEqualTo(ExecutionIdSelector.Source.HEADER);
        assertThat(r.getValue()).isEqualTo(LEGAL);
    }

    @Test
    void allAbsent_generatesUuid() {
        ExecutionIdSelector.Result r = selector.select(null, null, null);
        assertThat(r.getSource()).isEqualTo(ExecutionIdSelector.Source.GENERATED);
        assertThat(r.getValue()).isEqualTo(FIXED_UUID);
    }

    // ---- 完整优先级组合 ----

    @Test
    void allLegal_priorityIsRestored() {
        ExecutionIdSelector.Result r = selector.select(LEGAL, "i2", "h2");
        assertThat(r.getSource()).isEqualTo(ExecutionIdSelector.Source.RESTORED);
    }

    @Test
    void internalBeforeHeader() {
        ExecutionIdSelector.Result r = selector.select(null, LEGAL, "h2");
        assertThat(r.getSource()).isEqualTo(ExecutionIdSelector.Source.INTERNAL);
    }

    // ---- 恢复值非空非法：明确失败，不降级、不生成 UUID ----

    @Test
    void restoredNonEmptyIllegal_returnsRestoreIllegal() {
        AtomicInteger uuidCalls = new AtomicInteger();
        ExecutionIdSelector s = new ExecutionIdSelector(() -> {
            uuidCalls.incrementAndGet();
            return FIXED_UUID;
        });
        ExecutionIdSelector.Result r = s.select(ILLEGAL, LEGAL, LEGAL);
        assertThat(r.isRestoreIllegal()).isTrue();
        assertThat(r.getValue()).isNull();
        assertThat(r.getSource()).isNull();
        // 不继续降级、不生成 UUID
        assertThat(uuidCalls.get()).isZero();
    }

    @Test
    void restoredEmptyString_treatedAsAbsent_notIllegal() {
        // 空串视为来源不存在，不是非法
        ExecutionIdSelector.Result r = selector.select("", LEGAL, null);
        assertThat(r.getSource()).isEqualTo(ExecutionIdSelector.Source.INTERNAL);
    }

    // ---- 内部/Header 非法时跳过 ----

    @Test
    void internalNonEmptyIllegal_skipsToLegalHeader() {
        ExecutionIdSelector.Result r = selector.select(null, ILLEGAL, LEGAL);
        assertThat(r.getSource()).isEqualTo(ExecutionIdSelector.Source.HEADER);
        assertThat(r.getValue()).isEqualTo(LEGAL);
    }

    @Test
    void internalAndHeaderBothIllegal_generatesUuid() {
        AtomicInteger uuidCalls = new AtomicInteger();
        ExecutionIdSelector s = new ExecutionIdSelector(() -> {
            uuidCalls.incrementAndGet();
            return FIXED_UUID;
        });
        ExecutionIdSelector.Result r = s.select(null, ILLEGAL, ILLEGAL);
        assertThat(r.getSource()).isEqualTo(ExecutionIdSelector.Source.GENERATED);
        assertThat(uuidCalls.get()).isEqualTo(1);
    }

    @Test
    void internalEmptyString_skippedAsAbsent() {
        ExecutionIdSelector.Result r = selector.select(null, "", LEGAL);
        assertThat(r.getSource()).isEqualTo(ExecutionIdSelector.Source.HEADER);
    }

    // ---- 生成结果只生成一次且为注入值 ----

    @Test
    void generated_isInjectedValue_andGeneratedOnce() {
        AtomicInteger uuidCalls = new AtomicInteger();
        ExecutionIdSelector s = new ExecutionIdSelector(() -> {
            uuidCalls.incrementAndGet();
            return FIXED_UUID;
        });
        ExecutionIdSelector.Result r = s.select(null, null, null);
        assertThat(r.getValue()).isEqualTo(FIXED_UUID);
        assertThat(uuidCalls.get()).isEqualTo(1);
    }

    @Test
    void defaultSelector_generatesLegalUuid() {
        ExecutionIdSelector defaultSelector = new ExecutionIdSelector();
        ExecutionIdSelector.Result r = defaultSelector.select(null, null, null);
        assertThat(r.getSource()).isEqualTo(ExecutionIdSelector.Source.GENERATED);
        assertThat(CorrelationIdValidator.isValid(r.getValue())).isTrue();
    }

    // ---- 结果不携带非法原值 ----

    @Test
    void restoreIllegalResult_doesNotCarryRawValue() {
        ExecutionIdSelector.Result r = selector.select("secret bad value", null, null);
        assertThat(r.isRestoreIllegal()).isTrue();
        assertThat(r.getValue()).isNull();
        assertThat(r.toString()).doesNotContain("secret");
    }
}
