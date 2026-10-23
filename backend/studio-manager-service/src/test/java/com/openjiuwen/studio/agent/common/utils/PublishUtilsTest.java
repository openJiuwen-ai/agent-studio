/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */

package com.openjiuwen.studio.agent.common.utils;

import com.openjiuwen.studio.agent.common.bo.AgentMetadata;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.service.CommonObsService;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class PublishUtilsTest {

    @Mock
    private RedisClient redisClient;

    @Mock
    private CommonObsService obsService;

    @InjectMocks
    private PublishUtils publishUtils;

    @Test
    void testSavePublish() {
        AgentMetadata metadata = AgentMetadata.builder()
                .agentId("agent-1")
                .domainId("domain-1")
                .projectId("project-1")
                .build();
        doNothing().when(obsService).putObject(anyString(), anyString());

        publishUtils.savePublish(metadata, "latest", obsService);

        verify(obsService).putObject(anyString(), anyString());
        verify(redisClient).set(anyString(), anyString(), any(Duration.class));
    }

    @Test
    void testDeletePublish() {
        doNothing().when(obsService).deleteObject(anyString());
        when(redisClient.delete(anyString())).thenReturn(true);

        publishUtils.deletePublish("agent-1", "latest", obsService);

        verify(obsService).deleteObject(anyString());
        verify(redisClient).delete(anyString());
    }

    @Test
    void testGetPublish_FromRedis() {
        String json = "{\"agentId\":\"agent-1\",\"domainId\":\"d\",\"projectId\":\"p\"}";
        when(redisClient.get(anyString())).thenReturn(json);

        AgentMetadata result = publishUtils.getPublish("agent-1", "latest", obsService);

        assertNotNull(result);
    }

    @Test
    void testGetPublish_FromObs() {
        String json = "{\"agentId\":\"agent-1\",\"domainId\":\"d\",\"projectId\":\"p\"}";
        when(redisClient.get(anyString())).thenReturn(null);
        when(obsService.getObject(anyString())).thenReturn(json);

        AgentMetadata result = publishUtils.getPublish("agent-1", "latest", obsService);

        assertNotNull(result);
    }

    @Test
    void testGetPublish_BothEmpty() {
        when(redisClient.get(anyString())).thenReturn(null);
        when(obsService.getObject(anyString())).thenReturn(null);

        AgentMetadata result = publishUtils.getPublish("agent-1", "latest", obsService);

        assertNull(result);
    }

    @Test
    void testGetPublish_InvalidJson() {
        when(redisClient.get(anyString())).thenReturn("invalid-json{{{");

        assertThrows(Exception.class, () -> publishUtils.getPublish("agent-1", "latest", obsService));
    }
}
