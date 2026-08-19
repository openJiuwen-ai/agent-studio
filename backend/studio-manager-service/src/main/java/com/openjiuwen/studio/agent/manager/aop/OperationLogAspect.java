/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.aop;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONWriter;
import com.openjiuwen.studio.agent.common.annotation.OperationLog;
import com.openjiuwen.studio.agent.common.dto.AuditLogEntry;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;

import jakarta.annotation.PostConstruct;
import org.apache.commons.lang3.StringUtils;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.ThreadContext;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.reflect.MethodSignature;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.lang.reflect.Array;
import java.lang.reflect.Method;
import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;

/**
 * 操作审计日志切面。
 *
 * <p>拦截所有标注了 {@link OperationLog} 的方法，将审计信息以 JSON 格式
 * 写入独立的审计日志文件（由 log4j2.xml 中的 AUDIT_LOGGER 配置）。
 *
 * <p>支持三种 resourceId 配置格式：
 * 1. 参数名字：如 "agentId" 表示从 agentId 参数获取
 * 2. 对象属性路径：如 "body.id" 表示从 body 参数的 id 属性获取
 * 3. 数组下标访问：如 "body.ids[0]" 表示从 body 参数的 ids 数组获取第一个元素
 */
@Aspect
@Component
public class OperationLogAspect {

    private static final String AUDIT_LOGGER_NAME = "AUDIT_LOGGER";

    private static final Logger AUDIT_LOGGER = LogManager.getLogger(AUDIT_LOGGER_NAME);//获取审计日志专用Logger

    private static final Logger LOGGER = LogManager.getLogger(OperationLogAspect.class);//用于记录切面自身错误的Logger

    private static final String MASK_REPLACEMENT = "******";

    // 命中敏感字段名后，最多将后续 value 内容的这段长度替换成 ******。
    private static final int SENSITIVE_VALUE_MASK_LENGTH = 12;

    @Value("${studio.operationLog.switch:false}")
    private boolean operationLogSwitch;

    @Value("${studio.operationLog.sensitiveFieldPattern:}")
    private String sensitiveFieldPattern;

    private Pattern compiledSensitiveFieldPattern;

    @PostConstruct
    private void initSensitiveFieldPattern() {
        compiledSensitiveFieldPattern = compileSensitiveFieldPattern(sensitiveFieldPattern).orElse(null);
    }

    @Around("@annotation(operationLog)")
    public Object around(ProceedingJoinPoint joinPoint, OperationLog operationLog) throws Throwable {
        if (!operationLogSwitch) {
            return joinPoint.proceed();
        }

        Object result = null;
        Throwable throwable = null;

        try {
            result = joinPoint.proceed();
            return result;
        } catch (Throwable ex) {
            throwable = ex;
            throw ex;
        } finally {
            writeAuditLog(joinPoint, operationLog, throwable);
        }
    }

    private void writeAuditLog(ProceedingJoinPoint joinPoint, OperationLog operationLog, Throwable throwable) {
        try {
            AuditLogEntry.AuditLogEntryBuilder builder = AuditLogEntry.builder()
                    .timestamp(Instant.now().toString())
                    .operationType(operationLog.operationType().getValue())
                    .success(throwable == null)
                    .errorMessage(throwable != null ? throwable.getMessage() : null);
            builder.userId(RequestContextUtils.getRequestUserId());
            builder.userName(RequestContextUtils.getRequestUserName());

            // TraceId from MDC or ThreadContext
            String traceId = ThreadContext.get("request-id");
            if (traceId != null) {
                builder.traceId(traceId);
            }

            // 方法签名信息
            MethodSignature signature = (MethodSignature) joinPoint.getSignature();
            Method method = signature.getMethod();
            builder.method(method.getName());

            // 资源类型（优先使用注解值，否则从类名推断）
            String resourceType = operationLog.resourceType();
            if (resourceType == null || resourceType.isEmpty()) {
                resourceType = inferResourceType(signature.getDeclaringType().getSimpleName());
            }
            builder.resourceType(resourceType);

            // 描述
            String description = operationLog.description();
            if (description != null && !description.isEmpty()) {
                builder.description(description);
            } else {
                builder.description(String.format("%s %s", operationLog.operationType().getValue(), resourceType));
            }

            // 资源ID（从方法参数中提取）
            String resourceId = extractResourceId(joinPoint, operationLog.resourceId());
            if (resourceId != null) {
                builder.resourceId(resourceId);
            }

            // 资源名称（从方法参数中提取）
            String resourceName = extractResourceId(joinPoint, operationLog.resourceName());
            builder.resourceName(resourceName != null ? resourceName : "");

            // 参数整体序列化为字符串后脱敏，避免递归解析用户对象结构。
            Map<String, Object> paramsMap = getMethodParamsMap(joinPoint);
            builder.params(paramsMap);

            AuditLogEntry entry = builder.build();
            String json = JSON.toJSONString(entry);
            AUDIT_LOGGER.info(json);

        } catch (Exception e) {
            LOGGER.warn("Failed to write audit log, falling back to main log", e);
        }
    }

