/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.conversation.interfaces.controller;

import com.openjiuwen.studio.agent.foundation.connection.model.PageResult;
import com.openjiuwen.studio.conversation.application.ConversationWorkspaceAppService;
import com.openjiuwen.studio.conversation.application.dto.ConversationCreateCmd;
import com.openjiuwen.studio.conversation.application.dto.ConversationDetailVo;
import com.openjiuwen.studio.conversation.application.dto.ConversationListQuery;
import com.openjiuwen.studio.conversation.application.dto.ConversationSkillVo;
import com.openjiuwen.studio.conversation.application.dto.ConversationVo;
import com.openjiuwen.studio.conversation.application.dto.SendMessageCmd;

import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;

import org.springframework.http.HttpHeaders;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;


/**
 * 对话工作台会话接口（挂载 manager 服务）
 */
@Api(tags = "Conversation Workspace")
@RestController
@RequestMapping("/v1/{project_id}/conversation/sessions")
public class ConversationWorkspaceController {

    private final ConversationWorkspaceAppService conversationWorkspaceAppService;

    public ConversationWorkspaceController(ConversationWorkspaceAppService conversationWorkspaceAppService) {
        this.conversationWorkspaceAppService = conversationWorkspaceAppService;
    }

    /**
     * 创建会话
     *
     * @param projectId 租户
     * @param cmd       创建命令
     * @return 会话
     */
    @ApiOperation("创建会话")
    @PostMapping
    public ConversationVo create(@PathVariable("project_id") String projectId,
                                 @ApiParam("空间id") @RequestParam(value = "workspace_id") String workspaceId,
                                 @RequestBody ConversationCreateCmd cmd) {
        return conversationWorkspaceAppService.create(projectId, workspaceId, cmd);
    }

    /**
     * 会话列表（updated_on 倒序，分页）
     *
     * @param projectId   租户
     * @param workspaceId 工作空间
     * @param page        页码（从0开始）
     * @param size        页大小
     * @return 分页结果
     */
    @ApiOperation("会话列表")
    @GetMapping
    public PageResult<ConversationVo> list(@PathVariable("project_id") String projectId,
                                           @ApiParam("空间id") @RequestParam(value = "workspace_id") String workspaceId,
                                           @RequestParam(value = "page", required = false) Integer page,
                                           @RequestParam(value = "size", required = false) Integer size) {
        ConversationListQuery query = new ConversationListQuery();
        query.setPage(page);
        query.setSize(size);
        return conversationWorkspaceAppService.list(projectId, workspaceId, query);
    }

    @ApiOperation("工作空间技能目录")
    @GetMapping("/skills")
    public List<ConversationSkillVo> listSkills(
            @PathVariable("project_id") String projectId,
            @RequestParam("workspace_id") String workspaceId) {
        return conversationWorkspaceAppService.listSkills(projectId, workspaceId);
    }

    /**
     * 会话详情（含全部消息）
     *
     * @param projectId       租户
     * @param workspaceId     工作空间
     * @param conversationId  会话ID
     * @return 详情
     */
    @ApiOperation("会话详情")
    @GetMapping("/{conversation_id}")
    public ConversationDetailVo detail(@PathVariable("project_id") String projectId,
                                       @ApiParam("空间id") @RequestParam(value = "workspace_id") String workspaceId,
                                       @PathVariable("conversation_id") String conversationId) {
        return conversationWorkspaceAppService.detail(projectId, workspaceId, conversationId);
    }

    /**
     * 发送消息（多轮对话入口，SSE 流式返回）
     *
     * @param projectId      租户
     * @param workspaceId    工作空间
     * @param conversationId 会话ID
     * @param cmd            发送消息命令（query/model_deployment_id）
     * @return SSE 流
     */
    @ApiOperation("发送消息（SSE）")
    @PostMapping("/{conversation_id}/messages")
    public SseEmitter sendMessage(@PathVariable("project_id") String projectId,
                                  @ApiParam("空间id") @RequestParam(value = "workspace_id") String workspaceId,
                                  @PathVariable("conversation_id") String conversationId,
                                  @RequestBody SendMessageCmd cmd,
                                  @RequestHeader HttpHeaders httpHeaders) {
        return conversationWorkspaceAppService.sendMessage(projectId, workspaceId, conversationId, cmd, httpHeaders);
    }

    /**
     * 删除会话（软删除）
     *
     * @param projectId      租户
     * @param workspaceId    工作空间
     * @param conversationId 会话ID
     */
    @ApiOperation("删除会话")
    @DeleteMapping("/{conversation_id}")
    public void delete(@PathVariable("project_id") String projectId,
                       @ApiParam("空间id") @RequestParam(value = "workspace_id") String workspaceId,
                       @PathVariable("conversation_id") String conversationId) {
        conversationWorkspaceAppService.delete(projectId, workspaceId, conversationId);
    }
}
