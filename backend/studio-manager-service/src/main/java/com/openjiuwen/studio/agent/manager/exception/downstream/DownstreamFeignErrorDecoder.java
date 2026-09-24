/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.downstream;

import com.openjiuwen.studio.agent.common.error.DownstreamService;

import feign.Response;
import feign.codec.ErrorDecoder;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

/**
 * COM-04 §5.1: Feign 专用 ErrorDecoder。
 * <p>
 * 每个 Feign 客户端配置注入对应的 {@link DownstreamService}（Runtime/Builder），
 * 显式确定来源身份（不按 URL/客户端名猜测）。读取受限响应体（≤ {@link DownstreamErrorParser#MAX_BODY_BYTES}
 * +1）后调用 {@link DownstreamErrorParser}，抛出 {@link DownstreamFailureException}
 * 供统一 Advice 经 {@link DownstreamErrorMapper} 一次映射。
 *
 * <p>不解析 {@code exception.getMessage()}；body 只在本 decoder 局部存在，不进异常 message、不进日志。
 * 读取失败或 IO 异常 → transportFailure（无可信原码，安全降级）。
 */
public final class DownstreamFeignErrorDecoder implements ErrorDecoder {

    private final DownstreamService service;
    private final DownstreamErrorParser parser;

    public DownstreamFeignErrorDecoder(DownstreamService service, DownstreamErrorParser parser) {
        if (service == null) {
            throw new IllegalArgumentException("DownstreamService must not be null");
        }
        this.service = service;
        this.parser = parser;
    }

    @Override
    public Exception decode(String methodKey, Response response) {
        Integer status = response != null ? response.status() : null;
        if (response == null || response.body() == null) {
            DownstreamFailure failure = parser.parseHttp(service, Transport.FEIGN,
                status, contentType(response), null, null);
            return new DownstreamFailureException(failure);
        }
        byte[] boundedBody = readBounded(response);
        Throwable cause = null;  // Feign error response 无底层异常；cause 留空
        DownstreamFailure failure = parser.parseHttp(service, Transport.FEIGN,
            status, contentType(response), boundedBody, cause);
        return new DownstreamFailureException(failure);
    }

    private static String contentType(Response response) {
        if (response == null || response.headers() == null) {
            return null;
        }
        return response.headers().get("Content-Type") != null
            ? response.headers().get("Content-Type").toString() : null;
    }

    /**
     * 受限读取响应体：最多读 {@link DownstreamErrorParser#MAX_BODY_BYTES} + 1 字节
     * （多读 1 字节用于检测超限，由 parser 安全降级）。读取/IO 异常 → 返回 null。
     */
    private static byte[] readBounded(Response response) {
        try (InputStream is = response.body().asInputStream()) {
            return DownstreamErrorParser.readBounded(is);
        } catch (IOException | RuntimeException e) {
            // 读取/IO 异常 → 无可信原码（parser 的 null body 路径）
            return null;
        }
    }
}
