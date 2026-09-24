/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2020-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.space.app.service.client;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.openjiuwen.studio.agent.space.api.client.ManagerInstClient;
import com.openjiuwen.studio.agent.space.api.vo.AgentType;
import com.openjiuwen.studio.agent.space.api.vo.request.AgentQueryReq;
import com.openjiuwen.studio.agent.space.api.vo.request.AgentStudioQueryReq;
import com.openjiuwen.studio.agent.space.api.vo.request.PageInfo;
import com.openjiuwen.studio.agent.space.api.vo.response.AgentApplicationInfo;
import com.openjiuwen.studio.agent.space.api.vo.response.AgentChatContent;
import com.openjiuwen.studio.agent.space.api.vo.response.AgentChatResp;
import com.openjiuwen.studio.agent.space.api.vo.response.AgentListResp;
import com.openjiuwen.studio.agent.space.api.vo.response.AgentSummaryInfo;
import com.openjiuwen.studio.agent.space.api.vo.response.EmitterInfo;
import com.openjiuwen.studio.agent.space.api.vo.response.QueryAgentApplicationListRsp;
import com.openjiuwen.studio.agent.space.api.vo.response.WorkflowChatResp;
import com.openjiuwen.studio.agent.space.api.vo.response.WorkspaceInfoResp;
import com.openjiuwen.studio.agent.space.api.vo.response.file.MsgFileInfo;
import com.openjiuwen.studio.agent.space.app.constant.Constant;
import com.openjiuwen.studio.agent.space.app.util.AppCommonUtils;
import com.openjiuwen.studio.agent.space.app.util.DateUtils;
import com.openjiuwen.studio.agent.space.app.util.FileTransferUtils;
import com.openjiuwen.studio.agent.space.app.util.WebClientUtils;
import com.openjiuwen.studio.agent.space.common.constant.HeaderConstant;
import com.openjiuwen.studio.agent.space.common.context.AuthorizationContextHolder;
import com.openjiuwen.studio.agent.space.common.exception.AgentSpaceErrorCodes;
import com.openjiuwen.studio.agent.space.common.exception.AgentSpaceException;
import com.openjiuwen.studio.agent.space.common.utils.JacksonUtils;
import com.openjiuwen.studio.agent.space.common.utils.SeqNoUtil;
import com.openjiuwen.studio.agent.space.common.utils.StringUtil;
import com.openjiuwen.studio.agent.space.dao.application.AgentDefaultMapper;
import com.openjiuwen.studio.agent.space.dao.application.AgentMapper;
import com.openjiuwen.studio.agent.space.dao.application.AgentBuilderFileMapper;
import com.openjiuwen.studio.agent.space.dao.application.AgentBuilderMessageMapper;
import com.openjiuwen.studio.agent.space.dao.application.AgentBuilderTaskMapper;
import com.openjiuwen.studio.agent.space.dao.entity.Agent;
import com.openjiuwen.studio.agent.space.dao.entity.AgentDefault;
import com.openjiuwen.studio.agent.space.dao.entity.AgentBuilderFileEntity;
import com.openjiuwen.studio.agent.space.dao.entity.AgentBuilderMessageEntity;
import com.openjiuwen.studio.agent.space.dao.entity.AgentBuilderTaskEntity;

import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;

import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;

/**
 * managerCenter交互实现
 */
@Service
@Slf4j
public class AgentManagerService {
    @Resource
    private AgentBuilderFileMapper AgentBuilderFileMapper;

    @Resource
    private AgentBuilderMessageMapper messageMapper;

    @Resource
    private FileTransferUtils fileTransferUtil;

    @Resource
    private ManagerInstClient managerInstClient;

    @Resource
    private AgentMapper agentMapper;

    @Resource
    private AgentDefaultMapper agentDefaultMapper;

    @Resource
    private AgentBuilderTaskMapper taskMapper;

    @Value("${agent.runtime.endpoint}")
    private String agentRuntimeEndPoint;

    @Value("${agent.space.chat.bucketName:agentBuilder}")
    private String normalAgentbucketName;

    @Value("${agent.space.downloadurl.expires:7}")
    private long downloadUrlExpires;

    private static final String WORKFLOW_CHAT = "/v1/%s/workflows/%s/conversations/%s?workspace_id=%s";

    private static final String AGENT_CHAT = "/v1/%s/agents/%s/conversations/%s?workspace_id=%s";

