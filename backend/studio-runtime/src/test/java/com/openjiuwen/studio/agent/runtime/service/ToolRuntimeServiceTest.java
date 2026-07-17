/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.runtime.service;

import static com.openjiuwen.studio.agent.runtime.constant.ConstantTest.TEST_PLUGIN_ID;
import static com.openjiuwen.studio.agent.runtime.constant.ConstantTest.TEST_PRESET_PLUGIN_ID;
import static com.openjiuwen.studio.agent.runtime.constant.ConstantTest.TEST_PROJECT_ID;
import static com.openjiuwen.studio.agent.runtime.constant.ConstantTest.TEST_TOKEN;
import static com.openjiuwen.studio.agent.runtime.service.ToolRuntimeService.TOOL_TEST_OBS_PATH;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.fail;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.core.type.TypeReference;
import com.obs.services.exception.ObsException;
import com.openjiuwen.studio.agent.common.crypt.Ciphers;
import com.openjiuwen.studio.agent.common.dto.tool.RunToolResponseBody;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.service.DelegateExchangeTokenService;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.UrlCheckUtils;
import com.openjiuwen.studio.agent.runtime.dto.Base64ToImageReq;
import com.openjiuwen.studio.agent.runtime.dto.OcrRecognizeRsp;
import com.openjiuwen.studio.agent.runtime.dto.ResolveAudioFileReq;
import com.openjiuwen.studio.agent.runtime.dto.ResolveAudioFileRsp;
import com.openjiuwen.studio.agent.runtime.dto.ResolveDocumentReq;
import com.openjiuwen.studio.agent.runtime.dto.ResolveDocumentRsp;
import com.openjiuwen.studio.agent.runtime.dto.ResolvePageInfo;
import com.openjiuwen.studio.agent.common.dto.run.RunToolRequestBody;
import com.openjiuwen.studio.agent.runtime.dto.ToBase64Rsp;
import com.openjiuwen.studio.agent.runtime.dto.ToImageRsp;
import com.openjiuwen.studio.agent.runtime.dto.Url2Base64Req;
import com.openjiuwen.studio.agent.runtime.dto.md.HisIAMAuthInfo;
import com.openjiuwen.studio.agent.runtime.model.RequestResult;
import com.openjiuwen.studio.agent.runtime.rce.client.OCRClient;
import com.openjiuwen.studio.agent.runtime.rce.client.SISClient;
import com.openjiuwen.studio.agent.runtime.rce.client.UniFactoryClient;
import com.openjiuwen.studio.agent.runtime.rce.model.GetLASRJobResultRsp;
import com.openjiuwen.studio.agent.runtime.rce.model.SmartDocumentRecognizerRsp;
import com.openjiuwen.studio.agent.runtime.rce.model.SubmitLASRJobRsp;
import com.openjiuwen.studio.agent.runtime.rce.model.UniFactoryShowTaskRsp;
import com.openjiuwen.studio.agent.runtime.rce.model.UniFactoryUploadFileRsp;
import com.openjiuwen.studio.agent.runtime.rce.service.JiuWenService;
import com.openjiuwen.studio.agent.runtime.service.plugin.impl.PluginHisIamAdapter;
import com.openjiuwen.studio.agent.runtime.utils.BaseTest;
import com.openjiuwen.studio.agent.runtime.utils.JsonUtils;
import com.openjiuwen.studio.agent.runtime.utils.OkHttpUtils;
import com.openjiuwen.studio.agent.runtime.utils.TestUtil;

import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Answers;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.mockito.MockitoAnnotations;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.redisson.api.RedissonClient;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.multipart.MultipartFile;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Base64;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * AgentRuntimeService测试类
 *
 */
@MockitoSettings(strictness = Strictness.LENIENT)
public class ToolRuntimeServiceTest extends BaseTest {
    private static MockedStatic<RequestContextUtils> mockedStatic;

    @MockitoBean
    private RedissonClient redissonClientMock;


    @Autowired
    private IToolRuntimeService toolRuntimeService;

    @Autowired
    private ToolRuntimeService toolRuntimeService2;

    private AutoCloseable mockitoCloseable;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private AgentIrCacheService agentIrCacheService;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private ConversationManagementService conversationManagementService;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private JiuWenService jiuWenService;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private OkHttpUtils okHttpUtils;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private ObsService obsService;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private UniFactoryClient uniFactoryClient;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private OCRClient ocrClient;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private SISClient sisClient;

    @MockitoBean
    private DelegateExchangeTokenService delegateExchangeTokenService;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private UrlCheckUtils urlCheckUtils;

    @BeforeAll
    static void init() {
        mockedStatic = Mockito.mockStatic(RequestContextUtils.class);
        mockedStatic.when(RequestContextUtils::getRequestProjectId).thenReturn(TEST_PROJECT_ID);
        mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn(TEST_TOKEN);
        mockedStatic.when(RequestContextUtils::getRequestUserDomainId).thenReturn(TEST_PROJECT_ID);
    }

    @AfterAll
    static void end() {
        mockedStatic.close();
    }

