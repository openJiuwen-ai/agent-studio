/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.service.v2.job;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceBase;
import com.openjiuwen.studio.agent.manager.entity.md.ProviderAuthMetadata;
import com.openjiuwen.studio.agent.manager.mapper.md.ModelServiceMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ProviderAuthDataMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ProviderAuthMetadataMapper;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.prompt.engineering.constant.CommonConstant;
import com.openjiuwen.studio.prompt.engineering.dto.Case;
import com.openjiuwen.studio.prompt.engineering.dto.ModelCase;
import com.openjiuwen.studio.prompt.engineering.entity.v2.PromptBuildRequest;
import com.openjiuwen.studio.prompt.engineering.entity.v2.PromptBuildResponse;
import com.openjiuwen.studio.prompt.engineering.entity.v2.PromptFeedbackRequest;
import com.openjiuwen.studio.prompt.engineering.entity.v2.PromptTaskDetailVo;
import com.openjiuwen.studio.prompt.engineering.entity.v2.PromptVar;
import com.openjiuwen.studio.prompt.engineering.enums.ResponseCode;
import com.openjiuwen.studio.prompt.engineering.enums.v2.PromptTaskStatusEnum;
import com.openjiuwen.studio.prompt.engineering.enums.v2.PtTypeEnum;
import com.openjiuwen.studio.prompt.engineering.mapper.v2.PromptTaskMapper;
import com.openjiuwen.studio.prompt.engineering.remote.ClientTemplate;
import com.openjiuwen.studio.prompt.engineering.service.model.v2.jiuwen.JIuWenPromptBaseRes;
import com.openjiuwen.studio.prompt.engineering.service.model.v2.jiuwen.JiuWenCreTaskReq;
import com.openjiuwen.studio.prompt.engineering.service.model.v2.jiuwen.JiuWenCreTaskRes;
import com.openjiuwen.studio.prompt.engineering.service.model.v2.jiuwen.JiuWenJobDeatails;
import com.openjiuwen.studio.prompt.engineering.service.model.v2.jiuwen.JiuWenJobInfo;
import com.openjiuwen.studio.prompt.engineering.service.model.v2.jiuwen.JiuWenOptimizeInfo;
import com.openjiuwen.studio.prompt.engineering.service.model.v2.jiuwen.JiuWenPromptBatchReq;
import com.openjiuwen.studio.prompt.engineering.service.model.v2.jiuwen.JiuWenPromptBatchRes;
import com.openjiuwen.studio.prompt.engineering.service.model.v2.jiuwen.JiuWenPromptDeatilRes;
import com.openjiuwen.studio.prompt.engineering.service.v2.PromptEngineerDataSetService;
import com.openjiuwen.studio.prompt.engineering.utils.JsonUtil;

import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;

@Slf4j
@Component
public class JiuWenPromptTaskJob implements Job {

    private static final String TEMPLATES_OPTIMIZATION_CREATE_MULTI_API
        = "/flask/v1/MMprompt/templates_optimization/jobs";

    private static final String TEMPLATES_OPTIMIZATION_PROGRESS_MULTI_API
        = "/flask/v1/MMprompt/templates_optimization/jobs/%s";

    private static final String TEMPLATES_OPTIMIZATION_BATCH_PROGRESS_MULTI_API
        = "/flask/v1/MMprompt/templates_optimization/jobs/get_infos";

    private static final String TEMPLATES_OPTIMIZATION_STOP_MULTI_API
        = "/flask/v1/MMprompt/templates_optimization/jobs/%s/stop";

    private static final String TEMPLATES_OPTIMIZATION_RESTART_MULTI_API
        = "/flask/v1/MMprompt/templates_optimization/jobs/%s/restart";

    private static final String TEMPLATES_OPTIMIZATION_DELETE_MULTI_API
        = "/flask/v1/MMprompt/templates_optimization/jobs/%s";

    private static final String TEMPLATES_OPTIMIZATION_CREATE_API = "/flask/v1/prompt/templates_optimization/jobs";

    private static final String TEMPLATES_OPTIMIZATION_PROGRESS_API = "/flask/v1/prompt/templates_optimization/jobs/%s";

