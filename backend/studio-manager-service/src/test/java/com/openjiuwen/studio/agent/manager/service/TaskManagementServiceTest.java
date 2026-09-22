/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.dto.run.CancelTaskRsp;
import com.openjiuwen.studio.agent.common.dto.run.CreateTaskReq;
import com.openjiuwen.studio.agent.common.dto.run.ListTaskQo;
import com.openjiuwen.studio.agent.common.dto.run.ModifyTaskReq;
import com.openjiuwen.studio.agent.common.dto.run.ResumeTaskReq;
import com.openjiuwen.studio.agent.common.dto.run.RetrieveTaskQo;
import com.openjiuwen.studio.agent.common.dto.run.TaskListItem;
import com.openjiuwen.studio.agent.common.dto.run.TaskListRsp;
import com.openjiuwen.studio.agent.common.dto.run.TaskRsp;
import com.openjiuwen.studio.agent.common.dto.run.TaskStatus;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.entity.TaskEntity;
import com.openjiuwen.studio.agent.manager.mapper.AsyncTaskMapper;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.util.Arrays;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * TaskManagementService 单元测试
 *
 * <p>覆盖 A 方案（BUG2026091500803）修改点：
 * <ul>
 *     <li>getTaskEntityById 查空时抛出 WORKFLOW_ASYNC_TASK_NOT_FOUND（404），不再返回空实体</li>
 *     <li>convertEntityToRsp / convertEntityToTaskItem 使用 TaskStatus.fromValue 按 value 匹配，
 *     status 为 null 或未匹配值时返回 null，不抛 NPE</li>
 *     <li>cancelTask 成功分支与 else 分支 setStatus 使用 TaskStatus.fromValue 按 value 匹配</li>
 *     <li>resumeTask 调用点 checkStatus(TaskStatus.fromValue(status), type)，覆盖正常匹配、
 *     RUNNING/COMPLETED 分支抛 WORKFLOW_ASYNC_NOT_PENDING、null/非法值行为</li>
 *     <li>createTask / deleteTask / modifyTask 基本路径覆盖</li>
 * </ul>
 */
@ExtendWith(MockitoExtension.class)
public class TaskManagementServiceTest {

    private static final String PROJECT_ID = "project-1";
    private static final String WORKFLOW_ID = "workflow-1";
    private static final String TASK_ID = "task-1";
    private static final String WORKSPACE_ID = "workspace-1";

    @Mock
    private AsyncTaskMapper asyncTaskMapper;

    @Mock
    private RedisClient redisClient;

    @Mock
    private TaskRuntimeService taskRuntimeService;

    @Mock
    private ConversationHistoryService conversationHistoryService;

    @InjectMocks
    private TaskManagementService taskManagementService;

    /**
     * 构造一个字段齐全的任务实体
     *
     * @param status 任务状态值（可传 null）
     * @return 任务实体
     */
    private TaskEntity buildTaskEntity(String status) {
        return TaskEntity.builder()
                .id(TASK_ID)
                .name("test-task")
                .conversationId("conversation-1")
                .isPublished(true)
                .status(status)
                .inputs("{\"a\":1}")
                .outputs("{\"b\":2}")
                .message("task message")
                .createTime(new Date(1700000000000L))
                .updateTime(new Date(1700000001000L))
                .finishTime(new Date(1700000002000L))
                .appId(WORKFLOW_ID)
                .type("chat")
                .appVersion("v1")
                .build();
    }

    /**
     * 用例描述：retrieveTask 查询的任务在库中不存在时，getTaskEntityById 查空应抛出任务不存在异常
     * 预制条件：asyncTaskMapper.getTaskEntity 返回空列表
     * 输入参数：projectId=project-1, workflowId=workflow-1, taskId=task-1, workspaceId=workspace-1
     * 预期结果：抛出 AgentStudioException，errorCode 为 WORKFLOW_ASYNC_TASK_NOT_FOUND（HTTP 404，code=1023）
     */
    @Test
    public void testRetrieveTaskShouldThrowNotFoundWhenTaskMissing() {
        when(asyncTaskMapper.getTaskEntity(any(), any(), any())).thenReturn(Collections.emptyList());

        AgentStudioException exception = assertThrows(AgentStudioException.class,
                () -> taskManagementService.retrieveTask(PROJECT_ID, WORKFLOW_ID, TASK_ID,
                        new RetrieveTaskQo().setWorkspaceId(WORKSPACE_ID)));

        assertEquals(StudioError.WORKFLOW_ASYNC_TASK_NOT_FOUND, exception.getErrorCode());
        assertEquals(HttpStatus.NOT_FOUND, exception.getErrorCode().getHttpStatus());
        assertEquals("1023", exception.getErrorCode().getCode());
    }

