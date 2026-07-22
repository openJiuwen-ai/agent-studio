/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.runtime.service.md;

import static com.openjiuwen.studio.agent.runtime.constant.Constant.REQUEST_ID;
import static com.openjiuwen.studio.agent.runtime.constant.Constant.TASK_ID;
import static com.openjiuwen.studio.agent.runtime.constant.Constant.X_REQUEST_ID;
import static com.openjiuwen.studio.agent.runtime.constant.Constant.X_TASK_ID;
import static com.openjiuwen.studio.agent.runtime.utils.OkHttpUtils.MEDIA_TYPE_JSON;

import com.alibaba.fastjson.JSONObject;
import com.openjiuwen.studio.agent.common.dto.md.ModelServiceCheckReq;
import com.openjiuwen.studio.agent.common.dto.md.ProviderAuth;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.utils.JsonUtils;
import com.openjiuwen.studio.agent.common.dto.md.ChatCompletionRequest;
import com.openjiuwen.studio.agent.runtime.dto.md.EmbeddingRequest;
import com.openjiuwen.studio.agent.runtime.dto.md.ImageGenerationReq;
import com.openjiuwen.studio.agent.common.dto.md.ModelInvokeBase;
import com.openjiuwen.studio.agent.runtime.dto.md.ModelServiceDetail;
import com.openjiuwen.studio.agent.runtime.dto.md.ModelStrategy;
import com.openjiuwen.studio.agent.runtime.dto.md.RankDocumentsRequest;
import com.openjiuwen.studio.agent.runtime.service.md.adapter.req.MaasRerankRequestAdaptor;
import com.openjiuwen.studio.agent.runtime.dto.md.VideoGenerationReq;
import com.openjiuwen.studio.agent.runtime.entity.md.ModelServiceBase;
import com.openjiuwen.studio.agent.runtime.enums.ModelStrategyEnum;
import com.openjiuwen.studio.agent.runtime.exception.OpenAiHttpException;
import com.openjiuwen.studio.agent.runtime.http.HttpResponse;
import com.openjiuwen.studio.agent.runtime.model.ModelApiLog;
import com.openjiuwen.studio.agent.runtime.service.md.adapter.auth.AuthAdapterFactory;
import com.openjiuwen.studio.agent.runtime.service.md.adapter.req.RequestAdapter;
import com.openjiuwen.studio.agent.runtime.service.md.adapter.req.RuntimeRequestAdapterFactory;
import com.openjiuwen.studio.agent.runtime.thread.ModelApiLogThreadLocal;
import com.openjiuwen.studio.agent.runtime.utils.AlarmLogUtil;
import com.openjiuwen.studio.agent.runtime.utils.OkHttpUtils;

import lombok.extern.slf4j.Slf4j;
import okhttp3.HttpUrl;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.apache.hc.client5.http.ConnectTimeoutException;
import org.apache.hc.client5.http.classic.methods.HttpGet;
import org.apache.hc.client5.http.classic.methods.HttpPost;
import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.core5.http.ContentType;
import org.apache.hc.core5.http.io.entity.EntityUtils;
import org.apache.hc.core5.http.io.entity.StringEntity;
import org.jetbrains.annotations.NotNull;
import org.slf4j.MDC;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.net.SocketTimeoutException;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

@Service
@Slf4j
public class RuntimeModelServiceManager {
    @Autowired
    private RuntimeModelHttpClientService httpClientService;

    @Autowired
    private RuntimeRequestAdapterFactory factory;

    @Autowired
    private ModelStorageService modelStorageService;

    // 10 分钟
    @Value("${model.strategy.default-timeout-ms:600000}")
    private int defaultTimeout;

    @Value("${model.platform.provider:100}")
    private String platformProviderId;

    @Value("${model.video.task.keep-time:604800}")
    private int videoTaskKeepTime;

    @Value("${model.invoke.debug:false}")
    private boolean modelDebugEnable;

    @Autowired
    private RedisClient redisClient;

    @Autowired
    private ModelAuthStorageService authStorageService;

    @Autowired
    private OkHttpUtils httpUtils;

    @Autowired
    private AlarmLogUtil alarmLogUtil;