    private Map<String, Object> getMethodParamsMap(ProceedingJoinPoint joinPoint) {
        try {
            MethodSignature signature = (MethodSignature) joinPoint.getSignature();
            String[] paramNames = signature.getParameterNames();
            Object[] args = joinPoint.getArgs();

            if (paramNames == null || args == null || paramNames.length != args.length) {
                LOGGER.warn("Failed to build audit log params because parameter names and args do not match");
                return new HashMap<>();
            }

            Map<String, Object> rawParams = new HashMap<>();
            for (int i = 0; i < paramNames.length; i++) {
                rawParams.put(paramNames[i], args[i]);
            }

            String paramsJson = JSON.toJSONString(rawParams, JSONWriter.Feature.ReferenceDetection,
                    JSONWriter.Feature.IgnoreErrorGetter);
            Map<String, Object> params = JSON.parseObject(maskSensitiveText(paramsJson));
            return params != null ? params : new HashMap<>();
        } catch (Exception e) {
            LOGGER.warn("Failed to build audit log params, falling back to empty params", e);
            return new HashMap<>();
        }
    }

    /**
     * 根据 resourceId 提取资源ID。
     * 支持三种格式：
     * 1. 参数名字：如 "agentId" 表示从 agentId 参数获取
     * 2. 对象属性路径：如 "body.id" 表示从 body 参数的 id 属性获取
     * 3. 数组下标访问：如 "body.ids[0]" 表示从 body 参数的 ids 数组获取第一个元素
     */
    private String extractResourceId(ProceedingJoinPoint joinPoint, String resourceId) {
        if (resourceId == null || resourceId.isEmpty()) {
            return null;
        }

        try {
            MethodSignature signature = (MethodSignature) joinPoint.getSignature();
            String[] paramNames = signature.getParameterNames();
            Object[] args = joinPoint.getArgs();

            if (paramNames == null || args == null) {
                return null;
            }

            // 找到参数索引
            String paramName;
            String propertyPath;

            if (resourceId.contains(".")) {
                // 对象属性路径，如 "body.id"
                String[] parts = resourceId.split("\\.", 2);
                paramName = parts[0];
                propertyPath = parts[1];
            } else {
                // 纯参数名，如 "agentId"
                paramName = resourceId;
                propertyPath = null;
            }

            // 找到匹配的参数
            int paramIndex = -1;
            for (int i = 0; i < paramNames.length; i++) {
                if (paramNames[i].equals(paramName)) {
                    paramIndex = i;
                    break;
                }
            }

            if (paramIndex < 0 || paramIndex >= args.length || args[paramIndex] == null) {
                return null;
            }

            if (propertyPath == null || propertyPath.isEmpty()) {
                // 直接返回参数值
                return String.valueOf(args[paramIndex]);
            } else {
                // 从对象属性提取
                return extractPropertyValue(args[paramIndex], propertyPath);
            }
        } catch (Exception e) {
            LOGGER.warn("Failed to write audit log when extractResourceId, falling back to main log", e);
        }
        return null;
    }

