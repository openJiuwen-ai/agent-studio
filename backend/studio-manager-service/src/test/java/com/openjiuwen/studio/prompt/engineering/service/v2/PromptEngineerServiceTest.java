/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.service.v2;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.RETURNS_DEEP_STUBS;
import static org.mockito.Mockito.any;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.core.type.TypeReference;
import com.github.pagehelper.ISelect;
import com.github.pagehelper.PageInfo;
import com.github.pagehelper.page.PageMethod;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.prompt.engineering.dto.CreatePromptTaskRsp;
import com.openjiuwen.studio.prompt.engineering.dto.ExecConfig;
import com.openjiuwen.studio.prompt.engineering.dto.GetPromptTaskIterEvalResQo;
import com.openjiuwen.studio.prompt.engineering.dto.ListPromptTasksQo;
import com.openjiuwen.studio.prompt.engineering.dto.PromptBaseInfo;
import com.openjiuwen.studio.prompt.engineering.dto.PromptBaseResp;
import com.openjiuwen.studio.prompt.engineering.dto.PromptTaskCreateReq;
import com.openjiuwen.studio.prompt.engineering.entity.v2.PromptTaskDetailVo;
import com.openjiuwen.studio.prompt.engineering.entity.v2.PromptTaskEntity;
import com.openjiuwen.studio.prompt.engineering.entity.v2.PromptVar;
import com.openjiuwen.studio.prompt.engineering.enums.v2.PromptTaskStatusEnum;
import com.openjiuwen.studio.prompt.engineering.enums.v2.PtTypeEnum;
import com.openjiuwen.studio.prompt.engineering.mapper.v2.PromptTaskMapper;
import com.openjiuwen.studio.prompt.engineering.service.model.v2.jiuwen.JiuWenEvaluation;
import com.openjiuwen.studio.prompt.engineering.service.model.v2.jiuwen.JiuWenHistory;
import com.openjiuwen.studio.prompt.engineering.service.model.v2.jiuwen.JiuWenJobDeatails;
import com.openjiuwen.studio.prompt.engineering.service.model.v2.jiuwen.JiuWenProgress;
import com.openjiuwen.studio.prompt.engineering.service.model.v2.jiuwen.JiuWenPromptDeatilRes;

import org.apache.commons.beanutils.BeanUtils;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Answers;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.MockitoAnnotations;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.util.CollectionUtils;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.UUID;

@MockitoSettings(strictness = Strictness.LENIENT)
class PromptEngineerServiceTest {
    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private PromptTaskMapper promptTaskMapper;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private PromptOptimizeTaskService promptOptimizeTaskService;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private PromptEngineerDataSetService promptEngineerDataSetService;

    @InjectMocks
    private PromptEngineerService promptEngineerService;

    private AutoCloseable mockitoCloseable;

    private String reqBody = "{\n" + "    \"name\": \"信息提取小助手31\",\n" + "    \"desc\": \"test\",\n"
        + "    \"execTime\": \"1761550129176\",\n" + "    \"ptType\": \"text\",\n"
        + "    \"ptText\": \"详细接收以下内容的示例，以下是用户输入：{{product}}\",\n"
        + "    \"ptVars\": \"[{\\\"name\\\": \\\"product\\\", \\\"type\\\": \\\"text\\\"},{\\\"name\\\": \\\"AGENT_BUILDER_PROMPT_OUTPUT\\\", \\\"type\\\": \\\"text\\\"}]\",\n"
        + "    \"ptObject\": {\n" + "        \"model\": \"180\",\n" + "        \"exec_type\": \"model\",\n"
        + "        \"top_p\": 1,\n" + "        \"temperature\": 0,\n" + "        \"max_tokens\": 1000\n" + "    },\n"
        + "    \"assitantObject\": {\n" + "        \"model\": \"180\",\n" + "        \"exec_type\": \"model\",\n"
        + "        \"top_p\": 1,\n" + "        \"temperature\": 0,\n" + "        \"max_tokens\": 1000\n" + "    },\n"
        + "    \"maxIterNum\": 3,\n" + "    \"targetAcc\": \"90\",\n" + "    \"showCaseNum\": 3,\n"
        + "    \"targetType\": \"objective\",\n" + "    \"scoreStandard\": \"内容相关性:30分,语言流畅度:20分,创新性:50分\",\n"
        + "    \"backKnowledge\": \"\"\n" + "}";

    @BeforeEach
    void setUp() throws Exception {
        mockitoCloseable = MockitoAnnotations.openMocks(this);
        ReflectionTestUtils.setField(promptEngineerService, "VARS_NUM", 20);
        ReflectionTestUtils.setField(promptEngineerService, "VARS_NAME_LENGTH", 50);
        ReflectionTestUtils.setField(promptEngineerService, "VARS_CONTENT_LENGTH", 1000);
        ReflectionTestUtils.setField(promptEngineerService, "isSoftDelete", false);
    }

    @AfterEach
    void tearDown() throws Exception {
        mockitoCloseable.close();
    }

    @Test
    public void test_createPromptTaskDraft_success() throws Exception {

        try (MockedStatic<RequestContextUtils> mockedStatic = mockStatic(RequestContextUtils.class)) {
            // Given
            String projectId = "proj123";
            String workspaceId = "ws123";
            PromptTaskCreateReq body = JsonUtils.json2ObjQuietly(reqBody, PromptTaskCreateReq.class);
            doNothing().when(promptTaskMapper).insert(any(PromptTaskEntity.class));
            mockedStatic.when(RequestContextUtils::getRequestUserName).thenReturn("not_empty");
            mockedStatic.when(RequestContextUtils::getRequestUserId).thenReturn("not_empty");
            when(promptTaskMapper.queryProjectIdByModelId("180")).thenReturn(projectId);
            when(promptTaskMapper.queryPublishStatusByModelId("180")).thenReturn("online");            // When
            when(promptTaskMapper.selectByTaskName(any(), any(), any())).thenReturn(null);
            CreatePromptTaskRsp response = promptEngineerService.createPromptTaskDraft(projectId, workspaceId, body);
            // Then
            assertNotNull(response);
        }
    }

