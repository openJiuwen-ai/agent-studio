/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.downstream;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.error.DownstreamService;

import java.util.Arrays;
import java.util.Optional;
import java.util.function.Function;

import org.springframework.web.reactive.function.client.ClientResponse;

import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * COM-04 §5.3: WebClient 共用 adapter/operator。
 * <p>
 * 统一 operator 在 {@link ClientResponse} 阶段保存 status，受限读取错误 body 并调用
 * parser；业务流中不得出现 {@code log.error("... error={}", errorBody)} 或
 * {@code onErrorResume(Exception.class, e -> new AgentStudioException(...))} 模式：
 * <ul>
 *   <li>已携带 {@link DownstreamFailure} 的异常（{@link DownstreamFailureException}）
 *       原样向最终出口传播，不得 catch-all 再改码；</li>
 *   <li>DNS、connect、TLS、read timeout、连接中断等未分类异常经
 *       {@code propagateOrTransportFailure} 转为 transport {@link DownstreamFailure}，
 *       对外默认映射 Manager 依赖失败（02001131/502）。</li>
 * </ul>
 *
 * <p>原始 body 只在受限解析局部存在，不进异常 message、不进日志。
 */
public final class DownstreamWebClientAdapter {

    private DownstreamWebClientAdapter() {
    }

    private static final ObjectMapper MAPPER = new ObjectMapper();

    /** SSE event 字段名（Runtime/Builder 把 event 类型嵌入 JSON data，非 SSE event: 字段）。 */
    private static final String EVENT_FIELD = "event";

    private static final String SSE_ERROR_EVENT = "error";

    /**
     * 非 2xx 的 {@code onStatus} handler：受限读取 body（截断至
     * {@link DownstreamErrorParser#MAX_BODY_BYTES}+1）→ parser →
     * {@code Mono.error(DownstreamFailureException)}。
     */
    public static Function<ClientResponse, Mono<? extends Throwable>> onStatusHandler(
            DownstreamService service, DownstreamErrorParser parser) {
        return response -> response.bodyToMono(byte[].class)
            .defaultIfEmpty(new byte[0])
            .map(body -> {
                byte[] bounded = bound(body);
                String contentType = null;
                try {
                    if (response.headers().contentType() != null) {
                        contentType = response.headers().contentType().toString();
                    }
                } catch (RuntimeException ignored) {
                    // Content-Type 仅诊断
                }
                Integer status = response.statusCode() != null ? response.statusCode().value() : null;
                DownstreamFailure failure = parser.parseHttp(service, Transport.WEBCLIENT,
                    status, contentType, bounded, null);
                return (Throwable) new DownstreamFailureException(failure);
            });
    }

    /**
     * 异常传播规则（替代 {@code onErrorResume(Exception.class)} catch-all）：
     * 已分类（{@link DownstreamFailureException}）原样传播；未分类转为 transport 失败。
     */
    public static <T> Flux<T> propagateOrTransportFailure(DownstreamService service,
                                                          DownstreamErrorParser parser,
                                                          Throwable e) {
        if (e instanceof DownstreamFailureException) {
            return Flux.error(e);
        }
        return Flux.error(new DownstreamFailureException(
            parser.fromTransportFailure(service, Transport.WEBCLIENT, e)));
    }

    /** 截断至 MAX+1 字节（超限由 parser 安全降级；多 1 字节用于检测）。 */
    private static byte[] bound(byte[] body) {
        if (body == null || body.length <= DownstreamErrorParser.MAX_BODY_BYTES + 1) {
            return body;
        }
        return Arrays.copyOf(body, DownstreamErrorParser.MAX_BODY_BYTES + 1);
    }

    /**
     * COM-04 §5.3: 检测 WebClient SSE 流内 error event。
     * <p>
     * WebClient {@code bodyToFlux(String.class)} 经 Spring
     * {@code ServerSentEventHttpMessageReader} 提取 SSE data 内容为 String——
     * Runtime/Builder 把 event 类型嵌入 JSON data（{@code {"event":"error",...}}，
     * 非 SSE {@code event:} 字段），故需解析 JSON 检查 {@code event} 字段。
     *
     * <p>检测到 {@code event=error} 时提取 {@code data} 子对象字节交 parser 严格解析；
     * 非 error event / 非 JSON / 解析失败 均返回 {@link Optional#empty()}——不构成失败事实，
     * 调用方不得将普通事件交给 mapper。
     *
     * @param service 调用适配器显式传入的下游身份
     * @param parser  统一解析器
     * @param chunk   WebClient 流内 String chunk（SSE data 内容）
     * @return 检测到 error event 时返回已解析 {@link DownstreamFailure}；否则 empty
     */
    public static Optional<DownstreamFailure> detectSseErrorEvent(
            DownstreamService service, DownstreamErrorParser parser, String chunk) {
        if (chunk == null || chunk.isBlank()) {
            return Optional.empty();
        }
        try {
            JsonNode root = MAPPER.readTree(chunk);
            if (root == null || !root.isObject()) {
                return Optional.empty();
            }
            JsonNode eventNode = root.get(EVENT_FIELD);
            if (eventNode == null || !eventNode.isTextual()
                || !SSE_ERROR_EVENT.equals(eventNode.asText())) {
                return Optional.empty();
            }
            // 提取 data 子对象字节（error_code 在 data 内层，非 chunk 顶层）
            byte[] dataBytes = null;
            JsonNode dataNode = root.get("data");
            if (dataNode != null) {
                dataBytes = MAPPER.writeValueAsBytes(dataNode);
            }
            return parser.parseSseError(service, Transport.WEBCLIENT,
                SSE_ERROR_EVENT, dataBytes, null);
        } catch (Exception e) {
            // 非 JSON / 损坏 / 非对象 → 非 error event（不抛第二异常）
            return Optional.empty();
        }
    }
}
