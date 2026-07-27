
/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.utils;

import com.alibaba.fastjson.JSONObject;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.dto.PageInfoV2;
import com.openjiuwen.studio.agent.manager.enums.NameSplitInfix;
import com.openjiuwen.studio.agent.manager.service.mcp.model.BaseEntity;
import com.openjiuwen.studio.agent.manager.service.mcp.model.UpdateBaseInfo;

import inet.ipaddr.IPAddressString;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.springframework.http.HttpHeaders;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.net.InetAddress;
import java.net.URI;
import java.net.URISyntaxException;
import java.net.UnknownHostException;
import java.nio.charset.StandardCharsets;
import java.sql.Timestamp;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

/**
 * CommonUtil
 *
 * @Date: 2024/5/14 14:34
 * @Description: 公共工具类
 */

@Slf4j
public class CommonUtil {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    public static String genUUID() {
        return UUID.randomUUID().toString();
    }

    public static String getTenantId() {
        return RequestContextUtils.getRequestUserDomainId();
    }

    public static String getUserId() {
        return RequestContextUtils.getRequestUserId();
    }

    public static String getDeptCode() {
        return "system";
    }

    public static void initBaseEntity(BaseEntity baseEntity) {
        String userId = getUserId();
        Date date = new Date();
        baseEntity.setTenantId(getTenantId());
        baseEntity.setDeptCode(getDeptCode());
        baseEntity.setCreatedDate(date);
        baseEntity.setCreatedByUserId(userId);
        baseEntity.setLastUpdatedDate(date);
        baseEntity.setLastUpdatedByUserId(userId);
    }

    public static UpdateBaseInfo initUpdateBaseInfo() {
        UpdateBaseInfo updateBaseInfo = new UpdateBaseInfo();
        updateBaseInfo.setLastUpdatedByUserId(getUserId());
        updateBaseInfo.setLastUpdatedDate(new Date());
        return updateBaseInfo;
    }

    public static boolean isValidUUid(String str) {
        try {
            UUID.fromString(str);
            return true;
        } catch (IllegalArgumentException exception) {
            return false;
        }
    }

    public static void replaceConnectorName(Map<String, Object> swagger, String newName) {
        JSONObject info = JSONObject.parseObject(JSONObject.toJSONString(swagger.get("info")));
        info.put("title", newName);
        swagger.put("info", info);
    }

    /**
     * 从mssi源端的名称中拆分出wiseAgent显示的名称
     */
    public static String splitName(String realName, NameSplitInfix infix) {
        return StringUtils.substringBeforeLast(realName, infix.toString());
    }

    /**
     * 从源名称生成目标名称，加上中缀与uuid
     */
    public static String spliceName(String name, NameSplitInfix infix) {
        return name + infix.toString() + CommonUtil.genUUID().replace("-", "").substring(0, 6);
    }

    public static String getExpireTime(long time) {
        Date date = new Date();
        date.setTime(date.getTime() + time);
        return new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(date);
    }

    public static String splitFunctionExpression(String functionExpression) {
        String name = StringUtils.substringBeforeLast(functionExpression, "(");
        String suffix = "(" + StringUtils.substringAfterLast(functionExpression, "(");
        return splitName(name, NameSplitInfix.FUNCTION) + suffix;
    }

    public static void validateTenantIdIsNotEmpty() {
        if (StringUtils.isBlank(CommonUtil.getTenantId())) {
            log.error("tenant id is empty");
            McpServiceExceptionUtils.throwMissingParameterError("tenantId");
        }
    }

    public static void validatePageInfo(PageInfoV2 pageInfo) {
        if (null == pageInfo) {
            throw new AgentStudioException(StudioError.MISSING_PARAM, "pageInfo");
        }
        if (pageInfo.getLimit() < 0) {
            throw new AgentStudioException(StudioError.MISSING_PARAM, "limit");
        }
        if (pageInfo.getOffset() < 0) {
            throw new AgentStudioException(StudioError.MISSING_PARAM, "offset");
        }
    }

