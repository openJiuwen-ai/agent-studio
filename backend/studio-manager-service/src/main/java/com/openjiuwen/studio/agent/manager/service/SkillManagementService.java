/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.DESCRIPTION;
import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.NAME;
import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.Skill.SKILL_VERSION_FILE_PATH_TEMPLATE;
import static com.openjiuwen.studio.agent.manager.constant.PresetPluginConstants.SKILL_DEFAULT_ICON;

import com.openjiuwen.studio.agent.common.annotation.OperationLog;
import com.openjiuwen.studio.agent.common.enums.OperationType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.bo.SkillDetails;
import com.openjiuwen.studio.agent.manager.dto.ExportStudioSkillResponseBody;
import com.openjiuwen.studio.agent.manager.dto.GetStudioSkillDetailsResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ImportStudioSkillResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ListStudioSkillsQo;
import com.openjiuwen.studio.agent.manager.dto.ListStudioSkillsResponseBody;
import com.openjiuwen.studio.agent.manager.dto.SkillSource;
import com.openjiuwen.studio.agent.manager.dto.SkillStatus;
import com.openjiuwen.studio.agent.manager.dto.StudioSkillInfo;
import com.openjiuwen.studio.agent.manager.entity.SkillEntity;
import com.openjiuwen.studio.agent.manager.entity.SkillVersionEntity;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.SkillMapper;
import com.openjiuwen.studio.agent.manager.mapper.SkillVersionMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.utils.MultipartFileToZipUtils;
import com.openjiuwen.studio.agent.manager.utils.ZipValidationUtils;

import lombok.extern.slf4j.Slf4j;

import org.mapstruct.ap.internal.util.Strings;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * 组件库的 Skill 生命周期管理
 */
@Slf4j
@Service
public class SkillManagementService implements ISkillManagementService {

    private final SkillMapper skillMapper;

    private final SkillVersionMapper skillVersionMapper;

    @Autowired
    private MgObsService mgObsService;

    @Autowired
    private MappingMapper mappingMapper;

    public SkillManagementService(SkillMapper skillMapper, SkillVersionMapper sKillVersionMapper) {
        this.skillMapper = skillMapper;
        this.skillVersionMapper = sKillVersionMapper;
    }

