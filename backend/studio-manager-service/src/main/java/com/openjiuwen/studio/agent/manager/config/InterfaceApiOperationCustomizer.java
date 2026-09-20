/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.config;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.PropertyNamingStrategy;
import com.fasterxml.jackson.databind.annotation.JsonNaming;

import io.swagger.annotations.ApiOperation;
import io.swagger.v3.oas.models.Operation;
import io.swagger.v3.oas.models.parameters.Parameter;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springdoc.core.customizers.OperationCustomizer;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.method.HandlerMethod;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.HashMap;
import java.util.Map;

/**
 * Swagger Codegen v2 生成代码的 springdoc 兼容修正。
 *
 * <p>修正两类问题：
 *
 * <p>1. @ApiOperation summary/description 补填
 * 本项目 48 个 Controller 实现 XxxApi 接口（Swagger Codegen 生成），
 * @ApiOperation 注解在接口方法上，Java 不继承接口方法注解，
 * springdoc 从 Controller 方法（仅有 @Override）读取时找不到 @ApiOperation，
 * 导致 Swagger UI 中接口 summary/description 为空。
 * 若 summary 为空，沿 Controller 类的接口层级查找同名同参方法上的 @ApiOperation，
 * 将其 value 填入 summary，notes 填入 description。
 *
 * <p>2. Qo POJO 参数名修正
 * 本项目 85 个 GET 接口使用 Qo POJO 包装多个 query 参数（Swagger Codegen v2 生成）。
 * springdoc 配置了 default-flat-param-object=true，会将 POJO 展开为独立 query Parameter，
 * 但参数名取 Java 反射字段名（camelCase 如 workspaceId），而非 @JsonProperty 值
 * （snake_case 如 workspace_id）。
 * 通过反射读取方法参数类型中字段的 @JsonProperty 注解值，将 camelCase 参数名替换为 snake_case。
 * 同时支持类级 @JsonNaming 策略（如 SnakeCaseStrategy）。
 *
 * <p>仅影响 OpenAPI 文档生成，不影响运行时行为。
 */
@Component
public class InterfaceApiOperationCustomizer implements OperationCustomizer {

    private static final Logger log = LoggerFactory.getLogger(InterfaceApiOperationCustomizer.class);

    @Override
    public Operation customize(Operation operation, HandlerMethod handlerMethod) {
        fillSummaryFromApiOperation(operation, handlerMethod);
        fixParameterNamesFromJsonProperty(operation, handlerMethod);
        return operation;
    }

    // ─── 1. @ApiOperation summary 补填 ───────────────────────────

    private void fillSummaryFromApiOperation(Operation operation, HandlerMethod handlerMethod) {
        if (StringUtils.hasText(operation.getSummary())) {
            return;
        }

        ApiOperation apiOperation = findApiOperationFromInterface(handlerMethod);
        if (apiOperation != null) {
            operation.setSummary(apiOperation.value());
            if (StringUtils.hasText(apiOperation.notes())) {
                operation.setDescription(apiOperation.notes());
            }
            log.debug("[InterfaceApiOperationCustomizer] Set summary='{}' for {}",
                apiOperation.value(), handlerMethod.getMethod().getName());
        }
    }

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
                }
            }
            current = current.getSuperclass();
        }
        return null;
    }

    // ─── 2. Qo 参数名 @JsonProperty 修正 ──────────────────────────

    private void fixParameterNamesFromJsonProperty(Operation operation, HandlerMethod handlerMethod) {
        if (operation.getParameters() == null || operation.getParameters().isEmpty()) {
            return;
        }

        Map<String, String> nameMap = buildPropertyNameMap(handlerMethod.getMethod());
        if (nameMap.isEmpty()) {
            return;
        }

        int renamed = 0;
        for (Parameter param : operation.getParameters()) {
            String mapped = nameMap.get(param.getName());
            if (mapped != null && !mapped.equals(param.getName())) {
                log.debug("[InterfaceApiOperationCustomizer] Rename parameter '{}' -> '{}' for {}",
                    param.getName(), mapped, handlerMethod.getMethod().getName());
                param.setName(mapped);
                renamed++;
            }
        }

        if (renamed > 0) {
            log.debug("[InterfaceApiOperationCustomizer] Renamed {} parameter(s) for {}",
                renamed, handlerMethod.getMethod().getName());
        }
    }

    private Map<String, String> buildPropertyNameMap(Method method) {
        Map<String, String> nameMap = new HashMap<>();
        for (Class<?> paramType : method.getParameterTypes()) {
            collectJsonPropertyNames(paramType, nameMap);
        }
        return nameMap;
    }

    private void collectJsonPropertyNames(Class<?> clazz, Map<String, String> nameMap) {
        Class<?> current = clazz;
        while (current != null && current != Object.class) {
            PropertyNamingStrategy namingStrategy = resolveNamingStrategy(current);

            for (Field field : current.getDeclaredFields()) {
                if (Modifier.isStatic(field.getModifiers())) {
                    continue;
                }
                String fieldName = field.getName();
                if (nameMap.containsKey(fieldName)) {
                    continue;
                }

                JsonProperty jp = field.getAnnotation(JsonProperty.class);
                if (jp != null && !jp.value().isEmpty() && !"_default".equals(jp.value())) {
                    nameMap.put(fieldName, jp.value());
                } else if (namingStrategy != null) {
                    String translated = translateByStrategy(namingStrategy, fieldName);
                    if (translated != null && !translated.equals(fieldName)) {
                        nameMap.put(fieldName, translated);
                    }
                }
            }

            current = current.getSuperclass();
        }
    }

    private PropertyNamingStrategy resolveNamingStrategy(Class<?> clazz) {
        JsonNaming jsonNaming = clazz.getAnnotation(JsonNaming.class);
        if (jsonNaming == null) {
            return null;
        }
        String strategyName = jsonNaming.value().getSimpleName();
        switch (strategyName) {
            case "SnakeCaseStrategy":
                return PropertyNamingStrategies.SNAKE_CASE;
            case "UpperSnakeCaseStrategy":
                return PropertyNamingStrategies.UPPER_SNAKE_CASE;
            case "KebabCaseStrategy":
                return PropertyNamingStrategies.KEBAB_CASE;
            case "LowerCaseStrategy":
                return PropertyNamingStrategies.LOWER_CASE;
            default:
                return null;
        }
    }

    private String translateByStrategy(PropertyNamingStrategy strategy, String fieldName) {
        if (strategy == PropertyNamingStrategies.SNAKE_CASE) {
            return toSnakeCase(fieldName, false);
        }
        if (strategy == PropertyNamingStrategies.UPPER_SNAKE_CASE) {
            return toSnakeCase(fieldName, true);
        }
        if (strategy == PropertyNamingStrategies.KEBAB_CASE) {
            return toSnakeCase(fieldName, false).replace('_', '-');
        }
        if (strategy == PropertyNamingStrategies.LOWER_CASE) {
            return fieldName.toLowerCase();
        }
        return null;
    }

    private String toSnakeCase(String camelCase, boolean upper) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < camelCase.length(); i++) {
            char c = camelCase.charAt(i);
            if (Character.isUpperCase(c)) {
                if (i > 0) {
                    sb.append('_');
                }
                sb.append(upper ? c : Character.toLowerCase(c));
            } else {
                sb.append(upper ? Character.toUpperCase(c) : c);
            }
        }
        return sb.toString();
    }
}
