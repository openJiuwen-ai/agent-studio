/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.OkHttpClientUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.dto.scheduler.ScheduledExecutionListRsp;
import com.openjiuwen.studio.agent.manager.dto.scheduler.ScheduledExecutionRsp;
import com.openjiuwen.studio.agent.manager.dto.scheduler.ScheduledTaskListRsp;
import com.openjiuwen.studio.agent.manager.dto.scheduler.ScheduledTaskReq;
import com.openjiuwen.studio.agent.manager.dto.scheduler.ScheduledTaskRsp;
import com.openjiuwen.studio.agent.manager.entity.ScheduledTaskEntity;
import com.openjiuwen.studio.agent.manager.entity.ScheduledTaskExecutionEntity;
import com.openjiuwen.studio.agent.manager.mapper.ScheduledTaskExecutionMapper;
import com.openjiuwen.studio.agent.manager.mapper.ScheduledTaskMapper;

import lombok.extern.slf4j.Slf4j;

import okhttp3.MediaType;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import okhttp3.ResponseBody;

import org.apache.commons.lang3.StringUtils;
import org.quartz.CronExpression;
import org.quartz.CronScheduleBuilder;
import org.quartz.JobBuilder;
import org.quartz.JobDetail;
import org.quartz.JobKey;
import org.quartz.Scheduler;
import org.quartz.SchedulerException;
import org.quartz.SimpleScheduleBuilder;
import org.quartz.Trigger;
import org.quartz.TriggerBuilder;
import org.quartz.TriggerKey;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.text.ParseException;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 自动化（定时任务）服务：任务的增删改查、Quartz 调度、执行与执行日志。
 */
@Slf4j
@Service
public class SchedulerTaskService implements ISchedulerTaskService {
    /**
     * Quartz 任务组名。
     */
    public static final String JOB_GROUP = "scheduler";

    /**
     * Quartz 任务名前缀。
     */
    public static final String JOB_NAME_PREFIX = "scheduled-task:";

    /**
     * JobDataMap 中任务 id 的 key。
     */
    public static final String JOB_DATA_TASK_ID = "task_id";

    private static final String LLM_CHAT_API = "/v1/agent-builder/chat/completions";

    private static final int MAX_OUTPUT_LENGTH = 4000;

    private static final List<String> EXECUTOR_TYPES = List.of("llm_prompt", "agent_run", "workflow_run",
        "http_call");

    @Autowired
    private ScheduledTaskMapper taskMapper;

    @Autowired
    private ScheduledTaskExecutionMapper executionMapper;

    @Autowired
    private Scheduler scheduler;

    @Autowired
    private OkHttpClientUtils okHttpClientUtils;

    @Autowired
    private MgAsyncService mgAsyncService;

    @Value("${inner.agent-runtime.endpoint}")
    private String agentRuntimeEndpoint;

    @Value("${inner.agent-runtime.run-agent.stream-url}")
    private String runAgentStreamUrl;

    @Value("${inner.agent-runtime.run-workflow.uri}")
    private String runWorkflowStreamUrl;

    // ==================== CRUD ====================

    /**
     * 创建自动化任务。
     */
    @Override
    public ScheduledTaskRsp createTask(String projectId, String workspaceId, ScheduledTaskReq req) {
        validateReq(req);
        ScheduledTaskEntity entity = new ScheduledTaskEntity();
        entity.setId(UUID.randomUUID().toString());
        entity.setProjectId(projectId);
        entity.setWorkspaceId(workspaceId);
        entity.setCreatorId(RequestContextUtils.getRequestUserId());
        entity.setCreatorName(RequestContextUtils.getRequestUser().getUserName());
        fillEntityFromReq(entity, req);
        entity.setStatus("enabled");
        long now = System.currentTimeMillis();
        entity.setCreatedAt(now);
        entity.setUpdatedAt(now);
        entity.setRunCount(0L);

        // 先调度，拿到下次执行时间后再落库
        Long nextRunAt = scheduleJob(entity);
        entity.setNextRunAt(nextRunAt);
        taskMapper.insert(entity);
        return toRsp(entity);
    }

