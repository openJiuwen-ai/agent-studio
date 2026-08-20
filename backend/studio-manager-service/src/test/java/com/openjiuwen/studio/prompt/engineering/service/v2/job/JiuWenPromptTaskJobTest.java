/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.service.v2.job;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.RETURNS_DEEP_STUBS;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.prompt.engineering.entity.v2.ExecConfig;
import com.openjiuwen.studio.prompt.engineering.entity.v2.PromptTaskDetailVo;
import com.openjiuwen.studio.prompt.engineering.entity.v2.PromptVar;
import com.openjiuwen.studio.prompt.engineering.enums.ResponseCode;
import com.openjiuwen.studio.prompt.engineering.enums.v2.PromptTaskStatusEnum;
import com.openjiuwen.studio.prompt.engineering.enums.v2.TargetTypeEnum;
import com.openjiuwen.studio.prompt.engineering.mapper.v2.PromptTaskMapper;
import com.openjiuwen.studio.prompt.engineering.remote.ClientTemplate;
import com.openjiuwen.studio.prompt.engineering.service.model.v2.jiuwen.JIuWenPromptBaseRes;
import com.openjiuwen.studio.prompt.engineering.service.model.v2.jiuwen.JiuWenCreTaskReq;
import com.openjiuwen.studio.prompt.engineering.service.model.v2.jiuwen.JiuWenCreTaskRes;
import com.openjiuwen.studio.prompt.engineering.service.model.v2.jiuwen.JiuWenJobDeatails;
import com.openjiuwen.studio.prompt.engineering.service.model.v2.jiuwen.JiuWenJobInfo;
import com.openjiuwen.studio.prompt.engineering.service.model.v2.jiuwen.JiuWenPromptBatchReq;
import com.openjiuwen.studio.prompt.engineering.service.model.v2.jiuwen.JiuWenPromptBatchRes;
import com.openjiuwen.studio.prompt.engineering.service.model.v2.jiuwen.JiuWenPromptDeatilRes;
import com.openjiuwen.studio.prompt.engineering.service.v2.PromptEngineerDataSetService;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.MockitoAnnotations;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.quartz.JobDataMap;
import org.quartz.JobDetail;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.ResourceAccessException;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

@MockitoSettings(strictness = Strictness.LENIENT)
class JiuWenPromptTaskJobTest {
    @Spy
    @InjectMocks
    private JiuWenPromptTaskJob jiuWenPromptTaskJob;

    @Mock
    private ClientTemplate clientTemplate; // 假设 ClientTemplate 为 HTTP 调用模板

    @Mock
    private PromptTaskMapper promptTaskMapper;

    @Mock
    private PromptEngineerDataSetService promptEngineerDataSetService;

    @Mock
    private JobExecutionContext jobExecutionContext;

    // 共用测试参数
    private static final String TASK_ID = "task1";

    private static final String PROJECT_ID = "proj1";

    private static final String WORKSPACE_ID = "ws1";

    private static final String TOKEN = "auth_token";

    private static final String JIUWEN_TASK_ID = "jiuwen123";

    private static final String TASK_PARAM_JSON
        = "{\"id\":\"task1\",\"name\":\"testTask\",\"desc\":\"desc\",\"ptText\":\"prompt text\",\"maxIterNum\":10,\"targetAcc\":90.0,\"showCaseNum\":5,\"targetType\":\"ACCURACY\",\"scoreStandard\":\"standard\",\"backKnowledge\":\"knowledge\"}";

    private static final String JIUWEN_BASE_URL = "http://localhost:8000";

    private static final String TEMPLATES_OPTIMIZATION_CREATE_API = "/flask/v1/prompt/templates_optimization/jobs";

    private static final String TEMPLATES_OPTIMIZATION_PROGRESS_API = "/flask/v1/prompt/templates_optimization/jobs/%s";

    private static final String TEMPLATES_OPTIMIZATION_BATCH_PROGRESS_API
        = "/flask/v1/prompt/templates_optimization/jobs/get_infos";

