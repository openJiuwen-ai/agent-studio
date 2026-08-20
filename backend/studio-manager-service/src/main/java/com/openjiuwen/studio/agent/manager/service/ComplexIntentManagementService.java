/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.alibaba.fastjson2.JSONObject;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.openjiuwen.studio.agent.common.annotation.OperationLog;
import com.openjiuwen.studio.agent.common.enums.OperationType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.LanguageUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.StrUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.ComplexIntentBranchBriefRsp;
import com.openjiuwen.studio.agent.manager.dto.ComplexIntentBranchInfoReq;
import com.openjiuwen.studio.agent.manager.dto.ComplexIntentBranchListRsp;
import com.openjiuwen.studio.agent.manager.dto.ComplexIntentBranchRsp;
import com.openjiuwen.studio.agent.manager.dto.ComplexIntentBriefRsp;
import com.openjiuwen.studio.agent.manager.dto.ComplexIntentExportParams;
import com.openjiuwen.studio.agent.manager.dto.ComplexIntentImportRsp;
import com.openjiuwen.studio.agent.manager.dto.ComplexIntentInfoReq;
import com.openjiuwen.studio.agent.manager.dto.ComplexIntentListRsp;
import com.openjiuwen.studio.agent.manager.dto.ComplexIntentRsp;
import com.openjiuwen.studio.agent.manager.dto.ListComplexIntentBranchQo;
import com.openjiuwen.studio.agent.manager.dto.ListComplexIntentQo;
import com.openjiuwen.studio.agent.manager.entity.ComplexIntentBranchEntity;
import com.openjiuwen.studio.agent.manager.entity.ComplexIntentEntity;
import com.openjiuwen.studio.agent.manager.mapper.ComplexIntentBranchMapper;
import com.openjiuwen.studio.agent.manager.mapper.ComplexIntentMapper;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;
import com.openjiuwen.studio.agent.manager.utils.XmlParser;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections.CollectionUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.poi.ooxml.POIXMLProperties;
import org.apache.poi.ss.usermodel.CellType;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.MessageSource;
import org.springframework.core.io.Resource;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * 复杂意图管理
 *
 */
@Slf4j
@Service
public class ComplexIntentManagementService implements IComplexIntentManagementService {
    // 意图分支id索引
    private static final int BRANCH_ID_INDEX = 2;

    // 分支索引前缀
    private static final String BRANCH_PREFIX = "branch_";

    private static final String FAQ_SPLIT_CHAT = ",";

    private static final int MAX_INTENT_SIZE = 100;

    private static final String NAME_REGEX = "^[\\u4e00-\\u9fa5a-zA-Z0-9\\-_]+$";

    private static final Pattern NAME_PATTERN = Pattern.compile(NAME_REGEX);

    @Autowired
    ComplexIntentMapper complexIntentMapper;

    @Autowired
    ComplexIntentBranchMapper complexIntentBranchMapper;

    @Autowired
    MessageSource messageSource;

    // 意图包知识库id
    @Value("${knowledge.complex-intent-repo-id}")
    private String complexIntentRepoId;

    // 最大文件大小，单位MB; 默认10M
    @Value("${MAX_COMPLEX_INTENT_IMPORT_FILE_SIZE:10}")
    private Integer maxComplexIntentImportFileSize;

    // 最大分支數量
    @Value("${MAX_COMPLEX_INTENT_IMPORT_BRANCH_SIZE:200}")
    private int maxComplexIntentImportBranchSize;

    @Value("${env.type}")
    private String envType;

    // 拼接分支索引
    private static String getBranchIndex(int index) {
        return String.format("%s%s", BRANCH_PREFIX, index);
    }

    // 分支内容转结构体
    private static ComplexIntentBranchInfoReq content2BranchInfo(String content) {
        if (StringUtils.isEmpty(content)) {
            return null;
        }

        return JSONObject.parseObject(content, ComplexIntentBranchInfoReq.class);
    }

    // 分支结构体转文本
    private static String branchInfo2Content(ComplexIntentBranchInfoReq info) {
        if (Objects.isNull(info)) {
            return null;
        }
        return JSONObject.toJSONString(info);
    }