    /**
     * 更新自动化任务。
     */
    @Override
    public ScheduledTaskRsp updateTask(String projectId, String workspaceId, String taskId, ScheduledTaskReq req) {
        validateReq(req);
        ScheduledTaskEntity entity = requireTask(projectId, workspaceId, taskId);
        String status = entity.getStatus();
        fillEntityFromReq(entity, req);
        entity.setStatus(status);
        entity.setUpdatedAt(System.currentTimeMillis());

        Long nextRunAt = null;
        if ("enabled".equals(status)) {
            nextRunAt = scheduleJob(entity);
        } else {
            unscheduleJob(taskId);
        }
        entity.setNextRunAt(nextRunAt);
        taskMapper.updateById(entity);
        return toRsp(entity);
    }

    /**
     * 删除自动化任务。
     */
    @Override
    public void deleteTask(String projectId, String workspaceId, String taskId) {
        requireTask(projectId, workspaceId, taskId);
        unscheduleJob(taskId);
        taskMapper.deleteById(taskId);
        executionMapper.deleteByTaskId(taskId);
    }

    /**
     * 查询单个任务。
     */
    @Override
    public ScheduledTaskRsp getTask(String projectId, String workspaceId, String taskId) {
        return toRsp(requireTask(projectId, workspaceId, taskId));
    }

    /**
     * 分页查询任务列表。
     */
    @Override
    public ScheduledTaskListRsp listTasks(String projectId, String workspaceId, String status, String search, int page,
        int pageSize) {
        int offset = Math.max(0, (page - 1) * pageSize);
        List<ScheduledTaskEntity> entities = taskMapper.selectPage(projectId, workspaceId, status, search, offset,
            pageSize);
        long total = taskMapper.selectCount(projectId, workspaceId, status, search);
        ScheduledTaskListRsp rsp = new ScheduledTaskListRsp();
        rsp.setItems(entities.stream().map(this::toRsp).toList());
        rsp.setTotal(total);
        rsp.setPage(page);
        rsp.setPageSize(pageSize);
        return rsp;
    }

    // ==================== 启停 / 手动触发 ====================

    /**
     * 启用任务。
     */
    @Override
    public ScheduledTaskRsp enableTask(String projectId, String workspaceId, String taskId) {
        ScheduledTaskEntity entity = requireTask(projectId, workspaceId, taskId);
        Long nextRunAt = scheduleJob(entity);
        entity.setNextRunAt(nextRunAt);
        entity.setStatus("enabled");
        taskMapper.updateStatus(taskId, "enabled", nextRunAt, System.currentTimeMillis());
        return toRsp(entity);
    }

    /**
     * 禁用任务。
     */
    @Override
    public ScheduledTaskRsp disableTask(String projectId, String workspaceId, String taskId) {
        ScheduledTaskEntity entity = requireTask(projectId, workspaceId, taskId);
        unscheduleJob(taskId);
        entity.setNextRunAt(null);
        entity.setStatus("disabled");
        taskMapper.updateStatus(taskId, "disabled", null, System.currentTimeMillis());
        return toRsp(entity);
    }

    /**
     * 手动触发一次执行（异步）。
     */
    @Override
    public void triggerTask(String projectId, String workspaceId, String taskId) {
        ScheduledTaskEntity entity = requireTask(projectId, workspaceId, taskId);
        mgAsyncService.callRunAgentStream(() -> executeTask(entity.getId(), "manual"));
    }

    // ==================== 执行日志 ====================

    /**
     * 分页查询执行日志。
     */
    @Override
    public ScheduledExecutionListRsp listExecutions(String projectId, String workspaceId, String taskId,
        String status, int page, int pageSize) {
        ScheduledTaskEntity task = requireTask(projectId, workspaceId, taskId);
        int offset = Math.max(0, (page - 1) * pageSize);
        List<ScheduledTaskExecutionEntity> entities = executionMapper.selectPageByTaskId(taskId, status, offset,
            pageSize);
        long total = executionMapper.selectCountByTaskId(taskId, status);
        ScheduledExecutionListRsp rsp = new ScheduledExecutionListRsp();
        rsp.setItems(entities.stream().map(e -> toExecutionRsp(e, task.getName())).toList());
        rsp.setTotal(total);
        rsp.setPage(page);
        rsp.setPageSize(pageSize);
        return rsp;
    }

