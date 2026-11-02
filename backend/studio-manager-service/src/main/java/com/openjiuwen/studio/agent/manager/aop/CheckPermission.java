/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.aop;

import com.openjiuwen.studio.agent.common.annotation.ValidPermission;
import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.entity.WorkSpaceMemberEntity;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMemberMapper;
import com.openjiuwen.studio.agent.manager.service.PermissionService;

import lombok.extern.slf4j.Slf4j;

import org.aspectj.lang.JoinPoint;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Before;
import org.aspectj.lang.annotation.Pointcut;
import org.aspectj.lang.reflect.MethodSignature;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;
import org.springframework.util.ObjectUtils;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.util.ArrayList;
import java.util.List;

/**
 * 接口权限校验
 *
 */
@Aspect
@Component
@Slf4j
@ConditionalOnProperty(name = "permission-switch", havingValue = "true")
public class CheckPermission {

    @Autowired
    private PermissionService permissionService;

    @Autowired
    WorkspaceMemberMapper workSpaceMemberMapper;

    @Pointcut("@annotation(com.openjiuwen.studio.agent.common.annotation.ValidPermission))")
    public void check() {
    }

    @Before("check()")
    public void checkPermission(JoinPoint joinPoint) {
        // 系统用户免校验：跳过权限校验
        ServletRequestAttributes requestAttributes = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        if (requestAttributes != null
            && Boolean.TRUE.equals(requestAttributes.getRequest().getAttribute(Constants.SYSTEM_USER_SKIP_ATTR))) {
            log.info("System user skip permission check");
            return;
        }

        List<String> actions = new ArrayList<>();

        log.info("start to check permission!");
        // 根据projectId、workspaceId和userid查询当前所属角色
        log.info("start to get user role, userId is {}, workspace id is {}", RequestContextUtils.getRequestUserId(),
            RequestContextUtils.getRequestWorkspaceId());
        WorkSpaceMemberEntity workSpaceMemberEntity = workSpaceMemberMapper.selectByMemberIdAndWorkspaceId(
            RequestContextUtils.getRequestUserId(), RequestContextUtils.getRequestWorkspaceId());

        if (ObjectUtils.isEmpty(workSpaceMemberEntity)) {
            log.error("the user is not in the workspace");
            throw new AgentStudioException(StudioError.USER_WORKSPACE_PERMISSION_INVALID);
        }

        actions.addAll(permissionService.getMergedPermissions().get(workSpaceMemberEntity.getRole()));

        // 获取方法上的注解
        MethodSignature signature = (MethodSignature) joinPoint.getSignature();
        ValidPermission validPermission = signature.getMethod().getAnnotation(ValidPermission.class);

        if (!actions.contains(validPermission.value())) {
            log.error("the user in the workspace role is {}, no permission do {}", workSpaceMemberEntity.getRole(),
                validPermission.value());
            throw new AgentStudioException(StudioError.USER_NO_PERMISSION_DO_THIS);
        }
        log.info("end check permission!");
    }
}