    private ModelServiceDetail getModelServiceDetail(ModelStrategy strategy, String modelType) {
        if (strategy.getType() != ModelStrategyEnum.MODEL) {
            log.error("Model type is not {} ", modelType);
            throw new AgentStudioException(StudioError.MD_MODEL_TYPE_INVALID);
        }
        ModelServiceDetail detail = strategy.getModels().isEmpty() ? null : strategy.getModels().get(0);
        if (detail == null || !detail.isAvailable()) {
            log.error("Model is not available. {} ", detail == null ? "null" : detail.getModel().getModelName());
            throw new AgentStudioException(StudioError.MD_MODEL_SERVICE_NOT_AVAILABLE);
        }
        if (!modelType.equals(detail.getModel().getModelType())) {
            log.error("Model type is not {}  {}  {}", modelType, detail.getModel().getModelType(),
                detail.getModel().getModelName());
            throw new AgentStudioException(StudioError.MD_MODEL_TYPE_INVALID);
        }
        return detail;
    }

    private Object commonInvoke(String workspaceId, String modelId, Map<String, String> originHeaders,
        ModelInvokeBase request, boolean refreshModel, String modelType, String projectId, String authId,
        String ownerProjectId) {
        ModelApiLog apiLog = ModelApiLogThreadLocal.getApiLog();
        ModelStrategy modelStrategy = getAndValidModelStragy(workspaceId, modelId, refreshModel, apiLog, ownerProjectId,
            authId);

        ModelServiceDetail detail = getModelServiceDetail(modelStrategy, modelType);

        applyRateLimit(detail.getModel());

        apiLog.setProvider(detail.getModel().getProviderId());
        apiLog.setServiceKey(detail.getModel().getServiceKey());
        apiLog.setApi(detail.getModel().getApiUrl());

        return commonInvoke(originHeaders, request, detail);
    }

    Map<String, String> initRequestHeader(Map<String, String> originHeaders) {
        Map<String, String> headers = new HashMap<>();
        headers.put("Content-Type", originHeaders.getOrDefault("content-type", "application/json"));
        headers.put(X_REQUEST_ID, MDC.get(REQUEST_ID));
        headers.put(X_TASK_ID, MDC.get(TASK_ID));
        return headers;
    }

    public JSONObject commonInvoke(Map<String, String> originHeaders, ModelInvokeBase request,
        ModelServiceDetail detail) {
        RequestAdapter adapter = factory.getAdapter(detail.getModel().getInterfaceProtocol());

        try {
            request.setModel(detail.getModel().getModelName());
            Object body = request instanceof RankDocumentsRequest
                ? MaasRerankRequestAdaptor.convertRerankRequestBody(request)
                : adapter.requestBodyConvert(originHeaders, request, false);

            Map<String, String> headers = initRequestHeader(originHeaders);

            String url = detail.getModel().getApiUrl();

            headers = AuthAdapterFactory.getAuthAdapter(detail.getAuth())
                .requestHeaderHandler(url, "POST", originHeaders, headers, body, detail.getAuth());

            adapter.postAuthHandler(originHeaders, headers, body, false);

            HttpResponse<String> response = sendPost(url, headers, JsonUtils.encode(body));
            return adapter.resBodyConvert(url, response, request);
        } catch (Exception e) {
            String msg = "Fail invoke model. url:" + detail.getModel().getApiUrl();
            String reson = e.getMessage();
            if (e instanceof AgentStudioException) {
                reson = ((AgentStudioException) e).getErrorCode().toString();
            }
            alarmLogUtil.logAlarm("LLM", msg, reson);
            throw adapter.requestExceptionHandler(e);
        }
    }

    /**
     * textEmbeddings
     *
     * @param workspaceId 空间ID
     * @param modelId 模型ID
     * @param originHeaders 请求头
     * @param request 请求
     * @param refreshModel 是否事实刷新模型
     * @return 排序结果
     */
    public Object textEmbeddings(String workspaceId, String modelId, Map<String, String> originHeaders,
        EmbeddingRequest request, boolean refreshModel, String projectId, String authId, String ownerProjectId) {
        return commonInvoke(workspaceId, modelId, originHeaders, request, refreshModel, "Text-Embedding", projectId,
            authId, ownerProjectId);
    }

