/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.agentbase.service.knowledgerepo;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.agentbase.entity.KnowledgeBaseEntity;
import com.openjiuwen.studio.agent.agentbase.entity.KnowledgeFileEntity;
import com.openjiuwen.studio.agent.agentbase.mapper.KnowledgeBaseMapper;
import com.openjiuwen.studio.agent.agentbase.mapper.KnowledgeFileMapper;
import com.openjiuwen.studio.agent.agentbase.model.KnowledgeRepo;
import com.openjiuwen.studio.agent.agentbase.service.KbConnectionStorageService;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.foundation.base.exception.AgentBaseException;
import com.openjiuwen.studio.agent.manager.dto.CreateKnowledgeTaskResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ListFileReq;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeFilesResponseBody;
import com.openjiuwen.studio.agent.manager.dto.openjiuwen.OpenJiuwenUploadResp;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.http.ResponseEntity;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.web.multipart.MultipartFile;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Executor;

/**
 * OpenJiuwenKBService 单元测试
 * 覆盖 upload/download/delete/retry/listFiles 核心业务逻辑
 */
@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
class OpenJiuwenKBServiceTest {

    @Mock
    private AgentRuntimeClient agentRuntimeClient;
    @Mock
    private KnowledgeBaseMapper knowledgeBaseMapper;
    @Mock
    private KnowledgeFileMapper knowledgeFileMapper;
    @Mock
    private KbConnectionStorageService kbConnectionStorageService;
    @Mock
    private MgObsService mgObsService;

    private OpenJiuwenKBService service;

    @BeforeEach
    void setUp() {
        // 同步执行器：asyncUploadToOpenJiuwen 在当前线程立即执行，便于断言
        Executor syncExecutor = Runnable::run;
        service = new OpenJiuwenKBService(
            agentRuntimeClient, knowledgeBaseMapper, knowledgeFileMapper,
            kbConnectionStorageService, mgObsService, syncExecutor);
    }

    private KnowledgeRepo buildRepo(String kbId) {
        KnowledgeRepo repo = new KnowledgeRepo();
        repo.setKnowledgeRepoId(kbId);
        return repo;
    }

    private MultipartFile buildMultipartFile(String name, String content) {
        return new MockMultipartFile(name, name, "application/octet-stream",
            content.getBytes(StandardCharsets.UTF_8));
    }

    // ==================== uploadFile ====================

    @Test
    void uploadFile_savesToObsAndDb_thenAsyncUploads() {
        try (var mocked = mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn("proj-1");
            mocked.when(RequestContextUtils::getCustomerHeaders).thenReturn(Collections.emptyMap());

            KnowledgeBaseEntity kbEntity = new KnowledgeBaseEntity();
            kbEntity.setEmbeddingModelServiceId("ms-001");
            kbEntity.setWorkspaceId("ws-001");
            when(knowledgeBaseMapper.selectById(null, "kb-1")).thenReturn(kbEntity);

            when(mgObsService.uploadObsFile(anyString(), any(InputStream.class), anyInt()))
                .thenReturn("kb-connection/ir/files/kb-1/file-1");

            InputStream obsStream = new ByteArrayInputStream("content".getBytes(StandardCharsets.UTF_8));
            when(mgObsService.readObsFileStream(anyString())).thenReturn(obsStream);

            OpenJiuwenUploadResp uploadResp = new OpenJiuwenUploadResp();
            uploadResp.setDocIds(List.of("doc-1", "doc-2"));
            when(agentRuntimeClient.uploadOpenJiuwenKBFile(anyString(), any(MultipartFile.class), anyString()))
                .thenReturn(ResponseEntity.ok(uploadResp));

            MultipartFile file = buildMultipartFile("test.pdf", "test content");
            String fileId = service.uploadFile(buildRepo("kb-1"), file, List.of("tag1"));

            assertNotNull(fileId);
            verify(mgObsService).uploadObsFile(anyString(), any(InputStream.class), anyInt());
            verify(knowledgeFileMapper).insertFile(any(KnowledgeFileEntity.class));
            // asyncUploadToOpenJiuwen 同步执行后应更新为 SUCCESS
            verify(knowledgeFileMapper).updateFileStatus(eq(fileId), eq("SUCCESS"), anyString(), any(Long.class));
        }
    }

