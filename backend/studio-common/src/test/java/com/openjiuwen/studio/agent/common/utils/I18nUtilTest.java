/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */

package com.openjiuwen.studio.agent.common.utils;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.context.MessageSource;

import java.util.Locale;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class I18nUtilTest {

    @Mock
    private MessageSource messageSource;

    @InjectMocks
    private I18nUtil i18nUtil;

    @Test
    void testGetMessage_ByCode() {
        when(messageSource.getMessage(eq("test.code"), any(Object[].class), eq("test.code"), any(Locale.class)))
                .thenReturn("Test Message");
        String result = i18nUtil.getMessage("test.code");
        assertEquals("Test Message", result);
    }

    @Test
    void testGetMessage_ByStudioError() {
        when(messageSource.getMessage(any(String.class), any(Object[].class), any(String.class), any(Locale.class)))
                .thenReturn("Error Message");
        String result = i18nUtil.getMessage(StudioError.UNEXPECTED_ERROR);
        assertNotNull(result);
    }

    @Test
    void testGetSuggestion_ByStudioError() {
        when(messageSource.getMessage(any(String.class), any(Object[].class), any(Locale.class)))
                .thenReturn("Suggestion text");
        String result = i18nUtil.getSuggestion(StudioError.UNEXPECTED_ERROR);
        assertEquals("Suggestion text", result);
    }

    @Test
    void testGetSuggestion_ExceptionReturnsNull() {
        when(messageSource.getMessage(any(String.class), any(Object[].class), any(Locale.class)))
                .thenThrow(new RuntimeException("not found"));
        String result = i18nUtil.getSuggestion(StudioError.UNEXPECTED_ERROR);
        assertNull(result);
    }

    @Test
    void testGetMessage_ByException() {
        AgentStudioException exception = new AgentStudioException(StudioError.UNEXPECTED_ERROR, "detail");
        when(messageSource.getMessage(any(String.class), any(Object[].class), any(String.class), any(Locale.class)))
                .thenReturn("msg");
        ErrorInfo result = i18nUtil.getMessage(exception);
        assertNotNull(result);
    }

    @Test
    void testGetMessage_threeArg_emptyArgs_normalizedToNull() {
        // 空 args 数组归一为 null（MessageFormat 空 args+占位不抛但留 {0} 原文；归一 null 统一"空 args"契约）。
        // mock 捕获归一后的 null args，返回兜底 code。
        when(messageSource.getMessage(eq("test.code"), isNull(), eq("test.code"), any(Locale.class)))
                .thenReturn("test.code");
        String result = i18nUtil.getMessage("test.code", new Object[0], Locale.CHINA);
        assertEquals("test.code", result, "空 args 数组应归一为 null，返回兜底 code");
    }

    @Test
    void testGetMessage_threeArg_nonNullArgs_passesThrough() {
        // 非空 args 透传（{0} 占位填 args[0]）。
        when(messageSource.getMessage(eq("test.code"), eq(new Object[]{"agent"}), eq("test.code"), any(Locale.class)))
                .thenReturn("agent资源不存在");
        String result = i18nUtil.getMessage("test.code", new Object[]{"agent"}, Locale.CHINA);
        assertEquals("agent资源不存在", result);
    }
}
