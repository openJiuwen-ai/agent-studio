/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.entity.WorkSpaceMemberEntity;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMemberMapper;

import lombok.extern.slf4j.Slf4j;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * 工作空间资源修改/删除权限校验。
 *
 * <p>角色规则由 role_permissions_interceptor.json 配置驱动，不在代码里硬编码角色：
 * <ul>
 *   <li>URI 在角色 permissions 列表 → 全权放行(OWNER/ADMIN 编辑/删除 URI 配置在 permissions)。</li>
 *   <li>URI 在角色 creatorCheckPermissions 列表 → 需校验资源创建人，仅创建者本人可操作
 *       (DEVELOPER/OPERATOR 编辑/删除 URI 配置在 creatorCheckPermissions)。</li>
 * </ul>
 * 是否需要创建人校验由 {@link PermissionService#isCreatorCheckRequired} 依据配置判断。</p>
 *
 * <p>创建人标识形态不统一，调用方按实际写入形态传 creatorIsUserId：
 * 模型供应商/服务的 createdByUser 存的是 userName(creatorIsUserId=false)；
 * 智能体/工作流的 creatorId 存的是 userId(creatorIsUserId=true)。</p>
 *
 * <p>调用方需显式传 requestMethod + requestUri(与 role_permissions_interceptor.json 中的
 * METHOD#URI 模板一致，如 "DELETE" + "/v1/{project_id}/agent-manager/workflows/{workflow_id}")，
 * 不依赖 RequestContextHolder，避免异步/线程上下文丢失导致静默放行越权。</p>
 */
@Slf4j
@Component
public class WorkspacePermissionValidator {
    @Autowired
    private WorkspaceMemberMapper workspaceMemberMapper;

    @Autowired
    private PermissionService permissionService;

    @Value("${op.svc.project-id}")
    private String opSvcProjectId;

    /**
     * 校验当前用户是否有权修改/删除指定资源。
     *
     * <p>依据 role_permissions_interceptor.json 配置判断当前角色+请求 URI 是否需创建人校验：
     * 需校验则仅创建者本人可操作，否则放行(全权)。管理租户全权跳过。</p>
     *
     * @param projectId 项目id(管理租户全权跳过)
     * @param workspaceId 工作空间id
     * @param creator 资源创建人标识(createdByUser 或 creatorId 的实际值)
     * @param creatorIsUserId 创建人标识是否为 userId：true 对比 getRequestUserId(智能体/工作流 creatorId)；
     *     false 对比 getRequestUserName(模型供应商/服务 createdByUser)
     * @param requestMethod HTTP 方法(如 "DELETE"/"PUT")
     * @param requestUri 请求 URI 模板(如 "/v1/{project_id}/agent-manager/workflows/{workflow_id}")，
     *     与 role_permissions_interceptor.json 中 creatorCheckPermissions 的 URI 段一致
     */
    public void validateModifyPrivilege(String projectId, String workspaceId, String creator,
        boolean creatorIsUserId, String requestMethod, String requestUri, boolean isSystemResource) {
        // 管理租户全权
        if (Objects.equals(projectId, opSvcProjectId)) {
            return;
        }
        String currentUserId = RequestContextUtils.getRequestUserId();
        WorkSpaceMemberEntity member = workspaceMemberMapper.selectByMemberIdAndWorkspaceId(currentUserId,
            workspaceId);
        if (member == null) {
            log.error("user not in workspace, userId:{}, workspaceId:{}", currentUserId, workspaceId);
            throw new AgentStudioException(StudioError.USER_WORKSPACE_PERMISSION_INVALID);
        }
        // 依据配置判断当前角色+请求 URI 是否需要创建人校验(不硬编码角色)
        // fail-closed 语义:URI 不在角色 creatorCheckPermissions 时，需确认在角色 permissions(全权)才放行；
        // 既不在 permissions 也不在 creatorCheckPermissions(配置漏配/内部调用绕过拦截器)则拒绝，
        // 避免拦截器被绕过时静默放行越权。
        // 安全前提:action 常量映射的 URI 必须与 role_permissions_interceptor.json 的
        // creatorCheckPermissions/permissions 保持一致(配置一致性，启动时 verifyActionConfigConsistency 校验)。
        if (!permissionService.isCreatorCheckRequired(member.getRole(), requestMethod, requestUri)) {
            // 不在 creatorCheckPermissions，确认是否在角色 permissions(全权)才放行
            if (permissionService.isPermissionGranted(member.getRole(), requestMethod, requestUri)) {
                return;
            }
            log.error("URI {} {} not in role {} permissions nor creatorCheckPermissions (fail-closed)",
                requestMethod, requestUri, member.getRole());
            throw new AgentStudioException(StudioError.USER_NO_PERMISSION_DO_THIS);
        }
        // 系统/平台资源(无创建人)放行,与前端 canModify 一致,
        // 与 ProviderAuthMgmtService 等系统资源跳过创建人校验一致
        if (isSystemResource) {
            return;
        }
        // 用户资源:creator 为空(历史/导入数据归属不明)fail-closed,避免越权防护被绕过
        String currentIdentifier = creatorIsUserId ? currentUserId : RequestContextUtils.getRequestUserName();
        if (creator == null || creator.isEmpty()) {
            log.error("user resource creator is empty, fail-closed. role={}, {} {}, currentUserId={}",
                member.getRole(), requestMethod, requestUri, currentUserId);
            throw new AgentStudioException(StudioError.NO_CREATOR_PERMISSION);
        }
        if (!Objects.equals(currentIdentifier, creator)) {
            log.error("user {} has no permission to modify resource created by {} (role={}, {} {})",
                currentIdentifier, creator, member.getRole(), requestMethod, requestUri);
            throw new AgentStudioException(StudioError.NO_CREATOR_PERMISSION);
        }
    }

    // ============ 语义化方法:按资源类型 + 操作校验，调用方不写 URI ============
    // 资源操作 -> [method, uriTemplate] 映射(与 role_permissions_interceptor.json 的 creatorCheckPermissions 对应)
    private static final String[][] AGENT_ACTIONS = {
        {"delete", "DELETE", "/v1/{project_id}/agent-manager/agents/{agent_id}"},
        {"edit", "PUT", "/v1/{project_id}/agent-manager/agents/{agent_id}"},
        {"channel-create", "POST", "/v1/{project_id}/agent-manager/agents/{agent_id}/channels"},
        {"channel-modify", "PUT", "/v1/{project_id}/agent-manager/agents/{agent_id}/channels/{channel_id}"},
        {"channel-delete", "DELETE", "/v1/{project_id}/agent-manager/agents/{agent_id}/channels/{channel_id}"},
        {"version-create", "POST", "/v1/{project_id}/agent-manager/agents/{agent_id}/versions"},
        {"version-delete", "DELETE", "/v1/{project_id}/agent-manager/agents/{agent_id}/versions/{version_id}"},
        {"version-batch-delete", "POST", "/v1/{project_id}/agent-manager/agents/{agent_id}/versions/batch-delete"},
    };
    private static final String[][] WORKFLOW_ACTIONS = {
        {"delete", "DELETE", "/v1/{project_id}/agent-manager/workflows/{workflow_id}"},
        {"edit", "PUT", "/v1/{project_id}/agent-manager/workflows/{workflow_id}"},
        {"channel-create", "POST", "/v1/{project_id}/agent-manager/workflows/{workflow_id}/channels"},
        {"channel-modify", "PUT", "/v1/{project_id}/agent-manager/workflows/{workflow_id}/channels/{channel_id}"},
        {"channel-delete", "DELETE", "/v1/{project_id}/agent-manager/workflows/{workflow_id}/channels/{channel_id}"},
        {"test-status", "PUT", "/v1/{project_id}/agent-manager/workflows/{workflow_id}/test-status"},
        {"trigger-add", "POST", "/v1/{project_id}/agent-manager/workflows/{workflow_id}/triggers/add"},
        {"trigger-edit", "POST", "/v1/{project_id}/agent-manager/workflows/{workflow_id}/triggers/edit"},
        {"trigger-delete", "DELETE", "/v1/{project_id}/agent-manager/workflows/{workflow_id}/triggers/{trigger_id}"},
        {"version-create", "POST", "/v1/{project_id}/agent-manager/workflows/{workflow_id}/versions"},
        {"version-delete", "DELETE", "/v1/{project_id}/agent-manager/workflows/{workflow_id}/versions/{version_id}"},
        {"version-batch-delete", "POST", "/v1/{project_id}/agent-manager/workflows/{workflow_id}/versions/batch-delete"},
    };
    private static final String[][] PROVIDER_ACTIONS = {
        {"delete", "DELETE", "/v1/{project_id}/model-manager/integration/providers/{id}"},
        {"edit", "PUT", "/v1/{project_id}/model-manager/integration/providers/{id}"},
        {"auth", "POST", "/v1/{project_id}/model-manager/provider/auths"},
        {"auth-info", "PUT", "/v1/{project_id}/agent-manager/integration/providers/auth-info/{id}"},
        {"auth-create", "POST", "/v1/{project_id}/model-manager/provider/auths"},
        {"auth-delete", "DELETE", "/v1/{project_id}/model-manager/provider/auths"},
        {"auth-delete-id", "DELETE", "/v1/{project_id}/model-manager/provider/auths/{id}"},
    };
    private static final String[][] MODEL_SERVICE_ACTIONS = {
        {"delete", "DELETE", "/v1/{project_id}/model-manager/model-services/{id}"},
        {"edit", "PUT", "/v1/{project_id}/model-manager/model-services/{id}"},
        {"online", "POST", "/v1/{project_id}/model-manager/model-services/{id}/online"},
        {"offline", "POST", "/v1/{project_id}/model-manager/model-services/{id}/offline"},
    };

    // 智能体创建人校验(creatorId=userId)。action: delete/edit/channel-create/channel-modify/channel-delete/version-*
    // isSystemResource: 系统预置智能体(无创建人)传 true 放行,用户智能体传 false(creator 为空 fail-closed)
    public void validateAgent(String projectId, String workspaceId, String creator, String action,
        boolean isSystemResource) {
        validateByAction(AGENT_ACTIONS, action, projectId, workspaceId, creator, true, isSystemResource);
    }

    // 工作流创建人校验(creatorId=userId)。action: delete/edit/channel-*/test-status/trigger-*/version-*
    public void validateWorkflow(String projectId, String workspaceId, String creator, String action,
        boolean isSystemResource) {
        validateByAction(WORKFLOW_ACTIONS, action, projectId, workspaceId, creator, true, isSystemResource);
    }

    // 模型供应商创建人校验(createdByUser=userName)。action: delete/edit/auth*
    public void validateProvider(String projectId, String workspaceId, String creator, String action,
        boolean isSystemResource) {
        validateByAction(PROVIDER_ACTIONS, action, projectId, workspaceId, creator, false, isSystemResource);
    }

    // 模型服务创建人校验(createdByUser=userName)。action: delete/edit/online/offline
    public void validateModelService(String projectId, String workspaceId, String creator, String action,
        boolean isSystemResource) {
        validateByAction(MODEL_SERVICE_ACTIONS, action, projectId, workspaceId, creator, false, isSystemResource);
    }

    private void validateByAction(String[][] actions, String action, String projectId, String workspaceId,
        String creator, boolean creatorIsUserId, boolean isSystemResource) {
        String[] entry = null;
        for (String[] a : actions) {
            if (a[0].equals(action)) {
                entry = a;
                break;
            }
        }
        if (entry == null) {
            // 未知 action 属编程错误，fail-closed 拒绝(避免笔误静默放行越权)
            throw new IllegalArgumentException("Unknown action: " + action);
        }
        validateModifyPrivilege(projectId, workspaceId, creator, creatorIsUserId, entry[1], entry[2],
            isSystemResource);
    }

    /**
     * 启动时校验 action 常量映射的 URI 与 role_permissions_interceptor.json 的 creatorCheckPermissions
     * 一致性。若 action 常量映射的 URI 未配在 DEVELOPER/OPERATOR 的 creatorCheckPermissions 里
     * (配置漂移)，会 warn 提示——这种 URI 对所有角色 isCreatorCheckRequired 都返回 false(全权放行)，
     * 形成越权缺口。仅 WARN 不阻塞启动(配置修复后重启即恢复)。
     * 由 PermissionLoader.run 末尾调用(配置加载完后校验，避免 @PostConstruct 时序问题)。
     */
    public void verifyActionConfigConsistency() {
        String[][][] allActions = {AGENT_ACTIONS, WORKFLOW_ACTIONS, PROVIDER_ACTIONS, MODEL_SERVICE_ACTIONS};
        Map<String, List<String>> creatorCheck = permissionService.getMergedCreatorCheckPermissions();
        for (String[][] actions : allActions) {
            for (String[] entry : actions) {
                String method = entry[1];
                String uri = entry[2];
                // 遍历所有配置了 creatorCheckPermissions 的角色(不硬编码角色名)，
                // 校验 action 常量映射的 URI 是否至少在一个角色的 creatorCheckPermissions 里
                boolean inAnyRole = creatorCheck.entrySet().stream()
                    .anyMatch(e -> !"REGISTERED_URIS".equals(e.getKey())
                        && inCreatorCheck(e.getValue(), method, uri));
                if (!inAnyRole) {
                    log.warn("[perm-config] action '{}' URI '{}#{}' not in any role's creatorCheckPermissions; "
                        + "isCreatorCheckRequired will return false for all roles (fail-open). "
                        + "Check role_permissions_interceptor.json consistency.", entry[0], method, uri);
                }
            }
        }
    }

    private boolean inCreatorCheck(List<String> list, String method, String uri) {
        if (list == null) return false;
        return list.stream().anyMatch(a -> {
            int idx = a.indexOf('#');
            return idx > 0 && a.substring(0, idx).equals(method) && a.substring(idx + 1).equals(uri);
        });
    }
}