    /**
     * 用例描述：retrieveTask 查询的任务存在时，应正常转换为 TaskRsp 返回
     * 预制条件：asyncTaskMapper.getTaskEntity 返回包含 1 条任务实体的列表，status=COMPLETED
     * 输入参数：projectId=project-1, workflowId=workflow-1, taskId=task-1, workspaceId=workspace-1
     * 预期结果：返回 TaskRsp，所有字段按实体正确转换，status 由 fromValue 匹配为 COMPLETED
     */
    @Test
    public void testRetrieveTaskShouldReturnConvertedRspWhenTaskFound() {
        TaskEntity entity = buildTaskEntity(TaskStatus.COMPLETED.getValue());
        when(asyncTaskMapper.getTaskEntity(any(), any(), any())).thenReturn(List.of(entity));

        TaskRsp rsp = taskManagementService.retrieveTask(PROJECT_ID, WORKFLOW_ID, TASK_ID,
                new RetrieveTaskQo().setWorkspaceId(WORKSPACE_ID));

        assertEquals(TASK_ID, rsp.getId());
        assertEquals("test-task", rsp.getName());
        assertEquals("conversation-1", rsp.getConversationId());
        assertEquals(Boolean.TRUE, rsp.isIsPublished());
        assertEquals(TaskStatus.COMPLETED, rsp.getStatus());
        assertEquals("task message", rsp.getMessage());
        assertEquals(entity.getCreateTime(), rsp.getCreateTime());
        assertEquals(entity.getUpdateTime(), rsp.getUpdateTime());
        assertEquals(entity.getFinishTime(), rsp.getFinishTime());
        assertNotNull(rsp.getInputs());
        assertNotNull(rsp.getOutputs());
        assertNotNull(rsp.getWorkflow());
        assertEquals(WORKFLOW_ID, rsp.getWorkflow().getId());
        assertEquals("chat", rsp.getWorkflow().getType());
        assertEquals("v1", rsp.getWorkflow().getVersionId());
    }

    /**
     * 用例描述：convertEntityToRsp 对全量 TaskStatus 枚举值，fromValue 均应正确匹配对应枚举
     * 预制条件：asyncTaskMapper.getTaskEntity 依次返回 status 为各枚举 value 的任务实体
     * 输入参数：循环传入 INIT/RUNNING/PENDING/COMPLETED/FAILED/CANCELLED 六个状态值
     * 预期结果：每个状态的 TaskRsp.status 与对应 TaskStatus 枚举一致
     */
    @Test
    public void testRetrieveTaskShouldMapAllTaskStatusValues() {
        for (TaskStatus expected : TaskStatus.values()) {
            TaskEntity entity = buildTaskEntity(expected.getValue());
            when(asyncTaskMapper.getTaskEntity(any(), any(), any())).thenReturn(List.of(entity));

            TaskRsp rsp = taskManagementService.retrieveTask(PROJECT_ID, WORKFLOW_ID, TASK_ID,
                    new RetrieveTaskQo().setWorkspaceId(WORKSPACE_ID));

            assertEquals(expected, rsp.getStatus(),
                    "status value [" + expected.getValue() + "] 应匹配枚举 " + expected);
        }
    }

    /**
     * 用例描述：convertEntityToRsp 遇到 status 为 null 的任务实体时，fromValue 返回 null，
     * setStatus(null) 不抛 NPE（修复前 valueOf(null) 会抛 NPE）
     * 预制条件：asyncTaskMapper.getTaskEntity 返回 status=null 的任务实体
     * 输入参数：status=null
     * 预期结果：不抛异常，TaskRsp.status 为 null
     */
    @Test
    public void testRetrieveTaskShouldNotThrowNpeWhenEntityStatusNull() {
        TaskEntity entity = buildTaskEntity(null);
        when(asyncTaskMapper.getTaskEntity(any(), any(), any())).thenReturn(List.of(entity));

        TaskRsp rsp = taskManagementService.retrieveTask(PROJECT_ID, WORKFLOW_ID, TASK_ID,
                new RetrieveTaskQo().setWorkspaceId(WORKSPACE_ID));

        assertNull(rsp.getStatus());
    }

    /**
     * 用例描述：convertEntityToRsp 遇到 status 为未匹配的非法值（如 UNKNOWN）时，
     * fromValue 返回 null 而不抛异常
     * 预制条件：asyncTaskMapper.getTaskEntity 返回 status=UNKNOWN 的任务实体
     * 输入参数：status=UNKNOWN（非枚举值）
     * 预期结果：不抛异常，TaskRsp.status 为 null
     */
    @Test
    public void testRetrieveTaskShouldMapUnknownStatusToNull() {
        TaskEntity entity = buildTaskEntity("UNKNOWN");
        when(asyncTaskMapper.getTaskEntity(any(), any(), any())).thenReturn(List.of(entity));

        TaskRsp rsp = taskManagementService.retrieveTask(PROJECT_ID, WORKFLOW_ID, TASK_ID,
                new RetrieveTaskQo().setWorkspaceId(WORKSPACE_ID));

        assertNull(rsp.getStatus());
    }