    /**
     * 从对象中提取属性值，支持嵌套属性路径和数组下标访问。
     * 支持格式：
     * - "id" - 直接获取 id 属性
     * - "body.id" - 先获取 body，再获取其 id 属性
     * - "ids[0]" - 从 ids 数组获取第一个元素
     * - "body.ids[0]" - 从 body 的 ids 数组获取第一个元素
     */
    private String extractPropertyValue(Object obj, String propertyPath) {
        if (obj == null || propertyPath == null || propertyPath.isEmpty()) {
            return null;
        }

        try {
            // 处理数组下标访问，如 "ids[0]" 或 "body.ids[0]"
            if (propertyPath.contains("[")) {
                int bracketIndex = propertyPath.indexOf('[');
                String arrayProperty = propertyPath.substring(0, bracketIndex);
                int arrayIndex = Integer.parseInt(propertyPath.substring(bracketIndex + 1, propertyPath.indexOf(']')));
                String remainingPath = propertyPath.substring(propertyPath.indexOf(']') + 1);

                // 获取数组
                Object array = getPropertyValue(obj, arrayProperty);
                if (array == null) {
                    return null;
                }

                // 获取数组元素
                Object element = null;
                if (array instanceof java.util.List) {
                    java.util.List<?> list = (java.util.List<?>) array;
                    if (arrayIndex >= 0 && arrayIndex < list.size()) {
                        element = list.get(arrayIndex);
                    }
                } else if (array.getClass().isArray()) {
                    int arrayLength = Array.getLength(array);
                    if (arrayIndex >= 0 && arrayIndex < arrayLength) {
                        element = Array.get(array, arrayIndex);
                    }
                }

                // 如果还有剩余路径，继续递归
                if (remainingPath.isEmpty()) {
                    return element != null ? String.valueOf(element) : null;
                }
                return extractPropertyValue(element, remainingPath.substring(1));
            }
            // 普通属性访问
            else {
                Object value = getPropertyValue(obj, propertyPath);
                return value != null ? String.valueOf(value) : null;
            }
        } catch (Exception e) {
            LOGGER.warn("Failed to write audit log when extractPropertyValue, falling back to main log", e);
            return null;
        }
    }

    /**
     * 获取对象的属性值
     */
    private Object getPropertyValue(Object obj, String propertyName) {
        if (obj == null || propertyName == null || propertyName.isEmpty()) {
            return null;
        }

        try {
            // 尝试获取 getter 方法
            String getterName = "get" + Character.toUpperCase(propertyName.charAt(0)) + propertyName.substring(1);
            try {
                Method getter = obj.getClass().getMethod(getterName);
                return getter.invoke(obj);
            } catch (NoSuchMethodException e) {
                // 尝试直接访问字段
                try {
                    java.lang.reflect.Field field = obj.getClass().getField(propertyName);
                    return field.get(obj);
                } catch (NoSuchFieldException ex) {
                    LOGGER.warn(
                            "Failed to write audit log when getPropertyValue with reflect, falling back to main log", e);
                    return null;
                }
            }
        } catch (Exception e) {
            LOGGER.warn("Failed to write audit log when getPropertyValue, falling back to main log", e);
            return null;
        }
    }

    private String inferResourceType(String className) {
        if (className == null || className.isEmpty()) {
            return "Unknown";
        }
        String resource = className.replace("ManagementService", "")
                .replace("Service", "")
                .replace("ManagerService", "");
        return resource.isEmpty() ? className : resource;
    }

    private boolean isSensitiveField(String propertyName) {
        Pattern pattern = compiledSensitiveFieldPattern;
        return pattern != null && StringUtils.isNotBlank(propertyName) && pattern.matcher(propertyName).matches();
    }

    private Optional<Pattern> compileSensitiveFieldPattern(String patternRule) {
        String rule = StringUtils.trimToEmpty(patternRule);
        if (StringUtils.isBlank(rule)) {
            return Optional.empty();
        }

        try {
            return Optional.of(Pattern.compile(rule));
        } catch (PatternSyntaxException e) {
            LOGGER.warn("Invalid operation log sensitive field pattern: {}", rule, e);
            return Optional.empty();
        }
    }

    private String maskSensitiveText(String text) {
        if (StringUtils.isEmpty(text) || compiledSensitiveFieldPattern == null) {
            return text;
        }

        StringBuilder builder = new StringBuilder(text);
        int index = 0;
        while (index < builder.length()) {
            //跳过非引号字符
            if (builder.charAt(index) != '"') {
                index++;
                continue;
            }

            //找到key的结束引号
            int keyEnd = findStringEnd(builder, index);
            if (keyEnd < 0) {
                break;
            }

            //跳过空白，寻找冒号
            int colonIndex = skipWhitespace(builder, keyEnd + 1);
            if (colonIndex >= builder.length() || builder.charAt(colonIndex) != ':') {
                index = keyEnd + 1;
                continue;
            }

            //提取并判断key是否为敏感字段
            String key = unescapeJsonString(builder.substring(index + 1, keyEnd));
            if (!isSensitiveField(key)) {
                index = keyEnd + 1;
                continue;
            }

            //寻找value的位置
            int valueStart = skipWhitespace(builder, colonIndex + 1);
            if (valueStart >= builder.length()) {
                index = keyEnd + 1;
                continue;
            }

            //代码可以走到这一步，就证明需要进行敏感字段处理
            int replacementEnd = maskSensitiveValueAfterKeyword(builder, valueStart);
            index = replacementEnd;
        }
        return builder.toString();
    }

