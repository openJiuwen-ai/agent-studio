/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.manager.entity.Session;
import com.openjiuwen.studio.agent.manager.entity.User;
import com.openjiuwen.studio.agent.manager.repository.SessionRepository;

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
 * 会话用户缓存统一走 RedisClient（Provider 单栈），以 JSON 字符串存储，
 * 不再依赖 RedisTemplate 第二栈。
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class SessionService {

    private static final String REDIS_SESSION_PREFIX = "session:";

    /** 会话用户 JSON 序列化器（User 含 LocalDateTime 字段，需 JavaTimeModule）
     *  宽容未知字段：旧 RedisTemplate Jackson 默认类型的存量缓存条目含
     *  @class 等额外属性，FAIL_ON_UNKNOWN_PROPERTIES 会让解析失败→按
     *  cache miss 处理，升级瞬间存量会话全部失效（用户被登出）。 */
    private static final ObjectMapper SESSION_MAPPER = new ObjectMapper()
        .registerModule(new JavaTimeModule())
        .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS)
        .disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);

    private final SessionRepository sessionRepository;

    private final RedisClient redisClient;

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

        // 存储到Redis（使用绝对超时时间）
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
        if (redisClient.exists(redisKey)) {
            // 原文续期即可，无需反序列化往返
            String userJson = redisClient.get(redisKey);
            if (userJson != null) {
                // 重新设置Redis，使用绝对超时时间
                redisClient.set(redisKey, userJson, Duration.ofSeconds(absoluteTimeoutSeconds));
            }
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
        return Optional.ofNullable(readUserJson(redisClient.get(redisKey)));
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
     * 会话用户序列化为 JSON（失败抛出，阻断创建流程）
     */
    private String writeUserJson(User user) {
        try {
            return SESSION_MAPPER.writeValueAsString(user);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("Session user serialization failed: " + user.getUsername(), e);
        }
    }

    /**
     * 会话用户反序列化（缓存值损坏按未命中处理，不影响会话校验）
     */
    private User readUserJson(String userJson) {
        if (userJson == null) {
            return null;
        }
        try {
            return SESSION_MAPPER.readValue(userJson, User.class);
        } catch (JsonProcessingException e) {
            log.warn("Session user cache deserialization failed, treated as cache miss", e);
            return null;
        }
    }

}