    /**
     * 删除 Skill
     */
    @Transactional
    @Override
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "Skill",
        description = "删除 Skill",
        resourceId = "skillId",
        resourceName = ""
    )
    public Void deleteStudioSkill(String skillId, String workspaceId, String projectId) {
        // 越权校验
        SkillDetails skill = skillMapper.searchBySkillIdAndDomainId(skillId, RequestContextUtils.getRequestUserDomainId());
        if (skill == null) {
            log.error("Skill not exists, skillId: {}", skillId);
            throw new AgentStudioException(StudioError.SKILL_NOT_EXISTS);
        }

        // 删除 OBS 中的所有版本文件
        List<SkillVersionEntity> skillVersionEntities = skillVersionMapper.searchBySkillId(skillId, 0, Integer.MAX_VALUE);
        for (SkillVersionEntity skillVersionEntity : skillVersionEntities) {
            mgObsService.deleteObsObjects(skillVersionEntity.getObsPath());
        }

        // 删除 Skill 基本信息和 Skill 版本信息
        skillMapper.delete(skillId);
        skillVersionMapper.deleteBySkillId(skillId);

        // 所有引用关系置为无效
        mappingMapper.updateValidByResourceId(skillId);

        return null;
    }

    /**
     * 查询 Skill 详情（默认最新版本）
     */
    @Override
    public GetStudioSkillDetailsResponseBody showStudioSkillDetail(String skillId, String workspaceId,
        String projectId) {
        SkillDetails skill = skillMapper.searchBySkillId(skillId);
        if (skill == null) {
            return new GetStudioSkillDetailsResponseBody().setSkillInfo(new StudioSkillInfo());
        }

        String temporaryObsUrl = "";
        if (!Strings.isEmpty(skill.getObsPath())) {
            temporaryObsUrl = mgObsService.getTemporaryGetRsp(false, skill.getObsPath(), 3600);
        }

        StudioSkillInfo skillInfo = new StudioSkillInfo().setSkillId(skill.getSkillId())
            .setDomainId(skill.getDomainId())
            .setSkillName(skill.getName())
            .setStatus(SkillStatus.fromValue(skill.getStatus()))
            .setSource(SkillSource.fromValue(skill.getSource()))
            .setIcon(skill.getIcon())
            .setDescription(skill.getDescription())
            .setCreatorName(skill.getCreatorName())
            .setCreatedTime(skill.getCreatedAt())
            .setUpdatedTime(skill.getUpdatedAt())
            .setLatestVersion(skill.getLatestVersion())
            .setUsedVersion(skill.getUsedVersion())
            .setUsedVersionName(skill.getVersionName())
            .setObsUrl(temporaryObsUrl)
            .setObsPath(skill.getObsPath());

        return new GetStudioSkillDetailsResponseBody().setSkillInfo(skillInfo);
    }

    /**
     * 导入 Skill 制品包
     */
    @Transactional
    @Override
    @OperationLog(
        operationType = OperationType.IMPORT,
        resourceType = "Skill",
        description = "导入 Skill 制品包",
        resourceId = "-1",
        resourceName = ""
    )
    public ImportStudioSkillResponseBody importStudioSkill(String workspaceId, String projectId, MultipartFile multipartFile) {
        log.info("Import skill, workspaceId: {}, projectId: {}", workspaceId, projectId);
        // 文件格式转换
        File zipFile = MultipartFileToZipUtils.convertToZipFile(multipartFile);

        // 调用校验方法
        ZipValidationUtils.validateZipFile(zipFile);

        // 获取frontmatter信息
        Map<String, Object> frontmatter = ZipValidationUtils.getFrontmatter();

        // 生成Skill相关
        String skillId = UUID.randomUUID().toString();

        // 构造OBS存储路径,上传文件到OBS
        String obsKey = String.format(SKILL_VERSION_FILE_PATH_TEMPLATE,
                RequestContextUtils.getRequestUserId(),
                skillId,
                skillId,
                zipFile.getName());
        String obsUrl;

        // 上传Skill制品包
        try (InputStream inputStream = new FileInputStream(zipFile)) {
            log.warn("File upload to OBS, obsKey: {}", obsKey);
            mgObsService.uploadObsFile(obsKey, inputStream, -1);
            obsUrl = mgObsService.getTemporaryGetRsp(false, obsKey, 3600);
        } catch (Exception e) {
            log.error("Error OBS upload, skillId: {}, filename: {}", skillId, zipFile.getName(), e);
            throw new AgentStudioException(StudioError.UPLOAD_FILE_TO_OBS_FAILED);
        }

        // 构造Skill实体并保存
        SkillEntity skillEntity = new SkillEntity()
                .setSkillId(skillId)
                .setDomainId(RequestContextUtils.getRequestUserDomainId())
                .setName(frontmatter.get(NAME).toString())
                .setIcon(SKILL_DEFAULT_ICON)
                .setStatus(SkillStatus.DEVELOPED.getValue())
                .setSource(SkillSource.IMPORT.getValue())
                .setDescription(frontmatter.get(DESCRIPTION).toString())
                .setCreatorId(RequestContextUtils.getRequestUserId())
                .setCreatorName(RequestContextUtils.getRequestUserName())
                .setLatestVersion(skillId)
                .setUsedVersion(skillId)
                .setCreatedAt(System.currentTimeMillis())
                .setUpdatedAt(System.currentTimeMillis())
                .setWorkspaceId(workspaceId)
                .setProjectId(projectId);
        skillMapper.insert(skillEntity);

        // 构造SkillVersion实体并保存
        String versionName = skillId.replace("-", "").substring(0, 7);
        SkillVersionEntity skillVersionEntity = new SkillVersionEntity()
                .setId(skillId)
                .setSkillId(skillId)
                .setVersionName(versionName)
                .setUsed(1)
                .setName(frontmatter.get(NAME).toString())
                .setDescription(frontmatter.get(DESCRIPTION).toString())
                .setObsPath(obsKey)
                .setCreatorId(RequestContextUtils.getRequestUserId())
                .setCreatorName(RequestContextUtils.getRequestUserName())
                .setCreatedAt(System.currentTimeMillis());
        skillVersionMapper.insert(skillVersionEntity);

        // 构造返回结果
        ImportStudioSkillResponseBody response = new ImportStudioSkillResponseBody()
                .setSkillId(skillId)
                .setSkillName(frontmatter.get(NAME).toString())
                .setDescription(frontmatter.get(DESCRIPTION).toString())
                .setObsUrl(obsUrl)
                .setVersionName(versionName)
                .setStatus(SkillStatus.DEVELOPED)
                .setSource(ImportStudioSkillResponseBody.SourceEnum.IMPORT);
        log.info("Import skill succeeded, skillId: {}, obsKey: {}", skillId, obsKey);
        return response;
    }

    /**
     * 导出 Skill 制品包
     */
    @Override
    public ExportStudioSkillResponseBody exportStudioSkill(String skillId, String workspaceId,
        String projectId) {
        // 参数校验
        if (skillId == null || skillId.trim().isEmpty()) {
            log.error("Export skill failed: skillId is empty");
            throw new AgentStudioException(StudioError.SKILL_ID_IS_EMPTY);
        }

        // 查询Skill基本信息
        SkillDetails skillEntity = skillMapper.searchBySkillId(skillId);
        if (skillEntity == null) {
            log.error("Export skill failed: skill not found, skillId: {}", skillId);
            throw new AgentStudioException(StudioError.SKILL_NOT_EXISTS);
        }

        // 检查Skill最新版本
        String versionId = skillEntity.getLatestVersion();
        SkillVersionEntity versionEntity = skillVersionMapper.searchByVersionId(versionId);
        if (versionEntity == null) {
            log.error("Export skill failed: version not found, skillId: {}, versionId: {}", skillId, versionId);
            throw new AgentStudioException(StudioError.SKILL_VERSION_IS_INCORRECT);
        }

        String obsUrl = versionEntity.getObsPath();
        if (obsUrl == null || obsUrl.trim().isEmpty()) {
            log.error("Export skill failed: obsUrl is empty, skillId: {}, skillVersion: {}",
                    skillId, versionId);
            throw new AgentStudioException(StudioError.OBS_URL_NOT_EXISTS);
        }

        // 生成带签名的OBS临时下载URL
        long expiresInSeconds = 600L;
        String tempUrl = mgObsService
                .getTemporaryGetRsp(false, obsUrl, expiresInSeconds);
        if (tempUrl == null || tempUrl.isEmpty()) {
            log.error("Export skill failed: failed to generate temporary URL, skillId: {}, skillVersion: {}",
                    skillId, versionId);
            throw new AgentStudioException(StudioError.GET_OBS_TEMPORARY_URL_NOT_EXIST);
        }

        ExportStudioSkillResponseBody response = new ExportStudioSkillResponseBody()
                .setObsUrl(tempUrl)
                .setSkillName(skillEntity.getName())
                .setVersionName(versionEntity.getVersionName())
                .setSkillId(skillId);

        log.info("Export skill succeeded, skillId: {}, versionId: {}, obsUrl: {}",
                skillId, versionId, obsUrl);
        return response;
    }


    /**
     * 查询 Skill 列表（包括模糊匹配）
     */
    @Override
    public ListStudioSkillsResponseBody listStudioSkills(String projectId, ListStudioSkillsQo listStudioSkillsQo) {
        // 1. 获取匹配列表
        SkillEntity selectCondition;
        if ( 1 == listStudioSkillsQo.getPublishedAsset()){
            selectCondition = new SkillEntity()
                .setName(escapeSqlSpecialChars(listStudioSkillsQo.getName()))
                .setDescription(escapeSqlSpecialChars(listStudioSkillsQo.getDescription()))
                .setStatus(listStudioSkillsQo.getStatus())
                .setSource(listStudioSkillsQo.getSource())
                .setWorkspaceId(listStudioSkillsQo.getWorkspaceId())
                .setProjectId(projectId)
                .setPublishedAsset(listStudioSkillsQo.getPublishedAsset());
        }else {
            selectCondition = new SkillEntity()
                .setDomainId(RequestContextUtils.getRequestUserDomainId())
                .setName(escapeSqlSpecialChars(listStudioSkillsQo.getName()))
                .setDescription(escapeSqlSpecialChars(listStudioSkillsQo.getDescription()))
                .setStatus(listStudioSkillsQo.getStatus())
                .setSource(listStudioSkillsQo.getSource())
                .setWorkspaceId(listStudioSkillsQo.getWorkspaceId())
                .setProjectId(projectId);
        }

        List<SkillDetails> selectedSkills = skillMapper.search(selectCondition, listStudioSkillsQo.getOffset(),
            listStudioSkillsQo.getLimit(), listStudioSkillsQo.getPriorityStatus(),listStudioSkillsQo.getTagId(),listStudioSkillsQo.getPublishedAsset());

        // 2. 构建响应体
        ListStudioSkillsResponseBody responseBody = new ListStudioSkillsResponseBody().setTotal(skillMapper.countSelectedSkills(selectCondition));
        responseBody.setItems(buildRsqEntity(selectedSkills));
        return responseBody;
    }


    private List<StudioSkillInfo> buildRsqEntity(List<SkillDetails> skills) {
        List<StudioSkillInfo> items = new ArrayList<>();
        skills.forEach(skill -> {
            String temporaryObsUrl = "";
            if (!Strings.isEmpty(skill.getObsPath())) {
                temporaryObsUrl = mgObsService.getTemporaryGetRsp(false, skill.getObsPath(), 3600);
            }
            items.add(new StudioSkillInfo()
                .setSkillId(skill.getSkillId())
                .setDomainId(skill.getDomainId())
                .setSkillName(skill.getName())
                .setStatus(SkillStatus.fromValue(skill.getStatus()))
                .setSource(SkillSource.fromValue(skill.getSource()))
                .setIcon(skill.getIcon())
                .setDescription(skill.getDescription())
                .setCreatorName(skill.getCreatorName())
                .setCreatedTime(skill.getCreatedAt() == null ? null : skill.getCreatedAt())
                .setUpdatedTime(skill.getUpdatedAt() == null ? null : skill.getUpdatedAt())
                .setLatestVersion(skill.getLatestVersion())
                .setObsUrl(temporaryObsUrl)
                .setObsPath(skill.getObsPath())
                .setUsedVersion(skill.getUsedVersion())
                .setUsedVersionName(skill.getVersionName()));
        });
        return items;
    }

    /**
     * 转换特殊字符
     */
    private String escapeSqlSpecialChars(String content) {
        if (content == null || content.isEmpty()) {
            return content;
        }
        return content.replace("!", "!!")
            .replace("%", "!%")
            .replace("_", "!_");
    }

}