    // ==================== 辅助接口 ====================

    /**
     * 预览调度接下来 5 次的执行时间。
     */
    @Override
    public Map<String, Object> preview(ScheduledTaskReq.ScheduleInfo schedule) {
        String quartzCron = resolveQuartzCron(schedule == null ? null : schedule.getType(),
            schedule == null ? null : schedule.getConfig());
        List<Long> nextRunTimes = new ArrayList<>();
        try {
            CronExpression cronExpression = new CronExpression(quartzCron);
            Date cursor = new Date();
            for (int i = 0; i < 5; i++) {
                cursor = cronExpression.getNextValidTimeAfter(cursor);
                if (cursor == null) {
                    break;
                }
                nextRunTimes.add(cursor.getTime());
            }
        } catch (ParseException e) {
            throw new AgentStudioException(StudioError.SCHEDULE_EXPRESSION_INVALID);
        }
        Map<String, Object> result = new HashMap<>();
        result.put("cron", quartzCron);
        result.put("next_run_times", nextRunTimes);
        return result;
    }

    /**
     * 支持的执行方式列表。
     */
    @Override
    public List<Map<String, Object>> executorTypes() {
        List<Map<String, Object>> types = new ArrayList<>();
        types.add(Map.of("type", "llm_prompt", "label", "大模型调用"));
        types.add(Map.of("type", "agent_run", "label", "运行智能体"));
        types.add(Map.of("type", "workflow_run", "label", "运行工作流"));
        types.add(Map.of("type", "http_call", "label", "HTTP 请求"));
        return types;
    }

    // ==================== Quartz 调度 ====================

    /**
     * 为任务创建/重建 Quartz 调度，返回下次执行时间。
     */
    private Long scheduleJob(ScheduledTaskEntity task) {
        JobKey jobKey = jobKey(task.getId());
        TriggerKey triggerKey = new TriggerKey(jobKey.getName(), JOB_GROUP);
        try {
            scheduler.deleteJob(jobKey);
            JobDetail jobDetail = JobBuilder.newJob(SchedulerTaskJob.class)
                .withIdentity(jobKey)
                .usingJobData(JOB_DATA_TASK_ID, task.getId())
                .build();
            Trigger trigger = buildTrigger(task, triggerKey);
            scheduler.scheduleJob(jobDetail, trigger);
            if (!scheduler.isShutdown()) {
                scheduler.start();
            }
            Date nextFireTime = trigger.getNextFireTime();
            return nextFireTime == null ? null : nextFireTime.getTime();
        } catch (SchedulerException e) {
            log.error("Schedule job failed. taskId={}", task.getId(), e);
            throw new AgentStudioException(StudioError.SCHEDULER_EXCEPTION);
        }
    }

    /**
     * 移除任务的 Quartz 调度。
     */
    private void unscheduleJob(String taskId) {
        try {
            scheduler.deleteJob(jobKey(taskId));
        } catch (SchedulerException e) {
            log.error("Unschedule job failed. taskId={}", taskId, e);
            throw new AgentStudioException(StudioError.SCHEDULER_EXCEPTION);
        }
    }

    private Trigger buildTrigger(ScheduledTaskEntity task, TriggerKey triggerKey) {
        long now = System.currentTimeMillis();
        long startAtMs = Math.max(now, task.getValidFrom() == null ? now : task.getValidFrom());
        Date endAt = task.getValidUntil() == null ? null : new Date(task.getValidUntil());
        @SuppressWarnings({"rawtypes", "unchecked"})
        TriggerBuilder builder = TriggerBuilder.newTrigger().withIdentity(triggerKey).startAt(new Date(startAtMs));
        if (endAt != null) {
            builder.endAt(endAt);
        }
        if ("once".equals(task.getRepeatType())) {
            Long runAt = getOnceRunAt(task);
            Date fireTime = runAt == null || runAt <= now ? new Date(now + 2000L)
                : new Date(Math.max(runAt, startAtMs));
            return builder.startAt(fireTime)
                .withSchedule(SimpleScheduleBuilder.simpleSchedule()
                    .withMisfireHandlingInstructionFireNow())
                .build();
        }
        String quartzCron = resolveQuartzCron(task.getScheduleType(), parseJsonMap(task.getScheduleConfig()));
        return builder.withSchedule(CronScheduleBuilder.cronSchedule(quartzCron)
                .withMisfireHandlingInstructionFireAndProceed())
            .build();
    }

