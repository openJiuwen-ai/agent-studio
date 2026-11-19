/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.entity.WorkspaceEntity;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMapper;
import com.openjiuwen.studio.agent.manager.service.workspace.WorkspaceMemberService;

import lombok.extern.slf4j.Slf4j;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * 资产广场上架/下架的公共权限校验器。
 *
 * <p>约束（FRS-091 公共横切）：上架/下架资产仅允许空间 OWNER/ADMIN（团队空间）或平台运营方；
 * 平台运营方（op.svc.project-id 对应的运营租户）全权兜底（DEC-10）。</p>
 */
@Slf4j
@Component
public class AssetShelfPermissionValidator {

    @Autowired
    private WorkspaceMapper workspaceMapper;

    @Autowired
    private WorkspaceMemberService workspaceMemberService;

    @Value("${op.svc.project-id}")
    private String opSvcProjectId;

    /**
     * 是否为平台运营租户（运营项目）。
     */
    public boolean isOpTenant(String projectId) {
        return opSvcProjectId != null && opSvcProjectId.equals(projectId);
    }

    /**
     * 校验当前用户具备资产上架/下架权限：
     * <ul>
     *   <li>运营租户：全权放行（DEC-10 兜底）；</li>
     *   <li>团队空间：仅 OWNER/ADMIN；</li>
     *   <li>非团队空间（无成员角色体系）：跨租户越权由各资源归属校验（domainId/项目）拦截。</li>
     * </ul>
     *
     * @param projectId 项目 ID
     * @param workspaceId 空间 ID
     */
    public void checkOwnerOrAdmin(String projectId, String workspaceId) {
        if (isOpTenant(projectId)) {
            return;
        }
        WorkspaceEntity workspace = workspaceMapper.getWorkspaceByWorkspaceId(projectId, workspaceId);
        if (workspace == null) {
            throw new AgentStudioException(StudioError.WORKSPACE_NOT_EXISTED);
        }
        if (CommonConstant.WORKSPACE.TYPE.TEAM_TYPE.equals(workspace.getType())) {
            workspaceMemberService.checkMemberOwnerOrAdminPermission(projectId, workspaceId,
                RequestContextUtils.getRequestUserId());
        }
        // 非团队空间无成员角色体系：跨租户越权由调用方资源归属校验拦截
    }
}