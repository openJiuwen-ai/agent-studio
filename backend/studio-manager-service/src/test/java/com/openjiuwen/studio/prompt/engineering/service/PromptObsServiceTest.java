/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.storage.FileMeta;
import com.openjiuwen.studio.agent.common.storage.FileStore;
import com.openjiuwen.studio.prompt.engineering.dto.GetObsObjectReq;
import com.openjiuwen.studio.prompt.engineering.dto.ObsObjectResp;
import com.openjiuwen.studio.prompt.engineering.enums.FileType;
import com.openjiuwen.studio.prompt.engineering.utils.FileUtil;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.util.ReflectionTestUtils;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.List;

@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
class PromptObsServiceTest {

    @Mock
    private FileStore fileStore;

    @InjectMocks
    private PromptObsService obsService;

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(obsService, "bucket", "test-bucket");
    }

    @Test
    void upLoadImage() throws IOException {
        when(fileStore.getUrl(anyString(), anyLong())).thenReturn("https://example.com/signed");

        MockMultipartFile file = new MockMultipartFile("file",
                "test.jpg",
                "image/jpeg",
                "test".getBytes(StandardCharsets.UTF_8)
        );
        try (var mockedFileUtil = mockStatic(FileUtil.class)) {
            mockedFileUtil.when(() -> FileUtil.validateFile(any(), any(FileType.class)))
                .thenAnswer(invocation -> null);
            var result = obsService.upLoadImage("mock", "mock", file);
            assertNotNull(result);
        }
    }

    @Test
    void testGetObsTempUrl() {
        when(fileStore.getUrl(anyString(), anyLong())).thenReturn("https://example.com/signed");
        String url = obsService.getObsTempUrl("image/file-001", 3600L);
        assertEquals("https://example.com/signed", url);
    }

    @Test
    void testGetObsTempUrl_Exception_Throws() {
        when(fileStore.getUrl(anyString(), anyLong())).thenThrow(new RuntimeException("OBS error"));

        assertThrows(AgentStudioException.class,
            () -> obsService.getObsTempUrl("image/file-001", 3600L));
    }

    @Test
    void testUploadObsFile_Success() {
        InputStream inputStream = new ByteArrayInputStream("test content".getBytes(StandardCharsets.UTF_8));
        obsService.uploadObsFile(inputStream, "test/path.txt");
        verify(fileStore).write("test-bucket/test/path.txt", inputStream);
    }

    @Test
    void testDownloadObsFile_Success() {
        when(fileStore.read(anyString())).thenReturn("downloaded content");

        String result = obsService.downloadObsFile("path/file.txt");
        assertEquals("downloaded content", result);
    }

    @Test
    void testDownloadObsFile_Exception_Throws() {
        when(fileStore.read(anyString())).thenThrow(new RuntimeException("fail"));

        assertThrows(AgentStudioException.class,
            () -> obsService.downloadObsFile("nonexistent.txt"));
    }

    @Test
    void testDeleteObsFile() {
        when(fileStore.delete(anyString())).thenReturn(true);
        obsService.deleteObsFile("path/file.txt");
        verify(fileStore).delete("test-bucket/path/file.txt");
    }

    @Test
    void testIsExistObsFile_Exists() {
        when(fileStore.exists(anyString())).thenReturn(true);
        assertTrue(obsService.isExistObsFile("path/file.txt"));
    }

    @Test
    void testIsExistObsFile_NotExists() {
        when(fileStore.exists(anyString())).thenReturn(false);
        assertFalse(obsService.isExistObsFile("path/file.txt"));
    }

    @Test
    void testCopyFile_Success() {
        when(fileStore.copy(anyString(), anyString())).thenReturn(true);
        obsService.copyFile("old/path.txt", "new/path.txt");
        verify(fileStore).copy("test-bucket/old/path.txt", "test-bucket/new/path.txt");
    }

    @Test
    void testCopyFile_NullOldPath() {
        obsService.copyFile(null, "new/path.txt");
        verify(fileStore, never()).copy(anyString(), anyString());
    }

    @Test
    void testCopyFile_NullNewPath() {
        obsService.copyFile("old/path.txt", null);
        verify(fileStore, never()).copy(anyString(), anyString());
    }

    @Test
    void testCopyFile_EmptyPaths() {
        obsService.copyFile("", "");
        verify(fileStore, never()).copy(anyString(), anyString());
    }

    @Test
    void testListObjectKeys_Success() {
        when(fileStore.list(anyString())).thenReturn(List.of("dir/file1.txt", "dir/file2.txt"));

        List<String> keys = obsService.listObjectKeys("dir");
        assertEquals(2, keys.size());
        assertEquals("dir/file1.txt", keys.get(0));
    }

    @Test
    void testListObjectKeys_NullObjects() {
        when(fileStore.list(anyString())).thenReturn(Collections.emptyList());

        List<String> keys = obsService.listObjectKeys("dir");
        assertTrue(keys.isEmpty());
    }

    @Test
    void testListObsObjects() {
        FileMeta meta1 = new FileMeta("file1.txt", 100L, System.currentTimeMillis(), false);
        FileMeta meta2 = new FileMeta("subdir", 0L, System.currentTimeMillis(), true);
        when(fileStore.listMetas(anyString())).thenReturn(List.of(meta1, meta2));

        GetObsObjectReq req = new GetObsObjectReq();
        req.setBucket("test-bucket");
        req.setPath("dir");
        ObsObjectResp resp = obsService.listObsObjects("proj", "ws", req);
        assertNotNull(resp);
    }
}