    private static JobKey jobKey(String taskId) {
        return JobKey.jobKey(JOB_NAME_PREFIX + taskId, JOB_GROUP);
    }

    /**
     * 解析一次性任务的执行时间点（schedule_config.run_at）。
     */
    private Long getOnceRunAt(ScheduledTaskEntity task) {
        Map<String, Object> config = parseJsonMap(task.getScheduleConfig());
        return config == null ? null : toMillis(config.get("run_at"));
    }

    /**
     * 根据调度类型解析出 Quartz cron 表达式。
     */
    private String resolveQuartzCron(String scheduleType, Map<String, Object> config) {
        if (config == null) {
            throw new AgentStudioException(StudioError.SCHEDULE_EXPRESSION_INVALID);
        }
        if ("natural_language".equals(scheduleType)) {
            Object text = config.get("text");
            if (text == null || StringUtils.isBlank(text.toString())) {
                throw new AgentStudioException(StudioError.SCHEDULE_EXPRESSION_INVALID);
            }
            return parseNaturalLanguage(text.toString());
        }
        Object expression = config.get("expression");
        if (expression == null || StringUtils.isBlank(expression.toString())) {
            throw new AgentStudioException(StudioError.SCHEDULE_EXPRESSION_INVALID);
        }
        return toQuartzCron(expression.toString());
    }

    /**
     * 将前端标准 5 段 cron（分 时 日 月 周）转换为 Quartz 6 段 cron（秒 分 时 日 月 周）。
     * 6 段输入认为是 Quartz 格式，直接透传。
     */
    public static String toQuartzCron(String expression) {
        String[] fields = expression.trim().split("\\s+");
        if (fields.length == 6 || fields.length == 7) {
            return expression.trim();
        }
        if (fields.length != 5) {
            throw new AgentStudioException(StudioError.SCHEDULE_EXPRESSION_INVALID);
        }
        String minute = fields[0];
        String hour = fields[1];
        String dayOfMonth = fields[2];
        String month = fields[3];
        String dayOfWeek = fields[4];
        boolean domAny = "*".equals(dayOfMonth) || "?".equals(dayOfMonth);
        boolean dowAny = "*".equals(dayOfWeek) || "?".equals(dayOfWeek);
        if (!domAny && !dowAny) {
            // Quartz 不允许日期与星期同时指定，优先日期
            dayOfWeek = "?";
        } else if (!dowAny) {
            dayOfMonth = "?";
            dayOfWeek = convertDayOfWeek(dayOfWeek);
        } else {
            dayOfWeek = "?";
        }
        return "0 " + minute + " " + hour + " " + dayOfMonth + " " + month + " " + dayOfWeek;
    }

    /**
     * 标准 cron 星期（0/7=周日）转 Quartz 星期（1=周日）。
     */
    private static String convertDayOfWeek(String dow) {
        StringBuilder result = new StringBuilder();
        for (char c : dow.toCharArray()) {
            if (Character.isDigit(c)) {
                int day = c - '0';
                result.append(day % 7 + 1);
            } else {
                result.append(c);
            }
        }
        return result.toString();
    }

    /**
     * 极简中文自然语言调度解析，支持：每天/工作日/每周X/每月N号 + H点M分、每小时。
     */
    public static String parseNaturalLanguage(String text) {
        String t = text.trim();
        if (t.contains("每小时")) {
            return "0 0 * * * ?";
        }
        int[] time = extractTime(t);
        int hour = time[0];
        int minute = time[1];
        if (t.contains("工作日")) {
            return String.format("0 %d %d ? * 2-6", minute, hour);
        }
        Matcher weekly = Pattern.compile("每周([一二三四五六日天])").matcher(t);
        if (weekly.find()) {
            int dow = "日天一二三四五六".indexOf(weekly.group(1)) + 1;
            return String.format("0 %d %d ? * %d", minute, hour, dow);
        }
        Matcher monthly = Pattern.compile("每月(\\d{1,2})[号日]").matcher(t);
        if (monthly.find()) {
            return String.format("0 %d %d %s * ?", minute, hour, monthly.group(1));
        }
        if (t.contains("每天")) {
            return String.format("0 %d %d * * ?", minute, hour);
        }
        throw new AgentStudioException(StudioError.SCHEDULE_EXPRESSION_INVALID);
    }

