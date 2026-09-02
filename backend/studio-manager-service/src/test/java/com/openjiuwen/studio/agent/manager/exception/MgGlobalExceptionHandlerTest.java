/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.exception;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
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
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.jdbc.BadSqlGrammarException;
import org.springframework.validation.BindingResult;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.context.request.async.AsyncRequestTimeoutException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

import java.sql.SQLException;
import java.util.List;

@ExtendWith(MockitoExtension.class)
class MgGlobalExceptionHandlerTest {

    @Mock
    private I18nUtil i18nUtil;

    private MgGlobalExceptionHandler handler;

    @BeforeEach
    void setUp() {
        handler = new MgGlobalExceptionHandler(i18nUtil);
    }

    @Test
    void testHandleAgentManagerException() {
        AgentStudioException ex = new AgentStudioException(StudioError.UNEXPECTED_ERROR);
        ErrorInfo errorInfo = new ErrorInfo("msg", "reason", "suggestion");
        when(i18nUtil.getMessage(any(AgentStudioException.class))).thenReturn(errorInfo);

        ResponseEntity<ErrorRsp> response = handler.handleAgentManagerException(ex);

        assertNotNull(response);
        assertNotNull(response.getBody());
        assertNotNull(response.getBody().getErrorCode());
        assertEquals("msg", response.getBody().getErrorMsg());
    }

    @Test
    void testHandleAgentManagerException_WithDetails() {
        AgentStudioException ex = new AgentStudioException(StudioError.UNEXPECTED_ERROR, List.of("detail1", "detail2"));
        ErrorInfo errorInfo = new ErrorInfo("msg", "reason", "suggestion");
        when(i18nUtil.getMessage(any(AgentStudioException.class))).thenReturn(errorInfo);

        ResponseEntity<ErrorRsp> response = handler.handleAgentManagerException(ex);

        assertNotNull(response);
        assertNotNull(response.getBody().getDetails());
        assertEquals(2, response.getBody().getDetails().size());
    }

    @Test
    void testHandleSqlErrorException() {
        BadSqlGrammarException ex = new BadSqlGrammarException("sql", "SELECT *", new SQLException("bad"));
        ErrorInfo errorInfo = new ErrorInfo("sql error", "reason", "suggestion");
        when(i18nUtil.getMessage(any(AgentStudioException.class))).thenReturn(errorInfo);

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
        when(i18nUtil.getMessage(any(StudioError.class))).thenReturn("validation error");
        when(i18nUtil.getSuggestion(any(StudioError.class))).thenReturn("fix it");

        ResponseEntity<ErrorRsp> response = handler.handleMethodArgumentNotValidException(ex);

        assertNotNull(response);
        assertNotNull(response.getBody());
        assertEquals("name: is required", response.getBody().getErrorMsg());
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
    }

    @Test
    void testHandleAsyncRequestTimeoutException() {
        AsyncRequestTimeoutException ex = new AsyncRequestTimeoutException();
        when(i18nUtil.getMessage(any(StudioError.class))).thenReturn("timeout error");

        assertThrows(NumberFormatException.class, () -> handler.handleException(ex));
    }

    @Test
    void testHandleSQLException() {
        SQLException ex = new SQLException("db error");
        ErrorInfo errorInfo = new ErrorInfo("sql fail", "reason", "suggestion");
        when(i18nUtil.getMessage(any(AgentStudioException.class))).thenReturn(errorInfo);

        ResponseEntity<ErrorRsp> response = handler.handleException(ex);

        assertNotNull(response);
        assertNotNull(response.getBody());
    }

    @Test
    void testHandleJSONException() {
        JSONException ex = new JSONException("json error");
        ErrorInfo errorInfo = new ErrorInfo("json fail", "reason", "suggestion");
        when(i18nUtil.getMessage(any(AgentStudioException.class))).thenReturn(errorInfo);

        ResponseEntity<ErrorRsp> response = handler.handleException(ex);

        assertNotNull(response);
        assertNotNull(response.getBody());
    }

    @Test
    void testHandleNotReadableException() {
        HttpMessageNotReadableException ex = mock(HttpMessageNotReadableException.class);
        when(i18nUtil.getMessage(any(StudioError.class))).thenReturn("not readable");

        ResponseEntity<ErrorRsp> response = handler.handleNotReadableException(ex);

        assertNotNull(response);
        assertNotNull(response.getBody());
    }

    @Test
    void testHandleMaxUploadSizeExceededException() {
        MaxUploadSizeExceededException ex = new MaxUploadSizeExceededException(1024);
        ErrorInfo errorInfo = new ErrorInfo("too large", "reason", "suggestion");
        when(i18nUtil.getMessage(any(AgentStudioException.class))).thenReturn(errorInfo);

        ResponseEntity<ErrorRsp> response = handler.handleException(ex);

        assertNotNull(response);
        assertNotNull(response.getBody());
    }
}
