/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.aop;

import com.openjiuwen.studio.agent.common.annotation.OperationLog;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.reflect.MethodSignature;
import org.springframework.stereotype.Component;

import java.lang.reflect.Method;
import java.util.concurrent.TimeUnit;

/**
 * Manager 性能日志切面。
 *
 * <p>对标注了 {@link OperationLog} 的业务方法计时，并将耗时写入独立性能日志文件
 * （由 log4j2.xml 中的 PERFORM_LOGGER 配置，appender 为 ASYNC_ROLLING_FILE_PERFORM）。
 * 与审计日志（AUDIT_LOGGER）保持同一切入点，但性能日志不依赖审计开关，始终记录。
 */
@Aspect
@Component
public class PerformanceLogAspect {

    private static final String PERFORM_LOGGER_NAME = "PERFORM_LOGGER";

    private static final Logger PERFORM_LOGGER = LogManager.getLogger(PERFORM_LOGGER_NAME);

    @Around("@annotation(operationLog)")
    public Object around(ProceedingJoinPoint joinPoint, OperationLog operationLog) throws Throwable {
        long startNanos = System.nanoTime();
        boolean success = true;
        try {
            return joinPoint.proceed();
        } catch (Throwable throwable) {
            success = false;
            throw throwable;
        } finally {
            writePerformanceLog(joinPoint, operationLog, success,
                    TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - startNanos));
        }
    }

    private void writePerformanceLog(ProceedingJoinPoint joinPoint, OperationLog operationLog, boolean success,
            long durationMillis) {
        try {
            MethodSignature signature = (MethodSignature) joinPoint.getSignature();
            Method method = signature.getMethod();
            PERFORM_LOGGER.info("manager|{}|{}|{}|{}", method.getName(), operationLog.resourceType(),
                    durationMillis, success);
        } catch (Exception e) {
            // 性能日志失败不影响主流程，也不回退到主日志，避免对业务造成额外噪音。
        }
    }
}