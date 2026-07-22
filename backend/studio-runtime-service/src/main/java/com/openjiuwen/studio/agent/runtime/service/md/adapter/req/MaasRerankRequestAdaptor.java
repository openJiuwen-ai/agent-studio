/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.runtime.service.md.adapter.req;

import com.alibaba.fastjson.JSONObject;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.runtime.dto.md.RankDocumentsRequest;
import com.openjiuwen.studio.agent.runtime.http.HttpResponse;
import com.openjiuwen.studio.agent.runtime.service.md.adapter.req.mapper.MaasRequestMapper;
import com.openjiuwen.studio.agent.runtime.utils.JsonUtils;
import com.openjiuwen.studio.agent.runtime.utils.ModelInvokeExceptionUtil;

import lombok.Data;
import lombok.extern.slf4j.Slf4j;

import org.springframework.stereotype.Component;

import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * MaasRerankRequestAdaptor
 * 针对MAAS-Rerank模型调用的适配器, 完成模型请求参数的转换等;
 *
 * <p>本类持有 rerank 场景唯一的请求/响应转换实现 (docs -> documents 映射、按 index 排序 + topN 截断),
 * 并以静态方法形式暴露给 {@link AbstractRequestAdapter} 及其他通用 adapter 复用, 避免逻辑散落多处.
 *
 */
@Slf4j
@Component
public class MaasRerankRequestAdaptor extends AbstractRequestAdapter {
    private static final Comparator<RerankResult> RERANK_RESULT_COMPARATOR = Comparator.comparing(
        (RerankResult result) -> result.getIndex() == null ? Integer.MAX_VALUE : result.getIndex());

    @Override
    public String getName() {
        return "maas_rerank";
    }

    @Override
    public Object requestBodyConvert(Map<String, String> headers, Object body, boolean stream) {
        return convertRerankRequestBody(body);
    }

    @Override
    public JSONObject resBodyConvert(String url, HttpResponse<String> response, Object request) {
        if (!(request instanceof RankDocumentsRequest)) {
            throw new AgentStudioException(StudioError.MD_INVOKE_MODEL_SERVICE_FAIL);
        }

        Integer topN = ((RankDocumentsRequest) request).getTopN();
        return convertRerankResponseBody(url, response, topN);
    }

    /**
     * 将 {@link RankDocumentsRequest} 转换为 rerank 端点期望的请求体 (docs -> documents).
     * 供所有协议 adapter 在 rerank 场景复用, 保证字段名一致.
     *
     * @param body 原始请求体, 通常为 {@link RankDocumentsRequest}
     * @return 转换后的 {@link RerankRequest}; 非 rerank 请求原样返回
     */
    public static Object convertRerankRequestBody(Object body) {
        if (!(body instanceof RankDocumentsRequest)) {
            log.error("Not a 'RankDocumentRequest', do none conversation.");
            return body;
        }

        RerankRequest request = MaasRequestMapper.INSTANCE.toMaasRerankRequest((RankDocumentsRequest) body);
        // 兼容端点默认不返回 document 字段, 前端展示需要 document.text, 故强制要求返回
        request.setReturnDocuments(true);
        log.info("Got convert request: {}.", request);
        return request;
    }

    /**
     * 解析 rerank 响应: 按 index 升序排序并按 topN 截断.
     * 供所有协议 adapter 在 rerank 场景复用, 避免重复实现.
     *
     * @param url 模型服务 URL, 仅用于日志
     * @param response HTTP 响应
     * @param topN 截断数量, 为 null 时不截断
     * @return 解析后的响应 JSON
     */
    public static JSONObject convertRerankResponseBody(String url, HttpResponse<String> response, Integer topN) {
        if (response.getResponseBody() == null) {
            log.error("Empty http response! Api path: '{}'", url);
            throw new AgentStudioException(StudioError.MD_INVOKE_MODEL_SERVICE_FAIL);
        }
        if (response.getStatusCode() >= 300) {
            log.error("Invoke model service error. url:{} status:{} response:{}", url, response.getStatusCode(),
                response.getErrorResponseBody());
            throw ModelInvokeExceptionUtil.commonHttpExceptionHandler(response.getStatusCode(),
                response.getErrorResponseBody());
        }

        RerankResp rerankResp = JsonUtils.json2ObjQuietly(response.getResponseBody(), RerankResp.class);
        if (rerankResp == null) {
            throw new AgentStudioException(StudioError.MD_INVOKE_MODEL_SERVICE_FAIL);
        }

        List<RerankResult> results = rerankResp.getResults();
        if (results == null) {
            return JSONObject.parseObject(JsonUtils.toJson(rerankResp));
        }

        int limit = topN == null ? results.size() : Math.min(topN, results.size());
        results = results.stream().sorted(RERANK_RESULT_COMPARATOR).limit(limit).collect(Collectors.toList());
        rerankResp.setResults(results);

        return JSONObject.parseObject(JsonUtils.toJson(rerankResp));
    }

    /**
     * MAAS rerank 模型请求参数
     *
     */
    @Data
    public static final class RerankRequest {
        private String model;

        private String query;

        private List<String> documents;

        @JsonProperty("return_documents")
        private Boolean returnDocuments;
    }

    /**
     * MAAS rerank 模型请求返回
     *
     */
    @Data
    public static final class RerankResp {
        private String id;

        private String model;

        private RerankUsage rerankUsage;

        private List<RerankResult> results;
    }

    /**
     * RerankResult
     *
     */
    @Data
    public static final class RerankResult {
        private Integer index;

        private Document document;

        @JsonProperty("relevance_score")
        private Double relevanceScore;
    }

    /**
     * Document
     *
     */
    @Data
    public static final class Document {
        private String text;
    }

    /**
     * RerankUsage
     *
     */
    @Data
    public static final class RerankUsage {
        @JsonProperty("total_tokens")
        private Integer totalTokens;
    }
}
