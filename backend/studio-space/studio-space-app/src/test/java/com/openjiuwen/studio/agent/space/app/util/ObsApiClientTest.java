package com.openjiuwen.studio.agent.space.app.util;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
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
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.storage.FileStore;
import com.openjiuwen.studio.agent.space.common.exception.AgentSpaceException;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;

import java.io.ByteArrayInputStream;
import java.io.InputStream;

@MockitoSettings(strictness = Strictness.LENIENT)
class ObsApiClientTest {

    private FileStore fileStore;
    private ObsApiClient obsApiClient;

    @BeforeEach
    void setUp() {
        fileStore = mock(FileStore.class);
        obsApiClient = new ObsApiClient(fileStore);
    }

    @Test
    void test_downloadFile_success() {
        InputStream stream = new ByteArrayInputStream("test".getBytes());
        when(fileStore.readStream(anyString())).thenReturn(stream);

        InputStream result = obsApiClient.downloadFile("bucket", "key");

        assertNotNull(result);
    }

    @Test
    void test_downloadFile_throw_AgentSpaceException_on_failure() {
        when(fileStore.readStream(anyString())).thenThrow(new RuntimeException("fail"));

        assertThrows(AgentSpaceException.class, () -> obsApiClient.downloadFile("bucket", "key"));
    }

    @Test
    void test_uploadFile_success() {
        FileTransferUtils.AgentBuilderFile file = mock(FileTransferUtils.AgentBuilderFile.class);
        when(file.getOriginalFilename()).thenReturn("test.txt");
        when(file.getInputStream()).thenReturn(new ByteArrayInputStream("test".getBytes()));

        String result = obsApiClient.uploadFile("bucket", "dir/", file);

        assertNotNull(result);
        assertTrue(result.contains("test.txt"));
    }

    @Test
    void test_uploadFile_throw_AgentSpaceException_on_failure() {
        doThrow(new RuntimeException("fail")).when(fileStore).write(anyString(), any(InputStream.class));

        FileTransferUtils.AgentBuilderFile file = mock(FileTransferUtils.AgentBuilderFile.class);
        when(file.getOriginalFilename()).thenReturn("test.txt");
        when(file.getInputStream()).thenReturn(new ByteArrayInputStream("test".getBytes()));

        assertThrows(AgentSpaceException.class, () -> obsApiClient.uploadFile("bucket", "dir/", file));
    }

    @Test
    void test_getTemporaryGetRsp_success() {
        when(fileStore.getUrl(anyString(), anyLong())).thenReturn("https://example.com/signed");

        String result = obsApiClient.getTemporaryGetRsp("bucket", "key", 3600L);

        assertEquals("https://example.com/signed", result);
    }

    @Test
    void test_getTemporaryGetRsp_throw_AgentSpaceException_on_failure() {
        when(fileStore.getUrl(anyString(), anyLong())).thenThrow(new RuntimeException("fail"));

        assertThrows(AgentSpaceException.class, () -> obsApiClient.getTemporaryGetRsp("bucket", "key", 3600L));
    }

    @Test
    void test_safeCopyObsObject_return_true_on_success() {
        when(fileStore.copy(anyString(), anyString())).thenReturn(true);

        assertTrue(obsApiClient.safeCopyObsObject("src", "key", "dest", "key2"));
    }

    @Test
    void test_safeCopyObsObject_return_false_on_failure() {
        doThrow(new RuntimeException("fail")).when(fileStore).copy(anyString(), anyString());

        assertFalse(obsApiClient.safeCopyObsObject("src", "key", "dest", "key2"));
    }

    @Test
    void test_copyObsObject_success() {
        when(fileStore.copy(anyString(), anyString())).thenReturn(true);

        assertDoesNotThrow(() -> obsApiClient.copyObsObject("src", "key", "dest", "key2"));
    }

    @Test
    void test_copyObsObject_throw_AgentSpaceException_on_failure() {
        doThrow(new RuntimeException("fail")).when(fileStore).copy(anyString(), anyString());

        assertThrows(AgentSpaceException.class, () -> obsApiClient.copyObsObject("src", "key", "dest", "key2"));
    }

    @Test
    void test_safeDeleteObsObject_return_true_for_empty_params() {
        assertTrue(obsApiClient.safeDeleteObsObject("", ""));
    }

    @Test
    void test_safeDeleteObsObject_return_true_on_success() {
        when(fileStore.delete(anyString())).thenReturn(true);

        assertTrue(obsApiClient.safeDeleteObsObject("bucket", "key"));
    }

    @Test
    void test_safeDeleteObsObject_return_false_on_failure() {
        doThrow(new RuntimeException("fail")).when(fileStore).delete(anyString());

        assertFalse(obsApiClient.safeDeleteObsObject("bucket", "key"));
    }

    @Test
    void test_deleteObsObject_return_true_on_success() {
        when(fileStore.delete(anyString())).thenReturn(true);

        assertTrue(obsApiClient.deleteObsObject("bucket", "key"));
    }

    @Test
    void test_deleteObsObject_throw_AgentSpaceException_for_empty_params() {
        assertThrows(AgentSpaceException.class, () -> obsApiClient.deleteObsObject("", ""));
    }

    @Test
    void test_deleteObsObject_throw_AgentSpaceException_on_failure() {
        doThrow(new RuntimeException("fail")).when(fileStore).delete(anyString());

        assertThrows(AgentSpaceException.class, () -> obsApiClient.deleteObsObject("bucket", "key"));
    }
}
