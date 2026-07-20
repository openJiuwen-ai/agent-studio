/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.alibaba.fastjson2.JSONObject;
import com.github.pagehelper.PageInfo;
import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.agent.common.dto.run.*;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.Constant;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.ConversationParams;
import com.openjiuwen.studio.agent.manager.entity.TaskEntity;
import com.openjiuwen.studio.agent.manager.enums.MessageRole;
import com.openjiuwen.studio.agent.manager.mapper.AsyncTaskMapper;
import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.time.Duration;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;

/**
 * 任务管理面service
 *
 */
@Slf4j
@Service
public class TaskManagementService implements ITaskManagementService {
    /**
     * redis存header key
     */
    private static final String REDIS_HEADER_KEY = "agent:runtime:async:header:%s";

    @Autowired
    AsyncTaskMapper asyncTaskMapper;

    @Autowired
    RedisClient redisClient;

    @Autowired
    TaskRuntimeService taskRuntimeService;

    @Autowired
    ConversationHistoryService conversationHistoryService;

    /**
     * 异步任务超期时间，建议调试记录超期时间保持一致
     */
    @Value("${task.async.expire-days:}")
    private int taskAsyncExpireDays;

    /**
     * 异步任务最长执行时间
     */
    @Value("${task.async.max-execute-milliseconds:}")
    private int taskAsyncMaxExecuteMilliseconds;

    @Override
    public CancelTaskRsp cancelTask(String projectId, String workflowId, String taskId, String workspaceId) {
        TaskEntity taskEntity = getTaskEntityById(projectId, workflowId, taskId, workspaceId);

        CancelTaskRsp cancelTaskRsp = new CancelTaskRsp().setId(taskId).setWorkflowId(workflowId);
        if (StringUtils.isEmpty(taskEntity.getId())) {
            return cancelTaskRsp.setStatus(TaskStatus.FAILED).setMessage("Please check your permission!");
        }
        // 取消初始化和允许中任务，同时释放线程池和连接池
        if (Strings.CS.equals(taskEntity.getStatus(), TaskStatus.INIT.getValue()) || Strings.CS.equals(
                taskEntity.getStatus(), TaskStatus.RUNNING.getValue())) {
            taskEntity.setStatus(TaskStatus.CANCELLED.getValue());
            taskEntity.setMessage("Task has been cancelled successfully!");
            Date currentDate = new Date(System.currentTimeMillis());
            taskEntity.setUpdateTime(currentDate);
            taskEntity.setFinishTime(currentDate);
            asyncTaskMapper.updateByPrimaryKey(taskEntity);
            taskRuntimeService.cancelTask(taskId);
            setUserQueryToHistory(workflowId, taskEntity.getConversationId(), currentDate, "会话取消",
                    MessageRole.ASSISTANT.name().toLowerCase(Locale.ROOT));
            return cancelTaskRsp.setStatus(TaskStatus.valueOf(taskEntity.getStatus()))
                    .setMessage(taskEntity.getMessage());
        } else {
            return cancelTaskRsp.setStatus(TaskStatus.valueOf(taskEntity.getStatus()))
                    .setMessage("Task status is not init or running!");
        }
    }

    @Override
    public TaskRsp createTask(String projectId, String workflowId, String version, String workspaceId,
                              CreateTaskReq body) {
        // 生成任务ID和conversation ID
        String taskId = UUID.randomUUID().toString();
        String conversationId = UUID.randomUUID().toString();
        Date currentTime = new Date(System.currentTimeMillis());

        // 任务header存入redis
        redisClient.set(String.format(REDIS_HEADER_KEY, taskId), JSONObject.toJSONString(getNonSensitiveHeader()),
                Duration.ofDays(taskAsyncExpireDays));

        if (body.getInputs() != null) {
            setUserQueryToHistory(workflowId, conversationId, currentTime, JSONObject.toJSONString(body.getInputs()),
                    MessageRole.USER.name().toLowerCase(Locale.ROOT));
        }

        // 如已发布工作流，appVersion为版本时间，如未发布工作流，appVersion为工作流最后编辑时间
        String appVersion = determineAppVersion(version, body);

        // 创建任务实体
        TaskEntity taskEntity = TaskEntity.builder()
                .id(taskId)
                .name(body.getName())
                .conversationId(conversationId)
                .userId(RequestContextUtils.getRequestUserId())
                .projectId(projectId)
                .domainId(RequestContextUtils.getRequestUserDomainId())
                .workspaceId(workspaceId)
                .type(body.getType())
                .mode(body.getMode())
                .appId(workflowId)
                .appVersion(appVersion)
                .isPublished(StringUtils.isNotEmpty(version))
                .status(body.getInputs() != null ? TaskStatus.INIT.getValue() : TaskStatus.PENDING.getValue())
                .inputs(body.getInputs() != null ? JSONObject.toJSONString(body.getInputs()) : null)
                .timeout(getLimitedTimeOut(body.getTimeout()))
                .createTime(currentTime)
                .updateTime(currentTime)
                .build();
        asyncTaskMapper.createEntity(taskEntity);
        return convertEntityToRsp(taskEntity);
    }

