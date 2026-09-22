/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.dto;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;

import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * CreateMemoryRepoRequestBody 单元测试，验证 long_term_memory_strategies 的
 * @NotNull/@Size(min=1) 与元素 type 的 @NotNull 级联校验行为。
 */
class CreateMemoryRepoRequestBodyTest {

    private static ValidatorFactory validatorFactory;

    private static Validator validator;

    @BeforeAll
    static void setUpValidator() {
        validatorFactory = Validation.buildDefaultValidatorFactory();
        validator = validatorFactory.getValidator();
    }

    @AfterAll
    static void tearDownValidator() {
        if (validatorFactory != null) {
            validatorFactory.close();
        }
    }

    private static LongTermMemoryStrategy buildStrategy() {
        return new LongTermMemoryStrategy()
            .setType(LongTermMemoryStrategy.TypeEnum.SEMANTIC_MEMORY)
            .setPrompt("test_prompt");
    }

    /**
     * 用例描述：long_term_memory_strategies 为 null 时，@NotNull 校验应失败
     * 预制条件：name 有效，strategies 保持默认 null
     * 输入参数：long_term_memory_strategies=null
     * 预期结果：存在针对 longTermMemoryStrategies 字段的校验违规
     */
    @Test
    void testStrategies_Null_ShouldFailValidation() {
        CreateMemoryRepoRequestBody req = new CreateMemoryRepoRequestBody().setName("test_name");

        Set<ConstraintViolation<CreateMemoryRepoRequestBody>> violations = validator.validate(req);

        assertFalse(violations.isEmpty(), "strategies 为 null 时应有校验违规");
        assertTrue(hasViolation(violations, "longTermMemoryStrategies"));
    }

    /**
     * 用例描述：long_term_memory_strategies 为空数组时，@Size(min=1) 校验应失败
     * 预制条件：name 有效，strategies 为空数组
     * 输入参数：long_term_memory_strategies=[]
     * 预期结果：存在针对 longTermMemoryStrategies 字段的校验违规
     */
    @Test
    void testStrategies_Empty_ShouldFailValidation() {
        CreateMemoryRepoRequestBody req = new CreateMemoryRepoRequestBody()
            .setName("test_name")
            .setLongTermMemoryStrategies(new ArrayList<>());

        Set<ConstraintViolation<CreateMemoryRepoRequestBody>> violations = validator.validate(req);

        assertFalse(violations.isEmpty(), "strategies 为空数组时应有校验违规");
        assertTrue(hasViolation(violations, "longTermMemoryStrategies"));
    }

    /**
     * 用例描述：策略元素 type 为 null 时，@Valid 级联的 @NotNull 校验应失败
     * 预制条件：name 有效，strategies 含一个 type 为 null 的策略
     * 输入参数：策略元素 type=null
     * 预期结果：存在针对 longTermMemoryStrategies[].type 路径的校验违规
     */
    @Test
    void testStrategyType_Null_ShouldFailValidation() {
        LongTermMemoryStrategy strategy = buildStrategy().setType(null);
        CreateMemoryRepoRequestBody req = new CreateMemoryRepoRequestBody()
            .setName("test_name")
            .setLongTermMemoryStrategies(List.of(strategy));

        Set<ConstraintViolation<CreateMemoryRepoRequestBody>> violations = validator.validate(req);

        assertFalse(violations.isEmpty(), "策略 type 为 null 时应有校验违规");
        assertTrue(violations.stream().anyMatch(
            v -> v.getPropertyPath().toString().contains("longTermMemoryStrategies") && v.getPropertyPath().toString()
                .contains("type")));
    }

    /**
     * 用例描述：name 与 strategies 均有效时，校验应通过
     * 预制条件：name 有效，strategies 含一个完整策略
     * 输入参数：正常请求体
     * 预期结果：不存在任何校验违规
     */
    @Test
    void testValidBody_ShouldPassValidation() {
        CreateMemoryRepoRequestBody req = new CreateMemoryRepoRequestBody()
            .setName("test_name")
            .setLongTermMemoryStrategies(List.of(buildStrategy()));

        Set<ConstraintViolation<CreateMemoryRepoRequestBody>> violations = validator.validate(req);

        assertTrue(violations.isEmpty(), "合法请求体不应有校验违规");
    }

    private static boolean hasViolation(Set<ConstraintViolation<CreateMemoryRepoRequestBody>> violations,
        String property) {
        return violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals(property));
    }
}