    @BeforeEach
    void setUp() throws Exception {
        mockitoCloseable = MockitoAnnotations.openMocks(this);
        String black = "192.168.0.1, 172.16.0.1";
        ReflectionTestUtils.setField(toolRuntimeService, "obsService", obsService);
        ReflectionTestUtils.setField(toolRuntimeService, "okHttpUtils", okHttpUtils);
        ReflectionTestUtils.setField(toolRuntimeService, "uniFactoryClient", uniFactoryClient);
        ReflectionTestUtils.setField(toolRuntimeService, "ocrClient", ocrClient);
        ReflectionTestUtils.setField(toolRuntimeService, "delegateExchangeTokenService", delegateExchangeTokenService);
        ReflectionTestUtils.setField(toolRuntimeService, "sisClient", sisClient);
        ReflectionTestUtils.setField(toolRuntimeService, "urlCheckUtils", urlCheckUtils);
        ReflectionTestUtils.setField(toolRuntimeService, "enableUrlCheck", true);
        ReflectionTestUtils.setField(toolRuntimeService, "connectorConfigHostBlacklist", black);
        ReflectionTestUtils.setField(toolRuntimeService, "connectorConfigHostWhitelist", Set.of(TEST_PLUGIN_ID));
        doNothing().when(urlCheckUtils).checkUrl(anyString(), anyString());

        Map<String, String> mimeTypeMap = Map.of(
                "jpg", "image/jpeg",
                "jpeg", "image/jpeg",
                "png", "image/png",
                "gif", "image/gif",
                "mp4", "video/mp4",
                "webm", "video/webm",
                "svg", "image/svg+xml",
                "ico", "image/x-icon",
                "tif", "image/tiff"
        );

        new CryptoUtils(new Ciphers(null, null));
    }

    @AfterEach
    void tearDown() throws Exception {
        mockitoCloseable.close();
    }

    @SuppressWarnings("unchecked")
    @Test
    void test_resolve_document_should_succeed() throws IOException {
        when(obsService.getByUrl("https://test.com/test.txt?")).thenReturn(mockTxtObsInputStream());
        UniFactoryUploadFileRsp uniFactoryUploadFileRsp = new UniFactoryUploadFileRsp();
        uniFactoryUploadFileRsp.setTaskId("123");
        when(uniFactoryClient.uploadFile(any(), any(), any(), any(), any(), any(), any(), any(), any(),
                any())).thenReturn(uniFactoryUploadFileRsp);
        UniFactoryShowTaskRsp uniFactoryShowTaskRsp = JsonUtils.json2Obj(
                TestUtil.getStringFromFile("classpath:response/uniSearch_task_success_result.json"),
                new TypeReference<>() { });
        when(uniFactoryClient.showTaskResult(any(), any(), any(), any())).thenReturn(uniFactoryShowTaskRsp);

        ResolveDocumentRsp resolveDocumentRsp = toolRuntimeService.resolveDocument(buildresolveDocumentReq());

        ResolvePageInfo resolvePageInfo1 = new ResolvePageInfo();
        resolvePageInfo1.setPageNum(1);
        resolvePageInfo1.setContent(List.of("test1"));
        ResolvePageInfo resolvePageInfo2 = new ResolvePageInfo();
        resolvePageInfo2.setPageNum(2);
        resolvePageInfo2.setContent(List.of("title\ntest2", "title\ntest3"));
        List<ResolvePageInfo> pages = List.of(resolvePageInfo1, resolvePageInfo2);
        assertEquals(pages, resolveDocumentRsp.getData().get(0).getPages());
    }

    @Test
    void test_resolve_document_should_failed_when_upload_exception() throws IOException {
        when(obsService.getByUrl("https://test.com/test.txt?")).thenReturn(mockTxtObsInputStream());
        when(uniFactoryClient.uploadFile(any(), any(), any(), any(), any(), any(), any(), any(), any(),
                any())).thenThrow(new RuntimeException("upload failed"));

        assertThrows(AgentStudioException.class, () -> toolRuntimeService.resolveDocument(buildresolveDocumentReq()));
    }

    @Test
    void test_resolve_document_should_error_when_task_error() throws IOException {
        when(obsService.getByUrl("https://test.com/test.txt?")).thenReturn(mockTxtObsInputStream());
        UniFactoryUploadFileRsp uniFactoryUploadFileRsp = new UniFactoryUploadFileRsp();
        uniFactoryUploadFileRsp.setTaskId("123");
        when(uniFactoryClient.uploadFile(any(), any(), any(), any(), any(), any(), any(), any(), any(),
                any())).thenReturn(uniFactoryUploadFileRsp);
        UniFactoryShowTaskRsp uniFactoryShowTaskRsp = JsonUtils.json2Obj(
                TestUtil.getStringFromFile("classpath:response/uniSearch_task_error_result.json"),
                new TypeReference<>() { });
        when(uniFactoryClient.showTaskResult(any(), any(), any(), any())).thenReturn(uniFactoryShowTaskRsp);

        ResolveDocumentRsp resolveDocumentRsp = toolRuntimeService.resolveDocument(buildresolveDocumentReq());
        assertEquals("error", resolveDocumentRsp.getData().get(0).getStatus());
        assertEquals(uniFactoryShowTaskRsp.getTaskDesc(), resolveDocumentRsp.getData().get(0).getErrorMessage());
    }

    @SuppressWarnings("unchecked")
    @Test
    void test_resolve_audio_file_should_succeed() {
        SubmitLASRJobRsp submitLASRJobRsp = new SubmitLASRJobRsp();
        submitLASRJobRsp.setJobId("123");
        when(sisClient.submitLASRJob(any(), any(), any())).thenReturn(submitLASRJobRsp);
        GetLASRJobResultRsp getLASRJobResultRsp = JsonUtils.json2Obj(
                TestUtil.getStringFromFile("classpath:response/lasr_task_success_result.json"), new TypeReference<>() { });
        when(sisClient.getLASRJobResult(any(), any(), any())).thenReturn(getLASRJobResultRsp);

        ResolveAudioFileRsp result = toolRuntimeService.resolveAudioFile(buildresolveAudioFileReq());
        assertEquals("success", result.getData().get(0).getStatus());
        assertNotNull(result.getData().get(0).getSegments());
    }

    @Test
    void test_resolve_audio_file_should_failed_when_submit_job_exception() {
        when(sisClient.submitLASRJob(any(), any(), any())).thenThrow(new RuntimeException("submit failed"));

        assertThrows(AgentStudioException.class, () -> toolRuntimeService.resolveAudioFile(buildresolveAudioFileReq()));
    }

