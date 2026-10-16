/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.alibaba.fastjson2.JSON;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.openjiuwen.studio.agent.common.annotation.OperationLog;
import com.openjiuwen.studio.agent.common.enums.OperationType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.StrUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.BatchDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.ExportMessagesParams;
import com.openjiuwen.studio.agent.manager.dto.FailedStructuredMessage;
import com.openjiuwen.studio.agent.manager.dto.ListStructuredMessagesQo;
import com.openjiuwen.studio.agent.manager.dto.StructMessage;
import com.openjiuwen.studio.agent.manager.dto.StructMessageListRsp;
import com.openjiuwen.studio.agent.manager.dto.StructuredInfoRequest;
import com.openjiuwen.studio.agent.manager.dto.StructuredInfoRequestDelete;
import com.openjiuwen.studio.agent.manager.dto.StructuredMessagesUploadResult;
import com.openjiuwen.studio.agent.manager.entity.StructuredMessageEntity;
import com.openjiuwen.studio.agent.manager.mapper.StructuredMessageMapper;
import com.openjiuwen.studio.agent.manager.utils.ExcelToJsonConverterUtil;

import lombok.extern.slf4j.Slf4j;

import org.springframework.core.io.Resource;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.CollectionUtils;
import org.springframework.web.multipart.MultipartFile;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/**
 * 消息管理Service
 *
 */
@Slf4j
@Service
public class MessageManagementService implements IMessageManagementService {
    private final StructuredMessageMapper structuredMessageMapper;

    private final I18nUtil i18nUtil;