    private static final String TEMPLATES_OPTIMIZATION_BATCH_PROGRESS_API
        = "/flask/v1/prompt/templates_optimization/jobs/get_infos";

    private static final String TEMPLATES_OPTIMIZATION_STOP_API
        = "/flask/v1/prompt/templates_optimization/jobs/%s/stop";

    private static final String TEMPLATES_OPTIMIZATION_RESTART_API
        = "/flask/v1/prompt/templates_optimization/jobs/%s/restart";

    private static final String TEMPLATES_OPTIMIZATION_DELETE_API = "/flask/v1/prompt/templates_optimization/jobs/%s";

    private static final String PROMPT_GENERATE_API = "/flask/v1/prompt/build";

    private static final String PROMPT_FEEDBACK_API = "/flask/v1/prompt/optimize_feedback";

    @Value("${agent_builder_endpoint:}")
    private String agentBuilderEndpoint;

    @Resource(name = "remoteClientTemplate")
    private ClientTemplate clientTemplate;

    @Autowired
    private WebClient webClient;

    @Autowired
    private PromptTaskMapper promptTaskMapper;

    @Autowired
    private PromptEngineerDataSetService promptEngineerDataSetService;

    @Autowired
    private ModelServiceMapper modelServiceMapper;

    @Autowired
    private ProviderAuthMetadataMapper providerAuthMetadataMapper;

    @Autowired
    private ProviderAuthDataMapper providerAuthDataMapper;

    @Override
    public void execute(JobExecutionContext jobExecutionContext) throws JobExecutionException {
        try {
            String taskParam = jobExecutionContext.getJobDetail().getJobDataMap().getString("taskParam");
            String token = jobExecutionContext.getJobDetail().getJobDataMap().getString("token");
            PromptTaskDetailVo promptTaskDetailVo = JsonUtils.json2ObjQuietly(taskParam, PromptTaskDetailVo.class);
            execTask(promptTaskDetailVo, token);
        } catch (Exception e) {
            log.error("schedule create prompt task error open, {}", e.getMessage());
            throw new JobExecutionException(e);
        }

    }