    /**
     * 用例描述：listTask 对 status 正常值（RUNNING）的任务实体，convertEntityToTaskItem
     * 应正确转换为 TaskListItem
     * 预制条件：asyncTaskMapper.getTaskEntity 返回包含 1 条 status=RUNNING 的任务实体列表
     * 输入参数：projectId=project-1, workflowId=workflow-1, workspaceId=workspace-1
     * 预期结果：返回 TaskListRsp，data 中元素字段正确转换，status 匹配为 RUNNING
     */
    @Test
    public void testListTaskShouldConvertTaskItemWithStatusMapping() {
        TaskEntity entity = buildTaskEntity(TaskStatus.RUNNING.getValue());
        when(asyncTaskMapper.getTaskEntity(any(), any(), any())).thenReturn(List.of(entity));

        TaskListRsp rsp = taskManagementService.listTask(PROJECT_ID, WORKFLOW_ID,
                new ListTaskQo().setWorkspaceId(WORKSPACE_ID));

        assertEquals(WORKFLOW_ID, rsp.getWorkflowId());
        assertEquals(1L, rsp.getCount());
        assertEquals(1, rsp.getData().size());
        TaskListItem item = rsp.getData().get(0);
        assertEquals(TASK_ID, item.getId());
        assertEquals("test-task", item.getName());
        assertEquals("chat", item.getType());
        assertEquals(Boolean.TRUE, item.isIsPublished());
        assertEquals(TaskStatus.RUNNING, item.getStatus());
        assertEquals(entity.getCreateTime(), item.getCreateTime());
        assertEquals(entity.getFinishTime(), item.getFinishTime());
    }

    /**
     * 用例描述：convertEntityToTaskItem 对全量 TaskStatus 枚举值，fromValue 均应正确匹配对应枚举
     * 预制条件：asyncTaskMapper.getTaskEntity 依次返回 status 为各枚举 value 的任务实体列表
     * 输入参数：循环传入 INIT/RUNNING/PENDING/COMPLETED/FAILED/CANCELLED 六个状态值
     * 预期结果：每个状态的 TaskListItem.status 与对应 TaskStatus 枚举一致
     */
    @Test
    public void testListTaskShouldMapAllTaskStatusValues() {
        for (TaskStatus expected : TaskStatus.values()) {
            TaskEntity entity = buildTaskEntity(expected.getValue());
            when(asyncTaskMapper.getTaskEntity(any(), any(), any())).thenReturn(List.of(entity));

            TaskListRsp rsp = taskManagementService.listTask(PROJECT_ID, WORKFLOW_ID,
                    new ListTaskQo().setWorkspaceId(WORKSPACE_ID));

            assertEquals(expected, rsp.getData().get(0).getStatus(),
                    "status value [" + expected.getValue() + "] 应匹配枚举 " + expected);
        }
    }

    /**
     * 用例描述：convertEntityToTaskItem 遇到 status 为 null 的任务实体时，fromValue 返回 null，
     * setStatus(null) 不抛 NPE（修复前 valueOf(null) 会抛 NPE）
     * 预制条件：asyncTaskMapper.getTaskEntity 返回 status=null 的任务实体列表
     * 输入参数：status=null
     * 预期结果：不抛异常，TaskListItem.status 为 null
     */
    @Test
    public void testListTaskShouldNotThrowNpeWhenEntityStatusNull() {
        TaskEntity entity = buildTaskEntity(null);
        when(asyncTaskMapper.getTaskEntity(any(), any(), any())).thenReturn(List.of(entity));

        TaskListRsp rsp = taskManagementService.listTask(PROJECT_ID, WORKFLOW_ID,
                new ListTaskQo().setWorkspaceId(WORKSPACE_ID));

        assertNull(rsp.getData().get(0).getStatus());
    }

    /**
     * 用例描述：convertEntityToTaskItem 遇到 status 为未匹配的非法值（如 UNKNOWN）时，
     * fromValue 返回 null 而不抛异常
     * 预制条件：asyncTaskMapper.getTaskEntity 返回 status=UNKNOWN 的任务实体列表
     * 输入参数：status=UNKNOWN（非枚举值）
     * 预期结果：不抛异常，TaskListItem.status 为 null
     */
    @Test
    public void testListTaskShouldMapUnknownStatusToNull() {
        TaskEntity entity = buildTaskEntity("UNKNOWN");
        when(asyncTaskMapper.getTaskEntity(any(), any(), any())).thenReturn(List.of(entity));

        TaskListRsp rsp = taskManagementService.listTask(PROJECT_ID, WORKFLOW_ID,
                new ListTaskQo().setWorkspaceId(WORKSPACE_ID));

        assertNull(rsp.getData().get(0).getStatus());
    }

    /**
     * 用例描述：convertEntityToRsp 对 message 为 null 的任务实体，输出 message 置为 null
     * 预制条件：asyncTaskMapper.getTaskEntity 返回 message=null 的任务实体，status=INIT
     * 输入参数：message=null
     * 预期结果：TaskRsp.message 为 null，不抛异常
     */
    @Test
    public void testRetrieveTaskShouldSetNullMessageWhenEntityMessageBlank() {
        TaskEntity entity = buildTaskEntity(TaskStatus.INIT.getValue());
        entity.setMessage(null);
        when(asyncTaskMapper.getTaskEntity(any(), any(), any())).thenReturn(List.of(entity));

        TaskRsp rsp = taskManagementService.retrieveTask(PROJECT_ID, WORKFLOW_ID, TASK_ID,
                new RetrieveTaskQo().setWorkspaceId(WORKSPACE_ID));

        assertNull(rsp.getMessage());
        assertEquals(TaskStatus.INIT, rsp.getStatus());
    }

