/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.service.environment;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;
import com.openjiuwen.studio.agent.manager.entity.EnvironmentManagerEntity;
import com.openjiuwen.studio.agent.manager.entity.EnvironmentVariableEntity;
import com.openjiuwen.studio.agent.manager.mapper.EnvironmentManagerMapper;
import com.openjiuwen.studio.agent.manager.mapper.EnvironmentVariableMapper;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Duration;
import java.util.Collections;
import java.util.List;

@ExtendWith(MockitoExtension.class)
class EnvironmentCacheUtilTest {

    @Mock
    private EnvironmentManagerMapper environmentManagerMapper;

    @Mock
    private EnvironmentVariableMapper environmentVariableMapper;

    @Mock
    private RedisClient redisClient;

    @InjectMocks
    private EnvironmentCacheUtil environmentCacheUtil;

    @Test
    void testUpdateEnvironmentCache_WithValue() {
        environmentCacheUtil.updateEnvironmentCache("env1", "ws1", "{\"key\":\"val\"}");
        verify(redisClient).set(eq("environment:env1:workspaceId:ws1"), eq("{\"key\":\"val\"}"), any(Duration.class));
    }

    @Test
    void testUpdateEnvironmentCache_WithBlankValue() {
        environmentCacheUtil.updateEnvironmentCache("env1", "ws1", "");
        verify(redisClient).set(eq("environment:env1:workspaceId:ws1"), eq("{}"), any(Duration.class));
    }

    @Test
    void testUpdateEnvironmentCache_WithNullValue() {
        environmentCacheUtil.updateEnvironmentCache("env1", "ws1", null);
        verify(redisClient).set(eq("environment:env1:workspaceId:ws1"), eq("{}"), any(Duration.class));
    }

    @Test
    void testDeleteEnvironmentCache() {
        environmentCacheUtil.deleteEnvironmentCache("env1", "ws1");
        verify(redisClient).delete("environment:env1:workspaceId:ws1");
    }

    @Test
    void testGetEnvironmentCache() {
        when(redisClient.get("environment:env1:workspaceId:ws1")).thenReturn("{\"key\":\"val\"}");
        String result = environmentCacheUtil.getEnvironmentCache("env1", "ws1");
        assertEquals("{\"key\":\"val\"}", result);
    }

    @Test
    void testGetEnvironmentCache_NotFound() {
        when(redisClient.get(anyString())).thenReturn(null);
        String result = environmentCacheUtil.getEnvironmentCache("env1", "ws1");
        assertEquals(null, result);
    }

    @Test
    void testIsExistEnvironmentVariableCache_True() {
        when(redisClient.exists("environment:env1:workspaceId:ws1")).thenReturn(true);
        assertTrue(environmentCacheUtil.isExistEnvironmentVariableCache("env1", "ws1"));
    }

    @Test
    void testIsExistEnvironmentVariableCache_False() {
        when(redisClient.exists("environment:env1:workspaceId:ws1")).thenReturn(false);
        assertFalse(environmentCacheUtil.isExistEnvironmentVariableCache("env1", "ws1"));
    }

    @Test
    void testRefreshCachedEnvironmentVariables_LockFailed() throws Exception {
        RedisLock lock = mock(RedisLock.class);
        when(redisClient.getLock(anyString())).thenReturn(lock);
        when(lock.tryLock(any(Duration.class))).thenReturn(false);

        environmentCacheUtil.refreshCachedEnvironmentVariables();

        verify(environmentManagerMapper, never()).findAllWithGroupByProjectId();
    }

    @Test
    void testRefreshCachedEnvironmentVariables_EmptyProjects() throws Exception {
        RedisLock lock = mock(RedisLock.class);
        when(redisClient.getLock(anyString())).thenReturn(lock);
        when(lock.tryLock(any(Duration.class))).thenReturn(true);
        when(environmentManagerMapper.findAllWithGroupByProjectId()).thenReturn(Collections.emptyList());

        environmentCacheUtil.refreshCachedEnvironmentVariables();

        verify(lock).unlock();
    }