    /**
     * 查询所有已发布智能体列表
     */
    public AgentListResp getReleasedAgentList(String name, Integer agentType, PageInfo pageInfo) {
        AgentListResp resp = new AgentListResp();
        String type = agentType == null
            ? "controller,chat,agent"
            : Objects.requireNonNull(AgentType.getTypeByCode(agentType)).getType();
        name = StringUtil.isEmpty(name) ? null : name;
        ResponseEntity<QueryAgentApplicationListRsp> response = managerInstClient.queryAgentList(
            AuthorizationContextHolder.projectId(), pageInfo.computeOffset(), pageInfo.getSize(), type, name,
            AuthorizationContextHolder.iamToken());

        if (response != null && response.getBody() != null) {
            QueryAgentApplicationListRsp queryAgentApplicationListRsp = response.getBody();
            resp.setTotal(queryAgentApplicationListRsp.getCount());
            List<AgentSummaryInfo> agents = new ArrayList<>();
            queryAgentApplicationListRsp.getAgentList().forEach(agentApplicationInfo -> {
                AgentSummaryInfo summaryInfo = new AgentSummaryInfo();
                BeanUtils.copyProperties(agentApplicationInfo, summaryInfo);
                summaryInfo.setType(String.valueOf(AgentType.getAgentCode(agentApplicationInfo.getType())));
                agents.add(summaryInfo);
            });
            resp.setAgents(agents);
        } else {
            log.error("getWorkflowAgentInfo failed!");
        }
        return resp;
    }

    private void postStream(String url, JSONObject requestBody, SseEmitter emitter, AgentType agentType,
        StringBuilder aiResponse, AgentBuilderMessageEntity responseMessage) {
        // agentRuntime接口通过slb直接调用
        log.info("start postStream");
        Map<String, String> headers = Map.of(HeaderConstant.HEADER_X_AUTH_TOKEN, AuthorizationContextHolder.iamToken(),
            "stream", "true");

        // 使用响应式WebClient处理流
        WebClientUtils.getSseResponseChunk(agentRuntimeEndPoint + url, requestBody, headers).subscribe(chunk -> {
            // 处理chunk
            EmitterInfo emitterInfo = messageHandler(chunk, agentType);
            sendChunk(emitter, emitterInfo, aiResponse, responseMessage);
        }, error -> {
            // 异常时也发送并保存已经产生的响应
            sendChunk(emitter, EmitterInfo.builder().content(error.getMessage()).name(Constant.ERROR).build(),
                aiResponse, responseMessage);
            updateAnswerContent(aiResponse.toString(), responseMessage);
            emitter.completeWithError(error);
            log.error("SSE stream completeWithError:", error);
        }, () -> {
            // 响应更新到表中
            updateAnswerContent(aiResponse.toString(), responseMessage);
            emitter.complete();
            log.info("SSE stream completed");
        });
    }

    private void updateAnswerContent(String content, AgentBuilderMessageEntity responseMessage) {
        AppCommonUtils.setCommonUpdateProperties(responseMessage);
        LambdaUpdateWrapper<AgentBuilderMessageEntity> msgUpdateWrapper
            = new LambdaUpdateWrapper<AgentBuilderMessageEntity>().set(AgentBuilderMessageEntity::getContent, content)
            .set(AgentBuilderMessageEntity::getLastUpdatedDate, responseMessage.getLastUpdatedDate())
            .set(AgentBuilderMessageEntity::getLastUpdatedByUserId, responseMessage.getLastUpdatedByUserId())
            .eq(AgentBuilderMessageEntity::getId, responseMessage.getId());
        messageMapper.update(msgUpdateWrapper);
    }

    private void sendChunk(SseEmitter emitter, EmitterInfo emitterInfo, StringBuilder aiResponse,
        AgentBuilderMessageEntity responseMessage) {
        if (emitterInfo != null) {
            SseEmitter.SseEventBuilder event = SseEmitter.event()
                .data(emitterInfo.getContent())
                .name(emitterInfo.getName())
                .id(StringUtil.generateUUID(Constant.EVENT_ID_LEN));
            try {
                emitter.send(event);
            } catch (Exception e) {
                log.error("emitter send error. msg = {}", e.getMessage());
                // 保存已经返回的message
                updateAnswerContent(aiResponse.toString(), responseMessage);
                throw new AgentSpaceException(e.getMessage());
            }
            aiResponse.append(emitterInfo.getContent());
        }
    }

