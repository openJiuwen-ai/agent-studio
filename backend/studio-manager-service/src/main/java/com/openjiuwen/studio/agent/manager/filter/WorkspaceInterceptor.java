/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.filter;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.ThreadLocalUtils;
import com.openjiuwen.studio.agent.manager.entity.WorkSpaceMemberEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkspaceEntity;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMapper;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMemberMapper;
import com.openjiuwen.studio.agent.manager.service.PermissionService;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import org.springframework.web.servlet.HandlerInterceptor;
import org.springframework.web.servlet.HandlerMapping;

import java.io.IOException;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * 校验空间权限
 *
 */
@Component
@Slf4j
public class WorkspaceInterceptor implements HandlerInterceptor {

    // 定义正则表达式模式，仅允许字母、数字、下划线和连字符
    private static final Pattern ID_PATTERN = Pattern.compile("^[a-zA-Z0-9_()-]+$");

    private static final String REGISTERED_URIS = "REGISTERED_URIS";

    private static final Set<String> WHITE_LIST = new HashSet<>(
        Arrays.asList("/v1/agent-builder/**", "/v1/*/agents/*/conversations/**", "/v1/*/agents/*/prompt/build",
            "/v1/*/workflows/*/conversations/**", "/v1/*/agent-manager/workspace",  "/v1/*/agent-manager/workspace/init","/v1/*/agent-manager/applications",
            "/v1/inner-tools/**", "/v1/*/releases", "/v1/*/releases/*", "/v1/agents/chat/**",
            "/v1/workflows/chat/*/conversations/*", "/v1/token/resolve", "/v1/common/**", "/v1/common-console/**", "/v1/common-intern/**",
            "/v1/open/developer/**", "/v1/*/agent-builder/prompt/engineering-tasks/*/variables/export",
            "/v1/*/agent-manager/system/settings", "/v1/*/model-service/status/check", "/v1/health",
            "/v1/*/agent-manager/releases/*",
            "/v1/*/agent-manager/workspace/member/role", "/v1/*/agent-manager/permissions",
            "/v1/*/agent-manager/license", "/v1/*/agent-manager/license/**", "/v1/*/ops/statistic/config",
            "/v2/*/agent-manager/knowledge-bases/images/*",
            "/v1/open/developer/agent-manager/agents/exist/published", "/v1/agent-manager/health",
            "/v1/agent-manager/*/cleannotify", "/v1/model-manager/model-services/subscribe","/v1/*/mcp/server/list",
            "/v1/*/agent-builder/prompt/industry/list", "/v1/*/model-manager/maas-model-services",
            "/v1/*/conversation/sessions/**"));

    @Autowired
    private WorkspaceMapper workspaceMapper;

    @Autowired
    private WorkspaceMemberMapper workSpaceMemberMapper;

    @Autowired
    private PermissionService permissionService;

