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

import java.util.Set;

/**
 * ModelServiceReq 单元测试，重点验证核心必填字段（provider_id/service_name/model_name/model_type/
 * api_url/interface_protocol）的 @NotNull 约束行为，确保创建/更新模型服务时缺字段在参数层被拦截。
 */
class ModelServiceReqTest {

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

    private static ModelServiceReq buildValidReq() {
        return new ModelServiceReq()
            .setProviderId("provider_001")
            .setServiceName("my-service")
            .setModelName("gpt-4")
            .setModelType("LLM")
            .setApiUrl("https://api.example.com/v1")
            .setInterfaceProtocol("OpenAI");
    }

    private static boolean hasViolation(Set<ConstraintViolation<ModelServiceReq>> violations, String property) {
        return violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals(property));
    }

    /**
     * 用例描述：providerId 为 null 时，@NotNull 校验应失败
     * 预制条件：其余核心必填字段均为有效值，providerId 保持默认 null
     * 输入参数：providerId=null
     * 预期结果：存在针对 providerId 字段的校验违规
     */
    @Test
    void testProviderId_Null_ShouldFailValidation() {
        ModelServiceReq req = buildValidReq().setProviderId(null);

        Set<ConstraintViolation<ModelServiceReq>> violations = validator.validate(req);

        assertFalse(violations.isEmpty(), "providerId 为 null 时应有校验违规");
        assertTrue(hasViolation(violations, "providerId"), "应存在 providerId 字段的校验违规");
    }

    /**
     * 用例描述：serviceName 为 null 时，@NotNull 校验应失败
     * 预制条件：其余核心必填字段均为有效值，serviceName 保持默认 null
     * 输入参数：serviceName=null
     * 预期结果：存在针对 serviceName 字段的校验违规
     */
    @Test
    void testServiceName_Null_ShouldFailValidation() {
        ModelServiceReq req = buildValidReq().setServiceName(null);

        Set<ConstraintViolation<ModelServiceReq>> violations = validator.validate(req);

        assertFalse(violations.isEmpty(), "serviceName 为 null 时应有校验违规");
        assertTrue(hasViolation(violations, "serviceName"), "应存在 serviceName 字段的校验违规");
    }

    /**
     * 用例描述：modelName 为 null 时，@NotNull 校验应失败
     * 预制条件：其余核心必填字段均为有效值，modelName 保持默认 null
     * 输入参数：modelName=null
     * 预期结果：存在针对 modelName 字段的校验违规
     */
    @Test
    void testModelName_Null_ShouldFailValidation() {
        ModelServiceReq req = buildValidReq().setModelName(null);

        Set<ConstraintViolation<ModelServiceReq>> violations = validator.validate(req);

        assertFalse(violations.isEmpty(), "modelName 为 null 时应有校验违规");
        assertTrue(hasViolation(violations, "modelName"), "应存在 modelName 字段的校验违规");
    }

    /**
     * 用例描述：modelType 为 null 时，@NotNull 校验应失败
     * 预制条件：其余核心必填字段均为有效值，modelType 保持默认 null
     * 输入参数：modelType=null
     * 预期结果：存在针对 modelType 字段的校验违规
     */
    @Test
    void testModelType_Null_ShouldFailValidation() {
        ModelServiceReq req = buildValidReq().setModelType(null);

        Set<ConstraintViolation<ModelServiceReq>> violations = validator.validate(req);

        assertFalse(violations.isEmpty(), "modelType 为 null 时应有校验违规");
        assertTrue(hasViolation(violations, "modelType"), "应存在 modelType 字段的校验违规");
    }

    /**
     * 用例描述：apiUrl 为 null 时，@NotNull 校验应失败
     * 预制条件：其余核心必填字段均为有效值，apiUrl 保持默认 null
     * 输入参数：apiUrl=null
     * 预期结果：存在针对 apiUrl 字段的校验违规
     */
    @Test
    void testApiUrl_Null_ShouldFailValidation() {
        ModelServiceReq req = buildValidReq().setApiUrl(null);

        Set<ConstraintViolation<ModelServiceReq>> violations = validator.validate(req);

        assertFalse(violations.isEmpty(), "apiUrl 为 null 时应有校验违规");
        assertTrue(hasViolation(violations, "apiUrl"), "应存在 apiUrl 字段的校验违规");
    }

    /**
     * 用例描述：interfaceProtocol 为 null 时，@NotNull 校验应失败
     * 预制条件：其余核心必填字段均为有效值，interfaceProtocol 保持默认 null
     * 输入参数：interfaceProtocol=null
     * 预期结果：存在针对 interfaceProtocol 字段的校验违规
     */
    @Test
    void testInterfaceProtocol_Null_ShouldFailValidation() {
        ModelServiceReq req = buildValidReq().setInterfaceProtocol(null);

        Set<ConstraintViolation<ModelServiceReq>> violations = validator.validate(req);

        assertFalse(violations.isEmpty(), "interfaceProtocol 为 null 时应有校验违规");
        assertTrue(hasViolation(violations, "interfaceProtocol"), "应存在 interfaceProtocol 字段的校验违规");
    }

    /**
     * 用例描述：全部核心必填字段均为有效值时，校验应通过（无任何违规）
     * 预制条件：构造含全部核心必填字段有效值的 ModelServiceReq
     * 输入参数：providerId/serviceName/modelName/modelType/apiUrl/interfaceProtocol 均为有效值
     * 预期结果：不存在任何校验违规
     */
    @Test
    void testAllRequiredFields_Valid_ShouldPassValidation() {
        ModelServiceReq req = buildValidReq();

        Set<ConstraintViolation<ModelServiceReq>> violations = validator.validate(req);

        assertTrue(violations.isEmpty(), "全部核心必填字段有效时不应有校验违规");
    }

    /**
     * 用例描述：全部字段为 null（空 DTO）时，6 个核心必填字段应全部触发 @NotNull 违规
     * 预制条件：创建不设置任何字段的 ModelServiceReq
     * 输入参数：全部字段为 null
     * 预期结果：存在 6 个核心字段的校验违规，且无其他字段违规
     */
    @Test
    void testAllFields_Null_ShouldFailAllRequired() {
        ModelServiceReq req = new ModelServiceReq();

        Set<ConstraintViolation<ModelServiceReq>> violations = validator.validate(req);

        assertEquals(6, violations.size(), "空 DTO 应恰好触发 6 个核心字段的校验违规");
        assertTrue(hasViolation(violations, "providerId"));
        assertTrue(hasViolation(violations, "serviceName"));
        assertTrue(hasViolation(violations, "modelName"));
        assertTrue(hasViolation(violations, "modelType"));
        assertTrue(hasViolation(violations, "apiUrl"));
        assertTrue(hasViolation(violations, "interfaceProtocol"));
    }
}
