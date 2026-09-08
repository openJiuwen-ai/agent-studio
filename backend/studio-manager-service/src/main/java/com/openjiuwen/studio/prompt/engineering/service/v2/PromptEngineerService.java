/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.service.v2;

import com.fasterxml.jackson.core.type.TypeReference;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.prompt.engineering.constant.CommonConstant;
import com.openjiuwen.studio.prompt.engineering.dto.CreatePromptTaskRsp;
import com.openjiuwen.studio.prompt.engineering.dto.GetPromptTaskIterEvalResQo;
import com.openjiuwen.studio.prompt.engineering.dto.ListPromptTasksQo;
import com.openjiuwen.studio.prompt.engineering.dto.PromptBaseInfo;
import com.openjiuwen.studio.prompt.engineering.dto.PromptBaseResp;
import com.openjiuwen.studio.prompt.engineering.dto.PromptTaskCreateReq;
import com.openjiuwen.studio.prompt.engineering.entity.v2.ExecConfig;
import com.openjiuwen.studio.prompt.engineering.entity.v2.IterationInfo;
import com.openjiuwen.studio.prompt.engineering.entity.v2.PromptEvalutionVo;
import com.openjiuwen.studio.prompt.engineering.entity.v2.PromptIterationResultVo;
import com.openjiuwen.studio.prompt.engineering.entity.v2.PromptTaskDetailVo;
import com.openjiuwen.studio.prompt.engineering.entity.v2.PromptTaskEntity;
import com.openjiuwen.studio.prompt.engineering.entity.v2.PromptVar;
import com.openjiuwen.studio.prompt.engineering.enums.v2.ExecTypeEnum;
import com.openjiuwen.studio.prompt.engineering.enums.v2.PromptTaskStatusEnum;
import com.openjiuwen.studio.prompt.engineering.enums.v2.PtTypeEnum;
import com.openjiuwen.studio.prompt.engineering.enums.v2.TargetTypeEnum;
import com.openjiuwen.studio.prompt.engineering.mapper.v2.PromptTaskMapper;
import com.openjiuwen.studio.prompt.engineering.service.IPromptEngineerService;
import com.openjiuwen.studio.prompt.engineering.service.model.v2.jiuwen.JiuWenJobDeatails;
import com.openjiuwen.studio.prompt.engineering.service.model.v2.jiuwen.JiuWenPromptDeatilRes;
import com.openjiuwen.studio.prompt.engineering.service.model.v2.jiuwen.JiuWenProgress;
import com.openjiuwen.studio.prompt.engineering.utils.StringUtil;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.SortedSet;
import java.util.TreeSet;
import java.util.UUID;
import java.util.stream.Collectors;

@Slf4j
@Service
public class PromptEngineerService implements IPromptEngineerService {

    @Autowired
    private PromptTaskMapper promptTaskMapper;

    @Autowired
    private PromptOptimizeTaskService promptOptimizeTaskService;

    @Autowired
    private PromptEngineerDataSetService promptEngineerDataSetService;

    @Value("${prompt.evaldata.vars.num: 20}")
    private int VARS_NUM;

    @Value("${prompt.evaldata.vars.namelength: 50}")
    private int VARS_NAME_LENGTH;

    @Value("${prompt.evaldata.vars.contentlength: 2000}")
    private int VARS_CONTENT_LENGTH;

    @Value("${spring.is-soft-delete: true}")
    private Boolean isSoftDelete;


    @Override
    public CreatePromptTaskRsp createPromptTaskDraft(String projectId, String workspaceId, PromptTaskCreateReq body) {
        log.info("start to create prompt task draft, projectId: {}, workspaceId: {}",
                projectId, workspaceId);

        PromptTaskDetailVo promptTaskDetailVo = buildPromptTaskDetailVo(body, projectId, workspaceId);

        PromptTaskEntity promptTaskEntity = promptTaskDetailVo.convert2PromptTaskEntity();

        // 任务名不能同名
        List<PromptTaskEntity> existTask = promptTaskMapper.selectByTaskName(promptTaskEntity.getName(), projectId, workspaceId);
        if (CollectionUtils.isNotEmpty(existTask)) {
            log.error("task name already exists, projectId: {}, workspaceId: {}, taskName: {}", projectId, workspaceId,
                promptTaskEntity.getName());
            throw new AgentStudioException(StudioError.OPTIMIZATION_TASK_IS_EXIST);
        }

        promptTaskMapper.insert(promptTaskEntity);

        log.info("prompt task draft created successfully, projectId: {}, workspaceId: {}, taskName: {}",
                projectId, workspaceId, body.getName());

        return new CreatePromptTaskRsp().setTaskId(promptTaskEntity.getId());

    }


