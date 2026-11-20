/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.mapper;

import com.openjiuwen.studio.agent.manager.bo.SkillDetails;
import com.openjiuwen.studio.agent.manager.entity.SkillEntity;

import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface SkillMapper {
    /**
     * 插入 Skill 基本信息
     * @return 新建的版本 id
     */
    int insert(SkillEntity skill);

    /**
     * 更新 Skill 基本信息
     * @return 更新的行数
     */
    int update(String skillId, SkillEntity skill);

    /**
     * 更新 Skill 资产广场上架状态与来源（FRS-091 上架/下架）
     *
     * @param skillId Skill ID
     * @param publishedAsset 上架标记（"1"=已上架，"0"=未上架；t_skill.published_asset 为 VARCHAR 列）
     * @param plazaSource 上架来源（PRESET=官方预置，USER=用户上架）
     * @param updatedAt 更新时间（毫秒时间戳）
     * @return 更新的行数
     */
    int updatePublishAsset(@Param("skillId") String skillId,
        @Param("publishedAsset") String publishedAsset,
        @Param("plazaSource") String plazaSource, @Param("updatedAt") Long updatedAt);

    /**
     * 更新 Skill 分类标签（上架时补充广场分类展示）
     *
     * @param skillId Skill ID
     * @param tagId 分类标签ID
     * @param updatedAt 更新时间（毫秒时间戳）
     * @return 更新的行数
     */
    int updateTagById(@Param("skillId") String skillId, @Param("tagId") String tagId,
        @Param("updatedAt") Long updatedAt);

    /**
     * 删除 Skill 基本信息
     * @return 删除的行数
     */
    int delete(String skillId);

    /**
     * 模糊搜索
     *
     * @param publishedAsset 上架标记过滤（null=不过滤，查全部；0/1=精确过滤）
     */
    List<SkillDetails> search(SkillEntity skill, int offset, int limit, String priorityStatus, String tagId,
        Integer publishedAsset);

    /**
     * 获取符合要求的 Skill 的数量
     */
    int countSelectedSkills(SkillEntity skill);

    /**
     * 查询 Skill 详情
     */
    SkillDetails searchBySkillId(String skillId);

    /**
     * 根据 skillIds 批量查询 Skills（通用批量查询，不硬编码广场可见性过滤）。
     *
     * <p>隔离语义（issue #1734）：domainId 非空时按"本 domain 全部 + 跨 domain 已上架
     * （published_asset='1'）"过滤——本 domain 的未上架草稿可见（修复删除前引用确认误报
     * 资源不存在），跨 domain 仅可见已上架（广场可见语义，堵住跨 domain 未上架草稿的存在性/元数据泄露）。
     * 粒度与既有契约对齐：getSkillPackageContent / deleteStudioSkill / searchBySkillIdAndDomainId
     * 均按 domain 校验（同 domain 内跨 workspace/project 预览属于既有契约，不阻断）。
     * domainId 为空时不过滤（保留全局行为，兼容无法获取 domain 上下文的调用方；
     * 新调用方应优先传 domainId = RequestContextUtils.getRequestUserDomainId()）。</p>
     *
     * @param skillIds skill id 列表
     * @param domainId 当前 domain id（null=不过滤 domain，保留全局行为）
     */
    List<SkillDetails> searchBySkillIds(@Param("skillIds") List<String> skillIds, @Param("domainId") String domainId);

    /**
     * 根据 Skill Id 和 domain Id 查询
     */
    SkillDetails searchBySkillIdAndDomainId(String skillId, String domainId);


}