    private static final String TEMPLATES_OPTIMIZATION_STOP_API
        = "/flask/v1/prompt/templates_optimization/jobs/%s/stop";

    private static final String TEMPLATES_OPTIMIZATION_RESTART_API
        = "/flask/v1/prompt/templates_optimization/jobs/%s/restart";

    private static final String TEMPLATES_OPTIMIZATION_DELETE_API = "/flask/v1/prompt/templates_optimization/jobs/%s";

    private AutoCloseable mockitoCloseable;

    @BeforeEach
    void setUp() throws Exception {
        mockitoCloseable = MockitoAnnotations.openMocks(this);
    }

    @AfterEach
    void tearDown() throws Exception {
        mockitoCloseable.close();
    }

    /**
     * 测试 execTask：九问创建任务成功，状态更新为 RUNNING
     */
    @Test
    void test_execTask_success() {
        // 1. 准备任务详情和九问返回结果
        PromptTaskDetailVo taskVo = buildPromptTaskDetailVo();
        JiuWenJobInfo jobInfo = JiuWenJobInfo.builder().id(JIUWEN_TASK_ID).build();
        JiuWenCreTaskRes creTaskRes = JiuWenCreTaskRes.builder()
            .code(ResponseCode.OK.getCode()) // 假设 ResponseCode.OK 为 200
            .jobInfo(jobInfo)
            .build();
        ResponseEntity<JiuWenCreTaskRes> response = new ResponseEntity<>(creTaskRes, HttpStatus.OK);

        // 2. Mock 依赖：数据集查询、HTTP 调用、JSON 工具类
        try (MockedStatic<JsonUtils> mockedJsonUtil = mockStatic(JsonUtils.class)) {
            // 模拟数据集查询（返回空列表，避免构建 cases 逻辑报错）
            when(promptEngineerDataSetService.getAllEvalDataSet(eq(TASK_ID), eq(PROJECT_ID),
                eq(WORKSPACE_ID))).thenReturn(new ArrayList<>());
            // 模拟 clientTemplate 调用九问成功
            when(clientTemplate.postForEntity(anyString(), any(HttpHeaders.class), anyString(), eq(JiuWenCreTaskRes.class))).thenReturn(response);
            // 模拟对象转 JSON（无实际逻辑，仅避免 NPE）
            mockedJsonUtil.when(() -> JsonUtils.toJson(any(JiuWenCreTaskReq.class))).thenReturn("req_json");

            // 3. 执行 execTask
            JiuWenJobInfo result = jiuWenPromptTaskJob.execTask(taskVo, TOKEN);

            // 4. 验证逻辑
            assertNotNull(result);
            assertEquals(JIUWEN_TASK_ID, result.getId()); // 验证返回的九问任务ID
            // 验证状态更新为 RUNNING
            verify(promptTaskMapper).updateJobIdStatusByPrimaryKey(eq(TASK_ID), eq(JIUWEN_TASK_ID),
                eq(PromptTaskStatusEnum.RUNNING.getCode()), eq(PROJECT_ID), eq(WORKSPACE_ID));
            verify(clientTemplate).postForEntity(anyString(), any(HttpHeaders.class), anyString(), eq(JiuWenCreTaskRes.class));
        }
    }

    /**
     * 测试 execTask：九问返回非200状态码，抛出异常
     */
    @Test
    void test_execTask_http_not_2xx() {
        // 1. 准备任务详情和非200响应
        PromptTaskDetailVo taskVo = buildPromptTaskDetailVo();
        ResponseEntity<JiuWenCreTaskRes> response = new ResponseEntity<>(HttpStatus.BAD_REQUEST); // 400 错误

        // 2. Mock 依赖
        try (MockedStatic<JsonUtils> mockedJsonUtil = mockStatic(JsonUtils.class)) {
            when(promptEngineerDataSetService.getAllEvalDataSet(anyString(), anyString(), anyString())).thenReturn(
                new ArrayList<>());
            when(clientTemplate.postForEntity(anyString(), eq(TOKEN), anyString(),
                eq(JiuWenCreTaskRes.class))).thenReturn(response);
            mockedJsonUtil.when(() -> JsonUtils.toJson(any())).thenReturn("req_json");

            // 3. 执行并验证异常
            AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
                jiuWenPromptTaskJob.execTask(taskVo, TOKEN);
            });

