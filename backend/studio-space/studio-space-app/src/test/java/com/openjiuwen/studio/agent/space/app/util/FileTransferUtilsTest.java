/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.space.app.util;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.space.app.enums.AgentBuilderStorageType;
import com.openjiuwen.studio.agent.space.app.enums.AgentBuilderUploadScene;
import com.openjiuwen.studio.agent.space.common.context.AuthorizationContextHolder;
import com.openjiuwen.studio.agent.space.common.exception.AgentSpaceException;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.UUID;

/**
 * FileTransferUtils单元测试
 */
@ExtendWith(MockitoExtension.class)
class FileTransferUtilsTest {
    @InjectMocks
    private FileTransferUtils fileTransferUtils;

    @Mock
    private ObsApiClient obsApiClient;

    @Mock
    private FileTransferUtils.AgentBuilderFile AgentBuilderFile;

    private static final String TEST_BUCKET_NAME = "agentBuilder";

    private static final String TEST_DOMAIN_ID = "test_domain";

    private static final String TEST_TASK_ID = "test_task_id";

    @BeforeEach
    void setUp() {
        // 设置测试环境
        ReflectionTestUtils.setField(fileTransferUtils, "storageType", "OBS");
        ReflectionTestUtils.setField(fileTransferUtils, "SPACE_OBS_BUCKET_NAME", TEST_BUCKET_NAME);
        ReflectionTestUtils.setField(fileTransferUtils, "SPACE_OBS_DIRECTORY_TMP",
            "space/task/tmp/{domain_id}/{UUID}/");
        ReflectionTestUtils.setField(fileTransferUtils, "SPACE_OBS_DIRECTORY_RUNTIME",
            "space/task/runtime/{domain_id}/{task_id}/");
    }

    @Test
    void testUploadTaskFile_UserUploadSceneSuccess() {
        // 模拟正常用户上传场景
        try (MockedStatic<AuthorizationContextHolder> mockedContext = mockStatic(AuthorizationContextHolder.class)) {
            mockedContext.when(AuthorizationContextHolder::domainId).thenReturn(TEST_DOMAIN_ID);

            // 设置模拟行为
            String expectedUploadKey = "space/task/tmp/test_domain/" + UUID.randomUUID() + "/test.txt";
            when(obsApiClient.uploadFile(anyString(), anyString(), any(FileTransferUtils.AgentBuilderFile.class)))
                .thenReturn(expectedUploadKey);

            // 执行测试
            FileTransferUtils.FileTransferResult result = fileTransferUtils.uploadTaskFile(AgentBuilderFile,
                AgentBuilderUploadScene.USER_UPLOAD);

            // 验证结果
            assertNotNull(result);
            assertTrue(result.isSuccess());
            assertEquals(expectedUploadKey, result.getFileKey());
            assertEquals(AgentBuilderStorageType.OBS, result.getStorageType());
            verify(obsApiClient, times(1)).uploadFile(eq(TEST_BUCKET_NAME), anyString(), eq(AgentBuilderFile));
        }
    }

    @Test
    void testUploadTaskFile_RuntimeUploadSceneWithTaskIdSuccess() {
        // 模拟正常运行时上传场景
        try (MockedStatic<AuthorizationContextHolder> mockedContext = mockStatic(AuthorizationContextHolder.class)) {
            mockedContext.when(AuthorizationContextHolder::domainId).thenReturn(TEST_DOMAIN_ID);

            // 设置模拟行为
            String expectedUploadKey = "space/task/runtime/" + TEST_DOMAIN_ID + "/" + TEST_TASK_ID + "/test.txt";
            when(obsApiClient.uploadFile(anyString(), anyString(), any(FileTransferUtils.AgentBuilderFile.class)))
                .thenReturn(expectedUploadKey);

            // 执行测试
            FileTransferUtils.FileTransferResult result = fileTransferUtils.uploadTaskFile(AgentBuilderFile, TEST_TASK_ID,
                AgentBuilderUploadScene.RUNTIME_UPLOAD);

            // 验证结果
            assertNotNull(result);
            assertTrue(result.isSuccess());
            assertEquals(expectedUploadKey, result.getFileKey());
            assertEquals(AgentBuilderStorageType.OBS, result.getStorageType());
            verify(obsApiClient, times(1)).uploadFile(eq(TEST_BUCKET_NAME), anyString(), eq(AgentBuilderFile));
        }
    }

    @Test
    void testUploadTaskFile_DirectoryStructureValidation() {
        when(obsApiClient.uploadFile(anyString(), anyString(), any(FileTransferUtils.AgentBuilderFile.class)))
            .thenReturn("space/task/tmp/test_domain/obs_temp_test_id/test.txt");

        // 执行测试
        FileTransferUtils.FileTransferResult result = fileTransferUtils.uploadTaskFile(AgentBuilderFile,
            AgentBuilderUploadScene.USER_UPLOAD);

        // 验证目录结构
        String fileKey = result.getFileKey();
        assertTrue(fileKey.startsWith("space/task/tmp/"));
        assertTrue(fileKey.contains("test_domain"));
        assertTrue(fileKey.contains("obs_temp_"));
        assertTrue(fileKey.endsWith("test.txt"));
    }