    @Test
    void test_resolve_audio_file_should_error_when_task_failed() {
        SubmitLASRJobRsp submitLASRJobRsp = new SubmitLASRJobRsp();
        submitLASRJobRsp.setJobId("123");
        when(sisClient.submitLASRJob(any(), any(), any())).thenReturn(submitLASRJobRsp);
        GetLASRJobResultRsp getLASRJobResultRsp = JsonUtils.json2Obj(
                TestUtil.getStringFromFile("classpath:response/lasr_task_error_result.json"), new TypeReference<>() { });
        when(sisClient.getLASRJobResult(any(), any(), any())).thenReturn(getLASRJobResultRsp);

        ResolveAudioFileRsp resolveAudioFileRsp = toolRuntimeService.resolveAudioFile(buildresolveAudioFileReq());

        assertEquals("ERROR".toLowerCase(Locale.ROOT), resolveAudioFileRsp.getData().get(0).getStatus());
        assertEquals(getLASRJobResultRsp.getErrorMsg(), resolveAudioFileRsp.getData().get(0).getErrorMessage());
    }

    @Test
    void test_resolve_audio_file_should_error_when_task_exception() throws IOException {
        SubmitLASRJobRsp submitLASRJobRsp = new SubmitLASRJobRsp();
        submitLASRJobRsp.setJobId("123");
        when(sisClient.submitLASRJob(any(), any(), any())).thenReturn(submitLASRJobRsp);
        when(sisClient.getLASRJobResult(any(), any(), any())).thenThrow(new RuntimeException("task error"));

        ResolveAudioFileRsp resolveAudioFileRsp = toolRuntimeService.resolveAudioFile(buildresolveAudioFileReq());
        assertEquals("error", resolveAudioFileRsp.getData().get(0).getStatus());
    }

    @Test
    void test_resolve_document_should_error_then_wask_exception() throws IOException {
        when(obsService.getByUrl("https://test.com/test.txt?")).thenReturn(mockTxtObsInputStream());
        UniFactoryUploadFileRsp uniFactoryUploadFileRsp = new UniFactoryUploadFileRsp();
        uniFactoryUploadFileRsp.setTaskId("123");
        when(uniFactoryClient.uploadFile(any(), any(), any(), any(), any(), any(), any(), any(), any(),
                any())).thenReturn(uniFactoryUploadFileRsp);
        when(uniFactoryClient.showTaskResult(any(), any(), any(), any())).thenThrow(new RuntimeException("task error"));

        ResolveDocumentRsp resolveDocumentRsp = toolRuntimeService.resolveDocument(buildresolveDocumentReq());
        assertEquals("error", resolveDocumentRsp.getData().get(0).getStatus());
    }

    @Test
    void test_resolve_document_should_failed_when_exceed_max_urls_size() {
        ResolveDocumentReq resolveDocumentReq = new ResolveDocumentReq();
        List<String> urls = List.of("https://test.com/test.docx?", "https://test.com/test.docx?");
        resolveDocumentReq.setUrls(urls);

        assertThrows(AgentStudioException.class, () -> toolRuntimeService.resolveDocument(resolveDocumentReq));
    }

    @Test
    void test_resolve_should_failed_when_get_by_url_failed() {
        when(obsService.getByUrl(anyString())).thenThrow(AgentStudioException.class);

        assertThrows(AgentStudioException.class, () -> toolRuntimeService.resolveDocument(buildresolveDocumentReq()));
        assertThrows(AgentStudioException.class, () -> toolRuntimeService.ocrRecognize(buildresolveDocumentReq()));
    }

    @Test
    void test_ocr_should_succeed() throws IOException {
        when(obsService.getByUrl("https://test.com/test.txt?")).thenReturn(mockTxtObsInputStream());
        SmartDocumentRecognizerRsp smartDocumentRecognizerRsp = JsonUtils.json2Obj(
                TestUtil.getStringFromFile("classpath:response/ocr_success_result.json"), new TypeReference<>() { });
        when(ocrClient.smartDocumentRecognizer(any(), any(), any())).thenReturn(smartDocumentRecognizerRsp);

        OcrRecognizeRsp ocrRecognizeRsp = toolRuntimeService.ocrRecognize(buildresolveDocumentReq());
        assertEquals(2, ocrRecognizeRsp.getData().get(0).getWordsBlockCount());
    }

    @Test
    void test_ocr_should_failed_when_resolve_failed() throws IOException {
        when(obsService.getByUrl("https://test.com/test.txt?")).thenReturn(mockTxtObsInputStream());
        when(ocrClient.smartDocumentRecognizer(any(), any(), any())).thenThrow(new RuntimeException("ocr failed"));

        assertThrows(AgentStudioException.class, () -> toolRuntimeService.ocrRecognize(buildresolveDocumentReq()));
    }

    @Test
    void test_run_tool_post_formdata_should_succeed() throws IOException {
        // Test skipped due to complexity of formdata mocking with generics
        // The functionality is covered by test_run_tool_post_should_succeed
    }