    public JiuWenJobInfo execTask(PromptTaskDetailVo promptTaskDetailVo, String token) {
        log.info("request jiuwen for create task");
        JiuWenCreTaskReq req = buildJiuWenCreTaskReq(promptTaskDetailVo);
        boolean statusUpdated = false;
        try {
            String jiuwenPath = promptTaskDetailVo.getPtType() == PtTypeEnum.TEXT
                ? TEMPLATES_OPTIMIZATION_CREATE_API
                : TEMPLATES_OPTIMIZATION_CREATE_MULTI_API;
            HttpHeaders headers = new HttpHeaders();
            if (Objects.nonNull(token)) {
                headers.set(CommonConstant.X_AUTH_TOKEN, token);
            }
            headers.set(CommonConstant.X_WORKSPACE_ID, promptTaskDetailVo.getWorkspaceId());
            ResponseEntity<JiuWenCreTaskRes> response = clientTemplate.postForEntity(agentBuilderEndpoint + jiuwenPath,
                headers, JsonUtil.object2Json(req), JiuWenCreTaskRes.class);
            if (!response.getStatusCode().is2xxSuccessful()) {
                String errorMsg = "Runtime returned " + response.getStatusCode();
                if (response.getBody() != null) {
                    errorMsg = response.getBody().getMessage();
                    log.error("Create optimization task from jiuwen server error! response:{}",
                        errorMsg);
                }
                promptTaskMapper.updateStatusByPrimaryKey(promptTaskDetailVo.getId(),
                    PromptTaskStatusEnum.FAILED.getCode(),
                    promptTaskDetailVo.getProjectId(), promptTaskDetailVo.getWorkspaceId());
                promptTaskMapper.updateMessageByPrimaryKey(promptTaskDetailVo.getId(),
                    errorMsg, promptTaskDetailVo.getProjectId(), promptTaskDetailVo.getWorkspaceId());
                statusUpdated = true;
                throw new AgentStudioException(StudioError.OPTIMIZATION_TASK_FROM_JIUWEN_SERVICE_ERROR);
            }
            JiuWenCreTaskRes jiuWenCreTaskRes = response.getBody();
            if (Objects.isNull(jiuWenCreTaskRes)) {
                log.error("Create optimization task resp is null");
                throw new AgentStudioException(StudioError.CREATE_OPTIMIZATION_TASK_RESP_NULL);
            }
            if (jiuWenCreTaskRes.getCode() != ResponseCode.OK.getCode()) {
                log.error("Create optimization task from jiuwen server error! response:{}",
                    jiuWenCreTaskRes.getMessage());
                promptTaskMapper.updateJobIdStatusByPrimaryKey(promptTaskDetailVo.getId(),
                    jiuWenCreTaskRes.getJobInfo().getId(), PromptTaskStatusEnum.FAILED.getCode(),
                    promptTaskDetailVo.getProjectId(), promptTaskDetailVo.getWorkspaceId());
                promptTaskMapper.updateMessageByPrimaryKey(promptTaskDetailVo.getId(),
                    jiuWenCreTaskRes.getMessage(), promptTaskDetailVo.getProjectId(),
                    promptTaskDetailVo.getWorkspaceId());
                statusUpdated = true;
                throw new AgentStudioException(StudioError.OPTIMIZE_TEMPLATE_FAILED,
                    Collections.singletonList(jiuWenCreTaskRes.getMessage()));
            }
            log.info("jiuwen create task successfully");
            promptTaskMapper.updateJobIdStatusByPrimaryKey(promptTaskDetailVo.getId(),
                jiuWenCreTaskRes.getJobInfo().getId(), PromptTaskStatusEnum.RUNNING.getCode(),
                promptTaskDetailVo.getProjectId(), promptTaskDetailVo.getWorkspaceId());
            return jiuWenCreTaskRes.getJobInfo();
        } catch (Exception e) {
            log.error("Create optimization task from jiuwen server error! ", e);
            if (!statusUpdated) {
                promptTaskMapper.updateStatusByPrimaryKey(promptTaskDetailVo.getId(), PromptTaskStatusEnum.FAILED.getCode(),
                    promptTaskDetailVo.getProjectId(), promptTaskDetailVo.getWorkspaceId());
                if (e.getMessage() != null && !e.getMessage().isEmpty()) {
                    promptTaskMapper.updateMessageByPrimaryKey(promptTaskDetailVo.getId(), e.getMessage(),
                        promptTaskDetailVo.getProjectId(), promptTaskDetailVo.getWorkspaceId());
                }
            }
            throw new AgentStudioException(StudioError.OPTIMIZATION_TASK_FROM_JIUWEN_SERVICE_ERROR);
        }
    }

    public void deleteTask(PromptTaskDetailVo promptTaskDetailVo, String token) {
        try {
            String jiuwenTaskId = promptTaskDetailVo.getJiuwenTaskId();
            log.info("delete jiuwen optimization taskId: {}", jiuwenTaskId);
            String jiuwenPath = promptTaskDetailVo.getPtType() == PtTypeEnum.TEXT
                ? TEMPLATES_OPTIMIZATION_DELETE_API
                : TEMPLATES_OPTIMIZATION_DELETE_MULTI_API;
            ResponseEntity<JIuWenPromptBaseRes> response = clientTemplate.deleteForEntity(
                agentBuilderEndpoint + String.format(jiuwenPath, jiuwenTaskId), token, JIuWenPromptBaseRes.class);
            if (!response.getStatusCode().is2xxSuccessful()) {
                if (response.getBody() != null) {
                    log.error("Delete optimization task from jiuwen server error! response:{}",
                        response.getBody().getMessage());
                }
                throw new AgentStudioException(StudioError.DELETE_OPTIMIZATION_TASK, response);
            }
            JIuWenPromptBaseRes jIuWenPromptBaseRes = response.getBody();
            if (Objects.isNull(jIuWenPromptBaseRes)) {
                log.error("Create optimization task resp is null");
                throw new AgentStudioException(StudioError.CREATE_OPTIMIZATION_TASK_RESP_NULL);
            }
            if (jIuWenPromptBaseRes.getCode() != ResponseCode.OK.getCode()) {
                log.warn("optimize template delete failed, response code: {}", jIuWenPromptBaseRes.getCode());
                throw new AgentStudioException(StudioError.OPTIMIZE_TEMPLATE_DELETE_FAILED);
            }
        } catch (ResourceAccessException e) {
            log.error("optimization template service access failed, error: {}", e.getMessage());
            throw new AgentStudioException(StudioError.OPTIMIZATION_TEMPLATE_SERVICE_ACCESS_FAILED);
        }
    }