    @Test
    void testRefreshCachedEnvironmentVariables_WithData() throws Exception {
        RedisLock lock = mock(RedisLock.class);
        when(redisClient.getLock(anyString())).thenReturn(lock);
        when(lock.tryLock(any(Duration.class))).thenReturn(true);
        when(environmentManagerMapper.findAllWithGroupByProjectId()).thenReturn(List.of("proj1"));

        EnvironmentManagerEntity envEntity = new EnvironmentManagerEntity();
        envEntity.setId("env1");
        envEntity.setName("dev");
        when(environmentManagerMapper.findByProjectId("proj1")).thenReturn(List.of(envEntity));

        EnvironmentVariableEntity varEntity = new EnvironmentVariableEntity();
        varEntity.setEnvId("env1");
        varEntity.setWorkspaceId("ws1");
        varEntity.setEnvVariable("{\"k\":\"v\"}");
        when(environmentVariableMapper.findByProjectIdAndEnvId("proj1", "env1")).thenReturn(List.of(varEntity));

        environmentCacheUtil.refreshCachedEnvironmentVariables();

        verify(redisClient).set(eq("environment:env1:workspaceId:ws1"), eq("{\"k\":\"v\"}"), any(Duration.class));
        verify(lock).unlock();
    }

    @Test
    void testRefreshCachedEnvironmentVariables_WithBlankEnvVariable() throws Exception {
        RedisLock lock = mock(RedisLock.class);
        when(redisClient.getLock(anyString())).thenReturn(lock);
        when(lock.tryLock(any(Duration.class))).thenReturn(true);
        when(environmentManagerMapper.findAllWithGroupByProjectId()).thenReturn(List.of("proj1"));

        EnvironmentManagerEntity envEntity = new EnvironmentManagerEntity();
        envEntity.setId("env1");
        envEntity.setName("dev");
        when(environmentManagerMapper.findByProjectId("proj1")).thenReturn(List.of(envEntity));

        EnvironmentVariableEntity varEntity = new EnvironmentVariableEntity();
        varEntity.setEnvId("env1");
        varEntity.setWorkspaceId("ws1");
        varEntity.setEnvVariable("");
        when(environmentVariableMapper.findByProjectIdAndEnvId("proj1", "env1")).thenReturn(List.of(varEntity));

        environmentCacheUtil.refreshCachedEnvironmentVariables();

        verify(redisClient).set(eq("environment:env1:workspaceId:ws1"), eq("{}"), any(Duration.class));
    }

    @Test
    void testRefreshCachedEnvironmentVariables_ExceptionThrows() throws Exception {
        RedisLock lock = mock(RedisLock.class);
        when(redisClient.getLock(anyString())).thenReturn(lock);
        when(lock.tryLock(any(Duration.class))).thenThrow(new RuntimeException("Redis error"));

        assertThrows(AgentStudioException.class, () -> environmentCacheUtil.refreshCachedEnvironmentVariables());
    }

    @Test
    void testUpdateDefaultEnvironmentCache_WithValues() {
        environmentCacheUtil.updateDefaultEnvironmentCache("p1", "env1");
        verify(redisClient).set(eq("project:p1:default_environment"), eq("env1"), any(Duration.class));
    }

    @Test
    void testUpdateDefaultEnvironmentCache_WithBlankProjectId() {
        environmentCacheUtil.updateDefaultEnvironmentCache("", "env1");
        verify(redisClient, never()).set(anyString(), anyString(), any(Duration.class));
    }

    @Test
    void testUpdateDefaultEnvironmentCache_WithNullProjectId() {
        environmentCacheUtil.updateDefaultEnvironmentCache(null, "env1");
        verify(redisClient, never()).set(anyString(), anyString(), any(Duration.class));
    }

    @Test
    void testUpdateDefaultEnvironmentCache_WithBlankEnvId() {
        environmentCacheUtil.updateDefaultEnvironmentCache("p1", "");
        verify(redisClient, never()).set(anyString(), anyString(), any(Duration.class));
    }

    @Test
    void testDeleteDefaultEnvironmentCache_WithProjectId() {
        environmentCacheUtil.deleteDefaultEnvironmentCache("p1");
        verify(redisClient).delete("project:p1:default_environment");
    }

    @Test
    void testDeleteDefaultEnvironmentCache_WithBlankProjectId() {
        environmentCacheUtil.deleteDefaultEnvironmentCache("");
        verify(redisClient, never()).delete(anyString());
    }

    @Test
    void testDeleteDefaultEnvironmentCache_WithNullProjectId() {
        environmentCacheUtil.deleteDefaultEnvironmentCache(null);
        verify(redisClient, never()).delete(anyString());
    }
}
