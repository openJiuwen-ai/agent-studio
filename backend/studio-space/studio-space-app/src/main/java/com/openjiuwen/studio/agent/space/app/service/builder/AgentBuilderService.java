/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.space.app.service.builder;

import com.alibaba.fastjson2.JSON;
import com.alibaba.ttl.threadpool.TtlExecutors;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.openjiuwen.studio.agent.space.api.vo.AgentType;
import com.openjiuwen.studio.agent.space.api.vo.AgentBuilderFileExtConfigVo;
import com.openjiuwen.studio.agent.space.api.vo.AgentBuilderTaskDisplayVo;
import com.openjiuwen.studio.agent.space.api.vo.AgentBuilderTaskInfoVo;
import com.openjiuwen.studio.agent.space.api.vo.request.AgentStudioQueryReq;
import com.openjiuwen.studio.agent.space.api.vo.request.PageInfo;
import com.openjiuwen.studio.agent.space.api.vo.request.PublishAgentRequest;
import com.openjiuwen.studio.agent.space.api.vo.request.AgentBuilderChatReq;
import com.openjiuwen.studio.agent.space.api.vo.request.AgentBuilderCreateTaskReq;
import com.openjiuwen.studio.agent.space.api.vo.request.AgentBuilderDeleteMessageReq;
import com.openjiuwen.studio.agent.space.api.vo.request.AgentBuilderMessageListReq;
import com.openjiuwen.studio.agent.space.api.vo.request.AgentBuilderOperateTaskReq;
import com.openjiuwen.studio.agent.space.api.vo.request.AgentBuilderQueryTaskReq;
import com.openjiuwen.studio.agent.space.api.vo.request.AgentBuilderUpdateTaskReq;
import com.openjiuwen.studio.agent.space.api.vo.response.AgentApplicationInfo;
import com.openjiuwen.studio.agent.space.api.vo.response.AgentListResp;
import com.openjiuwen.studio.agent.space.api.vo.response.QueryAgentApplicationListRsp;
import com.openjiuwen.studio.agent.space.api.vo.response.AgentBuilderTaskListRsp;
import com.openjiuwen.studio.agent.space.api.vo.response.WorkspaceInfoResp;
import com.openjiuwen.studio.agent.space.api.vo.response.deepresearch.ChunkResp;
import com.openjiuwen.studio.agent.space.api.vo.response.deepresearch.DRMessageVo;
import com.openjiuwen.studio.agent.space.api.vo.response.deepresearch.Latency;
import com.openjiuwen.studio.agent.space.api.vo.response.file.MsgFileInfo;
import com.openjiuwen.studio.agent.space.app.config.AgentBuilderConfiguration;
import com.openjiuwen.studio.agent.space.app.constant.Constant;
import com.openjiuwen.studio.agent.space.app.constant.RedisKeyConstant;
import com.openjiuwen.studio.agent.space.app.enums.DRTaskStatusType;
import com.openjiuwen.studio.agent.space.app.enums.AgentBuilderDataType;
import com.openjiuwen.studio.agent.space.app.enums.AgentBuilderStorageType;
import com.openjiuwen.studio.agent.space.app.enums.AgentBuilderFileType;
import com.openjiuwen.studio.agent.space.app.enums.AgentBuilderUploadScene;
import com.openjiuwen.studio.agent.space.app.enums.AgentBuilderMsgType;
import com.openjiuwen.studio.agent.space.app.enums.AgentBuilderTaskOperationType;
import com.openjiuwen.studio.agent.space.app.service.client.AgentManagerService;
import com.openjiuwen.studio.agent.space.app.task.DRTaskHandler;
import com.openjiuwen.studio.agent.space.app.util.AppCommonUtils;
import com.openjiuwen.studio.agent.space.app.util.FileTransferUtils;
import com.openjiuwen.studio.agent.space.app.util.AgentBuilderTransformUtil;
import com.openjiuwen.studio.agent.space.common.context.AuthorizationContextHolder;
import com.openjiuwen.studio.agent.space.common.exception.AgentSpaceErrorCodes;
import com.openjiuwen.studio.agent.space.common.exception.AgentSpaceException;
import com.openjiuwen.studio.agent.space.common.utils.CollectionUtil;
import com.openjiuwen.studio.agent.space.common.utils.StringUtil;
import com.openjiuwen.studio.agent.space.common.utils.redis.RedisClient;
import com.openjiuwen.studio.agent.space.common.utils.redis.RedisLock;
import com.openjiuwen.studio.agent.space.dao.application.AgentMapper;
import com.openjiuwen.studio.agent.space.dao.application.AgentBuilderActionMapper;
import com.openjiuwen.studio.agent.space.dao.application.AgentBuilderFileMapper;
import com.openjiuwen.studio.agent.space.dao.application.AgentBuilderMessageMapper;
import com.openjiuwen.studio.agent.space.dao.application.AgentBuilderStepMapper;
import com.openjiuwen.studio.agent.space.dao.application.AgentBuilderTaskMapper;
import com.openjiuwen.studio.agent.space.dao.entity.Agent;
import com.openjiuwen.studio.agent.space.dao.entity.AgentBuilderActionEntity;
import com.openjiuwen.studio.agent.space.dao.entity.AgentBuilderFileEntity;
import com.openjiuwen.studio.agent.space.dao.entity.AgentBuilderMessageEntity;
import com.openjiuwen.studio.agent.space.dao.entity.AgentBuilderStepEntity;
import com.openjiuwen.studio.agent.space.dao.entity.AgentBuilderTaskEntity;

import jakarta.annotation.Resource;
import jakarta.validation.constraints.NotNull;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.InputStreamResource;
import org.springframework.http.ResponseEntity;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.File;
import java.sql.Timestamp;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.Executor;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