    @Override
    public CreatePromptTaskRsp createPromptTask(String projectId, String taskId, String workspaceId) {
        log.info("start to create or restart prompt task, projectId: {}, workspaceId: {}, taskId: {}",
            projectId, workspaceId, taskId);

        PromptTaskEntity promptTaskEntity = promptTaskMapper.selectByPrimaryKey(taskId, projectId, workspaceId);
        entityEmpty(promptTaskEntity, taskId);

        // 创建任务不能同名
        if (promptTaskMapper.selectByTaskNameNotInDraft(promptTaskEntity.getName(), projectId, workspaceId) != null) {
            log.error("task name already exists, projectId: {}, workspaceId: {}, taskName: {}",
                projectId, workspaceId, promptTaskEntity.getName());
            throw new AgentStudioException(StudioError.OPTIMIZATION_TASK_IS_EXIST);
        }

        PromptTaskDetailVo promptTaskDetailVo = promptTaskEntity.convert2PromptTaskDetailVo();

        if (StringUtils.isNotBlank(promptTaskDetailVo.getJiuwenTaskId())) {
            // 重试
            log.info("restarting existing task, projectId: {}, workspaceId: {}, taskId: {}",
                projectId, workspaceId, taskId);
            checkOperationPermission(promptTaskEntity.getStatus(), PromptTaskStatusEnum.OperatorEnum.RESTART);

            try {
                promptOptimizeTaskService.deleteTask(promptTaskDetailVo);
                // 清空message信息
                promptTaskMapper.clearMessageById(taskId, projectId, workspaceId);
            } catch (Exception e) {
                log.warn("delete task failed before restart, projectId: {}, workspaceId: {}, taskId: {}",
                    projectId, workspaceId, taskId);
            }
        } else {
            // 创建任务
            log.info("creating new task, projectId: {}, workspaceId: {}, taskId: {}",
                projectId, workspaceId, taskId);
            checkOperationPermission(promptTaskEntity.getStatus(), PromptTaskStatusEnum.OperatorEnum.CREATE);
        }

        promptOptimizeTaskService.submitTask(promptTaskDetailVo);

        log.info("prompt task created successfully, projectId: {}, workspaceId: {}, taskName: {}",
            projectId, workspaceId, promptTaskDetailVo.getName());

        return new CreatePromptTaskRsp().setTaskId(promptTaskDetailVo.getId());
    }

    @Override
    public CreatePromptTaskRsp copyPromptTask(String projectId, String taskId, String workspaceId) {
        log.info("start to copy prompt task, projectId: {}, workspaceId: {}, taskId: {}",
                projectId, workspaceId, taskId);

        PromptTaskEntity promptTaskEntity = promptTaskMapper.selectByPrimaryKey(taskId, projectId, workspaceId);
        entityEmpty(promptTaskEntity, taskId);
        checkOperationPermission(promptTaskEntity.getStatus(), PromptTaskStatusEnum.OperatorEnum.COPY);

        // 获取所有已存在的任务名称
        List<String> names = promptTaskMapper.selectAllOptimizeTaskNames(projectId, workspaceId);

        // 生成副本名称
        promptTaskEntity.setName(copyName(promptTaskEntity.getName(), names));
        promptTaskEntity.setStatus(PromptTaskStatusEnum.DRAFT.getCode());
        promptTaskEntity.setMessage(null);
        promptTaskEntity.setId(UUID.randomUUID().toString());
        promptTaskEntity.setJiuwenTaskId(null);
        promptTaskEntity.setExecTime(promptTaskEntity.getExecTime());
        promptTaskEntity.setCreatedTime(new Date());

        log.info("start to copy dataset for task, projectId: {}, workspaceId: {}, taskId: {}",
                projectId, workspaceId, taskId);

        promptEngineerDataSetService.copyObsFile(projectId, workspaceId, taskId, promptTaskEntity.getId());

        log.info("start to insert copied task into database, projectId: {}, workspaceId: {}, taskId: {}",
                projectId, workspaceId, promptTaskEntity.getId());

        promptTaskMapper.insert(promptTaskEntity);

        log.info("prompt task copied successfully, projectId: {}, workspaceId: {}, taskId: {}",
                projectId, workspaceId, promptTaskEntity.getId());

        return new CreatePromptTaskRsp().setTaskId(promptTaskEntity.getId());
    }


    private String copyName(String name, List<String> names) {
        int suffix = 1;
        String newName;

        do {
            newName = name + "(副本" + suffix + ")";
            suffix++;
        } while (names.contains(newName));

        if ( newName.length() > 100) {
            log.error("task name length is invalid. taskName:{}", newName);
            throw new AgentStudioException(StudioError.TASK_NAME_LENGTH_EXCEED);
        }

        return newName;
    }


