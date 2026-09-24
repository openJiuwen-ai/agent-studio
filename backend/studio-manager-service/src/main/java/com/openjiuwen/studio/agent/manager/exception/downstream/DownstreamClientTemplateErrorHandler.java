/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.downstream;

import com.openjiuwen.studio.agent.common.error.DownstreamService;

import java.io.IOException;
import java.io.InputStream;
import java.net.URI;

import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.client.ClientHttpResponse;
import org.springframework.web.client.DefaultResponseErrorHandler;

/**
 * COM-04 §5.2: ClientTemplate 专用 {@link org.springframework.web.client.ResponseErrorHandler}。
 * <p>
 * 把<b>全部非 2xx</b> 判为错误（不再仅 5xx/429——否则 DEF-06 的 400/404/409 绕过统一解析），
 * 读取一次受限 body（≤ {@link DownstreamErrorParser#MAX_BODY_BYTES}+1）后调用
 * {@link DownstreamErrorParser}，抛出 {@link DownstreamFailureException} 供统一 Advice 经
 * {@link DownstreamErrorMapper} 一次映射。
 *
 * <p>重试边界：本 handler 只分类不重试；RestTemplate 默认无自动重试，
 * 确定性 4xx（参数非法/任务不存在/状态冲突）不因本任务新增任何重试。
 * body 只在本类局部存在，不进异常 message、不进日志。
 */
public class DownstreamClientTemplateErrorHandler extends DefaultResponseErrorHandler {

    private final DownstreamService service;
    private final DownstreamErrorParser parser;

    public DownstreamClientTemplateErrorHandler(DownstreamService service, DownstreamErrorParser parser) {
        if (service == null) {
            throw new IllegalArgumentException("DownstreamService must not be null");
        }
        this.service = service;
        this.parser = parser;
    }

    /** 全部非 2xx 判为错误——DEF-06 的 400/404/409 必须进入统一解析。 */
    @Override
    protected boolean hasError(HttpStatusCode statusCode) {
        return !statusCode.is2xxSuccessful();
    }

    @Override
    public void handleError(URI url, HttpMethod method, ClientHttpResponse response) throws IOException {
        byte[] boundedBody = null;
        try (InputStream body = response.getBody()) {
            if (body != null) {
                boundedBody = DownstreamErrorParser.readBounded(body);
            }
        } catch (IOException e) {
            boundedBody = null;  // IO 异常 → 无可信原码（安全降级）
        }
        String contentType = null;
        try {
            if (response.getHeaders() != null && response.getHeaders().getContentType() != null) {
                contentType = response.getHeaders().getContentType().toString();
            }
        } catch (RuntimeException ignored) {
            // Content-Type 仅诊断，读取失败不影响解析
        }
        Integer status = response.getStatusCode() != null ? response.getStatusCode().value() : null;
        DownstreamFailure failure = parser.parseHttp(service, Transport.CLIENT_TEMPLATE,
            status, contentType, boundedBody, null);
        throw new DownstreamFailureException(failure);
    }
}
