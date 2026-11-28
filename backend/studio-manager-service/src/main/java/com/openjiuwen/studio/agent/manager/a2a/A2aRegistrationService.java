/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.a2a;

import com.openjiuwen.studio.agent.common.a2a.dto.AgentCardDto;
import com.openjiuwen.studio.agent.common.a2a.enums.RegistrationStatus;
import com.openjiuwen.studio.agent.common.config.RdcProperties;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.manager.entity.AgentRdcRegistrationEntity;
import com.openjiuwen.studio.agent.manager.mapper.AgentRdcRegistrationMapper;
import com.openjiuwen.studio.agent.manager.rdc.RdcRegistrationClient;

import lombok.extern.slf4j.Slf4j;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.List;
import java.util.UUID;

/**
 * A2A 注册编排服务
 *
 * <p>FEAT-131: 编排 Card 生成 → RDC 注册/注销 → 状态持久化</p>
 * <p>注册失败不阻断发布，挂"注册异常"角标 + 重试入口</p>
 */
@Slf4j
@Service
public class A2aRegistrationService {

    private static final String AGENT_CARD_REDIS_PREFIX = "a2a:agent-card:";
    private static final int AGENT_CARD_TTL_DAYS = 10;

    private final RdcProperties rdcProperties;
    private final RdcRegistrationClient rdcClient;
    private final AgentCardGenerator cardGenerator;
    private final AgentRdcRegistrationMapper registrationMapper;
    private final RedisClient redisClient;

    public A2aRegistrationService(RdcProperties rdcProperties,
                                  RdcRegistrationClient rdcClient,
                                  AgentCardGenerator cardGenerator,
                                  AgentRdcRegistrationMapper registrationMapper,
                                  RedisClient redisClient) {
        this.rdcProperties = rdcProperties;
        this.rdcClient = rdcClient;
        this.cardGenerator = cardGenerator;
        this.registrationMapper = registrationMapper;
        this.redisClient = redisClient;
    }

    /**
     * 发布后注册到 RDC（A1）
     *
     * <p>注册失败不阻断发布。失败时标记 REGISTRATION_FAILED，可重试。</p>
     *
     * @param agentId 应用 ID
     * @param description 应用描述
     * @param version 发布版本号
     * @param appType 应用类型
     */
    public void registerOnPublish(String agentId, String description, String version, String appType) {
        if (!rdcProperties.isEnabled()) {
            log.info("A2A registration disabled, skip for agent: {}", agentId);
            return;
        }

        // 检查应用类型是否支持 A2A
        if (!cardGenerator.isSupportedAppType(appType)) {
            log.info("App type {} not supported for A2A, agentId={}, marking NOT_SUPPORTED", appType, agentId);
            upsertRegistration(agentId, null, RegistrationStatus.NOT_SUPPORTED, null, "A1");
            return;
        }

        // 生成 Agent Card
        AgentCardDto card = cardGenerator.generate(agentId, description, version, appType);
        if (card == null) {
            upsertRegistration(agentId, null, RegistrationStatus.NOT_SUPPORTED, null, "A1");
            return;
        }
        String cardJson = cardGenerator.toJson(card);

        // 调用 RDC A1 注册
        String instanceId = rdcClient.register(agentId, cardJson);

        if (instanceId != null) {
            // 注册成功
            upsertRegistration(agentId, instanceId, RegistrationStatus.REGISTERED, cardJson, "A1");
            // 写入 Redis 供 runtime 读取 Card
            redisClient.set(AGENT_CARD_REDIS_PREFIX + agentId, cardJson, Duration.ofDays(AGENT_CARD_TTL_DAYS));
            log.info("A2A registration success, agentId={}, instanceId={}", agentId, instanceId);
        } else {
            // 注册失败，不阻断发布
            upsertRegistration(agentId, null, RegistrationStatus.REGISTRATION_FAILED, cardJson, "A1");
            log.warn("A2A registration failed (non-blocking), agentId={}, publish continues", agentId);
        }
    }

    /**
     * A2 心跳保活：每 10 秒为所有已注册实例发送心跳
     *
     * <p>RDC PostgreSQL 后端不支持 STATIC 免心跳，必须定期续命 TTL。</p>
     */
    @Scheduled(fixedDelay = 10000)
    public void heartbeatAll() {
        if (!rdcProperties.isEnabled()) {
            return;
        }
        List<AgentRdcRegistrationEntity> registered = registrationMapper.selectByStatus(RegistrationStatus.REGISTERED);
        if (registered == null || registered.isEmpty()) {
            return;
        }
        for (AgentRdcRegistrationEntity entity : registered) {
            String agentId = entity.getAgentId();
            String instanceId = entity.getInstanceId();
            if (instanceId == null || instanceId.isBlank()) {
                continue;
            }
            boolean ok = rdcClient.heartbeat(agentId, instanceId);
            if (!ok) {
                log.warn("Heartbeat failed for agentId={}, instanceId={}, will retry next cycle", agentId, instanceId);
            }
        }
    }

