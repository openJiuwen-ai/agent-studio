/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.conversation.application;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.foundation.connection.model.PageResult;
import com.openjiuwen.studio.conversation.application.dto.ConversationCreateCmd;
import com.openjiuwen.studio.conversation.application.dto.ConversationDetailVo;
import com.openjiuwen.studio.conversation.application.dto.ConversationListQuery;
import com.openjiuwen.studio.conversation.application.dto.ConversationSkillContext;
import com.openjiuwen.studio.conversation.application.dto.ConversationSkillVo;
import com.openjiuwen.studio.conversation.application.dto.ConversationVo;
import com.openjiuwen.studio.conversation.application.dto.MessageVo;
import com.openjiuwen.studio.conversation.application.dto.SendMessageCmd;
import com.openjiuwen.studio.conversation.domain.model.Conversation;
import com.openjiuwen.studio.conversation.domain.model.ConversationMessage;
import com.openjiuwen.studio.conversation.domain.model.valueobject.ExecutionRef;
import com.openjiuwen.studio.conversation.domain.model.valueobject.FileRef;
import com.openjiuwen.studio.conversation.domain.repository.ConversationRepository;
import com.openjiuwen.studio.conversation.domain.service.ConversationHistoryAssembler;
import com.openjiuwen.studio.conversation.infrastructure.adapter.AgentRuntimeAdapter;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.Date;
import java.util.List;
import java.util.Objects;
import java.util.UUID;

/**
 * 对话工作台应用服务：会话 CRUD 与消息发送编排（按 project_id+workspace_id+owner_user_id 隔离）
 */
@Slf4j
@Service
public class ConversationWorkspaceAppService {

    public static final String STATUS_ACTIVE = "ACTIVE";
    public static final String DEFAULT_TITLE = "新会话";

    private final ConversationRepository conversationRepository;
    private final ConversationHistoryAssembler conversationHistoryAssembler;
    private final AgentRuntimeAdapter agentRuntimeAdapter;
    private final ConversationSkillResolver conversationSkillResolver;
    private final ConversationWorkspaceAccessGuard conversationWorkspaceAccessGuard;
    private final ConversationAgentResourceResolver conversationAgentResourceResolver;

    public ConversationWorkspaceAppService(ConversationRepository conversationRepository,
                                           ConversationHistoryAssembler conversationHistoryAssembler,
                                           AgentRuntimeAdapter agentRuntimeAdapter,
                                           ConversationSkillResolver conversationSkillResolver,
                                           ConversationWorkspaceAccessGuard conversationWorkspaceAccessGuard,
                                           ConversationAgentResourceResolver conversationAgentResourceResolver) {
        this.conversationRepository = conversationRepository;
        this.conversationHistoryAssembler = conversationHistoryAssembler;
        this.agentRuntimeAdapter = agentRuntimeAdapter;
        this.conversationSkillResolver = conversationSkillResolver;
        this.conversationWorkspaceAccessGuard = conversationWorkspaceAccessGuard;
        this.conversationAgentResourceResolver = conversationAgentResourceResolver;
    }

    /**
     * 查询当前用户域可用的工作空间技能目录。
     *
     * @param projectId   租户
     * @param workspaceId 工作空间
     * @return 浏览器可见的技能目录
     */
    public List<ConversationSkillVo> listSkills(String projectId, String workspaceId) {
        conversationWorkspaceAccessGuard.requireAccess(projectId, workspaceId);
        return conversationSkillResolver.listAvailable(projectId, workspaceId,
            RequestContextUtils.getRequestUserDomainId());
    }

    /**
     * 创建会话
     *
     * @param projectId   租户
     * @param workspaceId 工作空间
     * @param cmd         创建命令
     * @return 会话
     */
    public ConversationVo create(String projectId, String workspaceId, ConversationCreateCmd cmd) {
        Conversation conversation = Conversation.builder()
            .conversationId(UUID.randomUUID().toString())
            .title(StringUtils.isBlank(cmd.getTitle()) ? DEFAULT_TITLE : cmd.getTitle())
            .projectId(projectId)
            .workspaceId(workspaceId)
            .domainId(RequestContextUtils.getRequestUserDomainId())
            .ownerDomainId(RequestContextUtils.getRequestUserDomainId())
            .ownerUserId(RequestContextUtils.getRequestUserId())
            .source(cmd.getSource())
            .status(STATUS_ACTIVE)
            .build();
        conversationRepository.save(conversation);
        return ConversationVo.builder()
            .conversationId(conversation.getConversationId())
            .title(conversation.getTitle())
            .status(conversation.getStatus())
            .source(conversation.getSource())
            .build();
    }