    private int maskSensitiveValueAfterKeyword(StringBuilder builder, int valueStart) {
        switch (builder.charAt(valueStart)) {
            case '{':
                // 对象内部可能有多层嵌套，继续向对象内部扫描，避免预先扫描完整对象边界。
                return valueStart + 1;
            case '[':
                return maskSensitiveArrayValue(builder, valueStart);
            default:
                int valueEnd = findJsonValueEnd(builder, valueStart);
                return maskSensitiveScalarValue(builder, valueStart, valueEnd);
        }
    }

    private int maskSensitiveArrayValue(StringBuilder builder, int valueStart) {
        int valueEnd = findJsonValueEnd(builder, valueStart);
        maskSensitiveArrayScalarValues(builder, valueStart, valueEnd);
        return valueStart + 1;
    }

    private int maskSensitiveScalarValue(StringBuilder builder, int valueStart, int valueEnd) {
        if (builder.charAt(valueStart) == '"') {
            int maskEnd = valueEnd - 1;
            int maskStart = Math.max(valueStart + 1, maskEnd - SENSITIVE_VALUE_MASK_LENGTH);//长度小于SENSITIVE_VALUE_MASK_LENGTH将被全部掩码
            int maskedLength = maskEnd - maskStart;
            builder.replace(maskStart, maskEnd, MASK_REPLACEMENT);
            return valueEnd - maskedLength + MASK_REPLACEMENT.length();
        }
        String replacement = JSON.toJSONString(MASK_REPLACEMENT);
        builder.replace(valueStart, valueEnd, replacement);
        return valueStart + replacement.length();
    }

    private void maskSensitiveArrayScalarValues(StringBuilder builder, int arrayStart, int arrayEnd) {
        int cursor = arrayStart + 1;
        int end = arrayEnd - 1;
        while (cursor < end) {
            cursor = skipWhitespace(builder, cursor);
            if (cursor >= end) {
                return;
            }
            char current = builder.charAt(cursor);
            if (current == ',') {
                cursor++;
                continue;
            }

            int elementStart = cursor;
            int elementEnd = findJsonValueEnd(builder, elementStart);
            if (elementEnd <= elementStart) {
                cursor++;
                continue;
            }

            switch (builder.charAt(elementStart)) {
                case '{':
                case '[':
                    cursor = elementEnd;
                    continue;
                default:
                    int replacementEnd = maskSensitiveScalarValue(builder, elementStart, elementEnd);
                    end += replacementEnd - elementEnd;
                    cursor = replacementEnd;
            }
        }
    }

    private int findJsonValueEnd(CharSequence text, int valueStart) {
        int index = skipWhitespace(text, valueStart);
        if (index >= text.length()) {
            return index;
        }

        char first = text.charAt(index);
        if (first == '"') {
            int stringEnd = findStringEnd(text, index);
            return stringEnd < 0 ? text.length() : stringEnd + 1;
        }

        if (first != '{' && first != '[') {
            int cursor = index;
            while (cursor < text.length()) {
                char current = text.charAt(cursor);
                if (current == ',' || current == '}' || current == ']') {
                    break;
                }
                cursor++;
            }
            return cursor;
        }

        int depth = 0;
        boolean inString = false;
        boolean escaped = false;
        for (int cursor = index; cursor < text.length(); cursor++) {
            char current = text.charAt(cursor);
            if (inString) {
                if (escaped) {
                    escaped = false;
                } else if (current == '\\') {
                    escaped = true;
                } else if (current == '"') {
                    inString = false;
                }
                continue;
            }

            if (current == '"') {
                inString = true;
            } else if (current == '{' || current == '[') {
                depth++;
            } else if (current == '}' || current == ']') {
                depth--;
                if (depth == 0) {
                    return cursor + 1;
                }
            }
        }
        return text.length();
    }

    private int findStringEnd(CharSequence text, int quoteIndex) {
        boolean escaped = false;
        for (int cursor = quoteIndex + 1; cursor < text.length(); cursor++) {
            char current = text.charAt(cursor);
            if (escaped) {
                escaped = false;
            } else if (current == '\\') {
                escaped = true;
            } else if (current == '"') {
                return cursor;
            }
        }
        return -1;
    }

    private int skipWhitespace(CharSequence text, int index) {
        int cursor = index;
        while (cursor < text.length() && Character.isWhitespace(text.charAt(cursor))) {
            cursor++;
        }
        return cursor;
    }

    private String unescapeJsonString(String value) {
        if (value.indexOf('\\') < 0) {
            return value;
        }
        try {
            return JSON.parseObject('"' + value + '"', String.class);
        } catch (Exception e) {
            return value;
        }
    }
}
