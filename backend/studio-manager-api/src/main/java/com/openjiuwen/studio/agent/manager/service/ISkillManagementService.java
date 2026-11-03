/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.manager.dto.ExportStudioSkillResponseBody;
import com.openjiuwen.studio.agent.manager.dto.GetStudioSkillDetailsResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ImportStudioSkillResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ListStudioSkillsQo;
import com.openjiuwen.studio.agent.manager.dto.ListStudioSkillsResponseBody;

import java.io.InputStream;

import org.springframework.web.multipart.MultipartFile;

/**
 * SkillManagement service
 */

public interface ISkillManagementService {

    /**
     * deleteStudioSkill
     *
     * @param skillId skillId
     * @param workspaceId workspaceId
     * @param projectId projectId
     */
    Void deleteStudioSkill(String skillId, String workspaceId, String projectId);

    /**
     * exportStudioSkill
     *
     * @param skillId skillId
     * @param workspaceId workspaceId
     * @param projectId projectId
     */
    ExportStudioSkillResponseBody exportStudioSkill(String skillId, String workspaceId, String projectId);

    /**
     * importStudioSkill
     *
     * @param workspaceId workspaceId
     * @param projectId projectId
     * @param file file
     */
    ImportStudioSkillResponseBody importStudioSkill(String workspaceId, String projectId, MultipartFile file);

    /**
     * listStudioSkills
     *
     * @param projectId projectId
     * @param listStudioSkillsQo listStudioSkillsQo
     */
    ListStudioSkillsResponseBody listStudioSkills(String projectId, ListStudioSkillsQo listStudioSkillsQo);

    /**
     * showStudioSkillDetail
     *
     * @param skillId skillId
     * @param workspaceId workspaceId
     * @param projectId projectId
     */
    GetStudioSkillDetailsResponseBody showStudioSkillDetail(String skillId, String workspaceId, String projectId);

    /**
     * 流式读取指定 Skill 最新版本的 zip 制品包内容。
     *
     * <p>供前端详情页文件目录树展示使用，避免前端跨域直接请求 OBS 签名 URL。
     * 返回的 InputStream 由调用方负责关闭。</p>
     *
     * @param skillId skillId
     * @param workspaceId workspaceId
     * @param projectId projectId
     * @return OBS zip 字节流
     */
    InputStream getSkillPackageContent(String skillId, String workspaceId, String projectId);
}