    @Override
    @Transactional
    public PromptBaseInfo deletePromptTask(String projectId, String taskId, String workspaceId) {
        log.info("operation log {} : delete prompt task.", projectId);
        PromptTaskEntity promptTaskEntity = promptTaskMapper.selectByPrimaryKey(taskId, projectId, workspaceId);
        entityEmpty(promptTaskEntity, taskId);
        checkOperationPermission(promptTaskEntity.getStatus(), PromptTaskStatusEnum.OperatorEnum.DELETE);

        if (promptTaskEntity.getStatus() == PromptTaskStatusEnum.RUNNING.getCode()) {
            log.error("delete prompt task failed, task is running. taskId:{}", taskId);
            throw new AgentStudioException(StudioError.OPTIMIZATION_TASK_IS_RUNNING);
        }

        if (promptTaskEntity.getStatus() != PromptTaskStatusEnum.WAITING.getCode()
            && promptTaskEntity.getStatus() != PromptTaskStatusEnum.DRAFT.getCode()) {
            promptOptimizeTaskService.deleteTask(promptTaskEntity.convert2PromptTaskDetailVo());
        }

        if (isSoftDelete) {
            // 软删除操作
            promptTaskMapper.copyToHistory(taskId, projectId, workspaceId);
            log.info("soft delete prompt task success. taskId:{}", taskId);
        } else {
            promptEngineerDataSetService.deleteDateSet(promptTaskEntity.convert2PromptTaskDetailVo(), projectId, workspaceId);
            log.info("delete prompt task success. taskId:{}", taskId);
        }
        promptTaskMapper.deleteByPrimaryKey(taskId, projectId, workspaceId);
        return new PromptBaseInfo().setTaskId(taskId);
    }


    @Override
    public PromptBaseResp getPromptTask(String projectId, String taskId, String workspaceId) {
        log.info("start to get prompt task detail, projectId: {}, workspaceId: {}, taskId: {}",
                projectId, workspaceId, taskId);

        try {
            // 基本信息与优化配置
            PromptTaskEntity promptTaskEntity = promptTaskMapper.selectByPrimaryKey(taskId, projectId, workspaceId);
            entityEmpty(promptTaskEntity, taskId);
            checkOperationPermission(promptTaskEntity.getStatus(), PromptTaskStatusEnum.OperatorEnum.QUERY);

            PromptTaskDetailVo promptTaskDetailVo = promptTaskEntity.convert2PromptTaskDetailVo();

            // 优化分数
            if (StringUtils.isNotBlank(promptTaskDetailVo.getJiuwenTaskId())) {
                log.info("start to get task detail from external service, jiuwenTaskId: {}",
                        promptTaskDetailVo.getJiuwenTaskId());

                JiuWenPromptDeatilRes jiuWenPromptDeatilRes;
                try {
                    jiuWenPromptDeatilRes = promptOptimizeTaskService.getTaskDetail(promptTaskDetailVo);
                } catch (AgentStudioException e) {
                    // builder 侧 job 已丢失（清理/重启无 store 兜底）：降级为 FAILED + lostTaskMsg，
                    // 不再冒泡到外层 catch 包成 02701185
                    if (StudioError.JOB_NOT_FOUND_IN_BUILDER == e.getErrorCode()) {
                        log.warn("prompt task {} (jiuwenTaskId={}) not found in builder, mark as FAILED",
                            promptTaskDetailVo.getId(), promptTaskDetailVo.getJiuwenTaskId());
                        String lostTaskMsg =
                            "Task not found in execution engine, may have been cleaned up, please retry or delete.";
                        promptTaskDetailVo.setMessage(lostTaskMsg);
                        promptTaskDetailVo.setStatus(PromptTaskStatusEnum.FAILED);
                        promptTaskMapper.updateMessageByPrimaryKey(promptTaskDetailVo.getId(),
                            lostTaskMsg, projectId, workspaceId);
                        promptTaskMapper.updateStatusByPrimaryKey(promptTaskDetailVo.getId(),
                            PromptTaskStatusEnum.FAILED.getCode(), projectId, workspaceId);
                        return new PromptBaseResp().setCode(200).setMessage("success").setData(promptTaskDetailVo);
                    }
                    throw e;
                }
                PromptTaskStatusEnum currentStatus = PromptTaskStatusEnum.getByJiuWenStatus(
                        jiuWenPromptDeatilRes.getProgress().getStatus());

                if (PromptTaskStatusEnum.statusMaybeChange(promptTaskDetailVo.getStatus().getCode())) {
                    log.info("update progress rate for task, taskId: {}", promptTaskDetailVo.getId());
                    promptTaskDetailVo.setProgressRate(jiuWenPromptDeatilRes.getProgress().getProgressRate());
                    promptTaskMapper.updateProgressRateByPrimaryKey(promptTaskDetailVo.getId(),
                            jiuWenPromptDeatilRes.getProgress().getProgressRate(), projectId, workspaceId);
                }

                if (currentStatus != null && currentStatus != promptTaskDetailVo.getStatus()) {
                    log.info("task status changed from {} to {}", promptTaskDetailVo.getStatus(), currentStatus);

                    if (currentStatus == PromptTaskStatusEnum.FAILED) {
                        promptTaskDetailVo.setMessage(jiuWenPromptDeatilRes.getProgress().getErrorMsg());
                        promptTaskMapper.updateMessageByPrimaryKey(promptTaskDetailVo.getId(),
                                jiuWenPromptDeatilRes.getProgress().getErrorMsg(), projectId, workspaceId);
                    }

                    promptTaskDetailVo.setStatus(currentStatus);
                    promptTaskMapper.updateStatusByPrimaryKey(promptTaskDetailVo.getId(), currentStatus.getCode(),
                            projectId, workspaceId);
                } else if (currentStatus == null
                        && PromptTaskStatusEnum.statusMaybeChange(promptTaskDetailVo.getStatus().getCode())) {
                    // 反向检查：builder 返回了响应但状态无效（任务信息缺失），
                    // 对仍处于中间态(RUNNING/PAUSING)的任务标记为 FAILED，避免丢失后永久卡在执行中/暂停中
                    log.warn("prompt task {} (jiuwenTaskId={}) got invalid status from builder, mark as FAILED",
                            promptTaskDetailVo.getId(), promptTaskDetailVo.getJiuwenTaskId());
                    String lostTaskMsg = "Task not found in execution engine, may have been cleaned up, please retry or delete.";
                    promptTaskDetailVo.setMessage(lostTaskMsg);
                    promptTaskDetailVo.setStatus(PromptTaskStatusEnum.FAILED);
                    promptTaskMapper.updateMessageByPrimaryKey(promptTaskDetailVo.getId(), lostTaskMsg,
                            projectId, workspaceId);
                    promptTaskMapper.updateStatusByPrimaryKey(promptTaskDetailVo.getId(),
                            PromptTaskStatusEnum.FAILED.getCode(), projectId, workspaceId);
                }

                PromptIterationResultVo promptIterationResultVo = PromptIterationResultVo.builder()
                        .currentBestPrompt(jiuWenPromptDeatilRes.getProgress().getBestPrompt())
                        .iterationInfoList(new ArrayList<>())
                        .build();

                // 文本优化任务提示词有填充示例，多模填充示例无效
                jiuWenPromptDeatilRes.getHistory().forEach(jiuWenHistory -> {
                    IterationInfo iterationInfo = IterationInfo.builder()
                            .optimizedPrompt(promptTaskDetailVo.getPtType() == PtTypeEnum.TEXT
                                    ? jiuWenHistory.getFilledPrompt()
                                    : jiuWenHistory.getOptimizedPrompt())
                            .iterationRound(jiuWenHistory.getIterationRound())
                            .successRate(jiuWenHistory.getSuccessRate())
                            .build();
                    promptIterationResultVo.getIterationInfoList().add(iterationInfo);
                });

                promptTaskDetailVo.setIterationResult(promptIterationResultVo);
            }

            log.info("get prompt task detail successfully, taskId: {}", promptTaskDetailVo.getId());
            return new PromptBaseResp().setCode(200).setMessage("success").setData(promptTaskDetailVo);

        } catch (Exception e) {
            log.error("get prompt task detail failed, projectId: {}, workspaceId: {}, taskId: {}, error: {}",
                    projectId, workspaceId, taskId, e.getMessage(), e);
            throw new AgentStudioException(StudioError.GET_PROMPT_TASK_DETAIL_FAILED);
        }
    }