    /**
     * 文本排序
     *
     * @param workspaceId 空间ID
     * @param modelId 模型ID
     * @param headers 请求头
     * @param request 请求
     * @param refreshModel 是否事实刷新模型
     * @return 排序结果
     */
    public Object rerank(String workspaceId, String modelId, Map<String, String> headers, RankDocumentsRequest request,
        boolean refreshModel, String projectId, String authId, String ownerProjectId) {
        return commonInvoke(workspaceId, modelId, headers, request, refreshModel, "RERANK", projectId, authId,
            ownerProjectId);
    }

    /**
     * 图片生成
     *
     * @param workspaceId 空间ID
     * @param modelId 模型ID
     * @param headers 请求头
     * @param request 请求
     * @param refreshModel 是否事实刷新模型
     * @return 排序结果
     */
    public Object imageGenerations(String workspaceId, String modelId, Map<String, String> headers, ImageGenerationReq request,
        boolean refreshModel, String projectId, String authId, String ownerProjectId) {
        return commonInvoke(workspaceId, modelId, headers, request, refreshModel, "TEXT-TO-IMAGE", projectId, authId,
            ownerProjectId);
    }

    /**
     * 视频生成
     *
     * @param workspaceId 空间ID
     * @param modelId 模型ID
     * @param headers 请求头
     * @param request 请求
     * @param refreshModel 是否事实刷新模型
     * @return 排序结果
     */
    public Object videoGenerations(String workspaceId, String modelId, Map<String, String> headers,
        VideoGenerationReq request, boolean refreshModel, String projectId, String authId, String ownerProjectId) {
        ModelApiLog apiLog = ModelApiLogThreadLocal.getApiLog();
        ModelStrategy modelStrategy = getAndValidModelStragy(workspaceId, modelId, refreshModel, apiLog, ownerProjectId,
            authId);

        ModelServiceDetail detail = getModelServiceDetail(modelStrategy, "TEXT-TO-VIDEO");

        applyRateLimit(detail.getModel());

        apiLog.setServiceKey(detail.getModel().getServiceKey());
        apiLog.setApi(detail.getModel().getApiUrl());
        apiLog.setProvider(detail.getModel().getProviderId());

        JSONObject rsp = commonInvoke(headers, request, detail);
        String taskId = rsp.getString("task_id");

        JSONObject taskCache = new JSONObject();
        taskCache.put("owner_project_id", ownerProjectId);
        taskCache.put("auth_id", detail.getAuth().getAuthId());
        taskCache.put("project_id", projectId);
        taskCache.put("model_id", detail.getModel().getId());
        taskCache.put("model_name", detail.getModel().getModelName());
        taskCache.put("url", detail.getModel().getApiUrl());
        taskCache.put("workspace_id", workspaceId);
        taskCache.put("provider_id", detail.getModel().getProviderId());
        redisClient.set("video_generator_" + projectId + "_" + taskId, taskCache.toJSONString(), Duration.ofSeconds(videoTaskKeepTime));

        return rsp;
    }

    public Object queryVideoGenerationTask(String projectId, String workspaceId, String authId, String taskId) {
        String taskCache = redisClient.get("video_generator_" + projectId + "_" + taskId);
        if (StringUtils.isEmpty(taskCache)) {
            log.error("Not found video generation task. project:{} task:{}", projectId, taskId);
            throw new AgentStudioException(StudioError.MD_VIDEO_GENERATION_TASK_NOT_EXIST);
        }
        JSONObject task = JSONObject.parseObject(taskCache);
        String providerId = task.getString("provider_id");
        String ownerProjectId = task.getString("owner_project_id");
        ProviderAuth auth;
        try {
            auth = authStorageService.queryProviderAuth(ownerProjectId, workspaceId, providerId,
                task.getString("auth_id"), false, "");
        } catch (Exception e) {
            try {
                auth = authStorageService.queryProviderAuth(ownerProjectId, workspaceId, providerId, authId, false, "");
            } catch (Exception exp) {
                throw e;
            }
        }

        RequestAdapter adapter = factory.getAdapter("openai");
        try {

            Map<String, String> headers = initRequestHeader(new HashMap<>());
            String url = task.getString("url") + "/" + taskId;

            headers = AuthAdapterFactory.getAuthAdapter(auth)
                .requestHeaderHandler(url, "GET", new HashMap<>(), headers, "", auth);

            HttpResponse<String> response = sendGet(url, headers);
            return adapter.resBodyConvert(url, response, "");
        } catch (Exception e) {
            throw adapter.requestExceptionHandler(e);
        }
    }

