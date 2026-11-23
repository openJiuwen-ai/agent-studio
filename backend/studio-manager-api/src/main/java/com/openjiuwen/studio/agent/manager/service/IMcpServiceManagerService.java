/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

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
import com.openjiuwen.studio.agent.manager.dto.McpServerShelfReq;
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
import com.openjiuwen.studio.agent.manager.dto.McpServiceToolsTestReq;
import com.openjiuwen.studio.agent.manager.dto.McpServicesCesLineChartQo;
import com.openjiuwen.studio.agent.manager.dto.McpServicesCesSuccessRateLineChartQo;
import com.openjiuwen.studio.agent.manager.dto.PageInfoV2;

import java.util.List;
import java.util.Map;

/**
 * McpServiceManager service
 */

public interface IMcpServiceManagerService {

    /**
     * batchDeployServices
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param resource resource
     * @param body body
     */
    McpServiceBatchDeployResp batchDeployServices(String projectId, String workspaceId, String resource,
        McpServiceBatchDeployReq body);

    /**
     * createServer
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param body body
     */
    String createServer(String projectId, String workspaceId, McpServerDetailReq body);

    /**
     * dataProcessList
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param language language
     * @param name name
     * @param body body
     */
    McpDataProcessBaseInfoListResp dataProcessList(String projectId, String workspaceId, String language, String name,
        PageInfoV2 body);

    /**
     * deleteService
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param id id
     */
    String deleteService(String projectId, String workspaceId, String id);

    /**
     * deploy
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param id id
     * @param body body
     */
    String deploy(String projectId, String workspaceId, String id, McpServiceDeployReq body);

    /**
     * listServers
     *
     * @param projectId projectId
     * @param listServersQo listServersQo
     */
    McpServerBaseInfoListResp listServers(String projectId, ListServersQo listServersQo);

    /**
     * listServices
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param language language
     * @param name name
     * @param fcInstanceStatus fcInstanceStatus
     * @param nodeType nodeType
     * @param visibility visibility
     * @param body body
     */
    McpServiceBaseInfoListResp listServices(String projectId, String workspaceId, String language, String name,
        String fcInstanceStatus, String nodeType, String visibility, PageInfoV2 body);

    /**
     * listServicesSummary
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     */
    Map<String, Integer> listServicesSummary(String projectId, String workspaceId);

    /**
     * listServicesWithRuntimeInfo
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param language language
     * @param name name
     * @param body body
     */
    McpServiceBaseInfoListResp listServicesWithRuntimeInfo(String projectId, String workspaceId, String language,
        String name, PageInfoV2 body);

    /**
     * mcpServerRating
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param body body
     */
    Boolean mcpServerRating(String projectId, String workspaceId, McpServerRatingReq body);

    /**
     * mcpServerRecommendation
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     */
    List<McpServerBaseInfoDto> mcpServerRecommendation(String projectId, String workspaceId);

    /**
     * mcpServicesCesLineChart
     *
     * @param projectId projectId
     * @param id id
     * @param mcpServicesCesLineChartQo mcpServicesCesLineChartQo
     */
    CesMetricDataResp mcpServicesCesLineChart(String projectId, String id,
        McpServicesCesLineChartQo mcpServicesCesLineChartQo);

    /**
     * mcpServicesCesStatistic
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param id id
     */
    McpServiceStatisticResp mcpServicesCesStatistic(String projectId, String workspaceId, String id);

    /**
     * mcpServicesCesStatisticListMcp
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param body body
     */
    Map<String, Long> mcpServicesCesStatisticListMcp(String projectId, String workspaceId, IdListRequest body);

    /**
     * mcpServicesCesSuccessRateLineChart
     *
     * @param projectId projectId
     * @param id id
     * @param mcpServicesCesSuccessRateLineChartQo mcpServicesCesSuccessRateLineChartQo
     */
    CesMetricDataResp mcpServicesCesSuccessRateLineChart(String projectId, String id,
        McpServicesCesSuccessRateLineChartQo mcpServicesCesSuccessRateLineChartQo);

    /**
     * mcpServicesToolsList
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param id id
     */
    String mcpServicesToolsList(String projectId, String workspaceId, String id);

    /**
     * mcpServicesToolsListWithFlow
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param id id
     */
    McpServiceToolsEntity mcpServicesToolsListWithFlow(String projectId, String workspaceId, String id);

    /**
     * modifyService
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param body body
     */
    Boolean modifyService(String projectId, String workspaceId, McpServiceModifyReq body);

    /**
     * queryMcpListByIds
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param ids ids
     */
    List<McpServiceSkinnyEntity> queryMcpListByIds(String projectId, String workspaceId, List<String> ids);

    /**
     * queryServerDetail
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param id id
     */
    McpServerDetailInfoDto queryServerDetail(String projectId, String workspaceId, String id);

    /**
     * queryServiceDetail
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param id id
     */
    McpServiceDetailInfoDto queryServiceDetail(String projectId, String workspaceId, String id);

    /**
     * queryServiceDetailForRuntime
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param id id
     */
    McpServiceDetailInfoDto queryServiceDetailForRuntime(String projectId, String workspaceId, String id);

    /**
     * testServicesTools
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param body body
     */
    McpServiceDataResp testServicesTools(String projectId, String workspaceId, McpServiceToolsTestReq body);

    /**
     * updateMcpAuthInfo
     *
     * @param projectId projectId
     * @param id id
     * @param workspaceId workspaceId
     * @param body body
     */
    Boolean updateMcpAuthInfo(String projectId, String id, String workspaceId, AuthInfo body);

    /**
     * publishServer：将已部署的 MCP 服务实例上架到资产广场（平台精选，跨租户可见）。
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param req 上架请求（service_id 必填，category 可选）
     * @return 服务目录条目 ID（同一实例重复上架返回既有条目并刷新快照）
     */
    String publishServer(String projectId, String workspaceId, McpServerShelfReq req);

    /**
     * unpublishServer：将 MCP 服务目录条目从资产广场下架（软删目录条目，不影响已安装实例）。
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param serverId 服务目录条目 ID
     * @return 服务目录条目 ID（重复下架幂等）
     */
    String unpublishServer(String projectId, String workspaceId, String serverId);

    /**
     * FEAT-134：导出 MCP 服务为迁移文件（不含凭据）。
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param req 导出请求（selection=IDS/ALL + service_ids）
     * @return 迁移文件 JSON 字符串
     */
    String exportMcpServices(String projectId, String workspaceId,
        com.openjiuwen.studio.agent.manager.dto.McpTransferExportReq req);

    /**
     * FEAT-134：导入 MCP 服务（全量校验 + 新建实例 + 异步刷新）。
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param fileContent 迁移文件内容
     * @return 操作结果（受理快照，HTTP 202 语义）
     */
    com.openjiuwen.studio.agent.manager.dto.McpTransferOperationResp importMcpServices(String projectId,
        String workspaceId, String fileContent);

    /**
     * FEAT-134：重载 MCP 服务工具快照（原地刷新，不动引用）。
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param serviceId 服务 ID
     * @return 操作结果（受理快照）
     */
    com.openjiuwen.studio.agent.manager.dto.McpTransferOperationResp reloadMcpService(String projectId,
        String workspaceId, String serviceId);

    /**
     * FEAT-134：查询导入/重载操作结果。
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param operationId 操作 ID
     * @return 操作终态或运行态
     */
    com.openjiuwen.studio.agent.manager.dto.McpTransferOperationResp getMcpOperationResult(String projectId,
        String workspaceId, String operationId);
}