    /**
     * 从文本中提取时间（如"9点30分"、"下午2点"、"9:15"），返回[hour, minute]。
     */
    private static int[] extractTime(String text) {
        Matcher m = Pattern.compile("(\\d{1,2})\\s*(?:点|时|:|：)\\s*(半|\\d{1,2})?").matcher(text);
        if (!m.find()) {
            return new int[]{9, 0};
        }
        int hour = Integer.parseInt(m.group(1));
        int minute = "半".equals(m.group(2)) ? 30 : (m.group(2) == null ? 0 : Integer.parseInt(m.group(2)));
        if ((text.contains("下午") || text.contains("晚上")) && hour < 12) {
            hour += 12;
        }
        return new int[]{hour, minute};
    }

    // ==================== 任务执行 ====================

    /**
     * 执行任务（由 Quartz Job 或手动触发调用），并落执行日志。
     *
     * @param taskId 任务 id
     * @param triggerType 触发方式：scheduled / manual
     */
    @Override
    public void executeTask(String taskId, String triggerType) {
        ScheduledTaskEntity task = taskMapper.selectById(taskId);
        if (task == null) {
            log.warn("Execute task skipped, task not found. taskId={}", taskId);
            return;
        }
        long now = System.currentTimeMillis();
        if (task.getValidFrom() != null && now < task.getValidFrom()) {
            log.info("Execute task skipped, before valid_from. taskId={}", taskId);
            return;
        }
        if (task.getValidUntil() != null && now > task.getValidUntil()) {
            log.info("Execute task skipped, after valid_until. taskId={}", taskId);
            return;
        }

        ScheduledTaskExecutionEntity execution = new ScheduledTaskExecutionEntity();
        execution.setId(UUID.randomUUID().toString());
        execution.setTaskId(taskId);
        execution.setProjectId(task.getProjectId());
        execution.setWorkspaceId(task.getWorkspaceId());
        execution.setStatus("running");
        execution.setTriggerType(triggerType);
        execution.setStartedAt(now);
        execution.setRetryCount(0);
        executionMapper.insert(execution);

        int maxRetries = task.getMaxRetries() == null ? 0 : Math.max(0, task.getMaxRetries());
        int retryCount = 0;
        String output = null;
        Exception error = null;
        while (true) {
            try {
                output = doExecute(task);
                error = null;
                break;
            } catch (Exception e) {
                error = e;
                log.error("Execute task failed. taskId={}, attempt={}", taskId, retryCount + 1, e);
                if (retryCount >= maxRetries) {
                    break;
                }
                retryCount++;
            }
        }

        long finishedAt = System.currentTimeMillis();
        execution.setFinishedAt(finishedAt);
        execution.setDurationMs(finishedAt - now);
        execution.setRetryCount(retryCount);
        if (error == null) {
            execution.setStatus("success");
            execution.setModelOutput(truncate(output));
        } else {
            execution.setStatus("failed");
            execution.setErrorMessage(truncate(String.valueOf(error.getMessage())));
        }
        executionMapper.updateFinish(execution);
        taskMapper.updateRunInfo(taskId, now, peekNextFireTime(taskId), error == null ? "success" : "failed",
            finishedAt);
    }

    /**
     * 按执行方式分发执行，返回输出文本。
     */
    private String doExecute(ScheduledTaskEntity task) throws Exception {
        Map<String, Object> config = parseJsonMap(task.getExecutorConfig());
        return switch (task.getExecutorType() == null ? "" : task.getExecutorType()) {
            case "agent_run" -> executeAgent(task, config);
            case "workflow_run" -> executeWorkflow(task, config);
            case "http_call" -> executeHttp(task, config);
            case "llm_prompt" -> executeLlm(task);
            default -> throw new AgentStudioException(StudioError.AGENT_TRIGGER_TYPE_INCORRECT,
                String.valueOf(task.getExecutorType()));
        };
    }

