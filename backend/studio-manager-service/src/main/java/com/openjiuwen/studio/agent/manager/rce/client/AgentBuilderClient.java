package com.openjiuwen.studio.agent.manager.rce.client;

import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.dto.md.ChatCompletionRequest;
import com.openjiuwen.studio.agent.common.dto.md.ModelServiceCheckReq;
import com.openjiuwen.studio.agent.common.dto.md.ModelServiceCheckRsp;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.runtime.EmbeddingRequest;
import com.openjiuwen.studio.agent.manager.dto.runtime.RankDocumentsRequest;
import com.openjiuwen.studio.agent.manager.rce.models.AskModelReq;
import jakarta.validation.Valid;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Flux;

/**
 * agent builder服务client
 *
 */
@FeignClient(name = "agentBuilder", url = "${feign.client.config.agentBuilder.url:}")
public interface AgentBuilderClient {

    /**
     * 运行模型调用接口
     *
     * @param authToken   String
     * @param askModelReq AskModelReq
     * @return 响应体
     */
    @PostMapping(path = "/v1/agent-builder/chat/completions", consumes = MediaType.APPLICATION_JSON_VALUE,
            produces = MediaType.APPLICATION_JSON_VALUE)
    ResponseEntity<JSONObject> askModel(@RequestHeader("X-Auth-Token") String authToken,
                                        @RequestHeader(value = "X-Auth-Id", required = false) String authId, @RequestBody AskModelReq askModelReq);


    @PostMapping("/v1/{project_id}/model-service/status/check")
    ResponseEntity<ModelServiceCheckRsp> modelServiceAvailableCheck(
            @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
            @PathVariable(value = "project_id") String projectId, @RequestBody ModelServiceCheckReq request);

    @PostMapping("/v1/agent-builder/rerank")
    Object rerank(
            @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
            @RequestParam("project_id") String projectId,
            @RequestParam("workspace_id") String workspaceId, @RequestBody @Valid RankDocumentsRequest request,
            @RequestParam("refresh") Boolean refresh);

    @PostMapping("/v1/agent-builder/embeddings")
    Object textEmbeddings(
            @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
            @RequestParam("project_id") String projectId,
            @RequestParam("workspace_id") String workspaceId, @RequestBody @Valid EmbeddingRequest request,
            @RequestParam("refresh") Boolean refresh);

    @PostMapping("/v1/agent-builder/chat/completions")
    Object chatCompletions(
            @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
            @RequestParam("project_id") String projectId,
            @RequestParam("workspace_id") String workspaceId, @RequestBody ChatCompletionRequest request,
            @RequestParam("refresh") boolean refresh);

    @PostMapping("/v1/agent-builder/chat/completions")
    Flux<Object> chatCompletionsStream(
            @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
            @RequestParam("project_id") String projectId,
            @RequestParam("workspace_id") String workspaceId, @RequestBody ChatCompletionRequest request,
            @RequestParam("refresh") boolean refresh);
}