    public static void validateProjectId(String projectId) {
    }

    public static void validateWorkspaceId(String workspaceId) {
    }

    public static void validateProjectAndWorkspaceId(String projectId, String workspaceId) {
        validateProjectId(projectId);
        validateWorkspaceId(workspaceId);
    }

    public static String getAndValidateTenantId() {
        String tenantId = getTenantId();
        if (StringUtils.isBlank(tenantId)) {
            log.error("tenant id is empty");
            McpServiceExceptionUtils.throwMissingParameterError("tenantId");
        }
        return tenantId;
    }

    public static void validateMcpConfigFormat(String config) {
        boolean validJson = McpJsonUtils.isValidJson(config);
        if (!validJson) {
            log.error("The format of the MCP service configuration is incorrect");
            throw new AgentStudioException(StudioError.MCP_SERVICE_CONFIG_FORMAT_INCORRECT);
        }
    }

    public static String getUUID() {
        return UUID.randomUUID().toString().replaceAll("-", "");
    }

    /**
     * 更新最后修改人，最后修改时间
     *
     * @param object 对象
     */
    public static void setCommonUpdateProperties(Object object) {
        try {
            Class<?> cls = object.getClass();
            Timestamp now = new Timestamp(new Date().getTime());

            Method setLastUpdatedDate = cls.getMethod("setLastUpdatedDate", Timestamp.class);
            setLastUpdatedDate.invoke(object, now);

            Method setLastUpdatedByUserId = cls.getMethod("setLastUpdatedByUserId", String.class);
            setLastUpdatedByUserId.invoke(object, RequestContextUtils.getRequestUserId());

        } catch (NoSuchMethodException | InvocationTargetException | IllegalAccessException e) {
            log.error("WPS set common properties error. {}", e.getMessage());
            throw new AgentStudioException(StudioError.UPDATE_OBJECT_PROPERTIES_FAILED);
        }
    }

    public static void setCommonCreateProperties(Object object) {
        try {
            Class<?> cls = object.getClass();
            Timestamp now = new Timestamp(new Date().getTime());

            Method setCreatedDate = cls.getMethod("setCreatedDate", Timestamp.class);
            setCreatedDate.invoke(object, now);

            Method setCreatedByUserId = cls.getMethod("setCreatedByUserId", String.class);
            setCreatedByUserId.invoke(object, RequestContextUtils.getRequestUserId());

            Method setLastUpdatedDate = cls.getMethod("setLastUpdatedDate", Timestamp.class);
            setLastUpdatedDate.invoke(object, now);

            Method setLastUpdatedByUserId = cls.getMethod("setLastUpdatedByUserId", String.class);
            setLastUpdatedByUserId.invoke(object, RequestContextUtils.getRequestUserId());

            Method setTenantId = cls.getMethod("setTenantId", String.class);
            setTenantId.invoke(object, RequestContextUtils.getRequestUserDomainId());

            Method setDeptCode = cls.getMethod("setDeptCode", String.class);
            setDeptCode.invoke(object, getDeptCode());

        } catch (NoSuchMethodException | InvocationTargetException | IllegalAccessException e) {
            log.error("WPS set common properties error.");
            throw new AgentStudioException(StudioError.UPDATE_OBJECT_PROPERTIES_FAILED);
        }
    }

    public static boolean isIntegerAndLessThan10(String input) {
        return Optional.ofNullable(input).filter(s -> s.matches("-?\\d+")).map(Integer::parseInt).filter(i -> i <= 10)
            .isPresent();
    }

    @SuppressWarnings("unchecked")
    public static void parseMcpConfigHeaderInfo(Object configInfo, Map<String, String> headers, int count) {
        if (count >= 10) {
            return;
        }
        if (configInfo instanceof Map<?, ?>) {
            for (Map.Entry<?, ?> entry : ((Map<?, ?>) configInfo).entrySet()) {
                if (Strings.CI.equals("headers", entry.getKey().toString())) {
                    headers.putAll((Map<? extends String, ? extends String>) entry.getValue());
                    continue;
                }
                parseMcpConfigHeaderInfo(entry.getValue(), headers, count + 1);
            }
        }
    }