    /**
     * 调用智能体运行接口（流式），返回聚合的输出文本。
     */
    private String executeAgent(ScheduledTaskEntity task, Map<String, Object> config) throws IOException {
        String agentId = config == null ? null : String.valueOf(config.get("agent_id"));
        String query = config != null && config.get("query") != null ? String.valueOf(config.get("query"))
            : task.getPrompt();
        String path = String.format(runAgentStreamUrl, task.getProjectId(), agentId,
            UUID.randomUUID().toString());
        JSONObject body = new JSONObject();
        body.put("query", query == null ? "" : query);
        return executeStreamRequest(path, task.getWorkspaceId(), body.toJSONString());
    }

    /**
     * 调用工作流运行接口（流式），返回聚合的输出文本。
     */
    private String executeWorkflow(ScheduledTaskEntity task, Map<String, Object> config) throws IOException {
        String workflowId = config == null ? null : String.valueOf(config.get("workflow_id"));
        String path = String.format(runWorkflowStreamUrl, task.getProjectId(), workflowId,
            UUID.randomUUID().toString());
        JSONObject body = new JSONObject();
        Object inputs = config == null ? null : config.get("inputs");
        if (inputs instanceof Map<?, ?> inputsMap && !inputsMap.isEmpty()) {
            body.put("inputs", inputsMap);
        } else {
            body.put("inputs", Map.of("query", task.getPrompt() == null ? "" : task.getPrompt()));
        }
        return executeStreamRequest(path, task.getWorkspaceId(), body.toJSONString());
    }

    /**
     * 发起 HTTP POST 请求，返回响应体文本。
     */
    private String executeHttp(ScheduledTaskEntity task, Map<String, Object> config) throws IOException {
        String url = config == null ? null : String.valueOf(config.get("url"));
        if (StringUtils.isBlank(url) || "null".equals(url)) {
            throw new AgentStudioException(StudioError.SCHEDULE_EXPRESSION_INVALID);
        }
        JSONObject body = new JSONObject();
        body.put("task_id", task.getId());
        body.put("task_name", task.getName());
        body.put("prompt", task.getPrompt());
        Request request = new Request.Builder().url(url)
            .addHeader("Content-Type", "application/json")
            .post(RequestBody.create(body.toJSONString(), MediaType.get("application/json")))
            .build();
        try (Response response = okHttpClientUtils.getHttpClient().newCall(request).execute()) {
            String responseBody = response.body() == null ? "" : response.body().string();
            if (!response.isSuccessful()) {
                throw new IOException("HTTP " + response.code() + ": " + truncate(responseBody));
            }
            return responseBody;
        }
    }

    /**
     * 调用大模型（经 agent-runtime 的 chat completions 接口），返回模型输出文本。
     */
    private String executeLlm(ScheduledTaskEntity task) throws IOException {
        JSONObject message = new JSONObject();
        message.put("role", "user");
        message.put("content", task.getPrompt() == null ? "" : task.getPrompt());
        JSONObject body = new JSONObject();
        body.put("model", task.getModelId());
        body.put("stream", false);
        body.put("messages", JSONArray.of(message));
        String url = agentRuntimeEndpoint + LLM_CHAT_API + "?workspace_id=" + task.getWorkspaceId();
        Request request = new Request.Builder().url(url)
            .addHeader("Content-Type", "application/json")
            .addHeader("X-Auth-Token", "")
            .post(RequestBody.create(body.toJSONString(), MediaType.get("application/json")))
            .build();
        try (Response response = okHttpClientUtils.getHttpClient().newCall(request).execute()) {
            String responseBody = response.body() == null ? "" : response.body().string();
            if (!response.isSuccessful()) {
                throw new IOException("HTTP " + response.code() + ": " + truncate(responseBody));
            }
            try {
                JSONObject json = JSON.parseObject(responseBody);
                JSONArray choices = json.getJSONArray("choices");
                if (choices != null && !choices.isEmpty()) {
                    JSONObject messageObj = choices.getJSONObject(0).getJSONObject("message");
                    if (messageObj != null && messageObj.getString("content") != null) {
                        return messageObj.getString("content");
                    }
                }
            } catch (Exception e) {
                log.warn("Parse llm response failed, return raw body. taskId={}", task.getId());
            }
            return responseBody;
        }
    }