    /**
     * 大模型回话
     *
     * @param workspaceId 空间ID
     * @param modelId 模型服务ID
     * @param stream 是否流式调用
     * @param originHeaders 请求头
     * @param requestBody 请求体
     * @param refresh 是否刷新模型信息
     * @return 响应消息
     */
    public Object chatCompletions(String workspaceId, String modelId, boolean stream, Map<String, String> originHeaders,
        ChatCompletionRequest requestBody, boolean refresh, String projectId, String authId, String ownerProjectId) {

        ModelApiLog apiLog = ModelApiLogThreadLocal.getApiLog();
        ModelStrategy modelStrategy = getAndValidModelStragy(workspaceId, modelId, refresh, apiLog, ownerProjectId,
            authId);

        int retryTime = modelStrategy.getRetryCount() == null ? 0 : modelStrategy.getRetryCount();
        retryTime = Math.max(retryTime, 0);

        int timeout = modelStrategy.getStrategyTimeout() == null ? defaultTimeout : modelStrategy.getStrategyTimeout();
        timeout = Math.max(timeout, 5000);

        if (ModelStrategyEnum.MODEL == modelStrategy.getType()) {
            return doChatCompletions(apiLog, modelStrategy.getModels().get(0), stream, originHeaders, requestBody);
        } else {
            long beginTime = System.currentTimeMillis();
            boolean haveAvailableModel = false;
            Object result = null;
            for (ModelServiceDetail detail : modelStrategy.getModels()) {
                if (detail.isFreeModel()) {
                    apiLog.setFreeModel(true);
                } else {
                    apiLog.setFreeModel(false);
                    if (!detail.isAvailable()) {
                        continue;
                    }
                }

                haveAvailableModel = true;
                int curRetryTime = retryTime + 1;
                while (curRetryTime > 0) {
                    --curRetryTime;
                    if (System.currentTimeMillis() - beginTime > timeout) {
                        log.error(
                            "Strategy model service process timeout, please try again later! start:{} timeout:{} ",
                            beginTime, timeout);
                        throw new OpenAiHttpException(400,
                            "Strategy model service process timeout, please try again later!");
                    }

                    try {
                        result = doChatCompletions(apiLog, detail, stream, originHeaders, requestBody);
                        break;
                    } catch (Throwable throwable) {
                        log.warn("Strategy model service process exception. retry:{}", curRetryTime, throwable);
                    }
                }
                if (result != null) {
                    break;
                }
            }
            if (result != null) {
                return result;
            }
            if (!haveAvailableModel) {
                log.error("Model strategy no available model.");
                throw new AgentStudioException(StudioError.MD_MODEL_SERVICE_NOT_AVAILABLE);
            }
            throw new OpenAiHttpException(400, "Strategy model service process failed");
        }
    }

    private @NotNull ModelStrategy getAndValidModelStragy(String workspaceId, String modelId, boolean refresh,
        ModelApiLog apiLog, String projectId, String authId) {
        apiLog.setModelId(modelId);
        // 适配有符号的modelId
        modelId = modelId != null && modelId.contains("|") ? modelId.substring(modelId.indexOf('|') + 1) : modelId;

        ModelStrategy modelStrategy = modelStorageService.queryModelStrategy(projectId, workspaceId, modelId, authId,
            refresh);
        if (modelStrategy == null) {
            apiLog.setModelName(modelId);
            log.error("Fail get model strategy. id:{} workspaceId:{}", modelId, workspaceId);
            throw new AgentStudioException(StudioError.MD_MODEL_SERVICE_NOT_PUBLISH);
        }

        apiLog.setModelName(modelStrategy.getName());
        return modelStrategy;
    }

