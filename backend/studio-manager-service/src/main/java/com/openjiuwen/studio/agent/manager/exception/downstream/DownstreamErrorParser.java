/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.downstream;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import com.openjiuwen.studio.agent.common.error.DownstreamService;

import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.Optional;

/**
 * COM-04 §4.2: 统一下游错误解析器。HTTP 与 SSE 共用字段提取内核。
 * <p>
 * 严格规则：
 * <ol>
 *   <li>标准 HTTP 错误仅由非 2xx 响应进入解析（adapter 保证）；2xx legacy profile
 *       由具名 endpoint adapter 处理，通用 parser 不扫描任意成功 DTO；</li>
 *   <li>标准形态只读取顶层字符串 {@code error_code}；不递归搜索嵌套字段；</li>
 *   <li>SSE 只把明确 {@code event:error} 当错误；普通 message 含 {@code error_code} 不误判；</li>
 *   <li>canonical 码精确匹配 catalog 已识别定义；不补前缀、不改大小写、不把数字转 canonical；</li>
 *   <li>非 JSON、数组、空 body、字段非字符串、blank、未知码和损坏 UTF-8 均视为"无可信原码"；</li>
 *   <li>响应体固定 64 KiB 上限；超限停止解析并安全降级；</li>
 *   <li>{@code Content-Type} 仅诊断，不因漏标 JSON 拒绝结构完整且大小受控的标准 body；</li>
 *   <li>解析失败不抛第二业务异常，不替换原始 cause。</li>
 * </ol>
 *
 * <p>原始 body 只在本类局部存在，不进入 {@link DownstreamFailure}、不进异常 message、不进日志。
 */
public final class DownstreamErrorParser {

    /** 响应体字节上限（64 KiB）。超限即停止解析并安全降级。 */
    public static final int MAX_BODY_BYTES = 64 * 1024;

    /** SSE error event 名（仅此事件名触发 SSE 错误解析）。 */
    private static final String SSE_ERROR_EVENT = "error";

    /** 顶层 error_code 字段名（标准五字段形态）。 */
    private static final String ERROR_CODE_FIELD = "error_code";

    /** Builder pre-canonical8 裸 int code 字段名（桥接，等 Builder 迁 canonical8 后过时）。 */
    private static final String BUILDER_CODE_FIELD = "code";

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final DownstreamErrorMappingCatalog catalog;

    public DownstreamErrorParser(DownstreamErrorMappingCatalog catalog) {
        this.catalog = catalog;
    }

    /**
     * 解析非 2xx HTTP 响应体。caller 传入受限 body 字节（≤ {@link #MAX_BODY_BYTES}）。
     *
     * @param service        调用适配器显式传入的下游身份
     * @param transport       传输通道
     * @param downstreamHttpStatus 下游 HTTP 状态（仅诊断）
     * @param contentType     Content-Type（仅诊断，不决定是否解析）
     * @param boundedBody     受限 body 字节；null/空 → 无可信原码
     * @param cause           原始 cause（仅内部日志）
     */
    public DownstreamFailure parseHttp(DownstreamService service, Transport transport,
                                       Integer downstreamHttpStatus, String contentType,
                                       byte[] boundedBody, Throwable cause) {
        String trustedCode = extractTrustedErrorCode(service, boundedBody);
        return DownstreamFailure.httpResponse(service, transport, downstreamHttpStatus,
            trustedCode, cause);
    }

    /**
     * 解析 SSE 流内 error event。仅 {@code event:error} 触发；普通 message/其他 event
     * 返回 {@link Optional#empty()}——不构成失败事实，调用方不得将普通事件交给 mapper。
     *
     * @param eventName SSE event 名；非 {@code error} → empty（不是失败）
     * @param boundedData 受限 event data 字节
     */
    public Optional<DownstreamFailure> parseSseError(DownstreamService service, Transport transport,
                                                     String eventName, byte[] boundedData,
                                                     Throwable cause) {
        if (eventName == null || !SSE_ERROR_EVENT.equals(eventName)) {
            // 非 error event（含普通 message 中出现 error_code）不构成失败事实
            return Optional.empty();
        }
        String trustedCode = extractTrustedErrorCode(service, boundedData);
        return Optional.of(DownstreamFailure.sseEvent(service, transport, trustedCode, cause));
    }

