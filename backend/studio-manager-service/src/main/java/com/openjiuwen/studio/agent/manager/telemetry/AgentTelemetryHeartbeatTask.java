/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.telemetry;

import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.Duration;

/**
 * agent 清单快照心跳任务。
 *
 * <p>每周期重读 DB 在册 agent 全量存量，经 OTLP logs 逐 agent 发送 snapshot 记录，
 * 作为"当前态快照 + 对账"依据：后端按 agent_id 取最新 snapshot 即当前清单；
 * 生命周期事件丢失时，下一周期快照自动修复（自愈）。
 * DB 为空时仍发送一条 0 计数心跳，用于区分"没有 agent"与"服务不可用"。
 *
 * <p>多实例部署时通过分布式锁保证同一周期只有一个实例上报。
 * 间隔须 <= 遥测后端 staleness 窗口的 1/5（如 Prometheus lookback 5min -> <= 60s）。
 */
@Component
@Slf4j
public class AgentTelemetryHeartbeatTask {

    private static final String HEARTBEAT_LOCK = "AGENT_TELEMETRY_HEARTBEAT_LOCK";

    /**
     * 分布式锁等待时间（秒）
     */
    private static final int LOCK_TIME = 10;

    @Autowired
    private AgentTelemetryService telemetryService;

    @Autowired
    private AgentMapper agentMapper;

    @Autowired
    private RedisClient redisClient;

    @Scheduled(fixedDelayString = "${studio.agentTelemetry.heartbeatIntervalMillis:60000}",
        initialDelayString = "${studio.agentTelemetry.heartbeatIntervalMillis:60000}")
    public void emitInventorySnapshot() {
        if (!telemetryService.isEnabled()) {
            return;
        }
        RedisLock lock = null;
        try {
            lock = redisClient.getLock(HEARTBEAT_LOCK);
            if (lock.tryLock(Duration.ofSeconds(LOCK_TIME))) {
                telemetryService.emitSnapshot(agentMapper.selectAllActiveAgents());
            } else {
                log.debug("skip agent telemetry heartbeat, another instance holds the lock");
            }
        } catch (Exception e) {
            log.warn("agent telemetry heartbeat failed: {}", e.getMessage());
        } finally {
            if (lock != null) {
                lock.unlock();
            }
        }
    }
}