    @Test
    void testUploadTaskFile_RuntimeSceneDirectoryStructureValidation() {
        when(obsApiClient.uploadFile(anyString(), anyString(), any(FileTransferUtils.AgentBuilderFile.class)))
            .thenReturn("space/task/runtime/test_domain/test_task_id/test.txt");

        // 执行测试
        FileTransferUtils.FileTransferResult result = fileTransferUtils.uploadTaskFile(AgentBuilderFile, TEST_TASK_ID,
            AgentBuilderUploadScene.RUNTIME_UPLOAD);

        // 验证目录结构
        String fileKey = result.getFileKey();
        assertTrue(fileKey.startsWith("space/task/runtime/"));
        assertTrue(fileKey.contains("test_domain"));
        assertTrue(fileKey.contains("test_task_id"));
        assertTrue(fileKey.endsWith("test.txt"));
    }

    @Test
    void testUploadTaskFile_OverloadedMethodWithTwoParameters() {
        when(obsApiClient.uploadFile(anyString(), anyString(), any(FileTransferUtils.AgentBuilderFile.class)))
            .thenReturn("space/task/tmp/test_domain/obs_temp_test_id/test.txt");

        // 执行测试 - 使用重载的方法
        FileTransferUtils.FileTransferResult result = fileTransferUtils.uploadTaskFile(AgentBuilderFile,
            AgentBuilderUploadScene.USER_UPLOAD);

        // 验证结果
        assertNotNull(result);
        assertTrue(result.isSuccess());
        verify(obsApiClient, times(1)).uploadFile(eq(TEST_BUCKET_NAME), anyString(), eq(AgentBuilderFile));
    }

    @Test
    void testAgentBuilderFileCreation_WithValidBytes() {
        // 测试AgentBuilderFile的创建
        FileTransferUtils.AgentBuilderFile testFile = new FileTransferUtils.AgentBuilderFile();
        testFile.setOriginalFilename("test.txt");
        testFile.setBytes(new byte[] {1, 2, 3, 4, 5});

        // 验证方法调用
        assertNotNull(testFile.getInputStream());
        assertEquals("test.txt", testFile.getOriginalFilename());
        assertEquals(5, testFile.getBytes().length);
    }

    @Test
    void testFileTransferResult_WithNullFile() {
        // 测试FileTransferResult处理空文件的情况
        FileTransferUtils.AgentBuilderFile nullFile = null;

        // 验证方法能处理null参数而不崩溃
        assertDoesNotThrow(() -> {
            fileTransferUtils.uploadTaskFile(nullFile, AgentBuilderUploadScene.USER_UPLOAD);
        });
    }

    @Test
    void testUploadTaskFile_ObsEnableTrueUploadFailThrowsException() {
        // 设置obsEnable为true
        ReflectionTestUtils.setField(fileTransferUtils, "storageType", "OBS");

        // 模拟obsApiClient上传文件时抛出AgentSpaceException
        when(obsApiClient.uploadFile(anyString(), anyString(), any(FileTransferUtils.AgentBuilderFile.class)))
            .thenThrow(new AgentSpaceException("upload failed"));

        // 验证调用uploadTaskFile方法时抛出AgentSpaceException
        AgentSpaceException exception = assertThrows(AgentSpaceException.class, () -> {
            fileTransferUtils.uploadTaskFile(AgentBuilderFile, AgentBuilderUploadScene.USER_UPLOAD);
        });

        assertEquals("failed to upload file to obs!", exception.getMessage());
        verify(obsApiClient, times(1)).uploadFile(eq(TEST_BUCKET_NAME), anyString(), eq(AgentBuilderFile));
    }

    @Test
    void testUploadTaskFile_ObsEnableFalseThrowsException() {
        // 设置obsEnable为false
        ReflectionTestUtils.setField(fileTransferUtils, "storageType", "LOCAL");

        // 验证调用uploadTaskFile方法时抛出AgentSpaceException
        AgentSpaceException exception = assertThrows(AgentSpaceException.class, () -> {
            fileTransferUtils.uploadTaskFile(AgentBuilderFile, AgentBuilderUploadScene.USER_UPLOAD);
        });

        // 验证异常消息
        assertEquals("storage is disabled, failed to upload file!", exception.getMessage());
        verify(obsApiClient, times(0)).uploadFile(anyString(), anyString(), any(FileTransferUtils.AgentBuilderFile.class));
    }
}