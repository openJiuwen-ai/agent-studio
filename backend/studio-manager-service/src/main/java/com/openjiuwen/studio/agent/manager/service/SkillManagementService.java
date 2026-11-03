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
import java.util.Objects;

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
     * 流式读取指定 Skill 最新版本的 zip 制品包内容。
     *
     * <p>供前端详情页文件目录树展示使用，避免前端跨域直接请求 OBS 签名 URL。
     * 复用 {@link MgObsService#readObsFileStream(String)} 直接读取 OBS 对象字节流，
     * 由 Controller 层包装为 StreamingResponseBody 流式转发给前端。</p>
     *
     * <p><b>访问控制（按发布状态区分）</b>：</p>
     * <ul>
     *   <li><b>已发布资源</b>（published_asset = 1）：跳过 domainId 校验。
     *       skill 市场按 published_asset 查询时不带 domainId 过滤，市场资源可能来自其他 domain，
     *       跨 domain 预览属于既有契约（详见检视意见 #127、#151）。</li>
     *   <li><b>私有包</b>（published_asset = 0 或 null）：必须校验 domainId 归属。
     *       私有 skill 的完整制品包含源码与工具配置，不应被其他 domain 的用户越权拉取
     *       （详见检视意见 Medium Priority #168）。鉴权强度与 deleteStudioSkill 对齐。</li>
     * </ul>
     * <p>不比对 workspaceId / projectId：同 domain 内跨工作区/项目的预览属于既有契约。</p>
     *
     * <p>实现说明：使用 {@link SkillMapper#searchBySkillId(String)}（LEFT JOIN 版本表 + t_skill.*）
     * 一次性拿到 obs_path / domain_id / published_asset。</p>
     *
     * <p>返回的 InputStream 由调用方（Controller）负责关闭。</p>
     */
    @Override
    public InputStream getSkillPackageContent(String skillId, String workspaceId, String projectId) {
        log.info("Get skill package content, skillId: {}, workspaceId: {}, projectId: {}",
                skillId, workspaceId, projectId);
        // 查询 Skill 基本信息及最新版本 obs_path（searchBySkillId 已 LEFT JOIN t_skill_version）
        SkillDetails skill = skillMapper.searchBySkillId(skillId);
        if (skill == null || Strings.isEmpty(skill.getObsPath())) {
            log.error("Skill not exists or obs path is empty, skillId: {}", skillId);
            throw new AgentStudioException(StudioError.SKILL_NOT_EXISTS);
        }
        // 访问控制：私有包必须校验 domainId，已发布资源跳过（保留跨 domain 市场预览契约）
        boolean isPublished = skill.getPublishedAsset() != null && skill.getPublishedAsset() == 1;
        if (!isPublished) {
            String requestDomainId = RequestContextUtils.getRequestUserDomainId();
            if (!Objects.equals(skill.getDomainId(), requestDomainId)) {
                log.error("Private skill does not belong to the current domain, skillId: {}, domainId: {}, requestDomainId: {}",
                        skillId, skill.getDomainId(), requestDomainId);
                throw new AgentStudioException(StudioError.SKILL_NOT_EXISTS);
            }
        }
        return mgObsService.readObsFileStream(skill.getObsPath());
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
        // finalZipFile 提前声明，便于 finally 引用清理重打包临时文件
        File finalZipFile = zipFile;
        try {
            // 1. 校验（validateZipFile 改为返回 frontmatter，不再依赖静态变量）
            Map<String, Object> frontmatter = ZipValidationUtils.validateZipFile(zipFile);

            // 2. 获取 skill name
            String skillName = frontmatter.get(NAME).toString();

            // 3. 生成Skill相关
            String skillId = UUID.randomUUID().toString();

            // 4. 检测并重打包平铺结构（平铺包会被重打包为 {skillName}/ 结构）
            finalZipFile = ZipValidationUtils.repackIfFlat(zipFile, skillName);

            // 5. 构造OBS存储路径,上传文件到OBS（统一使用 skillName 命名）
            String obsKey = String.format(SKILL_VERSION_FILE_PATH_TEMPLATE,
                    RequestContextUtils.getRequestUserId(),
                    skillId,
                    skillId,
                    skillName + ".zip");
            String obsUrl;

            // 上传Skill制品包
            try (InputStream inputStream = new FileInputStream(finalZipFile)) {
                log.warn("File upload to OBS, obsKey: {}", obsKey);
                mgObsService.uploadObsFile(obsKey, inputStream, -1);
                obsUrl = mgObsService.getTemporaryGetRsp(false, obsKey, 3600);
            } catch (Exception e) {
                log.error("Error OBS upload, skillId: {}, filename: {}", skillId, finalZipFile.getName(), e);
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
        } finally {
            // 清理重打包临时文件（仅当产生了重打包文件时）
            if (finalZipFile != zipFile && finalZipFile.exists()) {
                try {
                    if (!finalZipFile.delete()) {
                        finalZipFile.deleteOnExit();
                        log.warn("Failed to delete repacked zip: {}", finalZipFile.getAbsolutePath());
                    }
                } catch (SecurityException e) {
                    log.warn("Security exception while deleting repacked zip: {}",
                            finalZipFile.getAbsolutePath(), e);
                }
            }
            // 清理原始临时 zip
            if (zipFile.exists()) {
                try {
                    if (!zipFile.delete()) {
                        zipFile.deleteOnExit();
                        log.warn("Failed to delete temporary zip file: {}", zipFile.getAbsolutePath());
                    }
                } catch (SecurityException e) {
                    log.warn("Security exception while deleting temporary zip file: {}",
                            zipFile.getAbsolutePath(), e);
                }
            }
        }
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
        if (Integer.valueOf(1).equals(listStudioSkillsQo.getPublishedAsset())) {
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
