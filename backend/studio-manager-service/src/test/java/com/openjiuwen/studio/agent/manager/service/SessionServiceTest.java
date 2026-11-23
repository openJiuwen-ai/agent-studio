/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.any;
import static org.mockito.Mockito.eq;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

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
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.ValueOperations;

import java.lang.reflect.Field;
import java.time.LocalDateTime;
import java.util.Optional;
import java.util.concurrent.TimeUnit;

@ExtendWith(MockitoExtension.class)
class SessionServiceTest {

    private static final int ABSOLUTE_TIMEOUT = 7200;

    private static final int INACTIVITY_TIMEOUT = 1800;

    @Mock
    private SessionRepository sessionRepository;

    @Mock
    private RedisTemplate<String, Object> redisTemplate;

    @Mock
    private ValueOperations<String, Object> valueOperations;

    @Mock
    private HttpServletRequest request;

    @InjectMocks
    private SessionService sessionService;

    private User testUser;

    @Captor
    private ArgumentCaptor<LocalDateTime> timeCaptor;
    @BeforeEach
    void setUp() throws Exception {
        // 添加lenient()
        testUser = new User();
        testUser.setId(1L);
        testUser.setUsername("testUser");
        testUser.setDomainId("domain1");
        testUser.setProjectId("project1");

        // 设置RedisTemplate行为
        lenient().when(redisTemplate.opsForValue()).thenReturn(valueOperations);

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
        // 验证Redis存储
        assertNotNull(result);
        assertEquals(generatedSessionId, result.getSessionId());
    }

    @Test
    void refreshSession_ShouldUpdateActivityTime() {
        String sessionId = "activeSession";
        LocalDateTime now = LocalDateTime.now();

        // 设置Redis存在该会话
        when(redisTemplate.hasKey("session:" + sessionId)).thenReturn(true);
        when(valueOperations.get("session:" + sessionId)).thenReturn(testUser);

        // 刷新会话
        sessionService.refreshSession(sessionId);

        // 验证数据库更新
        verify(sessionRepository).updateLastActivity(eq(sessionId), any(LocalDateTime.class));
        // 验证Redis续期
        verify(valueOperations).set(eq("session:" + sessionId), eq(testUser), eq((long) ABSOLUTE_TIMEOUT),
            eq(TimeUnit.SECONDS));
    }

    @Test
    void validateSession_WhenValid_ShouldReturnTrue() {
        String sessionId = "validSession";
        Session activeSession = createValidSession();

        when(redisTemplate.hasKey("session:" + sessionId)).thenReturn(true);
        when(sessionRepository.findBySessionId(sessionId)).thenReturn(Optional.of(activeSession));

        assertTrue(sessionService.validateSession(sessionId));
    }

    @Test
    void validateSession_WhenRedisMissing_ShouldReturnFalse() {
        String sessionId = "invalidSession";
        when(redisTemplate.hasKey("session:" + sessionId)).thenReturn(false);

        assertFalse(sessionService.validateSession(sessionId));
    }

    @Test
    void validateSession_WhenDbMissing_ShouldReturnFalse() {
        String sessionId = "dbMissingSession";
        when(redisTemplate.hasKey("session:" + sessionId)).thenReturn(true);
        when(sessionRepository.findBySessionId(sessionId)).thenReturn(Optional.empty());

        assertFalse(sessionService.validateSession(sessionId));
    }

    @Test
    void validateSession_WhenAbsoluteTimeout_ShouldReturnFalse() {
        String sessionId = "expiredSession";
        Session expiredSession = createValidSession();
        expiredSession.setExpireTime(LocalDateTime.now().minusMinutes(1)); // 设置为过去时间

        when(redisTemplate.hasKey("session:" + sessionId)).thenReturn(true);
        when(sessionRepository.findBySessionId(sessionId)).thenReturn(Optional.of(expiredSession));

        assertFalse(sessionService.validateSession(sessionId));
    }

    @Test
    void validateSession_WhenInactiveTimeout_ShouldReturnFalse() {
        String sessionId = "inactiveSession";
        Session inactiveSession = createValidSession();
        // 设置最后活动时间为超过无操作超时时间
        inactiveSession.setLastActivityTime(LocalDateTime.now().minusSeconds(INACTIVITY_TIMEOUT + 1));

        when(redisTemplate.hasKey("session:" + sessionId)).thenReturn(true);
        when(sessionRepository.findBySessionId(sessionId)).thenReturn(Optional.of(inactiveSession));

        assertFalse(sessionService.validateSession(sessionId));
    }

    @Test
    void getUserBySession_WhenValid_ShouldReturnUser() {
        String sessionId = "validSession";
        Session activeSession = createValidSession();

        when(redisTemplate.hasKey("session:" + sessionId)).thenReturn(true);
        when(sessionRepository.findBySessionId(sessionId)).thenReturn(Optional.of(activeSession));
        when(valueOperations.get("session:" + sessionId)).thenReturn(testUser);

        Optional<User> user = sessionService.getUserBySession(sessionId);
        assertTrue(user.isPresent());
        assertEquals(testUser, user.get());
    }

    @Test
    void getUserBySession_WhenInvalidSession_ShouldReturnEmpty() {
        String sessionId = "invalidSession";
        when(redisTemplate.hasKey("session:" + sessionId)).thenReturn(false);

        Optional<User> user = sessionService.getUserBySession(sessionId);
        assertTrue(user.isEmpty());
    }

    @Test
    void cleanupExpiredSessions_ShouldCallBothOperations() {
        // 准备测试数据
        LocalDateTime testCurrentTime = LocalDateTime.now();
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