    public static Map<String, String> parseMcpConfigHeaderInfo(String configInfo) {
        Map<?, ?> map = McpJsonUtils.fromJson(configInfo, Map.class);
        Map<String, String> headers = new HashMap<>();
        parseMcpConfigHeaderInfo(map, headers, 0);
        return headers;
    }

    public static HttpHeaders generateHeaders() {
        HttpHeaders httpHeaders = new HttpHeaders();
        httpHeaders.add("tenant-id-w", CommonUtil.getTenantId());
        httpHeaders.add("dept-code", CommonUtil.getDeptCode());
        httpHeaders.add("Content-Type", "application/json;charset=UTF-8");
        return httpHeaders;
    }

    public static String List2String(List<String> list) {
        return list.stream().map(s -> "\"" + s + "\"").collect(Collectors.joining(", ", "[", "]"));
    }

    public static String parseUrlFromMcpConfig(com.alibaba.fastjson2.JSONObject config, int count) {
        if (count > 5) {
            return "";
        }
        for (String key : config.keySet()) {
            if (Strings.CI.equals(key, "url")) {
                return appendMcpPathIfNeeded(config.getString(key));
            }
            if (config.get(key) instanceof com.alibaba.fastjson2.JSONObject) {
                String result = parseUrlFromMcpConfig(config.getJSONObject(key), ++count);
                if(result != null) {
                    return result;
                }
            }
        }
        return null;
    }

    private static String appendMcpPathIfNeeded(String url) {
        if (url == null || url.isEmpty()) {
            return url;
        }
        try {
            java.net.URI uri = new java.net.URI(url);
            String path = uri.getPath();
            if (path == null || path.isEmpty() || "/".equals(path)) {
                String newPath = "/mcp";
                String query = uri.getQuery();
                String fragment = uri.getFragment();
                java.net.URI newUri = new java.net.URI(
                        uri.getScheme(),
                        uri.getUserInfo(),
                        uri.getHost(),
                        uri.getPort(),
                        newPath,
                        query,
                        fragment
                );
                return newUri.toString();
            }
        } catch (java.net.URISyntaxException e) {
            return url;
        }
        return url;
    }

    public static String getRawQueryString(String urlString) {
        // 1. 输入验证：如果 URL 是 null，直接返回 null
        if (urlString == null) {
            return null;
        }
        // 进一步处理，例如去除空白
        String trimmedUrlString = urlString.trim();
        if (trimmedUrlString.isEmpty()) {
            return null; // 空白字符串也视为没有查询
        }
        try {
            // 2. 使用 URI 类解析 URL 结构
            // URI 比 URL 更适合纯粹的解析和组件访问，不会尝试建立连接。
            URI uri = new URI(trimmedUrlString);

            // 3. 直接获取查询字符串部分
            return uri.getQuery();
        } catch (URISyntaxException e) {
            // 如果 URL 字符串的格式不符合 URI 规范，抛出 IllegalArgumentException。
            log.error("getRawQueryString failed.", e);
            return null;
        }
    }

