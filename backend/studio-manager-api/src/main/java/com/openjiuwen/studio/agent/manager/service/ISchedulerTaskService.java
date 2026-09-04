/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.manager.dto.scheduler.ScheduledExecutionListRsp;
import com.openjiuwen.studio.agent.manager.dto.scheduler.ScheduledTaskListRsp;
import com.openjiuwen.studio.agent.manager.dto.scheduler.ScheduledTaskReq;
import com.openjiuwen.studio.agent.manager.dto.scheduler.ScheduledTaskRsp;

import java.util.List;
import java.util.Map;

/**
 * 自动化（定时任务）服务接口。
 */
public interface ISchedulerTaskService {
    /**
     * 创建自动化任务。
     *
     * @param projectId 项目id
     * @param workspaceId 工作空间id
     * @param req 请求体
     * @return 任务信息
     */
    ScheduledTaskRsp createTask(String projectId, String workspaceId, ScheduledTaskReq req);

    /**
     * 更新自动化任务。
     *
     * @param projectId 项目id
     * @param workspaceId 工作空间id
     * @param taskId 任务id
     * @param req 请求体
     * @return 任务信息
     */
    ScheduledTaskRsp updateTask(String projectId, String workspaceId, String taskId, ScheduledTaskReq req);

    /**
     * 删除自动化任务。
     *
     * @param projectId 项目id
     * @param workspaceId 工作空间id
     * @param taskId 任务id
     */
    void deleteTask(String projectId, String workspaceId, String taskId);

    /**
     * 查询单个任务。
     *
     * @param projectId 项目id
     * @param workspaceId 工作空间id
     * @param taskId 任务id
     * @return 任务信息
     */
    ScheduledTaskRsp getTask(String projectId, String workspaceId, String taskId);

    /**
     * 分页查询任务列表。
     *
     * @param projectId 项目id
     * @param workspaceId 工作空间id
     * @param status 状态过滤
     * @param search 名称搜索
     * @param page 页码
     * @param pageSize 页大小
     * @return 分页列表
     */
    ScheduledTaskListRsp listTasks(String projectId, String workspaceId, String status, String search, int page,
        int pageSize);

    /**
     * 启用任务。
     *
     * @param projectId 项目id
     * @param workspaceId 工作空间id
     * @param taskId 任务id
     * @return 任务信息
     */
    ScheduledTaskRsp enableTask(String projectId, String workspaceId, String taskId);

    /**
     * 禁用任务。
     *
     * @param projectId 项目id
     * @param workspaceId 工作空间id
     * @param taskId 任务id
     * @return 任务信息
     */
    ScheduledTaskRsp disableTask(String projectId, String workspaceId, String taskId);

    /**
     * 手动触发一次执行（异步）。
     *
     * @param projectId 项目id
     * @param workspaceId 工作空间id
     * @param taskId 任务id
     */
    void triggerTask(String projectId, String workspaceId, String taskId);

    /**
     * 分页查询执行日志。
     *
     * @param projectId 项目id
     * @param workspaceId 工作空间id
     * @param taskId 任务id
     * @param status 状态过滤
     * @param page 页码
     * @param pageSize 页大小
     * @return 分页列表
     */
    ScheduledExecutionListRsp listExecutions(String projectId, String workspaceId, String taskId, String status,
        int page, int pageSize);

    /**
     * 预览调度接下来 5 次的执行时间。
     *
     * @param schedule 调度配置
     * @return 下次执行时间列表
     */
    Map<String, Object> preview(ScheduledTaskReq.ScheduleInfo schedule);

    /**
     * 支持的执行方式列表。
     *
     * @return 执行方式列表
     */
    List<Map<String, Object>> executorTypes();

    /**
     * 执行任务（由 Quartz Job 或手动触发调用），并落执行日志。
     *
     * @param taskId 任务id
     * @param triggerType 触发方式：scheduled / manual
     */
    void executeTask(String taskId, String triggerType);
}