    /**
     * 会话列表（updated_on 倒序，分页）
     *
     * @param projectId   租户
     * @param workspaceId 工作空间
     * @param query       查询条件
     * @return 分页结果
     */
    public PageResult<ConversationVo> list(String projectId, String workspaceId, ConversationListQuery query) {
        String ownerUserId = RequestContextUtils.getRequestUserId();

        long total = conversationRepository.countByOwner(projectId, workspaceId, ownerUserId);
        int page = query.getPage() == null ? 0 : query.getPage();
        int size = query.getSize() == null ? 20 : query.getSize();
        List<ConversationVo> items = conversationRepository
            .listByOwner(projectId, workspaceId, ownerUserId, page, size)
            .stream()
            .map(c -> ConversationVo.builder()
                .conversationId(c.getConversationId())
                .title(c.getTitle())
                .status(c.getStatus())
                .source(c.getSource())
                .createdAt(c.getCreatedAt())
                .updatedAt(c.getUpdatedAt())
                .build())
            .toList();

        PageResult<ConversationVo> pageResult = new PageResult<>();
        pageResult.setTotalCount(total);
        pageResult.setItems(items);
        return pageResult;
    }

    /**
     * 会话详情（含全部消息）
     *
     * @param projectId       租户
     * @param workspaceId     工作空间
     * @param conversationId  会话ID
     * @return 详情
     */
    public ConversationDetailVo detail(String projectId, String workspaceId, String conversationId) {
        Conversation conversation = getOwnedConversation(projectId, workspaceId, conversationId);
        List<MessageVo> messages = conversation.getMessages().stream().map(this::toMessageVo).toList();
        return ConversationDetailVo.builder()
            .conversationId(conversation.getConversationId())
            .title(conversation.getTitle())
            .status(conversation.getStatus())
            .messages(messages)
            .build();
    }

    /**
     * 删除会话（软删除）
     *
     * @param projectId       租户
     * @param workspaceId     工作空间
     * @param conversationId  会话ID
     */
    public void delete(String projectId, String workspaceId, String conversationId) {
        getOwnedConversation(projectId, workspaceId, conversationId);
        conversationRepository.softDelete(conversationId);
    }