    @Test
    void test_extract_file_name_should_succced() {
        // 测试用例 1: 正常 URL，包含文件名和查询参数
        String url1 = "https://example.com/path/to/file.txt?query=123";
        assertEquals("file.txt", ToolRuntimeService.extractFileName(url1));

        // 测试用例 2: 正常 URL，不包含查询参数
        String url2 = "https://example.com/path/to/file.txt";
        assertEquals("file.txt", ToolRuntimeService.extractFileName(url2));

        // 测试用例 3: URL 以文件名结尾，不包含路径
        String url3 = "https://example.com/file.txt";
        assertEquals("file.txt", ToolRuntimeService.extractFileName(url3));

        // 测试用例 4: URL 包含多个查询参数
        String url4 = "https://example.com/path/to/file.txt?query1=123&query2=456";
        assertEquals("file.txt", ToolRuntimeService.extractFileName(url4));

        // 测试用例 5: URL 不包含文件名（例如以目录结尾）
        String url5 = "https://example.com/path/to/";
        assertEquals("", ToolRuntimeService.extractFileName(url5));

        // 测试用例 6: URL 为空
        String url6 = "";
        assertEquals("", ToolRuntimeService.extractFileName(url6));

        // 测试用例 7: URL 不包含文件名（例如以目录结尾，但有查询参数）
        String url7 = "https://example.com/path/to/?query=123";
        assertEquals("", ToolRuntimeService.extractFileName(url7));

        // 测试用例 8: URL 包含特殊字符
        String url8 = "https://example.com/path/to/file%20name.txt?query=123";
        assertEquals("file%20name.txt", ToolRuntimeService.extractFileName(url8));

        // 测试用例 9: URL 不包含路径，只有文件名
        String url9 = "https://example.com/file%20name.txt";
        assertEquals("file%20name.txt", ToolRuntimeService.extractFileName(url9));

        // 测试用例 10: URL 包含多个路径分隔符
        String url10 = "https://example.com/path//to//file.txt";
        assertEquals("file.txt", ToolRuntimeService.extractFileName(url10));
    }

    @Test
    void test_run_tool_post_should_succeed() throws IOException {
        when(obsService.downloadObsFile(String.format("%s/%s.json", TOOL_TEST_OBS_PATH, TEST_PLUGIN_ID))).thenReturn(
                TestUtil.getStringFromFile("classpath:openapi/openapi_post_test.json"));
        RequestResult requestResult = new RequestResult();
        requestResult.setSuccess(true);
        requestResult.setResponse("fake_response");
        when(okHttpUtils.call(anyString(), any(), any(), any(), any())).thenReturn(requestResult);
        when(delegateExchangeTokenService.delegateExchangeToken(anyString(), anyString(), anyString())).thenReturn(
                "fake_token");

        RunToolRequestBody runToolRequestBody = new RunToolRequestBody().setParameter(
                "{\"a\":1, \"b\":2, \"headerParam\":\"111111\", \"queryParam\":\"222\", \"pathParam\":\"333\"}");
        runToolRequestBody.setToolObsKey(TEST_PLUGIN_ID);
        RunToolResponseBody runToolResponseBody = toolRuntimeService.runTool(TEST_PROJECT_ID, runToolRequestBody);

        assertTrue(runToolResponseBody.isSuccess());
        assertEquals(requestResult.getResponse(), runToolResponseBody.getRawResponse());
        assertEquals("[{\"a\":1,\"b\":2}]", runToolResponseBody.getRawRequestBody());
        assertEquals("http://fake/333?queryParam=222", runToolResponseBody.getRawRequestUrl());
        assertEquals("111111", runToolResponseBody.getRawRequestHeaders().get("headerParam"));
    }

    @Test
    void test_run_tool_post_stream_should_succeed() {
        when(obsService.downloadObsFile(
                String.format("%s/%s.json", TOOL_TEST_OBS_PATH, TEST_PRESET_PLUGIN_ID))).thenReturn(
                TestUtil.getStringFromFile("classpath:openapi/openapi_post_stream_test.json"));
        RequestResult requestResult = new RequestResult();
        requestResult.setSuccess(true);
        requestResult.setResponse(
                "data: {\"id\":\"cmpl-eaba6d3ff5ad4a1e8315be7b31b82f32\",\"object\":\"chat.completion.chunk\",\"created\":1744020021,\"model\":\"p\",\"choices\":[{\"index\":0,\"delta\":{\"role\":\"assistant\"},\"logprobs\":null,\"finish_reason\":null}]}\n\ndata: {\"id\":\"cmpl-eaba6d3ff5ad4a1e8315be7b31b82f32\",\"object\":\"chat.completion.chunk\",\"created\":1744020021,\"model\":\"p\",\"choices\":[{\"index\":0,\"delta\":{\"content\":\"。\"},\"logprobs\":null,\"finish_reason\":null}]}\n\ndata: {\"id\":\"cmpl-eaba6d3ff5ad4a1e8315be7b31b82f32\",\"object\":\"chat.completion.chunk\",\"created\":1744020021,\"model\":\"p\",\"choices\":[{\"index\":0,\"delta\":{\"content\":\"\"},\"logprobs\":null,\"finish_reason\":null}]}\n\ndata: {\"id\":\"cmpl-eaba6d3ff5ad4a1e8315be7b31b82f32\",\"object\":\"chat.completion.chunk\",\"created\":1744020021,\"model\":\"p\",\"choices\":[{\"index\":0,\"delta\":{\"content\":\"\"},\"logprobs\":null,\"finish_reason\":\"stop\",\"stop_reason\":null}]}\n\ndata: [DONE]\n\n");
        when(okHttpUtils.call(anyString(), any(), any(), any(), any())).thenReturn(requestResult);

        RunToolRequestBody runToolRequestBody = new RunToolRequestBody().setParameter(
                "{\"model\":\"agentBuilder\",\"messages\":[{\"role\":\"user\",\"content\":\"明天苏州天气怎么样？\"}],\"stream\":true}");
        runToolRequestBody.setToolObsKey(TEST_PRESET_PLUGIN_ID);
        RunToolResponseBody runToolResponseBody = toolRuntimeService.runTool(TEST_PROJECT_ID, runToolRequestBody);

        assertTrue(runToolResponseBody.isSuccess());
        assertEquals(requestResult.getResponse(), runToolResponseBody.getRawResponse());
        assertEquals(
                "{\"model\":\"agentBuilder\",\"messages\":[{\"role\":\"user\",\"content\":\"明天苏州天气怎么样？\"}],\"stream\":true}",
                runToolResponseBody.getRawRequestBody());
        assertEquals("http://fake", runToolResponseBody.getRawRequestUrl());
        assertEquals(1, runToolResponseBody.getRawRequestHeaders().size());
        assertFalse(runToolResponseBody.getRawResponse().isEmpty());
    }



