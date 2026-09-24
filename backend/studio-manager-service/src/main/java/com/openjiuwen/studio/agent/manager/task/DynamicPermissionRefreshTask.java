/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.task;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.manager.config.PermissionProperties;
import com.openjiuwen.studio.agent.manager.entity.RolePermission;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.PermissionService;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;

@Component
@ConditionalOnProperty(name = "system.permission.enabled", havingValue = "true", matchIfMissing = false)
public class DynamicPermissionRefreshTask {

    private static final Logger logger = LoggerFactory.getLogger(DynamicPermissionRefreshTask.class);

    @Autowired
    private PermissionProperties permissionProperties;

    @Autowired
    private PermissionService permissionService;

    @Resource
    private MgObsService mgObsService;

    // 记录上一次成功的权限版本（用于监控）
    private String lastSuccessfulVersion = "initial";

    @PostConstruct
    public void init() {
        logger.info("DynamicPermissionRefreshTask initialized");
        logger.info("Refresh interval: {} ms", permissionProperties.getRefreshIntervalMs());

        // 启动时立即加载一次
        if (permissionProperties.getObsRolePermissionUrl() != null
            && !permissionProperties.getObsRolePermissionUrl().isEmpty()) {
            refreshPermissions();
        }
    }

    /**
     * 定时刷新权限配置
     */
    @Scheduled(fixedDelayString = "${system.permission.refresh-interval-ms:600000}", initialDelay = 10000)
    public void scheduledRefresh() {
        // 如果刷新间隔为负数，则不开启定时任务
        if (permissionProperties.getRefreshIntervalMs() < 0) {
            logger.debug("Refresh interval is negative, skipping scheduled refresh");
            return;
        }

        if (permissionProperties.getObsRolePermissionUrl() == null
            || permissionProperties.getObsRolePermissionUrl().isEmpty()) {
            logger.debug("OBS URL not configured, skipping refresh");
            return;
        }

        refreshPermissions();
    }

    /**
     * 手动刷新权限 - 增强错误处理，确保格式错误时不更新缓存
     */
    public boolean refreshPermissions() {
        try {
            String obsUrl = permissionProperties.getObsRolePermissionUrl();
            logger.debug("Refreshing permissions from OBS: {}", obsUrl);
            ObjectMapper objectMapper = new ObjectMapper();
            String controllerJson = mgObsService.downloadObsFile(obsUrl);
            // 解析JSON到对象列表
            Map<String, List<String>> roleAndPermission = new HashMap<>();
            // 动态需创建人校验权限(与 permissions 配套，OBS 文件可下发 creatorCheckPermissions 覆盖预置)
            Map<String, List<String>> dynamicCreatorCheck = new HashMap<>();
            RolePermission[] rolePermissions = objectMapper.readValue(controllerJson, RolePermission[].class);
            for (RolePermission rp : rolePermissions) {
                roleAndPermission.put(rp.getRoleName(), rp.getPermissions());
                if (rp.getCreatorCheckPermissions() != null && !rp.getCreatorCheckPermissions().isEmpty()) {
                    dynamicCreatorCheck.put(rp.getRoleName(), rp.getCreatorCheckPermissions());
                }
            }
            if (roleAndPermission.isEmpty()) {
                logger.warn("Failed to download permissions from OBS or file is empty, keeping current permissions");
                return false;
            }
            boolean success = permissionService.updateDynamicPermissions(roleAndPermission);
            if (success) {
                // permissions 更新成功才同步更新 creatorCheckPermissions,避免版本不一致
                permissionService.updateDynamicCreatorCheckPermissions(dynamicCreatorCheck);
                lastSuccessfulVersion = "updated_" + System.currentTimeMillis();
                logger.info("Permissions refreshed successfully from OBS, new roles: {}",
                    roleAndPermission.keySet());
                return true;
            } else {
                logger.warn("Permission update failed due to format validation, keeping current permissions");
                return false;
            }
        } catch (Exception e) {
            logger.error("Unexpected error during permission refresh, keeping current permissions", e);
            return false;
        }
    }

    /**
     * 获取任务状态（用于监控）
     */
    public String getTaskStatus() {
        return String.format("DynamicPermissionRefreshTask[lastSuccess: %s, hasDynamic: %s]", lastSuccessfulVersion,
            permissionService.hasDynamicPermissions());
    }
}
