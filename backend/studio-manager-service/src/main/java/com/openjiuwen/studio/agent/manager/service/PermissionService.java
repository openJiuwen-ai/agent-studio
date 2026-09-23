/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.util.AntPathMatcher;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class PermissionService {

    private static final Logger logger = LoggerFactory.getLogger(PermissionService.class);

    private static final AntPathMatcher PATH_MATCHER = new AntPathMatcher();

    // 平台预置权限缓存 - 保持原来的数据结构
    private final Map<String, List<String>> presetRolePermissions = new ConcurrentHashMap<>();

    // 动态权限缓存（会覆盖预置权限） - 保持原来的数据结构
    private final Map<String, List<String>> dynamicRolePermissions = new ConcurrentHashMap<>();

    // 需创建人校验的权限缓存 - 平台预置(role -> METHOD#URI 列表)
    private final Map<String, List<String>> presetCreatorCheckPermissions = new ConcurrentHashMap<>();

    // 需创建人校验的权限缓存 - 动态(覆盖预置)
    // 注:当前 updateDynamicPermissions(OBS 动态权限)不写入本字段(OBS JSON 暂无 creatorCheckPermissions 维度)，
    // getMergedCreatorCheckPermissions 实际只用预置。若 OBS JSON 后续支持该维度，需在
    // DynamicPermissionRefreshTask.refreshPermissions 同步解析 rp.getCreatorCheckPermissions() 并调
    // updateDynamicCreatorCheckPermissions(待新增)。保留本字段以备动态权限扩展。
    private final Map<String, List<String>> dynamicCreatorCheckPermissions = new ConcurrentHashMap<>();

    /**
     * 更新动态权限 - 添加格式验证和错误处理
     */
    public boolean updateDynamicPermissions(Map<String, List<String>> permissions) {
        try {
            // 验证权限格式
            if (!validatePermissionFormat(permissions)) {
                logger.error("Dynamic permission format validation failed");
                return false;
            }

            dynamicRolePermissions.clear();
            dynamicRolePermissions.putAll(permissions);
            logger.info("Dynamic permissions updated successfully, roles: {}", permissions.keySet());
            return true;
        } catch (Exception e) {
            logger.error("Error updating dynamic permissions, keeping current permissions", e);
            return false;
        }
    }

    /**
     * 更新动态需创建人校验权限(与 updateDynamicPermissions 配套)。
     * <p>OBS 动态权限文件同时下发 permissions + creatorCheckPermissions 时，
     * 由 DynamicPermissionRefreshTask 解析后调用本方法更新 dynamicCreatorCheckPermissions，
     * 使动态权限能覆盖预置 creatorCheckPermissions(收紧或放开),保持"动态覆盖预置"契约。</p>
     */
    public boolean updateDynamicCreatorCheckPermissions(Map<String, List<String>> creatorCheckPermissions) {
        try {
            if (!validatePermissionFormat(creatorCheckPermissions)) {
                logger.error("Dynamic creator-check permission format validation failed");
                return false;
            }
            dynamicCreatorCheckPermissions.clear();
            dynamicCreatorCheckPermissions.putAll(creatorCheckPermissions);
            logger.info("Dynamic creator-check permissions updated, roles: {}", creatorCheckPermissions.keySet());
            return true;
        } catch (Exception e) {
            logger.error("Error updating dynamic creator-check permissions, keeping current", e);
            return false;
        }
    }

    /**
     * 验证权限数据格式
     */
    private boolean validatePermissionFormat(Map<String, List<String>> permissions) {
        if (permissions == null) {
            logger.warn("Permissions map is null");
            return false;
        }

        for (Map.Entry<String, List<String>> entry : permissions.entrySet()) {
            String role = entry.getKey();
            List<String> permissionList = entry.getValue();

            if (role == null || role.trim().isEmpty()) {
                logger.warn("Invalid role name found: {}", role);
                return false;
            }

            if (permissionList == null) {
                logger.warn("Permission list is null for role: {}", role);
                return false;
            }

            // 检查权限列表中的每个权限是否合法
            for (String permission : permissionList) {
                if (permission == null || permission.trim().isEmpty()) {
                    logger.warn("Invalid permission found for role {}: {}", role, permission);
                    return false;
                }
            }
        }

        return true;
    }

    /**
     * 获取最终权限（动态权限覆盖预置权限）
     * <p>每次调用新建 HashMap 合并 preset + dynamic。配置项有限(角色数 x 权限数)，
     * 单次合并开销小，与既有 getMergedPermissions 模式一致。如需优化可缓存 merged 结果
     * (setPreset 或 updateDynamic 时 invalidate)，但引入并发复杂性，当前可接受。</p>
     */
    public Map<String, List<String>> getMergedPermissions() {
        Map<String, List<String>> merged = new HashMap<>(presetRolePermissions);
        merged.putAll(dynamicRolePermissions);
        return merged;
    }

    /**
     * 获取特定角色的权限列表
     */
    public List<String> getPermissionsByRole(String role) {
        // 先查动态权限，如果没有则查预置权限
        if (dynamicRolePermissions.containsKey(role)) {
            return dynamicRolePermissions.get(role);
        }
        return presetRolePermissions.get(role);
    }

    /**
     * 清空动态权限（回退到预置权限）
     */
    public void clearDynamicPermissions() {
        dynamicRolePermissions.clear();
        logger.info("Dynamic permissions cleared, using preset permissions");
    }

    public boolean hasDynamicPermissions() {
        return !dynamicRolePermissions.isEmpty();
    }

    /**
     * 获取当前动态权限（用于调试和监控）
     */
    public Map<String, List<String>> getCurrentDynamicPermissions() {
        return new HashMap<>(dynamicRolePermissions);
    }

    /**
     * 获取平台预置权限（用于调试和监控）
     */
    public Map<String, List<String>> getPresetPermissions() {
        return new HashMap<>(presetRolePermissions);
    }

    /**
     * 设置平台预置权限
     */
    public void setPresetPermissions(Map<String, List<String>> permissions) {
        presetRolePermissions.clear();
        presetRolePermissions.putAll(permissions);
        logger.info("Platform preset permissions loaded, roles: {}", permissions.keySet());
    }

    /**
     * 设置平台预置的需创建人校验权限(role -> METHOD#URI 列表)。
     */
    public void setPresetCreatorCheckPermissions(Map<String, List<String>> creatorCheckPermissions) {
        presetCreatorCheckPermissions.clear();
        presetCreatorCheckPermissions.putAll(creatorCheckPermissions);
        logger.info("Platform preset creator-check permissions loaded, roles: {}", creatorCheckPermissions.keySet());
    }

    /**
     * 获取合并后的需创建人校验权限(动态覆盖预置)。
     */
    public Map<String, List<String>> getMergedCreatorCheckPermissions() {
        Map<String, List<String>> merged = new HashMap<>(presetCreatorCheckPermissions);
        merged.putAll(dynamicCreatorCheckPermissions);
        return merged;
    }

    /**
     * 判断指定角色对当前请求 URI 是否需要创建人校验。
     * <p>角色 actions 不含该 URI(拦截器已拒绝)时返回 false；
     * 角色全权(permissions 含该 URI)且 creatorCheckPermissions 不含时返回 false；
     * 角色需创建人校验(creatorCheckPermissions 含该 URI)时返回 true。</p>
     *
     * @param role 当前用户在空间的角色
     * @param requestMethod HTTP 方法
     * @param requestUri 请求 URI
     * @return 是否需要创建人校验
     */
    public boolean isCreatorCheckRequired(String role, String requestMethod, String requestUri) {
        List<String> creatorCheckList = getMergedCreatorCheckPermissions().get(role);
        if (creatorCheckList == null || creatorCheckList.isEmpty()) {
            return false;
        }
        return creatorCheckList.stream()
            .map(action -> action.split("#"))
            .filter(parts -> parts.length == 2)
            .anyMatch(parts -> parts[0].equals(requestMethod) && PATH_MATCHER.match(parts[1], requestUri));
    }

    /**
     * 判断指定角色是否被显式授予该 URI(在角色 permissions 全权列表中)。
     * 用于 validator fail-closed：URI 不在 creatorCheckPermissions 时，确认是否在 permissions(全权)。
     *
     * @param role 当前用户在空间的角色
     * @param requestMethod HTTP 方法
     * @param requestUri 请求 URI
     * @return 是否在角色 permissions 全权列表中
     */
    public boolean isPermissionGranted(String role, String requestMethod, String requestUri) {
        List<String> permissionList = getMergedPermissions().get(role);
        if (permissionList == null || permissionList.isEmpty()) {
            return false;
        }
        return permissionList.stream()
            .map(action -> action.split("#"))
            .filter(parts -> parts.length == 2)
            .anyMatch(parts -> parts[0].equals(requestMethod) && PATH_MATCHER.match(parts[1], requestUri));
    }
}