    /**
     * 处理请求前的验证逻辑，包括验证项目ID和工作区ID的格式、存在性等。
     *
     * @param request HttpServletRequest对象，包含请求信息
     * @param response HttpServletResponse对象，用于发送错误响应
     * @param handler 处理请求的对象
     * @return 如果验证通过，返回true；如果验证失败，返回false
     * @throws Exception 可能抛出的异常
     */
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler)
        throws Exception {
        // 白名单校验
        String requestUri = request.getRequestURI();
        String requestMethod = request.getMethod();

        // 从路径中获取project_id和workspace_id
        String projectId = extractProjectId(request);
        String workspaceId = extractWorkspaceId(request);

        if (isInWhiteList(requestUri)) {
            ThreadLocalUtils.setWorkspaceId(StringUtils.isBlank(workspaceId) ? "" : workspaceId);
            return true;
        }

        // 验证ID格式是否合法
        // 验证workspace_id是否为空（project_id为空时路由匹配不到，不会走到这里）
        if (isEmptyId(workspaceId)) {
            sendErrorResponse(response, HttpServletResponse.SC_BAD_REQUEST,
                "openjiuwen.02001009", "Workspace ID cannot be empty",
                "Please provide a valid Workspace ID in the request parameters.");
            return false;
        }
        if (!isValidId(projectId)) {
            log.error("invalid format, projectId: {}", projectId);
            throw new AgentStudioException(StudioError.PROJECT_ID_INVALID);
        }
        if (!isValidId(workspaceId)) {
            log.error("invalid format, workspaceId: {}", workspaceId);
            throw new AgentStudioException(StudioError.WORKSPACE_FORMAT_INVALID);
        }

        // 验证ID长度是否合法
        if (projectId.length() > 64) {
            log.error("projectId length exceeded: {}", projectId.length());
            sendErrorResponse(response, HttpServletResponse.SC_BAD_REQUEST,
                "openjiuwen.02001010", "Project ID length must be between 1 and 64",
                "Please ensure the Project ID does not exceed 64 characters.");
            return false;
        }
        if (workspaceId.length() > 64) {
            log.error("workspaceId length exceeded: {}", workspaceId.length());
            sendErrorResponse(response, HttpServletResponse.SC_BAD_REQUEST,
                "openjiuwen.02001009", "Workspace ID length must be between 1 and 64",
                "Please ensure the Workspace ID does not exceed 64 characters.");
            return false;
        }

        ThreadLocalUtils.setWorkspaceId(workspaceId);

        // 检查workspace是否存在
        WorkspaceEntity workspaceEntity = workspaceMapper.getWorkspaceByWorkspaceId(projectId, workspaceId);

        if (workspaceEntity == null) {
            log.error("invalid workspace id, projectId: {}, workspaceId: {}", projectId, workspaceId);
            // 如果工作区不存在，发送错误响应并返回false
            throw new AgentStudioException(StudioError.WORKSPACE_ID_INVALID);
        }

        ThreadLocalUtils.setWorkspaceName(workspaceEntity.getName());

        // 空间用户校验
        WorkSpaceMemberEntity workSpaceMemberEntity = workSpaceMemberMapper.selectByMemberIdAndWorkspaceId(
            RequestContextUtils.getRequestUserId(), workspaceId);
        if (ObjectUtils.isEmpty(workSpaceMemberEntity)) {
            log.error("user permission invalid, projectId: {}, workspaceId: {}", projectId, workspaceId);
            throw new AgentStudioException(StudioError.USER_WORKSPACE_PERMISSION_INVALID);
        }

        // 用户权限校验
        // 获取当前所有已分配ROLE权限的请求，如果当前请求未登记ROLE，先放行
        List<String> allRegisteredURI = permissionService.getMergedPermissions().get(REGISTERED_URIS);
        if (checkPermission(allRegisteredURI, requestUri, requestMethod)) {
            List<String> actions = permissionService.getMergedPermissions().get(workSpaceMemberEntity.getRole());
            boolean hasPermission = checkPermission(actions, requestUri, requestMethod);
            if (!hasPermission) {
                log.error("User with workspace role {} has no permission", workSpaceMemberEntity.getRole());
                throw new AgentStudioException(StudioError.USER_NO_PERMISSION_DO_THIS);
            }
        }

        return true;
    }

    /**
     * 判断当前请求是否在权限列表中
     * @param actions 当前role下允许的权限列表
     * @param requestUri 当前请求URI
     * @param requestMethod 当前请求Method
     * @return boolean 当前请求是否在权限列表中
     */
    private boolean checkPermission(List<String> actions, String requestUri, String requestMethod) {
        return actions.stream().map(action -> action.split("#")).filter(parts -> parts.length == 2).anyMatch(parts -> {
            String method = parts[0];
            String uri = parts[1];
            return checkUriPermission(requestUri, uri) && requestMethod.equals(method);
        });
    }

    private boolean isEmptyId(String id) {
        // 检查ID是否为空或者仅包含空白字符
        if (id == null || id.trim().isEmpty()) {
            return true;
        }
        return false;
    }

    /**
     * 检查给定的项目工作区列表中是否存在指定ID的工作区。
     *
     * @param list 项目工作区实体对象的列表
     * @param workspaceId 需要检查的工作区ID
     * @return 如果存在指定ID的工作区则返回true，否则返回false
     */
    private boolean hasWorkspaceWithId(List<WorkspaceEntity> list, String workspaceId) {
        // 使用流操作检查列表中是否存在ID与给定workspaceId相同的工作区
        return list.stream().anyMatch(item -> item.getId().equals(workspaceId));
    }

    /**
     * 检查给定的请求URI是否在白名单中。
     *
     * @param requestUri 要检查的请求URI
     * @return 如果请求URI匹配白名单中的某个模式，则返回true，否则返回false
     */
    private boolean isInWhiteList(String requestUri) {
        // 创建一个AntPathMatcher实例，用于路径匹配
        AntPathMatcher pathMatcher = new AntPathMatcher();
        // 遍历白名单中的每个模式
        for (String pattern : WHITE_LIST) {
            // 如果请求URI与当前模式匹配，则返回true
            if (pathMatcher.match(pattern, requestUri)) {
                return true;
            }
        }
        // 如果没有匹配的模式，返回false
        return false;
    }

    /**
     * 检查给定的请求URI是否路径匹配
     * @param requestUri 要检查的请求URI /v1/1234/tests
     * @param permission 允许的URI /v1/{project_id}/tests
     * @return 是否匹配
     */
    private boolean checkUriPermission(String requestUri, String permission) {
        AntPathMatcher pathMatcher = new AntPathMatcher();
        return pathMatcher.match(permission, requestUri);
    }

    /**
     * 从HttpServletRequest中提取项目ID。
     *
     * @param request 包含路径变量的HttpServletRequest对象
     * @return 从request属性中获取的项目ID，类型为String
     */
    String extractProjectId(HttpServletRequest request) {
        try {
            @SuppressWarnings("unchecked")
            Map<String, String> pathVariables =
                (Map<String, String>) request.getAttribute(HandlerMapping.URI_TEMPLATE_VARIABLES_ATTRIBUTE);

            return pathVariables.get("project_id");
        } catch (Exception e) {
            log.info("api is not exist project id. {}", request.getRequestURI());
            return "";
        }
    }

    /**
     * 从 HttpServletRequest 对象中提取工作区 ID。
     *
     * @param request HttpServletRequest 对象，包含请求信息。
     * @return 返回工作区 ID，类型为 String。
     */
    private String extractWorkspaceId(HttpServletRequest request) {
        // 从请求属性中获取 "workspace_id" 的值, 没有就使用default
        return request.getParameter("workspace_id");
    }

    /**
     * 检查给定的ID是否符合预定义的格式。
     *
     * @param id 需要检查的ID字符串
     * @return 如果ID为空或者不符合格式，则返回false；否则返回true
     */
    private boolean isValidId(String id) {
        // 检查ID是否为空或者仅包含空白字符
        if (id == null || id.trim().isEmpty()) {
            return false;
        }
        // 否则校验是否符合正则表达式
        return ID_PATTERN.matcher(id).matches();
    }

    /**
     * 发送错误响应
     */
    private void sendErrorResponse(HttpServletResponse response, int status, String errorCode, String message, String suggestion) throws IOException {
        response.setStatus(status);
        response.setContentType("application/json;charset=UTF-8");
        response.getWriter().write("{\"error_code\": \"" + errorCode + "\", \"error_msg\": \"" + message + "\", \"error_suggestion\": \"" + suggestion + "\"}");
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler,
        Exception ex) {
        ThreadLocalUtils.clearWorkspaceId();
    }
}
