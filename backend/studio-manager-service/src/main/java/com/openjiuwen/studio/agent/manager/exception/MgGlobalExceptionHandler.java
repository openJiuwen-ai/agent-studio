/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception;

import com.alibaba.fastjson.JSONException;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.error.ErrorDescriptor;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.utils.ErrorInfo;
import org.springframework.util.CollectionUtils;
import org.springframework.web.HttpMediaTypeNotSupportedException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.multipart.MultipartException;
import org.springframework.web.multipart.support.MissingServletRequestPartException;
import java.util.stream.Collectors;
import com.openjiuwen.studio.agent.common.utils.LanguageUtils;
import com.openjiuwen.studio.agent.common.dto.ErrorDetail;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.foundation.base.exception.AgentBaseException;
import com.openjiuwen.studio.agent.manager.exception.contract.ManagerErrorCatalog;
import com.openjiuwen.studio.agent.manager.exception.contract.ManagerErrorDescriptorFactory;
import com.openjiuwen.studio.agent.manager.exception.contract.ManagerHttpErrorResponseBuilder;
import com.openjiuwen.studio.agent.manager.exception.downstream.DownstreamErrorMapper;
import com.openjiuwen.studio.agent.manager.exception.downstream.DownstreamErrorMappingCatalog;
import com.openjiuwen.studio.agent.manager.exception.downstream.DownstreamFailure;
import com.openjiuwen.studio.agent.manager.exception.downstream.DownstreamFailureException;
import com.openjiuwen.studio.agent.manager.exception.downstream.Transport;
import com.openjiuwen.studio.agent.common.error.DownstreamService;
import com.openjiuwen.studio.agent.common.error.ErrorDescriptorDiagnostics;

import feign.FeignException;

import jakarta.validation.ConstraintViolation;
import jakarta.validation.ConstraintViolationException;

import lombok.extern.slf4j.Slf4j;

import org.slf4j.MDC;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.jdbc.BadSqlGrammarException;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;
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
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.stream.Collectors;

/**
 * 功能描述 异常捕获类
 *
 */
@ControllerAdvice
@org.springframework.core.annotation.Order(org.springframework.core.Ordered.HIGHEST_PRECEDENCE)
@Slf4j
public class MgGlobalExceptionHandler {
    final I18nUtil i18nUtil;
    private final ManagerErrorDescriptorFactory factory;
    private final ManagerHttpErrorResponseBuilder httpBuilder;
    private final DownstreamErrorMapper downstreamMapper;

    public MgGlobalExceptionHandler(I18nUtil i18nUtil) {
        this.i18nUtil = i18nUtil;
        ManagerErrorCatalog catalog = new ManagerErrorCatalog();
        this.factory = new ManagerErrorDescriptorFactory(catalog);
        // COM-03 §5.1/#4: resolver 使用显式 locale,不读线程上下文
        this.httpBuilder = new ManagerHttpErrorResponseBuilder(
            (key, locale) -> i18nUtil.getMessage(key, locale));
        // COM-04 §4.3: 统一下游映射入口，由各传输 adapter 产出的 DownstreamFailure 经此一次映射
        this.downstreamMapper = new DownstreamErrorMapper(
            new DownstreamErrorMappingCatalog(catalog));
    }

    /**
     * COM-03 §4/#3: fail-closed 安全构建——httpBuilder.build() 失败时
     * 返回硬编码完整五字段安全响应,不让 Advice 自身失败。
     */
    private ResponseEntity<ErrorRsp> safeBuild(ErrorDescriptor descriptor, Locale locale) {
        try {
            return httpBuilder.build(descriptor, locale);
        } catch (Exception e) {
            log.error("HTTP builder failed, using safe fallback: {}", e.getMessage());
            ErrorRsp rsp = new ErrorRsp()
                .setErrorCode(descriptor.getErrorCode())
                .setErrorMsg("Internal server error.")
                .setErrorReason("An internal error occurred while processing the request.")
                .setErrorSuggestion("Please retry later; contact support if the issue persists.")
                .setRequestId(descriptor.getRequestId());
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.set("X-Request-Id", descriptor.getRequestId());
            return new ResponseEntity<>(rsp, headers,
                HttpStatus.valueOf(descriptor.getHttpStatus()));
        }
    }

