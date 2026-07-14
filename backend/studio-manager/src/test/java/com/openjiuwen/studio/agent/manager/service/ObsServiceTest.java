/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import static com.openjiuwen.studio.agent.manager.constant.Constants.TEST_PROJECT_ID;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

import com.alibaba.fastjson2.JSON;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.storage.FileStore;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.constant.Constants;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.utils.BaseTest;

import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.mockito.MockitoAnnotations;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.util.ReflectionTestUtils;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@MockitoSettings(strictness = Strictness.LENIENT)
class ObsServiceTest extends BaseTest {
    private static MockedStatic<RequestContextUtils> mockedStatic;

    @Mock
    private FileStore fileStore;

    private MgObsService obsService;

    private AutoCloseable mockitoCloseable;

    @BeforeAll
    static void init() {
        mockedStatic = Mockito.mockStatic(RequestContextUtils.class);
        mockedStatic.when(RequestContextUtils::getRequestProjectId).thenReturn(TEST_PROJECT_ID);
        mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn(Constants.TEST_TOKEN);
    }

    @AfterAll
    static void end() {
        mockedStatic.close();
    }

    @BeforeEach
    void setUp() {
        mockitoCloseable = MockitoAnnotations.openMocks(this);
        when(fileStore.getDefaultNamespace()).thenReturn("workflow-ir");
        when(fileStore.getStagingNamespace()).thenReturn("staging-bucket");
        obsService = new MgObsService(fileStore);
    }

    @AfterEach
    void tearDown() throws Exception {
        mockitoCloseable.close();
    }

    @Test
    void testObsUploadFile() {
        String objectKey = Constants.TEST_DIR_NAME + "/" + Constants.TEST_WORKFLOW_ID + ".json";
        Map<String, Object> irInfo = new HashMap<>();
        irInfo.put("components", new ArrayList<>());
        when(fileStore.write(anyString(), any(), anyInt())).thenReturn(objectKey);
        String result = obsService.uploadObsFile(Constants.TEST_WORKFLOW_ID, Constants.TEST_WORKFLOW_ID,
            CommonConstant.WORKFLOW, JSON.toJSONString(irInfo), CommonConstant.Workflow.FLOW);
        assertNotNull(result);
    }

    @Test
    void testObsUploadFailed() {
        Map<String, Object> irInfo = new HashMap<>();
        irInfo.put("components", new ArrayList<>());
        when(fileStore.write(anyString(), any(), anyInt())).thenThrow(new RuntimeException("upload failed"));
        assertThrows(AgentStudioException.class, () -> {
            obsService.uploadObsFile(Constants.TEST_WORKFLOW_ID, Constants.TEST_WORKFLOW_ID,
                CommonConstant.WORKFLOW, JSON.toJSONString(irInfo), CommonConstant.Workflow.FLOW);
        });
    }

    @Test
    void testObsDownloadFile() {
        String objectKey = Constants.TEST_DIR_NAME + "/" + Constants.TEST_WORKFLOW_ID + ".json";
        when(fileStore.read(anyString())).thenThrow(new RuntimeException("download failed"));
        assertThrows(AgentStudioException.class, () -> obsService.downloadObsFile(objectKey));
    }

    @Test
    void testObsDeleteFile() {
        when(fileStore.delete(anyString())).thenReturn(true);
        obsService.deleteObsFile("testKey");
    }

    @Test
    void testObsDeleteObjects() {
        when(fileStore.deleteByPrefix(anyString())).thenReturn(true);
        obsService.deleteObsObjects("dirPath");
    }

    @Test
    void testUploadObsFileWithExpires() throws IOException {
        when(fileStore.write(anyString(), any(InputStream.class), anyInt())).thenReturn("path");
        MockMultipartFile file = new MockMultipartFile("file", "test.txt", "text/plain",
            "test".getBytes(StandardCharsets.UTF_8));
        String result = obsService.uploadObsFileWithExpires(file.getInputStream(), "name", 100);
        assertNotNull(result);
    }

    @Test
    void testDeleteByPrefix() {
        when(fileStore.deleteByPrefix(anyString())).thenReturn(true);
        boolean result = obsService.deleteByPrefix("mock_delete_obs_prefix");
        assertTrue(result);
    }
}