    public JiuWenPromptDeatilRes getTaskDetail(PromptTaskDetailVo promptTaskDetailVo, String token) {
        // 后续调用九问接口查询任务详情
        try {
            String jiuwenTaskId = promptTaskDetailVo.getJiuwenTaskId();
            log.info("getOptimizationProgress jiuwenTaskId: {}", jiuwenTaskId);
            String jiuwenPath = promptTaskDetailVo.getPtType() == PtTypeEnum.TEXT
                ? TEMPLATES_OPTIMIZATION_PROGRESS_API
                : TEMPLATES_OPTIMIZATION_PROGRESS_MULTI_API;
            ResponseEntity<JiuWenPromptDeatilRes> response = clientTemplate.getForEntity(
                agentBuilderEndpoint + String.format(jiuwenPath, jiuwenTaskId), token, JiuWenPromptDeatilRes.class);
            if (!response.getStatusCode().is2xxSuccessful()) {
                if (response.getBody() != null) {
                    log.error("Get optimization task progress from jiuwen server error! response:{}",
                        response.getBody().getMessage());
                }
                throw new AgentStudioException(StudioError.GET_OPTIMIZATION_TASK);
            }
            if (Objects.isNull(response.getBody())) {
                log.info("get optimization task progress is null");
                throw new AgentStudioException(StudioError.GET_OPTIMIZATION_TASK);
            }
            return response.getBody();
        } catch (ResourceAccessException e) {
            log.error("optimization template service access failed, error: {}", e.getMessage());
            throw new AgentStudioException(StudioError.OPTIMIZATION_TEMPLATE_SERVICE_ACCESS_FAILED);
        }
    }

    /**
     * 批量查询多模态任务
     *
     * @param jiuwenTaskIds
     * @param token
     * @return
     */
    public JiuWenJobDeatails queryMultiTaskDetailsByIds(List<String> jiuwenTaskIds, String token) {
        // 后续调用九问批量任务查询接口
        try {
            log.info("getOptimizationProgress jiuwenTaskIds: {}", jiuwenTaskIds);
            ResponseEntity<JiuWenPromptBatchRes> response = clientTemplate.postForEntity(
                agentBuilderEndpoint + TEMPLATES_OPTIMIZATION_BATCH_PROGRESS_MULTI_API, token,
                JsonUtil.object2Json(JiuWenPromptBatchReq.builder().idList(jiuwenTaskIds).build()),
                JiuWenPromptBatchRes.class);
            if (!response.getStatusCode().is2xxSuccessful()) {
                if (response.getBody() != null) {
                    log.error("Get optimization task progresses from jiuwen server error! response:{}",
                        response.getBody().getMessage());
                }
                throw new AgentStudioException(StudioError.GET_OPTIMIZATION_TASK);
            }
            if (Objects.isNull(response.getBody())) {
                log.info("get optimization task progresses is null");
                throw new AgentStudioException(StudioError.GET_OPTIMIZATION_TASK);
            }
            return response.getBody().getJobDetails();
        } catch (ResourceAccessException e) {
            log.error("optimization template service access failed, error: {}", e.getMessage(), e);
            throw new AgentStudioException(StudioError.OPTIMIZATION_TEMPLATE_SERVICE_ACCESS_FAILED);
        }
    }