    @Test
    public void test_createPromptTaskDraft_insert_throws_exception() throws Exception {
        // Given
        String projectId = "proj123";
        String workspaceId = "ws123";
        PromptTaskCreateReq body = mock(PromptTaskCreateReq.class);
        when(body.getName()).thenReturn("TaskName");

        PromptTaskDetailVo promptTaskDetailVo = mock(PromptTaskDetailVo.class);
        PromptTaskEntity promptTaskEntity = mock(PromptTaskEntity.class);
        when(promptTaskDetailVo.convert2PromptTaskEntity()).thenReturn(promptTaskEntity);
        when(promptTaskEntity.getId()).thenReturn("task123");

        doThrow(new RuntimeException("Database error")).when(promptTaskMapper).insert(any(PromptTaskEntity.class));

        // When & Then
        assertThrows(RuntimeException.class, () -> {
            promptEngineerService.createPromptTaskDraft(projectId, workspaceId, body);
        });
    }

    @Test
    void test_createPromptTaskDraft_should_not_throw_exception() throws Exception {
        assertThrows(NullPointerException.class, () -> {
            // 只保留实际使用的 2 个静态 Mock 资源
            try (MockedStatic<RequestContextUtils> mockedStaticRequestContextUtils = mockStatic(
                    RequestContextUtils.class, RETURNS_DEEP_STUBS);
                 MockedStatic<JsonUtils> mockedStaticJsonUtils = mockStatic(JsonUtils.class, RETURNS_DEEP_STUBS)) {

                // Given：配置用到的静态方法 Mock 行为
                mockedStaticRequestContextUtils.when(() -> RequestContextUtils.getRequestUserName()).thenReturn(null);
                mockedStaticRequestContextUtils.when(() -> RequestContextUtils.getRequestUserId()).thenReturn(null);

                mockedStaticJsonUtils.when(() -> JsonUtils.json2Obj(anyString(), any(TypeReference.class)))
                        .thenReturn(null);

                // When：调用被测试方法（预期抛出 AgentStudioException）
                CreatePromptTaskRsp result = promptEngineerService.createPromptTaskDraft(null, null, null);
            }
        });
    }

    @Test
    public void test_createPromptTask_task_not_found() throws Exception {
        // Given
        String projectId = "proj1";
        String taskId = "task1";
        String workspaceId = "ws1";
        when(promptTaskMapper.selectByPrimaryKey(eq(taskId), eq(projectId), eq(workspaceId))).thenReturn(null);

        // When & Then
        assertThrows(AgentStudioException.class, () -> {
            promptEngineerService.createPromptTask(projectId, taskId, workspaceId);
        });
    }

    @Test
    public void test_createPromptTask_success() throws Exception {
        // Given
        String projectId = "proj1";
        String taskId = "task1";
        String workspaceId = "ws1";
        PromptTaskEntity taskEntity = mock(PromptTaskEntity.class);
        when(taskEntity.getName()).thenReturn("taskName");
        when(taskEntity.convert2PromptTaskDetailVo()).thenReturn(mock(PromptTaskDetailVo.class));
        when(promptTaskMapper.selectByPrimaryKey(eq(taskId), eq(projectId), eq(workspaceId))).thenReturn(taskEntity);
        when(promptTaskMapper.selectByTaskNameNotInDraft(anyString(), anyString(), anyString())).thenReturn(null);

        // When
        CreatePromptTaskRsp response = promptEngineerService.createPromptTask(projectId, taskId, workspaceId);

        // Then
        assertNotNull(response);
        assertEquals(taskEntity.convert2PromptTaskDetailVo().getId(), response.getTaskId());
        verify(promptOptimizeTaskService).submitTask(any(PromptTaskDetailVo.class));
    }

    @Test
    void test_createPromptTask_should_return_not_null() throws Exception {
        // Given
        PromptTaskEntity promptTaskEntity = PromptTaskEntity.builder().name("not_empty").build();
        when(promptTaskMapper.selectByTaskNameNotInDraft(anyString(), anyString(), anyString())).thenReturn(
            promptTaskEntity);
        PromptTaskEntity promptTaskEntity1 = PromptTaskEntity.builder().name("not_empty").build();
        when(promptTaskMapper.selectByPrimaryKey(anyString(), anyString(), anyString())).thenReturn(promptTaskEntity1);

        assertThrows(AgentStudioException.class, () -> {
            promptEngineerService.createPromptTask("not_empty", "not_empty", "not_empty");
        });
    }

    @Test
    void test_createPromptTask_should_not_throw_exception() throws Exception {
        assertThrows(AgentStudioException.class, () -> {
            // Given
            when(promptTaskMapper.selectByTaskNameNotInDraft(anyString(), anyString(), anyString())).thenReturn(null);
            when(promptTaskMapper.selectByPrimaryKey(anyString(), anyString(), anyString())).thenReturn(null);

            // When
            CreatePromptTaskRsp result = promptEngineerService.createPromptTask(null, null, null);
        });
    }

    @Test
    void test_copyPromptTask_success() {
        // Given
        String projectId = "proj1";
        String taskId = "task1";
        String workspaceId = "ws1";
        PromptTaskEntity taskEntity = mock(PromptTaskEntity.class);
        when(promptTaskMapper.selectByPrimaryKey(eq(taskId), eq(projectId), eq(workspaceId))).thenReturn(taskEntity);
        when(promptTaskMapper.selectAllOptimizeTaskNames(anyString(), anyString())).thenReturn(new ArrayList<String>());
        when(taskEntity.getStatus()).thenReturn(PromptTaskStatusEnum.SUCCESS.getCode());

        // When
        CreatePromptTaskRsp response = promptEngineerService.copyPromptTask(projectId, taskId, workspaceId);

        // Then
        assertNotNull(response);
        assertNotEquals(taskId, response.getTaskId());
    }

    @Test
    public void test_task_does_not_exist() throws Exception {
        // Given
        String projectId = "proj1";
        String taskId = "task1";
        String workspaceId = "ws1";
        when(promptTaskMapper.selectByPrimaryKey(eq(taskId), eq(projectId), eq(workspaceId))).thenReturn(null);

        // When & Then
        assertThrows(AgentStudioException.class, () -> {
            promptEngineerService.deletePromptTask(projectId, taskId, workspaceId);
        });
    }

