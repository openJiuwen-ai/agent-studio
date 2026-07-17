/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.obs;

import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.storage.FileMeta;
import com.openjiuwen.studio.agent.common.storage.FileStore;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.test.util.ReflectionTestUtils;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
class MgObsServiceTest {

    @Mock
    private FileStore fileStore;

    @InjectMocks
    private MgObsService mgObsService;

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(mgObsService, "bucket", "test-bucket");
        ReflectionTestUtils.setField(mgObsService, "stagingBucket", "test-staging-bucket");
    }

    @Test
    void testGetAbsolutePath() {
        String result = mgObsService.getAbsolutePath("path/to/file");
        assertEquals("obs://test-bucket/path/to/file", result);
    }

    @Test
    void testIsExistedKey_True() {
        when(fileStore.exists(anyString())).thenReturn(true);
        assertTrue(mgObsService.isExistedKey("key"));
    }

    @Test
    void testIsExistedKey_False() {
        when(fileStore.exists(anyString())).thenReturn(false);
        assertFalse(mgObsService.isExistedKey("key"));
    }

    @Test
    void testDeleteObsFile_Success() {
        when(fileStore.delete(anyString())).thenReturn(true);
        mgObsService.deleteObsFile("key");
        verify(fileStore).delete("test-bucket/key");
    }

    @Test
    void testDeleteObsFile_Exception() {
        doThrow(new RuntimeException("fail")).when(fileStore).delete(anyString());
        assertThrows(RuntimeException.class, () -> mgObsService.deleteObsFile("key"));
    }

    @Test
    void testSoftDeleteObsFile_Exists() {
        when(fileStore.exists(anyString())).thenReturn(true);
        when(fileStore.copy(anyString(), anyString())).thenReturn(true);
        when(fileStore.delete(anyString())).thenReturn(true);
        mgObsService.softDeleteObsFile("key");
        verify(fileStore).copy("test-bucket/key", "test-bucket/key.deleted");
        verify(fileStore).delete("test-bucket/key");
    }

    @Test
    void testSoftDeleteObsFile_NotExists() {
        when(fileStore.exists(anyString())).thenReturn(false);
        mgObsService.softDeleteObsFile("key");
        verify(fileStore, never()).copy(anyString(), anyString());
        verify(fileStore, never()).delete(anyString());
    }

    @Test
    void testSoftDeleteObsFile_Exception() {
        when(fileStore.exists(anyString())).thenThrow(new RuntimeException("fail"));
        assertThrows(AgentStudioException.class, () -> mgObsService.softDeleteObsFile("key"));
    }

    @Test
    void testCopyObsObject_Success() {
        when(fileStore.copy(anyString(), anyString())).thenReturn(true);
        mgObsService.copyObsObject("source", "target");
        verify(fileStore).copy("test-bucket/source", "test-bucket/target");
    }

    @Test
    void testCopyObsObject_Exception() {
        doThrow(new RuntimeException("fail")).when(fileStore).copy(anyString(), anyString());
        assertThrows(RuntimeException.class, () -> mgObsService.copyObsObject("source", "target"));
    }

    @Test
    void testGetObjectMetadata_Exists() {
        FileMeta meta = new FileMeta("key", 100L, System.currentTimeMillis(), false);
        when(fileStore.getMeta(anyString())).thenReturn(meta);
        var result = mgObsService.getObjectMetadata("key");
        assertNotNull(result);
        assertEquals(100L, result.getSize());
    }

    @Test
    void testGetObjectMetadata_NotObsType() {
        var result = mgObsService.getObjectMetadata("key");
        assertNotNull(result);
    }

    @Test
    void testGetTemporaryGetRsp_Success() {
        when(fileStore.getUrl(anyString(), anyLong())).thenReturn("https://example.com/signed");
        String result = mgObsService.getTemporaryGetRsp(false, "object", 3600);
        assertEquals("https://example.com/signed", result);
    }

    @Test
    void testUploadObsFile_StringContent_Success() {
        when(fileStore.write(anyString(), anyString())).thenReturn("test-bucket/key");
        String result = mgObsService.uploadObsFile("key", "content", -1);
        assertEquals("key", result);
    }

    @Test
    void testUploadObsFile_Stream_Success() {
        when(fileStore.write(anyString(), any(InputStream.class), anyInt())).thenReturn("test-bucket/key");
        InputStream stream = new ByteArrayInputStream("content".getBytes(StandardCharsets.UTF_8));
        String result = mgObsService.uploadObsFile("key", stream, -1);
        assertEquals("key", result);
    }

    @Test
    void testUploadObsFile_Stream_WithExpires() {
        when(fileStore.write(anyString(), any(InputStream.class), anyInt())).thenReturn("test-bucket/key");
        InputStream stream = new ByteArrayInputStream("content".getBytes(StandardCharsets.UTF_8));
        String result = mgObsService.uploadObsFile("key", stream, 7);
        assertEquals("key", result);
    }

    @Test
    void testUploadStagingBucket_Success() {
        when(fileStore.write(anyString(), any(InputStream.class), anyInt())).thenReturn("test-staging-bucket/key");
        String result = mgObsService.uploadStagingBucket("key", "content", -1);
        assertEquals("key", result);
    }

    @Test
    void testUploadStreamStagingBucket_Success() {
        when(fileStore.write(anyString(), any(InputStream.class), anyInt())).thenReturn("test-staging-bucket/key");
        InputStream stream = new ByteArrayInputStream("content".getBytes(StandardCharsets.UTF_8));
        String result = mgObsService.uploadStreamStagingBucket("key", stream, -1);
        assertEquals("key", result);
    }

    @Test
    void testUploadObsFile_5Param_Success() {
        when(fileStore.write(anyString(), anyString())).thenReturn("test-bucket/type/prefix/pathKey/objectKey.json");
        String result = mgObsService.uploadObsFile("pathKey", "objectKey", "type", "fileInfo", "prefix");
        assertEquals("type/prefix/pathKey/objectKey.json", result);
    }

    @Test
    void testUploadObsFileWithExpires_Success() {
        when(fileStore.write(anyString(), any(InputStream.class), anyInt())).thenReturn("test-bucket/file/file.json");
        InputStream stream = new ByteArrayInputStream("content".getBytes(StandardCharsets.UTF_8));
        String result = mgObsService.uploadObsFileWithExpires(stream, "file.json", 7);
        assertEquals("file/file.json", result);
    }

    @Test
    void testDownloadObsFile_Success() {
        when(fileStore.read(anyString())).thenReturn("test content");
        String result = mgObsService.downloadObsFile("key");
        assertEquals("test content", result);
    }

    @Test
    void testDownloadObsFile_Exception() {
        when(fileStore.read(anyString())).thenThrow(new RuntimeException("fail"));
        assertThrows(RuntimeException.class, () -> mgObsService.downloadObsFile("key"));
    }

    @Test
    void testDeleteObsObjects_Success() {
        when(fileStore.deleteByPrefix(anyString())).thenReturn(true);
        mgObsService.deleteObsObjects("dir");
        verify(fileStore).deleteByPrefix("test-bucket/dir");
    }

    @Test
    void testDeleteObsObjects_Exception() {
        doThrow(new RuntimeException("fail")).when(fileStore).deleteByPrefix(anyString());
        assertThrows(RuntimeException.class, () -> mgObsService.deleteObsObjects("dir"));
    }

    @Test
    void testCleanObsObjects_NoObjects() {
        when(fileStore.listMetas(anyString())).thenReturn(Collections.emptyList());
        mgObsService.cleanObsObjects();
        verify(fileStore, never()).delete(anyString());
    }

    @Test
    void testCleanObsObjects_WithOldFiles() {
        FileMeta oldFile = new FileMeta("file/old-file.json", 100L,
            System.currentTimeMillis() - 8L * 24 * 60 * 60 * 1000, false);
        when(fileStore.listMetas(anyString())).thenReturn(List.of(oldFile));
        when(fileStore.delete(anyString())).thenReturn(true);
        mgObsService.cleanObsObjects();
        verify(fileStore).delete("test-bucket/file/old-file.json");
    }

    @Test
    void testCleanObsObjects_WithRecentFiles() {
        FileMeta recentFile = new FileMeta("file/recent-file.json", 100L,
            System.currentTimeMillis() - 1L * 24 * 60 * 60 * 1000, false);
        when(fileStore.listMetas(anyString())).thenReturn(List.of(recentFile));
        mgObsService.cleanObsObjects();
        verify(fileStore, never()).delete(anyString());
    }

    @Test
    void testCleanObsObjects_Exception() {
        when(fileStore.listMetas(anyString())).thenThrow(new RuntimeException("fail"));
        assertThrows(AgentStudioException.class, () -> mgObsService.cleanObsObjects());
    }

    @Test
    void testPutObject_Success() {
        when(fileStore.write(anyString(), any(InputStream.class), anyInt())).thenReturn("test-bucket/key");
        mgObsService.putObject("key", "content");
        verify(fileStore).write(eq("test-bucket/key"), any(InputStream.class), eq(-1));
    }

    @Test
    void testDeleteObject_Success() {
        when(fileStore.delete(anyString())).thenReturn(true);
        mgObsService.deleteObject("key");
        verify(fileStore).delete("test-bucket/key");
    }

    @Test
    void testGetObject_Success() {
        when(fileStore.read(anyString())).thenReturn("content");
        String result = mgObsService.getObject("key");
        assertEquals("content", result);
    }

    @Test
    void testDeleteByPrefix_NoObjects() {
        when(fileStore.deleteByPrefix(anyString())).thenReturn(true);
        var result = mgObsService.deleteByPrefix("prefix");
        assertNotNull(result);
    }
}
