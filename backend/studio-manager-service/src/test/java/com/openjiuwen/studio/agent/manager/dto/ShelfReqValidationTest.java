/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.dto;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;

import java.util.Set;

import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * #1731：上架分类 DTO 长度/格式校验 UT。
 * 覆盖边界：
 * - C 点：SkillShelfReq.tagId 非法 UUID 格式（含非十六进制字符）→ @Pattern 拦
 * - D 点：SkillShelfReq.tagId 65 位 → @Size(max=36) 拦
 * - E 点：PluginShelfReq.category 37 位 → @Size(max=36) 拦（修复前 max=64 放行致 DB 500）
 * - 正向：合法 36 位 UUID 通过
 */
class ShelfReqValidationTest {

    private static ValidatorFactory factory;
    private static Validator validator;

    /** 36 位合法 UUID（a1020002 系列，dml.sql 中 library_type='skill' 的真实数据） */
    private static final String VALID_SKILL_TAG = "a1020002-0000-4000-8000-000000000001";

    @BeforeAll
    static void setUp() {
        factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
    }

    @AfterAll
    static void tearDown() {
        if (factory != null) {
            factory.close();
        }
    }

    @Test
    void skillShelfReq_ValidTagId_Pass() {
        SkillShelfReq req = new SkillShelfReq().setTagId(VALID_SKILL_TAG);
        Set<ConstraintViolation<SkillShelfReq>> violations = validator.validate(req);
        assertTrue(violations.isEmpty(), "合法 36 位 UUID 应通过校验，违规: " + violations);
    }

    /** C 点：硬编码非法 ID（含 s/t/x 等非十六进制字符）被 @Pattern 拦 */
    @Test
    void skillShelfReq_InvalidUuidFormat_Rejected() {
        SkillShelfReq req = new SkillShelfReq().setTagId("dsa79d76-c26a-4dad-92s7-a46dcs2271eb");
        Set<ConstraintViolation<SkillShelfReq>> violations = validator.validate(req);
        assertTrue(violations.stream().anyMatch(v -> v.getMessage().contains("valid UUID")),
            "非法 UUID 格式应被 @Pattern 拦");
    }

    /** D 点：65 位 tagId 被 @Size(max=36) 拦（修复前 max=64 放行；65 位也非合法 UUID，@Size 与 @Pattern 双拦） */
    @Test
    void skillShelfReq_TagIdTooLong65_Rejected() {
        SkillShelfReq req = new SkillShelfReq().setTagId("1234567890123456789012345678901234567890"
            + "1234567890123456789012345"); // 65 位
        Set<ConstraintViolation<SkillShelfReq>> violations = validator.validate(req);
        assertTrue(violations.stream().anyMatch(v -> v.getMessage().contains("36")),
            "65 位 tagId 应被 @Size(max=36) 拦");
    }

    /** E 点核心复现：37 位 category 被 @Size(max=36) 拦（修复前 max=64 放行 → DB VARCHAR(36) 抛 500） */
    @Test
    void pluginShelfReq_Category37Chars_Rejected() {
        PluginShelfReq req = new PluginShelfReq().setCategory("1234567890123456789012345678901234567"); // 37 位
        Set<ConstraintViolation<PluginShelfReq>> violations = validator.validate(req);
        assertTrue(violations.stream().anyMatch(v -> v.getMessage().contains("36")),
            "37 位 category 应被 @Size(max=36) 拦");
    }

    @Test
    void pluginShelfReq_ValidCategory_Pass() {
        PluginShelfReq req = new PluginShelfReq().setCategory("a1020001-0000-4000-8000-000000000001");
        Set<ConstraintViolation<PluginShelfReq>> violations = validator.validate(req);
        assertTrue(violations.isEmpty(), "合法 36 位 UUID category 应通过，违规: " + violations);
    }

    @Test
    void mcpServerShelfReq_InvalidUuidCategory_Rejected() {
        McpServerShelfReq req = new McpServerShelfReq()
            .setServiceId("svc-001")
            .setCategory("not-a-uuid");
        Set<ConstraintViolation<McpServerShelfReq>> violations = validator.validate(req);
        assertTrue(violations.stream().anyMatch(v -> v.getMessage().contains("valid UUID")),
            "非法 UUID category 应被 @Pattern 拦");
    }

    @Test
    void mcpServerShelfReq_37CharsCategory_Rejected() {
        McpServerShelfReq req = new McpServerShelfReq()
            .setServiceId("svc-001")
            .setCategory("1234567890123456789012345678901234567"); // 37 位
        Set<ConstraintViolation<McpServerShelfReq>> violations = validator.validate(req);
        assertTrue(violations.stream().anyMatch(v -> v.getMessage().contains("36")),
            "37 位 category 应被 @Size(max=36) 拦");
    }
}
