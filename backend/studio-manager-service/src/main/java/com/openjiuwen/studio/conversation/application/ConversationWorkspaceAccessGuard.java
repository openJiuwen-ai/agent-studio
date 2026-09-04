/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.conversation.application;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.entity.WorkSpaceMemberEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkspaceEntity;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMapper;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMemberMapper;

import org.springframework.stereotype.Service;

import java.util.Objects;

/**
 * 对话工作台工作空间访问边界校验。
 */
@Service
public class ConversationWorkspaceAccessGuard {
    private final WorkspaceMapper workspaceMapper;
    private final WorkspaceMemberMapper workspaceMemberMapper;

    public ConversationWorkspaceAccessGuard(WorkspaceMapper workspaceMapper,
                                            WorkspaceMemberMapper workspaceMemberMapper) {
        this.workspaceMapper = workspaceMapper;
        this.workspaceMemberMapper = workspaceMemberMapper;
    }

    public void requireAccess(String projectId, String workspaceId) {
        if (!Objects.equals(projectId, RequestContextUtils.getRequestProjectId())) {
            throw new AgentStudioException(StudioError.USER_WORKSPACE_PERMISSION_INVALID);
        }
        WorkspaceEntity workspace = workspaceMapper.getWorkspaceByWorkspaceId(projectId, workspaceId);
        if (workspace == null) {
            throw new AgentStudioException(StudioError.WORKSPACE_ID_INVALID);
        }
        WorkSpaceMemberEntity member = workspaceMemberMapper.selectByMemberIdAndWorkspaceId(
            RequestContextUtils.getRequestUserId(), workspaceId);
        if (member == null) {
            throw new AgentStudioException(StudioError.USER_WORKSPACE_PERMISSION_INVALID);
        }
    }
}