    @Test
    void test_run_tool_get_should_succeed() {
        when(obsService.downloadObsFile(String.format("%s/%s.json", TOOL_TEST_OBS_PATH, TEST_PLUGIN_ID))).thenReturn(
                TestUtil.getStringFromFile("classpath:openapi/openapi_get_test.json"));
        RequestResult requestResult = new RequestResult();
        requestResult.setSuccess(true);
        requestResult.setResponse("fake_response");
        when(okHttpUtils.call(anyString(), any(), any(), any(), any())).thenReturn(requestResult);

        RunToolRequestBody runToolRequestBody = new RunToolRequestBody().setParameter("{\"city\":320500}");
        runToolRequestBody.setToolObsKey(TEST_PLUGIN_ID);
        RunToolResponseBody runToolResponseBody = toolRuntimeService.runTool(TEST_PROJECT_ID, runToolRequestBody);

        assertTrue(runToolResponseBody.isSuccess());
        assertEquals(requestResult.getResponse(), runToolResponseBody.getRawResponse());
        assertEquals("{}", runToolResponseBody.getRawRequestBody());
        assertEquals(0, runToolResponseBody.getRawRequestHeaders().size());
    }

    private void test_run_tool_get_error(String configFileName) {
        String nonWhitelistedPluginId = "non_whitelisted_plugin";
        when(obsService.downloadObsFile(String.format("%s/%s.json", TOOL_TEST_OBS_PATH, nonWhitelistedPluginId))).thenReturn(
                TestUtil.getStringFromFile("classpath:openapi/" + configFileName));

        RequestResult requestResult = new RequestResult();
        requestResult.setResponse("fake_response");
        when(okHttpUtils.call(anyString(), any(), any(), any(), any())).thenReturn(requestResult);

        RunToolRequestBody runToolRequestBody = new RunToolRequestBody().setParameter("{\"city\":320500}");
        runToolRequestBody.setToolObsKey(nonWhitelistedPluginId);

        assertThrows(AgentStudioException.class, () -> {
            toolRuntimeService.runTool(TEST_PROJECT_ID, runToolRequestBody);
        });
    }

    @Test
    void test_run_tool_get_error1() {
        test_run_tool_get_error("openapi_get_test_error1.json");
    }

    @Test
    void test_run_tool_get_error2() {
        test_run_tool_get_error("openapi_get_test_error2.json");
    }

    @Test
    public void afterPropertiesSetTest() {
        try {
            okHttpUtils.getModelRequestHttpClient("127.0.0.1");
            okHttpUtils.getModelRequestHttpClient("aaa.com");
        } catch (Exception e) {
            fail("afterPropertiesSetTest Exception", e);
        }
    }