    @Test
    public void test_task_is_running() throws Exception {
        // Given
        String projectId = "proj1";
        String taskId = "task1";
        String workspaceId = "ws1";
        PromptTaskEntity taskEntity = mock(PromptTaskEntity.class);
        when(taskEntity.getStatus()).thenReturn(PromptTaskStatusEnum.RUNNING.getCode());
        when(promptTaskMapper.selectByPrimaryKey(eq(taskId), eq(projectId), eq(workspaceId))).thenReturn(taskEntity);

        // When & Then
        assertThrows(AgentStudioException.class, () -> {
            promptEngineerService.deletePromptTask(projectId, taskId, workspaceId);
        });
    }

    @Test
    public void test_delete_task() throws Exception {
        assertDoesNotThrow(() -> {
            String projectId = "proj1";
            String taskId = "task1";
            String workspaceId = "ws1";
            PromptTaskEntity taskEntity = mock(PromptTaskEntity.class);
            when(taskEntity.getStatus()).thenReturn(PromptTaskStatusEnum.WAITING.getCode());
            when(promptTaskMapper.selectByPrimaryKey(eq(taskId), eq(projectId), eq(workspaceId))).thenReturn(
                taskEntity);

            // When
            promptEngineerService.deletePromptTask(projectId, taskId, workspaceId);
        });
    }

    @Test
    public void test_successful_deletion() throws Exception {
        // Given
        String projectId = "proj1";
        String taskId = "task1";
        String workspaceId = "ws1";
        PromptTaskEntity taskEntity = mock(PromptTaskEntity.class);
        when(taskEntity.getStatus()).thenReturn(PromptTaskStatusEnum.WAITING.getCode());
        when(promptTaskMapper.selectByPrimaryKey(eq(taskId), eq(projectId), eq(workspaceId))).thenReturn(taskEntity);

        // When
        PromptBaseInfo result = promptEngineerService.deletePromptTask(projectId, taskId, workspaceId);

        // Then
        assertEquals(taskId, result.getTaskId());
    }

    @Test
    public void test_getPromptTask_task_entity_not_found() throws Exception {
        // Given
        String projectId = "proj1";
        String taskId = "task1";
        String workspaceId = "ws1";
        when(promptTaskMapper.selectByPrimaryKey(eq(taskId), eq(projectId), eq(workspaceId))).thenReturn(null);

        // When & Then
        assertThrows(AgentStudioException.class, () -> {
            promptEngineerService.getPromptTask(projectId, taskId, workspaceId);
        });
    }

    @Test
    public void test_getPromptTask_task_entity_found_no_jiuwen_task_id() throws Exception {

        // Given
        String projectId = "proj1";
        String taskId = "task1";
        String workspaceId = "ws1";
        PromptTaskEntity taskEntity = mock(PromptTaskEntity.class);
        PromptTaskDetailVo taskDetailVo = mock(PromptTaskDetailVo.class);
        when(promptTaskMapper.selectByPrimaryKey(eq(taskId), eq(projectId), eq(workspaceId))).thenReturn(taskEntity);
        when(taskEntity.convert2PromptTaskDetailVo()).thenReturn(taskDetailVo);
        when(taskEntity.getStatus()).thenReturn(2);

        // When
        PromptBaseResp response = promptEngineerService.getPromptTask(projectId, taskId, workspaceId);

        // Then
        assertEquals(200, response.getCode());
        assertEquals("success", response.getMessage());
        assertNotNull(response.getData());
    }

    @Test
    public void test_getPromptTask_task_entity_found_with_jiuwen_task_id() throws Exception {
        // Given
        String projectId = "proj1";
        String taskId = "task1";
        String workspaceId = "ws1";
        PromptTaskEntity taskEntity = mock(PromptTaskEntity.class);
        PromptTaskDetailVo taskDetailVo = mock(PromptTaskDetailVo.class);
        when(promptTaskMapper.selectByPrimaryKey(eq(taskId), eq(projectId), eq(workspaceId))).thenReturn(taskEntity);
        when(taskEntity.convert2PromptTaskDetailVo()).thenReturn(taskDetailVo);
        when(taskEntity.getStatus()).thenReturn(2);
        when(taskDetailVo.getJiuwenTaskId()).thenReturn("jiuwen1");
        when(taskDetailVo.getStatus()).thenReturn(PromptTaskStatusEnum.RUNNING);

        JiuWenPromptDeatilRes jiuWenPromptDetailRes = new JiuWenPromptDeatilRes();
        JiuWenProgress jiuWenProgress = new JiuWenProgress();
        jiuWenProgress.setStatus("running");
        jiuWenProgress.setProgressRate(50d);
        jiuWenProgress.setBestPrompt("best1");
        jiuWenPromptDetailRes.setProgress(jiuWenProgress);

        List<JiuWenHistory> jiuWenHistoryList = new ArrayList<>();
        JiuWenHistory jiuWenHistory = new JiuWenHistory();
        jiuWenHistory.setOptimizedPrompt("opt1");
        jiuWenHistory.setIterationRound(1);
        jiuWenHistory.setSuccessRate(80d);
        jiuWenHistoryList.add(jiuWenHistory);
        jiuWenPromptDetailRes.setHistory(jiuWenHistoryList);

        when(promptOptimizeTaskService.getTaskDetail(any(PromptTaskDetailVo.class)))
                .thenReturn(jiuWenPromptDetailRes);

        // When
        PromptBaseResp response = promptEngineerService.getPromptTask(projectId, taskId, workspaceId);

        // Then
        assertEquals(200, response.getCode());
        assertEquals("success", response.getMessage());
        assertNotNull(response.getData());
    }

    @Test
    void test_getPromptTask_should_not_throw_exception() throws Exception {
        assertDoesNotThrow(() -> {
            String projectId = "proj1";
            String taskId = "task1";
            String workspaceId = "ws1";
            PromptTaskDetailVo promptTaskDetailVo = mock(PromptTaskDetailVo.class);


            // Given
            PromptTaskEntity promptTaskEntity = mock(PromptTaskEntity.class);
            when(promptTaskMapper.selectByPrimaryKey(anyString(), anyString(), anyString())).thenReturn(promptTaskEntity);
            when(promptTaskEntity.getStatus()).thenReturn(2);
            when(promptTaskEntity.convert2PromptTaskDetailVo()).thenReturn(promptTaskDetailVo);

            when(promptOptimizeTaskService.getTaskDetail(any(PromptTaskDetailVo.class))).thenReturn(null);

            // When
            PromptBaseResp result = promptEngineerService.getPromptTask(projectId, taskId, workspaceId);
        });
    }