    /** 传输层失败（无 HTTP 响应，无可信原码）。 */
    public DownstreamFailure fromTransportFailure(DownstreamService service, Transport transport,
                                                  Throwable cause) {
        return DownstreamFailure.transportFailure(service, transport, cause);
    }

    /**
     * 严格提取顶层字符串 {@code error_code} 并 trust-check。
     * <p>无可信原码的所有情况均返回 {@code null}：body null/空/超限、非 JSON、数组、
     * 字段缺失/非字符串/blank、未识别码、损坏 UTF-8、解析异常。
     */
    private String extractTrustedErrorCode(DownstreamService service, byte[] boundedBody) {
        if (boundedBody == null || boundedBody.length == 0) {
            return null;
        }
        if (boundedBody.length > MAX_BODY_BYTES) {
            // 超限：停止解析，安全降级（caller 已应受限读取，此处为双保险）
            return null;
        }
        JsonNode root;
        try {
            root = MAPPER.readTree(decodeStrictUtf8(boundedBody));
        } catch (JsonProcessingException e) {
            // 非 JSON / 损坏 → 无可信原码（不抛第二异常）
            return null;
        } catch (CharacterCodingException e) {
            // 损坏 UTF-8（含其他字段非法字节）→ 一律无可信原码
            return null;
        } catch (RuntimeException e) {
            // 其余解析异常 → 无可信原码
            return null;
        }
        if (root == null || !root.isObject()) {
            // 数组、标量等非对象 → 无可信原码
            return null;
        }
        JsonNode codeNode = root.get(ERROR_CODE_FIELD);
        if (codeNode != null && codeNode.isTextual()) {
            String code = codeNode.asText();
            if (code != null && !code.isBlank()
                && catalog.isRecognizedDownstreamCode(service, code)) {
                // 精确匹配 catalog 已识别 canonical8 定义；不补前缀、不改大小写、不把数字转 canonical
                return code;
            }
        }
        // 桥接（pre-canonical8）：Builder 裸 int "code" 字段——不经 canonical8 信任门，
        // 原样返回供 JiuWen catch / mapper 按业务语义判定（102155 幂等 / LLM 分类 / 默认 502）。
        // 等 Builder 迁 canonical8 后此分支过时，由 "error_code" 路径接管。
        if (service == DownstreamService.BUILDER) {
            JsonNode builderCodeNode = root.get(BUILDER_CODE_FIELD);
            if (builderCodeNode != null) {
                if (builderCodeNode.isNumber()) {
                    return String.valueOf(builderCodeNode.asInt());
                }
                if (builderCodeNode.isTextual()) {
                    String bc = builderCodeNode.asText();
                    if (bc != null && !bc.isBlank()) {
                        return bc;
                    }
                }
            }
        }
        return null;
    }

    /**
     * 严格 UTF-8 解码：非法字节（位于任何字段，包括不影响 error_code 的字段）
     * 一律抛 {@link CharacterCodingException} → 调用方视为无可信原码。
     * Java 默认 {@code new String(bytes, UTF_8)} 用替换字符容忍非法字节，不满足冻结规则。
     */
    private static String decodeStrictUtf8(byte[] bytes) throws CharacterCodingException {
        return StandardCharsets.UTF_8.newDecoder()
            .onMalformedInput(CodingErrorAction.REPORT)
            .onUnmappableCharacter(CodingErrorAction.REPORT)
            .decode(ByteBuffer.wrap(bytes))
            .toString();
    }
}