    @Test
    void uploadFile_obsFailure_stillInsertsDbWithNullObsPath() {
        try (var mocked = mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn("proj-1");
            mocked.when(RequestContextUtils::getCustomerHeaders).thenReturn(Collections.emptyMap());

            doThrow(new RuntimeException("obs down"))
                .when(mgObsService).uploadObsFile(anyString(), any(InputStream.class), anyInt());

            KnowledgeBaseEntity kbEntity = new KnowledgeBaseEntity();
            kbEntity.setEmbeddingModelServiceId("ms-001");
            when(knowledgeBaseMapper.selectById(null, "kb-1")).thenReturn(kbEntity);

            MultipartFile file = buildMultipartFile("test.pdf", "test content");
            String fileId = service.uploadFile(buildRepo("kb-1"), file, null);

            assertNotNull(fileId);
            verify(knowledgeFileMapper).insertFile(any(KnowledgeFileEntity.class));
            // OBS 失败后 asyncUploadToOpenJiuwen 应标记 ERROR（obsPath 为 null）
            verify(knowledgeFileMapper).updateFileStatus(eq(fileId), eq("ERROR"), eq(null), any(Long.class));
        }
    }

    @Test
    void uploadFile_asyncUploadNullBody_marksError() {
        try (var mocked = mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn("proj-1");
            mocked.when(RequestContextUtils::getCustomerHeaders).thenReturn(Collections.emptyMap());

            KnowledgeBaseEntity kbEntity = new KnowledgeBaseEntity();
            kbEntity.setEmbeddingModelServiceId("ms-001");
            when(knowledgeBaseMapper.selectById(null, "kb-1")).thenReturn(kbEntity);

            when(mgObsService.uploadObsFile(anyString(), any(InputStream.class), anyInt()))
                .thenReturn("path");
            InputStream obsStream = new ByteArrayInputStream("content".getBytes(StandardCharsets.UTF_8));
            when(mgObsService.readObsFileStream(anyString())).thenReturn(obsStream);

            when(agentRuntimeClient.uploadOpenJiuwenKBFile(anyString(), any(MultipartFile.class), anyString()))
                .thenReturn(new ResponseEntity<>(null, org.springframework.http.HttpStatus.OK));

            MultipartFile file = buildMultipartFile("test.pdf", "test content");
            String fileId = service.uploadFile(buildRepo("kb-1"), file, null);

            verify(knowledgeFileMapper).updateFileStatus(eq(fileId), eq("ERROR"), eq(null), any(Long.class));
        }
    }

    // ==================== downloadFile ====================

    @Test
    void downloadFile_returnsBytesFromObs() {
        KnowledgeFileEntity entity = KnowledgeFileEntity.builder()
            .fileId("f-1").kbId("kb-1").fileName("doc.pdf")
            .obsPath("kb-connection/ir/files/kb-1/f-1").build();
        when(knowledgeFileMapper.selectByFileId("f-1")).thenReturn(entity);

        byte[] content = "download me".getBytes(StandardCharsets.UTF_8);
        when(mgObsService.readObsFileStream(anyString()))
            .thenReturn(new ByteArrayInputStream(content));

        ResponseEntity<byte[]> resp = service.downloadFile(buildRepo("kb-1"), "f-1");

        assertEquals(200, resp.getStatusCodeValue());
        assertArrayEquals(content, resp.getBody());
        assertEquals("attachment; filename=\"doc.pdf\"",
            resp.getHeaders().getFirst("Content-Disposition"));
    }

    @Test
    void downloadFile_notFound_throwsException() {
        when(knowledgeFileMapper.selectByFileId("missing")).thenReturn(null);
        assertThrows(AgentBaseException.class,
            () -> service.downloadFile(buildRepo("kb-1"), "missing"));
    }

    @Test
    void downloadFile_nullObsPath_throwsException() {
        KnowledgeFileEntity entity = KnowledgeFileEntity.builder()
            .fileId("f-1").obsPath(null).build();
        when(knowledgeFileMapper.selectByFileId("f-1")).thenReturn(entity);
        assertThrows(AgentBaseException.class,
            () -> service.downloadFile(buildRepo("kb-1"), "f-1"));
    }

    // ==================== deleteFile ====================