    private EmitterInfo messageHandler(String chunk, AgentType agentType) {
        return switch (agentType) {
            case BUILT_IN, DEEP_RESEARCH -> null;
            case CHAT_WORKFLOW, TASK_WORKFLOW ->
                // 工作流智能体
                processWorkflowResp(chunk);
            case SINGLE_AGENT, MULTI_AGENT ->
                // agent智能体
                processAgentResp(chunk);
        };
    }

    private EmitterInfo processAgentResp(String chunk) {
        AgentChatResp response = JacksonUtils.fromJson(chunk, AgentChatResp.class);
        if (response == null) {
            // 解析失败，说明调用失败，直接发送并保存报错信息
            log.error("parse agent chunk error. chunk = {}", chunk);
            return EmitterInfo.builder().content(chunk).name(Constant.MESSAGE).build();
        }

        // 解析message
        if (StringUtil.stringEquals(response.getEvent(), Constant.MESSAGE) && response.getContent() != null) {
            String content = response.getContent().toString();
            if (StringUtil.isNotEmptyString(content) && content.contains("role")) {
                AgentChatContent chatContent = JacksonUtils.fromJson(content, AgentChatContent.class);
                content = chatContent == null ? response.getContent().toString() : chatContent.getContent();
            }

            return EmitterInfo.builder().content(content).name(Constant.MESSAGE).build();
        }

        if (StringUtil.stringEquals(response.getEvent(), Constant.ERROR) && response.getContent() != null) {
            log.error("chat with agent error! msg = {}", response.getContent());
            return EmitterInfo.builder().content(response.getContent().toString()).name(Constant.ERROR).build();
        }

        return null;
    }

    private EmitterInfo processWorkflowResp(String chunk) {
        WorkflowChatResp response = JacksonUtils.fromJson(chunk, WorkflowChatResp.class);

        if (response == null) {
            // 解析失败，说明调用失败，直接发送并保存报错信息
            log.error("parse workflow chunk error. chunk = {}", chunk);
            return EmitterInfo.builder().content(chunk).name(Constant.MESSAGE).build();
        }

        // 解析message
        if (StringUtil.stringEquals(response.getEvent(), Constant.MESSAGE)) {
            if (response.getData() == null) {
                log.error("parse workflow chunk error. chunk = {}", chunk);
                return EmitterInfo.builder().content(chunk).name(Constant.MESSAGE).build();
            }
            return EmitterInfo.builder().content(response.getData().getText()).name(Constant.MESSAGE).build();
        }

        // 当agent执行异常时，message会是空，返回error信息
        if (StringUtil.stringEquals(response.getEvent(), Constant.ERROR)) {
            return EmitterInfo.builder().content(response.getData().getMessage()).name(Constant.ERROR).build();
        }

        return null;
    }

    /**
     * 创建新文件
     */
    public MsgFileInfo createMessageFile(String fileName, String obsUrl) {
        String fileId = SeqNoUtil.generateId(SeqNoUtil.ChatPrefix.CHAT_FILE);
        AgentBuilderFileEntity AgentBuilderFileEntity = new AgentBuilderFileEntity();
        AgentBuilderFileEntity.setId(fileId);
        AgentBuilderFileEntity.setName(fileName);
        AgentBuilderFileEntity.setType(1);
        AgentBuilderFileEntity.setStorageType(1);
        AgentBuilderFileEntity.setUrl(obsUrl);
        AppCommonUtils.setCommonCreateProperties(AgentBuilderFileEntity);
        AgentBuilderFileMapper.insert(AgentBuilderFileEntity);
        return MsgFileInfo.builder()
            .fileId(fileId)
            .fileName(fileName)
            .downloadUrl(fileTransferUtil.getDownloadUrlFromObs(normalAgentbucketName, obsUrl, downloadUrlExpires))
            .build();
    }

    public WorkspaceInfoResp getWorkspaceList() {
        log.info("getWorkspaceList start.");
        ResponseEntity<WorkspaceInfoResp> workspaceList = managerInstClient.getWorkspaceList(
            AuthorizationContextHolder.projectId(), AuthorizationContextHolder.iamToken());
        return workspaceList.getBody();
    }

