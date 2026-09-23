/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.exception;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.isA;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.alibaba.fastjson.JSONException;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.ErrorInfo;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.jdbc.BadSqlGrammarException;
import org.springframework.validation.BindingResult;
import org.springframework.validation.FieldError;
import org.springframework.web.HttpMediaTypeNotSupportedException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.context.request.async.AsyncRequestTimeoutException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

import java.sql.SQLException;
import java.util.List;

/**
 * MgGlobalExceptionHandler 测试。
 *
 * <p>合并说明（SYNC-01 §0.1）：基底为旧分支 COM-03 版测试（factory → httpBuilder 路径，
 * i18n 经 {@code getMessage(String, Locale)} resolver，lenient stub），覆盖 handleAgentManagerException /
 * handleMethodArgumentNotValidException / handleNoResourceFoundException / handleAsyncRequestTimeoutException 等
 * COM-03 出口；尾部追加 sync_01 业务测试（testHandleHttpRequestMethodNotSupportedException /
 * testHandleHttpMediaTypeNotSupportedException_*）覆盖 sync_01 保留的 4xx handler（直连 i18n，非 factory 路径）。
 */
@ExtendWith(MockitoExtension.class)
class MgGlobalExceptionHandlerTest {

    @Mock
    private I18nUtil i18nUtil;

    private MgGlobalExceptionHandler handler;

    @BeforeEach
    void setUp() {
        handler = new MgGlobalExceptionHandler(i18nUtil);
        // COM-03: builder resolves via getMessage(String key, Locale locale)
        lenient().when(i18nUtil.getMessage(anyString())).thenReturn("i18n-msg");
        lenient().when(i18nUtil.getMessage(anyString(), isA(java.util.Locale.class)))
            .thenReturn("i18n-msg");
    }

    @Test
    void testHandleAgentManagerException() {
        AgentStudioException ex = new AgentStudioException(StudioError.UNEXPECTED_ERROR);

        ResponseEntity<ErrorRsp> response = handler.handleAgentManagerException(ex);

        assertNotNull(response);
        assertNotNull(response.getBody());
        assertNotNull(response.getBody().getErrorCode());
        assertEquals("i18n-msg", response.getBody().getErrorMsg());
        assertNotNull(response.getBody().getRequestId());
    }

    @Test
    void testHandleAgentManagerException_WithDetails() {
        AgentStudioException ex = new AgentStudioException(StudioError.UNEXPECTED_ERROR, List.of("detail1", "detail2"));

        ResponseEntity<ErrorRsp> response = handler.handleAgentManagerException(ex);

        assertNotNull(response);
        assertNotNull(response.getBody().getDetails());
        assertEquals(2, response.getBody().getDetails().size());
    }

    @Test
    void testHandleSqlErrorException() {
        BadSqlGrammarException ex = new BadSqlGrammarException("sql", "SELECT *", new SQLException("bad"));

        ResponseEntity<ErrorRsp> response = handler.handleSqlErrorException(ex);

        assertNotNull(response);
        assertNotNull(response.getBody());
    }

    @Test
    void testHandleMethodArgumentNotValidException() {
        MethodArgumentNotValidException ex = mock(MethodArgumentNotValidException.class);
        BindingResult bindingResult = mock(BindingResult.class);
        FieldError fieldError = new FieldError("obj", "name", "is required");
        when(ex.getBindingResult()).thenReturn(bindingResult);
        when(bindingResult.getFieldErrors()).thenReturn(List.of(fieldError));

        ResponseEntity<ErrorRsp> response = handler.handleMethodArgumentNotValidException(ex);

        assertNotNull(response);
        assertNotNull(response.getBody());
        // 切 factory 后：errorMsg = canonical i18n-msg（非 joined field errors，不泄漏入参详情）；details 保留字段错误；errorCode 准确 + requestId 存在
        assertNotNull(response.getBody().getErrorMsg());
        assertEquals("openjiuwen.02001003", response.getBody().getErrorCode());
        assertNotNull(response.getBody().getRequestId());
        assertNotNull(response.getBody().getDetails());
        assertEquals(1, response.getBody().getDetails().size());
        assertEquals("name: is required", response.getBody().getDetails().get(0).getErrorMsg());
    }

    @Test
    void testHandleNoResourceFoundException() {
        NoResourceFoundException ex = new NoResourceFoundException(HttpMethod.GET, "/missing");

        ResponseEntity<ErrorRsp> response = handler.handleNoResourceFoundException(ex);

        assertNotNull(response);
        assertNotNull(response.getBody());
        // 切 factory 后：404 用 STATIC_RESOURCE_NOT_EXIST canonical + i18n errorMsg（非 exception.getMessage()，不泄漏路径）+ requestId
        assertEquals("openjiuwen.02601007", response.getBody().getErrorCode());
        String errorMsg = response.getBody().getErrorMsg();
        assertNotNull(errorMsg);
        assertNotEquals(ex.getMessage(), errorMsg);
        assertEquals(404, response.getStatusCode().value());
    }

