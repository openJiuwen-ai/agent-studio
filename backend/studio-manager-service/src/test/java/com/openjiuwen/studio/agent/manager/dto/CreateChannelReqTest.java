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

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * CreateChannelReq 单元测试，重点验证 versionId 可空（@NotBlank 已移除，缺失场景由业务层校验兜底）
 * 与 channelType 的 @NotBlank 约束行为。
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
     * 用例描述：versionId 为空字符串时不再触发校验违规（@NotBlank 已移除，versionId 可空）
     * 预制条件：创建 CreateChannelReq，versionId 设为空字符串，channelType 设为有效值
     * 输入参数：versionId="", channelType="WEB"
     * 预期结果：不存在针对 versionId 字段的校验违规
     */
    @Test
    void testVersionId_Blank_ShouldPassValidation() {
        CreateChannelReq req = new CreateChannelReq();
        req.setVersionId("");
        req.setChannelType("WEB");

        Set<ConstraintViolation<CreateChannelReq>> violations = validator.validate(req);

        boolean hasVersionIdViolation = violations.stream()
            .anyMatch(v -> v.getPropertyPath().toString().equals("versionId"));
        assertFalse(hasVersionIdViolation, "versionId 为空字符串时可空，不应存在校验违规");
    }

    /**
     * 用例描述：versionId 为 null 时不再触发校验违规（@NotBlank 已移除，versionId 可空）
     * 预制条件：创建 CreateChannelReq，versionId 保持默认 null，channelType 设为有效值
     * 输入参数：versionId=null, channelType="WEB"
     * 预期结果：不存在针对 versionId 字段的校验违规
     */
    @Test
    void testVersionId_Null_ShouldPassValidation() {
        CreateChannelReq req = new CreateChannelReq();
        req.setVersionId(null);
        req.setChannelType("WEB");

        Set<ConstraintViolation<CreateChannelReq>> violations = validator.validate(req);

        boolean hasVersionIdViolation = violations.stream()
            .anyMatch(v -> v.getPropertyPath().toString().equals("versionId"));
        assertFalse(hasVersionIdViolation, "versionId 为 null 时可空，不应存在校验违规");
    }

    /**
     * 用例描述：versionId 为空白字符串（仅空格）时不再触发校验违规（@NotBlank 已移除，versionId 可空）
     * 预制条件：创建 CreateChannelReq，versionId 设为纯空格字符串，channelType 设为有效值
     * 输入参数：versionId="   ", channelType="WEB"
     * 预期结果：不存在针对 versionId 字段的校验违规
     */
    @Test
    void testVersionId_Whitespace_ShouldPassValidation() {
        CreateChannelReq req = new CreateChannelReq();
        req.setVersionId("   ");
        req.setChannelType("WEB");

        Set<ConstraintViolation<CreateChannelReq>> violations = validator.validate(req);

        boolean hasVersionIdViolation = violations.stream()
            .anyMatch(v -> v.getPropertyPath().toString().equals("versionId"));
        assertFalse(hasVersionIdViolation, "versionId 为纯空格时可空，不应存在校验违规");
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

    /**
     * 用例描述：链式 setter 设置其余全部字段后，对应 getter 应返回设置的值
     * 预制条件：无
     * 输入参数：subType="chat", metadata=["meta1"], inputs=[param], outputs=[param],
     *           prologue="你好", suggestQueries=["q1"]
     * 预期结果：各 getter 返回设置值
     */
    @Test
    void testSetterChainAllFields_ShouldReturnValues() {
        WorkflowFrontParam param = new WorkflowFrontParam();
        List<WorkflowFrontParam> inputs = new ArrayList<>(List.of(param));
        List<String> metadata = new ArrayList<>(List.of("meta1"));
        List<String> suggestQueries = new ArrayList<>(List.of("q1"));

        CreateChannelReq req = new CreateChannelReq()
            .setSubType("chat")
            .setMetadata(metadata)
            .setInputs(inputs)
            .setOutputs(inputs)
            .setPrologue("你好")
            .setSuggestQueries(suggestQueries);

        assertEquals("chat", req.getSubType());
        assertEquals(metadata, req.getMetadata());
        assertEquals(inputs, req.getInputs());
        assertEquals(inputs, req.getOutputs());
        assertEquals("你好", req.getPrologue());
        assertEquals(suggestQueries, req.getSuggestQueries());
    }

    /**
     * 用例描述：toString 应包含已设置字段的名称与值（覆盖 toString 序列化逻辑）
     * 预制条件：创建含 versionId/channelType/subType 字段值的 CreateChannelReq
     * 输入参数：versionId="v1.0", channelType="WEB", subType="chat"
     * 预期结果：toString 输出包含各字段名与对应值
     */
    @Test
    void testToString_ShouldContainAllFields() {
        CreateChannelReq req = new CreateChannelReq()
            .setVersionId("v1.0")
            .setChannelType("WEB")
            .setSubType("chat");

        String str = req.toString();

        assertNotNull(str);
        assertTrue(str.contains("versionId"), "toString 应包含 versionId");
        assertTrue(str.contains("v1.0"), "toString 应包含 versionId 值");
        assertTrue(str.contains("channelType"), "toString 应包含 channelType");
        assertTrue(str.contains("WEB"), "toString 应包含 channelType 值");
        assertTrue(str.contains("subType"), "toString 应包含 subType");
        assertTrue(str.contains("chat"), "toString 应包含 subType 值");
    }

    /**
     * 用例描述：全字段为 null 时 toString 应输出 null 文本（覆盖 toIndentedString 空值分支）
     * 预制条件：创建无任何字段值的 CreateChannelReq
     * 输入参数：无
     * 预期结果：toString 输出包含 "versionId: null"、"channelType: null"
     */
    @Test
    void testToString_WithNullFields_ShouldOutputNullText() {
        CreateChannelReq req = new CreateChannelReq();

        String str = req.toString();

        assertNotNull(str);
        assertTrue(str.contains("versionId: null"), "null 字段应输出 null 文本");
        assertTrue(str.contains("channelType: null"), "null 字段应输出 null 文本");
    }

    /**
     * 用例描述：equals 对同一对象返回 true，内容相同对象返回 true，内容不同返回 false，
     * 对 null 与非同类对象返回 false
     * 预制条件：构造内容相同与内容不同的 CreateChannelReq
     * 输入参数：versionId/channelType 组合
     * 预期结果：equals 按字段比较返回正确布尔值
     */
    @Test
    void testEquals_ShouldCompareAllFields() {
        CreateChannelReq base = new CreateChannelReq()
            .setVersionId("v1.0")
            .setChannelType("WEB");
        CreateChannelReq same = new CreateChannelReq()
            .setVersionId("v1.0")
            .setChannelType("WEB");
        CreateChannelReq diffVersion = new CreateChannelReq()
            .setVersionId("v2.0")
            .setChannelType("WEB");
        CreateChannelReq diffChannel = new CreateChannelReq()
            .setVersionId("v1.0")
            .setChannelType("API");

        assertTrue(base.equals(base), "同一对象 equals 应为 true");
        assertTrue(base.equals(same), "内容相同对象 equals 应为 true");
        assertFalse(base.equals(diffVersion), "versionId 不同 equals 应为 false");
        assertFalse(base.equals(diffChannel), "channelType 不同 equals 应为 false");
        assertFalse(base.equals(null), "与 null 比较应为 false");
        assertFalse(base.equals(new Object()), "与非同类对象比较应为 false");
    }

    /**
     * 用例描述：内容相同对象的 hashCode 应一致
     * 预制条件：构造两个内容相同的 CreateChannelReq
     * 输入参数：versionId="v1.0", channelType="WEB"
     * 预期结果：两个对象的 hashCode 相等
     */
    @Test
    void testHashCode_ShouldBeConsistentForEqualObjects() {
        CreateChannelReq a = new CreateChannelReq()
            .setVersionId("v1.0")
            .setChannelType("WEB");
        CreateChannelReq b = new CreateChannelReq()
            .setVersionId("v1.0")
            .setChannelType("WEB");

        assertEquals(a.hashCode(), b.hashCode());
    }
}