    /**
     * 批量查询纯文本任务
     *
     * @param jiuwenTaskIds
     * @param token
     * @return
     */
    public JiuWenJobDeatails queryTaskDetailsByIds(List<String> jiuwenTaskIds, String token) {
        // 后续调用九问批量任务查询接口
        try {
            log.info("getOptimizationProgress jiuwenTaskIds: {}", jiuwenTaskIds);
            ResponseEntity<JiuWenPromptBatchRes> response = clientTemplate.postForEntity(
                agentBuilderEndpoint + TEMPLATES_OPTIMIZATION_BATCH_PROGRESS_API, token,
                JsonUtil.object2Json(JiuWenPromptBatchReq.builder().idList(jiuwenTaskIds).build()),
                JiuWenPromptBatchRes.class);
            if (!response.getStatusCode().is2xxSuccessful()) {
                if (response.getBody() != null) {
                    log.error("Get optimization task progresses from jiuwen server error! response:{}",
                        response.getBody().getMessage());
                }
                throw new AgentStudioException(StudioError.GET_OPTIMIZATION_TASK);
            }
            if (Objects.isNull(response.getBody())) {
                log.info("get optimization task progresses is null");
                throw new AgentStudioException(StudioError.GET_OPTIMIZATION_TASK);
            }
            return response.getBody().getJobDetails();
        } catch (ResourceAccessException e) {
            log.error("optimization template service access failed, error: {}", e.getMessage(), e);
            throw new AgentStudioException(StudioError.OPTIMIZATION_TEMPLATE_SERVICE_ACCESS_FAILED);
        }
    }

    public void pauseTask(PromptTaskDetailVo promptTaskDetailVo, String token) {
        // 后续调用九问任务暂停接口
        try {
            String jiuwenTaskId = promptTaskDetailVo.getJiuwenTaskId();
            log.info("Pause OptimizationProgress jiuwenTaskId: {}", jiuwenTaskId);
            String jiuwenPath = promptTaskDetailVo.getPtType() == PtTypeEnum.TEXT
                ? TEMPLATES_OPTIMIZATION_STOP_API
                : TEMPLATES_OPTIMIZATION_STOP_MULTI_API;
            ResponseEntity<JIuWenPromptBaseRes> response = clientTemplate.postForEntity(
                agentBuilderEndpoint + String.format(jiuwenPath, jiuwenTaskId), token, null, JIuWenPromptBaseRes.class);
            if (!response.getStatusCode().is2xxSuccessful()) {
                if (response.getBody() != null) {
                    log.error("Get optimization task progresses from jiuwen server error! response:{}",
                        response.getBody().getMessage());
                }
                throw new AgentStudioException(StudioError.GET_OPTIMIZATION_TASK);
            }
        } catch (ResourceAccessException e) {
            log.error("optimization template service access failed, error: {}", e.getMessage(), e);
            throw new AgentStudioException(StudioError.OPTIMIZATION_TEMPLATE_SERVICE_ACCESS_FAILED);
        }
    }

    public void resumeTask(PromptTaskDetailVo promptTaskDetailVo, String token) {
        // 后续调用九问任务重启任务接口
        try {
            String jiuwenTaskId = promptTaskDetailVo.getJiuwenTaskId();
            log.info("resume OptimizationProgress jiuwenTaskId: {}", jiuwenTaskId);
            String jiuwenPath = promptTaskDetailVo.getPtType() == PtTypeEnum.TEXT
                ? TEMPLATES_OPTIMIZATION_RESTART_API
                : TEMPLATES_OPTIMIZATION_RESTART_MULTI_API;
            HttpHeaders headers = new HttpHeaders();
            if (Objects.nonNull(token)) {
                headers.set(CommonConstant.X_AUTH_TOKEN, token);
            }
            headers.set(CommonConstant.X_WORKSPACE_ID, promptTaskDetailVo.getWorkspaceId());
            ResponseEntity<JIuWenPromptBaseRes> response = clientTemplate.postForEntity(
                agentBuilderEndpoint + String.format(jiuwenPath, jiuwenTaskId), headers, null, JIuWenPromptBaseRes.class);
            if (!response.getStatusCode().is2xxSuccessful()) {
                if (response.getBody() != null) {
                    log.error("resume optimization task progresses from jiuwen server error! response:{}",
                        response.getBody().getMessage());
                }
                throw new AgentStudioException(StudioError.GET_OPTIMIZATION_TASK);
            }
        } catch (ResourceAccessException e) {
            log.error("optimization template service access failed, error: {}", e.getMessage(), e);
            throw new AgentStudioException(StudioError.OPTIMIZATION_TEMPLATE_SERVICE_ACCESS_FAILED);
        }
    }