    private Object doChatCompletions(ModelApiLog apiLog, ModelServiceDetail modelDetail, boolean stream,
        Map<String, String> originHeaders, ChatCompletionRequest requestBody) {
        if (modelDetail.getAuth() == null) {
            if (modelDetail.getModel() != null && modelDetail.getModel().getProviderId() != null
                    && modelDetail.getModel().getProviderId().equals(platformProviderId)) {
                log.error("The free quota has been used up, providerId is {}, modelId is {}",
                        modelDetail.getModel().getProviderId(), modelDetail.getModel().getId());
                throw new AgentStudioException(StudioError.MD_FREE_MODEL_TOKENS_USED_UP);
            }
            log.error(
                    "Model auth config is not available. model exist = {} auth exist = {} projectId:{} workspace:{} model:{}",
                    modelDetail.getModel() != null, null, apiLog.getProjectId(), apiLog.getWorkspaceId(),
                    modelDetail.getModel() == null ? "null" : modelDetail.getModel().getId());
            throw new AgentStudioException(StudioError.MD_PROVIDER_AUTH_DATA_NOT_EXIST);
        }
        if (!modelDetail.isAvailable()) {
            log.error("Model is not available. model exist = {} auth exist = {} projectId:{} workspace:{} model:{}",
                modelDetail.getModel() != null, true, apiLog.getProjectId(), apiLog.getWorkspaceId(),
                modelDetail.getModel() == null ? "null" : modelDetail.getModel().getId());
            throw new AgentStudioException(StudioError.MD_MODEL_SERVICE_NOT_AVAILABLE);
        }

        applyRateLimit(modelDetail.getModel());

        apiLog.setApi(modelDetail.getModel().getApiUrl());
        apiLog.setServiceKey(modelDetail.getModel().getServiceKey());
        apiLog.setProvider(modelDetail.getModel().getProviderId());

        RequestAdapter adapter = factory.getAdapter(modelDetail.getModel().getInterfaceProtocol());

        try {
            requestBody.setModel(modelDetail.getModel().getModelName());
            Object body = adapter.requestBodyConvert(originHeaders, requestBody, stream);

            Map<String, String> headers = initRequestHeader(originHeaders);
            String url = modelDetail.getModel().getApiUrl();
            headers = AuthAdapterFactory.getAuthAdapter(modelDetail.getAuth())
                .requestHeaderHandler(url, "POST", originHeaders, headers, body, modelDetail.getAuth());

            adapter.postAuthHandler(originHeaders, headers, body, stream);
            String bodyStr = JsonUtils.encode(body);
            try {
                if (stream) {
                    HttpResponse<String> response = sendPostByStream(url, headers, bodyStr);
                    return adapter.streamResBodyConvert(url, response);
                } else {
                    HttpResponse<String> response = sendPost(url, headers, bodyStr);
                    return adapter.resBodyConvert(url, response, requestBody);
                }
            } catch (Exception e) {
                log.error("Fail invoke model. url:{} body:{} authId:{}", url, bodyStr,
                    modelDetail.getAuth().getAuthId());
                String msg = "Fail invoke model. url:" + url;
                String detail = e.getMessage();
                if (e instanceof AgentStudioException) {
                    detail = ((AgentStudioException) e).getErrorCode().toString();
                    StudioError error = ((AgentStudioException) e).getErrorCode();
                    if (Strings.CS.equals(modelDetail.getModel().getProviderId(), platformProviderId)) {
                        if (error == StudioError.MD_MODEL_SERVICE_REQUEST_TIMEOUT) {
                            log.error("check the network connection or mas model server");
                        }
                        if (error == StudioError.MD_MODEL_SERVICE_NOT_EXIST) {
                            log.error("model not exist, name: {}, check mas model server", modelDetail.getModel().getModelName());
                        }
                        if (error == StudioError.MD_MODEL_SERVICE_NOT_AVAILABLE) {
                            log.error("model service not available, name: {}, check mas model server", modelDetail.getModel().getModelName());
                        }
                    }
                }
                alarmLogUtil.logAlarm("LLM", msg, detail);
                if (modelDebugEnable) {
                    log.error("Fail invoke model. Header:{}", JsonUtils.encode(headers));
                }
                throw e;
            }
        } catch (Exception e) {
            throw adapter.requestExceptionHandler(e);
        }
    }

