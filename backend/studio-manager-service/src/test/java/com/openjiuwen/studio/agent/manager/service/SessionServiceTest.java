/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.startsWith;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.manager.entity.Session;
import com.openjiuwen.studio.agent.manager.entity.User;
import com.openjiuwen.studio.agent.manager.repository.SessionRepository;

import jakarta.servlet.http.HttpServletRequest;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Captor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.lang.reflect.Field;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.Optional;

/**
 * SessionService 基于 RedisClient 单栈的会话缓存行为验证
 * （key 前缀 + JSON 值 + Duration 超时；损坏缓存按未命中处理）。
 */
@ExtendWith(MockitoExtension.class)
class SessionServiceTest {

    private static final int ABSOLUTE_TIMEOUT = 7200;

    private static final int INACTIVITY_TIMEOUT = 1800;

    private static final Duration ABSOLUTE_TIMEOUT_DURATION = Duration.ofSeconds(ABSOLUTE_TIMEOUT);

    /** 与实现同口径的用户 JSON 序列化器（User 含 LocalDateTime 字段，需 JavaTimeModule） */
    private static final ObjectMapper MAPPER = new ObjectMapper()
        .registerModule(new JavaTimeModule())
        .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);

    @Mock
    private SessionRepository sessionRepository;

    @Mock
    private RedisClient redisClient;

    @Mock
    private HttpServletRequest request;

    @InjectMocks
    private SessionService sessionService;

    private User testUser;

    private String testUserJson;

    @Captor
    private ArgumentCaptor<LocalDateTime> timeCaptor;

    @BeforeEach
    void setUp() throws Exception {
        testUser = new User();
        testUser.setId(1L);
        testUser.setUsername("testUser");
        testUser.setDomainId("domain1");
        testUser.setProjectId("project1");
        testUserJson = MAPPER.writeValueAsString(testUser);

        // 使用反射设置私有字段值
        setPrivateField(sessionService, "absoluteTimeoutSeconds", ABSOLUTE_TIMEOUT);
        setPrivateField(sessionService, "inactivityTimeoutSeconds", INACTIVITY_TIMEOUT);
    }

    // 反射工具方法设置私有字段
    private void setPrivateField(Object target, String fieldName, Object value)
        throws NoSuchFieldException, IllegalAccessException {
        Field field = target.getClass().getDeclaredField(fieldName);
        field.setAccessible(true);
        field.set(target, value);
    }

    @Test
    void createSession_ShouldSaveToDbAndRedis() throws Exception {
        // 模拟保存的Session
        Session savedSession = new Session();
        String generatedSessionId = "generated-session-id";
        savedSession.setSessionId(generatedSessionId);

        when(sessionRepository.save(any(Session.class))).thenReturn(savedSession);

        Session result = sessionService.createSession(testUser, request);

        // 验证数据库保存
        verify(sessionRepository).save(any(Session.class));
        assertNotNull(result);
        assertEquals(generatedSessionId, result.getSessionId());
        // 验证Redis存储（key 前缀 + 用户 JSON + 绝对超时 Duration）
        verify(redisClient).set(startsWith("session:"), eq(testUserJson), eq(ABSOLUTE_TIMEOUT_DURATION));
    }

    @Test
    void refreshSession_ShouldUpdateActivityTime() {
        String sessionId = "activeSession";

        // 设置Redis存在该会话
        when(redisClient.exists("session:" + sessionId)).thenReturn(true);
        when(redisClient.get("session:" + sessionId)).thenReturn(testUserJson);

        // 刷新会话
        sessionService.refreshSession(sessionId);

        // 验证数据库更新
        verify(sessionRepository).updateLastActivity(eq(sessionId), any(LocalDateTime.class));
        // 验证Redis续期（原文透传，不做反序列化往返）
        verify(redisClient).set(eq("session:" + sessionId), eq(testUserJson), eq(ABSOLUTE_TIMEOUT_DURATION));
    }

    @Test
    void refreshSession_WhenRedisValueMissing_ShouldSkipRenewal() {
        String sessionId = "noValueSession";
        when(redisClient.exists("session:" + sessionId)).thenReturn(true);
        when(redisClient.get("session:" + sessionId)).thenReturn(null);

        sessionService.refreshSession(sessionId);

        verify(sessionRepository).updateLastActivity(eq(sessionId), any(LocalDateTime.class));
        verify(redisClient, never()).set(anyString(), anyString(), any(Duration.class));
    }

    @Test
    void validateSession_WhenValid_ShouldReturnTrue() {
        String sessionId = "validSession";
        Session activeSession = createValidSession();

        when(redisClient.exists("session:" + sessionId)).thenReturn(true);
        when(sessionRepository.findBySessionId(sessionId)).thenReturn(Optional.of(activeSession));

        assertTrue(sessionService.validateSession(sessionId));
    }

    @Test
    void validateSession_WhenRedisMissing_ShouldReturnFalse() {
        String sessionId = "invalidSession";
        when(redisClient.exists("session:" + sessionId)).thenReturn(false);

        assertFalse(sessionService.validateSession(sessionId));
    }

    @Test
    void validateSession_WhenDbMissing_ShouldReturnFalse() {
        String sessionId = "dbMissingSession";
        when(redisClient.exists("session:" + sessionId)).thenReturn(true);
        when(sessionRepository.findBySessionId(sessionId)).thenReturn(Optional.empty());

        assertFalse(sessionService.validateSession(sessionId));
    }

    @Test
    void validateSession_WhenAbsoluteTimeout_ShouldReturnFalse() {
        String sessionId = "expiredSession";
        Session expiredSession = createValidSession();
        expiredSession.setExpireTime(LocalDateTime.now().minusMinutes(1)); // 设置为过去时间

        when(redisClient.exists("session:" + sessionId)).thenReturn(true);
        when(sessionRepository.findBySessionId(sessionId)).thenReturn(Optional.of(expiredSession));

        assertFalse(sessionService.validateSession(sessionId));
    }

    @Test
    void validateSession_WhenInactiveTimeout_ShouldReturnFalse() {
        String sessionId = "inactiveSession";
        Session inactiveSession = createValidSession();
        // 设置最后活动时间为超过无操作超时时间
        inactiveSession.setLastActivityTime(LocalDateTime.now().minusSeconds(INACTIVITY_TIMEOUT + 1));

        when(redisClient.exists("session:" + sessionId)).thenReturn(true);
        when(sessionRepository.findBySessionId(sessionId)).thenReturn(Optional.of(inactiveSession));

        assertFalse(sessionService.validateSession(sessionId));
    }

    @Test
    void getUserBySession_WhenValid_ShouldReturnUser() {
        String sessionId = "validSession";
        Session activeSession = createValidSession();

        when(redisClient.exists("session:" + sessionId)).thenReturn(true);
        when(sessionRepository.findBySessionId(sessionId)).thenReturn(Optional.of(activeSession));
        when(redisClient.get("session:" + sessionId)).thenReturn(testUserJson);

        Optional<User> user = sessionService.getUserBySession(sessionId);
        assertTrue(user.isPresent());
        assertEquals(testUser, user.get());
    }

    @Test
    void getUserBySession_WhenJsonCorrupted_ShouldReturnEmpty() {
        String sessionId = "corruptedSession";
        Session activeSession = createValidSession();

        when(redisClient.exists("session:" + sessionId)).thenReturn(true);
        when(sessionRepository.findBySessionId(sessionId)).thenReturn(Optional.of(activeSession));
        when(redisClient.get("session:" + sessionId)).thenReturn("not-a-json{");

        // 缓存值损坏按未命中处理，不抛异常
        Optional<User> user = sessionService.getUserBySession(sessionId);
        assertTrue(user.isEmpty());
    }

    @Test
    void getUserBySession_WhenInvalidSession_ShouldReturnEmpty() {
        String sessionId = "invalidSession";
        when(redisClient.exists("session:" + sessionId)).thenReturn(false);

        Optional<User> user = sessionService.getUserBySession(sessionId);
        assertTrue(user.isEmpty());
    }

    @Test
    void cleanupExpiredSessions_ShouldCallBothOperations() {
        // 准备测试数据
        int expectedExpiredCount = 5;
        int expectedDeletedCount = 3;
        // 模拟repository行为
        when(sessionRepository.expireSessions(any(LocalDateTime.class))).thenReturn(expectedExpiredCount);
        when(sessionRepository.deleteOldSessions(any(LocalDateTime.class))).thenReturn(expectedDeletedCount);
        // 执行被测方法
        sessionService.cleanupExpiredSessions();
        // 验证方法调用
        verify(sessionRepository).expireSessions(timeCaptor.capture());
        verify(sessionRepository).deleteOldSessions(timeCaptor.capture());
        // 获取捕获的时间参数

    }

    @Test
    void cleanupExpiredSessions_ShouldHandleZeroResults() {
        // 模拟repository返回0记录
        when(sessionRepository.expireSessions(any())).thenReturn(0);
        when(sessionRepository.deleteOldSessions(any())).thenReturn(0);
        // 执行被测方法
        sessionService.cleanupExpiredSessions();
        // 验证方法仍被调用
        verify(sessionRepository).expireSessions(any());
        verify(sessionRepository).deleteOldSessions(any());
    }

    // 辅助方法：创建有效的Session对象
    private Session createValidSession() {
        Session session = new Session();
        session.setSessionId("validSession");
        session.setStatus(Session.SessionStatus.ACTIVE);
        session.setExpireTime(LocalDateTime.now().plusHours(1));
        session.setLastActivityTime(LocalDateTime.now().minusMinutes(10)); // 10分钟前活动
        return session;
    }
}
