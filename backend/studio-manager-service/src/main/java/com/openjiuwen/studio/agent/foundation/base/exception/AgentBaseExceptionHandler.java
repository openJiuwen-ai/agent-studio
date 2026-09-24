/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.foundation.base.exception;

import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;
import com.openjiuwen.studio.agent.foundation.i18n.I18nUtils;

import feign.FeignException;

import lombok.extern.slf4j.Slf4j;

import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.BadSqlGrammarException;
import org.springframework.validation.BindingResult;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.context.request.async.AsyncRequestTimeoutException;

import java.sql.SQLException;
import java.util.Optional;

/**
 * 功能描述 异常捕获类
 *
 * @since 2024-08-05
 */
@Deprecated
@Slf4j
public class AgentBaseExceptionHandler {

    /**
     * Exception handling AgentBaseException
     *
     * @param agentBaseException AgentBaseException
     * @return Return result
     */
    @ExceptionHandler(AgentBaseException.class)
    @ResponseBody
    public ResponseEntity<ErrorResponse> handleAgentBaseException(AgentBaseException agentBaseException) {
        log.error("throw AgentBaseException exception: {}", agentBaseException.getMessage(), agentBaseException);
        ErrorResponse errorResponse = new ErrorResponse();
        errorResponse.setErrorCode(agentBaseException.getErrorCode().getCode());
        errorResponse.setErrorMsg(agentBaseException.getErrorMsg());
        errorResponse.setErrorReason(agentBaseException.getErrorReason());
        errorResponse.setErrorSuggestion(agentBaseException.getErrorSuggestion());
        return new ResponseEntity<>(errorResponse,
            ResponseModel.num2HttpStatus(Integer.toString(agentBaseException.getErrorCode().getHttpCode())));
    }

    /**
     * Processor FeignException to extract original error details
     *
     * @param exception FeignException
     * @return Return result
     */
    @ExceptionHandler(FeignException.class)
    @ResponseBody
    public ResponseEntity<ErrorResponse> handleFeignException(FeignException exception) {
        log.error("Feign exception: {}", exception.getMessage(), exception);
        ErrorResponse errorResponse = new ErrorResponse();
        
        // Try to extract error details from the exception message
        String errorMsg = exception.getMessage();
        if (errorMsg != null && errorMsg.startsWith("[")) {
            try {
                JSONArray errorArray = JSONArray.parseArray(errorMsg);
                if (errorArray != null && !errorArray.isEmpty()) {
                    JSONObject errorObj = errorArray.getJSONObject(0);
                    if (errorObj != null) {
                        String errorCode = errorObj.getString("error_code");
                        String errorMsgDetail = errorObj.getString("error_msg");
                        String errorReason = errorObj.getString("error_reason");
                        String errorSuggestion = errorObj.getString("error_suggestion");
                        
                        if (errorCode != null) {
                            errorResponse.setErrorCode(errorCode);
                        }
                        if (errorMsgDetail != null) {
                            errorResponse.setErrorMsg(errorMsgDetail);
                        }
                        if (errorReason != null) {
                            errorResponse.setErrorReason(errorReason);
                        }
                        if (errorSuggestion != null) {
                            errorResponse.setErrorSuggestion(errorSuggestion);
                        }
                        
                        // If we successfully extracted error details, return with original HTTP status
                        if (errorCode != null || errorMsgDetail != null) {
                            int httpStatus = getHttpStatusFromFeignException(exception);
                            return new ResponseEntity<>(errorResponse, 
                                ResponseModel.num2HttpStatus(Integer.toString(httpStatus)));
                        }
                    }
                }
            } catch (Exception e) {
                log.warn("Failed to parse Feign exception message as JSON: {}", errorMsg);
            }
        }
        
        // Fallback: if we couldn't extract details, use the exception message
        return handleAgentBaseException(new AgentBaseException(
            ErrorCode.SERVER_INTERNAL_ERROR, 
            Optional.ofNullable(errorMsg).orElse("Feign call failed")));
    }
    
    private int getHttpStatusFromFeignException(FeignException exception) {
        if (exception instanceof FeignException.BadRequest) {
            return 400;
        } else if (exception instanceof FeignException.Unauthorized) {
            return 401;
        } else if (exception instanceof FeignException.Forbidden) {
            return 403;
        } else if (exception instanceof FeignException.NotFound) {
            return 404;
        } else if (exception instanceof FeignException.TooManyRequests) {
            return 429;
        }
        return exception.status() > 0 ? exception.status() : 500;
    }

