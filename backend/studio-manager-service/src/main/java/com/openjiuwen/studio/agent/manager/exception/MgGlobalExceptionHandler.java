/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception;

import com.alibaba.fastjson.JSONException;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.ErrorInfo;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.dto.ErrorDetail;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;

import jakarta.validation.ConstraintViolation;
import jakarta.validation.ConstraintViolationException;

import lombok.extern.slf4j.Slf4j;

import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.jdbc.BadSqlGrammarException;
import org.springframework.util.CollectionUtils;
import org.springframework.validation.BindingResult;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.context.request.async.AsyncRequestTimeoutException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

import java.sql.SQLException;
import java.util.stream.Collectors;

/**
 * 功能描述 异常捕获类
 *
 */
@ControllerAdvice
@Slf4j
public class MgGlobalExceptionHandler {
    final I18nUtil i18nUtil;

    public MgGlobalExceptionHandler(I18nUtil i18nUtil) {
        this.i18nUtil = i18nUtil;
    }

    /**
     * 处理AgentStudioException，根据ErrorCode从i18n读取对应的错误信息
     *
     * @param agentStudioException AgentStudioException
     * @return ResponseEntity<ErrorRsp>
     */
    @ExceptionHandler(AgentStudioException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleAgentManagerException(AgentStudioException agentStudioException) {
        StudioError errorCode = agentStudioException.getErrorCode();
        String code = "openjiuwen." + errorCode.getModule().getSubCode() + errorCode.getCode();
        ErrorInfo errorInfo = i18nUtil.getMessage(agentStudioException);

        log.error("handle AgentStudioException, code = {}", code, agentStudioException);
        ErrorRsp rsp = new ErrorRsp().setErrorCode(code).setErrorMsg(errorInfo.getMessage()).setErrorReason(errorInfo
            .getReason()).setErrorSuggestion(errorInfo.getSuggestion());
        if (!CollectionUtils.isEmpty(agentStudioException.getDetails())) {
            rsp.setDetails(agentStudioException.getDetails()
                .stream()
                .map(msg -> new ErrorDetail().setErrorMsg(msg))
                .collect(Collectors.toList()));
        }
        return new ResponseEntity<>(rsp, agentStudioException.getErrorCode().getHttpStatus());
    }

    /**
     * Processor exception
     *
     * @param exception Unknown exception
     * @return Return result
     */
    @ExceptionHandler(BadSqlGrammarException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleSqlErrorException(BadSqlGrammarException exception) {
        log.error("exception: {}", exception.getMessage());
        return handleAgentManagerException(new AgentStudioException(StudioError.SQL_EXECUTE_FAILED));
    }

    /**
     * 处理方法参数校验异常使用
     *
     * @param exception MethodArgumentNotValidException
     * @return Return result
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleMethodArgumentNotValidException(MethodArgumentNotValidException exception) {
        String errMessage = null;

        // 获取校验异常参数
        BindingResult bindingResult = exception.getBindingResult();
        for (FieldError fieldError : bindingResult.getFieldErrors()) {
            errMessage = fieldError.getField() + fieldError.getDefaultMessage();
        }
        log.error("throw MethodArgumentNotValidException", exception);
        StudioError errorInfo = StudioError.METHOD_ARGUMENT_NOT_VALID;
        String code = "openjiuwen." + errorInfo.getModule().getSubCode() + errorInfo.getCode();
        ErrorRsp errorRsp = new ErrorRsp().setErrorCode(code)
            .setErrorMsg(errMessage).setErrorReason(i18nUtil.getMessage(errorInfo)).setErrorSuggestion(i18nUtil.getSuggestion(errorInfo));
        return new ResponseEntity<>(errorRsp,
            ResponseModel.num2HttpStatus(Integer.toString(exception.getStatusCode().value())));
    }

    /**
     * 处理 @PathVariable / @RequestParam 上的校验注解（@Size, @Pattern 等）失败
     */
    @ExceptionHandler(ConstraintViolationException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleConstraintViolationException(ConstraintViolationException exception) {
        StringBuilder errMsg = new StringBuilder();
        for (ConstraintViolation<?> violation : exception.getConstraintViolations()) {
            String paramName = violation.getPropertyPath().toString();
            if (paramName.contains(".")) {
                paramName = paramName.substring(paramName.lastIndexOf('.') + 1);
            }
            errMsg.append(paramName).append(violation.getMessage()).append("; ");
        }
        log.error("throw ConstraintViolationException: {}", errMsg);
        StudioError errorInfo = StudioError.METHOD_ARGUMENT_NOT_VALID;
        String code = "openjiuwen." + errorInfo.getModule().getSubCode() + errorInfo.getCode();
        ErrorRsp errorRsp = new ErrorRsp().setErrorCode(code)
            .setErrorMsg(errMsg.toString())
            .setErrorReason(i18nUtil.getMessage(errorInfo))
            .setErrorSuggestion(i18nUtil.getSuggestion(errorInfo));
        return new ResponseEntity<>(errorRsp, errorInfo.getHttpStatus());
    }

    /**
     * NoResourceFoundException handling injection
     *
     * @param exception NoResourceFoundException
     * @return Return result
     */
    @ExceptionHandler(NoResourceFoundException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleNoResourceFoundException(Exception exception) {
        log.error("exception: {}", exception.getMessage());
        ErrorRsp errorRsp = new ErrorRsp().setErrorCode(String.valueOf(StudioError.STATIC_RESOURCE_NOT_EXIST.getCode()))
            .setErrorMsg(exception.getMessage());
        return new ResponseEntity<>(errorRsp, StudioError.STATIC_RESOURCE_NOT_EXIST.getHttpStatus());
    }

    /**
     * Processor exception
     *
     * @param exception 流式接口超时异常
     * @return Return result
     */
    @ExceptionHandler(AsyncRequestTimeoutException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleException(AsyncRequestTimeoutException exception) {
        log.error("AsyncRequestTimeoutException", exception);
        ErrorRsp errorRsp = new ErrorRsp().setErrorCode(
                String.valueOf(StudioError.STREAM_INTERFACE_EXECUTE_TIMEOUT.getCode()))
            .setErrorMsg(i18nUtil.getMessage(StudioError.STREAM_INTERFACE_EXECUTE_TIMEOUT));
        return new ResponseEntity<>(errorRsp,
            StudioError.STREAM_INTERFACE_EXECUTE_TIMEOUT.getHttpStatus());
    }

    /**
     * Processor exception
     *
     * @param exception 数据库执行异常（防止接口报错打印暴露数据库信息）
     * @return Return result
     */
    @ExceptionHandler(SQLException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleException(SQLException exception) {
        log.error("SQLException: {}", exception.getMessage());
        return handleAgentManagerException(new AgentStudioException(StudioError.SQL_EXECUTE_FAILED,
            "Sql execute failed!"));
    }

    /**
     * Processor exception
     *
     * @param exception Json转换异常（防止接口报错打印Json版本信息）
     * @return Return result
     */
    @ExceptionHandler(JSONException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleException(JSONException exception) {
        log.error("JsonException: {}", exception.getMessage());
        return handleAgentManagerException(new AgentStudioException(StudioError.JSON_CONVERT_ERROR));
    }

    /**
     * api入参校验异常
     * @param exception
     * @return
     */
    @ExceptionHandler(HttpMessageNotReadableException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleNotReadableException(Exception exception) {
        log.error("NotReadableException: {}", exception.getMessage());
        ErrorRsp errorRsp = new ErrorRsp().setErrorCode(StudioError.METHOD_ARGUMENT_NOT_VALID.getFullCode())
            .setErrorMsg(i18nUtil.getMessage(StudioError.METHOD_ARGUMENT_NOT_VALID));
        return new ResponseEntity<>(errorRsp, StudioError.METHOD_ARGUMENT_NOT_VALID.getHttpStatus());
    }

    /**
     * Processor MaxUploadSizeExceededException
     *
     * @param exception MaxUploadSizeExceededException
     * @return Return result
     */
    @ExceptionHandler(MaxUploadSizeExceededException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleException(MaxUploadSizeExceededException exception) {
        log.error("MaxUploadSizeExceededException: {}", exception.getMessage());
        return handleAgentManagerException(new AgentStudioException(StudioError.MAX_UPLOAD_SIZE_EXCEEDED));
    }
}
