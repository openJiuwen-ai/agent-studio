/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.manager.dto.CesMetricDataResp;
import com.openjiuwen.studio.agent.manager.dto.IdListRequest;
import com.openjiuwen.studio.agent.manager.dto.ListServersQo;
import com.openjiuwen.studio.agent.manager.dto.McpDataProcessBaseInfoListResp;
import com.openjiuwen.studio.agent.manager.dto.McpServerBaseInfoDto;
import com.openjiuwen.studio.agent.manager.dto.McpServerBaseInfoListResp;
import com.openjiuwen.studio.agent.manager.dto.McpServerDetailInfoDto;
import com.openjiuwen.studio.agent.manager.dto.McpServerDetailReq;
import com.openjiuwen.studio.agent.manager.dto.McpServerRatingReq;
import com.openjiuwen.studio.agent.manager.dto.McpServiceBaseInfoListResp;
import com.openjiuwen.studio.agent.manager.dto.McpServiceBatchDeployReq;
import com.openjiuwen.studio.agent.manager.dto.McpServiceBatchDeployResp;
import com.openjiuwen.studio.agent.manager.dto.McpServiceDataResp;
import com.openjiuwen.studio.agent.manager.dto.McpServiceDeployReq;
import com.openjiuwen.studio.agent.manager.dto.McpServiceDetailInfoDto;
import com.openjiuwen.studio.agent.manager.dto.McpServiceModifyReq;
import com.openjiuwen.studio.agent.manager.dto.McpServiceSkinnyEntity;
import com.openjiuwen.studio.agent.manager.dto.McpServiceStatisticResp;
import com.openjiuwen.studio.agent.manager.dto.McpServiceToolsEntity;
import com.openjiuwen.studio.agent.manager.dto.McpServiceToolsRefreshResp;
import com.openjiuwen.studio.agent.manager.dto.McpServiceToolsTestReq;
import com.openjiuwen.studio.agent.manager.dto.McpServicesCesLineChartQo;
import com.openjiuwen.studio.agent.manager.dto.McpServicesCesSuccessRateLineChartQo;
import com.openjiuwen.studio.agent.manager.dto.PageInfoV2;
import com.openjiuwen.studio.agent.manager.service.IMcpServiceManagerService;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/**
 * McpServiceManager controller
 */
@RestController

public class McpServiceManagerApiController implements McpServiceManagerApi {
    private static final Logger log = LoggerFactory.getLogger(McpServiceManagerApiController.class);

    @Autowired
    private IMcpServiceManagerService mcpServiceManagerService;

    @Override
    public ResponseEntity<McpServiceBatchDeployResp> batchDeployServices(String projectId, String workspaceId,
        String resource, McpServiceBatchDeployReq body) {
        return ResponseModel.success(
            mcpServiceManagerService.batchDeployServices(projectId, workspaceId, resource, body));
    }

    @Override
    public ResponseEntity<String> createServer(String projectId, String workspaceId, McpServerDetailReq body) {
        return ResponseModel.success(mcpServiceManagerService.createServer(projectId, workspaceId, body));
    }

    @Override
    public ResponseEntity<McpDataProcessBaseInfoListResp> dataProcessList(String projectId, String workspaceId,
        String language, String name, PageInfoV2 body) {
        return ResponseModel.success(
            mcpServiceManagerService.dataProcessList(projectId, workspaceId, language, name, body));
    }

    @Override
    public ResponseEntity<String> deleteService(String projectId, String workspaceId, String id) {
        return ResponseModel.success(mcpServiceManagerService.deleteService(projectId, workspaceId, id));
    }

    @Override
    public ResponseEntity<String> deploy(String projectId, String workspaceId, String id, McpServiceDeployReq body) {
        return ResponseModel.success(mcpServiceManagerService.deploy(projectId, workspaceId, id, body));
    }

    @Override
    public ResponseEntity<McpServerBaseInfoListResp> listServers(String projectId, ListServersQo listServersQo) {
        return ResponseModel.success(mcpServiceManagerService.listServers(projectId, listServersQo));
    }

    @Override
    public ResponseEntity<McpServiceBaseInfoListResp> listServices(String projectId, String workspaceId,
        String language, String name, String fcInstanceStatus, String nodeType, String visibility, PageInfoV2 body) {
        return ResponseModel.success(
            mcpServiceManagerService.listServices(projectId, workspaceId, language, name, fcInstanceStatus, nodeType,
                visibility, body));
    }

    @Override
    public ResponseEntity<Map<String, Integer>> listServicesSummary(String projectId, String workspaceId) {
        return ResponseModel.success(mcpServiceManagerService.listServicesSummary(projectId, workspaceId));
    }