    /** COM-04 §5.1: 读取当前 request-id（MDC，COM-05 CorrelationContextFilter 设置）；缺失返回 unknown。 */
    private static String currentRequestId() {
        String rid = MDC.get("request-id");
        return StringUtils.hasText(rid) ? rid : "unknown";
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
        log.error("handle AgentStudioException, code = {}",
            "openjiuwen." + agentStudioException.getErrorCode().getModule().getSubCode()
                + agentStudioException.getErrorCode().getCode(), agentStudioException);
        ErrorDescriptor descriptor = factory.fromAgentStudioException(agentStudioException);
        return safeBuild(descriptor, LanguageUtils.getLanguageLocale());
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
        log.error("BadSqlGrammarException: {}", exception.getMessage(), exception);
        ErrorDescriptor descriptor = factory.fromStudioError(StudioError.SQL_EXECUTE_FAILED, exception);
        return safeBuild(descriptor, LanguageUtils.getLanguageLocale());
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
        List<String> detailMessages = bindingResult.getFieldErrors().stream()
            .map(fe -> fe.getField() + ": " + fe.getDefaultMessage())
            .collect(Collectors.toList());
        log.error("throw MethodArgumentNotValidException: {}", String.join("; ", detailMessages));
        ErrorDescriptor descriptor = factory.fromValidation(
            StudioError.METHOD_ARGUMENT_NOT_VALID, detailMessages);
        return safeBuild(descriptor, LanguageUtils.getLanguageLocale());
    }

