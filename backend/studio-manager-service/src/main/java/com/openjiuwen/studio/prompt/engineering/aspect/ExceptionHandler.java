/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.aspect;

import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.CONTACT;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.DELETE;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.FAILED;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.INSERT;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.OPERATE;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.RETRY;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.SELECT;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.UPDATE;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;

import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.dao.DataAccessException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.BindException;
import org.springframework.validation.BindingResult;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ResponseBody;

import java.sql.SQLException;
import java.util.Locale;
import java.util.Map;
import java.util.stream.Collectors;


/**
 * Global exception handler class
 */
@ControllerAdvice
@Order(Ordered.LOWEST_PRECEDENCE)
public class ExceptionHandler {
    private static final Logger log = LoggerFactory.getLogger(ExceptionHandler.class);

    /**
     * Exception handling injection
     *
     * @param exception PeException
     * @return Return result
     */
    @org.springframework.web.bind.annotation.ExceptionHandler(AgentStudioException.class)
    @ResponseBody
    public ResponseEntity<Map<String, String>> handlePeException(AgentStudioException exception) {
        log.error("throw PeException exception: ", exception);
        return ResponseModel.failed(String.valueOf(exception.getErrorCode()), exception.getMessage());
    }

    /**
     * Method argument valid Exception handling injection
     *
     * @param exception PeException
     * @return Return result
     */
    @org.springframework.web.bind.annotation.ExceptionHandler(BindException.class)
    @ResponseBody
    public ResponseEntity<Map<String, String>> handlePeException(BindException exception) {
        BindingResult bindingResult = exception.getBindingResult();
        String errMessage = bindingResult.getFieldErrors().stream()
            .map(fe -> fe.getField() + ": " + fe.getDefaultMessage())
            .collect(Collectors.joining("; "));
        log.error("throw BindException: {}", errMessage);
        AgentStudioException peException = new AgentStudioException(StudioError.ARGUMENT_VALID_ERROR);
        return ResponseModel.failed(String.valueOf(peException.getErrorCode()), errMessage);
    }

    /**
     * Processor exception
     *
     * @param exception Unknown exception
     * @return Return result
     */
    @org.springframework.web.bind.annotation.ExceptionHandler(Exception.class)
    @ResponseBody
    public ResponseEntity<Map<String, String>> handleException(Exception exception) {
        log.error("error: ", exception);
        return ResponseModel.failed(String.valueOf(HttpStatus.BAD_REQUEST.value()), exception.getMessage());
    }

    /**
     * process SQLException
     *
     * @param exception
     * @return
     */
    @org.springframework.web.bind.annotation.ExceptionHandler(SQLException.class)
    @ResponseBody
    public ResponseEntity<Map<String, String>> handleSQLException(Exception exception) {
        log.error("SQLException error: ", exception);
        return ResponseModel.failed(String.valueOf(HttpStatus.BAD_REQUEST.value()), getMessageFromException(exception));
    }

    /**
     * process SQLException
     *
     * @param exception
     * @return
     */
    @org.springframework.web.bind.annotation.ExceptionHandler(DataAccessException.class)
    @ResponseBody
    public ResponseEntity<Map<String, String>> handleDataAccessException(Exception exception) {
        log.error("DataAccessException error: ", exception);
        return ResponseModel.failed(String.valueOf(HttpStatus.BAD_REQUEST.value()),
            getMessageFromException(exception) + RETRY + CONTACT);
    }

    private String getMessageFromException(Exception exception) {
        String message = OPERATE;
        if (null != exception && StringUtils.isNotBlank(exception.getMessage())) {
            if (exception.getMessage().toLowerCase(Locale.ENGLISH).contains(UPDATE)) {
                message = UPDATE;
            }
            if (exception.getMessage().toLowerCase(Locale.ENGLISH).contains(INSERT)) {
                message = INSERT;
            }
            if (exception.getMessage().toLowerCase(Locale.ENGLISH).contains(DELETE)) {
                message = DELETE;
            }
            if (exception.getMessage().toLowerCase(Locale.ENGLISH).contains(SELECT)) {
                message = SELECT;
            }
        }
        message += " " + FAILED + ". ";
        message += getErrorMessage(getExceptionClassName(exception));
        return message;
    }

    private static String getErrorMessage(String name) {
        StringBuilder resultBuilder = new StringBuilder();
        if (StringUtils.isNotBlank(name)) {
            resultBuilder.append(name.charAt(0));
            for (int i = 1; i < name.length(); i++) {
                char c = name.charAt(i);
                if (Character.isUpperCase(c)) {
                    c = (char) (c + 32);
                    resultBuilder.append(" ");
                }
                resultBuilder.append(c);
            }
            resultBuilder.append(". ");
        }
        return resultBuilder.toString();
    }

    private static String getExceptionClassName(Exception exception) {
        String clazzName = exception.getClass().getName();
        String[] split = clazzName.split("\\.");
        return split[split.length - 1];
    }
}
