/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.mapper;

import com.openjiuwen.studio.prompt.engineering.dto.IndustryDto;
import com.openjiuwen.studio.prompt.engineering.entity.Industry;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface PeIndustryMapper {
    Boolean isExist(@Param("body") IndustryDto body, @Param("workspaceId") String workspaceId);

    void insertOne(Industry industry);

    List<Industry> queryAll();

    List<Industry> queryIndustryByLibraryType(@Param("libraryType") String libraryType);

    /**
     * 校验指定 id 且 library_type 的行业分类是否存在（上架分类存在性校验，跨 prompt/plugin/mcp/skill 复用）。
     *
     * @param id          行业分类 ID（t_pe_industry.id，UUID）
     * @param libraryType 资源类型（prompt/plugin/mcp/skill）
     * @return 存在返回 true
     */
    Boolean existsByIdAndLibraryType(@Param("id") String id, @Param("libraryType") String libraryType);

    Integer deleteById(String industryId, String workspaceId);

    Integer updateOne(Industry industry);
}
