/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.prompt.engineering.mapper.PeIndustryMapper;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

/**
 * 资产广场上架分类校验器（FR-03：上架校验存在/归属/状态，失败有明确原因且无半成品）。
 *
 * <p>统一校验 Skill/Plugin/MCP 上架时的分类标签是否存在于 t_pe_industry 且 library_type 匹配，
 * 避免三套上架链路分类校验逻辑分叉（consistency-check 同类型资源口径一致）。</p>
 */
@Slf4j
@Component
public class AssetCategoryValidator {

    /** t_pe_industry.library_type 取值：Skill 资源分类。 */
    public static final String LIBRARY_TYPE_SKILL = "skill";

    /** t_pe_industry.library_type 取值：Plugin 资源分类。 */
    public static final String LIBRARY_TYPE_PLUGIN = "plugin";

    /** t_pe_industry.library_type 取值：MCP 资源分类。 */
    public static final String LIBRARY_TYPE_MCP = "mcp";

    @Autowired
    private PeIndustryMapper peIndustryMapper;

    /**
     * 校验分类标签存在且 library_type 匹配；不存在则抛 400（fail-closed，非法值不进库不留半成品）。
     *
     * @param categoryId 分类标签 ID（t_pe_industry.id 的 UUID；为空时跳过——缺省沿用既有分类）
     * @param libraryType 资源类型（LIBRARY_TYPE_SKILL / PLUGIN / MCP）
     */
    public void validateCategoryExists(String categoryId, String libraryType) {
        if (StringUtils.isBlank(categoryId)) {
            // 缺省沿用既有分类，不校验
            return;
        }
        Boolean exists = peIndustryMapper.existsByIdAndLibraryType(categoryId, libraryType);
        if (!Boolean.TRUE.equals(exists)) {
            log.error("Asset shelf category not exist, categoryId: {}, libraryType: {}", categoryId, libraryType);
            throw new AgentStudioException(StudioError.INDUSTRY_ID_NOT_EXIST, categoryId);
        }
    }
}
