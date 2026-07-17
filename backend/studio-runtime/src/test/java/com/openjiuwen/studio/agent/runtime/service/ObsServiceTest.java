/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.runtime.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.storage.FileStore;
import com.openjiuwen.studio.agent.common.storage.ObsFileStoreImpl;
import com.openjiuwen.studio.agent.runtime.constant.Constant;
import com.openjiuwen.studio.agent.runtime.utils.BaseTest;
import com.openjiuwen.studio.agent.runtime.utils.OkHttpUtils;

import okhttp3.Call;
import okhttp3.OkHttpClient;

import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mock;
import org.redisson.api.RedissonClient;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.util.ReflectionTestUtils;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.SocketTimeoutException;
import java.nio.charset.StandardCharsets;
import java.util.Map;

public class ObsServiceTest extends BaseTest {
    private static final String OBS_CONTENT = "obs_content";

    @MockitoBean
    RedissonClient redissonClientMock;

    @Mock
    private OkHttpUtils okHttpUtils;

    @Autowired
    private ObsService obsService;

    @MockitoBean
    private FileStore fileStore;

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(obsService, "bucket", "workflow-ir");
        ReflectionTestUtils.setField(obsService, "stagingBucket", "agent-builder-files-staging");
        ReflectionTestUtils.setField(obsService, "okHttpUtils", okHttpUtils);
    }

    @Test
    public void testPutObject() {
        when(fileStore.write(anyString(), anyString())).thenReturn(anyString());
        obsService.putObject("", "", "");

        when(fileStore.write(anyString(), any(InputStream.class), any(int.class))).thenReturn(anyString());
        obsService.putObject("", new ByteArrayInputStream(OBS_CONTENT.getBytes(StandardCharsets.UTF_8)), 1);
    }

    @Test
    public void testGetObject() {
        when(fileStore.read(anyString())).thenReturn(OBS_CONTENT);
        Map<String, String> result = obsService.getObject("", "");
        assertEquals(OBS_CONTENT, result.get(Constant.Obs.CONTENT));
    }

    @Test
    public void testGetMd5() {
        when(fileStore.read(anyString())).thenReturn(OBS_CONTENT);
        String md5 = obsService.getMd5("", "");
        assertNotNull(md5);
    }

    @Test
    public void testGetByUrl() throws IOException {
        OkHttpClient okHttpClient = mock(OkHttpClient.class);
        when(okHttpUtils.getHttpClient()).thenReturn(okHttpClient);
        Call mockCall = mock(Call.class);
        when(okHttpClient.newCall(any())).thenReturn(mockCall);
        when(mockCall.execute()).thenThrow(SocketTimeoutException.class);
        String url = "http://test.com/test.txt?";
        assertThrows(AgentStudioException.class, () -> obsService.getByUrl(url));
    }

    @Test
    public void testUploadObsFileWithExpires() {
        when(fileStore.write(anyString(), any(InputStream.class), any(int.class))).thenReturn(anyString());
        InputStream inputStream = new ByteArrayInputStream("test".getBytes(StandardCharsets.UTF_8));
        String url = obsService.uploadObsFileWithExpires(inputStream, "test.txt", 300);
        assertNotNull(url);
    }

    @Test
    public void uploadWithPublicReadTest() {
        try {
            obsService.uploadToStagingWithPublicRead(
                new ByteArrayInputStream(OBS_CONTENT.getBytes(StandardCharsets.UTF_8)), "demo", 10);
        } catch (AgentStudioException e) {
            Assertions.assertEquals(StudioError.OBS_FAILED, e.getErrorCode());
        }

        when(fileStore.write(anyString(), any(InputStream.class), any(int.class))).thenReturn(anyString());
        InputStream inputStream = new ByteArrayInputStream(OBS_CONTENT.getBytes(StandardCharsets.UTF_8));
        String url = obsService.uploadToStagingWithExpires(inputStream, "test.txt", 300);
        assertNotNull(url);
    }
}