    /**
     * Processor exception
     *
     * @param exception Unknown exception
     * @return Return result
     */
    @ExceptionHandler(Exception.class)
    @ResponseBody
    public ResponseEntity<ErrorResponse> handleException(Exception exception) {
        log.error("exception: {}", exception.getMessage(), exception);
        return handleAgentBaseException(new AgentBaseException(ErrorCode.SERVER_INTERNAL_ERROR));
    }

    /**
     * Processor exception
     *
     * @param exception Unknown exception
     * @return Return result
     */
    @ExceptionHandler(BadSqlGrammarException.class)
    @ResponseBody
    public ResponseEntity<ErrorResponse> handleSqlErrorException(BadSqlGrammarException exception) {
        log.error("exception: {}", exception.getMessage(), exception);
        return handleAgentBaseException(new AgentBaseException(ErrorCode.SERVER_INTERNAL_ERROR, "Sql execute failed!"));
    }

    /**
     * 处理方法参数校验异常使用
     *
     * @param exception MethodArgumentNotValidException
     * @return Return result
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    @ResponseBody
    public ResponseEntity<ErrorResponse> handleMethodArgumentNotValidException(
        MethodArgumentNotValidException exception) {
        String errMessage = null;
        String errField = null;

        // 获取校验异常参数
        BindingResult bindingResult = exception.getBindingResult();
        for (FieldError fieldError : bindingResult.getFieldErrors()) {
            errField = fieldError.getField();
            errMessage = fieldError.getField() + fieldError.getDefaultMessage();
        }
        log.error("throw MethodArgumentNotValidException: {}", exception.getMessage(), exception);
        ErrorResponse errorResponse = ErrorResponse.builder()
            .errorCode(ErrorCode.METHOD_ARGUMENT_INVALID.getCode())
            .errorMsg(I18nUtils.getMessage(ErrorCode.METHOD_ARGUMENT_INVALID.getCode()))
            .errorReason(I18nUtils.getMessage(ErrorCode.METHOD_ARGUMENT_INVALID.getCode() + ".reason", errMessage))
            .errorSuggestion(
                I18nUtils.getMessage(ErrorCode.METHOD_ARGUMENT_INVALID.getCode() + ".suggestion", errField))
            .build();
        return new ResponseEntity<>(errorResponse,
            ResponseModel.num2HttpStatus(Integer.toString(exception.getStatusCode().value())));
    }

    /**
     * Processor exception
     *
     * @param exception 流式接口超时异常
     * @return Return result
     */
    @ExceptionHandler(AsyncRequestTimeoutException.class)
    @ResponseBody
    public ResponseEntity<ErrorResponse> handleException(AsyncRequestTimeoutException exception) {
        log.error("throw AsyncRequestTimeoutException: {}", exception.getMessage(), exception);
        ErrorResponse errorResponse = ErrorResponse.builder()
            .errorCode(ErrorCode.STREAM_INTERFACE_EXECUTE_TIMEOUT.getCode())
            .errorMsg(I18nUtils.getMessage(ErrorCode.STREAM_INTERFACE_EXECUTE_TIMEOUT.getCode()))
            .errorReason(I18nUtils.getMessage(ErrorCode.STREAM_INTERFACE_EXECUTE_TIMEOUT.getCode() + ".reason"))
            .errorSuggestion(I18nUtils.getMessage(ErrorCode.STREAM_INTERFACE_EXECUTE_TIMEOUT.getCode() + ".suggestion"))
            .build();
        return new ResponseEntity<>(errorResponse,
            ResponseModel.num2HttpStatus(Integer.toString(ErrorCode.STREAM_INTERFACE_EXECUTE_TIMEOUT.getHttpCode())));
    }

    /**
     * Processor exception
     *
     * @param exception 数据库执行异常（防止接口报错打印暴露数据库信息）
     * @return Return result
     */
    @ExceptionHandler(SQLException.class)
    @ResponseBody
    public ResponseEntity<ErrorResponse> handleException(SQLException exception) {
        log.error("throw SQLException: {}", exception.getMessage(), exception);
        return handleAgentBaseException(new AgentBaseException(ErrorCode.SERVER_INTERNAL_ERROR, "Sql execute failed!"));
    }
}