    @Test
    void test_getPromptTask_should_return_not_null5() throws Exception {
        String projectId = "proj1";
        String taskId = "task1";
        String workspaceId = "ws1";
        // Given
        PromptTaskEntity promptTaskEntity = mock(PromptTaskEntity.class);
        PromptTaskDetailVo promptTaskDetailVo = mock(PromptTaskDetailVo.class);

        when(promptTaskMapper.selectByPrimaryKey(eq(taskId), eq(projectId), eq(workspaceId))).thenReturn(promptTaskEntity);
        when(promptTaskEntity.getStatus()).thenReturn(2);
        when(promptTaskEntity.convert2PromptTaskDetailVo()).thenReturn(promptTaskDetailVo);

        when(promptOptimizeTaskService.getTaskDetail(any(PromptTaskDetailVo.class))).thenReturn(null);

        // When
        PromptBaseResp result = promptEngineerService.getPromptTask(projectId, taskId, workspaceId);


        // Then
        assertNotNull(result);
    }

    @Test
    public void test_task_entity_not_exist() throws Exception {
        // Given
        String projectId = "proj1";
        String taskId = "task1";
        String iterNum = "1";
        GetPromptTaskIterEvalResQo qo = new GetPromptTaskIterEvalResQo();
        when(promptTaskMapper.selectByPrimaryKey(eq(taskId), eq(projectId), eq(qo.getWorkspaceId()))).thenReturn(null);

        // When & Then
        assertThrows(AgentStudioException.class, () -> {
            promptEngineerService.getPromptTaskIterEvalRes(projectId, taskId, iterNum, qo);
        });
    }

    @Test
    public void test_task_not_executed() throws Exception {
        // Given
        GetPromptTaskIterEvalResQo qo = mock(GetPromptTaskIterEvalResQo.class);
        PromptTaskEntity taskEntity = mock(PromptTaskEntity.class);
        PromptTaskDetailVo taskDetailVo = mock(PromptTaskDetailVo.class);
        when(promptTaskMapper.selectByPrimaryKey(anyString(), anyString(), anyString())).thenReturn(taskEntity);
        when(taskEntity.convert2PromptTaskDetailVo()).thenReturn(taskDetailVo);
        when(taskDetailVo.getJiuwenTaskId()).thenReturn("");

        // When & Then
        assertThrows(AgentStudioException.class, () -> {
            promptEngineerService.getPromptTaskIterEvalRes("anyString()", "anyString()", "anyString()", qo);
        });
    }

    @Test
    public void test_iteration_not_exist() throws Exception {
        // Given
        String projectId = "proj1";
        String taskId = "task1";
        String workspaceId = "ws1";
        String iterNum = "1"; // 假设此迭代编号在 history 中不存在
        String jiuwenTaskId = "jiuwen1"; // 确保非空，跳过 isBlank 分支

        GetPromptTaskIterEvalResQo qo = mock(GetPromptTaskIterEvalResQo.class);
        PromptTaskEntity taskEntity = mock(PromptTaskEntity.class);
        PromptTaskDetailVo promptTaskDetailVo = mock(PromptTaskDetailVo.class);

        // 1. 配置 taskEntity 返回 mock 的 promptTaskDetailVo
        when(promptTaskMapper.selectByPrimaryKey(eq(taskId), eq(projectId), eq(workspaceId))).thenReturn(taskEntity);
        when(taskEntity.convert2PromptTaskDetailVo()).thenReturn(promptTaskDetailVo);

        when(qo.getWorkspaceId()).thenReturn(workspaceId);

        // 2. 确保 jiuwenTaskId 非空，跳过 isBlank 检查
        when(promptTaskDetailVo.getJiuwenTaskId()).thenReturn(jiuwenTaskId);

        // 3. 配置优化任务详情：返回空 history（无迭代记录）
        JiuWenPromptDeatilRes res = new JiuWenPromptDeatilRes();
        res.setHistory(new ArrayList<>()); // 空列表，模拟“迭代不存在”
        when(promptOptimizeTaskService.getTaskDetail(any(PromptTaskDetailVo.class))).thenReturn(res); // 必须配置，否则返回 null

        // When & Then：验证抛出“迭代不存在”的异常
        assertThrows(AgentStudioException.class, () -> {
            promptEngineerService.getPromptTaskIterEvalRes(projectId, taskId, iterNum, qo);
        });
    }

    @Test
    public void test_normal_flow() throws Exception {
        // Given
        String projectId = "proj1";
        String taskId = "task1";
        String workspaceId = "ws1";
        String iterNum = "0"; // 假设此迭代编号在 history 中不存在
        String jiuwenTaskId = "jiuwen1"; // 确保非空，跳过 isBlank 分支
        GetPromptTaskIterEvalResQo qo = mock(GetPromptTaskIterEvalResQo.class);
        PromptTaskEntity taskEntity = mock(PromptTaskEntity.class);
        PromptTaskDetailVo promptTaskDetailVo = mock(PromptTaskDetailVo.class);
        when(promptTaskDetailVo.getJiuwenTaskId()).thenReturn(jiuwenTaskId);
        when(promptTaskMapper.selectByPrimaryKey(eq(taskId), eq(projectId), eq(workspaceId))).thenReturn(taskEntity);
        when(taskEntity.convert2PromptTaskDetailVo()).thenReturn(promptTaskDetailVo);
        when(taskEntity.getStatus()).thenReturn(PromptTaskStatusEnum.RUNNING.getCode());
        when(qo.getWorkspaceId()).thenReturn(workspaceId);
        JiuWenPromptDeatilRes res = new JiuWenPromptDeatilRes();
        List<JiuWenHistory> history = new ArrayList<>();
        JiuWenHistory jiuWenHistory = new JiuWenHistory();
        List<JiuWenEvaluation> evaluations = new ArrayList<>();
        JiuWenEvaluation evaluation = new JiuWenEvaluation();
        evaluation.setOrder(1);
        evaluation.setVariable(new HashMap<>());
        evaluation.setPredict("pred1");
        evaluation.setLabel("label1");
        evaluation.setScore(0.9f);
        evaluation.setReason("reason1");
        evaluations.add(evaluation);
        jiuWenHistory.setEvaluations(evaluations);
        history.add(jiuWenHistory);
        res.setHistory(history);
        when(promptOptimizeTaskService.getTaskDetail(any(PromptTaskDetailVo.class))).thenReturn(res);

        // When
        PromptBaseResp response = promptEngineerService.getPromptTaskIterEvalRes(projectId, taskId, iterNum, qo);

        // Then
        assertNotNull(response);
        assertEquals(200, response.getCode());
        assertEquals("success", response.getMessage());
        assertNotNull(response.getData());
    }