    public MessageManagementService(StructuredMessageMapper structuredMessageMapper, I18nUtil i18nUtil) {
        this.structuredMessageMapper = structuredMessageMapper;
        this.i18nUtil = i18nUtil;
    }

    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "StructuredMessage",
        description = "创建结构化消息模板",
        resourceId = "-1",
        resourceName = "body.name"
    )
    public StructMessage createStructuredMessages(String projectId, String workspaceId, StructuredInfoRequest body) {
        validateStructuredMessagesName(body.getName());
        if (!CommonConstant.EXCEPTION_CATEGORY.equals(body.getCategory())) {
            throw new AgentStudioException(StudioError.ONLY_SUPPORTED_EXCEPTION_TYPE);
        }
        StructuredMessageEntity newStructuredMessage = new StructuredMessageEntity();
        // 获取所有中文名称
        Set<String> currentNames = getStructuredMessagesCurrentNames(projectId, workspaceId, null);
        if (currentNames.contains(body.getName())) {
            throw new AgentStudioException(StudioError.MESSAGE_TEMPLATE_NAME_REPETITION);
        }
        String newStructuredMessageId = UUID.randomUUID().toString();
        newStructuredMessage.setId(newStructuredMessageId);
        newStructuredMessage.setName(body.getName());
        newStructuredMessage.setCategory(body.getCategory());
        // json注意检查 是否是合理的json 符合ir的规范
        newStructuredMessage.setContentMap(body.getContent());
        // 默认展示 软删除
        newStructuredMessage.setStatus("0");
        // 非导入 网页创建
        newStructuredMessage.setImportMethod("PAGE");
        newStructuredMessage.setVisibility(body.getVisibility().toString());
        newStructuredMessage.setWorkspaceId(workspaceId);
        newStructuredMessage.setDomainId(RequestContextUtils.getRequestUserDomainId());
        newStructuredMessage.setUserId(RequestContextUtils.getRequestUserId());
        newStructuredMessage.setProjectId(projectId);
        // 格式是否满足
        newStructuredMessage.setCreatedOn(new Date());
        newStructuredMessage.setCreatorId(RequestContextUtils.getRequestUserId());
        newStructuredMessage.setUpdatedOn(new Date());
        newStructuredMessage.setUpdaterId(RequestContextUtils.getRequestUserId());
        this.structuredMessageMapper.createStructuredMessage(newStructuredMessage);

        // 构造返回结果
        StructMessage resp = new StructMessage();
        resp.setId(newStructuredMessageId);
        resp.setName(body.getName());
        resp.setCategory(body.getCategory());
        resp.setContent(body.getContent());
        resp.setVisibility(
            ExcelToJsonConverterUtil.REVERSE_VISIBILITY_MAP.getOrDefault(body.getVisibility().toString(), "当前空间内"));
        return resp;
    }

    @Transactional
    @Override
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "StructuredMessage",
        description = "删除结构化消息模板",
        resourceId = "body[0].id",
        resourceName = ""
    )
    public BatchDeleteRsp deleteStructuredMessages(String projectId, String workspaceId,
        List<StructuredInfoRequestDelete> body) {
        List<String> items = new ArrayList<>();
        for (StructuredInfoRequestDelete request : body) {
            String id = request.getId();
            if (id != null && !id.trim().isEmpty()) {
                items.add(id.trim());
            }
        }
        // 如果 items 为空，直接返回成功响应，count 为 0
        if (items.isEmpty()) {
            BatchDeleteRsp structuredMessagesBatchDeleteRsp = new BatchDeleteRsp();
            structuredMessagesBatchDeleteRsp.setIds(new ArrayList<>());
            structuredMessagesBatchDeleteRsp.setCount(0L);
            return structuredMessagesBatchDeleteRsp;
        }
        // 在删除前校验消息模板
        List<StructuredMessageEntity> structuredMessages =
            this.structuredMessageMapper.getByIds(items, RequestContextUtils.getRequestWorkspaceId(),
                RequestContextUtils.getRequestUserDomainId(), RequestContextUtils.getRequestUserId());
        if (structuredMessages.size() != items.size()) {
            // 存在不符合条件的消息模板
            throw new AgentStudioException(StudioError.MESSAGE_TEMPLATE_NOT_FOUND_OR_PERMISSION_DENIED);
        }
        // 批量删除
        this.structuredMessageMapper.deleteByIds(items, projectId);
        BatchDeleteRsp structuredMessagesBatchDeleteRsp = new BatchDeleteRsp();
        structuredMessagesBatchDeleteRsp.setIds(items);
        structuredMessagesBatchDeleteRsp.setCount((long) items.size());
        return structuredMessagesBatchDeleteRsp;
    }

    @Override
    public Resource exportStructuredMessages(String projectId, String workspaceId, ExportMessagesParams body) {
        List<StructMessage> infos = new ArrayList<>();
        // 空 messages_ids 直接返回空导出文件，不查库（与 batchDelete 空 items 短路一致）
        if (!CollectionUtils.isEmpty(body.getMessagesIds())) {
            List<StructuredMessageEntity> structuredMessageEntities =
                this.structuredMessageMapper.getByIds(body.getMessagesIds(), RequestContextUtils.getRequestWorkspaceId(),
                    RequestContextUtils.getRequestUserDomainId(), RequestContextUtils.getRequestUserId());
            structuredMessageEntities
                .forEach(structuredMessageEntity -> infos.add(convertStructMessage(structuredMessageEntity)));
        }
        Resource resource;
        try {
            resource = ExcelToJsonConverterUtil.exportMessagesToExcel(infos);
        } catch (Exception e) {
            log.error("export file:{}, error: {}", i18nUtil.getMessage(StudioError.EXPORT_STRUCTURED_MESSAGES_FAILED),
                e.getMessage());
            throw new AgentStudioException(StudioError.EXPORT_STRUCTURED_MESSAGES_FAILED);
        }
        return resource;
    }

    @Override
    public Resource exportStructuredTemplate(String projectId, String workspaceId) {
        return ExcelToJsonConverterUtil.exportStructuredMessagesTemplate(projectId, workspaceId);
    }

    /**
     * 查询structuredMessages
     *
     * @param projectId projectId
     * @param listStructuredMessagesQo 结构化信息查询体
     * @return listStructuredMessages 根据文件内容解析出来的配置
     */
    @Override
    public StructMessageListRsp listStructuredMessages(String projectId,
        ListStructuredMessagesQo listStructuredMessagesQo) {
        StructuredMessageEntity search = StructuredMessageEntity.builder()
            .workspaceId(listStructuredMessagesQo.getWorkspaceId())
            .name(StrUtils.filterSpecialWords(listStructuredMessagesQo.getName()))
            .category(listStructuredMessagesQo.getCategory())
            .importMethod(listStructuredMessagesQo.getImportMethod())
            .status(listStructuredMessagesQo.getStatus())
            .userId(RequestContextUtils.getRequestUserId())
            .domainId(RequestContextUtils.getRequestUserDomainId())
            .build();
        PageHelper.offsetPage(listStructuredMessagesQo.getOffset(), listStructuredMessagesQo.getLimit());
        List<StructuredMessageEntity> structuredMessageEntities =
            this.structuredMessageMapper.getStructuredMessageEntity(search, listStructuredMessagesQo.getSort());
        PageInfo<StructuredMessageEntity> pageInfo = new PageInfo<>(structuredMessageEntities);
        List<StructMessage> infos = new ArrayList<>();
        pageInfo.getList().forEach(structuredMessageEntity -> infos.add(convertStructMessage(structuredMessageEntity)));
        return new StructMessageListRsp().setCount(pageInfo.getTotal()).setMessageList(infos);
    }

    @Transactional
    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "StructuredMessage",
        description = "更新结构化消息模板",
        resourceId = "workspaceId",
        resourceName = "body.name"
    )
    public StructMessage updateStructuredMessages(String projectId, String workspaceId, StructuredInfoRequest body) {
        // 在更新前校验消息模板是否存在且权限正确
        List<StructuredMessageEntity> existingMessage =
            this.structuredMessageMapper.getByIds(List.of(body.getId()), RequestContextUtils.getRequestWorkspaceId(),
                RequestContextUtils.getRequestUserDomainId(), RequestContextUtils.getRequestUserId());
        if (existingMessage.isEmpty()) {
            throw new AgentStudioException(StudioError.MESSAGE_TEMPLATE_NOT_FOUND_OR_PERMISSION_DENIED);
        }
        validateStructuredMessagesName(body.getName());
        StructuredMessageEntity updateStructuredMessage = new StructuredMessageEntity();
        updateStructuredMessage.setId(body.getId());
        updateStructuredMessage.setName(body.getName());
        Set<String> currentNames = getStructuredMessagesCurrentNames(projectId, workspaceId, body.getId());
        if (currentNames.contains(body.getName())) {
            throw new AgentStudioException(StudioError.MESSAGE_TEMPLATE_NAME_REPETITION);
        }
        updateStructuredMessage.setCategory(body.getCategory());
        if (!CommonConstant.EXCEPTION_CATEGORY.equals(body.getCategory())) {
            throw new AgentStudioException(StudioError.ONLY_SUPPORTED_EXCEPTION_TYPE);
        }
        // json注意检查 是否是合理的json 符合ir的规范
        updateStructuredMessage.setContentMap(body.getContent());
        // 默认展示 软删除
        updateStructuredMessage.setStatus("0");
        // 非导入 网页创建
        updateStructuredMessage.setImportMethod("PAGE");
        updateStructuredMessage.setVisibility(body.getVisibility().toString());
        updateStructuredMessage.setWorkspaceId(workspaceId);
        updateStructuredMessage.setDomainId(RequestContextUtils.getRequestUserDomainId());
        updateStructuredMessage.setUserId(RequestContextUtils.getRequestUserId());
        updateStructuredMessage.setProjectId(projectId);
        // 格式是否满足
        updateStructuredMessage.setUpdatedOn(new Date());
        updateStructuredMessage.setUpdaterId(RequestContextUtils.getRequestUserId());
        this.structuredMessageMapper.updateByPrimaryKey(updateStructuredMessage);
        // 构造返回结果
        StructMessage resp = new StructMessage();
        resp.setId(updateStructuredMessage.getId());
        resp.setName(updateStructuredMessage.getName());
        resp.setCategory(updateStructuredMessage.getCategory());
        resp.setContent(updateStructuredMessage.getContentMap());
        resp.setVisibility(ExcelToJsonConverterUtil.REVERSE_VISIBILITY_MAP
            .getOrDefault(updateStructuredMessage.getVisibility(), "当前空间内"));
        return resp;
    }

    @Override
    @OperationLog(
        operationType = OperationType.IMPORT,
        resourceType = "StructuredMessage",
        description = "导入结构化消息模板",
        resourceId = "-1",
        resourceName = ""
    )
    public StructuredMessagesUploadResult uploadStructuredMessages(String workspaceId, String projectId,
        MultipartFile file) {
        // 创建结果对象

        StructuredMessagesUploadResult result = new StructuredMessagesUploadResult();
        List<StructMessage> successList = new ArrayList<>();
        List<FailedStructuredMessage> failedList = new ArrayList<>();
        // 处理Excel文件
        try {
            // 首先进行Excel文件预检查，防止DOS攻击
            ExcelToJsonConverterUtil.preCheckExcelFile(file);

            List<Map<String, Object>> data = ExcelToJsonConverterUtil.processUploadedExcel(file);
            // 初始化统计 - 注意：行数校验已在预检查阶段完成，这里不需要再次校验
            long totalCount = data.size();
            result.setTotalCount(totalCount);
            for (Map<String, Object> row : data) {
                try {
                    // 处理单行数据
                    StructuredMessageEntity newStructuredMessage = new StructuredMessageEntity();
                    String newStructuredMessageId = UUID.randomUUID().toString();
                    newStructuredMessage.setId(newStructuredMessageId);
                    // 校验并设置name
                    Object nameObj = row.get("name");
                    String name;
                    try {
                        name = String.valueOf(nameObj);
                    } catch (Exception e) {
                        name = "Unnamed_Message_" + System.currentTimeMillis();
                    }
                    if (name == null || name.trim().isEmpty()) {
                        name = "Unnamed_Message_" + System.currentTimeMillis();
                    }
                    validateStructuredMessagesName(name);
                    Set<String> currentNames = getStructuredMessagesCurrentNames(projectId, workspaceId, null);
                    if (currentNames.contains(name)) {
                        throw new AgentStudioException(StudioError.MESSAGE_TEMPLATE_NAME_REPETITION, "消息模板信息名字重复");
                    }
                    newStructuredMessage.setName(name);
                    // 校验并设置category
                    Object categoryObj = row.get("category");
                    String category = categoryObj instanceof String ? (String) categoryObj : "异常";
                    // 目前仅支持异常类型
                    if (!CommonConstant.EXCEPTION_CATEGORY.equals(category)) {
                        throw new AgentStudioException(StudioError.ONLY_SUPPORTED_EXCEPTION_TYPE, "仅支持异常类型");
                    }
                    newStructuredMessage.setCategory(category);

                    // 处理content字段
                    Object contentObj = row.get("content");
                    Map<String, Object> contentMap;
                    if (contentObj instanceof String contentStr) {
                        try {
                            contentMap = JSON.parseObject(contentStr);
                        } catch (Exception e) {
                            throw new AgentStudioException(StudioError.JSON_PARSER_INSTEAD, "不符合JSON格式");
                        }
                    } else {
                        throw new IllegalArgumentException("content字段必须是字符串类型");
                    }
                    newStructuredMessage.setContentMap(contentMap);
                    Object visibilityObj = row.get("visibility");
                    newStructuredMessage
                        .setVisibility(visibilityObj instanceof String ? (String) visibilityObj : "workspace");
                    // 设置其他字段
                    newStructuredMessage.setStatus("0");
                    newStructuredMessage.setImportMethod("UPLOAD");
                    newStructuredMessage.setWorkspaceId(workspaceId);
                    newStructuredMessage.setDomainId(RequestContextUtils.getRequestUserDomainId());
                    newStructuredMessage.setUserId(RequestContextUtils.getRequestUserId());
                    newStructuredMessage.setProjectId(projectId);
                    newStructuredMessage.setCreatedOn(new Date());
                    newStructuredMessage.setCreatorId(RequestContextUtils.getRequestUserId());
                    newStructuredMessage.setUpdatedOn(new Date());
                    newStructuredMessage.setUpdaterId(RequestContextUtils.getRequestUserId());
                    // 保存到数据库
                    try {
                        this.structuredMessageMapper.createStructuredMessage(newStructuredMessage);
                    } catch (Exception e) {
                        // 数据库保存失败
                        throw new IllegalArgumentException("保存失败: " + e.getMessage());
                    }
                    // 转换并添加到成功列表
                    successList.add(convertStructMessage(newStructuredMessage));
                } catch (Exception e) {
                    // 处理单行失败，记录到失败列表
                    FailedStructuredMessage failedItem = new FailedStructuredMessage();
                    Optional.ofNullable(row.get("name"))
                        .map(Object::toString)
                        .ifPresentOrElse(failedItem::setName, () -> failedItem.setName(null) // 或者设置默认值
                        );
                    failedItem.setReason(e.getMessage());
                    failedList.add(failedItem);
                }
            }

            result.setSuccessCount((long) successList.size());
            result.setFailedCount((long) failedList.size());
            result.setSuccessList(successList);
            result.setFailedList(failedList);
        } catch (AgentStudioException exception) {
            log.error("Excel processing failed. projectId={}, userId={}, error code={}", projectId,
                RequestContextUtils.getRequestUserId(), exception.getErrorCode());
            throw exception;
        } catch (Exception exception) {
            log.error("Failed to resolve file. projectId = {}, userId = {}", projectId,
                RequestContextUtils.getRequestUserId());
            throw new AgentStudioException(StudioError.FILE_RESOLVE_FILE);
        }
        return result;
    }

    /**
     * 校验名称是否符合命名规则
     * 规则说明：
     * 1. 名称必须为 2 到 64 个字符
     * 2. 允许的字符包括：中文字、英文字母、数字、下划线、中划线、空格
     * 3. 不允许以空格开头或结尾
     * 4. 不允许为空或 null
     * 如果不符合规则，将抛出 AgentStudioException 异常
     *
     * @param name 要校验的名称字符串
     * @throws AgentStudioException 如果名称不符合规则
     */
    public void validateStructuredMessagesName(String name) {
        // 如果 name 为 null 或空字符串，直接抛出异常
        if (name == null || name.isEmpty()) {
            throw new AgentStudioException(StudioError.STRUCTURED_MESSAGES_NAME_INVALID);
        }

        // 正则表达式说明：
        // ^(?!\\s)：不允许以空格开头
        // (?!.*\\s$)：不允许以空格结尾
        // [\\u4e00-\\u9fa5a-zA-Z0-9_\\- ]：允许中文字、英文字母、数字、下划线、中划线、空格
        // {2,64}：字符长度必须在 2 到 64 之间
        String regex = "^(?!\\s)(?!.*\\s$)[\\u4e00-\\u9fa5a-zA-Z0-9_\\- ]{2,64}$";

        // 如果 name 不符合正则规则，抛出异常
        if (!name.matches(regex)) {
            throw new AgentStudioException(StudioError.STRUCTURED_MESSAGES_NAME_INVALID);
        }
    }

    /**
     * 获取当前项目和工作空间下所有结构化消息的名称集合。
     * 通过构建查询条件，从数据库中查询符合条件的结构化消息实体，
     * 并提取其名称字段，最终返回一个不重复的名称集合。
     *
     * @param projectId 项目ID，用于限定查询范围
     * @param workspaceId 工作空间ID，用于限定查询范围
     * @return 返回所有结构化消息的名称集合（Set<String>）
     */
    public Set<String> getStructuredMessagesCurrentNames(String projectId, String workspaceId, String excludeId) {
        // 构建查询条件
        StructuredMessageEntity search = StructuredMessageEntity.builder()
            .workspaceId(workspaceId)
            .projectId(projectId)
            .userId(RequestContextUtils.getRequestUserId())
            .domainId(RequestContextUtils.getRequestUserDomainId())
            .build();

        // 获取消息列表流
        Stream<StructuredMessageEntity> messageStream =
            this.structuredMessageMapper.getStructuredMessageEntity(search, "desc").stream();

        // 如果提供了需要排除的ID，则过滤掉该记录
        if (excludeId != null && !excludeId.isEmpty()) {
            messageStream = messageStream.filter(message -> !excludeId.equals(message.getId()));
        }

        return messageStream.map(StructuredMessageEntity::getName).collect(Collectors.toSet());
    }

    private StructMessage convertStructMessage(StructuredMessageEntity entity) {
        return new StructMessage().setId(entity.getId())
            .setName(entity.getName())
            .setCategory(entity.getCategory())
            .setContent(entity.getContentMap())
            .setVisibility(
                ExcelToJsonConverterUtil.REVERSE_VISIBILITY_MAP.getOrDefault(entity.getVisibility(), "当前空间内"));
    }
}
