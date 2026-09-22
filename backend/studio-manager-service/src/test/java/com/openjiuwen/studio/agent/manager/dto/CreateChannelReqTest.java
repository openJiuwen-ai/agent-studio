/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.dto;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
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
 * CreateChannelReq 单元测试，重点验证 @NotBlank 校验注解对 versionId 和 channelType 的约束。
 */
class CreateChannelReqTest {

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

    /**
     * 用例描述：versionId 为空字符串时，@NotBlank 校验应失败
     * 预制条件：创建 CreateChannelReq，versionId 设为空字符串，channelType 设为有效值
     * 输入参数：versionId="", channelType="WEB"
     * 预期结果：存在针对 versionId 字段的 @NotBlank 校验违规
     */
    @Test
    void testVersionId_Blank_ShouldFailValidation() {
        CreateChannelReq req = new CreateChannelReq();
        req.setVersionId("");
        req.setChannelType("WEB");

        Set<ConstraintViolation<CreateChannelReq>> violations = validator.validate(req);

        assertFalse(violations.isEmpty(), "versionId 为空时应有校验违规");
        boolean hasVersionIdViolation = violations.stream()
            .anyMatch(v -> v.getPropertyPath().toString().equals("versionId"));
        assertTrue(hasVersionIdViolation, "应存在 versionId 字段的校验违规");
    }

    /**
     * 用例描述：versionId 为 null 时，@NotBlank 校验应失败
     * 预制条件：创建 CreateChannelReq，versionId 保持默认 null，channelType 设为有效值
     * 输入参数：versionId=null, channelType="WEB"
     * 预期结果：存在针对 versionId 字段的 @NotBlank 校验违规
     */
    @Test
    void testVersionId_Null_ShouldFailValidation() {
        CreateChannelReq req = new CreateChannelReq();
        req.setVersionId(null);
        req.setChannelType("WEB");

        Set<ConstraintViolation<CreateChannelReq>> violations = validator.validate(req);

        assertFalse(violations.isEmpty(), "versionId 为 null 时应有校验违规");
        boolean hasVersionIdViolation = violations.stream()
            .anyMatch(v -> v.getPropertyPath().toString().equals("versionId"));
        assertTrue(hasVersionIdViolation, "应存在 versionId 字段的校验违规");
    }

    /**
     * 用例描述：versionId 为空白字符串（仅空格）时，@NotBlank 校验应失败
     * 预制条件：创建 CreateChannelReq，versionId 设为纯空格字符串，channelType 设为有效值
     * 输入参数：versionId="   ", channelType="WEB"
     * 预期结果：存在针对 versionId 字段的 @NotBlank 校验违规
     */
    @Test
    void testVersionId_Whitespace_ShouldFailValidation() {
        CreateChannelReq req = new CreateChannelReq();
        req.setVersionId("   ");
        req.setChannelType("WEB");

        Set<ConstraintViolation<CreateChannelReq>> violations = validator.validate(req);

        assertFalse(violations.isEmpty(), "versionId 为纯空格时应有校验违规");
        boolean hasVersionIdViolation = violations.stream()
            .anyMatch(v -> v.getPropertyPath().toString().equals("versionId"));
        assertTrue(hasVersionIdViolation, "应存在 versionId 字段的校验违规");
    }

    /**
     * 用例描述：versionId 和 channelType 均为有效非空值时，校验应通过（无 versionId/channelType 违规）
     * 预制条件：创建 CreateChannelReq，versionId 和 channelType 设为有效值
     * 输入参数：versionId="v1.0", channelType="WEB"
     * 预期结果：不存在针对 versionId 和 channelType 字段的校验违规
     */
    @Test
    void testVersionId_Valid_ShouldPassValidation() {
        CreateChannelReq req = new CreateChannelReq();
        req.setVersionId("v1.0");
        req.setChannelType("WEB");

        Set<ConstraintViolation<CreateChannelReq>> violations = validator.validate(req);

        boolean hasVersionIdViolation = violations.stream()
            .anyMatch(v -> v.getPropertyPath().toString().equals("versionId"));
        boolean hasChannelTypeViolation = violations.stream()
            .anyMatch(v -> v.getPropertyPath().toString().equals("channelType"));
        assertFalse(hasVersionIdViolation, "versionId 有效时不应有校验违规");
        assertFalse(hasChannelTypeViolation, "channelType 有效时不应有校验违规");
    }

    /**
     * 用例描述：channelType 为空时，@NotBlank 校验应失败
     * 预制条件：创建 CreateChannelReq，versionId 设为有效值，channelType 设为空字符串
     * 输入参数：versionId="v1.0", channelType=""
     * 预期结果：存在针对 channelType 字段的 @NotBlank 校验违规
     */
    @Test
    void testChannelType_Blank_ShouldFailValidation() {
        CreateChannelReq req = new CreateChannelReq();
        req.setVersionId("v1.0");
        req.setChannelType("");

        Set<ConstraintViolation<CreateChannelReq>> violations = validator.validate(req);

        assertFalse(violations.isEmpty(), "channelType 为空时应有校验违规");
        boolean hasChannelTypeViolation = violations.stream()
            .anyMatch(v -> v.getPropertyPath().toString().equals("channelType"));
        assertTrue(hasChannelTypeViolation, "应存在 channelType 字段的校验违规");
    }

    /**
     * 用例描述：CreateChannelReq 的 setter 返回 this（链式调用），getter 正常返回值
     * 预制条件：无
     * 输入参数：versionId="v1.0", channelType="WEB"
     * 预期结果：链式 setter 返回自身，getter 返回设置的值
     */
    @Test
    void testSetterChainAndGetter() {
        CreateChannelReq req = new CreateChannelReq()
            .setVersionId("v1.0")
            .setChannelType("WEB");

        assertNotNull(req);
        assertEquals("v1.0", req.getVersionId());
        assertEquals("WEB", req.getChannelType());
    }
}