    /**
     * 用例描述：cancelTask 取消 INIT 状态任务，成功分支将实体状态置为 CANCELLED，
     * setStatus 通过 fromValue 按 value 正确匹配返回 CANCELLED
     * 预制条件：asyncTaskMapper.getTaskEntity 返回 status=INIT 的任务实体
     * 输入参数：projectId=project-1, workflowId=workflow-1, taskId=task-1, workspaceId=workspace-1
     * 预期结果：返回 CancelTaskRsp，status 为 CANCELLED、message 为取消成功提示；
     *          asyncTaskMapper.updateByPrimaryKey 与 taskRuntimeService.cancelTask 均被调用
     */
    @Test
    public void testCancelTaskShouldCancelInitTaskAndReturnCancelledStatus() {
        TaskEntity entity = buildTaskEntity(TaskStatus.INIT.getValue());
        when(asyncTaskMapper.getTaskEntity(any(), any(), any())).thenReturn(List.of(entity));

        CancelTaskRsp rsp = taskManagementService.cancelTask(PROJECT_ID, WORKFLOW_ID, TASK_ID, WORKSPACE_ID);

        assertEquals(TASK_ID, rsp.getId());
        assertEquals(WORKFLOW_ID, rsp.getWorkflowId());
        assertEquals(TaskStatus.CANCELLED, rsp.getStatus());
        assertEquals("Task has been cancelled successfully!", rsp.getMessage());
        // 参数对象状态迁移：实体状态应被置为 CANCELLED
        assertEquals(TaskStatus.CANCELLED.getValue(), entity.getStatus(), "取消成功后实体状态应迁移为 CANCELLED");
        verify(asyncTaskMapper).updateByPrimaryKey(entity);
        verify(taskRuntimeService).cancelTask(TASK_ID);
    }

    /**
     * 用例描述：cancelTask 取消 RUNNING 状态任务，成功分支将实体状态置为 CANCELLED，
     * setStatus 通过 fromValue 按 value 正确匹配返回 CANCELLED
     * 预制条件：asyncTaskMapper.getTaskEntity 返回 status=RUNNING 的任务实体
     * 输入参数：projectId=project-1, workflowId=workflow-1, taskId=task-1, workspaceId=workspace-1
     * 预期结果：返回 CancelTaskRsp，status 为 CANCELLED、message 为取消成功提示；
     *          asyncTaskMapper.updateByPrimaryKey 与 taskRuntimeService.cancelTask 均被调用
     */
    @Test
    public void testCancelTaskShouldCancelRunningTaskAndReturnCancelledStatus() {
        TaskEntity entity = buildTaskEntity(TaskStatus.RUNNING.getValue());
        when(asyncTaskMapper.getTaskEntity(any(), any(), any())).thenReturn(List.of(entity));

        CancelTaskRsp rsp = taskManagementService.cancelTask(PROJECT_ID, WORKFLOW_ID, TASK_ID, WORKSPACE_ID);

        assertEquals(TASK_ID, rsp.getId());
        assertEquals(WORKFLOW_ID, rsp.getWorkflowId());
        assertEquals(TaskStatus.CANCELLED, rsp.getStatus());
        assertEquals("Task has been cancelled successfully!", rsp.getMessage());
        // 参数对象状态迁移：实体状态应被置为 CANCELLED
        assertEquals(TaskStatus.CANCELLED.getValue(), entity.getStatus(), "取消成功后实体状态应迁移为 CANCELLED");
        verify(asyncTaskMapper).updateByPrimaryKey(entity);
        verify(taskRuntimeService).cancelTask(TASK_ID);
    }

    /**
     * 用例描述：cancelTask 取消非 INIT/RUNNING 状态任务（如 COMPLETED），
     * 走 else 分支，setStatus 通过 fromValue 按 value 正确匹配返回原状态
     * 预制条件：asyncTaskMapper.getTaskEntity 返回 status=COMPLETED 的任务实体
     * 输入参数：projectId=project-1, workflowId=workflow-1, taskId=task-1, workspaceId=workspace-1
     * 预期结果：返回 CancelTaskRsp，status 为 COMPLETED，message 为不可取消提示；
     *          不调用 updateByPrimaryKey 与 cancelTask
     */
    @Test
    public void testCancelTaskShouldReturnOriginalStatusWhenNotInitOrRunning() {
        TaskEntity entity = buildTaskEntity(TaskStatus.COMPLETED.getValue());
        when(asyncTaskMapper.getTaskEntity(any(), any(), any())).thenReturn(List.of(entity));

        CancelTaskRsp rsp = taskManagementService.cancelTask(PROJECT_ID, WORKFLOW_ID, TASK_ID, WORKSPACE_ID);

        assertEquals(TASK_ID, rsp.getId());
        assertEquals(WORKFLOW_ID, rsp.getWorkflowId());
        assertEquals(TaskStatus.COMPLETED, rsp.getStatus());
        assertEquals("Task status is not init or running!", rsp.getMessage());
        verify(asyncTaskMapper, never()).updateByPrimaryKey(any());
        verify(taskRuntimeService, never()).cancelTask(any());
    }