@Slf4j
@Service
public class AgentBuilderService {
    public static final String TASK_LOCK_KEY_TEMPLATE = "CREAT_TASK_%s_%s";

    @Value("${agent.space.chat.bucketName:agentBuilder}")
    private String normalAgentBucketName;

    @Value("${agent.space.memory.messageSize:10000}")
    private int memoriesMsgSize;

    @Value("${agent.space.memory.fileSize:10}")
    private int memoriesFileSize;

    @Value("${agent.space.downloadurl.expires:7}")
    private long downloadUrlExpires;

    /**
     * AgentStudio快速访问地址
     */
    @Value("${agent.space.request.url:}")
    private String requestUrl;

    @Resource
    private AgentBuilderTaskMapper taskMapper;

    @Resource
    private AgentBuilderMessageMapper messageMapper;

    @Resource
    private AgentBuilderStepMapper stepMapper;

    @Resource
    private AgentBuilderActionMapper actionMapper;

    @Resource
    private AgentBuilderFileMapper fileMapper;

    @Resource
    private RedisClient redisClient;

    @Resource
    private AgentBuilderHelperService AgentBuilderHelperService;

    @Resource
    private AgentBuilderTransformUtil transformUtil;

    @Resource
    private AgentManagerService agentManagerService;

    @Resource
    private AgentBuilderConfiguration AgentBuilderConfiguration;

    @Resource
    private FileTransferUtils fileTransferUtil;

    @Value("${agent.builder.task.pinTaskLimit:15}")
    private int pinTaskLimit;

    @Resource
    private ThreadPoolTaskExecutor taskExecutor;

    @Resource
    private AgentMapper agentMapper;

    @Resource
    private DRTaskHandler drTaskHandler;