    @Override
    public PromptBaseResp getPromptTaskIterEvalRes(String projectId, String taskId, String iterNum,
        GetPromptTaskIterEvalResQo getPromptTaskIterEvalResQo) {
        log.info("operation log {} : get prompt task iter eval res.", projectId);

        PromptTaskEntity promptTaskEntity = promptTaskMapper.selectByPrimaryKey(taskId, projectId,
            getPromptTaskIterEvalResQo.getWorkspaceId());
        entityEmpty(promptTaskEntity, taskId);
        checkOperationPermission(promptTaskEntity.getStatus(), PromptTaskStatusEnum.OperatorEnum.QUERY);

        PromptTaskDetailVo promptTaskDetailVo = promptTaskEntity.convert2PromptTaskDetailVo();

        if (StringUtils.isBlank(promptTaskDetailVo.getJiuwenTaskId())) {
            log.error("The task has not been executed. taskId:{}", taskId);
            throw new AgentStudioException(StudioError.OPTIMIZATION_TASK_NOT_CREATED);
        }

        SortedSet<PromptEvalutionVo> sortedSet = new TreeSet<>(Comparator.comparingInt(PromptEvalutionVo::getOrder));

        JiuWenPromptDeatilRes jiuWenPromptDeatilRes = promptOptimizeTaskService.getTaskDetail(promptTaskDetailVo);

        int iterationNum = Integer.parseInt(iterNum);
        if (iterationNum >= jiuWenPromptDeatilRes.getHistory().size()) {
            log.error("The iteration number does not exist. taskId:{}, iterNum:{}", taskId, iterationNum);
            throw new AgentStudioException(StudioError.OPTIMIZATION_TASK_ITERATION_NOT_EXIST);
        }

        jiuWenPromptDeatilRes.getHistory().get(iterationNum).getEvaluations().forEach(evaluation -> {
            PromptEvalutionVo promptEvalutionVo = PromptEvalutionVo.builder()
                .order(evaluation.getOrder())
                .variable(JsonUtils.toJson(evaluation.getVariable()))
                .predict(evaluation.getPredict())
                .label(evaluation.getLabel())
                .score(evaluation.getScore())
                .reason(evaluation.getReason())
                .build();
            sortedSet.add(promptEvalutionVo);
        });

        return new PromptBaseResp().setCode(200).setMessage("success").setData(sortedSet);
    }


