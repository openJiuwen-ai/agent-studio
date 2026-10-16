/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.enums;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

/**
 * PluginCallModeEnum 枚举单元测试，验证 CUSTOM 和 API 枚举值的 code 与 desc。
 *
 */
class PluginCallModeEnumTest {

    /**
     * 用例描述：验证 CUSTOM 枚举的 code 为 "custom"
     * 预制条件：无
     * 输入参数：无
     * 预期结果：PluginCallModeEnum.CUSTOM.getCode() 返回 "custom"
     *
     * @throws Exception 异常
     */
    @Test
    public void testCustomCodeShouldReturnCustom() throws Exception {
        // Then
        assertEquals("custom", PluginCallModeEnum.CUSTOM.getCode());
    }

    /**
     * 用例描述：验证 CUSTOM 枚举的 desc 为 "自定义插件"
     * 预制条件：无
     * 输入参数：无
     * 预期结果：PluginCallModeEnum.CUSTOM.getDesc() 返回 "自定义插件"
     *
     * @throws Exception 异常
     */
    @Test
    public void testCustomDescShouldReturnChineseDescription() throws Exception {
        // Then
        assertEquals("自定义插件", PluginCallModeEnum.CUSTOM.getDesc());
    }

    /**
     * 用例描述：验证 API 枚举的 code 为 "api"
     * 预制条件：无
     * 输入参数：无
     * 预期结果：PluginCallModeEnum.API.getCode() 返回 "api"
     *
     * @throws Exception 异常
     */
    @Test
    public void testApiCodeShouldReturnApi() throws Exception {
        // Then
        assertEquals("api", PluginCallModeEnum.API.getCode());
    }

    /**
     * 用例描述：验证 API 枚举的 desc 为 "api类型插件"
     * 预制条件：无
     * 输入参数：无
     * 预期结果：PluginCallModeEnum.API.getDesc() 返回 "api类型插件"
     *
     * @throws Exception 异常
     */
    @Test
    public void testApiDescShouldReturnApiTypeDescription() throws Exception {
        // Then
        assertEquals("api类型插件", PluginCallModeEnum.API.getDesc());
    }

    /**
     * 用例描述：验证枚举包含两个值，且枚举数量正确
     * 预制条件：无
     * 输入参数：无
     * 预期结果：PluginCallModeEnum.values() 长度为 2
     *
     * @throws Exception 异常
     */
    @Test
    public void testEnumValuesShouldContainTwoEntries() throws Exception {
        // Then
        assertEquals(2, PluginCallModeEnum.values().length);
    }
}