    @Test
    void testHandleAsyncRequestTimeoutException() {
        AsyncRequestTimeoutException ex = new AsyncRequestTimeoutException();

        ResponseEntity<ErrorRsp> response = handler.handleException(ex);

        // COM-03: refactored to use factory → builder; no longer throws NFE
        assertNotNull(response);
        assertNotNull(response.getBody());
    }

    @Test
    void testHandleSQLException() {
        SQLException ex = new SQLException("db error");

        ResponseEntity<ErrorRsp> response = handler.handleException(ex);

        assertNotNull(response);
        assertNotNull(response.getBody());
    }

    @Test
    void testHandleJSONException() {
        JSONException ex = new JSONException("json error");

        ResponseEntity<ErrorRsp> response = handler.handleException(ex);

        assertNotNull(response);
        assertNotNull(response.getBody());
    }

    @Test
    void testHandleNotReadableException() {
        HttpMessageNotReadableException ex = mock(HttpMessageNotReadableException.class);

        ResponseEntity<ErrorRsp> response = handler.handleNotReadableException(ex);

        assertNotNull(response);
        assertNotNull(response.getBody());
    }

    @Test
    void testHandleMaxUploadSizeExceededException() {
        MaxUploadSizeExceededException ex = new MaxUploadSizeExceededException(1024);

        ResponseEntity<ErrorRsp> response = handler.handleException(ex);

        assertNotNull(response);
        assertNotNull(response.getBody());
    }

    // === sync_01 业务测试：4xx handler（直连 i18n，非 factory 路径）===

    @Test
    void testHandleHttpRequestMethodNotSupportedException() {
        HttpRequestMethodNotSupportedException ex =
            new HttpRequestMethodNotSupportedException("POST", List.of("GET"));
        ErrorInfo errorInfo = new ErrorInfo("method not supported",
            "the request used an unsupported method", "check request method");
        when(i18nUtil.getMessage(any(AgentStudioException.class))).thenReturn(errorInfo);

        ResponseEntity<ErrorRsp> response = handler.handleHttpRequestMethodNotSupportedException(ex);

        assertNotNull(response);
        assertNotNull(response.getBody());
        assertEquals(HttpStatus.METHOD_NOT_ALLOWED, response.getStatusCode());
        assertEquals("openjiuwen.02001129", response.getBody().getErrorCode());
        assertEquals("method not supported", response.getBody().getErrorMsg());
        assertEquals("the request used an unsupported method", response.getBody().getErrorReason());
        assertEquals("check request method", response.getBody().getErrorSuggestion());
    }

    @Test
    void testHandleHttpMediaTypeNotSupportedException_JsonEndpoint() {
        // JSON接口收到text/plain时，reason应提示期望application/json而非误导性的multipart
        HttpMediaTypeNotSupportedException ex =
            new HttpMediaTypeNotSupportedException(MediaType.TEXT_PLAIN,
                List.of(MediaType.APPLICATION_JSON), HttpMethod.POST);
        when(i18nUtil.getMessage(any(StudioError.class))).thenReturn("validation error");
        when(i18nUtil.getSuggestion(any(StudioError.class))).thenReturn("fix it");

        ResponseEntity<ErrorRsp> response = handler.handleHttpMediaTypeNotSupportedException(ex);

        assertNotNull(response);
        assertNotNull(response.getBody());
        assertEquals("请求格式错误，Content-Type 不被该接口支持，期望：application/json",
            response.getBody().getErrorReason());
    }

    @Test
    void testHandleHttpMediaTypeNotSupportedException_MultipartEndpoint() {
        // 文件上传接口（consumes=multipart/form-data）的提示应如实列出multipart类型
        HttpMediaTypeNotSupportedException ex =
            new HttpMediaTypeNotSupportedException(MediaType.APPLICATION_JSON,
                List.of(MediaType.MULTIPART_FORM_DATA, MediaType.MULTIPART_MIXED), HttpMethod.POST);
        when(i18nUtil.getMessage(any(StudioError.class))).thenReturn("validation error");
        when(i18nUtil.getSuggestion(any(StudioError.class))).thenReturn("fix it");

        ResponseEntity<ErrorRsp> response = handler.handleHttpMediaTypeNotSupportedException(ex);

        assertNotNull(response);
        assertNotNull(response.getBody());
        assertEquals("请求格式错误，Content-Type 不被该接口支持，期望：multipart/form-data、multipart/mixed",
            response.getBody().getErrorReason());
    }
}