    private HttpResponse<String> sendPostByStream(String url, Map<String, String> headers, String bodyStr) {
        HttpUrl httpUrl = HttpUrl.parse(url);
        if (httpUrl == null) {
            throw new AgentStudioException(StudioError.MD_URL_INVALID, url);
        }
        HttpUrl.Builder urlBuilder = httpUrl.newBuilder();
        Request.Builder builder = new Request.Builder().url(urlBuilder.build());
        if (!headers.isEmpty()) {
            headers.forEach((key, value) -> {
                if (value != null) {
                    builder.addHeader(key, value);
                }
            });
        }
        RequestBody body = RequestBody.create(bodyStr, MEDIA_TYPE_JSON);
        Request request = builder.post(body).build();
        long start = System.currentTimeMillis();
        try {
            String responseString = null;
            InputStream contentStream;
            Response response = httpUtils.getModelRequestHttpClient(url).newCall(request).execute();
            String contentTypeHeader = response.headers().toString();
            // 兼容场景：流式请求，返回非流式报错，状态码却为200
            if (response.code() >= 300 || !contentTypeHeader.contains("stream")) {
                byte[] bodyBytes = (response.body() != null ? response.body().string() : "").getBytes();
                responseString = new String(bodyBytes, StandardCharsets.UTF_8);
                contentStream = new ByteArrayInputStream(bodyBytes);
            } else if (response.body() != null) {
                contentStream = response.body().byteStream();
            } else {
                contentStream = new ByteArrayInputStream(new byte[] {});
            }
            HttpResponse<String> httpResponse = HttpResponse.<String>builder()
                .statusCode(response.code()) // 设置状态码
                .headers(httpClientService.header2Map(response.headers())) // 设置返回头
                .responseBody(responseString) // 设置返回体
                .streamResponse(contentStream) // 设置流式返回体
                .errorResponseBody(responseString) // 设置错误返回体
                .rawResponse(response)
                .build();
            log.info("Stream request Success. {}, cost: {} ms", url, System.currentTimeMillis() - start);
            return httpResponse;
        } catch (AgentStudioException e) {
            alarmLogUtil.logAlarm("LLM", "Fail invoke model. url:" + url, e.getErrorCode().toString());
            throw e;
        } catch (SocketTimeoutException e) {
            log.error("Stream Request {} timeout. {}", url, e.getMessage());
            alarmLogUtil.logAlarm("LLM", "Stream Request {} timeout. url url:" + url, e.getMessage());
            throw new AgentStudioException(StudioError.MD_MODEL_SERVICE_REQUEST_TIMEOUT);
        } catch (Exception e) {
            log.error("Fail Stream request {}, cost: {} ms", url, System.currentTimeMillis() - start, e);
            alarmLogUtil.logAlarm("LLM", "Fail Stream request " + url, e.getMessage());
            throw new AgentStudioException(StudioError.MD_MODEL_SERVICE_REQUEST_INTERNAL_ERROR);
        }
    }

