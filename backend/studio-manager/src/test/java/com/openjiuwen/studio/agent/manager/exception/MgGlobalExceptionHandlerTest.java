/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.utils.BaseTest;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;
import org.mockito.MockitoAnnotations;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.MethodParameter;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.BadSqlGrammarException;
import org.springframework.validation.BindingResult;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

import java.util.Collections;
import java.util.Objects;

/**
 * MgGlobalExceptionHandler测试类
 *
 */
@MockitoSettings(strictness = Strictness.LENIENT)
public class MgGlobalExceptionHandlerTest extends BaseTest {
    @Autowired
    private MgGlobalExceptionHandler globalExceptionHandler;

    @Autowired
    private I18nUtil i18nUtil;

    private AutoCloseable mockitoCloseable;

    @BeforeEach
    public void setUp() throws Exception {
        mockitoCloseable = MockitoAnnotations.openMocks(this);
    }

    @AfterEach
    public void tearDown() throws Exception {
        mockitoCloseable.close();
    }

    @Test
    public void test_handle_handleAgentManagerException_should_succeed_when_test_data_combination() {
        // setup
        AgentStudioException exception = new AgentStudioException("fake_error_message");

        // run the test
        ResponseEntity<ErrorRsp> result = globalExceptionHandler.handleAgentManagerException(exception);

        // verify the results
        assertEquals("服务内部错误。", result.getBody().getErrorMsg());
    }

    @Test
    public void test_handleSqlErrorException_should_succeed_when_test_data_combination() {
        // setup
        BadSqlGrammarException exception = mock(BadSqlGrammarException.class);

        // run the test
        ResponseEntity<ErrorRsp> result = globalExceptionHandler.handleSqlErrorException(exception);

        // verify the results
        assertEquals("SQL执行失败。", result.getBody().getErrorMsg());
    }

    @Test
    void test_handleMethodArgumentNotValidException_should_succeed_when_test_data_combination() {
        // setup
        MethodParameter original = mock(MethodParameter.class);
        MethodParameter parameter = new MethodParameter(original);
        BindingResult bindingResult = mock(BindingResult.class);
        when(bindingResult.getFieldErrors()).thenReturn(
            Collections.singletonList(new FieldError("objectA", "fieldA", "field error")));
        MethodArgumentNotValidException exception = new MethodArgumentNotValidException(parameter, bindingResult);

        // run the test
        ResponseEntity<ErrorRsp> result = globalExceptionHandler.handleMethodArgumentNotValidException(exception);

        // verify the results
        assertEquals("fieldA: field error", Objects.requireNonNull(result.getBody()).getErrorMsg());
    }

    @Test
    public void test_handleMethodArgumentNotValidException_empty_field_error() {
        // Given
        MethodArgumentNotValidException exception = mock(MethodArgumentNotValidException.class);
        BindingResult bindingResult = mock(BindingResult.class);
        when(exception.getBindingResult()).thenReturn(bindingResult);
        when(bindingResult.getFieldErrors()).thenReturn(Collections.emptyList());
        // When
        ResponseEntity<ErrorRsp> response = globalExceptionHandler.handleMethodArgumentNotValidException(exception);
        // Then
        assertEquals(HttpStatus.BAD_REQUEST, response.getStatusCode());
        assertEquals("openjiuwen.02001003", Objects.requireNonNull(response.getBody()).getErrorCode());
        assertEquals("", response.getBody().getErrorMsg());
    }

    @Test
    void test_handleNoResourceFoundException_should_succeed_when_test_data_combination() {
        // setup
        NoResourceFoundException exception = new NoResourceFoundException(HttpMethod.GET, "fake_resource_path");

        // run the test
        ResponseEntity<ErrorRsp> result = globalExceptionHandler.handleNoResourceFoundException(exception);

        // verify the results
        assertEquals("No static resource fake_resource_path.", result.getBody().getErrorMsg());
    }

    @Test
    void testAgentStudioException() {
        AgentStudioException agentStudioException = new AgentStudioException(StudioError.AGENT_NAME_INVALID,
            Collections.singletonList("demo"));

        ResponseEntity<ErrorRsp> errorRspResponseEntity = globalExceptionHandler.handleAgentManagerException(
            agentStudioException);

        ErrorRsp body = errorRspResponseEntity.getBody();

        assertNotNull(body);
        assertEquals("openjiuwen.02101001", body.getErrorCode());
        assertEquals(i18nUtil.getMessage("openjiuwen.02101001"), body.getErrorMsg());
        assertEquals(i18nUtil.getMessage("openjiuwen.02101001.reason"), body.getErrorReason());
        assertEquals(i18nUtil.getMessage("openjiuwen.02101001.suggestion"), body.getErrorSuggestion());
    }

    @Test
    public void test_gentStudioException_prefix() {
        // setup
        AgentStudioException exception = new AgentStudioException("openjiuwen.Exception");

        // run the test
        ResponseEntity<ErrorRsp> result = globalExceptionHandler.handleAgentManagerException(exception);

        // verify the results
        assertTrue(result.getBody().getErrorCode().startsWith("openjiuwen"));
    }
}