    public Flux<String> generatePrompt(String projectId, String workspaceId, PromptBuildRequest body, String token) {
        log.info("start to generate prompt, projectId: {}, workspaceId: {}", projectId, workspaceId);

        // 补充 modelInfo 的 url、api_key 等字段
        if (body.getModelInfo() != null) {
            enrichExecConfig(body.getModelInfo(), projectId, workspaceId);
        }

        Flux<String> dataFlux = webClient.post()
            .uri(agentBuilderEndpoint + PROMPT_GENERATE_API)
            .contentType(MediaType.APPLICATION_JSON)
            .header(CommonConstant.X_AUTH_TOKEN, token)
            .header(CommonConstant.X_WORKSPACE_ID, workspaceId)
            .bodyValue(body)
            .retrieve()
            // 处理HTTP非2xx状态码：直接抛异常
            .onStatus(status -> !status.is2xxSuccessful(),
                response -> response.bodyToMono(String.class).flatMap(errorBody -> {
                    String errorMsg = String.format("Prompt generate failed:  status=%s, error=%s",
                        response.statusCode(), errorBody);
                    log.error(errorMsg);
                    // 抛出异常，终止流（不返回任何数据）
                    return Mono.error(
                        new AgentStudioException(StudioError.OPTIMIZATION_TEMPLATE_SERVICE_ACCESS_FAILED));
                }))
            .bodyToFlux(String.class)
            .mapNotNull(chunk -> {
                PromptBuildResponse response = JsonUtils.json2ObjQuietly(chunk, PromptBuildResponse.class);
                return response != null ? chunk : ""; // 过滤无效 JSON
            })
            .filter(chunk -> chunk != null && !chunk.trim().isEmpty())
            .onErrorResume(Exception.class, e -> {
                // 直接抛出异常，流终止，不会执行后续的[Done]拼接
                return Flux.error(new AgentStudioException(StudioError.OPTIMIZATION_TEMPLATE_SERVICE_ACCESS_FAILED));
            });

        Flux<String> doneFlux = Flux.just("[Done]");

        log.info("prompt generation completed, projectId: {}, workspaceId: {}", projectId, workspaceId);
        return Flux.concat(dataFlux, doneFlux);
    }

