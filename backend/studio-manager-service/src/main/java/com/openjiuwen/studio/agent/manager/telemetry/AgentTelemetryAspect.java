/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.telemetry;

import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.dto.AgentInfo;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.service.AgentManagementService;

import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Pointcut;
import org.aspectj.lang.reflect.MethodSignature;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/**
 * agent 生命周期事件遥测切面。
 *
 * <p>拦截 {@link AgentManagementService} 的 agent 增 / 复制 / 改 / 发布 / 删 五个写入口，
 * 方法成功且事务提交后（afterCommit）发送 OTLP logs 生命周期事件。
 * 开关关闭时直接放行，任何上报失败仅记录告警，不影响业务流程。
 */
@Aspect
@Component
@Slf4j
public class AgentTelemetryAspect {

    private final AgentTelemetryService telemetryService;

    private final AgentMapper agentMapper;

    public AgentTelemetryAspect(AgentTelemetryService telemetryService, AgentMapper agentMapper) {
        this.telemetryService = telemetryService;
        this.agentMapper = agentMapper;
    }

    /**
     * agent 定义态写入口：创建 / 复制（创建）/ 修改 / 删除 / 发布
     */
    @Pointcut("execution(* com.openjiuwen.studio.agent.manager.service.AgentManagementService.createAgent(..))"
        + " || execution(* com.openjiuwen.studio.agent.manager.service.AgentManagementService.copyAgent(..))"
        + " || execution(* com.openjiuwen.studio.agent.manager.service.AgentManagementService.modifyAgent(..))"
        + " || execution(* com.openjiuwen.studio.agent.manager.service.AgentManagementService.deleteAgent(..))"
        + " || execution(* com.openjiuwen.studio.agent.manager.service.AgentManagementService.publishAgent(..))")
    public void agentWriteMethods() {
    }

    @Around("agentWriteMethods()")
    public Object aroundAgentWrite(ProceedingJoinPoint joinPoint) throws Throwable {
        if (!telemetryService.isEnabled()) {
            return joinPoint.proceed();
        }

        String methodName = joinPoint.getSignature().getName();
        boolean isDelete = "deleteAgent".equals(methodName);

        String projectId = stringArg(joinPoint, "projectId");
        String workspaceId = stringArg(joinPoint, "workspaceId");
        String agentId = stringArg(joinPoint, "agentId");

        // 删除事件属性来自删除前捕获的实体：方法返回后记录已迁移/删除，查不到了
        Agent capturedAgent = null;
        if (isDelete && agentId != null && projectId != null) {
            try {
                capturedAgent = agentMapper.selectByPrimaryKey(projectId, agentId);
            } catch (Exception e) {
                log.warn("agent telemetry: failed to capture agent before delete: {}", e.getMessage());
            }
        }

        Object result = joinPoint.proceed();

        try {
            String operator = resolveOperator();
            if (isDelete) {
                final Agent captured = capturedAgent;
                scheduleEmit(() -> telemetryService
                    .emitDeletedEvent(captured, projectId, workspaceId, agentId, operator));
            } else if (result instanceof AgentInfo info) {
                String eventType = resolveEventType(methodName);
                scheduleEmit(() -> telemetryService
                    .emitEvent(eventType, projectId, workspaceId, info, operator));
            } else {
                log.debug("agent telemetry: skip emit for {}, unexpected result type {}",
                    methodName, result == null ? "null" : result.getClass().getSimpleName());
            }
        } catch (Exception e) {
            log.warn("agent telemetry: emit lifecycle event failed: {}", e.getMessage());
        }
        return result;
    }

    private String resolveEventType(String methodName) {
        return switch (methodName) {
            case "createAgent", "copyAgent" -> AgentTelemetryService.EVENT_CREATED;
            case "modifyAgent" -> AgentTelemetryService.EVENT_UPDATED;
            case "publishAgent" -> AgentTelemetryService.EVENT_PUBLISHED;
            default -> AgentTelemetryService.EVENT_UPDATED;
        };
    }

    private String resolveOperator() {
        try {
            String name = RequestContextUtils.getRequestUserName();
            if (StringUtils.isNotBlank(name)) {
                return name;
            }
            return RequestContextUtils.getRequestUserId();
        } catch (Exception e) {
            return "";
        }
    }

    /**
     * 事务提交成功后再发送事件，保证事件与 DB 落库一致；
     * 无活动事务（理论上不出现，写方法均有 @Transactional）时直接发送。
     */
    private void scheduleEmit(Runnable emit) {
        if (TransactionSynchronizationManager.isSynchronizationActive()) {
            TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                @Override
                public void afterCommit() {
                    emit.run();
                }
            });
        } else {
            emit.run();
        }
    }

    private String stringArg(ProceedingJoinPoint joinPoint, String paramName) {
        try {
            MethodSignature signature = (MethodSignature) joinPoint.getSignature();
            String[] paramNames = signature.getParameterNames();
            Object[] args = joinPoint.getArgs();
            if (paramNames == null) {
                return null;
            }
            for (int i = 0; i < paramNames.length && i < args.length; i++) {
                if (paramName.equals(paramNames[i]) && args[i] != null) {
                    return String.valueOf(args[i]);
                }
            }
        } catch (Exception e) {
            log.debug("agent telemetry: resolve param {} failed: {}", paramName, e.getMessage());
        }
        return null;
    }
}
