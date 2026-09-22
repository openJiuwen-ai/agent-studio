/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.dto.nl;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;

import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;

/**
 * NLChatReq 单元测试，重点验证 model 字段 @NotNull/@Size(max=10) 与 query 字段 @NotNull 的校验约束。
 */
class NLChatReqTest {

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

    @Test
    void testModelNullShouldFailValidation() {
        NLChatReq req = new NLChatReq();
        req.setQuery("hello");
        req.setModel(null);

        Set<ConstraintViolation<NLChatReq>> violations = validator.validate(req);

        assertFalse(violations.isEmpty(), "model 为 null 时应有校验违规");
        boolean hasModelViolation = violations.stream()
            .anyMatch(v -> v.getPropertyPath().toString().equals("model"));
        assertTrue(hasModelViolation, "应存在 model 字段的校验违规");
    }

    @Test
    void testModelValidShouldPassValidation() {
        NLChatReq req = new NLChatReq();
        req.setQuery("hello");
        Map<String, Object> model = new HashMap<>();
        model.put("modelName", "gpt-4o");
        req.setModel(model);

        Set<ConstraintViolation<NLChatReq>> violations = validator.validate(req);

        boolean hasModelViolation = violations.stream()
            .anyMatch(v -> v.getPropertyPath().toString().equals("model"));
        assertFalse(hasModelViolation, "model 有效时不应有校验违规");
    }

    @Test
    void testModelSizeExceedShouldFailValidation() {
        NLChatReq req = new NLChatReq();
        req.setQuery("hello");
        Map<String, Object> model = new HashMap<>();
        for (int i = 0; i < 11; i++) {
            model.put("key" + i, "value" + i);
        }
        req.setModel(model);

        Set<ConstraintViolation<NLChatReq>> violations = validator.validate(req);

        boolean hasModelViolation = violations.stream()
            .anyMatch(v -> v.getPropertyPath().toString().equals("model"));
        assertTrue(hasModelViolation, "model 超过 10 个键时应有校验违规");
    }

    @Test
    void testQueryNullShouldFailValidation() {
        NLChatReq req = new NLChatReq();
        Map<String, Object> model = new HashMap<>();
        model.put("modelName", "gpt-4o");
        req.setModel(model);
        req.setQuery(null);

        Set<ConstraintViolation<NLChatReq>> violations = validator.validate(req);

        boolean hasQueryViolation = violations.stream()
            .anyMatch(v -> v.getPropertyPath().toString().equals("query"));
        assertTrue(hasQueryViolation, "query 为 null 时应有校验违规");
    }
}