    /**
     * 用例描述：cancelTask 遇到 status 为未匹配的非法值（如 UNKNOWN）时，
     * else 分支 setStatus 通过 fromValue 返回 null，不抛 NPE（修复前 valueOf 抛 IllegalArgumentException）
     * 预制条件：asyncTaskMapper.getTaskEntity 返回 status=UNKNOWN 的任务实体
     * 输入参数：status=UNKNOWN（非枚举值）
     * 预期结果：不抛异常，CancelTaskRsp.status 为 null
     */
    @Test
    public void testCancelTaskShouldReturnNullStatusWhenStatusInvalid() {
        TaskEntity entity = buildTaskEntity("UNKNOWN");
        when(asyncTaskMapper.getTaskEntity(any(), any(), any())).thenReturn(List.of(entity));

        CancelTaskRsp rsp = taskManagementService.cancelTask(PROJECT_ID, WORKFLOW_ID, TASK_ID, WORKSPACE_ID);

        assertEquals(TASK_ID, rsp.getId());
        assertEquals(WORKFLOW_ID, rsp.getWorkflowId());
        assertNull(rsp.getStatus());
        assertEquals("Task status is not init or running!", rsp.getMessage());
    }

    /**
     * 用例描述：cancelTask 遇到 status 为 null 时，else 分支 setStatus 通过 fromValue 返回 null，
     * 不抛 NPE（修复前 valueOf(null) 抛 NPE）
     * 预制条件：asyncTaskMapper.getTaskEntity 返回 status=null 的任务实体
     * 输入参数：status=null
     * 预期结果：不抛异常，CancelTaskRsp.status 为 null
     */
    @Test
    public void testCancelTaskShouldReturnNullStatusWhenStatusNull() {
        TaskEntity entity = buildTaskEntity(null);
        when(asyncTaskMapper.getTaskEntity(any(), any(), any())).thenReturn(List.of(entity));

        CancelTaskRsp rsp = taskManagementService.cancelTask(PROJECT_ID, WORKFLOW_ID, TASK_ID, WORKSPACE_ID);

        assertEquals(TASK_ID, rsp.getId());
        assertEquals(WORKFLOW_ID, rsp.getWorkflowId());
        assertNull(rsp.getStatus());
        assertEquals("Task status is not init or running!", rsp.getMessage());
    }

    /**
     * 用例描述：resumeTask 触发 checkStatus，status 为 PENDING（default 分支）时校验通过，
     * 任务状态被置为 INIT 并通过 fromValue 正确匹配
     * 预制条件：asyncTaskMapper.getTaskEntity 返回 status=PENDING、type=chat 的任务实体
     * 输入参数：projectId=project-1, workflowId=workflow-1, taskId=task-1, workspaceId=workspace-1
     * 预期结果：不抛异常，返回 TaskRsp.status 为 INIT
     */
    @Test
    public void testResumeTaskShouldPassStatusCheckWhenStatusPending() {
        TaskEntity entity = buildTaskEntity(TaskStatus.PENDING.getValue());
        when(asyncTaskMapper.getTaskEntity(any(), any(), any())).thenReturn(List.of(entity));

        TaskRsp rsp = taskManagementService.resumeTask(PROJECT_ID, WORKFLOW_ID, TASK_ID, WORKSPACE_ID,
                new ResumeTaskReq());

        assertEquals(TaskStatus.INIT, rsp.getStatus());
    }

    /**
     * 用例描述：resumeTask 触发 checkStatus，status 为 RUNNING 时 fromValue 正确匹配，
     * 进入 switch 的 INIT/RUNNING 分支，抛出不可恢复异常
     * 预制条件：asyncTaskMapper.getTaskEntity 返回 status=RUNNING 的任务实体
     * 输入参数：status=RUNNING, type=chat
     * 预期结果：抛出 AgentStudioException，errorCode 为 WORKFLOW_ASYNC_NOT_PENDING
     */
    @Test
    public void testResumeTaskShouldThrowNotPendingWhenStatusRunning() {
        TaskEntity entity = buildTaskEntity(TaskStatus.RUNNING.getValue());
        when(asyncTaskMapper.getTaskEntity(any(), any(), any())).thenReturn(List.of(entity));

        AgentStudioException exception = assertThrows(AgentStudioException.class,
                () -> taskManagementService.resumeTask(PROJECT_ID, WORKFLOW_ID, TASK_ID, WORKSPACE_ID,
                        new ResumeTaskReq()));

        assertEquals(StudioError.WORKFLOW_ASYNC_NOT_PENDING, exception.getErrorCode());
    }