    /**
     * 将包含JSON字符串字段的源对象转换为目标对象
     *
     * @param source 源对象（可能包含JSON字符串字段）
     * @param targetClass 目标对象的类（纯Java类，不含JSON字符串字段）
     * @param <S> 源对象类型
     * @param <T> 目标对象类型
     * @return 转换后的目标对象
     * @throws Exception 转换过程中发生的异常
     */
    public static <S, T> T convert(S source, Class<T> targetClass, Map<String, Class<?>> jsonFieldTypes)
        throws Exception {
        if (source == null) {
            return null;
        }

        // 创建属性映射Map
        Map<String, Object> propertyMap = new HashMap<>();

        // 处理源对象的所有字段
        Field[] sourceFields = source.getClass().getDeclaredFields();
        for (Field sourceField : sourceFields) {
            sourceField.setAccessible(true);
            String fieldName = sourceField.getName();
            Object fieldValue = sourceField.get(source);

            // 如果是JSON字符串字段，解析为对应的Java对象
            if (jsonFieldTypes.containsKey(fieldName) && fieldValue instanceof String) {
                String jsonValue = (String) fieldValue;
                Class<?> targetFieldType = jsonFieldTypes.get(fieldName);

                // 解析JSON字符串为Java对象
                Object parsedObject = OBJECT_MAPPER.readValue(jsonValue, targetFieldType);
                propertyMap.put(fieldName, parsedObject);
            } else {
                // 非JSON字段直接放入映射
                propertyMap.put(fieldName, fieldValue);
            }
        }

        // 将属性映射转换为目标对象
        return mapToObject(propertyMap, targetClass);
    }

    /**
     * 将属性映射转换为目标对象
     */
    private static <T> T mapToObject(Map<String, Object> propertyMap, Class<T> targetClass) throws Exception {
        T target = targetClass.getDeclaredConstructor().newInstance();

        Field[] targetFields = targetClass.getDeclaredFields();
        for (Field targetField : targetFields) {
            targetField.setAccessible(true);
            String fieldName = targetField.getName();

            if (propertyMap.containsKey(fieldName)) {
                Object value = propertyMap.get(fieldName);
                if (value != null && targetField.getType().isAssignableFrom(value.getClass())) {
                    targetField.set(target, value);
                }
            }
        }

        return target;
    }