    @Test
    void test_getPromptTaskIterEvalRes_should_not_throw_exception() throws Exception {
        assertThrows(NullPointerException.class, () -> {
            // 只保留实际使用的静态 Mock 资源
            try (MockedStatic<JsonUtils> mockedStaticJsonUtils = mockStatic(JsonUtils.class, RETURNS_DEEP_STUBS)) {
                // Given
                mockedStaticJsonUtils.when(() -> JsonUtils.toJson(anyMap())).thenReturn(null);

                when(promptTaskMapper.selectByPrimaryKey(anyString(), anyString(), anyString())).thenReturn(null);

                when(promptOptimizeTaskService.getTaskDetail(any(PromptTaskDetailVo.class))).thenReturn(null);

                // When
                PromptBaseResp result = promptEngineerService.getPromptTaskIterEvalRes(null, null, null, null);
            }
        });
    }

    @Test
    void test_listPromptTasks_with_empty_result() throws Exception {
        // Given
        String projectId = "proj1";
        ListPromptTasksQo listPromptTasksQo = mock(ListPromptTasksQo.class);
        PageInfo<PromptTaskEntity> emptyPage = new PageInfo<>(Collections.emptyList());

        try (MockedStatic<CollectionUtils> mockedCollectionUtils = mockStatic(CollectionUtils.class)) {
            mockedCollectionUtils.when(() -> CollectionUtils.isEmpty(any(Collection.class))).thenReturn(true);

            // When
            PromptBaseResp response = promptEngineerService.listPromptTasks(projectId, listPromptTasksQo);

            // Then
            assertNotNull(response);
            assertEquals(200, response.getCode());
        }
    }

    /**
     * 测试 pausePromptTask 正常流程：
     * 1. 任务存在
     * 2. 调用暂停接口
     * 3. 更新状态为 PAUSE
     */
    @Test
    void test_pausePromptTask_success() {
        String projectId = "proj1";
        String taskId = "task1";
        String workspaceId = "ws1";
        String jiuwenTaskId = "jiuwen123"; // 九问任务ID
        // 1. 准备测试数据：模拟存在的任务实体
        PromptTaskEntity taskEntity = PromptTaskEntity.builder()
            .id(taskId)
            .projectId(projectId)
            .jiuwenTaskId(jiuwenTaskId)
            .status(PromptTaskStatusEnum.RUNNING.getCode()) // 原状态为运行中
            .build();
        when(promptTaskMapper.selectByPrimaryKey(eq(taskId), eq(projectId), eq(workspaceId))).thenReturn(taskEntity);

        // 2. 执行暂停任务
        PromptBaseInfo result = promptEngineerService.pausePromptTask(projectId, taskId, workspaceId);

        // 3. 验证结果
        assertNotNull(result);
        assertEquals(taskId, result.getTaskId());
        assertEquals("task stop successfully", result.getMessage());

        // 4. 验证依赖调用：暂停九问任务 + 更新状态
        verify(promptOptimizeTaskService).pauseTask(any(PromptTaskDetailVo.class));
        verify(promptTaskMapper).updateStatusByPrimaryKey(eq(taskId), eq(PromptTaskStatusEnum.PAUSING.getCode()),
            eq(projectId), eq(workspaceId));
    }