    /**
     * 用例描述：resumeTask 触发 checkStatus，status 为 COMPLETED 且 type 非 chat 时，
     * fromValue 正确匹配进入 COMPLETED/FAILED 分支，抛出不可恢复异常
     * 预制条件：asyncTaskMapper.getTaskEntity 返回 status=COMPLETED、type=workflow 的任务实体
     * 输入参数：status=COMPLETED, type=workflow
     * 预期结果：抛出 AgentStudioException，errorCode 为 WORKFLOW_ASYNC_NOT_PENDING
     */
    @Test
    public void testResumeTaskShouldThrowNotPendingWhenStatusCompletedAndTypeNotChat() {
        TaskEntity entity = buildTaskEntity(TaskStatus.COMPLETED.getValue());
        entity.setType("workflow");
        when(asyncTaskMapper.getTaskEntity(any(), any(), any())).thenReturn(List.of(entity));

        AgentStudioException exception = assertThrows(AgentStudioException.class,
                () -> taskManagementService.resumeTask(PROJECT_ID, WORKFLOW_ID, TASK_ID, WORKSPACE_ID,
                        new ResumeTaskReq()));

        assertEquals(StudioError.WORKFLOW_ASYNC_NOT_PENDING, exception.getErrorCode());
    }

    /**
     * 用例描述：resumeTask 触发 checkStatus，status 为 COMPLETED 且 type 为 chat 时，
     * fromValue 正确匹配进入 COMPLETED/FAILED 分支但 type 放行，校验通过
     * 预制条件：asyncTaskMapper.getTaskEntity 返回 status=COMPLETED、type=chat 的任务实体
     * 输入参数：status=COMPLETED, type=chat
     * 预期结果：不抛异常，返回 TaskRsp.status 为 INIT
     */
    @Test
    public void testResumeTaskShouldPassStatusCheckWhenStatusCompletedAndTypeChat() {
        TaskEntity entity = buildTaskEntity(TaskStatus.COMPLETED.getValue());
        when(asyncTaskMapper.getTaskEntity(any(), any(), any())).thenReturn(List.of(entity));

        TaskRsp rsp = taskManagementService.resumeTask(PROJECT_ID, WORKFLOW_ID, TASK_ID, WORKSPACE_ID,
                new ResumeTaskReq());

        assertEquals(TaskStatus.INIT, rsp.getStatus());
    }

    /**
     * 用例描述：resumeTask 触发 checkStatus，status 为 null 或未匹配非法值时，fromValue 返回 null，
     * checkStatus 入口对 null 做保护直接返回（不抛 NPE），resumeTask 继续执行并将任务状态置为 INIT
     * 预制条件：asyncTaskMapper.getTaskEntity 返回 status=null / UNKNOWN 的任务实体
     * 输入参数：status=null / UNKNOWN
     * 预期结果：不抛任何异常，返回 TaskRsp.status 为 INIT
     */
    @Test
    public void testResumeTaskShouldNotThrowWhenStatusInvalidOrNull() {
        for (String statusValue : Arrays.asList(null, "UNKNOWN")) {
            TaskEntity entity = buildTaskEntity(statusValue);
            when(asyncTaskMapper.getTaskEntity(any(), any(), any())).thenReturn(List.of(entity));

            TaskRsp rsp = taskManagementService.resumeTask(PROJECT_ID, WORKFLOW_ID, TASK_ID, WORKSPACE_ID,
                    new ResumeTaskReq());
            assertEquals(TaskStatus.INIT, rsp.getStatus(),
                    "status [" + statusValue + "] 经 fromValue 转 null 后，checkStatus 应直接返回，resumeTask 不抛异常");
        }
    }

    /**
     * 用例描述：checkStatus 入口对 currentStatus 为 null 时直接返回，不进入 switch，不抛任何异常
     * 预制条件：无（checkStatus 为公开方法，直接调用）
     * 输入参数：currentStatus=null, workflowType=chat / null
     * 预期结果：方法正常返回，不抛异常（修复前 switch(null) 会抛 NPE）
     */
    @Test
    public void testCheckStatusShouldReturnEarlyWhenStatusNull() {
        assertDoesNotThrow(() -> taskManagementService.checkStatus(null, "chat"));
        assertDoesNotThrow(() -> taskManagementService.checkStatus(null, null));
    }