    @Test
    void deleteFile_deletesAgentRuntimeObsAndDb() {
        KnowledgeFileEntity entity = KnowledgeFileEntity.builder()
            .fileId("f-1").kbId("kb-1")
            .docIds("[\"doc-1\"]").obsPath("kb-connection/ir/files/kb-1/f-1").build();
        when(knowledgeFileMapper.selectByFileId("f-1")).thenReturn(entity);
        when(agentRuntimeClient.deleteOpenJiuwenKBDocument(anyString(), anyString(), any()))
            .thenReturn(new ResponseEntity<>(org.springframework.http.HttpStatus.OK));
        doNothing().when(mgObsService).deleteObsFile(anyString());

        service.deleteFile(buildRepo("kb-1"), "f-1");

        verify(agentRuntimeClient).deleteOpenJiuwenKBDocument(eq("kb-1"), eq("f-1"), any());
        verify(mgObsService).deleteObsFile("kb-connection/ir/files/kb-1/f-1");
        verify(knowledgeFileMapper).deleteByFileId("f-1");
    }

    @Test
    void deleteFile_notInDb_skipsSilently() {
        when(knowledgeFileMapper.selectByFileId("missing")).thenReturn(null);
        service.deleteFile(buildRepo("kb-1"), "missing");
        verify(knowledgeFileMapper, never()).deleteByFileId(anyString());
        verify(mgObsService, never()).deleteObsFile(anyString());
    }

    @Test
    void deleteFile_obsDeleteFailure_stillDeletesDb() {
        KnowledgeFileEntity entity = KnowledgeFileEntity.builder()
            .fileId("f-1").kbId("kb-1").obsPath("path").docIds(null).build();
        when(knowledgeFileMapper.selectByFileId("f-1")).thenReturn(entity);
        doThrow(new RuntimeException("obs down")).when(mgObsService).deleteObsFile(anyString());

        service.deleteFile(buildRepo("kb-1"), "f-1");

        verify(knowledgeFileMapper).deleteByFileId("f-1");
    }

    // ==================== deleteKnowledgeRepo ====================

    @Test
    void deleteKnowledgeRepo_deletesKbObsFilesAndDb() {
        when(agentRuntimeClient.deleteOpenJiuwenKB(any()))
            .thenReturn(new ResponseEntity<>(org.springframework.http.HttpStatus.OK));
        when(mgObsService.deleteByPrefix(anyString())).thenReturn(true);

        service.deleteKnowledgeRepo(buildRepo("kb-1"));

        verify(agentRuntimeClient).deleteOpenJiuwenKB(any());
        verify(mgObsService).deleteByPrefix("kb-connection/ir/files/kb-1/");
        verify(knowledgeFileMapper).deleteByKbId("kb-1");
    }

    @Test
    void deleteKnowledgeRepo_obsDeleteFailure_stillDeletesDb() {
        when(agentRuntimeClient.deleteOpenJiuwenKB(any()))
            .thenReturn(new ResponseEntity<>(org.springframework.http.HttpStatus.OK));
        doThrow(new RuntimeException("obs down")).when(mgObsService).deleteByPrefix(anyString());

        service.deleteKnowledgeRepo(buildRepo("kb-1"));

        verify(knowledgeFileMapper).deleteByKbId("kb-1");
    }

    // ==================== createTask (RETRY_FILES) ====================

    @Test
    void createTask_retryErrorFile_reuploadsAndUpdatesStatus() {
        KnowledgeFileEntity file = KnowledgeFileEntity.builder()
            .fileId("f-1").kbId("kb-1").fileName("doc.pdf")
            .fileStatus("ERROR").obsPath("path").docIds("[\"old-doc\"]").build();
        when(knowledgeFileMapper.selectByFileId("f-1")).thenReturn(file);

        KnowledgeBaseEntity kbEntity = new KnowledgeBaseEntity();
        kbEntity.setEmbeddingModelServiceId("ms-001");
        when(knowledgeBaseMapper.selectById(null, "kb-1")).thenReturn(kbEntity);

        InputStream obsStream = new ByteArrayInputStream("content".getBytes(StandardCharsets.UTF_8));
        when(mgObsService.readObsFileStream(anyString())).thenReturn(obsStream);

        OpenJiuwenUploadResp uploadResp = new OpenJiuwenUploadResp();
        uploadResp.setDocIds(List.of("new-doc-1"));
        when(agentRuntimeClient.uploadOpenJiuwenKBFile(anyString(), any(MultipartFile.class), anyString()))
            .thenReturn(ResponseEntity.ok(uploadResp));

        CreateKnowledgeTaskResponseBody resp =
            service.createTask("kb-1", "RETRY_FILES", List.of("f-1"));

        assertEquals(1, resp.getCreatedCount());
        assertEquals(1, resp.getTotalCount());
        verify(knowledgeFileMapper).updateFileStatus(eq("f-1"), eq("SUCCESS"), anyString(), any(Long.class));
        verify(agentRuntimeClient).deleteOpenJiuwenKBDocument(eq("kb-1"), eq("old-doc"), any());
    }