    /**
     * 发起流式请求并聚合 SSE data 行。
     */
    private String executeStreamRequest(String path, String workspaceId, String jsonBody) throws IOException {
        String url = agentRuntimeEndpoint + path + "?workspace_id=" + workspaceId;
        Request request = new Request.Builder().url(url)
            .addHeader("Content-Type", "application/json")
            .addHeader("X-Auth-Token", "")
            .addHeader("stream", "true")
            .post(RequestBody.create(jsonBody, MediaType.get("application/json")))
            .build();
        try (Response response = okHttpClientUtils.getHttpClient().newCall(request).execute()) {
            if (!response.isSuccessful()) {
                String errBody = response.body() == null ? "" : response.body().string();
                throw new IOException("HTTP " + response.code() + ": " + truncate(errBody));
            }
            ResponseBody body = response.body();
            if (body == null) {
                return "";
            }
            String raw = body.string();
            StringBuilder output = new StringBuilder();
            for (String line : raw.split("\n")) {
                if (line.startsWith("data:")) {
                    String data = line.substring("data:".length()).trim();
                    if (!data.isEmpty() && !"[DONE]".equals(data) && output.length() < MAX_OUTPUT_LENGTH) {
                        output.append(data).append('\n');
                    }
                }
            }
            return output.length() > 0 ? truncate(output.toString()) : truncate(raw);
        }
    }

    /**
     * 查询任务当前的下次触发时间。
     */
    private Long peekNextFireTime(String taskId) {
        try {
            Trigger trigger = scheduler.getTrigger(new TriggerKey(JOB_NAME_PREFIX + taskId, JOB_GROUP));
            Date nextFireTime = trigger == null ? null : trigger.getNextFireTime();
            return nextFireTime == null ? null : nextFireTime.getTime();
        } catch (SchedulerException e) {
            log.warn("Peek next fire time failed. taskId={}", taskId, e);
            return null;
        }
    }

    // ==================== 私有工具方法 ====================

    private ScheduledTaskEntity requireTask(String projectId, String workspaceId, String taskId) {
        ScheduledTaskEntity entity = taskMapper.selectById(taskId);
        if (entity == null || !projectId.equals(entity.getProjectId()) || !workspaceId.equals(
            entity.getWorkspaceId())) {
            throw new AgentStudioException(StudioError.SCHEDULED_TASK_NOT_EXIST, taskId);
        }
        return entity;
    }

    private void validateReq(ScheduledTaskReq req) {
        if (req == null || StringUtils.isBlank(req.getName())) {
            throw new AgentStudioException(StudioError.SCHEDULE_EXPRESSION_INVALID);
        }
        if (req.getExecutor() == null || !EXECUTOR_TYPES.contains(req.getExecutor().getType())) {
            throw new AgentStudioException(StudioError.AGENT_TRIGGER_TYPE_INCORRECT,
                req.getExecutor() == null ? "null" : req.getExecutor().getType());
        }
    }

    private void fillEntityFromReq(ScheduledTaskEntity entity, ScheduledTaskReq req) {
        entity.setName(req.getName());
        entity.setDescription(req.getDescription());
        entity.setScheduleType(req.getSchedule() == null ? "cron" : req.getSchedule().getType());
        entity.setScheduleConfig(
            req.getSchedule() == null ? null : JSON.toJSONString(req.getSchedule().getConfig()));
        entity.setRepeatType(req.getRepeat() == null ? "always" : req.getRepeat().getType());
        entity.setValidFrom(toMillis(req.getValidFrom()));
        entity.setValidUntil(toMillis(req.getValidUntil()));
        entity.setExecutorType(req.getExecutor().getType());
        entity.setExecutorConfig(JSON.toJSONString(
            req.getExecutor().getConfig() == null ? Map.of() : req.getExecutor().getConfig()));
        entity.setModelId(req.getModelId());
        entity.setPrompt(req.getPrompt());
        entity.setMaxRetries(req.getMaxRetries() == null ? 3 : req.getMaxRetries());
        entity.setNotification(req.getNotification() == null ? null : JSON.toJSONString(req.getNotification()));
    }