    private Map<String, String> getNonSensitiveHeader() {
        Map<String, String> headers = new HashMap<>();
        ServletRequestAttributes servletRequestAttributes
                = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        if (servletRequestAttributes != null) {
            HttpServletRequest request = servletRequestAttributes.getRequest();
            Enumeration<String> headerNames = request.getHeaderNames();

            // 遍历并过滤非敏感header存redis
            while (headerNames.hasMoreElements()) {
                String headerName = headerNames.nextElement();
                String headerValue = request.getHeader(headerName);
                // Include all headers for async task execution
                headers.put(headerName, headerValue);
            }
        }
        return headers;
    }

    @Override
    public CommonDeleteRsp deleteTask(String projectId, String workflowId, String taskId, String workspaceId) {
        TaskEntity taskEntity = getTaskEntityById(projectId, workflowId, taskId, workspaceId);
        CommonDeleteRsp commonDeleteRsp = new CommonDeleteRsp().setId(taskId);
        if (!StringUtils.isEmpty(taskEntity.getId())) {
            asyncTaskMapper.deleteByIds(Collections.singletonList(taskId));
        }
        return commonDeleteRsp;
    }

    @Override
    public TaskListRsp listTask(String projectId, String workflowId, ListTaskQo listTaskQo) {
        TaskEntity filter = TaskEntity.builder()
                .projectId(projectId)
                .type(listTaskQo.getType())
                .status(listTaskQo.getStatus())
                .workspaceId(listTaskQo.getWorkspaceId())
                .appId(workflowId)
                .build();
        List<TaskEntity> taskEntities = asyncTaskMapper.getTaskEntity(filter, listTaskQo.getSort(),
                listTaskQo.getOrder());
        PageInfo<TaskEntity> pageInfo = new PageInfo<>(taskEntities);

        List<TaskListItem> infos = new ArrayList<>();
        for (TaskEntity taskEntity : taskEntities) {
            infos.add(convertEntityToTaskItem(taskEntity));
        }
        return new TaskListRsp().setData(infos).setCount(pageInfo.getTotal()).setWorkflowId(workflowId);
    }

    @Override
    public TaskRsp resumeTask(String projectId, String workflowId, String taskId, String workspaceId,
                              ResumeTaskReq body) {
        // 任务header存入redis
        redisClient.set(String.format(REDIS_HEADER_KEY, taskId), JSONObject.toJSONString(getNonSensitiveHeader()),
                Duration.ofDays(taskAsyncExpireDays));

        TaskEntity taskEntity = getTaskEntityById(projectId, workflowId, taskId, workspaceId);
        if (StringUtils.isEmpty(taskEntity.getId())) {
            throw new AgentStudioException(StudioError.WORKFLOW_ASYNC_TASK_NOT_FOUND);
        }
        checkStatus(TaskStatus.valueOf(taskEntity.getStatus()), taskEntity.getType());
        Date currentTime = new Date(System.currentTimeMillis());
        taskEntity.setStatus(TaskStatus.INIT.getValue());
        taskEntity.setUpdateTime(currentTime);
        taskEntity.setInputs(JSONObject.toJSONString(body.getInputs()));
        taskEntity.setTimeout(getLimitedTimeOut(body.getTimeout()));
        asyncTaskMapper.updateByPrimaryKey(taskEntity);
        if (body.getInputs() != null) {
            setUserQueryToHistory(workflowId, taskEntity.getConversationId(), currentTime,
                    JSONObject.toJSONString(body.getInputs()), MessageRole.USER.name().toLowerCase(Locale.ROOT));
        }
        return convertEntityToRsp(taskEntity);
    }