    @Override
    public PromptBaseResp listPromptTasks(String projectId, ListPromptTasksQo listPromptTasksQo) {
        log.info("operation log {} : list prompt tasks.", projectId);
        listPromptTasksQo.setName(StringUtil.escapeLikeParam(listPromptTasksQo.getName()));

        // 0. 给出全部任务(0-草稿,1-等待执行,2-执行中,3-执行成功,4-执行失败，5-任务暂停，6-任务暂停中)的数量
        List<String> statusName = Arrays.asList("DRAFT", "WAITING", "RUNNING", "SUCCESS", "FAILED", "PAUSE", "PAUSING");
        Map<String, Integer> statusCountMap = new HashMap<>();
        List<PromptTaskEntity> allTasks = promptTaskMapper.selectTasksByPrimaryKey(projectId,
            listPromptTasksQo.getWorkspaceId());

        // 在内存中统计每个状态的任务数量
        int textCount = 0;
        int multiCount = 0;
        for (PromptTaskEntity task : allTasks) {
            String status = statusName.get(task.getStatus());
            statusCountMap.put(status, statusCountMap.getOrDefault(status, 0) + 1);
            if ("text".equals(task.getPtType())) {
                textCount++;
            } else if ("multi".equals(task.getPtType())) {
                multiCount++;
            }
        }
        statusCountMap.put("TOTAL", allTasks.size());
        statusCountMap.put("TEXT", textCount);
        statusCountMap.put("MULTI", multiCount);

        // 1. 分页查询符合条件的任务实体（含conversionId等核心字段）
        PageInfo<PromptTaskEntity> entityPage = PageHelper.startPage(listPromptTasksQo.getPageNum(),
                listPromptTasksQo.getPageSize())
            .doSelectPageInfo(() -> promptTaskMapper.queryTaskIdsByCondition(listPromptTasksQo, projectId,
                statusName.indexOf(listPromptTasksQo.getStatus())));

        // 2. 如果没有数据，直接返回空分页结果（避免空指针）
        if (CollectionUtils.isEmpty(entityPage.getList())) {
            return new PromptBaseResp().setCode(200).setMessage(JsonUtils.toJson(statusCountMap)).setData(new HashMap<>());
        }

        // 3. 提取所有任务ID（用于批量查询详情）
        Map<String, PromptTaskEntity> taskIdToEntityMap = entityPage.getList()
            .stream()
            .filter(entity -> PromptTaskStatusEnum.statusMaybeChange(entity.getStatus())) // 筛选可能变化的状态
            .collect(Collectors.toMap(PromptTaskEntity::getJiuwenTaskId, entity -> entity));

        // 4. 根据ID批量查询任务详情
        JiuWenJobDeatails jiuWenJobDetails = promptOptimizeTaskService.queryTaskDetailsByIds(
            new ArrayList<>(taskIdToEntityMap.values()));

        // 收集九问实际返回的 jobId，用于反向检查缺失的任务
        Set<String> returnedJiuwenIds = new HashSet<>();
        List<JiuWenProgress> jiuWenProgressList = jiuWenJobDetails.getData();
        if (jiuWenProgressList != null) {
            for (JiuWenProgress jiuWenJobDetail : jiuWenProgressList) {
                returnedJiuwenIds.add(jiuWenJobDetail.getJobInfo().getId());
                PromptTaskEntity promptTaskEntity = taskIdToEntityMap.get(jiuWenJobDetail.getJobInfo().getId());
                if (promptTaskEntity == null) {
                    continue;
                }
                PromptTaskStatusEnum currentStatus = PromptTaskStatusEnum.getByJiuWenStatus(jiuWenJobDetail.getStatus());
                if (currentStatus != null && currentStatus.getCode() != promptTaskEntity.getStatus()) {
                    promptTaskEntity.setStatus(currentStatus.getCode());
                    // 5. 更新状态变化
                    promptTaskMapper.updateStatusByPrimaryKey(promptTaskEntity.getId(), currentStatus.getCode(),
                        projectId, listPromptTasksQo.getWorkspaceId());
                    if (currentStatus == PromptTaskStatusEnum.FAILED) {
                        promptTaskEntity.setMessage(jiuWenJobDetail.getErrorMsg());
                        promptTaskMapper.updateMessageByPrimaryKey(promptTaskEntity.getId(),
                            jiuWenJobDetail.getErrorMsg(), projectId, listPromptTasksQo.getWorkspaceId());
                    }
                }
                promptTaskEntity.setProgressRate(jiuWenJobDetail.getProgressRate());
                promptTaskMapper.updateProgressRateByPrimaryKey(promptTaskEntity.getId(),
                    jiuWenJobDetail.getProgressRate(), projectId, listPromptTasksQo.getWorkspaceId());
            }
        }

        // 反向检查：查询了但九问未返回的任务（任务在执行引擎中已丢失），
        // 对仍处于中间态(RUNNING/PAUSING)的任务标记为 FAILED，避免丢失后永久卡在执行中/暂停中
        String lostTaskMsg = "Task not found in execution engine, may have been cleaned up, please retry or delete.";
        for (Map.Entry<String, PromptTaskEntity> entry : taskIdToEntityMap.entrySet()) {
            if (returnedJiuwenIds.contains(entry.getKey())) {
                continue;
            }
            PromptTaskEntity lostEntity = entry.getValue();
            if (!PromptTaskStatusEnum.statusMaybeChange(lostEntity.getStatus())) {
                continue;
            }
            log.warn("prompt task {} (jiuwenTaskId={}) not found in builder, mark as FAILED",
                lostEntity.getId(), entry.getKey());
            lostEntity.setStatus(PromptTaskStatusEnum.FAILED.getCode());
            lostEntity.setMessage(lostTaskMsg);
            promptTaskMapper.updateStatusByPrimaryKey(lostEntity.getId(),
                PromptTaskStatusEnum.FAILED.getCode(), projectId, listPromptTasksQo.getWorkspaceId());
            promptTaskMapper.updateMessageByPrimaryKey(lostEntity.getId(), lostTaskMsg,
                projectId, listPromptTasksQo.getWorkspaceId());
        }

        List<PromptTaskDetailVo> detailVos = entityPage.getList()
            .stream()
            .map(PromptTaskEntity::convert2PromptTaskDetailVo)
            .collect(Collectors.toList());

        // 6. 构建分页结果（复用原分页元数据，替换列表数据）
        PageInfo<PromptTaskDetailVo> resultPage = new PageInfo<>(detailVos);
        // 复制分页元数据（总条数、页码等）
        resultPage.setTotal(entityPage.getTotal());
        resultPage.setPageNum(entityPage.getPageNum());
        resultPage.setPageSize(entityPage.getPageSize());
        resultPage.setPages(entityPage.getPages());

        log.info("query task's num:{}", resultPage.getTotal());
        return new PromptBaseResp().setCode(200).setMessage(JsonUtils.toJson(statusCountMap)).setData(resultPage);
    }