    /**
     * 用例描述：resumeTask 携带 inputs 与 timeout 时，checkStatus 通过后更新实体 inputs/timeout，
     * 覆盖 getLimitedTimeOut 非 null 分支
     * 预制条件：asyncTaskMapper.getTaskEntity 返回 status=PENDING 的任务实体
     * 输入参数：body.inputs={"query":"hello"}，body.timeout=5000
     * 预期结果：返回 TaskRsp.status 为 INIT、inputs 正确写入实体；updateByPrimaryKey 被调用且 timeout 被收敛为 1
     */
    @Test
    public void testResumeTaskShouldSetInputsAndTimeoutWhenBodyHasInputs() {
        TaskEntity entity = buildTaskEntity(TaskStatus.PENDING.getValue());
        when(asyncTaskMapper.getTaskEntity(any(), any(), any())).thenReturn(List.of(entity));

        Map<String, Object> inputs = new HashMap<>();
        inputs.put("query", "hello");
        TaskRsp rsp = taskManagementService.resumeTask(PROJECT_ID, WORKFLOW_ID, TASK_ID, WORKSPACE_ID,
                new ResumeTaskReq().setInputs(inputs).setTimeout(5000));

        assertEquals(TaskStatus.INIT, rsp.getStatus());
        assertEquals("hello", ((JSONObject) rsp.getInputs()).getString("query"));
        // 参数对象状态迁移：实体状态应被置为 INIT，inputs/timeout 同步更新
        assertEquals(TaskStatus.INIT.getValue(), entity.getStatus(), "resume 后实体状态应迁移为 INIT");
        assertEquals("{\"query\":\"hello\"}", entity.getInputs());
        verify(asyncTaskMapper).updateByPrimaryKey(entity);
        assertEquals(Integer.valueOf(1), entity.getTimeout());
    }

    /**
     * 用例描述：deleteTask 删除存在任务，返回 id 并调用 deleteByIds
     * 预制条件：asyncTaskMapper.getTaskEntity 返回包含 1 条任务实体的列表
     * 输入参数：projectId=project-1, workflowId=workflow-1, taskId=task-1, workspaceId=workspace-1
     * 预期结果：返回 CommonDeleteRsp.id=task-1，deleteByIds 以单元素列表被调用
     */
    @Test
    public void testDeleteTaskShouldDeleteByIdsWhenTaskFound() {
        TaskEntity entity = buildTaskEntity(TaskStatus.COMPLETED.getValue());
        when(asyncTaskMapper.getTaskEntity(any(), any(), any())).thenReturn(List.of(entity));

        CommonDeleteRsp rsp = taskManagementService.deleteTask(PROJECT_ID, WORKFLOW_ID, TASK_ID, WORKSPACE_ID);

        assertEquals(TASK_ID, rsp.getId());
        verify(asyncTaskMapper).deleteByIds(Collections.singletonList(TASK_ID));
    }

    /**
     * 用例描述：deleteTask 遇到 id 为空的任务实体时，跳过 deleteByIds，仅返回响应
     * 预制条件：asyncTaskMapper.getTaskEntity 返回 id=null 的任务实体
     * 输入参数：projectId=project-1, workflowId=workflow-1, taskId=task-1, workspaceId=workspace-1
     * 预期结果：返回 CommonDeleteRsp.id=task-1，deleteByIds 未被调用
     */
    @Test
    public void testDeleteTaskShouldNotDeleteWhenTaskIdBlank() {
        TaskEntity entity = buildTaskEntity(TaskStatus.COMPLETED.getValue());
        entity.setId(null);
        when(asyncTaskMapper.getTaskEntity(any(), any(), any())).thenReturn(List.of(entity));

        CommonDeleteRsp rsp = taskManagementService.deleteTask(PROJECT_ID, WORKFLOW_ID, TASK_ID, WORKSPACE_ID);

        assertEquals(TASK_ID, rsp.getId());
        verify(asyncTaskMapper, never()).deleteByIds(any());
    }

    /**
     * 用例描述：modifyTask 修改任务 name/timeout，调用 updateByPrimaryKey 后返回检索到的任务详情
     * 预制条件：asyncTaskMapper.getTaskEntity 返回 status=PENDING 的任务实体
     * 输入参数：body.name=new-name, body.timeout=1000
     * 预期结果：返回 TaskRsp，name 为新名称，updateByPrimaryKey 被调用
     */
    @Test
    public void testModifyTaskShouldUpdateAndReturnRetrievedTask() {
        RequestContextUtils.setRequestAuthTokenAndUserId("token", PROJECT_ID, "user-1");
        try {
            TaskEntity entity = buildTaskEntity(TaskStatus.PENDING.getValue());
            when(asyncTaskMapper.getTaskEntity(any(), any(), any())).thenReturn(List.of(entity));

            TaskRsp rsp = taskManagementService.modifyTask(PROJECT_ID, WORKFLOW_ID, TASK_ID, WORKSPACE_ID,
                    new ModifyTaskReq().setName("new-name").setTimeout(1000));

            // 返回值来自修改后重新查询的实体（mock 实体）
            assertEquals(TASK_ID, rsp.getId());
            assertEquals("test-task", rsp.getName());
            // 写入库中的实体应携带新的 name 与收敛后的 timeout
            ArgumentCaptor<TaskEntity> captor = ArgumentCaptor.forClass(TaskEntity.class);
            verify(asyncTaskMapper).updateByPrimaryKey(captor.capture());
            assertEquals("new-name", captor.getValue().getName());
            assertEquals(Integer.valueOf(1), captor.getValue().getTimeout());
        } finally {
            RequestContextUtils.remove();
        }
    }