    /**
     * 创建AgentBudiler任务
     *
     * @param req 请求，包含任务类型、模式等内容
     * @return 任务id
     */
    @Transactional
    public String createTask(AgentBuilderCreateTaskReq req) {
        AppCommonUtils.validateDomainIdUserIdIsNotEmpty();
        String lockKey = TASK_LOCK_KEY_TEMPLATE.formatted(AuthorizationContextHolder.domainId(),
            AuthorizationContextHolder.userId());
        RedisLock lock = redisClient.getLock(lockKey);
        try {
            if (lock.tryLock(Duration.ofSeconds(10))) {
                AgentBuilderHelperService.checkConcurrencyOfUser();
                AgentBuilderHelperService.checkConcurrencyOfTotal();
                AgentBuilderTaskEntity task = transformUtil.createTask2TaskEntity(req);
                taskMapper.insert(task);
                redisClient.set(String.format(RedisKeyConstant.DR_STATUS, task.getId()),
                    String.valueOf(DRTaskStatusType.INITIATING.getStatus()),
                    Duration.ofSeconds(Constant.REDIS_EXPIRE_TIME));
                return task.getId();
            } else {
                log.error("[createTask] validate task fail, too frequent operation, tenantId:{}",
                    AuthorizationContextHolder.domainId());
                throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_SERVICE_INTERNAL_ERROR,
                    "too frequent operation");
            }
        } catch (InterruptedException e) {
            log.error("[createTask] interrupted while acquiring lock, tenantId:{}",
                AuthorizationContextHolder.domainId());
            Thread.currentThread().interrupt();
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_SERVICE_INTERNAL_ERROR,
                "interrupted while acquiring lock");
        } catch (Exception e) {
            log.error("[createTask] create task fail, tenantId: {}, error is: {}",
                AuthorizationContextHolder.domainId(), e.getMessage() + e.getCause());
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_SERVICE_INTERNAL_ERROR, "create task fail");
        } finally {
            if (lock != null) {
                try {
                    lock.unlock();
                    log.debug("Released lock: {}", lockKey);
                } catch (Exception e) {
                    log.warn("Failed to release distributed lock: {}", lockKey, e);
                }
            }
        }
    }

    private AgentBuilderTaskListRsp buildAgentBuilderTaskListRsp(AgentBuilderQueryTaskReq req, Page<AgentBuilderTaskEntity> infos) {
        AgentBuilderTaskListRsp rsp = new AgentBuilderTaskListRsp();
        rsp.setNum(req.getNum());
        rsp.setSize(req.getSize());
        rsp.setTotal(infos.getTotal())
            .setTaskList(
                infos.getRecords().stream().map(transformUtil::taskEntity2TaskInfoVo).collect(Collectors.toList()));
        return rsp;
    }

    /**
     * 获取任务详细信息
     *
     * @param taskId 任务id
     * @return 任务详情
     */
    public AgentBuilderTaskInfoVo detailTask(String taskId) {
        AppCommonUtils.validateDomainIdUserIdIsNotEmpty();
        // 校验
        AgentBuilderTaskEntity task = taskMapper.getTaskByIdAndTenantAndUser(taskId, AuthorizationContextHolder.domainId(),
            AuthorizationContextHolder.userId());
        if (ObjectUtils.isEmpty(task)) {
            log.error("[detailTask] validate task fail, task not exist, taskId:{}", taskId);
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_PARAM_INCORRECT_ERROR, "task is not exist");
        }
        return transformUtil.taskEntity2TaskInfoVo(task);
    }

    /**
     * 任务重命名
     *
     * @param req 请求
     * @return 任务详情
     */
    public String renameTask(AgentBuilderUpdateTaskReq req) {
        AppCommonUtils.validateDomainIdUserIdIsNotEmpty();
        // 校验
        AgentBuilderTaskEntity task = taskMapper.getTaskByIdAndTenantAndUser(req.getTaskId(),
            AuthorizationContextHolder.domainId(), AuthorizationContextHolder.userId());
        if (ObjectUtils.isEmpty(task)) {
            log.error("[renameTask] validate task fail, task not exist, taskId:{}", req.getTaskId());
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_PARAM_INCORRECT_ERROR, "task is not exist");
        }

        AgentBuilderTaskEntity newTask = new AgentBuilderTaskEntity();
        newTask.setId(req.getTaskId());
        newTask.setName(req.getName());
        AppCommonUtils.setCommonUpdateProperties(newTask);
        taskMapper.updateTaskNameById(newTask);

        return "success";
    }

    /**
     * 任务简单操作
     *
     * @param req 任务操作类型
     * @return 操作结果
     */
    public String operateTask(AgentBuilderOperateTaskReq req) {
        AppCommonUtils.validateDomainIdUserIdIsNotEmpty();
        // 校验
        AgentBuilderTaskEntity task = taskMapper.getTaskByIdAndTenantAndUser(req.getTaskId(),
            AuthorizationContextHolder.domainId(), AuthorizationContextHolder.userId());
        if (ObjectUtils.isEmpty(task)) {
            log.error("[operateTask] validate task fail, task not exist, taskId:{}", req.getTaskId());
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_PARAM_INCORRECT_ERROR, "task is not exist");
        }
        if (task.getAgentType() != AgentType.DEEP_RESEARCH.getCode()) {
            log.error("[operateTask] validate task fail, no dr task, taskId:{}", req.getTaskId());
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_DATA_STATUS_INOPERABLE);
        }
        log.info("[operateTask] validate task success.");
        AgentBuilderTaskOperationType operate = AgentBuilderTaskOperationType.getByType(req.getOperateType());
        switch (operate) {
            case DELETE:
                // 删除任务
                operateTask2Delete(task);
                break;
            case PIN:
                // 置顶任务
                operateTask2Pin(task, true);
                break;
            case CANCEL_PIN:
                // 取消置顶任务
                operateTask2Pin(task, false);
                break;
            case RATE:
                // 打分
                operateTask2Rate(req);
                break;
            case STOP:
                // 手动停止
                operateTask2Stop(req, task);
                break;
        }
        return "success";
    }

    /**
     * 获取任务列表
     *
     * @param req 分页
     * @return 包含分页信息的任务信息列表
     */
    public AgentBuilderTaskListRsp listTask(AgentBuilderQueryTaskReq req) {
        AppCommonUtils.validateDomainIdUserIdIsNotEmpty();
        // 拼接查询条件，按是否置顶、创建时间排序
        LambdaQueryWrapper<AgentBuilderTaskEntity> queryWrapper = new LambdaQueryWrapper<>();
        if (StringUtil.isNotEmptyString(req.getSearchKey())) {
            queryWrapper.like(AgentBuilderTaskEntity::getName, req.getSearchKey());
        }
        if (StringUtil.isNotEmptyString(req.getAgentId())) {
            queryWrapper.like(AgentBuilderTaskEntity::getAgentId, req.getAgentId());
        }
        queryWrapper.eq(AgentBuilderTaskEntity::getRunType, req.getRunType())
            .eq(AgentBuilderTaskEntity::getDeleted, false)
            .eq(AgentBuilderTaskEntity::getDomainId, AuthorizationContextHolder.domainId())
            .eq(AgentBuilderTaskEntity::getCreatedByUserId, AuthorizationContextHolder.userId())
            .last("ORDER BY JSON_EXTRACT(display_info, '$.is_pin') DESC, created_date DESC");

        Page<AgentBuilderTaskEntity> infos = new Page<>(req.getNum(), req.getSize());
        // 查询
        infos = taskMapper.selectPage(infos, queryWrapper);
        return buildAgentBuilderTaskListRsp(req, infos);
    }

    private void operateTask2Rate(AgentBuilderOperateTaskReq req) {
        // 只有系统答复才能打分
        AgentBuilderMessageEntity msg = messageMapper.getSystemMsgByIdAndTaskId(req.getMsgId(), req.getTaskId());
        if (ObjectUtils.isEmpty(msg) || msg.getType() != AgentBuilderMsgType.SYSTEM.getType()) {
            log.error("[operateTask] validate msg fail, msg not exist, taskId:{}, msgId: {}", req.getTaskId(),
                req.getMsgId());
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_PARAM_INCORRECT_ERROR, "message is not exist");
        }
        AppCommonUtils.setCommonUpdateProperties(msg);
        LambdaUpdateWrapper<AgentBuilderMessageEntity> msgUpdateWrapper
            = new LambdaUpdateWrapper<AgentBuilderMessageEntity>().set(AgentBuilderMessageEntity::getRating, req.getRating())
            .set(AgentBuilderMessageEntity::getLastUpdatedDate, msg.getLastUpdatedDate())
            .set(AgentBuilderMessageEntity::getLastUpdatedByUserId, msg.getLastUpdatedByUserId())
            .eq(AgentBuilderMessageEntity::getId, msg.getId());
        messageMapper.update(msgUpdateWrapper);
    }

    private void operateTask2Pin(AgentBuilderTaskEntity task, boolean pin) {
        if (pin) {
            log.info("pin task {}.", task.getId());
        } else {
            log.info("cancel pin task {}.", task.getId());
        }

        // 查询已置顶任务数
        if (pin) {
            LambdaQueryWrapper<AgentBuilderTaskEntity> userTasksWrapper = new LambdaQueryWrapper<AgentBuilderTaskEntity>().eq(
                    AgentBuilderTaskEntity::getDomainId, AuthorizationContextHolder.domainId())
                .eq(AgentBuilderTaskEntity::getCreatedByUserId, AuthorizationContextHolder.userId())
                .eq(AgentBuilderTaskEntity::getDeleted, false)
                .like(AgentBuilderTaskEntity::getDisplayInfo, "\"is_pin\":true");
            List<AgentBuilderTaskEntity> userTasks = taskMapper.selectList(userTasksWrapper);
            if (CollectionUtils.isNotEmpty(userTasks) && userTasks.size() >= pinTaskLimit) {
                log.error("[operateTask] validate task fail, task pin limit, taskId:{}, current limit is: {}",
                    task.getId(), pinTaskLimit);
                throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_TASK_PIN_LIMIT_ERROR, pinTaskLimit);
            }
        }

        AgentBuilderTaskDisplayVo displayInfo = JSON.parseObject(task.getDisplayInfo(), AgentBuilderTaskDisplayVo.class);
        displayInfo.setPin(pin);
        AppCommonUtils.setCommonUpdateProperties(task);
        LambdaUpdateWrapper<AgentBuilderTaskEntity> taskUpdateWrapper = new LambdaUpdateWrapper<AgentBuilderTaskEntity>().set(
                AgentBuilderTaskEntity::getDisplayInfo, JSON.toJSONString(displayInfo))
            .set(AgentBuilderTaskEntity::getLastUpdatedDate, task.getLastUpdatedDate())
            .set(AgentBuilderTaskEntity::getLastUpdatedByUserId, task.getLastUpdatedByUserId())
            .eq(AgentBuilderTaskEntity::getId, task.getId());
        taskMapper.update(taskUpdateWrapper);
    }

    private void operateTask2Stop(AgentBuilderOperateTaskReq req, AgentBuilderTaskEntity task) {
        if (!DRTaskStatusType.canStop(DRTaskStatusType.getByStatus(task.getStatus()))) {
            log.error("[operateTask] validate task fail, task cannot stop, taskId:{}, status:{}", req.getTaskId(),
                task.getStatus());
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_TASK_CANNOT_STOP_ERROR, task.getId(),
                task.getStatus());
        }
        drTaskHandler.updateTaskStatus(task.getId(), DRTaskStatusType.STOP.getStatus());
        log.info("stop task {}.", task.getId());
    }

    private void operateTask2Delete(AgentBuilderTaskEntity task) {
        log.info("delete task {} type {}.", task.getId(), task.getAgentType());
        AppCommonUtils.setCommonUpdateProperties(task);
        if (!DRTaskStatusType.isCompleted(DRTaskStatusType.getByStatus(task.getStatus()))) {
            drTaskHandler.updateTaskStatusWithDelete(task.getId(), DRTaskStatusType.DELETED.getStatus());
        } else {
            drTaskHandler.updateTaskStatusWithDelete(task.getId(), task.getStatus());
        }

        // 异步处理文件，如果删除失败,定时任务补偿
        Executor executor = TtlExecutors.getTtlExecutor(taskExecutor);
        executor.execute(() -> {
            // 需删除任务对应的文件，更新文件表中文件的状态
            List<AgentBuilderFileEntity> files = fileMapper.selectFilesByTaskId(task.getId());
            if (CollectionUtils.isNotEmpty(files)) {
                int res = fileMapper.softDeleteFiles(files.stream().map(AgentBuilderFileEntity::getId).toList(),
                    task.getId());
                log.info("soft delete {} files", res);
                files.forEach(file -> {
                    if (file.getStorageType() == AgentBuilderStorageType.OBS.getType()) {
                        fileTransferUtil.safeDeleteObsObject(file.getUri());
                    }
                });
            }
            log.info("delete file completed.");
        });
    }

    /**
     * 复杂任务规划对话
     *
     * @param req 任务
     * @return 执行结果
     */
    public SseEmitter chat(String workspaceId, AgentBuilderChatReq req) {
        AppCommonUtils.validateDomainIdUserIdIsNotEmpty();

        // 校验任务是否存在
        AgentBuilderTaskEntity task = taskMapper.getTaskByIdAndTenantAndUser(req.getTaskId(),
            AuthorizationContextHolder.domainId(), AuthorizationContextHolder.userId());
        if (ObjectUtils.isEmpty(task)) {
            log.error("[chat] validate task fail, task not exist, taskId:{}", req.getTaskId());
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_PARAM_INCORRECT_ERROR, "task is not exist");
        }
        if (task.getAgentType() != AgentType.DEEP_RESEARCH.getCode()) {
            log.error("[chat] validate task fail, no dr task, taskId:{}", req.getTaskId());
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_DATA_STATUS_INOPERABLE);
        }

        String status = redisClient.get(String.format(RedisKeyConstant.DR_STATUS, req.getTaskId()));
        if (!DRTaskStatusType.canChat(DRTaskStatusType.getByStatus(task.getStatus())) || (status != null
            && !DRTaskStatusType.canChat(DRTaskStatusType.getByStatus(Integer.parseInt(status))))) {
            log.error("[chat] validate task fail, task is not in the input status, taskId:{} redis status:{}",
                req.getTaskId(), status);
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_TASK_STATUS_INCORRECT);
        }
        log.info("[chatExecute] validate task success.");

        if (!DRTaskStatusType.isRunning(DRTaskStatusType.getByStatus(task.getStatus()))) {
            log.info("[chatExecute] start executing task {} .", task.getId());
            boolean chatSuccess = AgentBuilderHelperService.saveAndExecuteChat(req, task, workspaceId);
            if (!chatSuccess) {
                throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_SERVICE_INTERNAL_ERROR, "agent run error");
            }
        }

        return AgentBuilderHelperService.getSseEmitter(req);
    }

    /**
     * 获取已归档的历史消息
     * 任务完成时，返回所有消息
     * 任务未完成，最多返回确认阶段的消息；其他的消息在Redis中获取
     *
     * @param req 消息列表所属任务
     * @return 消息列表
     */
    public List<DRMessageVo> listMessage(AgentBuilderMessageListReq req) {
        AppCommonUtils.validateDomainIdUserIdIsNotEmpty();
        String taskId = req.getTaskId();
        AgentBuilderTaskEntity task = getTaskByUser(taskId);

        List<AgentBuilderMessageEntity> messageList = messageMapper.selectList(
            new LambdaQueryWrapper<AgentBuilderMessageEntity>().eq(AgentBuilderMessageEntity::getTaskId, taskId)
                .eq(AgentBuilderMessageEntity::getDeleted, false)
                .orderBy(true, true, AgentBuilderMessageEntity::getCreatedDate));

        List<AgentBuilderMessageEntity> processedMessages = processMessagesBasedOnStatus(messageList, task);

        return buildFinalMessageVoList(processedMessages, req.getTaskId());
    }

    /**
     * 校验消息查询参数
     */
    private @NotNull AgentBuilderTaskEntity getTaskByUser(String taskId) {
        AgentBuilderTaskEntity task = taskMapper.getTaskByIdAndTenantAndUser(taskId, AuthorizationContextHolder.domainId(),
            AuthorizationContextHolder.userId());
        if (ObjectUtils.isEmpty(task)) {
            log.error("[validateMessageQueryParams] validate task fail, task not exist, taskId:{}", taskId);
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_PARAM_INCORRECT_ERROR, "task is not exist");
        }
        log.info("[listMessage] validate task success.");
        return task;
    }

    /**
     * 根据任务状态处理消息
     */
    private List<AgentBuilderMessageEntity> processMessagesBasedOnStatus(List<AgentBuilderMessageEntity> messageList,
        AgentBuilderTaskEntity task) {
        if (ObjectUtils.isEmpty(messageList) || messageList.isEmpty()) {
            return Collections.emptyList();
        }
        List<AgentBuilderMessageEntity> filterMessages = new ArrayList<>();
        if (task.getStatus() < DRTaskStatusType.WAITING_USER_INPUT.getStatus()) {
            filterMessages.add(messageList.get(0));
            return filterMessages;
        } else if (task.getStatus() == DRTaskStatusType.WAITING_USER_INPUT.getStatus()) {
            filterMessages.add(messageList.get(0));
            if (messageList.size() > 1) {
                filterMessages.add(messageList.get(1));
            }
            return filterMessages;
        } else if (task.getStatus() == DRTaskStatusType.PLAN_RUNNING.getStatus()) {
            filterMessages.add(messageList.get(0));
            if (messageList.size() > 1) {
                filterMessages.add(messageList.get(1));
            }
            if (messageList.size() > 2) {
                filterMessages.add(messageList.get(2));
            }
            return filterMessages;
        } else {
            return messageList;
        }
    }

    /**
     * 构建最终的消息VO列表
     */
    private List<DRMessageVo> buildFinalMessageVoList(List<AgentBuilderMessageEntity> messageList, String taskId) {
        if (ObjectUtils.isEmpty(messageList)) {
            return Collections.emptyList();
        }

        // 1. 查询相关文件信息
        List<AgentBuilderFileEntity> fileEntities = fileMapper.selectFilesByTaskId(taskId);
        Map<String, List<MsgFileInfo>> msgFileInfoMap = getMsgFileInfoMap(fileEntities);

        // 2. 查询相关步骤和动作信息
        Map<String, List<AgentBuilderStepEntity>> stepMap = buildStepMap(messageList);
        Map<String, List<AgentBuilderActionEntity>> actionMap = buildActionMap(stepMap);

        // 3. 构建消息VO列表
        return buildMessageVoList(messageList, stepMap, actionMap, msgFileInfoMap);
    }

    private Map<String, List<MsgFileInfo>> getMsgFileInfoMap(List<AgentBuilderFileEntity> fileEntities) {
        if (CollectionUtil.isEmpty(fileEntities)) {
            return new HashMap<>();
        }

        List<MsgFileInfo> msgFileInfos = fileEntities.stream()
            .map(fileEntity -> MsgFileInfo.builder()
                .msgId(fileEntity.getMessageId())
                .taskId(fileEntity.getTaskId())
                .fileName(fileEntity.getName())
                .fileId(fileEntity.getId())
                .downloadUrl(fileTransferUtil.getDownloadUrlFromObs(normalAgentBucketName, fileEntity.getUri(),
                    downloadUrlExpires))
                .source(String.valueOf(fileEntity.getType()))
                .sourceId(fileEntity.getSourceId())
                .extConfig(JSON.parseObject(fileEntity.getExtraConfig(), AgentBuilderFileExtConfigVo.class))
                .build())
            .toList();
        if (CollectionUtils.isEmpty(msgFileInfos)) {
            return new HashMap<>();
        }
        return msgFileInfos.stream()
            .filter(msgFileInfo -> StringUtil.isNotEmptyString(msgFileInfo.getMsgId()))
            .collect(Collectors.groupingBy(MsgFileInfo::getMsgId));
    }

    /**
     * 构建步骤映射
     */
    private Map<String, List<AgentBuilderStepEntity>> buildStepMap(List<AgentBuilderMessageEntity> messageList) {
        List<String> messageIds = messageList.stream().map(AgentBuilderMessageEntity::getId).collect(Collectors.toList());

        List<AgentBuilderStepEntity> stepList = stepMapper.selectList(
            new LambdaQueryWrapper<AgentBuilderStepEntity>().in(AgentBuilderStepEntity::getMessageId, messageIds)
                .eq(AgentBuilderStepEntity::getDeleted, false)
                .orderBy(true, true, AgentBuilderStepEntity::getCreatedDate));

        return stepList.stream().collect(Collectors.groupingBy(AgentBuilderStepEntity::getMessageId));
    }

    /**
     * 构建动作映射
     */
    private Map<String, List<AgentBuilderActionEntity>> buildActionMap(Map<String, List<AgentBuilderStepEntity>> stepMap) {
        List<String> stepIds = stepMap.values()
            .stream()
            .flatMap(List::stream)
            .map(AgentBuilderStepEntity::getId)
            .collect(Collectors.toList());

        if (CollectionUtils.isEmpty(stepIds)) {
            return Collections.emptyMap();
        }

        List<AgentBuilderActionEntity> actionList = actionMapper.selectList(
            new LambdaQueryWrapper<AgentBuilderActionEntity>().in(AgentBuilderActionEntity::getStepId, stepIds)
                .eq(AgentBuilderActionEntity::getDeleted, false)
                .notIn(AgentBuilderActionEntity::getToolType, "log")
                .orderBy(true, true, AgentBuilderActionEntity::getCreatedDate));

        return actionList.stream().collect(Collectors.groupingBy(AgentBuilderActionEntity::getStepId));
    }

    /**
     * 构建消息VO列表
     */
    private List<DRMessageVo> buildMessageVoList(List<AgentBuilderMessageEntity> messageList,
        Map<String, List<AgentBuilderStepEntity>> stepMap, Map<String, List<AgentBuilderActionEntity>> actionMap,
        Map<String, List<MsgFileInfo>> msgFileInfoMap) {
        List<DRMessageVo> messageVoList = new ArrayList<>();
        for (AgentBuilderMessageEntity message : messageList) {
            List<ChunkResp> chunkRespList = buildChunkRespList(message, stepMap, actionMap);

            messageVoList.add(new DRMessageVo().setId(message.getId())
                .setParentId(message.getParentId())
                .setTaskId(message.getTaskId())
                .setType(message.getType())
                .setChunks(chunkRespList)
                .setContent(message.getContent())
                .setRating(message.getRating())
                .setCreateTime(message.getCreatedDate().getTime())
                .setMsgFileInfos(msgFileInfoMap.getOrDefault(message.getId(), Collections.emptyList())));
        }

        return messageVoList;
    }

    /**
     * 为单个消息构建块响应列表
     */
    private List<ChunkResp> buildChunkRespList(AgentBuilderMessageEntity message,
        Map<String, List<AgentBuilderStepEntity>> stepMap, Map<String, List<AgentBuilderActionEntity>> actionMap) {
        List<ChunkResp> chunkRespList = new ArrayList<>();
        AtomicLong endTime = new AtomicLong();
        if (stepMap.containsKey(message.getId())) {
            List<AgentBuilderStepEntity> steps = stepMap.get(message.getId());
            for (AgentBuilderStepEntity step : steps) {
                if (actionMap.containsKey(step.getId())) {
                    actionMap.get(step.getId()).forEach(action -> {
                        endTime.set(Math.max(endTime.get(), action.getCreatedDate().getTime()));
                        chunkRespList.add(JSON.parseObject(action.getContent(), ChunkResp.class)
                            .setCreatedTime(action.getCreatedDate()));
                    });
                }
            }
        }
        if (!chunkRespList.isEmpty()) {
            double runTime = (endTime.get() - message.getCreatedDate().getTime()) / 1000.0;
            chunkRespList.add(new ChunkResp().setCreatedTime(new Timestamp(endTime.get()))
                .setEvent("statistic_data")
                .setLatency(new Latency().setOverall(Math.round(runTime * 100.0) / 100.0)));
        }
        return chunkRespList;
    }

    /**
     * 删除消息历史
     *
     * @param req 请求
     */
    public String deleteMessage(AgentBuilderDeleteMessageReq req) {
        AppCommonUtils.validateDomainIdUserIdIsNotEmpty();
        // 参数校验
        AgentBuilderTaskEntity task = taskMapper.getTaskByIdAndTenantAndUser(req.getTaskId(),
            AuthorizationContextHolder.domainId(), AuthorizationContextHolder.userId());
        if (ObjectUtils.isEmpty(task)) {
            log.error("[deleteMessage] validate task fail, task not exist, taskId:{}", req.getTaskId());
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_PARAM_INCORRECT_ERROR, "task is not exist");
        }

        // 校验消息Id是否是Agent返回的消息
        AgentBuilderMessageEntity answerMsg = messageMapper.getSystemMsgByIdAndTaskId(req.getMessageId(), req.getTaskId());
        if (ObjectUtils.isEmpty(answerMsg) || answerMsg.getType() != AgentBuilderMsgType.SYSTEM.getType()) {
            log.error("[deleteMessage] validate msg fail, msg not exist, taskId:{}, msgId: {}", req.getTaskId(),
                req.getMessageId());
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_PARAM_INCORRECT_ERROR, "message is not exist");
        }

        List<String> needDeleteMsg = new ArrayList<>();
        needDeleteMsg.add(req.getMessageId());

        // answer的前一条消息
        AgentBuilderMessageEntity beforeMsgEntity = messageMapper.getBeforeMsgByAnswerId(answerMsg.getId(),
            req.getTaskId());

        // 获取提问的消息id
        String queryMsgId = StringUtils.isNotBlank(answerMsg.getParentId())
            ? answerMsg.getParentId()
            : (beforeMsgEntity != null && beforeMsgEntity.getType() == AgentBuilderMsgType.USER.getType()
                ? beforeMsgEntity.getId()
                : StringUtil.EMPTY_STRING);

        // 判断query是否有其他的answer，为了兼容老数据，需要判断前一条消息是否也是answer
        if (messageMapper.getAnswerMsgByQueryIdAndTaskId(queryMsgId, req.getTaskId()).size() <= 1
            && beforeMsgEntity != null && beforeMsgEntity.getType() == AgentBuilderMsgType.USER.getType()) {
            needDeleteMsg.add(queryMsgId);
        }

        // 软删除,如果query没有其他的answer,需连带问题一起删除,更新表中记录
        needDeleteMsg.forEach(msgId -> {
            LambdaUpdateWrapper<AgentBuilderMessageEntity> msgUpdateWrapper
                = new LambdaUpdateWrapper<AgentBuilderMessageEntity>().set(AgentBuilderMessageEntity::getDeleted, true)
                .set(AgentBuilderMessageEntity::getLastUpdatedByUserId, AuthorizationContextHolder.userId())
                .set(AgentBuilderMessageEntity::getLastUpdatedDate, new Timestamp(new Date().getTime()))
                .eq(AgentBuilderMessageEntity::getId, msgId);
            messageMapper.update(msgUpdateWrapper);
        });

        return "success";
    }

    public String uploadFile(MultipartFile file, AgentBuilderFileExtConfigVo extConfigVo) {
        AppCommonUtils.validateDomainIdUserIdIsNotEmpty();
        String extension = StringUtils.substringAfterLast(file.getOriginalFilename(), '.');
        if (extension == null) {
            log.error("[uploadFile] invalid file name {} ", file.getOriginalFilename());
            throw new AgentSpaceException(AgentSpaceErrorCodes.FILE_NAME_INVALID);
        }
        AgentBuilderFileType agentBuilderFileType = AgentBuilderFileType.toAgentBuilderFileType(extension.toLowerCase(Locale.ROOT));
        if (agentBuilderFileType == null) {
            log.error("[uploadFile] invalid file type {} ", file.getOriginalFilename());
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_FILE_NOT_SUPPORT_ERROR);
        }
        for (AgentBuilderDataType dataType : agentBuilderFileType.getBelongDataTypes()) {
            validateFile(file, dataType);
        }
        FileTransferUtils.FileTransferResult fileTransferResult = fileTransferUtil.uploadTaskFile(
            fileTransferUtil.multipartFile2AgentBuilderFile(file), AgentBuilderUploadScene.USER_UPLOAD);
        AgentBuilderFileEntity fileEntity = new AgentBuilderFileEntity().setId(AppCommonUtils.getUUID())
            .setKooPageId(StringUtils.EMPTY)
            .setName(AppCommonUtils.sanitizeFilename(file.getOriginalFilename()))
            .setTaskId(null)
            .setType(0)
            .setUrl(null)
            .setExtraConfig(JSON.toJSONString(extConfigVo));
        fileTransferResult.fillAgentBuilderFileEntityContent(fileEntity);
        AppCommonUtils.setCommonCreateProperties(fileEntity);
        fileMapper.insert(fileEntity);
        return fileEntity.getId();
    }

    private void validateFile(MultipartFile file, AgentBuilderDataType type) {
        type.checkSingleFile(AgentBuilderConfiguration, file.getOriginalFilename(), file.getSize());
    }

    /**
     * 任务文件下载
     *
     * @param taskId 任务Id
     * @param fileId 文件Id
     * @return 文件流
     */
    public ResponseEntity<InputStreamResource> downloadFile(String taskId, String fileId, String targetFormat) {
        AppCommonUtils.validateDomainIdUserIdIsNotEmpty();
        // 参数校验
        AgentBuilderTaskEntity task = taskMapper.getTaskByIdAndTenantAndUser(taskId, AuthorizationContextHolder.domainId(),
            AuthorizationContextHolder.userId());
        if (ObjectUtils.isEmpty(task)) {
            log.error("[downloadFile] validate task fail, task not exist, taskId:{}, userId:{}", taskId,
                AuthorizationContextHolder.userId());
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_PARAM_INCORRECT_ERROR, "task is not exist");
        }
        AgentBuilderFileEntity file = fileMapper.selectOne(
            new LambdaQueryWrapper<AgentBuilderFileEntity>().eq(AgentBuilderFileEntity::getId, fileId)
                .eq(AgentBuilderFileEntity::getTaskId, taskId)
                .eq(AgentBuilderFileEntity::getDeleted, false));
        if (ObjectUtils.isEmpty(file)) {
            log.error("[downloadFile] validate file fail, file not exist, fileId:{}", fileId);
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_PARAM_INCORRECT_ERROR, "file is not exist");
        }
        return fileTransferUtil.downloadTaskFileAndTransfer(file, targetFormat);
    }

    /**
     * 调用managerCenter接口获取agent列表
     *
     * @param pageInfo 分页
     * @return agent信息
     */
    public AgentListResp listAgent(String name, Integer agentType, PageInfo pageInfo) {
        AppCommonUtils.validateDomainIdUserIdIsNotEmpty();
        return agentManagerService.getReleasedAgentList(name, agentType, pageInfo);
    }

    public String publishAgent(PublishAgentRequest req) {
        AppCommonUtils.validateDomainIdUserIdIsNotEmpty();

        // 查询是否已发布，不能重复发布
        LambdaQueryWrapper<Agent> agentQuery = new LambdaQueryWrapper<>();
        agentQuery.eq(Agent::getAgentId, req.getId())
            .eq(Agent::getDomainId, AuthorizationContextHolder.domainId())
            .eq(Agent::getDeleted, 0);
        List<Agent> agents = agentMapper.selectList(agentQuery);
        if (!ObjectUtils.isEmpty(agents)) {
            log.error("Agent exist. agentId = {}, domainId = {}", req.getId(), AuthorizationContextHolder.domainId());
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_PARAM_INCORRECT_ERROR,
                String.format("Agent exist. agentId: %s, domainId: %s", req.getId(),
                    AuthorizationContextHolder.domainId()));
        }
        Agent agent = new Agent();
        agent.setAgentId(req.getId());
        agent.setWorkspaceId(req.getWorkspaceId());
        agent.setType(req.getAppType());
        agent.setCreator(req.getCreator());
        agent.setId(AppCommonUtils.getUUID());
        agent.setStatus(Constant.AGENT_STATUS_ACTIVE);
        agent.setCreatedDate(new Date());
        agent.setLastUpdatedDate(new Date());
        agent.setDomainId(AuthorizationContextHolder.domainId());
        agentMapper.insert(agent);
        return agent.getId();
    }

    public Boolean onlineAgent(String agentId) {
        Agent agent = agentMapper.queryAgentById(agentId);
        if (agent == null) {
            // 记录不存在，抛出异常
            log.error("onlineAgent Agent not exist. agentId = {}, domainId = {}", agentId,
                AuthorizationContextHolder.domainId());
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_DATA_NOT_EXIST);
        }
        if (!Constant.AGENT_STATUS_INACTIVE.equals(agent.getStatus())) {
            // 状态为已下线才可以做上线操作
            log.error("agent status inoperable. agentId = {}, domainId = {}", agentId,
                AuthorizationContextHolder.domainId());
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_DATA_STATUS_INOPERABLE);
        }
        agent.setStatus(Constant.AGENT_STATUS_ACTIVE);
        agent.setLastUpdatedDate(new Date());
        agentMapper.updateById(agent);
        agentMapper.updateById(agent);
        return true;
    }

    public Boolean offlineAgent(String agentId) {
        Agent agent = agentMapper.queryAgentById(agentId);
        if (agent == null) {
            // 记录不存在，抛出异常
            log.error("offlineAgent Agent not exist. agentId = {}, domainId = {}", agentId,
                AuthorizationContextHolder.domainId());
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_DATA_NOT_EXIST);
        }
        if (!Constant.AGENT_STATUS_ACTIVE.equals(agent.getStatus())) {
            // 状态为已下线才可以做上线操作
            log.error("agent status inoperable. agentId = {}, domainId = {}", agentId,
                AuthorizationContextHolder.domainId());
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_DATA_STATUS_INOPERABLE);
        }
        agent.setStatus(Constant.AGENT_STATUS_INACTIVE);
        agent.setLastUpdatedDate(new Date());
        agentMapper.updateById(agent);
        return true;
    }

    public Boolean deleteAgent(String agentId) {
        Agent agent = agentMapper.queryAgentById(agentId);
        if (agent == null) {
            // 记录不存在，抛出异常
            log.error("deleteAgent Agent not exist. agentId = {}, domainId = {}", agentId,
                AuthorizationContextHolder.domainId());
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_DATA_NOT_EXIST);
        }
        agentMapper.deleteById(agent.getId());
        return true;
    }

    @Transactional
    public Boolean addBatchAgent(List<String> agentIds) {
        // 查询数据库判断是否已发布到agentSpace
        for (String agentId : agentIds) {
            if (agentMapper.queryAgentById(agentId) != null) {
                log.error("addBatchAgent agent. agent published. agentId: {}", agentId);
                throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_DATA_STATUS_INOPERABLE);
            }
        }

        // 调用agentStudio接口判断agent是否都存在
        QueryAgentApplicationListRsp applicationListRsp = queryAgentListByIds(agentIds);
        if (applicationListRsp == null || applicationListRsp.getAgentList() == null || applicationListRsp.getAgentList()
            .isEmpty()) {
            // agentStudio返回agent为空
            log.error("addBatchAgent agent. queryAgentListByIds is null.");
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_DATA_NOT_EXIST);
        }

        List<AgentApplicationInfo> agentApplicationList = applicationListRsp.getAgentList();
        Map<String, AgentApplicationInfo> agentMap = agentApplicationList.stream()
            .collect(Collectors.toMap(AgentApplicationInfo::getId, agent -> agent));

        List<String> missingIds = agentIds.stream()
            .filter(id -> !agentMap.containsKey(id))
            .collect(Collectors.toList());
        if (!missingIds.isEmpty()) {
            // 有agent不存在
            log.error("addBatchAgent agent. agent not exist. agentIds: {}", JSON.toJSONString(missingIds));
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_DATA_NOT_EXIST);
        }

        // 构建agent数据
        List<Agent> agentList = new ArrayList<>();
        for (String agentId : agentIds) {
            AgentApplicationInfo agentApplicationInfo = agentMap.get(agentId);
            Agent agent = new Agent();
            agent.setId(AppCommonUtils.getUUID());
            agent.setAgentId(agentId);
            agent.setWorkspaceId(agentApplicationInfo.getWorkspaceId());
            agent.setDomainId(AuthorizationContextHolder.domainId());
            agent.setCreator(AuthorizationContextHolder.userName());
            agent.setType(agentApplicationInfo.getType());
            agent.setStatus(Constant.AGENT_STATUS_ACTIVE);
            agent.setCreatedDate(new Date());
            agent.setLastUpdatedDate(new Date());
            agentList.add(agent);
        }

        // 批量保存数据库
        agentMapper.insertBatchSomeColumn(agentList);
        return true;
    }

    public WorkspaceInfoResp getWorkspaceList() {
        return agentManagerService.getWorkspaceList();
    }

    private QueryAgentApplicationListRsp queryAgentListByIds(List<String> agentIds) {
        log.info("queryAgentListByIds start. ids size: {}", agentIds.size());
        AgentStudioQueryReq agentStudioQueryReq = new AgentStudioQueryReq();
        agentStudioQueryReq.setIds(agentIds);
        agentStudioQueryReq.setLimit(agentIds.size());
        agentStudioQueryReq.setOffset(0);
        QueryAgentApplicationListRsp applicationListRsp = agentManagerService.queryAgentList(agentStudioQueryReq);
        if (applicationListRsp == null) {
            return null;
        }
        log.info("response agentList size: {}", applicationListRsp.getCount());
        return applicationListRsp;
    }
}