    @Override
    public ResponseEntity<McpServiceBaseInfoListResp> listServicesWithRuntimeInfo(String projectId, String workspaceId,
        String language, String name, PageInfoV2 body) {
        return ResponseModel.success(
            mcpServiceManagerService.listServicesWithRuntimeInfo(projectId, workspaceId, language, name, body));
    }

    @Override
    public ResponseEntity<Boolean> mcpServerRating(String projectId, String workspaceId, McpServerRatingReq body) {
        return ResponseModel.success(mcpServiceManagerService.mcpServerRating(projectId, workspaceId, body));
    }

    @Override
    public ResponseEntity<List<McpServerBaseInfoDto>> mcpServerRecommendation(String projectId, String workspaceId) {
        return ResponseModel.success(mcpServiceManagerService.mcpServerRecommendation(projectId, workspaceId));
    }

    @Override
    public ResponseEntity<CesMetricDataResp> mcpServicesCesLineChart(String projectId, String id,
        McpServicesCesLineChartQo mcpServicesCesLineChartQo) {
        return ResponseModel.success(
            mcpServiceManagerService.mcpServicesCesLineChart(projectId, id, mcpServicesCesLineChartQo));
    }

    @Override
    public ResponseEntity<McpServiceStatisticResp> mcpServicesCesStatistic(String projectId, String workspaceId,
        String id) {
        return ResponseModel.success(mcpServiceManagerService.mcpServicesCesStatistic(projectId, workspaceId, id));
    }

    @Override
    public ResponseEntity<Map<String, Long>> mcpServicesCesStatisticListMcp(String projectId, String workspaceId,
        IdListRequest body) {
        return ResponseModel.success(
            mcpServiceManagerService.mcpServicesCesStatisticListMcp(projectId, workspaceId, body));
    }

    @Override
    public ResponseEntity<CesMetricDataResp> mcpServicesCesSuccessRateLineChart(String projectId, String id,
        McpServicesCesSuccessRateLineChartQo mcpServicesCesSuccessRateLineChartQo) {
        return ResponseModel.success(mcpServiceManagerService.mcpServicesCesSuccessRateLineChart(projectId, id,
            mcpServicesCesSuccessRateLineChartQo));
    }

    @Override
    public ResponseEntity<String> mcpServicesToolsList(String projectId, String workspaceId, String id) {
        return ResponseModel.success(mcpServiceManagerService.mcpServicesToolsList(projectId, workspaceId, id));
    }

    @Override
    public ResponseEntity<McpServiceToolsEntity> mcpServicesToolsListWithFlow(String projectId, String workspaceId,
        String id) {
        return ResponseModel.success(mcpServiceManagerService.mcpServicesToolsListWithFlow(projectId, workspaceId, id));
    }

    @Override
    public ResponseEntity<McpServiceToolsRefreshResp> refreshMcpServicesTools(String projectId, String workspaceId,
        String id) {
        return ResponseModel.success(mcpServiceManagerService.refreshMcpServicesTools(projectId, workspaceId, id));
    }

    @Override
    public ResponseEntity<Boolean> modifyService(String projectId, String workspaceId, McpServiceModifyReq body) {
        return ResponseModel.success(mcpServiceManagerService.modifyService(projectId, workspaceId, body));
    }

    @Override
    public ResponseEntity<List<McpServiceSkinnyEntity>> queryMcpListByIds(String projectId, String workspaceId,
        List<String> ids) {
        return ResponseModel.success(mcpServiceManagerService.queryMcpListByIds(projectId, workspaceId, ids));
    }

    @Override
    public ResponseEntity<McpServerDetailInfoDto> queryServerDetail(String projectId, String workspaceId, String id) {
        return ResponseModel.success(mcpServiceManagerService.queryServerDetail(projectId, workspaceId, id));
    }

    @Override
    public ResponseEntity<McpServiceDetailInfoDto> queryServiceDetail(String projectId, String workspaceId, String id) {
        return ResponseModel.success(mcpServiceManagerService.queryServiceDetail(projectId, workspaceId, id));
    }

    @Override
    public ResponseEntity<McpServiceDetailInfoDto> queryServiceDetailForRuntime(String projectId, String workspaceId,
        String id) {
        return ResponseModel.success(mcpServiceManagerService.queryServiceDetailForRuntime(projectId, workspaceId, id));
    }

    @Override
    public ResponseEntity<McpServiceDataResp> testServicesTools(String projectId, String workspaceId,
        McpServiceToolsTestReq body) {
        return ResponseModel.success(mcpServiceManagerService.testServicesTools(projectId, workspaceId, body));
    }

    @Override
    public ResponseEntity<Boolean> updateMcpAuthInfo(String projectId, String id, String workspaceId, AuthInfo body) {
        return ResponseModel.success(mcpServiceManagerService.updateMcpAuthInfo(projectId, id, workspaceId, body));
    }
}