    /**
     * 发送消息（多轮对话入口）：落库 user 行 → 全量历史注入 → 触发运行（SSE 流式返回，done 后落库 assistant/工具/子 agent 消息）
     *
     * @param projectId      租户
     * @param workspaceId    工作空间
     * @param conversationId 会话ID
     * @param cmd            发送消息命令
     * @param requestHeaders 当前请求头（转发给 runtime，认证所需的 X-Auth-Token 由 adapter 从 IAM 上下文补齐）
     * @return SSE 流
     */
    public SseEmitter sendMessage(String projectId, String workspaceId, String conversationId, SendMessageCmd cmd,
                                  HttpHeaders requestHeaders) {
        if (cmd == null || StringUtils.isBlank(cmd.getQuery())) {
            throw new AgentStudioException(StudioError.METHOD_ARGUMENT_NOT_VALID, List.of("query is required"));
        }
        String selectType = StringUtils.defaultIfBlank(cmd.getSelectType(), "SUPERVISOR").toUpperCase();
        boolean supervisor = "SUPERVISOR".equals(selectType);
        boolean app = "APP".equals(selectType);
        if (!supervisor && !app) {
            throw new AgentStudioException(StudioError.METHOD_ARGUMENT_NOT_VALID,
                List.of("select_type must be SUPERVISOR or APP"));
        }
        if (supervisor && StringUtils.isBlank(cmd.getModelDeploymentId())) {
            throw new AgentStudioException(StudioError.METHOD_ARGUMENT_NOT_VALID,
                List.of("model_deployment_id is required"));
        }
        if (app && StringUtils.isBlank(cmd.getAppId())) {
            throw new AgentStudioException(StudioError.METHOD_ARGUMENT_NOT_VALID,
                List.of("app_id is required"));
        }
        if (supervisor && StringUtils.isNotBlank(cmd.getAppId())) {
            throw new AgentStudioException(StudioError.METHOD_ARGUMENT_NOT_VALID,
                List.of("app_id is not allowed for SUPERVISOR"));
        }
        if (app && StringUtils.isNotBlank(cmd.getModelDeploymentId())) {
            throw new AgentStudioException(StudioError.METHOD_ARGUMENT_NOT_VALID,
                List.of("model_deployment_id is not allowed for APP"));
        }
        cmd.setSelectType(selectType);
        if (app) {
            conversationAgentResourceResolver.requirePublished(projectId, workspaceId, cmd.getAppId());
        }
        Conversation conversation = getOwnedConversation(projectId, workspaceId, conversationId);
        conversationWorkspaceAccessGuard.requireAccess(projectId, workspaceId);
        ConversationSkillContext skillContext = conversationSkillResolver.resolveForRun(projectId, workspaceId,
            RequestContextUtils.getRequestUserDomainId(), cmd.getRecommendedSkillIds());

        // 本轮 execution_id（调用方生成，经 X-Execution-Id 下发引擎，事件原样携带）
        String executionId = UUID.randomUUID().toString();

        // 运行前落库 user 消息
        ConversationMessage userMessage = ConversationMessage.builder()
            .role("user")
            .content(cmd.getQuery())
            .executionRef(new ExecutionRef(executionId, null, null))
            .fileRefs(toFileRefs(cmd.getFileIds()))
            .modelDeploymentId(cmd.getModelDeploymentId())
            .event("user_message")
            .createdAt(new Date())
            .build();
        conversationRepository.appendMessages(conversationId, List.of(userMessage));

        // 全量历史组装（含工具消息合成）后注入运行链路
        List<Message> histories = conversationHistoryAssembler.assemble(conversation);
        return agentRuntimeAdapter.run(conversation, cmd, histories, skillContext, executionId, requestHeaders);
    }

    /**
     * 加载会话并校验工作空间归属（隔离：project_id+workspace_id+owner_user_id）
     *
     * @param projectId       租户
     * @param workspaceId     工作空间
     * @param conversationId  会话ID
     * @return 会话
     */
    private Conversation getOwnedConversation(String projectId, String workspaceId, String conversationId) {
        Conversation conversation = conversationRepository.findById(conversationId)
            .orElseThrow(() -> new AgentStudioException(StudioError.METHOD_ARGUMENT_NOT_VALID,
                List.of("conversation not found: " + conversationId)));
        if (!Objects.equals(conversation.getProjectId(), projectId)
            || !Objects.equals(conversation.getWorkspaceId(), workspaceId)
            || !Objects.equals(conversation.getDomainId(), RequestContextUtils.getRequestUserDomainId())
            || !Objects.equals(conversation.getOwnerUserId(), RequestContextUtils.getRequestUserId())) {
            throw new AgentStudioException(StudioError.USER_WORKSPACE_PERMISSION_INVALID);
        }
        return conversation;
    }

    private List<FileRef> toFileRefs(List<java.util.Map<String, String>> fileIds) {
        if (fileIds == null || fileIds.isEmpty()) {
            return null;
        }
        return fileIds.stream()
            .map(item -> new FileRef(item.get("url"), item.get("fileName")))
            .filter(item -> StringUtils.isNotBlank(item.getKey()))
            .toList();
    }

    private MessageVo toMessageVo(ConversationMessage message) {
        return MessageVo.builder()
            .role(message.getRole())
            .content(message.getContent())
            .toolId(message.getToolRef() == null ? null : message.getToolRef().getToolId())
            .toolArgs(message.getToolRef() == null ? null : message.getToolRef().getArgs())
            .fileIds(message.getFileRefs() == null ? null
                : com.alibaba.fastjson2.JSON.toJSONString(message.getFileRefs()))
            .executionId(message.getExecutionRef() == null ? null : message.getExecutionRef().getExecutionId())
            .subExecutionId(message.getExecutionRef() == null ? null : message.getExecutionRef().getSubExecutionId())
            .agentId(message.getExecutionRef() == null ? null : message.getExecutionRef().getAgentId())
            .event(message.getEvent())
            .createdAt(message.getCreatedAt())
            .build();
    }
}