    public Flux<String> optimizeFeedback(String projectId, String workspaceId, PromptFeedbackRequest body,
        String token) {
        // 判断是一键生成还是反馈优化
        if (StringUtils.isEmpty(body.getPrompt())) {
            // 一键生成

            if (ObjectUtils.isEmpty(body.getModelInfo())) {
                log.error("generate prompt doesn't have extension info");
                throw new AgentStudioException(StudioError.PROMPT_FEEDBACK_PARAM_ERROR);
            }
            String instruct = "";
            for (Map.Entry<String, String> entry : body.getExtension_info().entrySet()) {
                instruct += entry.getKey() + ":" + entry.getValue() + "\n;";
            }

            PromptBuildRequest buildRequest = PromptBuildRequest.builder()
                .instruct(instruct)
                .tools(new ArrayList<>())
                .modelInfo(body.getModelInfo())
                .stream(true)
                .build();

            return generatePrompt(projectId, workspaceId, buildRequest, token);

        } else {
            // 反馈优化，补充反馈信息

            String feeback = "";
            for (Map.Entry<String, String> entry : body.getExtension_info().entrySet()) {
                feeback += entry.getKey() + ":" + entry.getValue() + "\n;";
            }
            if (StringUtils.isEmpty(body.getFeedback())) {
                body.setFeedback(feeback + "对提示词进一步丰富一些");
            } else {
                body.setFeedback(body.getFeedback() + "\n" + feeback);
            }

            Flux<String> dataFlux = webClient.post()
                .uri(agentBuilderEndpoint + PROMPT_FEEDBACK_API)
                .contentType(MediaType.APPLICATION_JSON)
                .header(CommonConstant.X_AUTH_TOKEN, token)
                .bodyValue(body)
                .retrieve()
                // 处理HTTP非2xx状态码：直接抛异常
                .onStatus(status -> !status.is2xxSuccessful(),
                    response -> response.bodyToMono(String.class).flatMap(errorBody -> {
                        String errorMsg = String.format("Prompt generate failed:  status=%s, error=%s",
                            response.statusCode(), errorBody);
                        log.error(errorMsg);
                        // 抛出异常，终止流（不返回任何数据）
                        return Mono.error(
                            new AgentStudioException(StudioError.OPTIMIZATION_TEMPLATE_SERVICE_ACCESS_FAILED));
                    }))
                .bodyToFlux(String.class)
                .mapNotNull(chunk -> {
                    PromptBuildResponse response = JsonUtils.json2ObjQuietly(chunk, PromptBuildResponse.class);
                    return response != null ? chunk : ""; // 过滤无效 JSON
                })
                .filter(chunk -> chunk != null && !chunk.trim().isEmpty())
                .onErrorResume(Exception.class, e -> {
                    // 直接抛出异常，流终止，不会执行后续的[Done]拼接
                    return Flux.error(
                        new AgentStudioException(StudioError.OPTIMIZATION_TEMPLATE_SERVICE_ACCESS_FAILED));
                });
            Flux<String> doneFlux = Flux.just("[Done]");

            return Flux.concat(dataFlux, doneFlux);
        }
    }

    private JiuWenCreTaskReq buildJiuWenCreTaskReq(PromptTaskDetailVo promptTaskDetailVo) {
        log.info("start to build JiuWenCreTaskReq, task name: {}", promptTaskDetailVo.getName());

        List<PromptVar> varsConfig = promptTaskDetailVo.getPtVars();
        Map<String, PromptVar> varConfigMap = varsConfig.stream()
            .collect(Collectors.toMap(PromptVar::getName, var -> var));

        List<List<PromptVar>> evalDataList = promptEngineerDataSetService.getAllEvalDataSet(promptTaskDetailVo.getId(),
            promptTaskDetailVo.getProjectId(), promptTaskDetailVo.getWorkspaceId());

        List<ModelCase> cases = new ArrayList<>();
        evalDataList.forEach(promptVars -> {
            Map<String, String> varMap = new HashMap<>();
            Map<String, String> varTypeMap = new HashMap<>();

            for (PromptVar var : promptVars) {
                if (varConfigMap.containsKey(var.getName())) {
                    varMap.put(var.getName(), var.getContent());
                    varTypeMap.put(var.getName(),
                        varConfigMap.get(var.getName()).getType() == PtTypeEnum.MULTI ? "image" : "text");
                }
            }

            String outPut = varMap.get(CommonConstant.AGENT_BUILDER_PROMPT_OUTPUT);
            varMap.remove(CommonConstant.AGENT_BUILDER_PROMPT_OUTPUT);
            varTypeMap.remove(CommonConstant.AGENT_BUILDER_PROMPT_OUTPUT);

            Case userMessage = Case.builder()
                .role("user")
                .content("<RAW_PROMPT>")
                .variable(varMap)
                .variableType(varTypeMap)
                .build();
            Case assistantMessage = Case.builder()
                .role("assistant")
                .content(outPut)
                .variable(new HashMap<>())
                .variableType(new HashMap<>())
                .build();
            ModelCase modelCase = ModelCase.builder().messages(List.of(userMessage, assistantMessage)).build();
            cases.add(modelCase);
        });

        JiuWenOptimizeInfo jiuWenOptimizeInfo = JiuWenOptimizeInfo.builder()
            .cases(cases)
            .numIter(promptTaskDetailVo.getMaxIterNum())
            .earlyStopScore(promptTaskDetailVo.getTargetAcc())
            .exampleNum(promptTaskDetailVo.getShowCaseNum())
            .placeholder(new ArrayList<>())
            .llmParallel(2)
            .cotExampleNum(0)
            .optimizeMethod("JOINT")
            .evaluationMethod("LLM")
            .userCompareOptions(promptTaskDetailVo.getTargetType().toString())
            .userCompareRules(promptTaskDetailVo.getScoreStandard())
            .externalKnowledge(promptTaskDetailVo.getBackKnowledge())
            .optimizeAlgorithm("beamsearch")
            .build();

        JiuWenCreTaskReq jiuWenCreTaskReq = JiuWenCreTaskReq.builder()
            .name(promptTaskDetailVo.getName())
            .desc(promptTaskDetailVo.getDesc())
            .rawTemplates(promptTaskDetailVo.getPtText())
            .modelInfo(enrichExecConfig(promptTaskDetailVo.getPtModel(),
                promptTaskDetailVo.getProjectId(), promptTaskDetailVo.getWorkspaceId()))
            .assistantInfo(enrichExecConfig(promptTaskDetailVo.getExecObject(),
                promptTaskDetailVo.getProjectId(), promptTaskDetailVo.getWorkspaceId()))
            .optimizeInfo(jiuWenOptimizeInfo)
            .build();

        log.info("JiuWenCreTaskReq built successfully, task name: {}", promptTaskDetailVo.getName());
        return jiuWenCreTaskReq;
    }

