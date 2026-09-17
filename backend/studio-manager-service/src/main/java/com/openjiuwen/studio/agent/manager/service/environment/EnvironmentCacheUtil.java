/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.environment;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;
import com.openjiuwen.studio.agent.manager.entity.EnvironmentManagerEntity;
import com.openjiuwen.studio.agent.manager.entity.EnvironmentVariableEntity;
import com.openjiuwen.studio.agent.manager.mapper.EnvironmentManagerMapper;
import com.openjiuwen.studio.agent.manager.mapper.EnvironmentVariableMapper;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.util.CollectionUtils;

import java.time.Duration;
import java.util.List;

@Slf4j
@Component
public class EnvironmentCacheUtil {

    /**
     * project:{project_id}:environment:{environment_name}
     */
    private static final String PROJECT_ENVIRONMENT = "environment:%s:workspaceId:%s";

    /**
     * project:{project_id}:default_environment
     */
    private static final String PROJECT_DEFAULT_ENVIRONMENT = "project:%s:default_environment";

    private static final String ENVIRONMENT_REFRESH_KEY = "environment:refresh";

    private static final int ENVIRONMENT_EXPIRE_DAYS = 1;

    private static final String LOCK_STR = "_lock";

    @Autowired
    private EnvironmentManagerMapper environmentManagerMapper;

    @Autowired
    private EnvironmentVariableMapper environmentVariableMapper;

    @Autowired
    private RedisClient redisClient;

    /**
     * 更新环境变量缓存
     *
     * @param envId 删除环境的id
     * @param workspaceId 工作空间id
     * @param value 环境变量的值 格式为json字符串
     */
    public void updateEnvironmentCache(String envId, String workspaceId, String value) {
        log.info("begin update environment cache, envName: {}", envId);
        value = StringUtils.isBlank(value) ? "{}" : value;
        redisClient.set(String.format(PROJECT_ENVIRONMENT, envId, workspaceId), value,
            Duration.ofDays(ENVIRONMENT_EXPIRE_DAYS));
        log.info("end update environment cache, envName: {}", envId);
    }


    /**
     * 删除环境变量缓存
     * @param envId 删除环境的id
     * @param workspaceId 工作空间id
     */
    public void deleteEnvironmentCache(String envId, String workspaceId) {
        log.info("begin delete environment cache, envId: {}, workspaceId: {}", envId, workspaceId);
        redisClient.delete(String.format(PROJECT_ENVIRONMENT, envId, workspaceId));
        log.info("end delete environment cache, envId: {}, workspaceId: {}", envId, workspaceId);
    }

    /**
     * 从缓存中获取环境变量信息
     *
     */
    public String getEnvironmentCache(String envId, String workspaceId) {
        return redisClient.get(String.format(PROJECT_ENVIRONMENT, envId, workspaceId));
    }

    /**
     * 更新项目默认环境缓存（runtime 直连时按 project_id 读取默认环境 id）
     *
     * @param projectId 项目id
     * @param envId 默认环境id
     */
    public void updateDefaultEnvironmentCache(String projectId, String envId) {
        if (StringUtils.isBlank(projectId) || StringUtils.isBlank(envId)) {
            return;
        }
        redisClient.set(String.format(PROJECT_DEFAULT_ENVIRONMENT, projectId), envId,
            Duration.ofDays(ENVIRONMENT_EXPIRE_DAYS));
        log.info("update default environment cache, projectId: {}, envId: {}", projectId, envId);
    }

    /**
     * 删除项目默认环境缓存（项目环境全部删除时调用）
     *
     * @param projectId 项目id
     */
    public void deleteDefaultEnvironmentCache(String projectId) {
        if (StringUtils.isBlank(projectId)) {
            return;
        }
        redisClient.delete(String.format(PROJECT_DEFAULT_ENVIRONMENT, projectId));
        log.info("delete default environment cache, projectId: {}", projectId);
    }

    /**
     * 定时刷新环境变量
     */
    @Scheduled(cron = "${env-management.variables.cache-refresh-cron: 0 30 1 * * ?}")
    public void refreshCachedEnvironmentVariables() {
        RedisLock lock = null;
        try {
            lock = redisClient.getLock(ENVIRONMENT_REFRESH_KEY + LOCK_STR);
            if (!lock.tryLock(Duration.ofMinutes(30))) {
                log.info("Environment update is running; skipping.");
                return;
            }
            log.info("Environment variables refresh start.");
            // 按projectId刷新环境变量
            List<String> projectIds = environmentManagerMapper.findAllWithGroupByProjectId();
            if (!CollectionUtils.isEmpty(projectIds)) {
                projectIds.forEach(projectId -> {
                    List<EnvironmentManagerEntity> environmentEntities = environmentManagerMapper.findByProjectId(
                        projectId);
                    if (CollectionUtils.isEmpty(environmentEntities)) {
                        return;
                    }
                    environmentEntities.forEach(entity -> {
                        log.info("Environment variables refresh, projectId: {}, envName: {}.", projectIds,
                            entity.getName());
                        List<EnvironmentVariableEntity> environmentVariableEntities
                            = this.environmentVariableMapper.findByProjectIdAndEnvId(projectId, entity.getId());
                        if (CollectionUtils.isEmpty(environmentVariableEntities)) {
                            return;
                        }
                        environmentVariableEntities.forEach(envVariableEntity -> {
                            redisClient.set(String.format(PROJECT_ENVIRONMENT, envVariableEntity.getEnvId(), envVariableEntity.getWorkspaceId()),
                                StringUtils.isBlank(envVariableEntity.getEnvVariable()) ? "{}" : envVariableEntity.getEnvVariable(),
                                Duration.ofDays(ENVIRONMENT_EXPIRE_DAYS));
                        });
                    });
                    // 补写项目默认环境缓存（兼容历史数据：老项目从未写过该 key，
                    // 定时刷新时按 DB 当前默认环境补齐，runtime 直连才能解析）
                    List<EnvironmentManagerEntity> defaults = environmentManagerMapper
                        .findByProjectIdAndIsDefaultTrue(projectId);
                    if (!CollectionUtils.isEmpty(defaults)) {
                        updateDefaultEnvironmentCache(projectId, defaults.get(0).getId());
                    } else {
                        deleteDefaultEnvironmentCache(projectId);
                    }
                });
            }
            log.info("Environment variables refresh end.");
        } catch (Exception e) {
            log.error("Error refresh environment.", e);
            throw new AgentStudioException(StudioError.ERROR_REFRESH_ENVIRONMENT);
        } finally {
            if (lock != null) {
                lock.unlock();
            }
        }
    }

    /**
     * 判断redis中是否存在key
     *
     */
    public boolean isExistEnvironmentVariableCache(String envId, String workspaceId) {
        return redisClient.exists(String.format(PROJECT_ENVIRONMENT, envId, workspaceId));
    }

}