    public QueryAgentApplicationListRsp queryAgentList(AgentStudioQueryReq agentQueryReq) {
        log.info("queryAgentList request params: {}", JSON.toJSONString(agentQueryReq));
        ResponseEntity<QueryAgentApplicationListRsp> response = managerInstClient.queryAgentList(
            AuthorizationContextHolder.projectId(), AuthorizationContextHolder.iamToken(), agentQueryReq);
        return response.getBody();
    }

    public AgentSummaryInfo getAgentInfo(String agentId) {
        AgentStudioQueryReq studioQueryReq = new AgentStudioQueryReq();
        studioQueryReq.setIds(Collections.singletonList(agentId));
        QueryAgentApplicationListRsp applicationListRsp = queryAgentList(studioQueryReq);
        List<AgentApplicationInfo> agentList = applicationListRsp.getAgentList();
        if (agentList.isEmpty()) {
            log.error("query agent info. agent not exist. agentId: {}", agentId);
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_DATA_NOT_EXIST);
        }
        AgentApplicationInfo agentApplicationInfo = agentList.get(0);
        AgentSummaryInfo summaryInfo = new AgentSummaryInfo();
        BeanUtils.copyProperties(agentApplicationInfo, summaryInfo);
        summaryInfo.setType(String.valueOf(AgentType.getAgentCode(agentApplicationInfo.getType())));
        Agent agent = agentMapper.queryAgentById(agentApplicationInfo.getId());
        summaryInfo.setPublishStatus(agent != null);
        if (agent != null) {
            summaryInfo.setCreator(agent.getCreator());
            summaryInfo.setStatus(agent.getStatus());
        }
        return summaryInfo;
    }

    public AgentListResp queryAllAgent(AgentQueryReq req) {
        log.info("queryAllAgent , name: {}, workspaceId: {}", req.getName(), req.getWorkspaceId());
        AgentStudioQueryReq studioQueryReq = new AgentStudioQueryReq();
        if (StringUtil.isNotEmptyString(req.getName())) {
            studioQueryReq.setName(req.getName());
        }
        studioQueryReq.setWorkspaceId(req.getWorkspaceId());
        studioQueryReq.setOffset(req.computeOffset());
        studioQueryReq.setLimit(req.getSize());
        QueryAgentApplicationListRsp applicationListRsp = queryAgentList(studioQueryReq);
        List<AgentApplicationInfo> agentList = applicationListRsp.getAgentList();
        AgentListResp resp = new AgentListResp();
        resp.setTotal(applicationListRsp.getCount());
        if (agentList.isEmpty()) {
            resp.setAgents(Collections.emptyList());
            return resp;
        }

        // 查询发布到AgentSpace的agent
        LambdaQueryWrapper<Agent> agentQuery = new LambdaQueryWrapper<>();
        agentQuery.eq(Agent::getDomainId, AuthorizationContextHolder.domainId()).eq(Agent::getDeleted, 0);
        List<Agent> publishedAgents = agentMapper.selectList(agentQuery);
        Map<String, Agent> agentMap = publishedAgents.stream()
            .collect(Collectors.toMap(Agent::getAgentId, agent -> agent));

        List<AgentSummaryInfo> agents = new ArrayList<>();
        agentList.forEach(agentApplicationInfo -> {
            Agent agent = agentMap.get(agentApplicationInfo.getId());
            AgentSummaryInfo summaryInfo = new AgentSummaryInfo();
            BeanUtils.copyProperties(agentApplicationInfo, summaryInfo);
            summaryInfo.setType(String.valueOf(AgentType.getAgentCode(agentApplicationInfo.getType())));
            summaryInfo.setPublishStatus(agent != null);
            if (agent != null) {
                summaryInfo.setCreator(agent.getCreator());
                summaryInfo.setStatus(agent.getStatus());
            }
            agents.add(summaryInfo);
        });
        resp.setAgents(agents);
        return resp;
    }

    /**
     * 查询已发布的agent列表
     *
     * @param req
     * @return
     */
    public AgentListResp queryReleasedAgentList(AgentQueryReq req) {
        log.info("getReleasedAgentList request params: {}", JSON.toJSONString(req));
        AgentType typeByCode = null;
        if (req.getAgentType() != null) {
            typeByCode = AgentType.getTypeByCode(req.getAgentType());
        }

        if (StringUtil.isEmpty(req.getName())) {
            // name为空，查询t_agent表进行分页操作，通过id从agentStudio查询详情填充信息
            return queryAgentListNameISnull(req, typeByCode);
        } else {
            // name不为空，查询t_agent表的符合条件的所有agentIds当作条件, 查询agentStudio接口获取数据
            return queryAgentListNameNotNull(req, typeByCode);
        }
    }

    private AgentListResp queryAgentListNameNotNull(AgentQueryReq req, AgentType typeByCode) {
        AgentListResp resp = new AgentListResp();
        // name不为空，查出所有的发布到agentSpace的agentId, 通过条件查询agentStudio
        LambdaQueryWrapper<Agent> agentQuery = buildLambdaQuery(req);
        List<Agent> agents = agentMapper.selectList(agentQuery);

        if (!agents.isEmpty()) {
            List<String> agentIds = agents.stream().map(Agent::getAgentId).toList();
            AgentStudioQueryReq studioQueryReq = new AgentStudioQueryReq();
            if (StringUtil.isNotEmptyString(req.getName())) {
                studioQueryReq.setName(req.getName());
            }
            studioQueryReq.setName(req.getName());
            studioQueryReq.setWorkspaceId(req.getWorkspaceId());
            if (typeByCode != null) {
                studioQueryReq.setType(Collections.singletonList(typeByCode.getType()));
            }

            studioQueryReq.setIds(agentIds);
            studioQueryReq.setOffset(req.computeOffset());
            studioQueryReq.setLimit(req.getSize());
            QueryAgentApplicationListRsp applicationListRsp = queryAgentList(studioQueryReq);

            resp = handleAgentData(agents, applicationListRsp, false);
            resp.setTotal(applicationListRsp.getCount());
        } else {
            log.info("agent list is empty.");
            resp.setTotal(0);
            resp.setAgents(Collections.emptyList());
        }
        return resp;
    }

    private AgentListResp queryAgentListNameISnull(AgentQueryReq req, AgentType typeByCode) {
        AgentListResp resp = new AgentListResp();
        // 没有根据名称过滤，直接查库，分页操作
        LambdaQueryWrapper<Agent> agentQuery = buildLambdaQuery(req);

        Page<Agent> infos = new Page<>(req.getNum(), req.getSize());
        // 查询
        Page<Agent> agents = agentMapper.selectPage(infos, agentQuery);

        List<Agent> records = agents.getRecords();
        List<String> agentIds = records.stream().map(Agent::getAgentId).collect(Collectors.toList());
        if (!agentIds.isEmpty()) {
            AgentStudioQueryReq studioQueryReq = new AgentStudioQueryReq();
            if (typeByCode != null) {
                studioQueryReq.setType(Collections.singletonList(typeByCode.getType()));
            }
            studioQueryReq.setIds(agentIds);
            studioQueryReq.setLimit(agentIds.size());
            studioQueryReq.setOffset(0);
            QueryAgentApplicationListRsp applicationListRsp = queryAgentList(studioQueryReq);
            resp = handleAgentData(records, applicationListRsp, true);
            resp.setTotal(agents.getTotal());
        } else {
            log.info("agent list is empty.");
            resp.setTotal(0);
            resp.setAgents(Collections.emptyList());
        }
        return resp;
    }

    private AgentListResp handleAgentData(List<Agent> records, QueryAgentApplicationListRsp applicationListRsp,
        boolean checkExistence) {
        Map<String, AgentApplicationInfo> agentMap = applicationListRsp.getAgentList()
            .stream()
            .collect(Collectors.toMap(AgentApplicationInfo::getId, agent -> agent));

        if (checkExistence) {
            List<String> allAgentIds = records.stream().map(Agent::getAgentId).toList();
            List<String> missingIds = allAgentIds.stream()
                .filter(id -> !agentMap.containsKey(id))
                .collect(Collectors.toList());
            // 在agentSpace数据库中存在，通过id去agentStudio全量查询，没查到，抛出异常
            if (!missingIds.isEmpty()) {
                // 有agent不存在
                log.error("query agent list. agent not exist. agentIds: {}", JSON.toJSONString(missingIds));
                throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_DATA_NOT_EXIST);
            }
        }

        AgentListResp resp = new AgentListResp();
        resp.setTotal(applicationListRsp.getCount());

        List<AgentSummaryInfo> agents = new ArrayList<>();
        records.forEach(agent -> {
            AgentSummaryInfo summaryInfo = new AgentSummaryInfo();
            AgentApplicationInfo agentApplicationInfo = agentMap.get(agent.getAgentId());
            if (agentApplicationInfo != null) {
                BeanUtils.copyProperties(agentApplicationInfo, summaryInfo);
                summaryInfo.setType(String.valueOf(AgentType.getAgentCode(agentApplicationInfo.getType())));
                summaryInfo.setCreator(agent.getCreator());
                summaryInfo.setStatus(agent.getStatus());
                agents.add(summaryInfo);
            }
        });
        resp.setAgents(agents);
        return resp;
    }

    /**
     * 构建查询条件对象
     */
    private LambdaQueryWrapper<Agent> buildLambdaQuery(AgentQueryReq req) {
        LambdaQueryWrapper<Agent> agentQuery = new LambdaQueryWrapper<>();
        agentQuery.eq(Agent::getDomainId, AuthorizationContextHolder.domainId()).eq(Agent::getDeleted, 0);
        if (StringUtil.isNotEmptyString(req.getWorkspaceId())) {
            agentQuery.eq(Agent::getWorkspaceId, req.getWorkspaceId());
        }

        AgentType typeByCode = null;
        if (req.getAgentType() != null) {
            typeByCode = AgentType.getTypeByCode(req.getAgentType());
            if (typeByCode == null) {
                log.error("query agent list. agent type is invalid. type: {}", req.getAgentType());
                throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_DATA_NOT_EXIST);
            }
            agentQuery.eq(Agent::getType, typeByCode.getType());
        }

        if (StringUtil.isNotEmptyString(req.getStatus())) {
            agentQuery.eq(Agent::getStatus, req.getStatus());
        }
        agentQuery.orderByDesc(Agent::getCreatedDate);
        return agentQuery;
    }

    /**
     * 查询系统内置的agent
     */
    public AgentListResp queryDefaultAgentList(AgentQueryReq req) {
        LambdaQueryWrapper<AgentDefault> agentQuery = new LambdaQueryWrapper<>();
        agentQuery.orderByAsc(AgentDefault::getSort);
        List<AgentDefault> agentDefaults = agentDefaultMapper.selectList(agentQuery);
        List<AgentSummaryInfo> agents = new ArrayList<>();
        for (AgentDefault agent : agentDefaults) {
            AgentSummaryInfo agentSummaryInfo = new AgentSummaryInfo();
            agentSummaryInfo.setType(String.valueOf(agent.getType()));
            agentSummaryInfo.setId(agent.getAgentId());
            agentSummaryInfo.setCreator(agent.getCreator());
            agentSummaryInfo.setName(agent.getName());
            agentSummaryInfo.setDescription(agent.getDescription());
            agentSummaryInfo.setIcon(agent.getIcon());
            agents.add(agentSummaryInfo);
        }
        AgentListResp resp = new AgentListResp();
        resp.setAgents(agents);
        resp.setTotal(agents.size());
        return resp;
    }

    /**
     * 查询用户最近使用的agent
     */
    public AgentListResp queryRecentAgentList(AgentQueryReq req) {
        LambdaQueryWrapper<AgentBuilderTaskEntity> taskQuery = new LambdaQueryWrapper<>();
        taskQuery.eq(AgentBuilderTaskEntity::getCreatedByUserId, AuthorizationContextHolder.userId())
            .eq(AgentBuilderTaskEntity::getDomainId, AuthorizationContextHolder.domainId());
        taskQuery.orderByDesc(AgentBuilderTaskEntity::getCreatedDate);
        int currentPage = 1;
        Page<AgentBuilderTaskEntity> page = new Page<>(currentPage, 100);
        Page<AgentBuilderTaskEntity> taskEntityPage = taskMapper.selectPage(page, taskQuery);
        // 总页数
        long pages = taskEntityPage.getPages();
        List<AgentBuilderTaskEntity> records = taskEntityPage.getRecords();
        LinkedHashSet<String> agentIds = new LinkedHashSet<>();
        List<String> defaultAgentIds = new ArrayList<>();
        List<String> studioAgentIds = new ArrayList<>();
        taskUseAgentHandle(records, agentIds, defaultAgentIds, studioAgentIds);

        // 查询最近的12条记录，最多查询最近500条对话任务使用的agent.
        while (currentPage < pages && agentIds.size() < 12 && currentPage < 5) {
            currentPage++;
            page = new Page<>(currentPage, 100);
            taskEntityPage = taskMapper.selectPage(page, taskQuery);
            records = taskEntityPage.getRecords();
            taskUseAgentHandle(records, agentIds, defaultAgentIds, studioAgentIds);
        }

        List<AgentSummaryInfo> summaryInfos = queryAgentListInfo(agentIds, studioAgentIds, defaultAgentIds);
        AgentListResp resp = new AgentListResp();
        resp.setAgents(summaryInfos);
        resp.setTotal(summaryInfos.size());
        return resp;
    }

    private List<AgentSummaryInfo> queryAgentListInfo(LinkedHashSet<String> agentIds, List<String> studioAgentIds,
        List<String> defaultAgentIds) {
        Map<String, AgentApplicationInfo> studioAgentMap = new HashMap<>();
        if (!studioAgentIds.isEmpty()) {
            AgentStudioQueryReq agentQueryReq = new AgentStudioQueryReq();
            agentQueryReq.setIds(studioAgentIds);
            agentQueryReq.setLimit(agentIds.size());
            agentQueryReq.setOffset(0);
            QueryAgentApplicationListRsp applicationListRsp = queryAgentList(agentQueryReq);
            List<AgentApplicationInfo> agentList = applicationListRsp.getAgentList();
            if (agentList != null) {
                studioAgentMap = agentList.stream()
                    .collect(Collectors.toMap(AgentApplicationInfo::getId, agent -> agent));
            }
        }

        Map<String, AgentDefault> agentDefaultMap = new HashMap<>();
        if (!defaultAgentIds.isEmpty()) {
            for (String defaultAgentId : defaultAgentIds) {
                AgentDefault agentDefault = agentDefaultMapper.queryAgentIds(defaultAgentId);
                agentDefaultMap.put(defaultAgentId, agentDefault);
            }
        }
        List<AgentSummaryInfo> agents = new ArrayList<>();
        for (String agentId : agentIds) {
            if (studioAgentIds.contains(agentId)) {
                AgentApplicationInfo agentApplicationInfo = studioAgentMap.get(agentId);
                AgentSummaryInfo summaryInfo = new AgentSummaryInfo();
                if (agentApplicationInfo != null) {
                    Agent agent = agentMapper.queryAgentById(agentId);
                    BeanUtils.copyProperties(agentApplicationInfo, summaryInfo);
                    summaryInfo.setType(String.valueOf(AgentType.getAgentCode(agentApplicationInfo.getType())));
                    summaryInfo.setCreator(agent.getCreator());
                    summaryInfo.setStatus(agent.getStatus());
                    agents.add(summaryInfo);
                }
                continue;
            }

            if (defaultAgentIds.contains(agentId)) {
                AgentDefault agentDefault = agentDefaultMap.get(agentId);
                AgentSummaryInfo summaryInfo = new AgentSummaryInfo();
                summaryInfo.setId(agentDefault.getAgentId());
                summaryInfo.setDescription(agentDefault.getDescription());
                summaryInfo.setName(agentDefault.getName());
                summaryInfo.setIcon(agentDefault.getIcon());
                summaryInfo.setType(String.valueOf(agentDefault.getType()));
                summaryInfo.setCreator(agentDefault.getCreator());
                summaryInfo.setUpdatedAt(
                    agentDefault.getUpdatedAt().format(DateTimeFormatter.ofPattern(DateUtils.NORM_DATETIME_FORMAT)));
                agents.add(summaryInfo);
            }
        }
        return agents;
    }

    private void taskUseAgentHandle(List<AgentBuilderTaskEntity> records, LinkedHashSet<String> agentIds,
        List<String> defaultAgentIds, List<String> studioAgentIds) {
        for (AgentBuilderTaskEntity record : records) {
            int agentType = record.getAgentType();
            List<String> agentList = record.getAgentList();
            String agentId = (agentList == null || agentList.isEmpty()) ? "" : agentList.get(0);
            if (!agentIds.contains(agentId)) {
                if (agentType == AgentType.BUILT_IN.getCode()) {
                    defaultAgentIds.add(agentId);
                    agentIds.add(agentId);
                } else {
                    // 查询是否已发布到agentSpace
                    Agent agent = agentMapper.queryAgentById(agentId);
                    if (agent != null) {
                        studioAgentIds.add(agentId);
                        agentIds.add(agentId);
                    }
                }
            }
            if (agentIds.size() >= 12) {
                break;
            }
        }
    }
}