    @Override
    public PromptBaseInfo pausePromptTask(String projectId, String taskId, String workspaceId) {
        log.info("start to pause prompt task, projectId: {}, workspaceId: {}, taskId: {}",
                projectId, workspaceId, taskId);

        PromptTaskEntity promptTaskEntity = promptTaskMapper.selectByPrimaryKey(taskId, projectId, workspaceId);
        entityEmpty(promptTaskEntity, taskId);
        checkOperationPermission(promptTaskEntity.getStatus(), PromptTaskStatusEnum.OperatorEnum.PAUSE);

        log.info("calling external service to pause task, taskId: {}", taskId);
        promptOptimizeTaskService.pauseTask(promptTaskEntity.convert2PromptTaskDetailVo());

        log.info("updating task status to PAUSE, taskId: {}", taskId);
        promptTaskMapper.updateStatusByPrimaryKey(promptTaskEntity.getId(),
                PromptTaskStatusEnum.PAUSING.getCode(), projectId, workspaceId);

        log.info("prompt task paused successfully, taskId: {}", taskId);
        return new PromptBaseInfo().setTaskId(taskId).setMessage("task stop successfully");

    }

    @Override
    public PromptBaseInfo resumePromptTask(String projectId, String taskId, String workspaceId) {
        log.info("start to resume prompt task, projectId: {}, workspaceId: {}, taskId: {}",
                projectId, workspaceId, taskId);

        PromptTaskEntity promptTaskEntity = promptTaskMapper.selectByPrimaryKey(taskId, projectId, workspaceId);
        entityEmpty(promptTaskEntity, taskId);
        checkOperationPermission(promptTaskEntity.getStatus(), PromptTaskStatusEnum.OperatorEnum.RESUME);

        log.info("calling external service to resume task, taskId: {}", taskId);
        promptOptimizeTaskService.resumeTask(promptTaskEntity.convert2PromptTaskDetailVo());

        log.info("updating task status to RUNNING, taskId: {}", taskId);
        promptTaskMapper.updateStatusByPrimaryKey(promptTaskEntity.getId(),
                PromptTaskStatusEnum.RUNNING.getCode(), projectId, workspaceId);

        log.info("prompt task resumed successfully, taskId: {}", taskId);
        return new PromptBaseInfo().setTaskId(taskId).setMessage("task resume successfully");

    }

    @Override
    public PromptBaseInfo startPromptTask(String projectId, String taskId, String workspaceId) {
        log.info("operation log {} : start prompt task.", projectId);
        return null;
    }


