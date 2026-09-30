/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.manager.entity.Session;
import com.openjiuwen.studio.agent.manager.entity.User;
import com.openjiuwen.studio.agent.manager.repository.SessionRepository;
import com.openjiuwen.studio.agent.common.redis.RedisClient;

import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.Optional;

/**
 * 会话服务层 - 支持自定义超时机制
 *
 * <p>Redis 访问统一走 {@link RedisClient} 适配层（序列化为 JSON 字符串存储），
 * 支持通过 Provider 插件机制替换底层实现，不再直连 RedisTemplate。
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class SessionService {

    private static final String REDIS_SESSION_PREFIX = "session:";

    private final SessionRepository sessionRepository;

    private final RedisClient redisClient;

    private final ObjectMapper objectMapper;

    // 从配置文件中注入超时时间
    @Value("${app.auth.session.absolute-timeout:86400}")
    private int absoluteTimeoutSeconds; // 绝对超时（从登录开始算起）

    @Value("${app.auth.session.inactivity-timeout:1800}")
    private int inactivityTimeoutSeconds; // 无操作超时

    @Value("${app.auth.session.cleanup.retention-days:3}")
    private int retentionDays; // 会话保留天数
    /**
     * 创建会话（Redis + 数据库）
     */
    @Transactional
    public Session createSession(User user, HttpServletRequest request) {
        String sessionId = generateSessionId();
        LocalDateTime now = LocalDateTime.now();
        LocalDateTime absoluteExpireTime = now.plusSeconds(absoluteTimeoutSeconds);

        // 创建数据库会话记录
        Session session = new Session();
        session.setSessionId(sessionId);
        session.setUserId(user.getId());
        session.setUsername(user.getUsername());
        session.setLoginTime(now);
        session.setLastActivityTime(now);
        session.setExpireTime(absoluteExpireTime);
        session.setDomainId(user.getDomainId());
        session.setProjectId(user.getProjectId());

        Session savedSession = sessionRepository.save(session);

        // 存储到Redis（使用绝对超时时间，JSON 字符串形式）
        String redisKey = REDIS_SESSION_PREFIX + sessionId;
        redisClient.set(redisKey, writeUserJson(user), Duration.ofSeconds(absoluteTimeoutSeconds));


        return savedSession;
    }

    /**
     * 刷新会话 - 更新最后活动时间
     */
    @Transactional
    public void refreshSession(String sessionId) {
        LocalDateTime now = LocalDateTime.now();

        // 更新数据库最后活动时间
        sessionRepository.updateLastActivity(sessionId, now);

        // 更新Redis中的用户对象（如果需要）
        String redisKey = REDIS_SESSION_PREFIX + sessionId;
        String userJson = redisClient.get(redisKey);
        if (userJson != null) {
            // 重新设置Redis，使用绝对超时时间
            redisClient.set(redisKey, userJson, Duration.ofSeconds(absoluteTimeoutSeconds));
        }

    }

    /**
     * 校验会话 - 检查绝对超时和无操作超时
     */
    public boolean validateSession(String sessionId) {
        if (sessionId == null) {
            return false;
        }

        // 检查Redis中是否存在
        String redisKey = REDIS_SESSION_PREFIX + sessionId;
        if (!redisClient.exists(redisKey)) {
            return false;
        }

        // 检查数据库记录
        Optional<Session> sessionOpt = sessionRepository.findBySessionId(sessionId);
        if (sessionOpt.isEmpty()) {
            return false;
        }

        Session session = sessionOpt.get();

        // 检查会话状态
        if (session.getStatus() != Session.SessionStatus.ACTIVE) {
            return false;
        }

        // 检查绝对超时（从登录开始算起）
        if (session.getExpireTime() == null || LocalDateTime.now().isAfter(session.getExpireTime())) {
            return false;
        }

        // 检查无操作超时（基于最后活动时间）
        if (session.isTimedOut(inactivityTimeoutSeconds)) {
            return false;
        }

        return true;
    }

    /**
     * 根据会话ID获取用户信息
     */
    public Optional<User> getUserBySession(String sessionId) {
        if (!validateSession(sessionId)) {
            return Optional.empty();
        }

        String redisKey = REDIS_SESSION_PREFIX + sessionId;
        return readUserJson(redisKey);
    }

    /**
     * 清理过期会话 - 完善版：包含状态标记和物理删除
     */
    @Transactional
    public void cleanupExpiredSessions() {
        LocalDateTime currentTime = LocalDateTime.now();

        // 1. 标记过期会话
        int expiredCount = sessionRepository.expireSessions(currentTime);

        // 2. 物理删除超过保留期限的旧记录
        LocalDateTime retentionTime = currentTime.minusDays(retentionDays);
        int deletedCount = sessionRepository.deleteOldSessions(retentionTime);

        log.info("Cleared {} expired sessions and deleted {} old session records", expiredCount, deletedCount);
    }

    /**
     * 生成会话ID
     */
    private String generateSessionId() {
        return java.util.UUID.randomUUID().toString();
    }

    /**
     * 序列化用户对象为 JSON（失败时返回空串，会话校验将退化为无效）。
     */
    private String writeUserJson(User user) {
        try {
            return objectMapper.writeValueAsString(user);
        } catch (Exception e) {
            log.error("Serialize user to json failed, username: {}", user.getUsername(), e);
            return "";
        }
    }

    /**
     * 反序列化 Redis 中的用户 JSON（损坏数据降级为空）。
     */
    private Optional<User> readUserJson(String redisKey) {
        String userJson = redisClient.get(redisKey);
        if (userJson == null || userJson.isEmpty()) {
            return Optional.empty();
        }
        try {
            return Optional.of(objectMapper.readValue(userJson, User.class));
        } catch (Exception e) {
            log.warn("Deserialize user from redis failed, degrade to empty, key: {}", redisKey, e);
            return Optional.empty();
        }
    }
}