    /**
     * 将 ISO8601 字符串 / 毫秒时间戳统一解析为毫秒时间戳。
     */
    private static Long toMillis(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof Number number) {
            return number.longValue();
        }
        String str = value.toString().trim();
        if (str.isEmpty() || "null".equalsIgnoreCase(str)) {
            return null;
        }
        try {
            return Instant.parse(str).toEpochMilli();
        } catch (Exception ignored) {
            // 非 ISO instant 格式，继续尝试其他格式
        }
        try {
            return OffsetDateTime.parse(str).toInstant().toEpochMilli();
        } catch (Exception ignored) {
            // 非 offset 时间格式，继续尝试数字
        }
        try {
            return Long.parseLong(str);
        } catch (NumberFormatException e) {
            throw new AgentStudioException(StudioError.SCHEDULE_EXPRESSION_INVALID);
        }
    }

    private static Map<String, Object> parseJsonMap(String json) {
        if (StringUtils.isBlank(json)) {
            return null;
        }
        try {
            return JSON.parseObject(json);
        } catch (Exception e) {
            return null;
        }
    }

    private static String truncate(String text) {
        if (text == null) {
            return null;
        }
        return text.length() <= MAX_OUTPUT_LENGTH ? text : text.substring(0, MAX_OUTPUT_LENGTH);
    }

    private ScheduledTaskRsp toRsp(ScheduledTaskEntity entity) {
        ScheduledTaskRsp rsp = new ScheduledTaskRsp();
        rsp.setId(entity.getId());
        rsp.setTenantId(null);
        rsp.setWorkspaceId(entity.getWorkspaceId());
        rsp.setCreatorId(entity.getCreatorId());
        rsp.setCreatorName(entity.getCreatorName());
        rsp.setName(entity.getName());
        rsp.setDescription(entity.getDescription());
        rsp.setStatus(entity.getStatus());
        rsp.setScheduleType(entity.getScheduleType());
        rsp.setScheduleConfig(parseJsonMap(entity.getScheduleConfig()));
        rsp.setRepeatType(entity.getRepeatType());
        rsp.setValidFrom(entity.getValidFrom());
        rsp.setValidUntil(entity.getValidUntil());
        rsp.setExecutorType(entity.getExecutorType());
        Map<String, Object> executorConfig = parseJsonMap(entity.getExecutorConfig());
        rsp.setExecutorConfig(executorConfig == null ? Map.of() : executorConfig);
        rsp.setModelId(entity.getModelId());
        rsp.setPrompt(entity.getPrompt());
        rsp.setSkills(Collections.emptyList());
        rsp.setConnectorType(null);
        rsp.setMaxRetries(entity.getMaxRetries());
        Map<String, Object> notification = parseJsonMap(entity.getNotification());
        rsp.setNotification(notification);
        rsp.setIsRunning(false);
        rsp.setLastRunAt(entity.getLastRunAt());
        rsp.setNextRunAt(entity.getNextRunAt());
        rsp.setLastRunStatus(entity.getLastRunStatus());
        rsp.setRunCount(entity.getRunCount());
        rsp.setTotalCreditsUsed(0L);
        rsp.setCreatedAt(entity.getCreatedAt());
        rsp.setUpdatedAt(entity.getUpdatedAt());
        return rsp;
    }

    private ScheduledExecutionRsp toExecutionRsp(ScheduledTaskExecutionEntity entity, String taskName) {
        ScheduledExecutionRsp rsp = new ScheduledExecutionRsp();
        rsp.setId(entity.getId());
        rsp.setTaskId(entity.getTaskId());
        rsp.setTaskName(taskName);
        rsp.setStatus(entity.getStatus());
        rsp.setTriggerType(entity.getTriggerType());
        rsp.setStartedAt(entity.getStartedAt());
        rsp.setFinishedAt(entity.getFinishedAt());
        rsp.setDurationMs(entity.getDurationMs());
        rsp.setErrorMessage(entity.getErrorMessage());
        rsp.setModelOutput(entity.getModelOutput());
        rsp.setCreditsUsed(0L);
        rsp.setRetryCount(entity.getRetryCount());
        rsp.setArtifacts(Collections.emptyList());
        return rsp;
    }
}