    @Override
    public TaskRsp modifyTask(String projectId, String workflowId, String taskId, String workspaceId,
                              ModifyTaskReq body) {
        // 修改接口当前支持修改name和超时时间
        TaskEntity entity = TaskEntity.builder()
                .id(taskId)
                .projectId(projectId)
                .userId(RequestContextUtils.getRequestUserId())
                .workspaceId(workspaceId)
                .appId(workflowId)
                .name(body.getName())
                .timeout(getLimitedTimeOut(body.getTimeout()))
                .updateTime(new Date(System.currentTimeMillis()))
                .build();
        asyncTaskMapper.updateByPrimaryKey(entity);
        return retrieveTask(projectId, workflowId, taskId, new RetrieveTaskQo().setWorkspaceId(workspaceId));
    }

    @Override
    public TaskRsp retrieveTask(String projectId, String workflowId, String taskId, RetrieveTaskQo retrieveTaskQo) {
        TaskEntity taskEntity = getTaskEntityById(projectId, workflowId, taskId, retrieveTaskQo.getWorkspaceId());
        return convertEntityToRsp(taskEntity);
    }

    private TaskEntity getTaskEntityById(String projectId, String workflowId, String taskId, String workspaceId) {
        TaskEntity filter = TaskEntity.builder()
                .id(taskId)
                .projectId(projectId)
                .appId(workflowId)
                .workspaceId(workspaceId)
                .build();
        List<TaskEntity> taskEntities = asyncTaskMapper.getTaskEntity(filter, null, null);
        if (taskEntities.isEmpty()) {
            return TaskEntity.builder().build();
        }
        return taskEntities.get(0);
    }

    private TaskListItem convertEntityToTaskItem(TaskEntity taskEntity) {
        return new TaskListItem().setId(taskEntity.getId())
                .setName(taskEntity.getName())
                .setType(taskEntity.getType())
                .setIsPublished(taskEntity.getIsPublished())
                .setStatus(TaskStatus.valueOf(taskEntity.getStatus()))
                .setCreateTime(taskEntity.getCreateTime())
                .setFinishTime(taskEntity.getFinishTime());
    }

    private TaskRsp convertEntityToRsp(TaskEntity taskEntity) {
        return new TaskRsp().setId(taskEntity.getId())
                .setName(taskEntity.getName())
                .setConversationId(taskEntity.getConversationId())
                .setIsPublished(taskEntity.getIsPublished())
                .setInputs(JSONObject.parseObject(taskEntity.getInputs()))
                .setOutputs(JSONObject.parseObject(taskEntity.getOutputs()))
                .setStatus(TaskStatus.valueOf(taskEntity.getStatus()))
                .setMessage(StringUtils.isEmpty(taskEntity.getMessage()) ? null : taskEntity.getMessage())
                .setCreateTime(taskEntity.getCreateTime())
                .setUpdateTime(taskEntity.getUpdateTime())
                .setFinishTime(taskEntity.getFinishTime())
                .setWorkflow(new TaskRspWorkflow().setId(taskEntity.getAppId())
                        .setType(taskEntity.getType())
                        .setVersionId(taskEntity.getAppVersion()));
    }

    private Integer getLimitedTimeOut(Integer timeout) {
        return timeout != null ? Math.max(Math.min(taskAsyncMaxExecuteMilliseconds, timeout), 1) : null;
    }

    public void checkStatus(TaskStatus currentStatus, String workflowType) {
        switch (currentStatus) {
            case INIT, RUNNING:
                throw new AgentStudioException(StudioError.WORKFLOW_ASYNC_NOT_PENDING);
            case COMPLETED, FAILED:
                if (!"chat".equalsIgnoreCase(workflowType)) {
                    throw new AgentStudioException(StudioError.WORKFLOW_ASYNC_NOT_PENDING);
                }
                break;
            default:
                break;
        }
    }

    public void setUserQueryToHistory(String workflowId, String conversationId, Date currentTime, String content,
                                      String name) {
        ConversationParams conversationParams = new ConversationParams()
                .setExecuteType(Constant.AppType.WORKFLOW)
                .setId(workflowId)
                .setConversationId(conversationId);
        Message message = new Message();
        message.setContent(content);
        message.setRole(name);
        message.setCreateTime(currentTime.getTime());
        conversationHistoryService.updateConversation(conversationParams, List.of(message), false);
    }

    private String determineAppVersion(String version, CreateTaskReq body) {
        if (StringUtils.isNotEmpty(version)) {
            return version;
        }
        if (body.getVersion() != null) {
            return body.getVersion().toString();
        }
        return null;
    }
}
