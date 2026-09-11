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

import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.jdbc.BadSqlGrammarException;
import org.springframework.util.CollectionUtils;
import org.springframework.validation.BindingResult;
import org.springframework.validation.FieldError;
import org.springframework.web.HttpMediaTypeNotSupportedException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.context.request.async.AsyncRequestTimeoutException;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.multipart.MultipartException;
import org.springframework.web.multipart.support.MissingServletRequestPartException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

import java.sql.SQLException;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * 功能描述 异常捕获类
 *
 */
@ControllerAdvice
@Slf4j
@Order(Ordered.HIGHEST_PRECEDENCE)
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
        BindingResult bindingResult = exception.getBindingResult();

        String errMessage = bindingResult.getFieldErrors().stream()
            .map(fe -> fe.getField() + ": " + fe.getDefaultMessage())
            .collect(Collectors.joining("; "));

        List<ErrorDetail> details = bindingResult.getFieldErrors().stream()
            .map(fe -> new ErrorDetail().setErrorMsg(fe.getField() + ": " + fe.getDefaultMessage()))
            .collect(Collectors.toList());

        log.error("throw MethodArgumentNotValidException: {}", errMessage);
        StudioError errorInfo = StudioError.METHOD_ARGUMENT_NOT_VALID;
        ErrorRsp errorRsp = new ErrorRsp().setErrorCode(errorInfo.getFullCode())
            .setErrorMsg(errMessage)
            .setErrorReason(i18nUtil.getMessage(errorInfo))
            .setErrorSuggestion(i18nUtil.getSuggestion(errorInfo))
            .setDetails(details);
        return new ResponseEntity<>(errorRsp, errorInfo.getHttpStatus());
    }

    /**
     * 处理 @PathVariable / @RequestParam 上的校验注解（@Size, @Pattern 等）失败
     */
    @ExceptionHandler(ConstraintViolationException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleConstraintViolationException(ConstraintViolationException exception) {
        List<ErrorDetail> details = exception.getConstraintViolations().stream()
            .map(violation -> {
                String paramName = violation.getPropertyPath().toString();
                if (paramName.contains(".")) {
                    paramName = paramName.substring(paramName.lastIndexOf('.') + 1);
                }
                return new ErrorDetail().setErrorMsg(paramName + ": " + violation.getMessage());
            })
            .collect(Collectors.toList());

        String errMsg = details.stream()
            .map(ErrorDetail::getErrorMsg)
            .collect(Collectors.joining("; "));

        log.error("throw ConstraintViolationException: {}", errMsg);
        StudioError errorInfo = StudioError.METHOD_ARGUMENT_NOT_VALID;
        ErrorRsp errorRsp = new ErrorRsp().setErrorCode(errorInfo.getFullCode())
            .setErrorMsg(errMsg)
            .setErrorReason(i18nUtil.getMessage(errorInfo))
            .setErrorSuggestion(i18nUtil.getSuggestion(errorInfo))
            .setDetails(details);
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

    /**
     * 必填 multipart 段缺失（如未传 file 参数）
     */
    @ExceptionHandler(MissingServletRequestPartException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleMissingServletRequestPartException(MissingServletRequestPartException exception) {
        String reason = "缺少必填参数：" + exception.getRequestPartName();
        log.error("MissingServletRequestPartException: {}", exception.getMessage());
        return badRequest(reason);
    }

    /**
     * 必填 RequestParam 缺失（如 workspace_id 没传）
     */
    @ExceptionHandler(MissingServletRequestParameterException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleMissingServletRequestParameterException(MissingServletRequestParameterException exception) {
        String reason = "缺少必填参数：" + exception.getParameterName();
        log.error("MissingServletRequestParameterException: {}", exception.getMessage());
        return badRequest(reason);
    }

    /**
     * 参数类型转换失败（如 enum 值非法：conflict_strategy=XXX 不是 SKIP/COVER）
     */
    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleMethodArgumentTypeMismatchException(MethodArgumentTypeMismatchException exception) {
        String name = exception.getName();
        Class<?> required = exception.getRequiredType();
        String expected = (required != null && required.isEnum())
            ? String.join("/", java.util.Arrays.stream(required.getEnumConstants())
                .map(Object::toString).toArray(String[]::new))
            : (required != null ? required.getSimpleName() : "value");
        String reason = "参数 " + name + " 取值非法，期望值：" + expected;
        log.error("MethodArgumentTypeMismatchException: {} expected={} got={}", name, expected, exception.getValue());
        return badRequest(reason);
    }

    /**
     * Multipart 请求本身异常（非 multipart 请求、解析失败等）。
     */
    @ExceptionHandler(MultipartException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleMultipartException(MultipartException exception) {
        String reason = "请求格式错误，需要 multipart/form-data 上传文件";
        log.error("MultipartException: {}", exception.getMessage());
        return badRequest(reason);
    }

    /**
     * Content-Type 不匹配。按接口声明的consumes动态提示期望类型：
     * 大多数接口期望application/json，仅文件上传类接口期望multipart/form-data，
     * 硬编码multipart提示会对JSON接口调用方产生误导。
     */
    @ExceptionHandler(HttpMediaTypeNotSupportedException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleHttpMediaTypeNotSupportedException(
        HttpMediaTypeNotSupportedException exception) {
        String supported = CollectionUtils.isEmpty(exception.getSupportedMediaTypes()) ? "application/json"
            : exception.getSupportedMediaTypes().stream().map(Object::toString).distinct()
                .collect(Collectors.joining("、"));
        String reason = "请求格式错误，Content-Type 不被该接口支持，期望：" + supported;
        log.error("HttpMediaTypeNotSupportedException: {}", exception.getMessage());
        return badRequest(reason);
    }

    /**
     * HTTP 方法不支持（如对仅支持 GET 的接口使用 POST 调用），返回 405 而非兜底的 500。
     * 错误信息统一走 i18n，不向响应体拼接 Spring 解析出的方法列表：
     * 路径变量映射会匹配出与业务无关的方法（如 /versions/{version_id} 可匹配 "references"），
     * 拼出来容易误导调用方，仅记录到日志供运维排查。
     */
    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleHttpRequestMethodNotSupportedException(
        HttpRequestMethodNotSupportedException exception) {
        Set<HttpMethod> supportedMethods = exception.getSupportedHttpMethods();
        String supported = CollectionUtils.isEmpty(supportedMethods) ? "未知"
            : supportedMethods.stream().map(HttpMethod::name).collect(Collectors.joining("/"));
        log.error("HttpRequestMethodNotSupportedException: {}, resolved supported methods: {}",
            exception.getMessage(), supported);
        ErrorInfo errorInfo = i18nUtil.getMessage(
            new AgentStudioException(StudioError.METHOD_NOT_SUPPORTED));
        ErrorRsp errorRsp = new ErrorRsp()
            .setErrorCode(StudioError.METHOD_NOT_SUPPORTED.getFullCode())
            .setErrorMsg(errorInfo.getMessage())
            .setErrorReason(errorInfo.getReason())
            .setErrorSuggestion(errorInfo.getSuggestion());
        // 透传 Spring 生成的 Allow 响应头（RFC 9110 要求 405 响应携带）
        return new ResponseEntity<>(errorRsp, exception.getHeaders(),
            StudioError.METHOD_NOT_SUPPORTED.getHttpStatus());
    }

    /** 构造 400 错误响应，error_reason 使用入参 reason（直接中文字面量），绕过 i18n 模板。 */
    private ResponseEntity<ErrorRsp> badRequest(String reason) {
        StudioError code = StudioError.METHOD_ARGUMENT_NOT_VALID;
        ErrorRsp rsp = new ErrorRsp()
            .setErrorCode(code.getFullCode())
            .setErrorMsg(i18nUtil.getMessage(code))
            .setErrorReason(reason)
            .setErrorSuggestion(i18nUtil.getSuggestion(code));
        return new ResponseEntity<>(rsp, code.getHttpStatus());
    }
}