    /**
     * 用例描述：createTask 创建任务，version 非空时直接使用 version，inputs 非空时状态为 INIT，
     * getNonSensitiveHeader 在无请求上下文时返回空 map
     * 预制条件：RequestContextUtils 已设置用户上下文；redis 与 mapper 为 mock
     * 输入参数：version=v2, body.inputs={"query":"hello"}, body.timeout=3000
     * 预期结果：返回 TaskRsp，status 为 INIT、isPublished 为 true、versionId=v2，
     *          createEntity 与 redisClient.set 被调用
     */
    @Test
    public void testCreateTaskShouldCreateEntityAndReturnRspWhenVersionProvided() {
        RequestContextUtils.setRequestAuthTokenAndUserId("token", PROJECT_ID, "user-1");
        try {
            Map<String, Object> inputs = new HashMap<>();
            inputs.put("query", "hello");
            CreateTaskReq body = new CreateTaskReq().setName("create-task").setType("chat")
                    .setMode("async").setInputs(inputs).setTimeout(3000);

            TaskRsp rsp = taskManagementService.createTask(PROJECT_ID, WORKFLOW_ID, "v2", WORKSPACE_ID, body);

            assertNotNull(rsp.getId());
            assertEquals("create-task", rsp.getName());
            assertEquals("chat", rsp.getWorkflow().getType());
            assertEquals("v2", rsp.getWorkflow().getVersionId());
            assertEquals(Boolean.TRUE, rsp.isIsPublished());
            assertEquals(TaskStatus.INIT, rsp.getStatus());
            verify(asyncTaskMapper).createEntity(any());
            verify(redisClient).set(any(), any(), any());
        } finally {
            RequestContextUtils.remove();
        }
    }

    /**
     * 用例描述：createTask 创建任务，version 为空但 body.version 非空时，
     * determineAppVersion 使用 body.version，inputs 为空时状态为 PENDING
     * 预制条件：RequestContextUtils 已设置用户上下文
     * 输入参数：version=null, body.version=100, body.inputs=null
     * 预期结果：返回 TaskRsp，status 为 PENDING、isPublished 为 false、versionId=100
     */
    @Test
    public void testCreateTaskShouldUseBodyVersionWhenVersionBlank() {
        RequestContextUtils.setRequestAuthTokenAndUserId("token", PROJECT_ID, "user-1");
        try {
            CreateTaskReq body = new CreateTaskReq().setName("create-task").setVersion(100L);

            TaskRsp rsp = taskManagementService.createTask(PROJECT_ID, WORKFLOW_ID, null, WORKSPACE_ID, body);

            assertEquals(TaskStatus.PENDING, rsp.getStatus());
            assertEquals(Boolean.FALSE, rsp.isIsPublished());
            assertEquals("100", rsp.getWorkflow().getVersionId());
        } finally {
            RequestContextUtils.remove();
        }
    }

    /**
     * 用例描述：createTask 创建任务，version 与 body.version 均为空时，
     * determineAppVersion 返回 null
     * 预制条件：RequestContextUtils 已设置用户上下文
     * 输入参数：version=null, body.version=null, body.inputs=null
     * 预期结果：返回 TaskRsp，status 为 PENDING、versionId 为 null
     */
    @Test
    public void testCreateTaskShouldReturnNullVersionWhenAllVersionBlank() {
        RequestContextUtils.setRequestAuthTokenAndUserId("token", PROJECT_ID, "user-1");
        try {
            CreateTaskReq body = new CreateTaskReq().setName("create-task");

            TaskRsp rsp = taskManagementService.createTask(PROJECT_ID, WORKFLOW_ID, null, WORKSPACE_ID, body);

            assertEquals(TaskStatus.PENDING, rsp.getStatus());
            assertNull(rsp.getWorkflow().getVersionId());
        } finally {
            RequestContextUtils.remove();
        }
    }

    /**
     * 用例描述：createTask 创建任务，存在 Servlet 请求上下文时，
     * getNonSensitiveHeader 遍历请求头写入 redis
     * 预制条件：RequestContextHolder 设置了 MockHttpServletRequest（含 X-Custom 头）
     * 输入参数：version=v3, body.inputs=null
     * 预期结果：返回 TaskRsp 且 id 非空，redisClient.set 被调用
     */
    @Test
    public void testCreateTaskShouldCollectHeadersWhenRequestPresent() {
        RequestContextUtils.setRequestAuthTokenAndUserId("token", PROJECT_ID, "user-1");
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader("X-Custom", "header-value");
        RequestContextHolder.setRequestAttributes(new ServletRequestAttributes(request));
        try {
            CreateTaskReq body = new CreateTaskReq().setName("create-task");

            TaskRsp rsp = taskManagementService.createTask(PROJECT_ID, WORKFLOW_ID, "v3", WORKSPACE_ID, body);

            assertNotNull(rsp.getId());
            verify(redisClient).set(any(), any(), any());
        } finally {
            RequestContextHolder.resetRequestAttributes();
            RequestContextUtils.remove();
        }
    }
}