    private HttpResponse<String> sendPost(String url, Map<String, String> headers, String bodyStr) {
        HttpPost httpPost = new HttpPost(url);
        httpPost.setEntity(new StringEntity(bodyStr, ContentType.APPLICATION_JSON));
        headers.forEach(httpPost::setHeader);

        long start = System.currentTimeMillis();
        HttpResponse<String> response = null;
        try {
            CloseableHttpClient client = httpClientService.getModelRequestHttpClient(httpPost.getUri().getHost());
            response = client.execute(httpPost, res -> {
                String responseString = res.getEntity() == null ? null : EntityUtils.toString(res.getEntity(), "UTF-8");
                HttpResponse<String> httpResponse = HttpResponse.<String>builder()
                    .statusCode(res.getCode()) // 设置状态码
                    .headers(httpClientService.header2Map(res.getHeaders())) // 设置返回头
                    .responseBody(responseString) // 设置返回体
                    .streamResponse(null) // 设置流式返回体
                    .errorResponseBody(res.getCode() >= 300 ? responseString : null) // 设置错误返回体
                    .build();
                log.info("Success request {}, cost: {} ms", url, System.currentTimeMillis() - start);
                return httpResponse;
            });
            return response;
        } catch (AgentStudioException e) {
            alarmLogUtil.logAlarm("LLM", "Fail invoke model. url:" + url, e.getErrorCode().toString());
            throw e;
        } catch (ConnectTimeoutException e) {
            log.error("Request {} timeout. {}", url, e.getMessage());
            alarmLogUtil.logAlarm("LLM", "Request " + url + "timeout. ", e.getMessage());
            throw new AgentStudioException(StudioError.MD_MODEL_SERVICE_REQUEST_TIMEOUT);
        } catch (Exception e) {
            log.error("Fail request {}, cost: {} ms", url, System.currentTimeMillis() - start, e);
            alarmLogUtil.logAlarm("LLM", "Fail request " + url, e.getMessage());
            throw new AgentStudioException(StudioError.MD_MODEL_SERVICE_REQUEST_INTERNAL_ERROR);
        }
    }

    private HttpResponse<String> sendGet(String url, Map<String, String> headers) {
        HttpGet httpGet = new HttpGet(url);
        headers.forEach(httpGet::setHeader);

        long start = System.currentTimeMillis();
        HttpResponse<String> response;
        try {
            CloseableHttpClient client = httpClientService.getModelRequestHttpClient(httpGet.getUri().getHost());
            response = client.execute(httpGet, res -> {
                String responseString = res.getEntity() == null ? null : EntityUtils.toString(res.getEntity(), "UTF-8");
                HttpResponse<String> httpResponse = HttpResponse.<String>builder()
                    .headers(httpClientService.header2Map(res.getHeaders())) // 设置返回头
                    .statusCode(res.getCode()) // 设置状态码
                    .responseBody(responseString) // 设置返回体
                    .errorResponseBody(res.getCode() >= 300 ? responseString : null) // 设置错误返回体
                    .streamResponse(null) // 设置流式返回体
                    .build();
                log.info("Success do get request {}, cost: {} ms", url, System.currentTimeMillis() - start);
                return httpResponse;
            });
            return response;
        } catch (AgentStudioException e) {
            throw e;
        } catch (ConnectTimeoutException e) {
            log.error("GetRequest {} timeout. {}", url, e.getMessage());
            throw new AgentStudioException(StudioError.MD_MODEL_SERVICE_REQUEST_TIMEOUT);
        } catch (Exception e) {
            log.error("Fail do get request {}, cost: {} ms", url, System.currentTimeMillis() - start, e);
            throw new AgentStudioException(StudioError.MD_MODEL_SERVICE_REQUEST_INTERNAL_ERROR);
        }
    }

    private void applyRateLimit(ModelServiceBase model) {
        if (model.getThrottlingPolicy() == null || model.getThrottlingPolicy() < 10) {
            return;
        }

        long count = redisClient.getAndIncrement(model.getId(), 1);
        if (count > model.getThrottlingPolicy()) {
            log.error("Request invoke too many. limit:{} count:{}", model.getThrottlingPolicy(), count);
            throw new AgentStudioException(StudioError.MD_INVOKE_TOO_MANY_REQUEST);
        }
    }

    public ModelServiceDetail createModelServiceDetail(ModelServiceCheckReq req) {
        ModelServiceDetail detail = new ModelServiceDetail();
        detail.setAvailable(true);

        ProviderAuth auth = authStorageService.getProviderAuth("", req.getAuthType(),
            com.openjiuwen.studio.agent.runtime.utils.JsonUtils.toJson(req.getAuthInfo()));
        detail.setAuth(auth);

        ModelServiceBase model = new ModelServiceBase();
        model.setModelName(req.getModelName());
        model.setApiUrl(req.getApiUrl());
        model.setInterfaceProtocol(req.getInterfaceProtocol());

        detail.setModel(model);
        return detail;
    }
}