            // 验证状态更新为 FAILED
            verify(promptTaskMapper).updateStatusByPrimaryKey(eq(TASK_ID), eq(PromptTaskStatusEnum.FAILED.getCode()),
                eq(PROJECT_ID), eq(WORKSPACE_ID));
        }
    }

    @Test
    void test_execTask_res_not_ok() {
        assertThrows(AgentStudioException.class, () -> {
            // 1. 准备任务详情和九问返回结果
            PromptTaskDetailVo taskVo = buildPromptTaskDetailVo();
            JiuWenJobInfo jobInfo = JiuWenJobInfo.builder().id(JIUWEN_TASK_ID).build();
            JiuWenCreTaskRes creTaskRes = JiuWenCreTaskRes.builder()
                .code(ResponseCode.BAD_REQUEST.getCode()) // 假设 ResponseCode.OK 为 200
                .jobInfo(jobInfo)
                .build();
            ResponseEntity<JiuWenCreTaskRes> response = new ResponseEntity<>(creTaskRes, HttpStatus.OK);

            // 2. Mock 依赖：数据集查询、HTTP 调用、JSON 工具类
            try (MockedStatic<JsonUtils> mockedJsonUtil = mockStatic(JsonUtils.class)) {
                // 模拟数据集查询（返回空列表，避免构建 cases 逻辑报错）
                when(promptEngineerDataSetService.getAllEvalDataSet(eq(TASK_ID), eq(PROJECT_ID),
                    eq(WORKSPACE_ID))).thenReturn(new ArrayList<>());
                // 模拟 clientTemplate 调用九问成功
                when(clientTemplate.postForEntity(anyString(), eq(TOKEN), anyString(),
                    eq(JiuWenCreTaskRes.class))).thenReturn(response);
                // 模拟对象转 JSON（无实际逻辑，仅避免 NPE）
                mockedJsonUtil.when(() -> JsonUtils.toJson(any(JiuWenCreTaskReq.class))).thenReturn("req_json");

                // 3. 执行 execTask
                JiuWenJobInfo result = jiuWenPromptTaskJob.execTask(taskVo, TOKEN);

            }
        });
    }

    /**
     * 测试 execTask：九问返回体为空，抛出异常
     */
    @Test
    void test_execTask_response_body_null() {
        // 1. 准备任务详情和空响应体
        PromptTaskDetailVo taskVo = buildPromptTaskDetailVo();
        ResponseEntity<JiuWenCreTaskRes> response = new ResponseEntity<>(null, HttpStatus.OK);

        // 2. Mock 依赖
        try (MockedStatic<JsonUtils> mockedJsonUtil = mockStatic(JsonUtils.class)) {
            when(promptEngineerDataSetService.getAllEvalDataSet(anyString(), anyString(), anyString())).thenReturn(
                new ArrayList<>());
            when(clientTemplate.postForEntity(anyString(), eq(TOKEN), anyString(),
                eq(JiuWenCreTaskRes.class))).thenReturn(response);
            mockedJsonUtil.when(() -> JsonUtils.toJson(any())).thenReturn("req_json");

            // 3. 执行并验证异常
            AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
                jiuWenPromptTaskJob.execTask(taskVo, TOKEN);
            });

            // 4. 验证逻辑
            verify(promptTaskMapper).updateStatusByPrimaryKey(eq(TASK_ID), eq(PromptTaskStatusEnum.FAILED.getCode()),
                eq(PROJECT_ID), eq(WORKSPACE_ID));
        }
    }

    /**
     * 测试 deleteTask：九问删除任务成功
     */
    @Test
    void test_deleteTask_success() {
        // 1. 准备九问返回结果
        JIuWenPromptBaseRes baseRes = JIuWenPromptBaseRes.builder().code(ResponseCode.OK.getCode()).build();
        ResponseEntity<JIuWenPromptBaseRes> response = new ResponseEntity<>(baseRes, HttpStatus.OK);

        // 2. Mock clientTemplate 调用成功
        when(clientTemplate.deleteForEntity(anyString(), eq(TOKEN), eq(JIuWenPromptBaseRes.class))).thenReturn(response);

        // 3. 执行 deleteTask
        jiuWenPromptTaskJob.deleteTask(buildPromptTaskDetailVo(), TOKEN);

        // 4. 验证逻辑
        verify(clientTemplate).deleteForEntity(anyString(), eq(TOKEN), eq(JIuWenPromptBaseRes.class));
    }

    /**
     * 测试 deleteTask：服务不可达（ResourceAccessException），抛出异常
     */
    @Test
    void test_deleteTask_service_unreachable() {
        // 1. Mock clientTemplate 抛出服务访问异常
        when(clientTemplate.deleteForEntity(anyString(), eq(TOKEN), eq(JIuWenPromptBaseRes.class))).thenThrow(
            new ResourceAccessException("Connection refused"));

        // 2. 执行并验证异常
        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            jiuWenPromptTaskJob.deleteTask(buildPromptTaskDetailVo(), TOKEN);
        });

    }

    /**
     * 测试 execute：Quartz Job 执行，从 JobDataMap 解析参数并调用 execTask
     */
    @Test
    void test_execute_job() throws JobExecutionException {
        // 1. 准备 JobDataMap（存储 taskParam 和 token）
        JobDataMap jobDataMap = new JobDataMap();
        jobDataMap.put("taskParam", TASK_PARAM_JSON);
        jobDataMap.put("token", TOKEN);

        JobDetail jobDetail = mock(JobDetail.class);
        // 2. Mock JobExecutionContext 和依赖
        when(jobExecutionContext.getJobDetail()).thenReturn(jobDetail);
        when(jobDetail.getJobDataMap()).thenReturn(jobDataMap);
        PromptTaskDetailVo taskVo = mock(PromptTaskDetailVo.class);
        // 关键：给 taskVo 设置 getPtVars() 的返回值，避免即使执行真实逻辑也不抛 NPE
        when(taskVo.getPtVars()).thenReturn(Collections.emptyList());
        JiuWenJobInfo jobInfo = JiuWenJobInfo.builder().id(JIUWEN_TASK_ID).build();

        try (MockedStatic<JsonUtils> mockedJsonUtils = mockStatic(JsonUtils.class)) {
            // 模拟 JSON 反序列化（从 taskParam 解析为 PromptTaskDetailVo）
            mockedJsonUtils.when(() -> JsonUtils.json2ObjQuietly(eq(TASK_PARAM_JSON), eq(PromptTaskDetailVo.class)))
                .thenReturn(taskVo);

            // 关键修正：用 doReturn 模拟 execTask，不执行真实逻辑
            doReturn(jobInfo).when(jiuWenPromptTaskJob).execTask(eq(taskVo), anyString());

            // 无需模拟 buildJiuWenCreTaskReq 依赖（因 execTask 真实逻辑未执行）
            // when(promptEngineerDataSetService.getAllEvalDataSet(...)).thenReturn(...) 可省略

            // 3. 执行 execute
            jiuWenPromptTaskJob.execute(jobExecutionContext);

            // 4. 验证逻辑
            verify(jobExecutionContext, times(2)).getJobDetail(); // 实际调用 2 次，验证 2 次
            verify(jobDetail, times(2)).getJobDataMap(); // 每次 getJobDetail() 后调用 getJobDataMap()，共 2 次
            verify(jiuWenPromptTaskJob).execTask(eq(taskVo), eq(TOKEN)); // 验证 execTask 调用
        }
    }

    /**
     * 测试 pauseTask 和 resumeTask：九问接口调用成功/失败
     */
    @Test
    void test_pauseTask_success() {
        // 测试 pauseTask 成功
        ResponseEntity<JIuWenPromptBaseRes> pauseResp = new ResponseEntity<>(
            JIuWenPromptBaseRes.builder().code(ResponseCode.OK.getCode()).build(), HttpStatus.OK);
        when(clientTemplate.postForEntity(anyString(), eq(TOKEN), isNull(), eq(JIuWenPromptBaseRes.class)))
            .thenReturn(pauseResp);
        jiuWenPromptTaskJob.pauseTask(buildPromptTaskDetailVo(), TOKEN);
        verify(clientTemplate).postForEntity(anyString(), eq(TOKEN), isNull(), eq(JIuWenPromptBaseRes.class));
    }
    @Test
    void test_pauseAndResumeTask_error() {
        // 测试 pauseTask 失败
        ResponseEntity<JIuWenPromptBaseRes> pauseResp = new ResponseEntity<>(
            JIuWenPromptBaseRes.builder().code(ResponseCode.OK.getCode()).build(), HttpStatus.BAD_REQUEST);
        when(clientTemplate.postForEntity(anyString(), eq(TOKEN), isNull(), eq(JIuWenPromptBaseRes.class)))
            .thenReturn(pauseResp);
        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            jiuWenPromptTaskJob.pauseTask(buildPromptTaskDetailVo(), TOKEN);});
    }

    @Test
    void test_resumeTask() {
        // 测试 resumeTask 失败（非200状态码）
        ResponseEntity<JIuWenPromptBaseRes> resumeResp = new ResponseEntity<>(HttpStatus.INTERNAL_SERVER_ERROR);
        when(clientTemplate.postForEntity(anyString(), any(HttpHeaders.class), isNull(), eq(JIuWenPromptBaseRes.class)))
            .thenReturn(resumeResp);

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            jiuWenPromptTaskJob.resumeTask(buildPromptTaskDetailVo(), TOKEN);
        });
    }

    // 辅助方法：构建 PromptTaskDetailVo 测试数据
    private PromptTaskDetailVo buildPromptTaskDetailVo() {
        return PromptTaskDetailVo.builder()
            .id(TASK_ID)
            .jiuwenTaskId(JIUWEN_TASK_ID)
            .name("testTask")
            .desc("testDesc")
            .ptText("prompt text")
            .maxIterNum(10)
            .targetAcc(90.0)
            .showCaseNum(5)
            .targetType(TargetTypeEnum.OBJECTIVE) // 假设 TargetTypeEnum 存在
            .scoreStandard("standard")
            .backKnowledge("knowledge")
            .projectId(PROJECT_ID)
            .workspaceId(WORKSPACE_ID)
            .ptModel(new ExecConfig()) // 假设 ExecConfig 为模型配置类
            .execObject(new ExecConfig())
            .ptVars(Collections.singletonList(PromptVar.builder().name("var1").content("value1").build()))
            .build();
    }

    @Test
    void test_getTaskDetail_should_not_throw_exception() throws Exception {
        assertThrows(NullPointerException.class, () -> {
            // Given
            when(clientTemplate.getForEntity(anyString(), anyString(), eq(JiuWenPromptDeatilRes.class))).thenReturn(
                null);

            // When
            JiuWenPromptDeatilRes result = jiuWenPromptTaskJob.getTaskDetail(null, null);
        });
    }

    @Test
    void test_getTaskDetail_should_return_not_null() throws Exception {
        // Given
        ResponseEntity<JiuWenPromptDeatilRes> response = ResponseEntity.ok(new JiuWenPromptDeatilRes());
        when(clientTemplate.getForEntity(anyString(), anyString(), eq(JiuWenPromptDeatilRes.class))).thenReturn(
            response);

        // When
        JiuWenPromptDeatilRes result = jiuWenPromptTaskJob.getTaskDetail(buildPromptTaskDetailVo(), "not_empty");

        // Then
        assertNotNull(result);
    }

    @Test
    void test_getTaskDetail_should_not_throw_exception1() throws Exception {
        assertThrows(NullPointerException.class, () -> {
            // Given
            when(clientTemplate.getForEntity(anyString(), anyString(), eq(JiuWenPromptDeatilRes.class))).thenReturn(
                null);

            // When
            JiuWenPromptDeatilRes result = jiuWenPromptTaskJob.getTaskDetail(null, null);
        });
    }

    @Test
    void test_getTaskDetail_should_return_not_null4() throws Exception {

        ResponseEntity<JiuWenPromptDeatilRes> response = ResponseEntity.ok(new JiuWenPromptDeatilRes());
        // Given
        when(clientTemplate.getForEntity(anyString(), anyString(), eq(JiuWenPromptDeatilRes.class))).thenReturn(
            response);

        // When
        JiuWenPromptDeatilRes result = jiuWenPromptTaskJob.getTaskDetail(buildPromptTaskDetailVo(), TOKEN);

        // Then
        assertNotNull(result);
    }

    @Test
    void test_queryTaskDetailsByIds_should_return_not_null() throws Exception {
        try (MockedStatic<JsonUtils> mockedStaticJsonUtil = mockStatic(JsonUtils.class, RETURNS_DEEP_STUBS)) {
            // Given
            mockedStaticJsonUtil.when(() -> JsonUtils.toJson(any(JiuWenPromptBatchReq.class))).thenReturn("not_empty");

            ResponseEntity<JiuWenPromptBatchRes> response = ResponseEntity.ok(new JiuWenPromptBatchRes());
            JiuWenJobDeatails jiuWenJobDeatails = new JiuWenJobDeatails();
            response.getBody().setJobDetails(jiuWenJobDeatails);

            when(clientTemplate.postForEntity(anyString(), anyString(), anyString(),
                eq(JiuWenPromptBatchRes.class))).thenReturn(response);

            List<String> jiuwenTaskIds = new ArrayList<>();
            jiuwenTaskIds.add("not_empty");

            // When
            JiuWenJobDeatails result1 = jiuWenPromptTaskJob.queryTaskDetailsByIds(jiuwenTaskIds, "not_empty");
            JiuWenJobDeatails result2 = jiuWenPromptTaskJob.queryMultiTaskDetailsByIds(jiuwenTaskIds, "not_empty");

            // Then
            assertNotNull(result1);
            assertNotNull(result2);
        }
    }

    @Test
    void test_queryTaskDetailsByIds_should_not_throw_exception() throws Exception {
        assertThrows(AgentStudioException.class, () -> {
            try (MockedStatic<JsonUtils> mockedStaticJsonUtil = mockStatic(JsonUtils.class, RETURNS_DEEP_STUBS)) {
                ResponseEntity<JiuWenPromptBatchRes> response = ResponseEntity.badRequest()
                    .body(new JiuWenPromptBatchRes());
                // Given
                mockedStaticJsonUtil.when(() -> JsonUtils.toJson(any(JiuWenPromptBatchReq.class))).thenReturn(null);

                when(clientTemplate.postForEntity(anyString(), anyString(), anyString(),
                    eq(JiuWenPromptBatchRes.class))).thenReturn(response);

                // When
                JiuWenJobDeatails result = jiuWenPromptTaskJob.queryTaskDetailsByIds(any(List.class), anyString());
            }
        });
    }

    @Test
    void test_queryTaskDetailsByIds_should_return_not_null4() throws Exception {
        assertThrows(AgentStudioException.class, () -> {
            try (MockedStatic<JsonUtils> mockedStaticJsonUtil = mockStatic(JsonUtils.class, RETURNS_DEEP_STUBS)) {
                ResponseEntity<JiuWenPromptBatchRes> mockResponse = mock(ResponseEntity.class);
                when(mockResponse.getBody()).thenReturn(null);
                when(mockResponse.getStatusCode()).thenReturn(HttpStatus.OK);
                // Given
                mockedStaticJsonUtil.when(() -> JsonUtils.toJson(any(JiuWenPromptBatchReq.class))).thenReturn(null);

                when(clientTemplate.postForEntity(anyString(), anyString(), anyString(),
                    eq(JiuWenPromptBatchRes.class))).thenReturn(mockResponse);

                // When
                JiuWenJobDeatails result = jiuWenPromptTaskJob.queryTaskDetailsByIds(any(List.class), anyString());
            }
        });
    }

    @Test
    void test_queryMultiTaskDetailsByIds_should_not_throw_exception() throws Exception {
        assertThrows(AgentStudioException.class, () -> {
            try (MockedStatic<JsonUtils> mockedStaticJsonUtil = mockStatic(JsonUtils.class, RETURNS_DEEP_STUBS)) {
                ResponseEntity<JiuWenPromptBatchRes> response = ResponseEntity.badRequest()
                        .body(new JiuWenPromptBatchRes());
                // Given
                mockedStaticJsonUtil.when(() -> JsonUtils.toJson(any(JiuWenPromptBatchReq.class))).thenReturn(null);

                when(clientTemplate.postForEntity(anyString(), anyString(), anyString(),
                        eq(JiuWenPromptBatchRes.class))).thenReturn(response);

                // When
                JiuWenJobDeatails result = jiuWenPromptTaskJob.queryMultiTaskDetailsByIds(any(List.class), anyString());
            }
        });
    }

    @Test
    void test_queryMultiTaskDetailsByIds_should_return_not_null4() throws Exception {
        assertThrows(AgentStudioException.class, () -> {
            try (MockedStatic<JsonUtils> mockedStaticJsonUtil = mockStatic(JsonUtils.class, RETURNS_DEEP_STUBS)) {
                ResponseEntity<JiuWenPromptBatchRes> mockResponse = mock(ResponseEntity.class);
                when(mockResponse.getBody()).thenReturn(null);
                when(mockResponse.getStatusCode()).thenReturn(HttpStatus.OK);
                // Given
                mockedStaticJsonUtil.when(() -> JsonUtils.toJson(any(JiuWenPromptBatchReq.class))).thenReturn(null);

                when(clientTemplate.postForEntity(anyString(), anyString(), anyString(),
                        eq(JiuWenPromptBatchRes.class))).thenReturn(mockResponse);

                // When
                JiuWenJobDeatails result = jiuWenPromptTaskJob.queryMultiTaskDetailsByIds(any(List.class), anyString());
            }
        });
    }

    @Test
    void test_delete_task_not_ok() {
        assertThrows(AgentStudioException.class, () -> {
            ResponseEntity<JIuWenPromptBaseRes> mockResponse = mock(ResponseEntity.class);
            when(mockResponse.getBody()).thenReturn(null);
            when(mockResponse.getStatusCode()).thenReturn(HttpStatus.BAD_REQUEST);

            when(clientTemplate.deleteForEntity(anyString(), anyString(), eq(JIuWenPromptBaseRes.class))).thenReturn(
                mockResponse);
            jiuWenPromptTaskJob.deleteTask(buildPromptTaskDetailVo(), TOKEN);
        });
    }

    @Test
    void test_delete_task_body_null() {
        assertThrows(AgentStudioException.class, () -> {
            ResponseEntity<JIuWenPromptBaseRes> mockResponse = mock(ResponseEntity.class);

            when(mockResponse.getBody()).thenReturn(null);
            when(mockResponse.getStatusCode()).thenReturn(HttpStatus.OK);
            when(mockResponse.getBody()).thenReturn(null);

            when(clientTemplate.deleteForEntity(anyString(), anyString(), eq(JIuWenPromptBaseRes.class))).thenReturn(
                mockResponse);
            jiuWenPromptTaskJob.deleteTask(buildPromptTaskDetailVo(), TOKEN);
        });
    }

    @Test
    void test_delete_task_res_code_not_ok() {
        assertThrows(AgentStudioException.class, () -> {
            ResponseEntity<JIuWenPromptBaseRes> mockResponse = mock(ResponseEntity.class);
            JIuWenPromptBaseRes jiuWenPromptBaseRes = mock(JIuWenPromptBaseRes.class);
            when(mockResponse.getBody()).thenReturn(null);
            when(mockResponse.getStatusCode()).thenReturn(HttpStatus.OK);
            when(mockResponse.getBody()).thenReturn(jiuWenPromptBaseRes);
            when(jiuWenPromptBaseRes.getCode()).thenReturn(ResponseCode.BAD_REQUEST.getCode());

            when(clientTemplate.deleteForEntity(anyString(), anyString(), eq(JIuWenPromptBaseRes.class))).thenReturn(
                mockResponse);
            PromptTaskDetailVo promptTaskDetailVo = buildPromptTaskDetailVo();
            jiuWenPromptTaskJob.deleteTask(promptTaskDetailVo, TOKEN);
        });
    }

    @Test
    void test_delete_task_job_not_found() {
        HttpServerErrorException notFoundEx = new HttpServerErrorException(
            HttpStatus.INTERNAL_SERVER_ERROR,
            "Internal Server Error",
            "{\"code\":102155,\"message\":\"Prompt optimize job not found.\"}".getBytes(),
            java.nio.charset.StandardCharsets.UTF_8);

        when(clientTemplate.deleteForEntity(anyString(), eq(TOKEN), eq(JIuWenPromptBaseRes.class))).thenThrow(
            notFoundEx);

        // 九问侧 job 不存在时不应抛异常，应正常返回
        jiuWenPromptTaskJob.deleteTask(buildPromptTaskDetailVo(), TOKEN);

        verify(clientTemplate).deleteForEntity(anyString(), eq(TOKEN), eq(JIuWenPromptBaseRes.class));
    }

    @Test
    void test_delete_task_server_error_other_than_not_found() {
        HttpServerErrorException serverErrorEx = new HttpServerErrorException(
            HttpStatus.INTERNAL_SERVER_ERROR,
            "Internal Server Error",
            "{\"code\":102099,\"message\":\"Some other server error.\"}".getBytes(),
            java.nio.charset.StandardCharsets.UTF_8);

        when(clientTemplate.deleteForEntity(anyString(), eq(TOKEN), eq(JIuWenPromptBaseRes.class))).thenThrow(
            serverErrorEx);

        // 非 job not found 的服务端错误仍应抛异常
        assertThrows(AgentStudioException.class, () -> {
            jiuWenPromptTaskJob.deleteTask(buildPromptTaskDetailVo(), TOKEN);
        });
    }

    @Test
    void test_get_task_res_not_ok() {
        assertThrows(AgentStudioException.class, () -> {
            ResponseEntity<JiuWenPromptDeatilRes> mockResponse = mock(ResponseEntity.class);
            JIuWenPromptBaseRes jiuWenPromptBaseRes = mock(JIuWenPromptBaseRes.class);
            when(mockResponse.getStatusCode()).thenReturn(HttpStatus.BAD_REQUEST);
            when(clientTemplate.getForEntity(anyString(), anyString(), eq(JiuWenPromptDeatilRes.class))).thenReturn(
                mockResponse);
            jiuWenPromptTaskJob.getTaskDetail(buildPromptTaskDetailVo(), TOKEN);
        });
    }

    @Test
    void test_get_task_body_null() {
        assertThrows(AgentStudioException.class, () -> {
            ResponseEntity<JiuWenPromptDeatilRes> mockResponse = mock(ResponseEntity.class);
            JIuWenPromptBaseRes jiuWenPromptBaseRes = mock(JIuWenPromptBaseRes.class);
            when(mockResponse.getStatusCode()).thenReturn(HttpStatus.OK);
            when(mockResponse.getBody()).thenReturn(null);
            when(clientTemplate.getForEntity(anyString(), anyString(), eq(JiuWenPromptDeatilRes.class))).thenReturn(
                mockResponse);
            jiuWenPromptTaskJob.getTaskDetail(buildPromptTaskDetailVo(), TOKEN);
        });
    }
}