    /**
     * 测试 pausePromptTask 异常场景：任务不存在
     */
    @Test
    void test_pausePromptTask_task_not_exist() {
        String projectId = "proj1";
        String taskId = "task1";
        String workspaceId = "ws1";
        String jiuwenTaskId = "jiuwen123"; // 九问任务ID
        // 1. 模拟任务不存在（mapper返回null）
        when(promptTaskMapper.selectByPrimaryKey(eq(taskId), eq(projectId), eq(workspaceId))).thenReturn(null);

        // 2. 执行并验证抛出异常
        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            promptEngineerService.pausePromptTask(projectId, taskId, workspaceId);
        });

        // 3. 验证依赖未被调用
        verify(promptOptimizeTaskService, never()).pauseTask(any(PromptTaskDetailVo.class));
        verify(promptTaskMapper, never()).updateStatusByPrimaryKey(anyString(), anyInt(), anyString(), anyString());
    }

    /**
     * 测试 resumePromptTask 正常流程：
     * 1. 任务存在
     * 2. 调用恢复接口
     * 3. 更新状态为 RUNNING
     */
    @Test
    void test_resumePromptTask_success() {
        String projectId = "proj1";
        String taskId = "task1";
        String workspaceId = "ws1";
        String jiuwenTaskId = "jiuwen123"; // 九问任务ID
        // 1. 准备测试数据：模拟存在的任务实体
        PromptTaskEntity taskEntity = PromptTaskEntity.builder()
            .id(taskId)
            .projectId(projectId)
            .jiuwenTaskId(jiuwenTaskId)
            .status(PromptTaskStatusEnum.PAUSE.getCode()) // 原状态为暂停
            .build();
        when(promptTaskMapper.selectByPrimaryKey(eq(taskId), eq(projectId), eq(workspaceId))).thenReturn(taskEntity);

        // 2. 执行恢复任务
        PromptBaseInfo result = promptEngineerService.resumePromptTask(projectId, taskId, workspaceId);

        // 3. 验证结果
        assertNotNull(result);
        assertEquals(taskId, result.getTaskId());
        assertEquals("task resume successfully", result.getMessage());

        // 4. 验证依赖调用：恢复九问任务 + 更新状态
        verify(promptOptimizeTaskService).resumeTask(any(PromptTaskDetailVo.class));
        verify(promptTaskMapper).updateStatusByPrimaryKey(eq(taskId), eq(PromptTaskStatusEnum.RUNNING.getCode()),
            eq(projectId), eq(workspaceId));
    }

    /**
     * 测试 resumePromptTask 异常场景：任务不存在
     */
    @Test
    void test_resumePromptTask_task_not_exist() {
        String projectId = "proj1";
        String taskId = "task1";
        String workspaceId = "ws1";
        // 1. 模拟任务不存在（mapper返回null）
        when(promptTaskMapper.selectByPrimaryKey(eq(taskId), eq(projectId), eq(workspaceId))).thenReturn(null);

        // 2. 执行并验证抛出异常
        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            promptEngineerService.resumePromptTask(projectId, taskId, workspaceId);
        });

        // 3. 验证依赖未被调用
        verify(promptOptimizeTaskService, never()).resumeTask(any(PromptTaskDetailVo.class));
        verify(promptTaskMapper, never()).updateStatusByPrimaryKey(anyString(), anyInt(), anyString(), anyString());
    }

    /**
     * 测试 startPromptTask：当前返回null，验证返回值
     */
    @Test
    void test_startPromptTask() {
        String projectId = "proj1";
        String taskId = "task1";
        String workspaceId = "ws1";
        // 执行启动任务（当前实现返回null）
        PromptBaseInfo result = promptEngineerService.startPromptTask(projectId, taskId, workspaceId);

        // 验证返回值为null（若后续实现逻辑，需更新测试）
        assertNull(result);
    }

    /**
     * 测试正常流程：更新存在的草稿任务
     */
    @Test
    void test_updatePromptTaskDraft_success() {
        String projectId = "proj1";
        String taskId = "task1";
        String workspaceId = "ws1";
        String userId = "user1";
        String userName = "userName1";

        // 1. 准备请求参数
        PromptTaskCreateReq req = JsonUtils.json2ObjQuietly(reqBody, PromptTaskCreateReq.class);

        // 2. 准备原始任务数据（存在且为草稿状态）
        PromptTaskEntity oriEntity = mock(PromptTaskEntity.class);
        PromptTaskDetailVo oriDetailVo = mock(PromptTaskDetailVo.class);
        when(oriEntity.convert2PromptTaskDetailVo()).thenReturn(oriDetailVo);
        when(promptTaskMapper.selectByPrimaryKey(eq(taskId), eq(projectId), eq(workspaceId))).thenReturn(oriEntity);
        when(oriDetailVo.getStatus()).thenReturn(PromptTaskStatusEnum.DRAFT);
        when(promptTaskMapper.queryProjectIdByModelId("180")).thenReturn(projectId);
        when(promptTaskMapper.queryPublishStatusByModelId("180")).thenReturn("online");
        List<PromptTaskEntity> promptTaskEntities = new ArrayList<>();
        when(promptTaskMapper.selectByTaskName(any(), any(), any())).thenReturn(promptTaskEntities);


        // 3. 准备 buildPromptTaskDetailVo 依赖的新任务详情
        PromptTaskDetailVo newDetailVo = PromptTaskDetailVo.builder()
            .id(UUID.randomUUID().toString())
            .name("newTask")
            .desc("newDesc")
            .status(PromptTaskStatusEnum.DRAFT)
            .build();

        // 4. Mock 静态方法和私有方法依赖
        try (MockedStatic<BeanUtils> mockedBeanUtils = mockStatic(BeanUtils.class);
            MockedStatic<JsonUtils> mockedJsonUtils = mockStatic(JsonUtils.class);
            MockedStatic<RequestContextUtils> mockedRequestContext = mockStatic(RequestContextUtils.class)) {

            // Mock BeanUtils.copyProperties（无实际逻辑，仅避免 NPE）
            mockedBeanUtils.when(() -> BeanUtils.copyProperties(any(), any())).thenAnswer(invocation -> null);

            // Mock JsonUtils.json2Obj（解析 ptVars 为 List<PromptVar>）
            List<PromptVar> promptVars = Collections.singletonList(
                PromptVar.builder().name("var1").content("value1").type(PtTypeEnum.TEXT).build());
            mockedJsonUtils.when(() -> JsonUtils.json2ObjQuietly(eq(req.getPtVars()), any())).thenReturn(promptVars);

            // Mock RequestContextUtils（获取当前用户）
            mockedRequestContext.when(RequestContextUtils::getRequestUserId).thenReturn(userId);
            mockedRequestContext.when(RequestContextUtils::getRequestUserName).thenReturn(userName);

            // 5. Mock Mapper 更新成功（返回 1）
            PromptTaskEntity updatedEntity = mock(PromptTaskEntity.class);
            when(oriDetailVo.convert2PromptTaskEntity()).thenReturn(updatedEntity);
            when(promptTaskMapper.updateByPrimaryKey(eq(updatedEntity), eq(projectId), eq(workspaceId))).thenReturn(1);

            // 6. 执行测试方法
            PromptBaseResp response = promptEngineerService.updatePromptTaskDraft(projectId, taskId, workspaceId, req);

            // 7. 验证结果
            assertNotNull(response);
            assertEquals(200, response.getCode());
            assertEquals("success", response.getMessage());

            // 8. 验证依赖调用
            verify(promptTaskMapper).selectByPrimaryKey(eq(taskId), eq(projectId), eq(workspaceId));
            verify(promptTaskMapper).updateByPrimaryKey(eq(updatedEntity), eq(projectId), eq(workspaceId));

        }
    }

    /**
     * 测试异常场景：任务不存在
     */
    @Test
    void test_updatePromptTaskDraft_task_not_exist() {
        String projectId = "proj1";
        String taskId = "task1";
        String workspaceId = "ws1";
        // 1. 模拟 Mapper 返回 null（任务不存在）
        when(promptTaskMapper.selectByPrimaryKey(eq(taskId), eq(projectId), eq(workspaceId))).thenReturn(null);

        // 2. 执行并验证异常
        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            promptEngineerService.updatePromptTaskDraft(projectId, taskId, workspaceId,
                mock(PromptTaskCreateReq.class));
        });

        // 3. 验证异常信息
        verify(promptTaskMapper).selectByPrimaryKey(eq(taskId), eq(projectId), eq(workspaceId));
        verify(promptTaskMapper, never()).updateByPrimaryKey(any(), anyString(), anyString());
    }

    /**
     * 测试异常场景：任务非草稿状态
     */
    @Test
    void test_updatePromptTaskDraft_task_not_draft() {

        // 只保留实际使用的 2 个静态 Mock 资源
        try (MockedStatic<RequestContextUtils> mockedStaticRequestContextUtils = mockStatic(
            RequestContextUtils.class, RETURNS_DEEP_STUBS)) {

            // Given：配置用到的静态方法 Mock 行为
            mockedStaticRequestContextUtils.when(() -> RequestContextUtils.getRequestUserName()).thenReturn(null);
            mockedStaticRequestContextUtils.when(() -> RequestContextUtils.getRequestUserId()).thenReturn(null);
            mockedStaticRequestContextUtils.when(() -> RequestContextUtils.getRequestUserDomainId()).thenReturn(null);

            String projectId = "proj1";
            String taskId = "task1";
            String workspaceId = "ws1";
            PromptTaskCreateReq promptTaskCreateReq = new PromptTaskCreateReq();
            ExecConfig execConfig = new ExecConfig();
            execConfig.setExecType(ExecConfig.ExecTypeEnum.MODEL);
            execConfig.setModel("180");
            promptTaskCreateReq.setPtObject(execConfig);
            promptTaskCreateReq.setAssitantObject(execConfig);
            promptTaskCreateReq.setTargetAcc("99");
            promptTaskCreateReq.setPtType(PromptTaskCreateReq.PtTypeEnum.TEXT);
            promptTaskCreateReq.setTargetType(PromptTaskCreateReq.TargetTypeEnum.OBJECTIVE);
            // 1. 准备非草稿状态的任务
            PromptTaskEntity oriEntity = mock(PromptTaskEntity.class);
            PromptTaskDetailVo oriDetailVo = PromptTaskDetailVo.builder()
                .id(taskId)
                .status(PromptTaskStatusEnum.RUNNING) // 运行中状态
                .build();
            when(oriEntity.convert2PromptTaskDetailVo()).thenReturn(oriDetailVo);
            when(promptTaskMapper.selectByPrimaryKey(eq(taskId), eq(projectId), eq(workspaceId))).thenReturn(oriEntity);


            // 2. 执行并验证异常
            AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
                promptEngineerService.updatePromptTaskDraft(projectId, taskId, workspaceId, promptTaskCreateReq);
            });

            // 3. 验证异常信息
            verify(promptTaskMapper).selectByPrimaryKey(eq(taskId), eq(projectId), eq(workspaceId));
        }
    }

    /**
     * 测试异常场景：更新失败（updateByPrimaryKey 返回 0）
     */
    @Test
    void test_updatePromptTaskDraft_update_return_zero() {
        String projectId = "proj1";
        String taskId = "task1";
        String workspaceId = "ws1";
        String userId = "user1";
        String domainId = "domain1";
        PromptTaskCreateReq promptTaskCreateReq = new PromptTaskCreateReq();
        ExecConfig execConfig = new ExecConfig();
        execConfig.setExecType(ExecConfig.ExecTypeEnum.MODEL);
        execConfig.setModel("180");
        promptTaskCreateReq.setPtObject(execConfig);
        promptTaskCreateReq.setAssitantObject(execConfig);
        promptTaskCreateReq.setTargetAcc("99");
        promptTaskCreateReq.setPtType(PromptTaskCreateReq.PtTypeEnum.TEXT);
        promptTaskCreateReq.setTargetType(PromptTaskCreateReq.TargetTypeEnum.OBJECTIVE);
        // 1. 准备草稿状态的任务
        PromptTaskEntity oriEntity = mock(PromptTaskEntity.class);
        PromptTaskDetailVo oriDetailVo = mock(PromptTaskDetailVo.class);
        when(oriEntity.convert2PromptTaskDetailVo()).thenReturn(oriDetailVo);
        when(promptTaskMapper.selectByPrimaryKey(eq(taskId), eq(projectId), eq(workspaceId))).thenReturn(oriEntity);

        // 2. Mock 静态方法（避免 buildPromptTaskDetailVo 报错）
        try (MockedStatic<BeanUtils> mockedBeanUtils = mockStatic(BeanUtils.class);
            MockedStatic<JsonUtils> mockedJsonUtils = mockStatic(JsonUtils.class);
            MockedStatic<RequestContextUtils> mockedRequestContext = mockStatic(RequestContextUtils.class)) {
            mockedBeanUtils.when(() -> BeanUtils.copyProperties(any(), any())).thenAnswer(invocation -> null);
            mockedJsonUtils.when(() -> JsonUtils.json2Obj(anyString(), any())).thenReturn(new ArrayList<>());
            mockedRequestContext.when(RequestContextUtils::getRequestUserId).thenReturn(userId);
            mockedRequestContext.when(RequestContextUtils::getRequestUserDomainId).thenReturn(domainId);

            // 3. Mock updateByPrimaryKey 返回 0（更新失败）
            PromptTaskEntity updatedEntity = mock(PromptTaskEntity.class);
            when(oriDetailVo.convert2PromptTaskEntity()).thenReturn(updatedEntity);
            when(promptTaskMapper.updateByPrimaryKey(eq(updatedEntity), eq(projectId), eq(workspaceId))).thenReturn(0);

            // 4. 执行并验证异常
            AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
                promptEngineerService.updatePromptTaskDraft(projectId, taskId, workspaceId, promptTaskCreateReq);
            });

        }
    }

    /**
     * 测试异常场景：更新抛出异常（如 SQL 异常）
     */
    @Test
    void test_updatePromptTaskDraft_update_throw_exception() {
        String projectId = "proj1";
        String taskId = "task1";
        String workspaceId = "ws1";
        String userId = "user1";
        String domainId = "domain1";
        PromptTaskCreateReq promptTaskCreateReq = new PromptTaskCreateReq();
        ExecConfig execConfig = new ExecConfig();
        execConfig.setExecType(ExecConfig.ExecTypeEnum.MODEL);
        execConfig.setModel("180");
        promptTaskCreateReq.setPtObject(execConfig);
        promptTaskCreateReq.setAssitantObject(execConfig);
        promptTaskCreateReq.setTargetAcc("99");
        promptTaskCreateReq.setPtType(PromptTaskCreateReq.PtTypeEnum.TEXT);
        promptTaskCreateReq.setTargetType(PromptTaskCreateReq.TargetTypeEnum.OBJECTIVE);
        // 1. 准备草稿状态的任务
        PromptTaskEntity oriEntity = mock(PromptTaskEntity.class);
        PromptTaskDetailVo oriDetailVo = mock(PromptTaskDetailVo.class);
        when(oriEntity.convert2PromptTaskDetailVo()).thenReturn(oriDetailVo);
        when(promptTaskMapper.selectByPrimaryKey(eq(taskId), eq(projectId), eq(workspaceId))).thenReturn(oriEntity);

        // 2. Mock 静态方法
        try (MockedStatic<BeanUtils> mockedBeanUtils = mockStatic(BeanUtils.class);
            MockedStatic<JsonUtils> mockedJsonUtils = mockStatic(JsonUtils.class);
            MockedStatic<RequestContextUtils> mockedRequestContext = mockStatic(RequestContextUtils.class)) {
            mockedBeanUtils.when(() -> BeanUtils.copyProperties(any(), any())).thenAnswer(invocation -> null);
            mockedJsonUtils.when(() -> JsonUtils.json2Obj(anyString(), any())).thenReturn(new ArrayList<>());
            mockedRequestContext.when(RequestContextUtils::getRequestUserId).thenReturn(userId);
            mockedRequestContext.when(RequestContextUtils::getRequestUserDomainId).thenReturn(domainId);

            // 3. Mock updateByPrimaryKey 抛出异常
            PromptTaskEntity updatedEntity = mock(PromptTaskEntity.class);
            when(oriDetailVo.convert2PromptTaskEntity()).thenReturn(updatedEntity);
            when(promptTaskMapper.updateByPrimaryKey(eq(updatedEntity), eq(projectId), eq(workspaceId))).thenThrow(
                new RuntimeException("DB error"));

            // 4. 执行并验证异常
            RuntimeException exception = assertThrows(RuntimeException.class, () -> {
                promptEngineerService.updatePromptTaskDraft(projectId, taskId, workspaceId, promptTaskCreateReq);
            });

        }
    }

    @Test
    void test_listPromptTasks_should_return_not_null() throws Exception {
        try (MockedStatic<PageMethod> mockedStaticPageMethod = mockStatic(PageMethod.class, RETURNS_DEEP_STUBS)) {
            // Given
            PageInfo<PromptTaskEntity> entityPage = new PageInfo<>();
            List<PromptTaskEntity> list = new ArrayList<>();
            entityPage.setList(list);
            mockedStaticPageMethod.when(
                    () -> PageMethod.startPage(anyInt(), anyInt()).doSelectPageInfo(any(ISelect.class)))
                .thenReturn(entityPage);

            List<PromptTaskEntity> list1 = new ArrayList<>();
            PromptTaskEntity promptTaskEntity = PromptTaskEntity.builder().id("not_empty").build();
            list1.add(promptTaskEntity);
            when(promptTaskMapper.queryTaskIdsByCondition(any(ListPromptTasksQo.class), anyString(),
                anyInt())).thenReturn(list1);

            List<JiuWenProgress> data = new ArrayList<>();
            JiuWenProgress jiuWenProgress = JiuWenProgress.builder().build();
            data.add(jiuWenProgress);
            JiuWenJobDeatails jiuWenJobDeatails = JiuWenJobDeatails.builder().data(data).build();
            when(promptOptimizeTaskService.queryTaskDetailsByIds(any(ArrayList.class))).thenReturn(jiuWenJobDeatails);

            ListPromptTasksQo listPromptTasksQo = new ListPromptTasksQo();

            // When
            PromptBaseResp result = promptEngineerService.listPromptTasks("not_empty", listPromptTasksQo);

            // Then
            assertNotNull(result);
        }
    }

    @Test
    void test_listPromptTasks_mark_lost_pausing_task_as_failed() throws Exception {
        // 验证反向检查：PAUSING 任务在九问侧已丢失（get_infos 未返回该 jobId）时，
        // 应被标记为 FAILED 并写入 message，避免永久卡在暂停中
        try (MockedStatic<PageMethod> mockedStaticPageMethod = mockStatic(PageMethod.class, RETURNS_DEEP_STUBS)) {
            // Given: 一个处于 PAUSING 中间态的任务
            String taskId = "task_pausing";
            String jiuwenTaskId = "jw_lost";
            PromptTaskEntity pausingEntity = PromptTaskEntity.builder()
                .id(taskId)
                .projectId("proj1")
                .jiuwenTaskId(jiuwenTaskId)
                .status(PromptTaskStatusEnum.PAUSING.getCode())
                .ptType(PtTypeEnum.TEXT.toString())
                .build();

            // 分页结果包含该任务
            PageInfo<PromptTaskEntity> entityPage = new PageInfo<>();
            List<PromptTaskEntity> list = new ArrayList<>();
            list.add(pausingEntity);
            entityPage.setList(list);
            mockedStaticPageMethod.when(
                    () -> PageMethod.startPage(anyInt(), anyInt()).doSelectPageInfo(any(ISelect.class)))
                .thenReturn(entityPage);

            when(promptTaskMapper.queryTaskIdsByCondition(any(ListPromptTasksQo.class), anyString(),
                anyInt())).thenReturn(list);

            // 九问批量查询返回空 data：任务在执行引擎中已丢失
            JiuWenJobDeatails jiuWenJobDeatails = JiuWenJobDeatails.builder().data(new ArrayList<>()).build();
            when(promptOptimizeTaskService.queryTaskDetailsByIds(any(ArrayList.class))).thenReturn(jiuWenJobDeatails);

            ListPromptTasksQo listPromptTasksQo = new ListPromptTasksQo();

            // When
            PromptBaseResp result = promptEngineerService.listPromptTasks("proj1", listPromptTasksQo);

            // Then: 丢失的 PAUSING 任务被反向检查标记为 FAILED
            assertNotNull(result);
            assertEquals(200, result.getCode());
            verify(promptTaskMapper).updateStatusByPrimaryKey(eq(taskId),
                eq(PromptTaskStatusEnum.FAILED.getCode()), eq("proj1"), any());
            verify(promptTaskMapper).updateMessageByPrimaryKey(eq(taskId), anyString(), eq("proj1"), any());
        }
    }

    @Test
    void test_entity_convert_not_exception() {
        PromptTaskEntity promptTaskEntity = new PromptTaskEntity();
        PromptTaskDetailVo promptTaskDetailVo = promptTaskEntity.convert2PromptTaskDetailVo();
        assertNotNull(promptTaskDetailVo);
    }

}