    /**
     * 创建意图包
     *
     * @param projectId projectId
     * @param body body 意图包信息
     * @return 意图id
     */
    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "ComplexIntent",
        description = "创建意图包",
        resourceId = "-1",
        resourceName = "body.name"
    )
    @Transactional
    public ComplexIntentBriefRsp createComplexIntent(String projectId, String workspaceId, ComplexIntentInfoReq body) {
        ComplexIntentEntity complexIntent = new ComplexIntentEntity();
        complexIntent.setIntentId(Optional.ofNullable(body.getId()).orElse(UUID.randomUUID().toString()));
        complexIntent.setProjectId(projectId);
        complexIntent.setWorkspaceId(workspaceId);
        complexIntent.setCreatorId(CommonConstant.EnvType.SIMPLE.equals(envType)
            ? RequestContextUtils.getRequestUserId() : RequestContextUtils.getRequestUserName());
        complexIntent.setDomainId(RequestContextUtils.getRequestUserDomainId());
        complexIntent.setCreatedOn(new Date());
        complexIntent.setUpdatedOn(new Date());
        complexIntent.setName(body.getName());
        complexIntent.setDescription(body.getDescription());
        complexIntent.setBranchesCnt(0);

        // 校验名称是否重复
        checkIntentNameRepeat(body.getName(), projectId, workspaceId, complexIntent.getIntentId());

        complexIntentMapper.createEntity(complexIntent);
        if (body.getBranches() == null || body.getBranches().isEmpty()) {
            return new ComplexIntentBriefRsp().setIntentId(complexIntent.getIntentId());
        }
        return new ComplexIntentBriefRsp().setIntentId(complexIntent.getIntentId())
            .setBranchId(createComplexIntentBranch(projectId, complexIntent.getIntentId(), workspaceId,
                body.getBranches().get(0)).getBranchId());
    }

    /**
     * 创建意图分支
     *
     * @param projectId projectId
     * @param intentId intentId
     * @param body body 意图分支信息
     * @return 分支id
     */
    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "ComplexIntent",
        description = "创建意图分支",
        resourceId = "intentId",
        resourceName = "body.name"
    )
    @Transactional
    public ComplexIntentBranchBriefRsp createComplexIntentBranch(String projectId, String intentId, String workspaceId,
        ComplexIntentBranchInfoReq body) {
        checkPermission(projectId, workspaceId, intentId);
        checkExamples(body.getExamples());
        ComplexIntentBranchEntity complexIntentBranchEntity = new ComplexIntentBranchEntity();

        // 如未传branchId，重新生成uuid
        complexIntentBranchEntity
            .setBranchId(StringUtils.isEmpty(body.getBranchId()) ? UUID.randomUUID().toString() : body.getBranchId());
        complexIntentBranchEntity.setProjectId(projectId);
        complexIntentBranchEntity.setWorkspaceId(workspaceId);
        complexIntentBranchEntity.setIntentId(intentId);
        complexIntentBranchEntity.setCreatorId(RequestContextUtils.getRequestUserId());
        complexIntentBranchEntity.setCreatedOn(new Date());
        complexIntentBranchEntity.setUpdatedOn(new Date());
        complexIntentBranchEntity.setContent(branchInfo2Content(body));
        complexIntentBranchEntity.setBranchName(body.getName());

        // 校验名称是否重复
        ComplexIntentBranchEntity intentBranchEntity = new ComplexIntentBranchEntity();
        intentBranchEntity.setProjectId(projectId);
        intentBranchEntity.setWorkspaceId(workspaceId);
        intentBranchEntity.setIntentId(intentId);
        intentBranchEntity.setBranchName(body.getName());
        List<ComplexIntentBranchEntity> origins = complexIntentBranchMapper.getEntities(intentBranchEntity);
        if (origins != null && !origins.isEmpty()) {
            List<String> names = origins.stream().map(ComplexIntentBranchEntity::getBranchName).toList();
            if (names.contains(body.getName())) {
                throw new AgentStudioException(StudioError.RESOURCE_OP_ERROR);
            }
        }

        Integer maxIndex = complexIntentBranchMapper.maxBranchIndex(intentId, projectId, workspaceId);
        complexIntentBranchEntity.setBranchIndex(Objects.isNull(maxIndex) ? 1 : maxIndex + 1);
        complexIntentBranchMapper.createEntity(complexIntentBranchEntity);

        // 增加分支时，更新分支对应的分支数
        updateBranchCnt(projectId, workspaceId, intentId);

        return new ComplexIntentBranchBriefRsp().setBranchId(complexIntentBranchEntity.getBranchId());
    }

    private void validateBranchId(String branchId) {
        // 分支id未传直接返回
        if (StringUtils.isEmpty(branchId)) {
            return;
        }
        // branch id键值唯一，如发生冲突，提示用户修改对应键值
        ComplexIntentBranchEntity branchSearch = new ComplexIntentBranchEntity();
        branchSearch.setBranchId(branchId);
        List<ComplexIntentBranchEntity> origins = complexIntentBranchMapper.getEntities(branchSearch);
        if (CollectionUtils.isEmpty(origins)) {
            return;
        }
        // 查表取的冲突的意图包和分支名，提示用户
        ComplexIntentBranchEntity branchEntity = origins.get(0);
        ComplexIntentEntity intentEntity =
            complexIntentMapper.getByKey(branchEntity.getIntentId(), branchEntity.getProjectId());
        throw new AgentStudioException(StudioError.RESOURCE_OP_ERROR_CONFLICT, branchId, intentEntity.getName(),
            branchEntity.getBranchName());
    }

    /**
     * 删除意图包
     *
     * @param projectId projectId
     * @param intentId intentId
     */
    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "ComplexIntent",
        description = "删除意图包",
        resourceId = "intentId",
        resourceName = ""
    )
    public ComplexIntentBriefRsp deleteComplexIntent(String projectId, String intentId, String workspaceId) {
        checkPermission(projectId, workspaceId, intentId);

        // 先获取需要删除的faq id
        ComplexIntentBranchEntity complexIntentBranchEntity = new ComplexIntentBranchEntity();
        complexIntentBranchEntity.setIntentId(intentId);
        List<ComplexIntentBranchEntity> boundBranchEntities =
            complexIntentBranchMapper.getEntities(complexIntentBranchEntity);
        String faqIds = boundBranchEntities.stream()
            .map(ComplexIntentBranchEntity::getFaqIds)
            .filter(StringUtils::isNotEmpty)
            .collect(Collectors.joining(FAQ_SPLIT_CHAT));

        // 删除意图分支
        complexIntentBranchMapper.deleteByIntentId(intentId, projectId);

        // 删除意图包
        complexIntentMapper.deleteByKey(intentId, projectId);
        return new ComplexIntentBriefRsp().setIntentId(intentId);
    }

    /**
     * 删除意图包分支
     *
     * @param projectId projectId
     * @param intentId intentId
     * @param branchId branchId
     * @return 响应体
     */
    @Override
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "ComplexIntent",
        description = "删除意图分支",
        resourceId = "branchId",
        resourceName = ""
    )
    public ComplexIntentBranchBriefRsp deleteComplexIntentBranch(String projectId, String intentId, String branchId,
        String workspaceId) {
        checkBranchPermission(projectId, workspaceId, intentId, branchId);
        String faqIds = complexIntentBranchMapper.getByKey(branchId, intentId, projectId).getFaqIds();
        complexIntentBranchMapper.deleteByKey(branchId, intentId, projectId);
        updateBranchCnt(projectId, workspaceId, intentId);

        return new ComplexIntentBranchBriefRsp().setBranchId(branchId);
    }

    /**
     * 检索意图包
     *
     * @param projectId projectId
     * @param listComplexIntentQo listComplexIntentQo
     * @return 意图包列表
     */
    @Override
    public ComplexIntentListRsp listComplexIntent(String projectId, ListComplexIntentQo listComplexIntentQo) {
        PageHelper.offsetPage(listComplexIntentQo.getOffset(), listComplexIntentQo.getLimit());
        ComplexIntentEntity complexIntentEntity = new ComplexIntentEntity();
        complexIntentEntity.setProjectId(projectId);
        complexIntentEntity.setWorkspaceId(listComplexIntentQo.getWorkspaceId());
        if (StringUtils.isNotEmpty(listComplexIntentQo.getName())) {
            complexIntentEntity.setName(StrUtils.filterSpecialWords(listComplexIntentQo.getName()));
        }
        List<ComplexIntentEntity> entities = complexIntentMapper.getEntities(complexIntentEntity);
        PageInfo<ComplexIntentEntity> pageInfo = new PageInfo<>(entities);

        List<ComplexIntentRsp> infos = new ArrayList<>();
        for (ComplexIntentEntity entity : entities) {
            infos.add(new ComplexIntentRsp().setIntentId(entity.getIntentId())
                .setProjectId(entity.getProjectId())
                .setWorkspaceId(entity.getWorkspaceId())
                .setCreatorId(entity.getCreatorId())
                .setName(entity.getName())
                .setDescription(entity.getDescription())
                .setBranchesCnt(entity.getBranchesCnt())
                .setCreateTime(entity.getCreatedOn()));
        }
        return new ComplexIntentListRsp().setIntents(infos).setCount(pageInfo.getTotal());
    }

    /**
     * 检索意图包分支
     *
     * @param projectId projectId
     * @param intentId intentId
     * @param listComplexIntentBranchQo listComplexIntentBranchQ
     * @return
     */
    @Override
    public ComplexIntentBranchListRsp listComplexIntentBranch(String projectId, String intentId,
        ListComplexIntentBranchQo listComplexIntentBranchQo) {
        String name = listComplexIntentBranchQo.getName();
        ComplexIntentBranchEntity complexIntentBranchEntity = new ComplexIntentBranchEntity();
        complexIntentBranchEntity.setProjectId(projectId);
        complexIntentBranchEntity.setWorkspaceId(listComplexIntentBranchQo.getWorkspaceId());
        complexIntentBranchEntity.setIntentId(intentId);
        if (StringUtils.isNotEmpty(name)) {
            complexIntentBranchEntity.setBranchName(name);
        }
        List<ComplexIntentBranchEntity> entities = complexIntentBranchMapper.getEntities(complexIntentBranchEntity);
        PageInfo<ComplexIntentBranchEntity> pageInfo = new PageInfo<>(entities);

        List<ComplexIntentBranchRsp> infos = new ArrayList<>();
        for (ComplexIntentBranchEntity intentBranchEntity : entities) {

            ComplexIntentBranchRsp branch = new ComplexIntentBranchRsp().setIntentId(intentBranchEntity.getIntentId())
                .setBranchId(intentBranchEntity.getBranchId())
                .setProjectId(intentBranchEntity.getProjectId())
                .setWorkspaceId(intentBranchEntity.getWorkspaceId())
                .setCreatorId(intentBranchEntity.getCreatorId())
                .setName(intentBranchEntity.getBranchName())
                .setBranchIndex(getBranchIndex(intentBranchEntity.getBranchIndex()));

            if (!StringUtils.isEmpty(intentBranchEntity.getContent())) {
                ComplexIntentBranchInfoReq content = content2BranchInfo(intentBranchEntity.getContent());
                branch.setDescription(content.getDescription());
                branch.setExamples(content.getExamples());
            }

            infos.add(branch);
        }

        return new ComplexIntentBranchListRsp().setBranches(infos).setCount(pageInfo.getTotal());
    }

    /**
     * 修改意图包
     *
     * @param projectId projectId
     * @param intentId intentId
     * @param body body
     * @return 意图包分支
     */
    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "ComplexIntent",
        description = "修改意图包",
        resourceId = "intentId",
        resourceName = "body.name"
    )
    @Transactional
    public ComplexIntentBriefRsp modifyComplexIntent(String projectId, String intentId, String workspaceId,
        ComplexIntentInfoReq body) {
        checkPermission(projectId, workspaceId, intentId);

        ComplexIntentEntity complexIntentEntity = new ComplexIntentEntity();
        complexIntentEntity.setProjectId(projectId);
        complexIntentEntity.setIntentId(intentId);
        complexIntentEntity.setName(body.getName());
        complexIntentEntity.setDescription(body.getDescription());
        complexIntentEntity.setUpdatedOn(new Date());

        // 校验名称重复
        checkIntentNameRepeat(body.getName(), projectId, workspaceId, intentId);
        complexIntentMapper.updateByKey(complexIntentEntity);
        if (body.getBranches() == null || body.getBranches().isEmpty()) {
            return new ComplexIntentBriefRsp().setIntentId(intentId);
        }
        ComplexIntentBranchInfoReq branchInfoReq = body.getBranches().get(0);
        ComplexIntentBranchBriefRsp complexIntentBranchBriefRsp = modifyComplexIntentBranch(projectId, intentId,
            branchInfoReq.getBranchId(), workspaceId, branchInfoReq);
        return new ComplexIntentBriefRsp().setIntentId(intentId).setBranchId(complexIntentBranchBriefRsp.getBranchId());
    }

    protected void checkIntentNameRepeat(String name, String projectId, String workspaceId, String intentId) {
        ComplexIntentEntity complexIntentSearch = new ComplexIntentEntity();
        complexIntentSearch.setProjectId(projectId);
        complexIntentSearch.setWorkspaceId(workspaceId);
        complexIntentSearch.setName(name);
        List<ComplexIntentEntity> entitiesAccurate = complexIntentMapper.getEntitiesAccurate(complexIntentSearch);
        if (entitiesAccurate.isEmpty()) {
            return;
        }
        if (entitiesAccurate.size() > 1) {
            log.error("multiple intent packages with the same name , entities:{}", entitiesAccurate);
            throw new AgentStudioException(StudioError.RESOURCE_OP_ERROR);
        }
        ComplexIntentEntity entity = entitiesAccurate.get(0);
        if (!entity.getIntentId().equals(intentId)) {
            log.error("already an intent package with the same name , entities:{}", entitiesAccurate);
            throw new AgentStudioException(StudioError.RESOURCE_OP_ERROR);
        }
    }

    // 校验操作权限
    private void checkPermission(String projectId, String workspaceId, String intentId) {
        ComplexIntentEntity originEntity = complexIntentMapper.getByKeyAndWorkspaceId(intentId, projectId, workspaceId);
        if (Objects.isNull(originEntity)) {
            throw new AgentStudioException(StudioError.NO_PERMISSION_MODIFY);
        }
    }

    private void checkExamples(List<String> examples) {
        if (CollectionUtils.isNotEmpty(examples) && examples.stream().collect(Collectors.toSet()).size() < examples
            .size()) {
            log.error("Duplicate intent examples");
            throw new AgentStudioException(StudioError.COMPLEX_INTENT_EXAMPLE_REPEATED);
        }
    }

    // 校验操作权限（分支）
    private void checkBranchPermission(String projectId, String workspaceId, String intentId, String branchId) {
        ComplexIntentBranchEntity originEntity =
            complexIntentBranchMapper.getByKeyAndWorkspaceId(branchId, intentId, projectId, workspaceId);
        if (Objects.isNull(originEntity)) {
            throw new AgentStudioException(StudioError.NO_PERMISSION_MODIFY);
        }
    }

    /**
     * 修改意图分支
     *
     * @param projectId projectId
     * @param intentId intentId
     * @param branchId branchId
     * @param body body
     * @return 分支id
     */
    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "ComplexIntent",
        description = "修改意图分支",
        resourceId = "branchId",
        resourceName = "body.name"
    )
    @Transactional
    public ComplexIntentBranchBriefRsp modifyComplexIntentBranch(String projectId, String intentId, String branchId,
        String workspaceId, ComplexIntentBranchInfoReq body) {
        if(body.getBranchId() == null || body.getBranchId().isEmpty()){
            // 分支id为空，创建
            return new ComplexIntentBranchBriefRsp().setBranchId(createComplexIntentBranch(projectId, intentId, workspaceId, body).getBranchId());
        }
        checkBranchPermission(projectId, workspaceId, intentId, branchId);
        checkExamples(body.getExamples());
        // 校验意图分支名称重复
        checkIntentBranchNameRepeat(body.getName(), projectId, workspaceId, intentId, branchId);
        ComplexIntentBranchEntity complexIntentBranchEntity = new ComplexIntentBranchEntity();
        complexIntentBranchEntity.setProjectId(projectId);
        complexIntentBranchEntity.setIntentId(intentId);
        complexIntentBranchEntity.setBranchId(branchId);
        complexIntentBranchEntity.setBranchName(body.getName());
        complexIntentBranchEntity.setContent(branchInfo2Content(body));
        complexIntentBranchEntity.setUpdatedOn(new Date());

        complexIntentBranchMapper.updateByKey(complexIntentBranchEntity);

        return new ComplexIntentBranchBriefRsp().setBranchId(branchId);
    }

    protected void checkIntentBranchNameRepeat(String name, String projectId, String workspaceId, String intentId,
        String branchId) {
        ComplexIntentBranchEntity complexIntentBranchSearch = new ComplexIntentBranchEntity();
        complexIntentBranchSearch.setProjectId(projectId);
        complexIntentBranchSearch.setWorkspaceId(workspaceId);
        complexIntentBranchSearch.setBranchName(name);
        complexIntentBranchSearch.setIntentId(intentId);
        List<ComplexIntentBranchEntity> entitiesAccurate = complexIntentBranchMapper.getEntitiesAccurate(complexIntentBranchSearch);
        if (entitiesAccurate.isEmpty()) {
            return;
        }
        if (entitiesAccurate.size() > 1) {
            log.error("multiple intent branch with the same name , entities:{}", entitiesAccurate);
            throw new AgentStudioException(StudioError.RESOURCE_OP_ERROR);
        }
        ComplexIntentBranchEntity entity = entitiesAccurate.get(0);
        if (!entity.getBranchId().equals(branchId)) {
            log.error("already an branch with the same name , entities:{}", entitiesAccurate);
            throw new AgentStudioException(StudioError.RESOURCE_OP_ERROR);
        }
    }

    /**
     * 检索意图包
     *
     * @param projectId projectId
     * @param intentId intentId
     * @return 意图包信息
     */
    @Override
    @OperationLog(
        operationType = OperationType.READ,
        resourceType = "ComplexIntent",
        description = "查询意图包",
        resourceId = "intentId",
        resourceName = ""
    )
    public ComplexIntentRsp retrieveComplexIntent(String projectId, String intentId, String workspaceId) {
        ComplexIntentEntity entity = complexIntentMapper.getByKeyAndWorkspaceId(intentId, projectId, workspaceId);

        // 无实体
        if (Objects.isNull(entity)) {
            throw new AgentStudioException(StudioError.STATIC_RESOURCE_NOT_EXIST);
        }

        return new ComplexIntentRsp().setProjectId(projectId)
            .setIntentId(intentId)
            .setCreatorId(entity.getCreatorId())
            .setName(entity.getName())
            .setDescription(entity.getDescription())
            .setBranchesCnt(entity.getBranchesCnt());
    }

    // 刷新主意图包的分支数
    private void updateBranchCnt(String projectId, String workspaceId, String intentId) {
        int branchCnt = complexIntentBranchMapper.countBranch(intentId, projectId, workspaceId);
        ComplexIntentEntity complexIntentEntity = new ComplexIntentEntity();
        complexIntentEntity.setProjectId(projectId);
        complexIntentEntity.setIntentId(intentId);
        complexIntentEntity.setBranchesCnt(branchCnt);
        complexIntentMapper.updateByKey(complexIntentEntity);
    }

    /**
     * 更新faq id。便于清理
     *
     * @param projectId
     * @param intentId
     * @param branchId
     * @param faqIds
     */
    private void updateFaqIds(String projectId, String intentId, String branchId, List<String> faqIds) {
        ComplexIntentBranchEntity intentBranchEntity = new ComplexIntentBranchEntity();
        intentBranchEntity.setBranchId(branchId);
        intentBranchEntity.setProjectId(projectId);
        intentBranchEntity.setIntentId(intentId);
        intentBranchEntity.setFaqIds(String.join(FAQ_SPLIT_CHAT, faqIds));
        complexIntentBranchMapper.updateByKey(intentBranchEntity);
    }

    private void clearFaqIds(String projectId, String intentId, String branchId) {
        ComplexIntentBranchEntity intentBranchEntity = new ComplexIntentBranchEntity();
        intentBranchEntity.setBranchId(branchId);
        intentBranchEntity.setProjectId(projectId);
        intentBranchEntity.setIntentId(intentId);
        complexIntentBranchMapper.clearFaqIds(intentBranchEntity);
    }

    @Override
    public Resource exportIntentTemplate(String projectId, String workspaceId) {
        return exportIntent(projectId, workspaceId, null);
    }

    @Override
    public Resource exportIntent(String projectId, String workspaceId, ComplexIntentExportParams body) {
        // 创建工作簿
        XSSFWorkbook workbook = new XSSFWorkbook();
        Map<String, List<ComplexIntentBranchRsp>> datas = new HashMap<>();
        POIXMLProperties.CustomProperties customProperties = workbook.getProperties().getCustomProperties();
        // 根据语言返回对应的模板
        Locale locale = LanguageUtils.getLanguageLocale();
        if (Objects.isNull(body) || body.getIds().isEmpty()) {
            datas.put(messageSource.getMessage("export-intent.package.name", null, locale), new ArrayList<>());
        } else {
            body.getIds().forEach(intentId -> {
                ComplexIntentEntity complexIntentEntity =
                    complexIntentMapper.getByKeyAndWorkspaceId(intentId, projectId, workspaceId);
                ComplexIntentBranchListRsp entities = listComplexIntentBranch(projectId, intentId,
                    new ListComplexIntentBranchQo().setWorkspaceId(workspaceId));
                if (!Objects.isNull(complexIntentEntity) && !Objects.isNull(entities)) {
                    datas.put(complexIntentEntity.getName(), entities.getBranches());
                    customProperties.addProperty(complexIntentEntity.getName(), complexIntentEntity.getIntentId());
                }
            });
        }

        int colIdxName = 0;
        int colIdxExamples = 1;

        datas.forEach((key, value) -> {
            // 创建工作表
            Sheet sheet = workbook.createSheet(key);

            // 创建标题行
            Row headerRow = sheet.createRow(0);
            headerRow.createCell(colIdxName)
                .setCellValue(messageSource.getMessage("export-intent.col.intent.name", null, locale));
            headerRow.createCell(colIdxExamples)
                .setCellValue(messageSource.getMessage("export-intent.col.intent.examples", null, locale));
            headerRow.createCell(BRANCH_ID_INDEX)
                .setCellValue(messageSource.getMessage("export-intent.col.intent.branchid", null, locale));

            value.forEach(s -> {
                // 创建数据行
                Row dataRow = sheet.createRow(sheet.getLastRowNum() + 1);
                dataRow.createCell(colIdxName).setCellValue(s.getName());
                dataRow.createCell(colIdxExamples).setCellValue(String.join(FAQ_SPLIT_CHAT, s.getExamples()));
                dataRow.createCell(BRANCH_ID_INDEX).setCellValue(s.getBranchId());
            });
        });

        // 将工作簿写入字节数组输出流
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try {
            workbook.write(bos);
            workbook.close();
        } catch (IOException e) {
            log.error("export excel file error. {}", e.getLocalizedMessage(), e);
            throw new AgentStudioException(StudioError.INTENT_EXPORT_FILE_ERROR);
        }

        // 处理响应体
        byte[] bytes = bos.toByteArray();
        ResponseModel.TransferResource resource = new ResponseModel.TransferResource(new ByteArrayInputStream(bytes));
        resource.setFilename(String.format(Locale.ROOT, "complex-intent-%s.xlsx", UUID.randomUUID()));
        resource.setLength((long) bytes.length);
        return resource;
    }

    @Override
    @OperationLog(
        operationType = OperationType.IMPORT,
        resourceType = "ComplexIntent",
        description = "导入意图包",
        resourceId = "-1",
        resourceName = ""
    )
    @Transactional
    public ComplexIntentImportRsp importIntent(String workspaceId, String projectId, MultipartFile file, String intentName) {
        return importIntentBranch(workspaceId, projectId, null, file, intentName);
    }

    @Override
    @OperationLog(
        operationType = OperationType.IMPORT,
        resourceType = "ComplexIntent",
        description = "导入意图分支",
        resourceId = "-1",
        resourceName = ""
    )
    @Transactional
    public ComplexIntentImportRsp importIntentBranch(String workspaceId, String projectId, String intentId,
        MultipartFile file) {
        return importIntentBranch(workspaceId, projectId, intentId, file, null);
    }

    public ComplexIntentImportRsp importIntentBranch(String workspaceId, String projectId, String intentId, MultipartFile file, String intentName) {
        XmlParser.parseXml(file, maxComplexIntentImportFileSize);
        // 指定意图包导入时， 校验;
        if (StringUtils.isNotEmpty(intentId)) {
            ComplexIntentEntity intentEntity =
                complexIntentMapper.getByKeyAndWorkspaceId(intentId, projectId, workspaceId);
            if (Objects.isNull(intentEntity)) {
                throw new AgentStudioException(StudioError.STATIC_RESOURCE_NOT_EXIST);
            }
        }

        Map<String, String> intentIdMap = new HashMap<>();
        Map<String, List<ComplexIntentBranchInfoReq>> datas = new HashMap<>();
        try (InputStream fis = file.getInputStream(); XSSFWorkbook workbook = new XSSFWorkbook(fis)) {

            // 最大单次导入100个
            int maxIntentSize = Math.min(MAX_INTENT_SIZE, workbook.getNumberOfSheets());

            // 指定分支导入时，只取第一个sheet
            if (StringUtils.isNotEmpty(intentId) || StringUtils.isNotEmpty(intentName)) {
                maxIntentSize = 1;
            }

            for (int sheetIdx = 0; sheetIdx < maxIntentSize; sheetIdx++) {
                Sheet sheet = workbook.getSheetAt(sheetIdx);
                String sheetName = sheet.getSheetName();
                if(StringUtils.isNotEmpty(intentName)) {
                    sheetName = intentName;
                }
                if (sheet.getLastRowNum() > maxComplexIntentImportBranchSize) {
                    throw new AgentStudioException(StudioError.BRANCHES_SIZE_EXCEEDS_LIMIT, sheetName);
                }
                List<ComplexIntentBranchInfoReq> branch = new ArrayList<>();

                // 意图包名称为空；
                if (StringUtils.isEmpty(sheetName)) {
                    continue;
                }

                // 构建意图包名称-id键值对
                POIXMLProperties.CustomProperties customProperties = workbook.getProperties().getCustomProperties();
                if (customProperties.getProperty(sheetName) != null) {
                    intentIdMap.put(sheetName, customProperties.getProperty(sheetName).getLpwstr());
                }

                for (int rowIdx = 1; rowIdx <= sheet.getLastRowNum(); rowIdx++) {
                    Row row = sheet.getRow(rowIdx);

                    // 校验单元格是否为字符串内容, 或空格
                    String branchName =
                        Objects.isNull(row.getCell(0)) || !CellType.STRING.equals(row.getCell(0).getCellType()) ? ""
                            : row.getCell(0).getStringCellValue();
                    if (StringUtils.isEmpty(branchName)) {
                        continue;
                    }

                    // 校验单元格是否为字符串内容, 或空格
                    String examples =
                        Objects.isNull(row.getCell(1)) || !CellType.STRING.equals(row.getCell(1).getCellType()) ? ""
                            : row.getCell(1).getStringCellValue();

                    String branchId = Objects.isNull(row.getCell(BRANCH_ID_INDEX))
                        || !CellType.STRING.equals(row.getCell(BRANCH_ID_INDEX).getCellType()) ? ""
                        : row.getCell(BRANCH_ID_INDEX).getStringCellValue();

                    branch.add(new ComplexIntentBranchInfoReq().setName(branchName)
                        .setExamples(StringUtils.isEmpty(examples) ? Collections.emptyList()
                            : Arrays.asList(examples.split(FAQ_SPLIT_CHAT)))
                        .setBranchId(branchId));
                }

                datas.put(sheetName, branch);
            }
        } catch (AgentStudioException e) {
            log.error("Failed to import intent file.", e);
            throw e;
        } catch (Exception e) {
            log.error("failed to intent import file, error: {}.", e.getLocalizedMessage());
            throw new AgentStudioException(StudioError.INTENT_IMPORT_FILE_ERROR);
        }

        for (Map.Entry<String, List<ComplexIntentBranchInfoReq>> entry : datas.entrySet()) {
            if (!NAME_PATTERN.matcher(entry.getKey()).matches()) {
                log.error("Failed to import intent file, intent name:{} invalid.", entry.getKey());
                throw new AgentStudioException(StudioError.IMPORT_COMPLEX_INTENT_NAME_INVALID, entry.getKey());
            }
            for (ComplexIntentBranchInfoReq branch : entry.getValue()) {
                if (branch.getName().length() > 32) {
                    log.error(
                        "Failed to import intent file. branch name length exceeding the limit. limit:{} length:{}", 32,
                        branch.getName().length());
                    throw new AgentStudioException(StudioError.IMPORT_BRANCH_NAME_EXCEED_LIMIT, 32);
                }
                if (!NAME_PATTERN.matcher(branch.getName()).matches()) {
                    log.error("Failed to import intent file, branch name:{} invalid.", branch.getName());
                    throw new AgentStudioException(StudioError.IMPORT_COMPLEX_INTENT_BRANCH_NAME_INVALID, branch
                        .getName());
                }
                for (String example : branch.getExamples()) {
                    if (example.length() > 63) {
                        log.error(
                            "Failed to import intent file. example name length exceeding the limit. limit:{} length:{}",
                            64, branch.getName().length());
                        throw new AgentStudioException(StudioError.IMPORT_COMPLEX_INTENT_EXAMPLE_EXCEED_LIMIT, 64);
                    }
                    if (!NAME_PATTERN.matcher(example).matches()) {
                        log.error("Failed to import intent file, example:{} invalid.", example);
                        throw new AgentStudioException(StudioError.IMPORT_COMPLEX_INTENT_EXAMPLE_INVALID, example);
                    }
                }
            }
        }

        // 插入数据
        List<String> intentIds = new ArrayList<>();
        try {
            datas.forEach((key, value) -> {
                // 意图名称重名校验
                int nameNotRepeatSize =
                    value.stream().map(ComplexIntentBranchInfoReq::getName).collect(Collectors.toSet()).size();
                if (nameNotRepeatSize != value.size()) {
                    throw new AgentStudioException(StudioError.RESOURCE_OP_ERROR);
                }
                String dstIntentId = intentId;

                // 创建意图包之前需校验branchId重复
                value.forEach(branch -> validateBranchId(branch.getBranchId()));
                if (StringUtils.isEmpty(intentId)) {
                    // 创建意图包
                    ComplexIntentInfoReq intent = new ComplexIntentInfoReq().setName(key);
                    if (intentIdMap.containsKey(key)) {
                        intent.setId(intentIdMap.get(key));
                    }
                    dstIntentId = createComplexIntent(projectId, workspaceId, intent).getIntentId();
                }

                final String dbIntentId = dstIntentId;
                intentIds.add(dbIntentId);
                value.forEach(branch -> {
                    ComplexIntentBranchInfoReq branchReq = new ComplexIntentBranchInfoReq().setName(branch.getName())
                        .setExamples(branch.getExamples())
                        .setBranchId(branch.getBranchId());
                    createComplexIntentBranch(projectId, dbIntentId, workspaceId, branchReq);
                });
            });
        } catch (AgentStudioException e) {
            log.error("Failed to import intent file.", e);
            throw e;
        } catch (Exception e) {
            log.error("failed to intent import file, error: {}.", e.getLocalizedMessage());
            throw new AgentStudioException(StudioError.INTENT_IMPORT_FILE_ERROR);
        }

        return new ComplexIntentImportRsp().setSuccess(Boolean.TRUE).setIntentIds(intentIds);
    }
}