    /**
     * Enrich ExecConfig with model URL and API key from the model service database.
     */
    private com.openjiuwen.studio.prompt.engineering.entity.v2.ExecConfig enrichExecConfig(
            com.openjiuwen.studio.prompt.engineering.entity.v2.ExecConfig config,
            String projectId, String workspaceId) {
        if (config == null || StringUtils.isEmpty(config.getModel())) {
            return config;
        }
        try {
            ModelServiceBase modelService = modelServiceMapper.queryById(config.getModel());
            if (modelService != null) {
                config.setUrl(modelService.getApiUrl());
                log.info("Enriched model config: id={}, modelName={}, url={}",
                    config.getModel(), modelService.getModelName(), config.getUrl());
                if (StringUtils.isNotEmpty(modelService.getProviderId())) {
                    List<ProviderAuthMetadata> authList = providerAuthDataMapper
                        .selectProviderAuthData(projectId, workspaceId, modelService.getProviderId());
                    log.info("Provider auth data list size: {}, providerId: {}",
                        authList == null ? 0 : authList.size(), modelService.getProviderId());
                    if (authList != null) {
                        for (ProviderAuthMetadata auth : authList) {
                            log.info("Provider auth data type: {}, hasAuthConfig: {}",
                                auth.getAuthType(), auth.getAuthConfig() != null);
                        }
                        authList.stream()
                            .filter(auth -> auth.getAuthConfig() != null)
                            .findFirst()
                            .ifPresent(auth -> {
                                try {
                                    Map<String, String> authMap = JsonUtils.json2Obj(
                                        auth.getAuthConfig(), new com.fasterxml.jackson.core.type.TypeReference<>() {});
                                    if (authMap != null && !authMap.isEmpty()) {
                                        String encryptedKey = authMap.values().iterator().next();
                                        String decryptedKey = CryptoUtils.decrypt(encryptedKey);
                                        config.setApiKey(decryptedKey);
                                        log.info("API key set successfully from authData");
                                    }
                                } catch (Exception e) {
                                    log.warn("Failed to decrypt provider API key: {}", e.getMessage());
                                }
                            });
                    }
                }
                // 设置 top_p 和 temperature 默认值（前端可能不传）
                if (config.getTopP() == null) {
                    config.setTopP(0.1);
                }
                if (config.getTemperature() == null) {
                    config.setTemperature(0.1);
                }
                log.info("Enriched model config: model={}, url={}", config.getModel(), config.getUrl());
            } else {
                log.warn("Model service not found for id: {}", config.getModel());
            }
        } catch (Exception e) {
            log.warn("Failed to enrich model config for model {}: {}", config.getModel(), e.getMessage());
        }
        return config;
    }

}