    @Override
    public PromptBaseResp updatePromptTaskDraft(String projectId, String taskId, String workspaceId,
        PromptTaskCreateReq body) {
        log.info("operation log {} : update prompt task.", projectId);
        // id要存在
        PromptTaskEntity oriPromptTaskEntity = promptTaskMapper.selectByPrimaryKey(taskId, projectId, workspaceId);
        entityEmpty(oriPromptTaskEntity, taskId);
        checkOperationPermission(oriPromptTaskEntity.getStatus(), PromptTaskStatusEnum.OperatorEnum.EDIT);

        PromptTaskDetailVo oriPromptTaskDetailVo = oriPromptTaskEntity.convert2PromptTaskDetailVo();

        // 构建新的实体
        buildUpdatePromptTaskDetailVo(buildPromptTaskDetailVo(body, projectId, workspaceId), oriPromptTaskDetailVo);

        PromptTaskEntity promptTaskEntity = oriPromptTaskDetailVo.convert2PromptTaskEntity();

        // 任务名不能同名
        List<PromptTaskEntity> existTask = promptTaskMapper.selectByTaskName(promptTaskEntity.getName(), projectId, workspaceId);

        if (CollectionUtils.isEmpty(existTask) || (existTask.size() == 1 && existTask.get(0).getId().equals(taskId))) {
            int updateCount = promptTaskMapper.updateByPrimaryKey(promptTaskEntity, projectId, workspaceId);
            if (updateCount < 1) {
                log.error("update prompt task failed. Data not exist. taskId:{}, taskName:{}", taskId, body.getName());
                throw new AgentStudioException(StudioError.DATA_NOT_EXIST);
            }
            return new PromptBaseResp().setCode(200)
                .setMessage("success")
                .setData(oriPromptTaskDetailVo.getUpdatedTime());
        } else {
            log.error("task name already exists, projectId: {}, workspaceId: {}, taskName: {}", projectId, workspaceId,
                oriPromptTaskEntity.getName());
            throw new AgentStudioException(StudioError.OPTIMIZATION_TASK_IS_EXIST);
        }
    }

    private PromptTaskDetailVo buildPromptTaskDetailVo(PromptTaskCreateReq body, String projectId, String workspaceId) {
        ExecConfig ptModel = new ExecConfig();
        BeanUtils.copyProperties(body.getPtObject(), ptModel);
        ptModel.setExecType(ExecTypeEnum.fromValue(body.getPtObject().getExecType().toString()));
        checkModel(ptModel.getModel(), projectId, workspaceId);

        ExecConfig execObject = new ExecConfig();
        BeanUtils.copyProperties(body.getAssitantObject(), execObject);
        execObject.setExecType(ExecTypeEnum.fromValue(body.getAssitantObject().getExecType().toString()));
        checkModel(execObject.getModel(), projectId, workspaceId);

        if (!StringUtils.isBlank(body.getPtVars())
            && body.getPtVars().length() > (VARS_NAME_LENGTH + VARS_CONTENT_LENGTH + 30) * VARS_NUM) {
            log.error("eval item is too long !");
            throw new AgentStudioException(StudioError.JSON_CONTENT_LENGTH_EXCEED);
        }

        List<PromptVar> promptVars = JsonUtils.json2Obj(body.getPtVars(), new TypeReference<List<PromptVar>>() { });
        validPromptVars(promptVars);

        return PromptTaskDetailVo.builder()
            .id(UUID.randomUUID().toString())
            .jiuwenTaskId(null)
            .name(body.getName())
            .desc(body.getDesc())
            .promptId(body.getPromptId()) // 源提示词id
            .ptType(body.getPtType() != null ? PtTypeEnum.fromValue(body.getPtType().toString()) : null)
            .execObject(execObject)
            .ptText(body.getPtText())
            .ptVars(promptVars)
            .ptModel(ptModel)
            .execTime(body.getExecTime() != null ? new Date(body.getExecTime()) : null)
            .targetAcc(body.getTargetAcc() != null ? Double.valueOf(body.getTargetAcc()) : null)
            .maxIterNum(body.getMaxIterNum())
            .showCaseNum(body.getShowCaseNum())
            .targetType(body.getTargetType() != null ? TargetTypeEnum.fromValue(body.getTargetType().toString()) : null)
            .scoreStandard(body.getScoreStandard())
            .backKnowledge(body.getBackKnowledge())
            .progressRate(0.00)
            .status(PromptTaskStatusEnum.DRAFT) // 草稿状态
            .createdTime(new Date().getTime())
            .updatedTime(new Date().getTime())
            .workspaceId(workspaceId)
            .projectId(projectId)
            .creator(RequestContextUtils.getRequestUserName())
            .creatorId(RequestContextUtils.getRequestUserId())
            .domainId(RequestContextUtils.getRequestUserDomainId())
            .algorithm(body.getAlgorithm() == null ? null : body.getAlgorithm().toString())
            .build();
    }

