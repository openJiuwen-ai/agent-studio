/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * DEF-02 §3.1 / §6.1：统一关联 ID 合法性规则边界测试。
 */
class CorrelationIdValidatorTest {

    @Test
    void null_isInvalid() {
        assertThat(CorrelationIdValidator.isValid(null)).isFalse();
    }

    @Test
    void empty_isInvalid() {
        assertThat(CorrelationIdValidator.isValid("")).isFalse();
    }

    @Test
    void singleChar_isValid() {
        assertThat(CorrelationIdValidator.isValid("a")).isTrue();
    }

    @Test
    void allLegalChars_areValid() {
        assertThat(CorrelationIdValidator.isValid("a.b_c:d-e")).isTrue();
    }

    @Test
    void length64_isValid() {
        String value = "a".repeat(64);
        assertThat(CorrelationIdValidator.isValid(value)).isTrue();
    }

    @Test
    void length65_isInvalid() {
        String value = "a".repeat(65);
        assertThat(CorrelationIdValidator.isValid(value)).isFalse();
    }

    @Test
    void whitespace_isInvalid() {
        assertThat(CorrelationIdValidator.isValid("a b")).isFalse();
    }

    @Test
    void tab_isInvalid() {
        assertThat(CorrelationIdValidator.isValid("a\tb")).isFalse();
    }

    @Test
    void newline_isInvalid() {
        assertThat(CorrelationIdValidator.isValid("a\nb")).isFalse();
    }

    @Test
    void controlChar_isInvalid() {
        assertThat(CorrelationIdValidator.isValid("ab")).isFalse();
    }

    @Test
    void illegalChar_isInvalid() {
        assertThat(CorrelationIdValidator.isValid("a@b")).isFalse();
    }

    @Test
    void slash_isInvalid() {
        assertThat(CorrelationIdValidator.isValid("a/b")).isFalse();
    }
}