    /**
     * 下线/删除时注销（A3）
     *
     * <p>注销失败如实标记可重试，不静默掩盖。</p>
     *
     * @param agentId 应用 ID
     */
    public void deregisterOnOffline(String agentId) {
        if (!rdcProperties.isEnabled()) {
            log.info("A2A registration disabled, skip deregistration for agent: {}", agentId);
            return;
        }

        AgentRdcRegistrationEntity existing = registrationMapper.selectByAgentId(agentId);
        if (existing == null) {
            log.info("No registration record for agent: {}, skip deregistration", agentId);
            return;
        }

        // 不支持的类型直接清理记录
        if (existing.getStatus() == RegistrationStatus.NOT_SUPPORTED) {
            registrationMapper.deleteByAgentId(agentId);
            redisClient.delete(AGENT_CARD_REDIS_PREFIX + agentId);
            return;
        }

        String instanceId = existing.getInstanceId();
        boolean success = rdcClient.deregister(agentId, instanceId);

        if (success) {
            registrationMapper.deleteByAgentId(agentId);
            redisClient.delete(AGENT_CARD_REDIS_PREFIX + agentId);
            log.info("A2A deregistration success, agentId={}", agentId);
        } else {
            // 注销失败，标记可重试
            existing.setStatus(RegistrationStatus.DEREGISTRATION_FAILED);
            existing.setUpdatedOn(new java.util.Date());
            registrationMapper.updateStatusByAgentId(existing);
            log.warn("A2A deregistration failed (marked for retry), agentId={}", agentId);
        }
    }

    /**
     * 重试注册
     *
     * @param agentId 应用 ID
     * @return true=重试成功
     */
    public boolean retryRegistration(String agentId) {
        AgentRdcRegistrationEntity existing = registrationMapper.selectByAgentId(agentId);
        if (existing == null) {
            log.warn("No registration record for retry, agentId={}", agentId);
            return false;
        }

        if (existing.getStatus() != RegistrationStatus.REGISTRATION_FAILED) {
            log.warn("Registration status is not REGISTRATION_FAILED, skip retry, agentId={}, status={}",
                agentId, existing.getStatus());
            return false;
        }

        String cardJson = existing.getAgentCardJson();
        if (cardJson == null || cardJson.isBlank()) {
            log.warn("No agent card json for retry, agentId={}", agentId);
            return false;
        }

        String instanceId = rdcClient.register(agentId, cardJson);
        if (instanceId != null) {
            existing.setInstanceId(instanceId);
            existing.setStatus(RegistrationStatus.REGISTERED);
            existing.setUpdatedOn(new java.util.Date());
            registrationMapper.updateStatusByAgentId(existing);
            redisClient.set(AGENT_CARD_REDIS_PREFIX + agentId, cardJson, Duration.ofDays(AGENT_CARD_TTL_DAYS));
            log.info("A2A retry registration success, agentId={}, instanceId={}", agentId, instanceId);
            return true;
        } else {
            log.warn("A2A retry registration failed, agentId={}", agentId);
            return false;
        }
    }

    /**
     * 重试注销
     *
     * @param agentId 应用 ID
     * @return true=重试成功
     */
    public boolean retryDeregistration(String agentId) {
        AgentRdcRegistrationEntity existing = registrationMapper.selectByAgentId(agentId);
        if (existing == null) {
            return true;
        }

        if (existing.getStatus() != RegistrationStatus.DEREGISTRATION_FAILED) {
            return false;
        }

        boolean success = rdcClient.deregister(agentId, existing.getInstanceId());
        if (success) {
            registrationMapper.deleteByAgentId(agentId);
            redisClient.delete(AGENT_CARD_REDIS_PREFIX + agentId);
            log.info("A2A retry deregistration success, agentId={}", agentId);
            return true;
        } else {
            log.warn("A2A retry deregistration failed, agentId={}", agentId);
            return false;
        }
    }

    /**
     * 查询注册状态
     */
    public AgentRdcRegistrationEntity getRegistration(String agentId) {
        return registrationMapper.selectByAgentId(agentId);
    }

    /**
     * 插入或更新注册记录
     */
    private void upsertRegistration(String agentId, String instanceId,
                                    RegistrationStatus status, String cardJson, String mode) {
        AgentRdcRegistrationEntity existing = registrationMapper.selectByAgentId(agentId);
        java.util.Date now = new java.util.Date();

        if (existing == null) {
            AgentRdcRegistrationEntity entity = new AgentRdcRegistrationEntity();
            entity.setId(UUID.randomUUID().toString());
            entity.setAgentId(agentId);
            entity.setInstanceId(instanceId);
            entity.setStatus(status);
            entity.setAgentCardJson(cardJson);
            entity.setRegistrationMode(mode);
            entity.setCreatedOn(now);
            entity.setUpdatedOn(now);
            registrationMapper.insert(entity);
        } else {
            existing.setInstanceId(instanceId);
            existing.setStatus(status);
            if (cardJson != null) {
                existing.setAgentCardJson(cardJson);
            }
            existing.setRegistrationMode(mode);
            existing.setUpdatedOn(now);
            registrationMapper.updateStatusByAgentId(existing);
        }
    }
}
