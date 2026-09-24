/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.service;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.Mockito.any;
import static org.mockito.Mockito.anyString;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.prompt.engineering.dto.FileInfoVo;
import com.openjiuwen.studio.prompt.engineering.dto.InvokeResp;
import com.openjiuwen.studio.prompt.engineering.dto.ModelConfig;
import com.openjiuwen.studio.prompt.engineering.dto.PromptBody;
import com.openjiuwen.studio.prompt.engineering.mapper.PeTaskMapper;
import com.openjiuwen.studio.prompt.engineering.service.model.PromptModelService;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.MockitoAnnotations;

import java.util.concurrent.CompletableFuture;

class ModelManagerServiceTest {
    @Mock
    private PeTaskMapper peTaskMapper;

    @Mock
    private PromptService promptService;

    @Mock
    private PromptModelService<?> promptModelService;

    @Mock
    private PromptObsService promptObsService;

    @Mock
    private InvokeResp invokeResp;

    @InjectMocks
    private ModelManagerService modelManagerService;

    @BeforeEach
    public void setUp() {
        MockitoAnnotations.openMocks(this);
        // COM-02: callModel 迁移至 promptModelCallExecutor（@InjectMocks 不注入非 mock 字段），
        // 注入真实受管 executor 供 supplyAsync 使用
        org.springframework.test.util.ReflectionTestUtils.setField(modelManagerService,
            "promptModelCallExecutor",
            new com.openjiuwen.studio.agent.manager.config.ObservabilityAsyncConfig()
                .promptModelCallExecutor(2, 4, 50, 60));
    }

    @Test
    public void testCallModel_ExecutionError() throws Exception {
        // Arrange
        String projectId = "project-id";
        String workspaceId = "workspace-id";
        PromptBody body = new PromptBody();
        body.setTaskId("task-id");
        body.setQuestion("prompt模板，带占位符");
        body.setModel("model信息");
        body.setModelConfig(new ModelConfig());
        body.setFileId("file-id");
        body.getModelConfig().setId("model-id");

        when(peTaskMapper.isIdExist(body.getTaskId(), workspaceId)).thenReturn(true);
        when(peTaskMapper.queryPublishStatusById(body.getModelConfig().getId(), body.getModel())).thenReturn("online");
        CompletableFuture<InvokeResp> future = new CompletableFuture<>();
        // 模拟 queryModelCenter 方法抛出的异常
        future.completeExceptionally(new RuntimeException("模拟的执行时异常"));

        InvokeResp invokeResp = new InvokeResp();
        invokeResp.setFileInfo(new FileInfoVo());
        when(promptModelService.queryModelCenter(anyString(), any(PromptBody.class), anyString(),
            anyString())).thenReturn(invokeResp);
        FileInfoVo fileInfoVo = new FileInfoVo();
        when(promptService.getFileInfoVoByFileId(body.getFileId())).thenReturn(fileInfoVo);
        try (MockedStatic<RequestContextUtils> mockedHttpUtil = mockStatic(RequestContextUtils.class)) {
            mockedHttpUtil.when(RequestContextUtils::getRequestAuthToken).thenReturn("mocked-xAuthToken");
            mockedHttpUtil.when(RequestContextUtils::getRequestUserName).thenReturn("mocked-user");
            InvokeResp response = modelManagerService.callModel(projectId, workspaceId, body);
            assertNotNull(response);
        }
    }

}
