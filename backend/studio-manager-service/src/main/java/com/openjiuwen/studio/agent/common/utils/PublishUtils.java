/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.utils;

import static com.openjiuwen.studio.agent.common.constant.Constants.OBS_METADATA_DIR;
import static com.openjiuwen.studio.agent.common.constant.Constants.UNDERLINE_STR;

import com.alibaba.fastjson2.JSON;
import com.openjiuwen.studio.agent.common.bo.AgentMetadata;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.service.CommonObsService;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.jetbrains.annotations.NotNull;
import org.springframework.stereotype.Component;

import java.time.Duration;

/**
 * Agent发布Utils
 *
 */
@Component
@Slf4j
public class PublishUtils {
    private static final int PUBLISH_METADATA_EXPIRE_DAYS = 10;

    private final RedisClient redisClient;

    public PublishUtils(RedisClient redisClient) {
        this.redisClient = redisClient;
    }

    /**
     * 保存发布信息
     *
     * @param agentMetadata agent元数据
     * @param type 类型，当前取值有latest和treasure
     * @param obsService OBSService
     */
    public void savePublish(AgentMetadata agentMetadata, String type, CommonObsService obsService) {
        String agentId = agentMetadata.getAgentId();
        String metaDataJson = JSON.toJSONString(agentMetadata);

        obsService.putObject(getObsKey(agentId, type), metaDataJson);
        redisClient.set(getRedisKey(agentId, type), metaDataJson, Duration.ofDays(PUBLISH_METADATA_EXPIRE_DAYS));

        log.info("save {} publish metadata {}", type, agentMetadata);
    }

    /**
     * 删除最新发布信息
     *
     * @param agentId agentId
     * @param type 类型，当前取值有latest和treasure
     * @param obsService OBSService
     */
    public void deletePublish(String agentId, String type, CommonObsService obsService) {
        obsService.deleteObject(getObsKey(agentId, type));
        redisClient.delete(getRedisKey(agentId, type));

        log.info("delete {} publish metadata {}", type, agentId);
    }

    /**
     * 获取最新发布信息
     *
     * @param agentId agentId
     * @param type 类型，当前取值有latest和treasure
     * @param obsService OBSService
     * @return AgentMetadata，如果获取失败，返回null
     */
    public AgentMetadata getPublish(String agentId, String type, CommonObsService obsService) {
        boolean readFromRedisFailed = false;

        // 读redis
        String metaString = redisClient.get(getRedisKey(agentId, type));

        // redis读失败，读OBS
        if (StringUtils.isEmpty(metaString)) {
            readFromRedisFailed = true;
            metaString = obsService.getObject(getObsKey(agentId, type));
        }

        // OBS读失败，异常
        if (StringUtils.isEmpty(metaString)) {
            log.error("get AgentMetadata failed for {}", agentId);
            return null;
        }
        AgentMetadata agentMetadata = JSON.parseObject(metaString, AgentMetadata.class);
        if (agentMetadata == null) {
            log.error("parse AgentMetadata failed for {}, content is {}", agentId, metaString);
            return null;
        }

        // redis读失败，OBS读成功，缓存redis
        if (readFromRedisFailed) {
            redisClient.set(getRedisKey(agentId, type), metaString, Duration.ofDays(PUBLISH_METADATA_EXPIRE_DAYS));
        }

        log.info("get {} publish metadata {}", type, agentMetadata);
        return agentMetadata;
    }

    @NotNull
    private String getObsKey(String agentId, String type) {
        return String.format("%s/%s/%s.json", OBS_METADATA_DIR, agentId, agentId + UNDERLINE_STR + type);
    }

    @NotNull
    private String getRedisKey(String agentId, String type) {
        return String.format("agent-builder:agent:metadata:%s:%s", agentId, type);
    }
}