    /**
     * 读取resource下资源文件内容
     *
     * @param resourceName 资源文件
     * @return 内容
     */
    public static String getResourceContent(String resourceName) {
        if (StringUtils.isEmpty(resourceName)) {
            return StringUtils.EMPTY;
        }

        try (InputStream inputStream = Thread.currentThread().getContextClassLoader().getResourceAsStream(
            resourceName)) {
            if (inputStream == null) {
                log.warn("Resource [{}] not found, return empty string", resourceName);
                return StringUtils.EMPTY;
            }
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(inputStream,
                StandardCharsets.UTF_8))) {
                StringBuilder buffer = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) {
                    buffer.append(line);
                    buffer.append("\n");
                }
                return Strings.CS.removeEnd(buffer.toString(), "\n");
            } catch (IOException e) {
                log.error("Read resource error:", e);
                throw new AgentStudioException(StudioError.RESOURCE_READER_ERROR);
            }
        } catch (Exception e) {
            log.error("Read resource [{}]", resourceName, e);
            return StringUtils.EMPTY;
        }
    }

    /**
     * 对字符串中的 URL 凭证进行脱敏
     * 场景：将 "http://user:password@127.0.0.1:8080" 替换为 "http://******@127.0.0.1:8080"
     * 用于清洗异常堆栈中的敏感 URL
     *
     * @param input 可能包含敏感 URL 的文本（如异常堆栈）
     * @return 脱敏后的文本
     */
    public static String maskUrlCredentials(String input) {
        if (StringUtils.isBlank(input)) {
            return input;
        }
        try {
            // 正则逻辑：
            // (https?://)  -> 捕获协议头 (Group 1)
            // [^@/\s]+     -> 匹配 @ 符号之前的所有非空白字符 (即 user:password 部分)
            // @            -> 锚定 @ 符号
            // 替换为：$1******@
            return input.replaceAll("(https?://)[^@/\\s]+@", "$1******@");
        } catch (Exception e) {
            // 如果正则处理失败，为了不影响主流程，返回原字符串或空串（视安全要求而定，这里建议返回原串以免丢失报错信息）
            log.warn("Failed to mask credentials in string", e);
            return input;
        }
    }

    /**
     * host 合法性检查
     *
     * @param host host
     * @param hostBlackList 连接器host黑名单
     */
    public static void checkHostValid(boolean enableHostCheck, String host, String hostBlackList) {
        if (!enableHostCheck) {
            return;
        }
        Set<String> connectorHostBlackList = Arrays.stream(hostBlackList.split(","))
                .map(String::trim)
                .collect(Collectors.toSet());
        try {
            // 检查host
            InetAddress address = InetAddress.getByName(host);
            String realIp = address.getHostAddress();
            if (connectorHostBlackList.contains(realIp)) {
                log.warn("checkHostValid failed, host: {}", host);
                throw new AgentStudioException(StudioError.INVALID_URL);
            }
        } catch (UnknownHostException e) {
            log.warn("checkHostValid failed, host: {}", host);
            throw new AgentStudioException(StudioError.INVALID_URL);
        }

        // 判断网段
        IPAddressString hostAddress = new IPAddressString(host);
        for (String ips : connectorHostBlackList) {
            if (StringUtils.isEmpty(ips)) continue;
            try {
                IPAddressString ipAddress = new IPAddressString(ips);
                if (ipAddress.contains(hostAddress) || host.contains(ips)) {
                    log.warn("checkHostValid failed, ipAddress:{}, hostAddress: {}, host: {}, ips:{}", ipAddress,
                            hostAddress, host, ips);
                    throw new AgentStudioException(StudioError.INVALID_URL);
                }
            } catch (IllegalArgumentException e) {
                // 忽略非法的IP格式
                log.warn("Invalid IP format in blacklist: {}", ips);
            }
        }
    }

    /**
     * list截取函数
     *
     * @param offset start
     * @param limit 限制长度
     * @param insightInfo insightInfo
     * @return 切割后list
     */
    public static <T> List<T> subList(Integer offset, Integer limit, List<T> insightInfo) {
        // offset和limit默认值为0，如果offset小于0，则默认为0；
        if (offset == null || offset < 0) {
            offset = 0;
        }
        // 如果limit小于0，则默认为0；
        if (limit == null || limit < 0) {
            limit = insightInfo.size();
        }
        // 如果offset+limit大于列表长度，则limit为剩余长度
        if (offset + limit > insightInfo.size()) {
            limit = insightInfo.size() - offset;
        }
        if (offset >= insightInfo.size() || limit <= 0) {
            return Collections.emptyList();
        }
        return new ArrayList<>(insightInfo.subList(offset, offset + limit));
    }

    /**
     * 分组
     *
     * @param list 原始范围
     * @param groupSize 分组大小
     * @param <T> 类型
     * @return 分组后数据
     */
    public static <T> List<List<T>> groupList(List<T> list, int groupSize) {
        return IntStream.range(0, (list.size() + groupSize - 1) / groupSize)
            .mapToObj(i -> list.subList(i * groupSize, Math.min((i + 1) * groupSize, list.size())))
            .collect(Collectors.toList());
    }

    /**
     * inputStream转化为byte数组
     *
     * @param inputStream 输入流
     * @return byte[]
     */
    public static byte[] toByteArray(InputStream inputStream) throws IOException {
        ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
        byte[] buffer = new byte[1024];
        int bytesRead;

        // 读取 InputStream 并写入 ByteArrayOutputStream
        while ((bytesRead = inputStream.read(buffer)) != -1) {
            outputStream.write(buffer, 0, bytesRead);
        }
        return outputStream.toByteArray();
    }

    public static String toTraceModel(String defaultMode, String invokeMode) {
        if (StringUtils.isEmpty(invokeMode)) {
            return defaultMode;
        }
        return switch (invokeMode.toUpperCase(Locale.ROOT)) {
            case "DEBUG" -> "DEBUG";
            case "EXPERIMENT" -> "EXPERIMENT";
            case "PROD", "API" -> "API";
            default -> defaultMode;
        };
    }

    public static boolean traceEnable(boolean opsEnable, String mode) {
        if (!opsEnable) {
            return false;
        }
        return !StringUtils.isEmpty(mode);
    }


}
