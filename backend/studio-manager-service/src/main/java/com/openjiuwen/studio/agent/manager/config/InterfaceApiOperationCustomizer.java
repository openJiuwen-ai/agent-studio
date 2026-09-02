/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.config;

import io.swagger.annotations.ApiOperation;
import io.swagger.v3.oas.models.Operation;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springdoc.core.customizers.OperationCustomizer;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.method.HandlerMethod;

import java.lang.reflect.Method;

/**
 * 从 Controller 实现的接口方法上读取 Swagger 2 @ApiOperation 注解，
 * 补填到 springdoc 生成的 Operation 中。
 *
 * <p>背景：本项目 48 个 Controller 实现 XxxApi 接口（Swagger Codegen 生成），
 * @ApiOperation 注解在接口方法上，Java 不继承接口方法注解，
 * springdoc 从 Controller 方法（仅有 @Override）读取时找不到 @ApiOperation，
 * 导致 Swagger UI 中接口 summary/description 为空。
 *
 * <p>此 Customizer 在 springdoc 生成 Operation 后检查：
 * 若 summary 为空，沿 Controller 类的接口层级查找同名同参方法上的 @ApiOperation，
 * 将其 value 填入 summary，notes 填入 description。
 */
@Component
public class InterfaceApiOperationCustomizer implements OperationCustomizer {

    private static final Logger log = LoggerFactory.getLogger(InterfaceApiOperationCustomizer.class);

    @Override
    public Operation customize(Operation operation, HandlerMethod handlerMethod) {
        if (StringUtils.hasText(operation.getSummary())) {
            return operation;
        }

        ApiOperation apiOperation = findApiOperationFromInterface(handlerMethod);
        if (apiOperation != null) {
            operation.setSummary(apiOperation.value());
            if (StringUtils.hasText(apiOperation.notes())) {
                operation.setDescription(apiOperation.notes());
            }
            log.debug("[InterfaceApiOperationCustomizer] Set summary='{}' for {}",
                apiOperation.value(), handlerMethod.getMethod().getName());
        } else {
            log.debug("[InterfaceApiOperationCustomizer] No @ApiOperation found for {} on {}",
                handlerMethod.getMethod().getName(), handlerMethod.getBeanType().getSimpleName());
        }

        return operation;
    }

    /**
     * 沿 Controller 类的继承链搜索接口方法上的 @ApiOperation。
     */
    private ApiOperation findApiOperationFromInterface(HandlerMethod handlerMethod) {
        Method method = handlerMethod.getMethod();
        Class<?>[] paramTypes = method.getParameterTypes();
        Class<?> current = handlerMethod.getBeanType();

        while (current != null && current != Object.class) {
            for (Class<?> iface : current.getInterfaces()) {
                try {
                    Method ifaceMethod = iface.getDeclaredMethod(method.getName(), paramTypes);
                    ApiOperation anno = ifaceMethod.getAnnotation(ApiOperation.class);
                    if (anno != null) {
                        return anno;
                    }
                } catch (NoSuchMethodException ignored) {
                    // 当前接口不包含此方法，继续搜索
                }
            }
            current = current.getSuperclass();
        }
        return null;
    }
}
