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

    /** 巡检1：空串/纯空白=缺省沿用既有分类，DTO 须放行（与 Service 层 isBlank 口径一致），不被 @Pattern 拒 400 */
    @Test
    void skillShelfReq_BlankTagId_Pass() {
        // null（前端不传字段）—— jakarta @Pattern 对 null 不校验，放行
        assertTrue(validator.validate(new SkillShelfReq().setTagId(null)).isEmpty());
        // 空串（API 直接调用方传 {"tag_id":""}）
        assertTrue(validator.validate(new SkillShelfReq().setTagId("")).isEmpty(),
            "空串=缺省应放行，不应被 @Pattern 拒");
        // 纯空白串（{"tag_id":"   "}，Service 层 isBlank 也判缺省）
        assertTrue(validator.validate(new SkillShelfReq().setTagId("   ")).isEmpty(),
            "纯空白=缺省应放行，与 Service 层 isBlank 口径一致");
    }

    /** 巡检1：Plugin category 空串/纯空白同样放行，保持可选字段传空即保持既有分类语义 */
    @Test
    void pluginShelfReq_BlankCategory_Pass() {
        assertTrue(validator.validate(new PluginShelfReq().setCategory(null)).isEmpty());
        assertTrue(validator.validate(new PluginShelfReq().setCategory("")).isEmpty(),
            "空串=缺省应放行");
        assertTrue(validator.validate(new PluginShelfReq().setCategory("  ")).isEmpty(),
            "纯空白=缺省应放行");
    }

    /** 巡检1：MCP category 空串/纯空白同样放行 */
    @Test
    void mcpServerShelfReq_BlankCategory_Pass() {
        McpServerShelfReq req = new McpServerShelfReq().setServiceId("svc-001");
        assertTrue(validator.validate(new McpServerShelfReq().setServiceId("svc-001").setCategory(null)).isEmpty());
        assertTrue(validator.validate(new McpServerShelfReq().setServiceId("svc-001").setCategory("")).isEmpty(),
            "空串=缺省应放行");
        assertTrue(validator.validate(new McpServerShelfReq().setServiceId("svc-001").setCategory("\t")).isEmpty(),
            "纯空白=缺省应放行");
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