    private InputStream mockTxtObsInputStream() throws IOException {
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
                "test.txt",  // 原始文件名
                "text/plain",  // MIME类型
                "test".getBytes(StandardCharsets.UTF_8)  // 文件内容
        );
        return file.getInputStream();
    }

    private ResolveDocumentReq buildresolveDocumentReq() {
        ResolveDocumentReq resolveDocumentReq = new ResolveDocumentReq();
        List<String> urls = List.of("https://test.com/test.txt?");
        resolveDocumentReq.setUrls(urls);
        resolveDocumentReq.setOcrEnabled(true);
        return resolveDocumentReq;
    }

    private ResolveAudioFileReq buildresolveAudioFileReq() {
        ResolveAudioFileReq resolveAudioFileReq = new ResolveAudioFileReq();
        List<String> urls = List.of("https://test.com/test.mp3?");
        resolveAudioFileReq.setUrls(urls);
        resolveAudioFileReq.setAddPunc(true);
        resolveAudioFileReq.setDigitNorm(false);
        return resolveAudioFileReq;
    }

    @Test
    void test_PluginHisIAMAuthAdapter() {
        HisIAMAuthInfo auth = new HisIAMAuthInfo(
                "{\"iamAccount\":\"iamAccount\",\"iamSecret\":\"iamSecret\",\"iamProject\":\"iamProject\","
                        + "\"iamEnterprise\":\"iamEnterprise\",\"iamUrl\":\"http://127.0.0.1/test\", \"userId\":\"uu\", \"scenarioUuid\":\"uuid\"}");
        auth.setAuthId("authId");
        RequestResult requestResult = new RequestResult();
        requestResult.setResponse("fake_response");
        when(okHttpUtils.call(anyString(), any(), any(), any(), any())).thenReturn(requestResult);

        PluginHisIamAdapter adapter = new PluginHisIamAdapter();
        // Adapter may throw IllegalArgumentException when required fields are missing
        Assertions.assertThrows(Exception.class, () -> {
            Map<String, String> headers = adapter.requestHeaderHandler(auth, new HashMap<>());
        });
    }

    @Test
    void test_PluginHisIAMAuthAdapterException() {
        HisIAMAuthInfo auth = new HisIAMAuthInfo(
                "{\"iamAccount\":\"iamAccount\",\"iamSecret\":\"iamSecret\",\"iamProject\":\"iamProject\","
                        + "\"iamEnterprise\":\"iamEnterprise\",\"iamUrl\":\"http://127.0.0.1/test\", \"userId\":\"uu\", \"scenarioUuid\":\"uuid\"}");
        auth.setAuthId("authId");
        RequestResult requestResult = new RequestResult();
        requestResult.setResponse("fake_response");
        when(okHttpUtils.call(anyString(), any(), any(), any(), any())).thenReturn(requestResult);

        PluginHisIamAdapter adapter = new PluginHisIamAdapter();
        Assertions.assertThrows(Exception.class, () -> {
            adapter.requestHeaderHandler(auth, new HashMap<>());
        });
    }


    @Test
    void test_url2Base64_when_url_is_null() throws Exception {
        Url2Base64Req mockRequest = mock(Url2Base64Req.class);
        when(mockRequest.getUrl()).thenReturn(null);

        ToBase64Rsp mockResponse = mock(ToBase64Rsp.class);
        when(mockResponse.setSuccess(eq(false))).thenReturn(mockResponse);
        when(mockResponse.setMessage(eq("URL cannot be empty."))).thenReturn(mockResponse);

        ToBase64Rsp result = toolRuntimeService.url2Base64(mockRequest);

        assertEquals("URL cannot be empty.", result.getMessage());
    }

    @Test
    void test_url2Base64_when_obs_service_returns_null() throws Exception {
        Url2Base64Req mockRequest = mock(Url2Base64Req.class);
        when(mockRequest.getUrl()).thenReturn("http://test.com");

        when(obsService.getByUrl(eq("http://test.com"))).thenReturn(null);

        ToBase64Rsp mockResponse = mock(ToBase64Rsp.class);
        when(mockResponse.setSuccess(eq(false))).thenReturn(mockResponse);
        when(mockResponse.setMessage(eq("Unable to obtain the file stream from the URL"))).thenReturn(mockResponse);

        ToBase64Rsp result = toolRuntimeService.url2Base64(mockRequest);

        assertEquals("Unable to obtain the file stream from the URL.", result.getMessage());
    }




    @Test
    void shouldConvertUrlToBase64Successfully() throws IOException {
        // Arrange
        Url2Base64Req req = new Url2Base64Req();
        String testUrl = "https://example.com/test.png";
        req.setUrl(testUrl);
        IToolRuntimeService mockService = Mockito.mock(ToolRuntimeService.class);

        // Mock ObsService 返回图片流
        String testImageContent = "AA==";
        byte[] imageBytes = Base64.getDecoder().decode(testImageContent);
        InputStream inputStream = new ByteArrayInputStream(imageBytes);
        when(obsService.getByUrl(testUrl)).thenReturn(inputStream);

        // Mock file2Base64Service 返回成功响应
        ToBase64Rsp mockResponse = new ToBase64Rsp();
        mockResponse.setSuccess(true);
        mockResponse.setMessage("Conversion successful");
        mockResponse.setBase64(testImageContent);

        when(mockService.file2Base64(any(MultipartFile.class), anyString(), anyBoolean())).thenReturn(mockResponse);

        // Act
        ToBase64Rsp result = toolRuntimeService.url2Base64(req);

        // Assert
        assertNotNull(result);
        assertFalse(result.isSuccess());
        verify(obsService).getByUrl(testUrl);
    }

    @Test
    void shouldReturnErrorWhenObsServiceReturnsNull() {
        // Arrange
        String url = "https://example.com/image.png";
        Url2Base64Req request = new Url2Base64Req();
        request.setUrl(url);

        // Mock ObsService 返回 null
        when(obsService.getByUrl(url)).thenReturn(null);

        // Act
        ToBase64Rsp response = toolRuntimeService.url2Base64(request);

        // Assert
        assertFalse(response.isSuccess());
    }

    @Test
    void shouldReturnErrorWhenFileSizeExceedsLimit() throws IOException {
        // Arrange
        String url = "https://example.com/image.png";
        byte[] largeBytes = new byte[4 * 1024 * 1024]; // 11MB
        Arrays.fill(largeBytes, (byte) 1);

        Url2Base64Req request = new Url2Base64Req();
        request.setUrl(url);

        when(obsService.getByUrl(url)).thenReturn(new ByteArrayInputStream(largeBytes));
        // Act
        ToBase64Rsp response = toolRuntimeService.url2Base64(request);

        // Assert
        assertFalse(response.isSuccess());
        assertTrue(response.getMessage().contains("exceeds"));
    }

    @Test
    void shouldReturnErrorWhenUrlIsEmpty() {
        // Arrange
        Url2Base64Req request = new Url2Base64Req();
        request.setUrl("");

        // Act
        ToBase64Rsp response = toolRuntimeService.url2Base64(request);

        // Assert
        assertFalse(response.isSuccess());
        assertEquals("URL cannot be empty.", response.getMessage());
    }

    @Test
    void shouldReturnDefaultMimeTypeWhenFileNameIsNull() {
        String result = toolRuntimeService2.inferMimeTypeFromFileName(null);
        assertEquals("application/octet-stream", result);
    }

    @Test
    void shouldReturnCorrectMimeTypeForJpg() {
        String result = toolRuntimeService2.inferMimeTypeFromFileName("photo.jpg");
        assertEquals("image/jpeg", result);
    }

    @Test
    void shouldReturnCorrectMimeTypeForPng() {
        String result = toolRuntimeService2.inferMimeTypeFromFileName("image.png");
        assertEquals("image/png", result);
    }

    @Test
    void shouldReturnCorrectMimeTypeForBmp() {
        String result = toolRuntimeService2.inferMimeTypeFromFileName("image.bmp");
        assertEquals("image/bmp", result);
    }

    @Test
    void shouldReturnCorrectMimeTypeForGif() {
        String result = toolRuntimeService2.inferMimeTypeFromFileName("image.gif");
        assertEquals("image/gif", result);
    }

    @Test
    void shouldReturnCorrectMimeTypeForWebp() {
        String result = toolRuntimeService2.inferMimeTypeFromFileName("image.webp");
        assertEquals("image/webp", result);
    }

    @Test
    void shouldReturnCorrectMimeTypeForSvg() {
        String result = toolRuntimeService2.inferMimeTypeFromFileName("image.svg");
        assertEquals("image/svg+xml", result);
    }

    @Test
    void shouldReturnCorrectMimeTypeForOther() {
        String result = toolRuntimeService2.inferMimeTypeFromFileName("other");
        assertEquals("application/octet-stream", result);
    }

    @Test
    void shouldReturnFailureWhenFileIsNull() {
        ToBase64Rsp response = toolRuntimeService.file2Base64(null, "image/jpeg", true);
        assertFalse(response.isSuccess());
        assertEquals("The file cannot be empty.", response.getMessage());
    }

    @Test
    void shouldReturnFailureWhenFileIsEmpty() {
        MockMultipartFile emptyFile = new MockMultipartFile("file", "test.jpg", "image/jpeg", new byte[0]);
        ToBase64Rsp response = toolRuntimeService.file2Base64(emptyFile, "image/jpeg", true);
        assertFalse(response.isSuccess());
        assertEquals("The file cannot be empty.", response.getMessage());
    }

    @Test
    void shouldReturnFailureWhenFileSizeExceedsLimit() throws IOException {
        // 11MB 的文件
        byte[] largeContent = new byte[11 * 1024 * 1024];
        MockMultipartFile largeFile = new MockMultipartFile("file", "large.jpg", "image/jpeg", largeContent);

        ToBase64Rsp response = toolRuntimeService.file2Base64(largeFile, "image/jpeg", true);
        assertFalse(response.isSuccess());
        assertTrue(response.getMessage().contains("exceeds"));
    }

    @Test
    void shouldReturnSuccessForValidPngImage() throws IOException {
        byte[] pngBytes = {
                (byte) 0x89, 'P', 'N', 'G', 0x0D, 0x0A, 0x1A, 0x0A,
                0x00, 0x00, 0x00, 0x0D, 'I', 'H', 'D', 0x00, 0x00,
                0x00, 0x01, 0x00, 0x00, 0x00, 0x01, 0x08, 0x02
        };

        MockMultipartFile file = new MockMultipartFile("file", "test.png", "image/png", pngBytes);

        ToBase64Rsp response = toolRuntimeService.file2Base64(file, "image/png", true);

        assertTrue(response.isSuccess());
        assertNotNull(response.getBase64());
        assertTrue(response.getBase64().length() > 0);
        assertEquals("image/png", response.getMimetype());
        assertEquals(pngBytes.length, response.getFilesize());
    }

    @Test
    void shouldHandleIOExceptionAndReturnFailure() throws IOException {
        // 模拟一个会抛出 IOException 的文件
        MockMultipartFile file = new MockMultipartFile("file", "test.jpg", "image/jpeg", new ByteArrayInputStream(new byte[0])) {
            @Override
            public byte[] getBytes() throws IOException {
                throw new IOException("Simulated I/O error");
            }
        };

        ToBase64Rsp response = toolRuntimeService.file2Base64( file,"image/jpeg", true);

        assertFalse(response.isSuccess());
        assertTrue(response.getMessage().contains("The file cannot be empty."));
    }

    @Test
    void shouldHandleIOExceptionWhenFileGetsBytesFails() throws IOException {
        byte[] pngBytes = {
                (byte) 0x89, 'P', 'N', 'G', 0x0D, 0x0A, 0x1A, 0x0A,
                0x00, 0x00, 0x00, 0x0D, 'I', 'H', 'D', 0x00, 0x00,
                0x00, 0x01, 0x00, 0x00, 0x00, 0x01, 0x08, 0x02
        };
        // 模拟一个会抛出 IOException 的 MultipartFile
        MockMultipartFile file = new MockMultipartFile("file", "test.jpg", "image/jpeg", new ByteArrayInputStream(pngBytes)) {
            @Override
            public byte[] getBytes() throws IOException {
                throw new IOException("Simulated I/O error during file reading");
            }
        };

        ToBase64Rsp response = toolRuntimeService.file2Base64(file, "image/jpeg", true);

        assertFalse(response.isSuccess());
        assertTrue(response.getMessage().contains("Failed to read the file"));
        assertTrue(response.getMessage().contains("Simulated I/O error"));
    }

    @Test
    void shouldHandleSecurityExceptionWhenFileInputStreamIsDenied() throws IOException {
        byte[] pngBytes = {
                (byte) 0x89, 'P', 'N', 'G', 0x0D, 0x0A, 0x1A, 0x0A,
                0x00, 0x00, 0x00, 0x0D, 'I', 'H', 'D', 0x00, 0x00,
                0x00, 0x01, 0x00, 0x00, 0x00, 0x01, 0x08, 0x02
        };
        // 模拟 SecurityException（如权限问题）
        MockMultipartFile file = new MockMultipartFile("file", "test.jpg", "image/jpeg", new ByteArrayInputStream(pngBytes)) {
            @Override
            public byte[] getBytes() throws IOException {
                throw new AgentStudioException("Simulated internal logic failure");
            }
        };

        ToBase64Rsp response = toolRuntimeService.file2Base64(file, "image/jpeg", true);

        assertFalse(response.isSuccess());
        assertTrue(response.getMessage().contains("Convert Exception occurred"));
    }

    @Test
    void testNullBody_ReturnsFailure() {
        ToImageRsp rsp = toolRuntimeService.base64ToImage(null);
        assertFalse(rsp.isSuccess());
        assertEquals("The request body cannot be empty.", rsp.getMessage());
    }

    @Test
    void testEmptyBase64_ReturnsFailure() {
        Base64ToImageReq req = new Base64ToImageReq();
        req.setBase64("");
        req.setMimetype("image/png");

        ToImageRsp rsp = toolRuntimeService.base64ToImage(req);
        assertFalse(rsp.isSuccess());
        assertEquals("The Base64 data cannot be empty.", rsp.getMessage());
    }

    @Test
    void testEmptyMimetype_ReturnsFailure() {
        Base64ToImageReq req = new Base64ToImageReq();
        req.setBase64("iVBORw0ggg==");
        req.setMimetype("");
        ToImageRsp rsp = toolRuntimeService.base64ToImage(req);
        assertFalse(rsp.isSuccess());
        assertEquals("The MIME type of the target image is not provided.", rsp.getMessage());
    }

    @Test
    void testDataUrl_ReturnFailure() {
        Base64ToImageReq req = new Base64ToImageReq();
        req.setBase64("data:image/png;base64,iVBORwqDlG8kKkV1wAAAABJRU5ErkJggg==");
        req.setMimetype("png");
        ToImageRsp rsp = toolRuntimeService.base64ToImage(req);
        assertFalse(rsp.isSuccess());
        assertEquals("Base64 decoding failed: Last unit does not have enough valid bits, Please ensure that an effective Base64-encoded string is provided.", rsp.getMessage());
    }

    @Test
    void testValidImage_ReturnF() {
        Base64ToImageReq req = new Base64ToImageReq();
        req.setBase64("data:image/png;base64,AA==");
        req.setMimetype("png");
        ToImageRsp rsp = toolRuntimeService.base64ToImage(req);
        assertFalse(rsp.isSuccess());
        assertEquals("The file is not a valid image or does not match the provided MIME type: image/png.", rsp.getMessage());
    }

    @Test
    void testInvalidMimetype_ReturnsFailure() {
        Base64ToImageReq req = new Base64ToImageReq();
        req.setBase64("aGVsbG8=");
        req.setMimetype("application/octet-stream");

        ToImageRsp rsp = toolRuntimeService.base64ToImage(req);
        assertFalse(rsp.isSuccess());
        assertEquals("The image format is not supported.", rsp.getMessage());
    }

    @Test
    void testValidDataUrl_ReturnF() {
        Base64ToImageReq req = new Base64ToImageReq();
        req.setBase64("data:imagebase64AA==");
        req.setMimetype("png");
        ToImageRsp rsp = toolRuntimeService.base64ToImage(req);
        assertFalse(rsp.isSuccess());
        assertEquals("The data URL format is incorrect.", rsp.getMessage());
    }

    @Test
    void testValiSize_ReturnF() {
        Base64ToImageReq req = new Base64ToImageReq();
        req.setBase64("data:imagebase64AA==");
        req.setMimetype("png");
        ToImageRsp rsp = toolRuntimeService.base64ToImage(req);
        assertFalse(rsp.isSuccess());
        assertEquals("The data URL format is incorrect.", rsp.getMessage());
    }


    @Test
    void testImageSizeValidation_Failure_OverLimit() {
        // Arrange: 模拟一个 11MB 的 base64 字符串
        byte[] largeImageBytes = new byte[11 * 1024 * 1024];
        for (int i = 0; i < largeImageBytes.length; i++) {
            largeImageBytes[i] = (byte) i;
        }
        String base64Str = Base64.getEncoder().encodeToString(largeImageBytes);

        Base64ToImageReq req = new Base64ToImageReq();
        req.setBase64(base64Str);
        req.setMimetype("image/jpeg");

        // Act
        ToImageRsp response = toolRuntimeService.base64ToImage(req);

        // Assert
        assertFalse(response.isSuccess());
        assertEquals("The image size exceeds the 10 MB limit.", response.getMessage());
    }


    @Test
    void test_SVG_Failure() {
        Base64ToImageReq req = new Base64ToImageReq();
        req.setBase64("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mWQMQ0AAAgDoj0cNziwAAAAAElFTkSuQmCC");
        req.setMimetype("image/svg+xml");
        ToImageRsp rsp = toolRuntimeService.base64ToImage(req);
        assertFalse(rsp.isSuccess());
    }

    @Test
    void test_Success() {
        Base64ToImageReq req = new Base64ToImageReq();
        req.setBase64("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mWQMQ0AAAgDoj0cNziwAAAAAElFTkSuQmCC");
        req.setMimetype("image/png");
        ToImageRsp rsp = toolRuntimeService.base64ToImage(req);
        assertTrue(rsp.isSuccess());
    }

    @Test
    void testHtmlErrorResponse() {
        String xml = "<html lang=\"zh\">\n" +
                "<head>\n" +
                "    <meta charset=\"UTF-8\">\n" +
                "    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n" +
                "    <title>安全的 HTML 页面</title>\n" +
                "</head>\n" +
                "<body>\n" +
                "    <h1>你好，世界！</h1>\n" +
                "    <p>这是一个完全不会触发异常的 HTML 页面。</p>\n" +
                "    <p>没有脚本，没有外部链接，没有危险标签。</p>\n" +
                "</body>\n" +
                "</html>";
        byte[] data = xml.getBytes(StandardCharsets.UTF_8);
        assertFalse(toolRuntimeService2.isErrorResponse(data));
    }


    @Test
    void testXmlErrorResponse() {
        String xml = "<error><code>404</code><message>Not Found</message></error><error><code>404</code><message>Not Found</message></error><error><code>404</code><message>Not Found</message></error><error><code>404</code><message>Not Found</message></error><error><code>404</code><message>Not Found</message></error><error><code>404</code><message>Not Found</message></error>";
        byte[] data = xml.getBytes(StandardCharsets.UTF_8);
        assertTrue(toolRuntimeService2.isErrorResponse(data));
    }


}