    @Test
    void createTask_retrySuccessFile_skipsAndCounts() {
        KnowledgeFileEntity file = KnowledgeFileEntity.builder()
            .fileId("f-1").fileStatus("SUCCESS").obsPath("path").build();
        when(knowledgeFileMapper.selectByFileId("f-1")).thenReturn(file);

        CreateKnowledgeTaskResponseBody resp =
            service.createTask("kb-1", "RETRY_FILES", List.of("f-1"));

        assertEquals(1, resp.getCreatedCount());
        verify(agentRuntimeClient, never())
            .uploadOpenJiuwenKBFile(anyString(), any(MultipartFile.class), anyString());
    }

    @Test
    void createTask_nullBody_skipsFile() {
        KnowledgeFileEntity file = KnowledgeFileEntity.builder()
            .fileId("f-1").kbId("kb-1").fileName("doc.pdf")
            .fileStatus("ERROR").obsPath("path").docIds(null).build();
        when(knowledgeFileMapper.selectByFileId("f-1")).thenReturn(file);

        KnowledgeBaseEntity kbEntity = new KnowledgeBaseEntity();
        kbEntity.setEmbeddingModelServiceId("ms-001");
        when(knowledgeBaseMapper.selectById(null, "kb-1")).thenReturn(kbEntity);

        InputStream obsStream = new ByteArrayInputStream("content".getBytes(StandardCharsets.UTF_8));
        when(mgObsService.readObsFileStream(anyString())).thenReturn(obsStream);

        when(agentRuntimeClient.uploadOpenJiuwenKBFile(anyString(), any(MultipartFile.class), anyString()))
            .thenReturn(new ResponseEntity<>(null, org.springframework.http.HttpStatus.OK));

        CreateKnowledgeTaskResponseBody resp =
            service.createTask("kb-1", "RETRY_FILES", List.of("f-1"));

        assertEquals(0, resp.getCreatedCount());
        verify(knowledgeFileMapper, never())
            .updateFileStatus(eq("f-1"), eq("SUCCESS"), anyString(), any(Long.class));
    }

    @Test
    void createTask_unsupportedType_throws() {
        assertThrows(AgentBaseException.class,
            () -> service.createTask("kb-1", "UNKNOWN", List.of("f-1")));
    }

    // ==================== listFiles ====================

    @Test
    void listFiles_returnsPaginatedResults() {
        try (var mocked = mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn("proj-1");

            KnowledgeFileEntity entity = KnowledgeFileEntity.builder()
                .fileId("f-1").kbId("kb-1").projectId("proj-1")
                .fileName("doc.pdf").fileType("pdf").fileSize(100L)
                .fileStatus("SUCCESS").fileTags("[\"tag1\"]")
                .createTime(1000L).updateTime(2000L).build();
            when(knowledgeFileMapper.selectByKbId(eq("kb-1"), eq("proj-1"),
                any(), any(), any(), anyInt(), anyInt()))
                .thenReturn(List.of(entity));
            when(knowledgeFileMapper.countByKbId(eq("kb-1"), eq("proj-1"),
                any(), any(), any()))
                .thenReturn(1);

            ListFileReq req = new ListFileReq().setPageNum(1).setPageSize(10);
            ListKnowledgeFilesResponseBody resp = service.listFiles(buildRepo("kb-1"), req);

            assertEquals(1, resp.getCount());
            assertEquals(1, resp.getFileInfoList().size());
            assertEquals("f-1", resp.getFileInfoList().get(0).getFileId());
            assertEquals("doc.pdf", resp.getFileInfoList().get(0).getFileName());
            assertEquals("SUCCESS", resp.getFileInfoList().get(0).getFileStatus());
        }
    }

    @Test
    void listFiles_emptyResults_returnsZero() {
        try (var mocked = mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn("proj-1");
            when(knowledgeFileMapper.selectByKbId(anyString(), anyString(),
                any(), any(), any(), anyInt(), anyInt()))
                .thenReturn(Collections.emptyList());
            when(knowledgeFileMapper.countByKbId(anyString(), anyString(),
                any(), any(), any()))
                .thenReturn(0);

            ListFileReq req = new ListFileReq();
            ListKnowledgeFilesResponseBody resp = service.listFiles(buildRepo("kb-1"), req);

            assertEquals(0, resp.getCount());
            assertEquals(0, resp.getFileInfoList().size());
        }
    }
}