    /**
     * 处理 @PathVariable / @RequestParam 上的校验注解（@Size, @Pattern 等）失败
     */
    @ExceptionHandler(ConstraintViolationException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleConstraintViolationException(ConstraintViolationException exception) {
        List<String> detailMessages = exception.getConstraintViolations().stream()
            .map(violation -> {
                String paramName = violation.getPropertyPath().toString();
                if (paramName.contains(".")) {
                    paramName = paramName.substring(paramName.lastIndexOf('.') + 1);
                }
                return paramName + ": " + violation.getMessage();
            })
            .collect(Collectors.toList());
        log.error("throw ConstraintViolationException: {}", String.join("; ", detailMessages));
        ErrorDescriptor descriptor = factory.fromValidation(
            StudioError.METHOD_ARGUMENT_NOT_VALID, detailMessages);
        return safeBuild(descriptor, LanguageUtils.getLanguageLocale());
    }

    /**
     * NoResourceFoundException handling injection
     *
     * @param exception NoResourceFoundException
     * @return Return result
     */
    @ExceptionHandler(NoResourceFoundException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleNoResourceFoundException(NoResourceFoundException exception) {
        log.error("NoResourceFoundException: {}", exception.getMessage());
        ErrorDescriptor descriptor = factory.fromStudioError(
            StudioError.STATIC_RESOURCE_NOT_EXIST, exception);
        return safeBuild(descriptor, LanguageUtils.getLanguageLocale());
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
        ErrorDescriptor descriptor = factory.fromValidation(
            StudioError.STREAM_INTERFACE_EXECUTE_TIMEOUT, null);
        return safeBuild(descriptor, LanguageUtils.getLanguageLocale());
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
        log.error("SQLException: {}", exception.getMessage(), exception);
        ErrorDescriptor descriptor = factory.fromStudioError(StudioError.SQL_EXECUTE_FAILED, exception);
        return safeBuild(descriptor, LanguageUtils.getLanguageLocale());
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
        log.error("JsonException: {}", exception.getMessage(), exception);
        ErrorDescriptor descriptor = factory.fromStudioError(StudioError.JSON_CONVERT_ERROR, exception);
        return safeBuild(descriptor, LanguageUtils.getLanguageLocale());
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
        ErrorDescriptor descriptor = factory.fromValidation(
            StudioError.METHOD_ARGUMENT_NOT_VALID, null);
        return safeBuild(descriptor, LanguageUtils.getLanguageLocale());
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
        log.error("MaxUploadSizeExceededException: {}", exception.getMessage(), exception);
        ErrorDescriptor descriptor = factory.fromStudioError(StudioError.MAX_UPLOAD_SIZE_EXCEEDED, exception);
        return safeBuild(descriptor, LanguageUtils.getLanguageLocale());
    }

    /**
     * COM-03 §7.1 第 8 点：AgentBaseException 从 AgentBaseExceptionHandler 迁入。
     * foundation 旧模型统一映射为安全兜底码，cause 保留异常栈。
     */
    @ExceptionHandler(AgentBaseException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleAgentBaseException(AgentBaseException exception) {
        log.error("AgentBaseException: {}", exception.getMessage(), exception);
        ErrorDescriptor descriptor = factory.fromAgentBaseException(exception);
        return safeBuild(descriptor, LanguageUtils.getLanguageLocale());
    }

    /**
     * COM-03 §7.1 第 8 点 / COM-04 §5.1：FeignException 收口。
     * <p>
     * 已登记 Runtime/Builder 客户端的非 2xx 已由各自 ErrorDecoder 转为
     * {@code DownstreamFailureException}（见 {@link #handleDownstreamFailure}）。
     * 到达此处的 FeignException 是：transport failure（DNS/connect/TLS/read timeout，
     * 无 HTTP 响应、不经 ErrorDecoder）或未分类 Feign 客户端——统一转为携带
     * {@code EXTERNAL} 身份的 {@code DownstreamFailure}，经同一 mapper 一次映射，
     * 满足"HTTP 响应与 transport failure 产生同一种内部结果"。
     */
    @ExceptionHandler(FeignException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleFeignException(FeignException exception) {
        log.error("FeignException: {}", exception.getMessage(), exception);
        int status = exception.status();
        DownstreamFailure failure = status >= 0
            ? DownstreamFailure.httpResponse(
                DownstreamService.EXTERNAL,
                Transport.FEIGN, status, null, exception)
            : DownstreamFailure.transportFailure(
                DownstreamService.EXTERNAL,
                Transport.FEIGN, exception);
        return handleDownstreamFailure(new DownstreamFailureException(failure));
    }

    /**
     * COM-04 §5.1/§8: 统一下游失败处理。各传输 adapter（Feign ErrorDecoder /
     * ClientTemplate ResponseErrorHandler / WebClient operator / OkHttp SSE listener）
     * 解析下游响应后抛出 {@link DownstreamFailureException}，本 handler 只调用
     * {@code DownstreamErrorMapper} 一次，再交 COM-03 builder 输出标准五字段。
     * 不再解析 body、不二次选码。
     */
    @ExceptionHandler(DownstreamFailureException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleDownstreamFailure(DownstreamFailureException exception) {
        var failure = exception.getFailure();
        String requestId = currentRequestId();
        // 唯一一次映射
        ErrorDescriptor descriptor = downstreamMapper.map(failure, requestId);
        // 最终责任边界：结构化安全诊断 + 原始 cause 完整栈只记一次
        Throwable cause = failure.getCause();
        var diag = ErrorDescriptorDiagnostics.toSafeLogFields(descriptor);
        String traceId = MDC.get("trace-id");
        if (cause != null) {
            log.error("Downstream failure service={} transport={} phase={} trace_id={}: {}",
                failure.getService(), failure.getTransport(), failure.getPhase(), traceId, diag, cause);
        } else {
            log.error("Downstream failure service={} transport={} phase={} trace_id={}: {}",
                failure.getService(), failure.getTransport(), failure.getPhase(), traceId, diag);
        }
        return safeBuild(descriptor, LanguageUtils.getLanguageLocale());
    }

    /**
     * COM-03 §3.1：405 方法不允许——从 prompt ExceptionHandler 迁入并统一。
     */
    @ExceptionHandler(org.springframework.web.HttpRequestMethodNotSupportedException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleHttpRequestMethodNotSupportedException(
            org.springframework.web.HttpRequestMethodNotSupportedException exception) {
        java.util.Set<org.springframework.http.HttpMethod> supportedMethods = exception.getSupportedHttpMethods();
        String supported = org.springframework.util.CollectionUtils.isEmpty(supportedMethods) ? "未知"
            : supportedMethods.stream().map(org.springframework.http.HttpMethod::name).collect(java.util.stream.Collectors.joining("/"));
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

    /**
     * COM-03 §3.1：BindException——从 prompt ExceptionHandler 迁入，统一为校验错误。
     */
    @ExceptionHandler(org.springframework.validation.BindException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleBindException(
            org.springframework.validation.BindException exception) {
        BindingResult bindingResult = exception.getBindingResult();
        String errMessage = bindingResult.getFieldErrors().stream()
            .map(fe -> fe.getField() + ": " + fe.getDefaultMessage())
            .collect(Collectors.joining("; "));
        List<ErrorDetail> details = bindingResult.getFieldErrors().stream()
            .map(fe -> new ErrorDetail().setErrorMsg(fe.getField() + ": " + fe.getDefaultMessage()))
            .collect(Collectors.toList());
        log.warn("BindException: {}", errMessage);
        StudioError errorInfo = StudioError.METHOD_ARGUMENT_NOT_VALID;
        ErrorRsp errorRsp = new ErrorRsp().setErrorCode(errorInfo.getFullCode())
            .setErrorMsg(errMessage)
            .setErrorReason(i18nUtil.getMessage(errorInfo))
            .setErrorSuggestion(i18nUtil.getSuggestion(errorInfo))
            .setDetails(details);
        return new ResponseEntity<>(errorRsp, errorInfo.getHttpStatus());
    }

    /**
     * COM-03 §3.1/§4.6：DataAccessException——从 prompt ExceptionHandler 迁入，
     * 统一映射为 SQL 执行失败；原始异常栈作为 cause 保留，不通过新异常替换。
     */
    @ExceptionHandler(org.springframework.dao.DataAccessException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleDataAccessException(Exception exception) {
        log.error("DataAccessException: {}", exception.getMessage(), exception);
        ErrorDescriptor descriptor = factory.fromStudioError(StudioError.SQL_EXECUTE_FAILED, exception);
        return safeBuild(descriptor, LanguageUtils.getLanguageLocale());
    }

    /**
     * COM-03 §3.1：最终兜底——未知异常统一映射为安全内部错误。
     * 不得返回 exception.getMessage()；cause 保留供日志诊断。
     */
    @ExceptionHandler(Exception.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleUnknownException(Exception exception) {
        log.error("Unhandled exception: {}", exception.getMessage(), exception);
        ErrorDescriptor descriptor = factory.fromUnknown(exception);
        return safeBuild(descriptor, LanguageUtils.getLanguageLocale());
    }

    // === sync_01 新增 4xx handlers（保留业务语义，走 i18n + manual ErrorRsp）===

    @ExceptionHandler(MissingServletRequestPartException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleMissingServletRequestPartException(
        MissingServletRequestPartException exception) {
        String reason = "缺少必填参数：" + exception.getRequestPartName();
        log.error("MissingServletRequestPartException: {}", exception.getMessage());
        return badRequest(reason);
    }

    @ExceptionHandler(MissingServletRequestParameterException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleMissingServletRequestParameterException(
        MissingServletRequestParameterException exception) {
        String reason = "缺少必填参数：" + exception.getParameterName();
        log.error("MissingServletRequestParameterException: {}", exception.getMessage());
        return badRequest(reason);
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleMethodArgumentTypeMismatchException(
        MethodArgumentTypeMismatchException exception) {
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

    @ExceptionHandler(MultipartException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleMultipartException(
        MultipartException exception) {
        String reason = "请求格式错误，需要 multipart/form-data 上传文件";
        log.error("MultipartException: {}", exception.getMessage());
        return badRequest(reason);
    }

    @ExceptionHandler(HttpMediaTypeNotSupportedException.class)
    @ResponseBody
    public ResponseEntity<ErrorRsp> handleHttpMediaTypeNotSupportedException(
        HttpMediaTypeNotSupportedException exception) {
        String supported = org.springframework.util.CollectionUtils.isEmpty(exception.getSupportedMediaTypes()) ? "application/json"
            : exception.getSupportedMediaTypes().stream().map(Object::toString).distinct()
                .collect(java.util.stream.Collectors.joining("、"));
        String reason = "请求格式错误，Content-Type 不被该接口支持，期望：" + supported;
        log.error("HttpMediaTypeNotSupportedException: {}", exception.getMessage());
        return badRequest(reason);
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