    private void checkModel(String modelId, String projectId, String workspaceId) {
        String currentProjectId = promptTaskMapper.queryProjectIdByModelId(modelId);
        String publishStatus = promptTaskMapper.queryPublishStatusByModelId(modelId);
        String modelType = promptTaskMapper.queryModelTypeByModelId(modelId);
        if (StringUtils.isBlank(currentProjectId) || StringUtils.isBlank(publishStatus) || StringUtils.isBlank(modelType)) {
            return;
        }
        if ((!Strings.CS.equals(modelType, "PLATFORM-INTEGRATION") && !Strings.CS.equals(projectId, currentProjectId)) || !Strings.CS.equals(publishStatus, "online")) {
            log.error("prompt model not exist. modelId:{}, currentProjectId is {}, publishStatus is {}", modelId, currentProjectId, publishStatus);
            throw new AgentStudioException(StudioError.PROMPT_MODEL_NOT_EXIST);
        }
    }


    private void buildUpdatePromptTaskDetailVo(PromptTaskDetailVo oriPromptTaskDetailVo,
        PromptTaskDetailVo promptTaskDetailVo) {
        if (oriPromptTaskDetailVo == null) {
            log.warn("oriPromptTaskDetailVo is null, taskId: {}", promptTaskDetailVo.getId());
            throw new AgentStudioException(StudioError.REQUEST_BODY_NOT_EMPTY);
        }
        log.info("start to build updated prompt task detail, taskId: {}", oriPromptTaskDetailVo.getId());

        promptTaskDetailVo.setName(oriPromptTaskDetailVo.getName());
        promptTaskDetailVo.setDesc(oriPromptTaskDetailVo.getDesc());
        promptTaskDetailVo.setPtType(oriPromptTaskDetailVo.getPtType());
        promptTaskDetailVo.setExecObject(oriPromptTaskDetailVo.getExecObject());
        promptTaskDetailVo.setPtText(oriPromptTaskDetailVo.getPtText());
        promptTaskDetailVo.setPtVars(oriPromptTaskDetailVo.getPtVars());
        promptTaskDetailVo.setPtModel(oriPromptTaskDetailVo.getPtModel());
        promptTaskDetailVo.setExecTime(oriPromptTaskDetailVo.getExecTime());
        promptTaskDetailVo.setTargetAcc(oriPromptTaskDetailVo.getTargetAcc());
        promptTaskDetailVo.setMaxIterNum(oriPromptTaskDetailVo.getMaxIterNum());
        promptTaskDetailVo.setShowCaseNum(oriPromptTaskDetailVo.getShowCaseNum());
        promptTaskDetailVo.setTargetType(oriPromptTaskDetailVo.getTargetType());
        promptTaskDetailVo.setScoreStandard(oriPromptTaskDetailVo.getScoreStandard());
        promptTaskDetailVo.setBackKnowledge(oriPromptTaskDetailVo.getBackKnowledge());
        promptTaskDetailVo.setUpdatedTime(new Date().getTime());
        promptTaskDetailVo.setDomainId(oriPromptTaskDetailVo.getDomainId());
        promptTaskDetailVo.setAlgorithm(oriPromptTaskDetailVo.getAlgorithm());
    }

    private void entityEmpty(PromptTaskEntity promptTaskEntity, String taskId) {
        if (promptTaskEntity == null) {
            log.error("The task ID to be deleted does not exist. id:{}", taskId);
            throw new AgentStudioException(StudioError.OPTIMIZATION_TASK_ID_IS_NOT_EXIST);
        }
    }

    private void checkOperationPermission(int status, PromptTaskStatusEnum.OperatorEnum op) {
        PromptTaskStatusEnum currentStatus = PromptTaskStatusEnum.getByCode(status);
        if (ObjectUtils.isEmpty(currentStatus) || !currentStatus.isOperatorAllowed(op)) {
            log.error("The task status is not allowed to be operated. status:{}", status);
            throw new AgentStudioException(StudioError.OPERATOR_ERROR);
        }
    }

    private void validPromptVars(List<PromptVar> promptVars) {
        if (!CollectionUtils.isEmpty(promptVars)) {
            if ( promptVars.size() > VARS_NUM ) {
                log.error("prompt var nums is invalid");
                throw new AgentStudioException(StudioError.VARS_NUM_EXCEED, VARS_NUM);
            }
            Set<String> varNamesSet = new HashSet<>();
            for (PromptVar promptVar : promptVars) {
                if (StringUtils.isEmpty(promptVar.getName()) || promptVar.getName().length() > VARS_NAME_LENGTH) {
                    log.error("prompt var is invalid");
                    throw new AgentStudioException(StudioError.VARS_NAME_LENGTH_EXCEED, VARS_NAME_LENGTH);
                }
                // 重名校验
                if (varNamesSet.contains(promptVar.getName())) {
                    log.error("prompt var name is Duplicate");
                    throw new AgentStudioException(StudioError.VARS_NAME_DUPLICATE, promptVar.getName());
                }
                varNamesSet.add(promptVar.getName());
            }
            if (!varNamesSet.contains(CommonConstant.AGENT_BUILDER_PROMPT_OUTPUT)) {
                log.error("AGENT_BUILDER_PROMPT_OUTPUT is not set");
                throw new AgentStudioException(StudioError.AGENT_BUILDER_PROMPT_OUTPUT_ERROR);
            }

        }
    }

}
