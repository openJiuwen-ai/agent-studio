/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.prompt.engineering.mapper.PeIndustryMapper;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * #1731：资产上架分类校验器 UT。
 * 覆盖：缺省(空 tagId)跳过 / 存在通过 / 不存在抛 INDUSTRY_ID_NOT_EXIST / MyBatis Boolean 返回 null 不 NPE。
 */
@ExtendWith(MockitoExtension.class)
class AssetCategoryValidatorTest {

    @Mock
    private PeIndustryMapper peIndustryMapper;

    private AssetCategoryValidator validator;

    @BeforeEach
    void setUp() {
        validator = new AssetCategoryValidator();
        ReflectionTestUtils.setField(validator, "peIndustryMapper", peIndustryMapper);
    }

    private static final String VALID_SKILL_TAG = "a1020002-0000-4000-8000-000000000001";
    private static final String VALID_PLUGIN_TAG = "a1020001-0000-4000-8000-000000000001";
    private static final String NON_EXIST_TAG = "bbbb2222-3333-4444-5555-666677778888";

    @Test
    void validateCategoryExists_BlankId_Skip() {
        // 缺省沿用既有分类，空 tagId 直接 return 不查库
        assertDoesNotThrow(() ->
            validator.validateCategoryExists(null, AssetCategoryValidator.LIBRARY_TYPE_SKILL));
        assertDoesNotThrow(() ->
            validator.validateCategoryExists("", AssetCategoryValidator.LIBRARY_TYPE_SKILL));
        assertDoesNotThrow(() ->
            validator.validateCategoryExists("   ", AssetCategoryValidator.LIBRARY_TYPE_SKILL));
        verify(peIndustryMapper, never()).existsByIdAndLibraryType(anyString(), anyString());
    }

    @Test
    void validateCategoryExists_Exist_Pass() {
        when(peIndustryMapper.existsByIdAndLibraryType(VALID_SKILL_TAG, AssetCategoryValidator.LIBRARY_TYPE_SKILL))
            .thenReturn(Boolean.TRUE);
        assertDoesNotThrow(() ->
            validator.validateCategoryExists(VALID_SKILL_TAG, AssetCategoryValidator.LIBRARY_TYPE_SKILL));
        verify(peIndustryMapper, times(1)).existsByIdAndLibraryType(VALID_SKILL_TAG,
            AssetCategoryValidator.LIBRARY_TYPE_SKILL);
    }

    @Test
    void validateCategoryExists_NotExist_Throws() {
        // F/H 点：不存在于 t_pe_industry 的合法 UUID → 抛 INDUSTRY_ID_NOT_EXIST
        when(peIndustryMapper.existsByIdAndLibraryType(NON_EXIST_TAG, AssetCategoryValidator.LIBRARY_TYPE_PLUGIN))
            .thenReturn(Boolean.FALSE);
        AgentStudioException ex = assertThrows(AgentStudioException.class, () ->
            validator.validateCategoryExists(NON_EXIST_TAG, AssetCategoryValidator.LIBRARY_TYPE_PLUGIN));
        assertEquals(StudioError.INDUSTRY_ID_NOT_EXIST, ex.getErrorCode());
    }

    @Test
    void validateCategoryExists_MyBatisBooleanNull_NotNpe() {
        // MyBatis Boolean 返回可能为 null：用 Boolean.TRUE.equals 判空，不 NPE，走 fail-closed 抛错
        when(peIndustryMapper.existsByIdAndLibraryType(NON_EXIST_TAG, AssetCategoryValidator.LIBRARY_TYPE_MCP))
            .thenReturn(null);
        AgentStudioException ex = assertThrows(AgentStudioException.class, () ->
            validator.validateCategoryExists(NON_EXIST_TAG, AssetCategoryValidator.LIBRARY_TYPE_MCP));
        assertEquals(StudioError.INDUSTRY_ID_NOT_EXIST, ex.getErrorCode());
    }
}
