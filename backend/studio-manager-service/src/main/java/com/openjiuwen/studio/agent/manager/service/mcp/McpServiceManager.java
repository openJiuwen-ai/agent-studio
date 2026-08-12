/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.mcp;

import static com.openjiuwen.studio.agent.manager.enums.EnumMcpStatus.CREATING_STACK;
import static com.openjiuwen.studio.agent.manager.enums.EnumMcpStatus.DELETING;
import static com.openjiuwen.studio.agent.manager.enums.EnumMcpStatus.SUCCESS;
import static com.openjiuwen.studio.agent.manager.utils.WorkflowUtils.removeQueryParamsFromUrl;

import com.alibaba.fastjson2.JSONObject;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.annotation.OperationLog;
import com.openjiuwen.studio.agent.common.enums.OperationType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.service.CommonService;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.utils.OkHttpClientUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.UrlCheckUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.CesMetricDataResp;
import com.openjiuwen.studio.agent.manager.dto.Datapoints;
import com.openjiuwen.studio.agent.manager.dto.Extension;
import com.openjiuwen.studio.agent.manager.dto.IdListRequest;
import com.openjiuwen.studio.agent.manager.dto.McpDataProcessBaseInfoListResp;
import com.openjiuwen.studio.agent.manager.dto.McpDeployResult;
import com.openjiuwen.studio.agent.manager.dto.McpServerBaseInfoDto;
import com.openjiuwen.studio.agent.manager.dto.McpServerBaseInfoListResp;
import com.openjiuwen.studio.agent.manager.dto.McpServerDetailInfoDto;
import com.openjiuwen.studio.agent.manager.dto.McpServerDetailReq;
import com.openjiuwen.studio.agent.manager.dto.McpServerRatingReq;
import com.openjiuwen.studio.agent.manager.dto.McpServiceBaseInfoDto;
import com.openjiuwen.studio.agent.manager.dto.McpServiceBaseInfoListResp;
import com.openjiuwen.studio.agent.manager.dto.McpServiceBatchDeployItem;
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
import com.openjiuwen.studio.agent.manager.dto.McpServiceToolsTestResp;
import com.openjiuwen.studio.agent.manager.dto.McpServicesCesLineChartQo;
import com.openjiuwen.studio.agent.manager.dto.McpServicesCesSuccessRateLineChartQo;
import com.openjiuwen.studio.agent.manager.dto.PageInfoV2;
import com.openjiuwen.studio.agent.manager.dto.McpFailReasonDetailDto;
import com.openjiuwen.studio.agent.manager.dto.ListServersQo;
import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.manager.entity.McpServerEntity;
import com.openjiuwen.studio.agent.manager.entity.McpServerRatingEntity;
import com.openjiuwen.studio.agent.manager.entity.McpServiceEntity;
import com.openjiuwen.studio.agent.manager.entity.ServerScore;
import com.openjiuwen.studio.agent.manager.enums.EnumMcpStatus;
import com.openjiuwen.studio.agent.manager.enums.EnumOrgType;
import com.openjiuwen.studio.agent.manager.enums.McpNodeType;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.service.IMcpServiceManagerService;
import com.openjiuwen.studio.agent.manager.service.mcp.apigservice.ApiMcpService;
import com.openjiuwen.studio.agent.manager.service.mcp.apigservice.bean.ApigRequsetDto;
import com.openjiuwen.studio.agent.manager.service.mcp.auth.IMcpBase;
import com.openjiuwen.studio.agent.manager.service.mcp.infrastructure.apig.CesService;
import com.openjiuwen.studio.agent.manager.service.mcp.local.McpUpdateTask;
import com.openjiuwen.studio.agent.manager.service.mcp.model.dao.McpServerDao;
import com.openjiuwen.studio.agent.manager.service.mcp.model.dao.McpServerRatingDao;
import com.openjiuwen.studio.agent.manager.service.mcp.model.dao.McpServiceDao;
import com.openjiuwen.studio.agent.manager.service.share.ShareInnerService;
import com.openjiuwen.studio.agent.manager.service.workspace.WorkspaceMappingService;
import com.openjiuwen.studio.agent.manager.utils.CommonUtil;
import com.openjiuwen.studio.agent.manager.utils.IamServiceUtils;
import com.openjiuwen.studio.agent.manager.utils.ImageBase64Utils;
import com.openjiuwen.studio.agent.manager.utils.McpJsonUtils;
import com.openjiuwen.studio.agent.manager.utils.McpServiceExceptionUtils;
import com.openjiuwen.studio.agent.manager.utils.McpUtil;
import com.openjiuwen.studio.common.service.service.EncryptionAdapter;
import com.huaweicloud.sdk.apig.v2.model.DeleteApiV2Response;

import inet.ipaddr.IPAddressString;
import io.modelcontextprotocol.spec.McpSchema;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import okhttp3.Request;
import okhttp3.Response;

import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.net.InetAddress;
import java.net.URI;
import java.net.URISyntaxException;
import java.net.UnknownHostException;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.Proxy;
import java.net.ProxySelector;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
import java.util.Collections;
import java.util.Comparator;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.Queue;
import java.util.regex.Pattern;
import java.util.stream.Collectors;


/**
 * MCP service
 *
 */
@Slf4j
@Service
public class McpServiceManager implements IMcpServiceManagerService {
    private static final String TENANT_ID = "tenantId";

    /**
     * 监控粒度
     */
    private static final int DEFAULT_PERIOD = 86400;

    /**
     * 监控数据默认最大显示个数
     */
    private static final int DEFAULT_LIMIT = 7;

    /**
     * 监控查询默认起始时间和当前时间相差天数
     */
    private static final int DEFAULT_DAY = 150;

    /**
     * 统计数据默认起始时间和当前时间相差天数
     */
    private static final int DEFAULT_MINUS_DAY = 30;

    /**
     * 默认评分
     */
    private static final double DEFAULT_SCORES = 6.0d;

    private static final String ROMA_RESOURCE_NAME = "ROMA";

    @Autowired
    private OkHttpClientUtils okHttpClientUtils;

    // 【修改点】在最后加上了 "+" 号，允许 Base64 Token 通过
    private static final Pattern SERVICE_CONFIG_PATTERN = Pattern.compile("^[\\u4e00-\\u9fa5_a-zA-Z0-9\\-,.?:;\"'：=；“”‘’//，。？、()（）\\[\\]{}@!！*%#+\\s]*$");

    private static final Pattern NAME_PATTERN = Pattern.compile("^(?!_)(?!-)(?!\\d)[a-zA-Z0-9_\\-\\u4e00-\\u9fa5()（）\\s.]{2,64}$");

    private enum LANGUAGE {
        /**
         * 英文
         */
        EN,

        /**
         * 中文
         */
        ZH
    }

    @Value("${mcp.mcp-quota:30}")
    private String mcpQuota;

    @Value("${mcp.default-icon}")
    private String mcpDefaultIcon;

    @Value("${hcs.switch.mcp:false}")
    private boolean hasHcsMcpSwitch;

    @Value("${agent.builder.agency.rsf.name:}")
    private String rsfAgencyName;

    @Value("${agent.builder.agency.rsf.trust.domainName:}")
    private String rsfAgencyTrustDomainName;

    @Value("${agent.builder.agency.fg.name:}")
    private String fgAgencyName;

    @Value("${agent.builder.agency.fg.trust.domainName:}")
    private String fgAgencyTrustDomainName;

    @Value("${mcp.mcp-name-en-check:false}")
    private Boolean mcpNameEnCheck;

    @Value("${mas.appcode}")
    private String masAppcode;

    @Value("${spring.is-soft-delete}")
    private Boolean isSoftDelete;

    @Resource
    private McpServerDao serverDao;

    @Resource
    private McpServiceDao serviceDao;

    @Resource
    private McpUtil mcpUtil;

    @Resource
    private ThreadPoolTaskExecutor mcpTaskExecutor;

    @Resource
    private ThreadPoolTaskExecutor mcpUpdateTaskExecutor;

    @Resource
    private McpUpdateTask mcpUpdateTask;

    @Resource
    private CesService cesService;

    @Resource
    private McpServerRatingDao mcpServerRatingDao;

    @Resource
    private IamServiceUtils iamServiceUtils;

    @Resource
    private CommonService commonService;

    @Resource
    private ApiMcpService apigMcpService;

    @Resource
    private McpClientService mcpClientService;

    @Autowired
    private MappingMapper mappingMapper;

    @Autowired
    private WorkspaceMappingService workspaceMappingService;

    @Autowired
    private EncryptionAdapter encryptionAdapter;

    @Value("${workflow.connector_config_host_blacklist}")
    private String connectorConfigHostBlacklist;

    @Value("${mcp.enable-url-check}")
    private Boolean enableUrlCheck;

    @Autowired
    private I18nUtil i18nUtil;

    @Autowired
    private IMcpBase mcpBase;
    @Autowired
    private ShareInnerService shareInnerService;

    @Autowired
    private UrlCheckUtils urlCheckUtils;
    /**
     * 服务列表
     *
     */
    public McpServerBaseInfoListResp listServers(String projectId, ListServersQo listServersQo) {
        log.info("operation log {}:start to query mcp server list", projectId);
        commonService.validSearchNameStartWithChineseEnglishLettersNumber(listServersQo.getName());

        String tenantId = RequestContextUtils.getRequestUserDomainId();


        if (StringUtils.isNotBlank(listServersQo.getLanguage()) && !Arrays.stream(LANGUAGE.values())
            .map(LANGUAGE::name)
            .toList()
            .contains(listServersQo.getLanguage())) {
            log.error("language is not in EN/ZH or null.");
            McpServiceExceptionUtils.throwMissingParameterError("language");
        }

        log.info("Initializing response object.");
        McpServerBaseInfoListResp resp = new McpServerBaseInfoListResp();

        String orgType = null;
        if (hasHcsMcpSwitch) {
            log.info("HCS MCP switch is on. Setting orgType to SSE.");
            orgType = EnumOrgType.SSE.getValue();
        }

        log.info("Querying MCP server entities with filters.");
        List<McpServerEntity> mcpServerEntities = getMcpServer(listServersQo.getLanguage(), listServersQo.getName(), listServersQo.getLimit(), listServersQo.getOffset(), tenantId, orgType, listServersQo.getCategory());

        log.info("Querying total count of MCP servers.");
        long total = this.serverDao.queryServerWithPageCount(CommonUtil.getTenantId(), listServersQo.getName(), listServersQo.getLanguage(), orgType, listServersQo.getCategory());
        resp.setTotal(total);
        if (CollectionUtils.isEmpty(mcpServerEntities)) {
            log.info("No MCP servers found. Returning empty response.");
            resp.setMcps(Collections.emptyList());
            return resp;
        }

        log.info("Querying server scores.");
        List<ServerScore> serverScores = this.mcpServerRatingDao.queryScoreAllServer();

        log.info("Mapping server entities to DTOs and calculating scores.");
        resp.setMcps(mcpServerEntities.stream().map(server -> {
            McpServerBaseInfoDto mcpServerBaseInfoDto = mcpUtil.serverEntity2McpBaseInfoDto(server);
            double avgScore = calculatedScore(mcpServerBaseInfoDto.getId(), serverScores);
            mcpServerBaseInfoDto.setScore(avgScore);
            return mcpServerBaseInfoDto;
        }).toList());

        log.info("MCP server list query completed. Total: {}", resp.getTotal());
        return resp;
    }

    private List<McpServerEntity> getMcpServer(String language, String name, int limit, int offset, String tenantId,
        String orgType, String category) {
        List<McpServerEntity> infos;

        log.info("Pagination parameters: limit = {}, offset = {}", limit, offset);

        if (limit < 0) { // 校验 limit 是否为正数
            log.warn("Invalid limit value: {}. Limit must be a non-negative number.", limit);
            throw new AgentStudioException(StudioError.ILLEGAL_API_INVOKE);
        }
        if (offset < 0) { // 偏移量不能为负数
            log.warn("Invalid offset value: {}. Offset must be a non-negative number.", offset);
            throw new AgentStudioException(StudioError.ILLEGAL_API_INVOKE);
        }
        infos = serverDao.queryServerWithPage(offset, limit, tenantId, name, language, orgType, category);
        return infos;
    }

    private double calculatedScore(String serverId, List<ServerScore> serverScores) {
        log.info("Calculating score for server ID: {}", serverId);
        if (serverScores == null || CollectionUtils.isEmpty(serverScores)) {
            log.warn("Server scores list is null or empty. Using default score.");
            return DEFAULT_SCORES;
        }
        log.info("Filtering server score by server ID.");
        Optional<ServerScore> first = serverScores.stream()
            .filter(score -> Strings.CI.equals(score.getServerId(), serverId))
            .findFirst();
        return first.map(serverScore -> BigDecimal.valueOf(serverScore.getTotalScore())
            .divide(BigDecimal.valueOf(serverScore.getTimes()), 0, RoundingMode.HALF_UP)
            .doubleValue()).orElse(DEFAULT_SCORES);
    }

    /**
     * 已兼容hcs下沉场景  hcs场景只展示sse方式部署的mcp服务
     *
     */
    public McpServiceBaseInfoListResp listServices(String projectId, String workspaceId, String language, String name,
        String fcInstanceStatus, String nodeType, String visibility, PageInfoV2 pageInfo) {
        log.info("operation log {}:start to query mcp service list", projectId);
        commonService.validSearchNameStartWithChineseEnglishLettersNumber(name);
        String tenantId = RequestContextUtils.getRequestUserDomainId();
        CommonUtil.validatePageInfo(pageInfo);
        CommonUtil.validateProjectAndWorkspaceId(projectId, workspaceId);
        String orgType = hasHcsMcpSwitch ? EnumOrgType.SSE.getValue() : null;
        nodeType = StringUtils.isEmpty(nodeType) ? McpNodeType.Mcp.getValue() : nodeType;
        log.info("Querying service entities with parameters.");
        List<McpServiceEntity> infos = this.serviceDao.selectServiceWithPage(pageInfo.getOffset(), pageInfo.getLimit(),
            (StringUtils.isNotBlank(name) && LANGUAGE.ZH.name().equals(language)) ? name : null,
            StringUtils.isNotBlank(name) && LANGUAGE.EN.name().equals(language) ? name : null, tenantId,
            CommonUtil.getDeptCode(), orgType,  workspaceId, fcInstanceStatus, nodeType, visibility);
        log.info("Querying total count.");
        long total = this.serviceDao.selectServiceWithPageCount(
            (StringUtils.isNotBlank(name) && LANGUAGE.ZH.name().equals(language)) ? name : null,
            StringUtils.isNotBlank(name) && LANGUAGE.EN.name().equals(language) ? name : null, tenantId,
            CommonUtil.getDeptCode(), orgType,  workspaceId, fcInstanceStatus, nodeType, visibility);
        return buildMcpServiceListRep(infos, total);
    }

    /**
     * 已兼容hcs下沉场景  hcs场景只展示sse方式部署的mcp服务
     *
     */
    public McpServiceBaseInfoListResp listServicesWithRuntimeInfo(String projectId, String workspaceId, String language,
        String name, PageInfoV2 pageInfo) {
        log.info("operation log {}:start to query mcp service list", projectId);
        String tenantId = RequestContextUtils.getRequestUserDomainId();
        CommonUtil.validatePageInfo(pageInfo);
        CommonUtil.validateProjectAndWorkspaceId(projectId, workspaceId);
        String orgType = hasHcsMcpSwitch ? EnumOrgType.SSE.getValue() : null;
        log.info("Querying service entities with runtime info.");
        List<McpServiceEntity> infos = this.serviceDao.selectServiceWithPage(pageInfo.getOffset(), pageInfo.getLimit(),
            (StringUtils.isNotBlank(name) && LANGUAGE.ZH.name().equals(language)) ? name : null,
            StringUtils.isNotBlank(name) && LANGUAGE.EN.name().equals(language) ? name : null, tenantId,
            CommonUtil.getDeptCode(), orgType, workspaceId, SUCCESS.getValue(), McpNodeType.Mcp.getValue(), null);
        log.info("Querying total count of services with runtime info.");
        long total = this.serviceDao.selectServiceWithPageCount(
            (StringUtils.isNotBlank(name) && LANGUAGE.ZH.name().equals(language)) ? name : null,
            StringUtils.isNotBlank(name) && LANGUAGE.EN.name().equals(language) ? name : null, tenantId,
            CommonUtil.getDeptCode(), orgType, workspaceId, SUCCESS.getValue(), McpNodeType.Mcp.getValue(), null);
        return buildMcpServiceListRepForRuntime(infos, total);
    }

    /**
     * 查询mcp列表
     *
     */
    public List<McpServiceSkinnyEntity> queryMcpListByIds(String projectId, String workspaceId, List<String> ids) {
        log.info("operation log {}:start to query mcp list by ids", projectId);
        String tenantId = RequestContextUtils.getRequestUserDomainId();
        if (CollectionUtils.isEmpty(ids)) {
            log.error("mcp ids is not null.");
            McpServiceExceptionUtils.throwMissingParameterError("ids");
        }
        List<McpServiceEntity> mcpServiceEntities = serviceDao.listMcpServiceByIdAndTenant(ids, tenantId,
            CommonUtil.getDeptCode(),  workspaceId);

        return mcpServiceEntities.stream().map(mcp -> {
            McpServiceSkinnyEntity serviceSkinny;

            // 增加对 STREAMABLE_HTTP 的判断
            if (Strings.CI.equals(mcp.getOrgType(), EnumOrgType.SSE.getValue()) ||
                Strings.CI.equals(mcp.getOrgType(), EnumOrgType.STREAMABLE_HTTP.getValue())) {

                // SSE 和 Streamable HTTP 逻辑一致：直接转换，不需要特殊处理 URL 后缀
                serviceSkinny = mcpUtil.serviceEntity2ServiceEntitySkinny(mcp);
                serviceSkinny.setFcInstanceUrl(serviceSkinny.getFcInstanceUrl());
                serviceSkinny.setServerConfig(encryptionAdapter.decrypt(serviceSkinny.getServerConfig()));
            } else {
                // NPX / UVX 逻辑 (保持不变)
                String baseUrl;
                if (mcp.getFcInstanceUrl().endsWith("/")) {
                    baseUrl = StringUtils.join(mcp.getFcInstanceUrl(), "sse");
                } else {
                    baseUrl = StringUtils.join(mcp.getFcInstanceUrl(), "/sse");
                }
                mcp.setFcInstanceUrl(baseUrl);
                serviceSkinny = mcpUtil.serviceEntity2ServiceEntitySkinny(mcp);
                serviceSkinny.setServerConfig(
                    mcpUtil.deleteAuthHeadersFromMcpServer(encryptionAdapter.decrypt(serviceSkinny.getServerConfig())));
            }

            McpServerEntity mcpServerEntity = this.serverDao.selectById(mcp.getServerId());
            if (mcpServerEntity != null) {
                serviceSkinny.setIcon(mcpServerEntity.getIcon());
            }
            return serviceSkinny;
        }).collect(Collectors.toList());
    }

    private McpServiceBaseInfoListResp buildMcpServiceListRepForRuntime(List<McpServiceEntity> infos, long total) {
        log.info("Building MCP service list response with runtime info. Total: {}", total);

        McpServiceBaseInfoListResp resp = new McpServiceBaseInfoListResp();
        resp.setTotal(total).setMcps(infos.stream().map(info -> {
            McpServiceBaseInfoDto mcpServiceBaseInfoDto;
            mcpServiceBaseInfoDto = mcpUtil.serviceEntity2McpBaseRuntimeInfoDto(info);

            log.info("Querying server entity for service ID: {}", info.getServerId());
            McpServerEntity mcpServerEntity = this.serverDao.selectById(info.getServerId());

            if (mcpServerEntity != null) {
                mcpServiceBaseInfoDto.setViewTimes(mcpServerEntity.getViewTimes());
                mcpServiceBaseInfoDto.setInstallTimes(mcpServerEntity.getInstallTimes());
                mcpServiceBaseInfoDto.setType(mcpServerEntity.getType());
                mcpServiceBaseInfoDto.setIcon(mcpServerEntity.getIcon());
            }

            return mcpServiceBaseInfoDto;
        }).toList());

        return resp;
    }

    private McpServiceBaseInfoListResp buildMcpServiceListRep(List<McpServiceEntity> infos, long total) {
        log.info("Building MCP service list response. Total: {}", total);

        McpServiceBaseInfoListResp resp = new McpServiceBaseInfoListResp();
        resp.setTotal(total).setMcps(infos.stream().map(info -> {
            McpServiceBaseInfoDto mcpServiceBaseInfoDto;
            mcpServiceBaseInfoDto = mcpUtil.serviceEntity2McpBaseInfoDto(info);
            // 初始化MCP来源是自定义
            mcpServiceBaseInfoDto.setResource("custom");
            log.info("Querying server entity for service ID: {}", info.getServerId());
            McpServerEntity mcpServerEntity = this.serverDao.selectById(info.getServerId());

            if (mcpServerEntity != null) {
                mcpServiceBaseInfoDto.setViewTimes(mcpServerEntity.getViewTimes());
                mcpServiceBaseInfoDto.setInstallTimes(mcpServerEntity.getInstallTimes());
                mcpServiceBaseInfoDto.setType(mcpServerEntity.getType());
                //如果是官方预置模板，修改来源类型
                mcpServiceBaseInfoDto.setResource("inner");
                if (StringUtils.isBlank(mcpServiceBaseInfoDto.getIcon())) {
                    mcpServiceBaseInfoDto.setIcon(mcpServerEntity.getIcon());
                }
            }
            // 第三方来源的MCP类型
            if (StringUtils.isNotBlank(info.getThirdResource())) {
                mcpServiceBaseInfoDto.setResource(info.getThirdResource());
            }
            mcpServiceBaseInfoDto.setAuthInfo(mcpBase.anonymizeAuthInfo(info.getAuthInfo()));
            return mcpServiceBaseInfoDto;
        }).toList());

        return resp;
    }

    /**
     * 查询服务详情
     *
     */
    public McpServerDetailInfoDto queryServerDetail(String projectId, String workspaceId, String serverId) {
        log.info("operation log {}:start to query mcp server detail", projectId);
        String tenantId = RequestContextUtils.getRequestUserDomainId();


        McpServerEntity serverEntity = serverDao.selectById(serverId);
        if (serverEntity == null) {
            log.info("Server not found. Server ID: {}", serverId);
            return new McpServerDetailInfoDto();
        }

        if ("private".equals(serverEntity.getType())) {
            if (!RequestContextUtils.getRequestUserDomainId().equals(serverEntity.getTenantId())
                || !CommonUtil.getDeptCode().equals(serverEntity.getDeptCode())) {
                log.error("get server's detail rejected. server is {}, belong to {}, but current tenant is {}",
                    serverId, serverEntity.getTenantId(), RequestContextUtils.getRequestUserDomainId());
                McpServiceExceptionUtils.throwUserNoPermissionError();
            }
        }

        McpServerDetailInfoDto mcpServerDetailInfoDto = mcpUtil.serverEntity2McpServerDetailInfoDto(serverEntity);
        log.info("Converted server entity to DTO. Server ID: {}", serverId);

        mcpUpdateTaskExecutor.execute(() -> this.mcpUpdateTask.updateServerViewCount(serverId));
        log.info("Scheduled view count update for server ID: {}", serverId);

        ServerScore serverScores = this.mcpServerRatingDao.queryScoreByServerIdAndTenantId(
            mcpServerDetailInfoDto.getId(), tenantId);
        List<ServerScore> serverAvgScores = this.mcpServerRatingDao.queryScoreByServerId(serverId);

        mcpServerDetailInfoDto.setScore((double) (serverScores == null ? 0 : serverScores.getTotalScore()));
        mcpServerDetailInfoDto.setScoreAvg(calculatedScore(serverId, serverAvgScores));

        log.info("Server detail query completed. Server ID: {}", serverId);
        return mcpServerDetailInfoDto;
    }

    @Override
    public McpServiceDetailInfoDto queryServiceDetail(String projectId, String workspaceId, String serviceId) {
        log.info("Operation log: Start to query MCP service detail. Project ID: {}", projectId);

        String tenantId = RequestContextUtils.getRequestUserDomainId();

        McpServiceEntity serviceEntity = serviceDao.selectById(serviceId, tenantId, CommonUtil.getDeptCode(), workspaceId);
        if (serviceEntity == null) {
            log.warn("MCP service not found. Service ID: {}", serviceId);
            throw new AgentStudioException(StudioError.MCP_SERVICE_NOT_EXIST);
        }

        // 鉴权信息做******处理
        serviceEntity.setAuthInfo(mcpBase.anonymizeAuthInfo(serviceEntity.getAuthInfo()));
        McpServiceDetailInfoDto mcpServiceDetailInfoDto = mcpUtil.serviceEntity2McpServiceDetailInfoDto(serviceEntity);
        log.info("Converted service entity to DTO. Service ID: {}", serviceId);

        mcpServiceDetailInfoDto.setServerConfig(encryptionAdapter.decrypt(mcpServiceDetailInfoDto.getServerConfig()));

        log.info("Server config decrypted for service ID: {}", serviceId);

        if (!Strings.CI.equals(mcpServiceDetailInfoDto.getOrgType(), EnumOrgType.SSE.getValue()) &&
                !Strings.CI.equals(mcpServiceDetailInfoDto.getOrgType(), EnumOrgType.STREAMABLE_HTTP.getValue())) {
            log.info("Removing auth headers from server config for non-SSE service. Service ID: {}", serviceId);
            // 非 SSE 且 非 Streamable HTTP (即 NPX/UVX) 才需要清除 headers
            mcpServiceDetailInfoDto.setServerConfig(
                    mcpUtil.deleteAuthHeadersFromMcpServer(mcpServiceDetailInfoDto.getServerConfig()));
        }

        mcpServiceDetailInfoDto.setTools(null);
        log.info("Set tools to null for service ID: {}", serviceId);

        McpServerEntity mcpServerEntity = this.serverDao.selectById(serviceEntity.getServerId());
        if (mcpServerEntity == null) {
            log.warn("Server entity not found for service ID: {}", serviceId);
            return mcpServiceDetailInfoDto;
        }

        if (StringUtils.isBlank(mcpServiceDetailInfoDto.getIcon())) {
            mcpServiceDetailInfoDto.setIcon(mcpServerEntity.getIcon());
            log.info("Icon copied from server entity for service ID: {}", serviceId);
        }

        mcpServiceDetailInfoDto.setType(mcpServerEntity.getType());
        log.info("Service type set from server entity for service ID: {}", serviceId);

        return mcpServiceDetailInfoDto;
    }

    /**
     * 运行时查询mcp服务详情
     *
     */
    public McpServiceDetailInfoDto queryServiceDetailForRuntime(String projectId, String workspaceId,
        String serviceId) {
        log.info("operation log {}:start to query mcp service detail for runtime", projectId);
        String tenantId = RequestContextUtils.getRequestUserDomainId();

        McpServiceEntity serviceEntity = serviceDao.selectById(serviceId, tenantId, CommonUtil.getDeptCode(), workspaceId);
        if (serviceEntity == null) {
            log.warn("MCP service not found. Service ID: {}", serviceId);
            throw new AgentStudioException(StudioError.MCP_SERVICE_NOT_EXIST);
        }

        McpServiceDetailInfoDto mcpServiceDetailInfoDto = mcpUtil.serviceEntity2McpServiceRuntimeDetailInfoDto(serviceEntity);
        log.info("Converted service entity to runtime DTO. Service ID: {}", serviceId);

        McpServerEntity mcpServerEntity = this.serverDao.selectById(serviceEntity.getServerId());
        if (mcpServerEntity == null) {
            log.warn("Server entity not found for service ID: {}", serviceId);
            return mcpServiceDetailInfoDto;
        }

        mcpServiceDetailInfoDto.setIcon(mcpServerEntity.getIcon());
        mcpServiceDetailInfoDto.setType(mcpServerEntity.getType());
        log.info("Icon and type copied from server entity for service ID: {}", serviceId);

        mcpServiceDetailInfoDto.setServerConfig(encryptionAdapter.decrypt(mcpServiceDetailInfoDto.getServerConfig()));
        log.info("Server config decrypted for service ID: {}", serviceId);
        if (!Strings.CI.equals(mcpServiceDetailInfoDto.getOrgType(), EnumOrgType.SSE.getValue()) &&
            !Strings.CI.equals(mcpServiceDetailInfoDto.getOrgType(), EnumOrgType.STREAMABLE_HTTP.getValue())) {
            // 非 SSE 且 非 Streamable HTTP 才清除 headers
            mcpServiceDetailInfoDto.setServerConfig(
                mcpUtil.deleteAuthHeadersFromMcpServer(mcpServiceDetailInfoDto.getServerConfig()));
        }

        return mcpServiceDetailInfoDto;
    }

    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "McpService",
        description = "批量部署MCP服务",
        resourceId = "-1",
        resourceName = "body.servers[0].name"
    )
    public McpServiceBatchDeployResp batchDeployServices(String projectId, String workspaceId, String resource,
        McpServiceBatchDeployReq body) {
        log.info("Operation log {}: Start to batch deploy MCP services. Project ID: {}", projectId, projectId);
        String tenantId = RequestContextUtils.getRequestUserDomainId();
        McpServiceBatchDeployResp mcpServiceBatchDeployResp = new McpServiceBatchDeployResp();
        mcpServiceBatchDeployResp.setTotalCount(body.getServers().size());
        mcpServiceBatchDeployResp.setResults(new ArrayList<>());
        mcpServiceBatchDeployResp.setFailedCount(0);
        mcpServiceBatchDeployResp.setSuccessCount(0);

        for (McpServiceBatchDeployItem mcpService :body.getServers()) {
            try {
                log.info("Service config format validated. {}", mcpService.getName());
                CommonUtil.validateMcpConfigFormat(mcpService.getServerConfig());

                if (!Strings.CI.equals(mcpService.getOrgType(), EnumOrgType.SSE.toString()) &&
                    !Strings.CI.equals(mcpService.getOrgType(), EnumOrgType.STREAMABLE_HTTP.toString())) {
                    log.warn("Non SSE or streamable_http service detected. Service name: {}", mcpService.getName());
                    throw new AgentStudioException(StudioError.ONLY_SSE_OR_STREAMABLE_HTTP_SERVICE_ALLOWED_THIRD);
                }

                JSONObject jsonObject = JSONObject.parseObject(mcpService.getServerConfig());
                String url = removeQueryParamsFromUrl(CommonUtil.parseUrlFromMcpConfig(jsonObject, 0));
                checkSwaggerUrlValid(url, connectorConfigHostBlacklist);
                String icon;
                if (resource.equals(ROMA_RESOURCE_NAME)) {
                    icon = mcpService.getIcon();
                } else {
                    icon = getBase64Icon(mcpService.getIcon());
                }
                try {
                    log.info("Validating service icon.");
                    ImageBase64Utils.validateImage(icon);
                } catch (Exception e) {
                    icon = mcpDefaultIcon;
                }
                McpServiceDetailInfoDto serviceDetail = mcpUtil.thirdService2McpServiceDetailInfoDto(mcpService, resource);
                log.info("Converted service request to detail DTO. Service name: {}", serviceDetail.getName());
                log.info("Start creating new service.");

                Map<String, String> params = new HashMap<>();
                params.put(TENANT_ID, tenantId);
                params.put("projectId", projectId);
                params.put("workspaceId", workspaceId);
                params.put("serverId", null);

                String serviceId = insertMcp(serviceDetail, params, icon);
                serviceDetail.setId(serviceId);

                log.info("Standard deployment for server ID: {}. Service ID: {}", null, serviceId);
                mcpDeployment(serviceDetail, null, serviceId);
                mcpServiceBatchDeployResp.setSuccessCount(mcpServiceBatchDeployResp.getSuccessCount() + 1);
                McpDeployResult mcpDeployResult = new McpDeployResult();
                mcpDeployResult.setId(serviceId);
                mcpDeployResult.setOriginId(mcpService.getThirdId());
                mcpDeployResult.setName(mcpService.getName());
                mcpDeployResult.setStatus(McpDeployResult.StatusEnum.SUCCESS);
                mcpServiceBatchDeployResp.getResults().add(mcpDeployResult);
            } catch (AgentStudioException e) {
                McpDeployResult mcpDeployResult = new McpDeployResult();
                mcpDeployResult.setOriginId(mcpService.getThirdId());
                mcpDeployResult.setName(mcpService.getName());
                mcpDeployResult.setStatus(McpDeployResult.StatusEnum.FAILED);
                mcpDeployResult.setErrorMessage(i18nUtil.getMessage(e.getErrorCode()));
                mcpDeployResult.setErrorCode(e.getErrorCode().getCode());
                mcpServiceBatchDeployResp.setFailedCount(mcpServiceBatchDeployResp.getFailedCount() + 1);
                mcpServiceBatchDeployResp.getResults().add(mcpDeployResult);
            } catch (Exception e) {
                McpDeployResult mcpDeployResult = new McpDeployResult();
                mcpDeployResult.setOriginId(mcpService.getThirdId());
                mcpDeployResult.setName(mcpService.getName());
                mcpDeployResult.setStatus(McpDeployResult.StatusEnum.FAILED);
                mcpDeployResult.setErrorMessage("deploy failed!!!");
                mcpServiceBatchDeployResp.setFailedCount(mcpServiceBatchDeployResp.getFailedCount() + 1);
                mcpServiceBatchDeployResp.getResults().add(mcpDeployResult);
            }
        }

        return mcpServiceBatchDeployResp;
    }

    public String getBase64Icon(String iconUrl) {
        log.info("get icon from url: {}", iconUrl);
        if (StringUtils.isBlank(iconUrl)) {
            return mcpDefaultIcon;
        }
        try {
            Request request = new Request.Builder().url(iconUrl).get().build();
            Response response = okHttpClientUtils.getHttpClient().newCall(request).execute();
            if (response.isSuccessful() && response.body() != null) {
                byte[] bytes = response.body().bytes();
                return Base64.getEncoder().encodeToString(bytes);
            }
        } catch (Exception e) {
            log.error("Failed to obtain the icon: {}", e.getMessage());
        }
        return mcpDefaultIcon;
    }
    /**
     * 内置mcp服务资产
     *
     */
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "McpService",
        description = "创建MCP服务",
        resourceId = "-1",
        resourceName = "serverDetail.name"
    )
    public String createServer(String projectId, String workspaceId, McpServerDetailReq serverDetail) {
        log.info("operation log {}:start to create mcp server", projectId);
        CommonUtil.validateTenantIdIsNotEmpty();

        // 构建实体
        McpServerEntity serverEntity = mcpUtil.mcpDetailInfoDto2ServerEntity(serverDetail);

        // 插入数据库
        serverDao.insert(serverEntity);
        return serverEntity.getId();
    }

    /**
     * 安装MCP
     * 调用function graph能力
     *
     * @param serviceDeployReq 部署的服务实例详情
     * @return 返回实例id
     */
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "McpService",
        description = "部署MCP服务",
        resourceId = "serverId",
        resourceName = ""
    )
    public String deploy(String projectId, String workspaceId, String serverId, McpServiceDeployReq serviceDeployReq) {
        log.info("operation log {}:start to deploy mcp service", projectId);
        if (StringUtils.isBlank(serviceDeployReq.getOrgType()) ) {
            log.error("orgType is invalid: {}", serviceDeployReq.getOrgType());
            throw new AgentStudioException(StudioError.MCP_SERVICE_ORG_TYPE_EMPTY,serviceDeployReq.getOrgType());
        }
        try {
            // STREAMABLE_HTTP("streamable_http")没办法直接用EnumOrgType.valueOf(mcpServiceFromDb.getOrgType());所以加了if，是streamable_http跳过
            // 判断类型只能是SSE,UVX,NPX,streamable_http
            if (!Strings.CI.equals(serviceDeployReq.getOrgType(), EnumOrgType.STREAMABLE_HTTP.getValue())) {
                EnumOrgType.valueOf(serviceDeployReq.getOrgType());
            }
        } catch (IllegalArgumentException e) {
            log.error("orgType is invalid: {}", serviceDeployReq.getOrgType());
            throw new AgentStudioException(StudioError.MCP_SERVICE_ORG_TYPE_INVALID,serviceDeployReq.getOrgType());
        }
        if (serviceDeployReq.getName().length() > 64 || !NAME_PATTERN.matcher(serviceDeployReq.getName()).matches()) {
            log.error("service name is invalid: {}", serviceDeployReq.getName());
            throw new AgentStudioException(StudioError.MCP_SERVICE_NAME_INVALID);
        }

        if (!SERVICE_CONFIG_PATTERN.matcher(serviceDeployReq.getServerConfig()).matches()) {
            log.error("service config is invalid: {}", serviceDeployReq.getServerConfig());
            throw new AgentStudioException(StudioError.MCP_SERVICE_CONFIG_INVALID);
        }

        String tenantId = RequestContextUtils.getRequestUserDomainId();

        // 捕获 JSON 格式校验异常，抛出明确错误码 (1146)
        try {
            CommonUtil.validateMcpConfigFormat(serviceDeployReq.getServerConfig());
        } catch (AgentStudioException e) {
            // 如果是业务异常 (1151 或 1146)，直接抛出，不要包装！
            throw e;
        } catch (Exception e) {
            // 只有未知的运行时异常，才报 "格式错误"
            log.error("MCP config format validation failed", e);
            throw new AgentStudioException(StudioError.MCP_CONFIG_FORMAT_INVALID);
        }
        log.info("Service config format validated.");

        if (Strings.CI.equals(serviceDeployReq.getOrgType(), EnumOrgType.SSE.toString()) ||
            Strings.CI.equals(serviceDeployReq.getOrgType(), EnumOrgType.STREAMABLE_HTTP.toString())) {
            JSONObject jsonObject = JSONObject.parseObject(serviceDeployReq.getServerConfig());
            String url = removeQueryParamsFromUrl(CommonUtil.parseUrlFromMcpConfig(jsonObject, 0));
            urlCheckUtils.checkUrl(null, url);
            checkSwaggerUrlValid(url, connectorConfigHostBlacklist);
        }
        if (StringUtils.isNotBlank(serviceDeployReq.getIcon())) {
            log.info("Validating service icon.");
            ImageBase64Utils.validateImage(serviceDeployReq.getIcon());
        }

        mcpBase.validAuthInfo(serviceDeployReq.getAuthInfo());

        // authInfo信息加密
        serviceDeployReq.setAuthInfo(mcpBase.encryptedAuthInfo(serviceDeployReq.getAuthInfo()));

        McpServiceDetailInfoDto serviceDetail = mcpUtil.serviceReq2McpServiceDetailInfoDto(serviceDeployReq);
        log.info("Converted service request to detail DTO. Service name: {}", serviceDeployReq.getName());

        // 定义 serviceId 变量，用于异常捕获时的状态回滚
        String serviceId = serviceDeployReq.getId();

        try {
            McpServiceEntity mcpServiceById = this.serviceDao.getMcpServiceOnlyById(serviceId);
            // 数据库操作（新增或更新）
            // 如果ID为空或者表中不存在这个ID，直接插入
            // 如果ID不为空，且该ID不是该用户创建的，提示无权限操作；如果ID原本是这个用户创建的且未被删除，更新（已删除的MCP不可再次被创建）
            if (StringUtils.isNotBlank(serviceId) && mcpServiceById != null) {
                log.info("Updating existing service. Service ID: {}", serviceId);

                McpServiceEntity mcpServiceByIdAndTenantDeptCode = this.serviceDao.getMcpServiceByIdAndTenantDeptCode(
                    serviceId, tenantId, workspaceId);
                if (mcpServiceByIdAndTenantDeptCode == null) {
                    log.warn("No permission to update service. Service ID: {}", serviceId);
                    throw new AgentStudioException(StudioError.NO_PERMISSION_FOR_MCP);
                }
                // updateMcp 方法已修改，会将状态置为 CREATING_STACK
                updateMcp(serviceDetail, tenantId, projectId, workspaceId);
            } else {
                log.info("Creating new service.");

                Map<String, String> params = new HashMap<>();
                params.put(TENANT_ID, tenantId);
                params.put("projectId", projectId);
                params.put("workspaceId", workspaceId);
                params.put("serverId", serverId);
                serviceId = insertMcp(serviceDetail, params, serviceDeployReq.getIcon());
                serviceDetail.setId(serviceId);
            }

            String functionName = StringUtils.join("agentBuilder-mcp-" + serviceDetail.getId());
            serviceDetail.setFunctionApplicationName(functionName);
            log.info("Set function application name to: {}", functionName);

            // 执行基础设施部署
            String deploymentResultId;
            if (Strings.CI.equals("1", serverId)) {
                log.info("Custom deployment for server ID 1. Service ID: {}", serviceId);
                deploymentResultId = customMcpDeployment(serviceDetail, serviceId);
            } else {
                log.info("Standard deployment for server ID: {}. Service ID: {}", serverId, serviceId);
                deploymentResultId = mcpDeployment(serviceDetail, serverId, serviceId);
            }

            // 异步触发工具获取与状态终结
            // 只有 NPX 和 UVX 需要在这里触发异步任务。
            // SSE 和 STREAMABLE_HTTP 已经在上面的 mcpDeployment/customMcpDeployment 方法内部触发了自己的专用异步任务。
            boolean isStreamableOrSse = Strings.CI.equals(serviceDetail.getOrgType(), EnumOrgType.SSE.toString()) ||
                Strings.CI.equals(serviceDetail.getOrgType(), EnumOrgType.STREAMABLE_HTTP.toString()) ||
                Strings.CI.equals(serviceDetail.getOrgType(), EnumOrgType.SSE.getValue()) ||
                Strings.CI.equals(serviceDetail.getOrgType(), EnumOrgType.STREAMABLE_HTTP.getValue());

            if (!isStreamableOrSse) {
                log.info("Starting generic async tool fetch for NPX/UVX service: {}", serviceId);
                String finalServiceId = serviceId;
                String authToken = RequestContextUtils.getRequestAuthToken(); // 获取当前线程Token传递给异步线程

                mcpTaskExecutor.execute(() -> {
                    try {
                        // 设置异步线程上下文
                        RequestContextUtils.setContext(authToken, projectId, tenantId);
                        // 查询最新实体信息
                        McpServiceEntity latestEntity = serviceDao.getMcpServiceById(finalServiceId, tenantId, CommonUtil.getDeptCode(), projectId, workspaceId);
                        if (latestEntity != null) {
                            log.info("Async tool fetch started for service: {}", finalServiceId);
                            // 核心方法：获取工具 -> 成功则SUCCESS / 失败则STACK_FAIL
                            this.getMcpServiceToolListAndUpdateStatus(latestEntity);
                        }
                    } catch (Throwable t) {
                        log.error("Async tool fetch failed after deploy for service: {}", finalServiceId, t);
                        // 异步线程内兜底：确保异常时状态置为失败
                        try {
                            serviceDao.updateStatus(finalServiceId, EnumMcpStatus.STACK_FAIL.getValue(),
                                tenantId, CommonUtil.getDeptCode());
                        } catch (Exception ex) {
                            log.error("Failed to update status to FAIL in async thread", ex);
                        }
                    }
                });
            } else {
                log.info("Skipping generic async tool fetch for Streamable/SSE service: {} (Handled internally)", serviceId);
            }
            return deploymentResultId;

        } catch (AgentStudioException e) {
            // 同步部署异常处理 - 处理 AgentStudioException 特定异常
            // 如果上述流程报错（如 updateMcp 成功但 mcpDeployment 失败），必须将状态回滚为 STACK_FAIL
            log.error("Deploy failed synchronously for service: {}", serviceId, e);

            if (StringUtils.isNotBlank(serviceId)) {
                // 直接获取异常中的错误码
                StudioError studioError = e.getErrorCode();

                // 复用通用的错误处理逻辑写入数据库
                McpServiceEntity errorEntity = new McpServiceEntity();
                errorEntity.setId(serviceId);
                errorEntity.setTenantId(tenantId);
                handleExceptionWithError(errorEntity, e, studioError);
            }
            throw e;
        } catch (Exception e) {
            // 同步部署异常处理 - 处理其他通用异常
            // 如果上述流程报错（如 updateMcp 成功但 mcpDeployment 失败），必须将状态回滚为 STACK_FAIL
            log.error("Deploy failed synchronously for service: {}", serviceId, e);

            if (StringUtils.isNotBlank(serviceId)) {
                // 设置默认错误码
                StudioError studioError = StudioError.MCP_CONFIG_FORMAT_INVALID;

                // 复用通用的错误处理逻辑写入数据库
                McpServiceEntity errorEntity = new McpServiceEntity();
                errorEntity.setId(serviceId);
                errorEntity.setTenantId(tenantId);
                handleExceptionWithError(errorEntity, e, studioError);
            }
            throw e;
        }
    }

    /**
     * 更新mcp
     *
     */
    public synchronized String updateMcp(McpServiceDetailInfoDto serviceDetail, String tenantId, String projectId,
        String workspaceId) {
        long mcpServiceCount = this.serviceDao.getMcpServiceCountByTenantId(tenantId);
        log.info("Current service count for tenant {}: {}", tenantId, mcpServiceCount);

        if (mcpServiceCount >= Long.parseLong(mcpQuota)) {
            log.warn("Service count exceeds quota. Current: {}, Quota: {}", mcpServiceCount, mcpQuota);
            throw new AgentStudioException(StudioError.SERVICE_EXCEEDING_LIMIT);
        }

        McpServiceEntity serviceEntity = mcpUtil.mcpServiceDetailInfoDto2ServiceEntity(serviceDetail, workspaceId);
        log.info("Converted service detail DTO to entity. Service ID: {}", serviceDetail.getId());

        // ServerConfig可能含有敏感信息，此处加密处理，读取时需要解密
        serviceEntity.setServerConfig(encryptionAdapter.encrypt(serviceDetail.getServerConfig(), RequestContextUtils.getRequestUserDomainId()));
        log.info("Server config encrypted for service ID: {}", serviceDetail.getId());

        serviceEntity.setOrgType(serviceDetail.getOrgType());

        if (Strings.CS.equals(serviceDetail.getOrgType(), EnumOrgType.SSE.getValue())) {
            serviceEntity.setDeployType("sse");
            serviceEntity.setFcInstanceUrl(removeQueryParamsFromUrl(
                CommonUtil.parseUrlFromMcpConfig(JSONObject.parseObject(serviceDetail.getServerConfig()), 0)));
        } else if (Strings.CI.equals(serviceDetail.getOrgType(), EnumOrgType.STREAMABLE_HTTP.getValue())) {
            // 新增 Streamable HTTP 更新逻辑
            serviceEntity.setDeployType("streamable_http");
            // 复用 URL 解析逻辑
            serviceEntity.setFcInstanceUrl(removeQueryParamsFromUrl(
                CommonUtil.parseUrlFromMcpConfig(JSONObject.parseObject(serviceDetail.getServerConfig()), 0)));
        } else if (Strings.CS.equals(serviceDetail.getOrgType(), EnumOrgType.NPX.getValue()) || Strings.CS.equals(
            serviceDetail.getOrgType(), EnumOrgType.UVX.getValue())) {
            serviceEntity.setDeployType("stdio");

            // NPX\UVX部署到FG，并注册到APIG，调用需要认证，刷新MCP的认证信息到ServerConfig
            log.info("Inserting auth headers into server config for service ID: {}", serviceDetail.getId());
            serviceEntity.setServerConfig(
                encryptionAdapter.encrypt(mcpUtil.insertAuthHeadersIntoMcpServer(serviceDetail.getServerConfig()), RequestContextUtils.getRequestUserDomainId()));
        }

        // 状态不要直接设为 SUCCESS，改为 CREATING_STACK
        // 这样前端会显示 loading 动画，直到异步任务更新为 SUCCESS 或 FAIL
        serviceEntity.setFcInstanceStatus(EnumMcpStatus.CREATING_STACK.getValue());
        // 重试部署时，清空之前的失败原因
        serviceEntity.setFailReason("");
        serviceEntity.setTenantId(tenantId);
        serviceEntity.setProjectId(projectId);



        log.info("Updating service entity. Service ID: {}", serviceEntity.getId());
        serviceDao.update(serviceEntity);

        return serviceEntity.getId();
    }

    /**
     * mcp信息入库
     *
     */
    public synchronized String insertMcp(McpServiceDetailInfoDto serviceDetail, Map<String, String> params, String icon) {
        long mcpServiceCount = this.serviceDao.getMcpServiceCountByTenantId(params.get(TENANT_ID));

        if (mcpServiceCount >= Long.parseLong(mcpQuota)) {
            log.warn("Service count exceeds quota.");
            throw new AgentStudioException(StudioError.SERVICE_EXCEEDING_LIMIT);
        }

        McpServiceEntity serviceEntity = mcpUtil.mcpServiceDetailInfoDto2ServiceEntity(serviceDetail,
            params.get("workspaceId"));

        // ServerConfig可能含有敏感信息，此处加密处理，读取时需要解密
        serviceEntity.setServerConfig(encryptionAdapter.encrypt(serviceDetail.getServerConfig(), RequestContextUtils.getRequestUserDomainId()));
        log.info("Server config encrypted for new service.");

        serviceEntity.setOrgType(serviceDetail.getOrgType());

        if (Strings.CS.equals(serviceDetail.getOrgType(), EnumOrgType.SSE.getValue())) {
            // SSE 逻辑
            log.info("Setting deploy type to 'sse' for new service.");
            serviceEntity.setDeployType("sse");
            serviceEntity.setFcInstanceUrl(removeQueryParamsFromUrl(
                CommonUtil.parseUrlFromMcpConfig(JSONObject.parseObject(serviceDetail.getServerConfig()), 0)));

        } else if (Strings.CI.equals(serviceDetail.getOrgType(), EnumOrgType.STREAMABLE_HTTP.getValue())) {
            // 新增 Streamable HTTP 插入逻辑
            serviceEntity.setDeployType("streamable_http");
            serviceEntity.setFcInstanceUrl(removeQueryParamsFromUrl(
                CommonUtil.parseUrlFromMcpConfig(JSONObject.parseObject(serviceDetail.getServerConfig()), 0)));

        } else if (Strings.CS.equals(serviceDetail.getOrgType(), EnumOrgType.NPX.getValue()) ||
            Strings.CS.equals(serviceDetail.getOrgType(), EnumOrgType.UVX.getValue())) {
            // 原有的 NPX/UVX 逻辑
            serviceEntity.setDeployType("stdio");

            // NPX\UVX部署到FG，并注册到APIG，调用需要认证，刷新MCP的认证信息到ServerConfig
            log.info("Inserting auth headers into server config for new service.");
            serviceEntity.setServerConfig(
                encryptionAdapter.encrypt(mcpUtil.insertAuthHeadersIntoMcpServer(serviceDetail.getServerConfig()), RequestContextUtils.getRequestUserDomainId()));
        }

        serviceEntity.setServerId(params.get("serverId"));
        // 注意：这里设置为 CREATING_STACK，意味着必须有后续的任务将其更新为 RUNNING
        // 如果没有异步部署任务，Streamable HTTP 可能会一直卡在 "创建中"
        serviceEntity.setFcInstanceStatus(CREATING_STACK.getValue());

        serviceEntity.setUniqueCode(CommonUtil.getUUID());
        serviceEntity.setProjectId(params.get("projectId"));
        serviceEntity.setWorkspaceId(params.get("workspaceId"));

        if (serviceEntity.getVisibility() == null) {
            serviceEntity.setVisibility("workspace");
            log.info("Set default visibility to 'workspace'.");
        }

        if (serviceEntity.getNodeType() == null) {
            serviceEntity.setNodeType(McpNodeType.Mcp.getValue());
            log.info("Set default node type to 'Mcp'.");
        }

        if (serviceEntity.getCreatedDate() == null) {
            serviceEntity.setCreatedDate(new Timestamp(new Date().getTime()));
            log.info("Set created date to current time.");
        }

        if (serviceEntity.getLastUpdatedDate() == null) {
            serviceEntity.setLastUpdatedDate(new Timestamp(new Date().getTime()));
            log.info("Set last updated date to current time.");
        }

        if (StringUtils.isNotBlank(icon)) {
            serviceEntity.setIcon(icon);
            log.info("Set icon for new service.");
        }

        log.info("Inserting new service entity. Service name: {}", serviceDetail.getName());
        serviceDao.insert(serviceEntity);

        return serviceEntity.getId();
    }

    private String mcpDeployment(McpServiceDetailInfoDto serviceDetail, String serverId, String serviceId) {
        log.info("Start MCP deployment. Service ID: {}, Server ID: {}", serviceId, serverId);

        String tenantId = RequestContextUtils.getRequestUserDomainId();

        CommonUtil.validateMcpConfigFormat(serviceDetail.getServerConfig());
        log.info("Service config format validated.");

        McpServerEntity mcpServerEntity = null;
        if (StringUtils.isEmpty(serviceDetail.getThirdResource())) {
            // 来自自有mcp模板库，需要校验mcp模板是否存在
            mcpServerEntity = this.serverDao.selectById(serverId);
            if (mcpServerEntity == null) {
                log.warn("Server not found. Server ID: {}", serverId);
                throw new AgentStudioException(StudioError.MCP_SERVICE_NOT_EXIST);
            }
        } else {
            mcpServerEntity = mcpUtil.mcpServiceInfoDto2ServerEntity(serviceDetail);
        }

        McpServiceEntity serviceEntity = new McpServiceEntity();
        serviceEntity.setId(serviceId);
        // 增加 OR STREAMABLE_HTTP 判断
        if (Strings.CI.equals(mcpServerEntity.getOrgType(), EnumOrgType.SSE.toString()) ||
            Strings.CI.equals(mcpServerEntity.getOrgType(), EnumOrgType.STREAMABLE_HTTP.toString())) {

            // SSE 和 Streamable HTTP 走相同的轻量级部署流程
            JSONObject jsonObject = JSONObject.parseObject(serviceDetail.getServerConfig());
            String url = removeQueryParamsFromUrl(CommonUtil.parseUrlFromMcpConfig(jsonObject, 0));
            serviceEntity.setFcInstanceUrl(url);

            // 初始状态设为 CREATING_STACK，前端显示部署中
            serviceEntity.setFcInstanceStatus(CREATING_STACK.getValue());

            serviceEntity.setServerConfig(encryptionAdapter.encrypt(serviceDetail.getServerConfig(), tenantId));
            serviceEntity.setName(serviceDetail.getName());
            serviceEntity.setOrgType(serviceDetail.getOrgType());
            serviceEntity.setNodeType(McpNodeType.Mcp.getValue());
            serviceEntity.setAuthType(serviceDetail.getAuthType());
            serviceEntity.setTempToken(RequestContextUtils.getRequestAuthToken());
            serviceEntity.setTenantId(tenantId);
            // 异步获取工具列表 (getMcpServiceToolList 方法在第二部分代码中，需要确保 ClientService 支持 streamable_http)
            // 替换旧的手动异步逻辑，调用统一公共方法

            String authToken = RequestContextUtils.getRequestAuthToken();
            String projectId = RequestContextUtils.getRequestProjectId();

            mcpTaskExecutor.execute(() -> {
                try {
                    RequestContextUtils.setContext(authToken, projectId, tenantId);
                    // 调用统一逻辑：获取工具 -> 成功/失败 -> 写入报错原因
                    this.getMcpServiceToolListAndUpdateStatus(serviceEntity);
                } catch (Throwable t) {
                    log.error("Fatal error during MCP async deployment for service {}", serviceId, t);
                    // 兜底处理
                    handleExceptionWithError(serviceEntity, t, StudioError.MCP_NETWORK_CONNECTION_ERROR);
                }
            });

            mcpUpdateTaskExecutor.execute(() -> this.mcpUpdateTask.updateInstallTimes(serverId));
            log.info("Scheduled install times update for server ID: {}", serverId);

            return serviceId;
        }
        return null;
    }

    private String customMcpDeployment(McpServiceDetailInfoDto serviceDetail, String serviceId) {
        log.info("Start custom MCP deployment. Service ID: {}", serviceId);

        String tenantId = RequestContextUtils.getRequestUserDomainId();
        CommonUtil.validateMcpConfigFormat(serviceDetail.getServerConfig());
        log.info("Service config format validated.");

        McpServiceEntity serviceEntity = new McpServiceEntity();
        serviceEntity.setId(serviceId);
        serviceEntity.setName(serviceDetail.getName());
        serviceEntity.setNameEn(serviceDetail.getNameEn());
        serviceEntity.setAuthInfo(serviceDetail.getAuthInfo());

        // 增加 OR STREAMABLE_HTTP 判断
        if (Strings.CI.equals(serviceDetail.getOrgType(), EnumOrgType.SSE.toString()) ||
            Strings.CI.equals(serviceDetail.getOrgType(), EnumOrgType.STREAMABLE_HTTP.toString())) {
            log.info("Processing custom SSE/streamable_http deployment for service ID: {}", serviceId);

            JSONObject jsonObject = JSONObject.parseObject(serviceDetail.getServerConfig());
            String url = removeQueryParamsFromUrl(CommonUtil.parseUrlFromMcpConfig(jsonObject, 0));
            serviceEntity.setFcInstanceUrl(url);
            serviceEntity.setOrgType(serviceDetail.getOrgType());
            serviceEntity.setServerConfig(encryptionAdapter.encrypt(serviceDetail.getServerConfig(), tenantId));
            serviceEntity.setName(serviceDetail.getName());
            serviceEntity.setNodeType(McpNodeType.Mcp.getValue());
            // 补全租户信息，否则异步线程里报错会空指针
            serviceEntity.setTenantId(tenantId);

            // 初始状态设为 CREATING_STACK
            serviceEntity.setFcInstanceStatus(CREATING_STACK.getValue());

            String authToken = RequestContextUtils.getRequestAuthToken();
            String projectId = RequestContextUtils.getRequestProjectId();

            // 使用新的公共方法
            mcpTaskExecutor.execute(() -> {
                try {
                    RequestContextUtils.setContext(authToken, projectId, tenantId);
                    // 调用统一的逻辑：获取工具 -> 成功/失败 -> 写入数据库(含报错原因)
                    this.getMcpServiceToolListAndUpdateStatus(serviceEntity);
                } catch (Throwable t) {
                    log.error("Fatal error during Custom MCP async deployment for service {}", serviceId, t);
                    // 兜底处理
                    handleExceptionWithError(serviceEntity, t, StudioError.MCP_NETWORK_CONNECTION_ERROR);
                }
            });

            return serviceId;
        }

        return null;
    }


    /**
     * 失败时执行清理逻辑
     * 独立方法，避免代码重复
     */
    private void performCleanupOnFailure(String serviceId) {
        try {
            if (isSoftDelete) {
                serviceDao.markAsDeleted(serviceId, RequestContextUtils.getRequestUserDomainId(), CommonUtil.getDeptCode());
            } else {
                serviceDao.hardDeleteSingleMcpServiceById(serviceId, RequestContextUtils.getRequestUserDomainId(), CommonUtil.getDeptCode());
            }
        } catch (Exception deleteEx) {
            // 防止清理时的异常覆盖了原本的部署异常，只记录日志
            log.error("Failed to clean up service after deployment failure. Service ID: {}", serviceId, deleteEx);
        }
    }

    /**
     * 删除应用
     *
     */
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "McpService",
        description = "删除MCP服务",
        resourceId = "id",
        resourceName = ""
    )
    public String deleteService(String projectId, String workspaceId, String id) {
        log.info("operation log {}:start to delete mcp service", projectId);
        String tenantId = RequestContextUtils.getRequestUserDomainId();
        McpServiceEntity serviceEntity = serviceDao.getMcpServiceById(id, tenantId, CommonUtil.getDeptCode(), projectId,
            workspaceId);
        if (ObjectUtils.isEmpty(serviceEntity)) {
            log.error("No mcp service id is {} !", id);
            McpServiceExceptionUtils.throwMissingParameterError("mcpId");
        }
        // 状态校验
        if ("creatingStack".equals(serviceEntity.getFcInstanceStatus())) {
            log.error("delete service rejected. service is {}, status is {}", id, serviceEntity.getFcInstanceStatus());
            throw new AgentStudioException(StudioError.MCP_SERVICE_CREATING_STATUS_NOT_DELETE);
        }
        // 是否共享校验
        shareInnerService.cancelMCPShared(id, projectId, workspaceId);
        // 增加 OR STREAMABLE_HTTP 判断
        if (Strings.CI.equals(serviceEntity.getOrgType(), EnumOrgType.SSE.toString()) ||
            Strings.CI.equals(serviceEntity.getOrgType(), EnumOrgType.STREAMABLE_HTTP.toString())
            || StringUtils.isBlank(serviceEntity.getOrgType())) {
            if (isSoftDelete) {
                serviceDao.markAsDeleted(id, serviceEntity.getTenantId(), serviceEntity.getDeptCode());
            } else {
                serviceDao.hardDeleteSingleMcpServiceById(id, serviceEntity.getTenantId(), serviceEntity.getDeptCode());
            }
            mappingMapper.updateValidByResourceId(id);
            return "deleted";
        }
        if ("deleting".equals(serviceEntity.getFcInstanceStatus())) {
            log.error("delete service rejected. service is {}, status is {}", id, serviceEntity.getFcInstanceStatus());
            throw new AgentStudioException(StudioError.MCP_SERVICE_DELETING_STATUS_NOT_DELETE);
        }
        int updateCount = serviceDao.updateFcInstanceStatus(id, DELETING.getValue(),
            RequestContextUtils.getRequestUserDomainId(), CommonUtil.getDeptCode());
        if (updateCount <= 0) {
            log.error("delete service fail. service is {}, status is {}", id, serviceEntity.getFcInstanceStatus());
            throw new AgentStudioException(StudioError.MCP_SERVICE_DELETE_FAILED_FROM_FG);
        }

        mappingMapper.updateValidByResourceId(id);
        ApigRequsetDto apigRequsetDto = new ApigRequsetDto();
        apigRequsetDto.setId(serviceEntity.getId());
        apigRequsetDto.setApiServiceName(serviceEntity.getFunctionApplicationName());
        ResponseEntity<DeleteApiV2Response> deleteApiV2Response = apigMcpService.deleteApi(apigRequsetDto);
        // 轮询查询结果
        if (deleteApiV2Response.getStatusCode().is2xxSuccessful()) {
            log.info("app {} delete complete at FG.", serviceEntity.getFunctionApplicationName());
            mcpUtil.updateServiceDeletedInfoFromFG(serviceEntity.getId(), serviceEntity.getTenantId(),
                serviceEntity.getDeptCode());
        } else {
            log.info("app {} delete complete at FG.", serviceEntity.getFunctionApplicationName());
            mcpUtil.updateServiceStatus(serviceEntity.getId(), EnumMcpStatus.DELETION_FAIL.getValue(),
                RequestContextUtils.getRequestUserDomainId(), serviceEntity.getDeptCode());
        }
        return "deleting";
    }

    /**
     * 测试MCP中的tool
     *
     */

    public McpServiceDataResp testServicesTools(String projectId, String workspaceId,
        McpServiceToolsTestReq testInfo) {
        log.info("operation log {}:start to test mcp tools", projectId);
        String tenantId = RequestContextUtils.getRequestUserDomainId();

        McpServiceEntity serviceEntity = serviceDao.getMcpServiceByIdAndTenant(testInfo.getServiceId(), tenantId,
            CommonUtil.getDeptCode(),  workspaceId);
        if (ObjectUtils.isEmpty(serviceEntity)) {
            log.error("[testServicesTools] no mcp service id is {} !", testInfo.getServiceId());
            throw new AgentStudioException(StudioError.MCP_SERVICE_NOT_EXIST);
        }

        String mcpUrl = serviceEntity.getFcInstanceUrl();

        String query = CommonUtil.getRawQueryString(CommonUtil.parseUrlFromMcpConfig(
            JSONObject.parseObject(encryptionAdapter.decrypt(serviceEntity.getServerConfig())), 0));
        if (!StringUtils.isEmpty(query)) {
            mcpUrl += "?" + query;
            log.info("Appending query parameters to URL: {}", query);
        }

        Map<String, String> headerInfo = new HashMap<>();
        if (!StringUtils.isEmpty(serviceEntity.getAuthType()) && Strings.CI.equals(
            serviceEntity.getAuthType(), "IAM-TOKEN")) {
            log.info("Using IAM-TOKEN authentication.");
            headerInfo.put("X-Auth-Token", RequestContextUtils.getRequestAuthToken());
            constructHeaderInfo(workspaceId, headerInfo);
        } else if (!StringUtils.isEmpty(serviceEntity.getAuthType()) && Strings.CI.equals(
            serviceEntity.getAuthType(), CommonConstant.MCP_AUTH_TYPE.USE_IAM_TOKEN)) {
            log.info("Using USE_IAM_TOKEN authentication.");
            String token = null;
            try {
                token = RequestContextUtils.getRequestAuthToken();
            } catch (AgentStudioException e) {
                // 跨线程无法传递token，使用serviceEntity临时传递
                token = serviceEntity.getTempToken();
            }
            headerInfo.put("X-Auth-Token", token);
        } else {
            log.info("Parsing headers from server config.");
            headerInfo = CommonUtil.parseMcpConfigHeaderInfo(encryptionAdapter.decrypt(serviceEntity.getServerConfig()));
        }
        // 若存在Oauth鉴权，交换token
        mcpUrl = mcpBase.exchangeTokenByAuth(serviceEntity.getAuthInfo(), headerInfo, mcpUrl);

        // 自定义 apikey 鉴权：出站前对 cust-* 做配置驱动 rename（cust-token→token, cust-userid→userId）
        McpCustomerHeaderProjection.renameOutboundCustomerHeaders(headerInfo, serviceEntity.getName());

        log.info("Calling MCP service tool. Service name: {}, Tool name: {}", serviceEntity.getName(), testInfo.getToolName());
        McpSchema.CallToolResult callToolResult = mcpClientService.callMcpServiceTool(
            serviceEntity.getName(), testInfo.getToolName(), mcpUrl, testInfo.getParams(), serviceEntity.getOrgType(), headerInfo);


        McpServiceDataResp resp = transformerMcpRes(callToolResult);;



        return resp;
    }

    private McpServiceDataResp transformerMcpRes(McpSchema.CallToolResult callToolResult) {
        McpServiceDataResp resp = new McpServiceDataResp();

        if (ObjectUtils.isEmpty(callToolResult.structuredContent())) {
            McpServiceToolsTestResp oldContent = new McpServiceToolsTestResp();
            oldContent.setContent(Collections.singletonList(callToolResult.content()));
            log.info("Tool call result content: {}", callToolResult.content());

            if (ObjectUtils.isNotEmpty(callToolResult.isError())) {
                log.warn("Tool call returned an error. Error: {}", callToolResult.isError());
                oldContent.setIsError(callToolResult.isError());
            }
            resp.setData(oldContent);
        } else {
            log.info("Tool call result structured content: {}", callToolResult.structuredContent());
            resp.setData(callToolResult.structuredContent());
        }
        return resp;
    }

    private void constructHeaderInfo(String workspaceId, Map<String, String> headerInfo) {
        List<Extension> masExtensions = workspaceMappingService.queryMappingWorkspaceExtensionInfo(workspaceId, CommonConstant.MAS.WORKSPACE_SOURCE_TYPE);
        if (CollectionUtils.isEmpty(masExtensions)) {
            throw new AgentStudioException(StudioError.INVALID_EXTENSION_PARAM);
        }
        for (Extension extension : masExtensions) {
            if (Strings.CI.equals(CommonConstant.MAS.APIKEY, extension.getKey())) {
                headerInfo.put(CommonConstant.MAS.APIKEY, encryptionAdapter.decrypt(extension.getValue()));
            }
        }
        headerInfo.put(CommonConstant.MAS.APPCODE, encryptionAdapter.decrypt(masAppcode));
    }

    /**
     * 部署成功的mcp详细页，查询工具列表
     *
     */
    public String mcpServicesToolsList(String projectId, String workspaceId, String serviceId) {
        log.info("Operation log: Start to query MCP tools detail. Project ID: {}", projectId);

        String tenantId = RequestContextUtils.getRequestUserDomainId();
        String authToken = RequestContextUtils.getRequestAuthToken();

        CommonUtil.validateProjectAndWorkspaceId(projectId, workspaceId);

        log.info("Project and workspace ID validated. Project: {}, Workspace: {}", projectId, workspaceId);

        McpServiceEntity serviceEntity = serviceDao.getMcpServiceById(serviceId, tenantId, CommonUtil.getDeptCode(),
            projectId, workspaceId);

        if (ObjectUtils.isEmpty(serviceEntity)) {
            // 判断是不是团队共享mcp
            // 增加共享判断，如果插件被共享到当前空间,则可以使用
            return getShareMcp(serviceId, workspaceId).getTools();
        }

        // 故障自愈：如果当前是部署失败状态，触发重新部署（获取工具）
        if (EnumMcpStatus.STACK_FAIL.getValue().equals(serviceEntity.getFcInstanceStatus())) {
            log.info("MCP status is STACK_FAIL, triggering auto re-deployment async. Service ID: {}", serviceId);

            // 1. 重置状态为 "创建中" (CREATING_STACK)，防止前端重复请求，并让UI显示加载态
            serviceDao.updateFcInstanceStatus(serviceEntity.getId(), EnumMcpStatus.CREATING_STACK.getValue(),
                tenantId, CommonUtil.getDeptCode());

            // 2. 异步触发工具获取和状态更新
            mcpTaskExecutor.execute(() -> {
                try {
                    // 重新设置上下文（因为是异步线程）
                    RequestContextUtils.setContext(authToken, projectId, tenantId);
                    // 调用包含 "获取工具 + 更新状态(SUCCESS/FAIL)" 的完整方法
                    this.getMcpServiceToolListAndUpdateStatus(serviceEntity);
                } catch (Throwable t) {
                    log.error("Async auto re-deploy failed for service: {}", serviceId, t);
                    // 异常兜底：确保状态回滚为失败，避免一直卡在"创建中"
                    serviceDao.updateStatus(serviceEntity.getId(), EnumMcpStatus.STACK_FAIL.getValue(),
                        serviceEntity.getTenantId(), CommonUtil.getDeptCode());
                } finally {
                    RequestContextUtils.remove(); // 清理
                }
            });
            // 3. 返回空字符串，前端根据状态 CREATING_STACK 会显示 loading
            return "";
        }

        // 如果正在部署/创建中，直接返回空，不要去请求还在启动的服务，避免报错
        if (EnumMcpStatus.CREATING_STACK.getValue().equals(serviceEntity.getFcInstanceStatus())) {
            log.info("MCP service is currently deploying (CREATING_STACK). Service ID: {}", serviceId);
            return ""; // 前端根据状态会继续显示 Loading
        }

        // 如果数据库已有工具，异步刷新并直接返回缓存
        if (StringUtils.isNotBlank(serviceEntity.getTools())) {
            log.info("Tools already exist for service ID: {}. Starting async update task.", serviceId);
            mcpTaskExecutor.execute(() -> {
                try {
                    RequestContextUtils.setContext(authToken, projectId, tenantId);
                    this.getMcpServiceToolListAndUpdate(serviceEntity);
                } catch (Throwable t) {
                    log.error("Async update tools failed for service: {}", serviceId, t);
                    // 这里通常不需要置为失败，因为旧数据还能用
                } finally {
                    RequestContextUtils.remove(); // 清理
                }
            });
            return serviceEntity.getTools();
        }

        // 首次获取或无缓存

        String mcpUrl = serviceEntity.getFcInstanceUrl();
        log.info("FC instance URL: {}", mcpUrl);

        String query = CommonUtil.getRawQueryString(CommonUtil.parseUrlFromMcpConfig(
            JSONObject.parseObject(encryptionAdapter.decrypt(serviceEntity.getServerConfig())), 0));
        if (!StringUtils.isEmpty(query)) {
            mcpUrl += "?" + query;
            log.info("Appending query parameters to URL: {}", query);
        }

        Map<String, String> headerInfo = CommonUtil.parseMcpConfigHeaderInfo(encryptionAdapter.decrypt(
            serviceEntity.getServerConfig()));

        // 同步获取一次，确保连接正常
        List<McpSchema.Tool> toolList = mcpClientService.getMcpServiceToolList(serviceEntity.getName(), mcpUrl,
            serviceEntity.getOrgType(), headerInfo);

        if (CollectionUtils.isEmpty(toolList)) {
            log.warn("No tools found for service ID: {}", serviceId);
            return "";
        }

        String tools = McpJsonUtils.toJson(toolList);

        // 异步更新状态
        mcpTaskExecutor.execute(() -> {
            try {
                RequestContextUtils.setContext(authToken, projectId, tenantId);
                serviceDao.updateTools(serviceEntity.getId(), tools, serviceEntity.getTenantId());

                // 增加 STREAMABLE_HTTP 判断，提供“故障恢复”能力
                if (Strings.CS.equals(serviceEntity.getOrgType(), EnumOrgType.NPX.toString()) ||
                    Strings.CS.equals(serviceEntity.getOrgType(), EnumOrgType.UVX.toString()) ||
                    Strings.CS.equals(serviceEntity.getOrgType(), EnumOrgType.STREAMABLE_HTTP.getValue()) || // 兼容 getValue
                    Strings.CS.equals(serviceEntity.getOrgType(), EnumOrgType.STREAMABLE_HTTP.toString())) { // 兼容 toString

                    serviceDao.updateFcInstanceStatus(serviceEntity.getId(), EnumMcpStatus.SUCCESS.getValue(),
                        tenantId, CommonUtil.getDeptCode());
                }
            } catch (Throwable t) {
                // 捕获所有错误，包括 NoClassDefFoundError
                log.error("Async status update failed for service {}", serviceId, t);
                // 如果是手动触发的刷新，这里是否置为失败取决于业务，通常保持原状即可，或者置为 STACK_FAIL
            } finally {
                RequestContextUtils.remove(); // 清理
            }
        });

        return tools;
    }

    private McpServiceEntity getShareMcp(String serviceId, String workspaceId) {
        List<McpServiceEntity> serviceEntities = shareInnerService.getShareMcp(List.of(serviceId), workspaceId);
        if (CollectionUtils.isEmpty(serviceEntities)) {
            log.error("[mcpServicesToolsList] No MCP service found. Service ID: {}", serviceId);
            throw new AgentStudioException(StudioError.MCP_SERVICE_NOT_EXIST);
        }
        return serviceEntities.get(0);
    }

    /**
     * 工具列表
     *
     */
    public void getMcpServiceToolListAndUpdate(McpServiceEntity serviceEntity) {
        log.info("Start to get and update MCP service tool list. Service ID: {}", serviceEntity.getId());

        String mcpServiceToolList = this.getMcpServiceToolList(serviceEntity);

        if (StringUtils.isNotBlank(mcpServiceToolList)) {
            log.info("Tool list is not empty. Updating database for service ID: {}", serviceEntity.getId());
            serviceDao.updateTools(serviceEntity.getId(), mcpServiceToolList, serviceEntity.getTenantId());
        } else {
            log.warn("Tool list is empty. No update performed for service ID: {}", serviceEntity.getId());
        }
    }

    /**
     * 异步获取工具列表并更新状态 (包含智能错误映射)
     */
    public void getMcpServiceToolListAndUpdateStatus(McpServiceEntity serviceEntity) {
        log.info("Start to get and update MCP service tool list. Service ID: {}", serviceEntity.getId());

        try {
            String mcpServiceToolList = this.getMcpServiceToolList(serviceEntity);

            if (StringUtils.isNotBlank(mcpServiceToolList)) {
                log.info("Tool list obtained. Updating status to SUCCESS.");
                serviceDao.updateToolsAndStatus(serviceEntity.getId(), serviceEntity.getTenantId(),
                    EnumMcpStatus.SUCCESS.getValue(), mcpServiceToolList);
            } else {
                log.warn("Tool list is empty.");
                serviceDao.updateStatusWithReason(serviceEntity.getId(),
                    EnumMcpStatus.STACK_FAIL.getValue(),
                    "[1149] 获取到的工具列表为空",
                    serviceEntity.getTenantId(), CommonUtil.getDeptCode());
            }

        } catch (AgentStudioException e) {
            // 1. 优先捕获业务异常
            log.error("Async tool fetch failed for service: {}", serviceEntity.getId(), e);
            handleExceptionWithError(serviceEntity, e, e.getErrorCode());

        } catch (Throwable t) {
            // 2. 捕获其他未知异常
            log.error("Async tool fetch failed (Unexpected): {}", serviceEntity.getId(), t);
            // 挖掘 + 匹配
            String fullStackMsg = collectAllExceptionInfo(t);
            StudioError studioError = matchErrorByMessage(fullStackMsg, StudioError.MCP_FETCH_TOOLS_SERVER_ERROR);

            handleExceptionWithError(serviceEntity, t, studioError);
        }
    }


    /**
     * 快速网络诊断 (支持携带 Header 进行认证探测)
     * 特性：
     * 1. 遇到硬错误(配置错误)直接抛出。
     * 2. 遇到超时(网络抖动)尝试重试 3 次，防止误杀。
     * 3. 日志全量脱敏。
     */
    private void quickNetworkCheck(String targetUrl, Map<String, String> headers) {
        // 定义最大尝试次数 (1次初始 + 3次重试 = 4次)
        int maxAttempts = 4;

        for (int i = 1; i <= maxAttempts; i++) {
            HttpURLConnection connection = null;
            try {
                URL url = new URL(targetUrl);

                // --- 代理选择逻辑 ---
                Proxy proxy = Proxy.NO_PROXY;
                try {
                    List<Proxy> proxies = ProxySelector.getDefault().select(url.toURI());
                    if (proxies != null && !proxies.isEmpty()) {
                        proxy = proxies.get(0);
                    }
                } catch (Exception e) {
                    log.warn("[NetworkCheck] Proxy selection failed, using DIRECT");
                }

                // 日志脱敏
                log.info("[NetworkCheck] Probing {} (Attempt {}/{}) using proxy: {}",
                        CommonUtil.maskUrlCredentials(targetUrl), i, maxAttempts, proxy);

                connection = (HttpURLConnection) url.openConnection(proxy);
                connection.setConnectTimeout(2000); // 2秒连接超时
                connection.setReadTimeout(2000);    // 2秒读取超时

                // 注入 Headers (Token/Auth)
                if (headers != null && !headers.isEmpty()) {
                    for (Map.Entry<String, String> entry : headers.entrySet()) {
                        // 防止空值注入
                        if (entry.getKey() != null && entry.getValue() != null) {
                            connection.setRequestProperty(entry.getKey(), entry.getValue());
                        }
                    }
                }

                // 默认 GET 请求，触发连接
                connection.connect();

                int responseCode = connection.getResponseCode();
                log.info("[NetworkCheck] Result code: {}", responseCode);

                // 认证失败 (即使带了Header还是401/403，说明Header不对或没权限，属于配置硬错误)
                if (responseCode == 407 || responseCode == 401 || responseCode == 403) {
                    throw new AgentStudioException(StudioError.MCP_AUTHENTICATION_FAILED,
                            "Auth Failed: HTTP " + responseCode);
                }
                // 路径不存在
                if (responseCode == 404) {
                    throw new AgentStudioException(StudioError.MCP_TARGET_NOT_FOUND,
                            "HTTP 404 Not Found: " + CommonUtil.maskUrlCredentials(targetUrl));
                }

            } catch (java.net.SocketTimeoutException e) {
                // 超时重试逻辑
                if (i < maxAttempts) {
                    log.warn("[NetworkCheck] Timeout on attempt {}, retrying...", i);
                    try {
                        Thread.sleep(500); // 稍微歇一下再试
                    } catch (InterruptedException ignored) {
                        Thread.currentThread().interrupt();
                        log.warn("[NetworkCheck] Sleep interrupted", ignored);
                    }
                    continue; // 进入下一次循环
                }

                // 最后一次尝试还是超时
                log.error("[NetworkCheck] Timeout (2s limit) after {} attempts", maxAttempts);
                throw new AgentStudioException(StudioError.MCP_NETWORK_TIMEOUT,
                        "Connect timed out (2s limit) to " + CommonUtil.maskUrlCredentials(targetUrl));

            } catch (UnknownHostException e) {
                log.error("[NetworkCheck] Unknown Host: {}", e.getMessage());
                throw new AgentStudioException(StudioError.MCP_UNKNOWN_HOST,
                        "Unknown Host: " + e.getMessage());

            } catch (java.net.ConnectException e) {
                log.error("[NetworkCheck] Connection Refused: {}", e.getMessage());
                throw new AgentStudioException(StudioError.MCP_CONNECTION_REFUSED,
                        "Connection Refused: " + e.getMessage());

            } catch (AgentStudioException e) {
                throw e; // 业务异常直接抛

            } catch (Exception e) {
                log.error("[NetworkCheck] Generic failure: {}", e.getMessage());
                throw new AgentStudioException(StudioError.MCP_NETWORK_CONNECTION_ERROR,
                        "Probe Error: " + e.getMessage());

            } finally {
                if (connection != null) {
                    try {
                        connection.disconnect();
                    } catch (Exception ignored) {
                        log.debug("Error while disconnecting HttpURLConnection", ignored);
                    }
                }
            }
        }
    }

    /**
     * 错误匹配器：根据挖掘到的堆栈信息返回精准的 StudioError
     *
     * @param errorMsg 挖掘到的全量异常信息 (小写)
     * @param defaultError 默认兜底错误
     * @return 精准的 StudioError
     */
    private StudioError matchErrorByMessage(String errorMsg, StudioError defaultError) {
        if (StringUtils.isBlank(errorMsg)) {
            return defaultError;
        }
        // 转小写以忽略大小写差异
        String msg = errorMsg.toLowerCase(Locale.ROOT);

        // 1. 认证失败 (Auth Failed) [1164]
        // 拆分逻辑运算符，降低复杂度
        boolean isAuthCode = msg.contains("407") || msg.contains("401") || msg.contains("403");
        boolean isAuthMsg = msg.contains("proxy authentication") || msg.contains("unauthorized") ||
                msg.contains("forbidden") || msg.contains("access denied");

        if (isAuthCode || isAuthMsg) {
            return StudioError.MCP_AUTHENTICATION_FAILED;
        }

        // 2. 目标不存在 (Not Found) [1163]
        if (msg.contains("404") || msg.contains("not found")) {
            return StudioError.MCP_TARGET_NOT_FOUND;
        }

        // 3. 连接被拒绝 (Connection Refused) [1162]
        if (msg.contains("connection refused") || msg.contains("refused")) {
            return StudioError.MCP_CONNECTION_REFUSED;
        }

        // 4. 域名错误 (Unknown Host) [1173]
        if (msg.contains("unknownhost") || msg.contains("no such host")) {
            return StudioError.MCP_UNKNOWN_HOST;
        }

        // 5. 超时 (Timeout) [1161]
        if (msg.contains("timeout") || msg.contains("timed out") ||
                msg.contains("pt30s") || // SDK 特有的 ISO-8601 持续时间格式
                msg.contains("did not observe")) {
            return StudioError.MCP_NETWORK_TIMEOUT;
        }

        // 6. SDK 内部/协议错误 (Generic Network/Protocol Error) [1150]
        if (msg.contains("internal error") || msg.contains("parse error") ||
                msg.contains("session closed") || msg.contains("session not found")) {
            return StudioError.MCP_NETWORK_CONNECTION_ERROR;
        }

        return defaultError;
    }

    /**
     * 异常挖掘机 (BFS 广度优先版 + toString 增强)
     */
    private String collectAllExceptionInfo(Throwable t) {
        if (t == null) {
            return "Unknown Error";
        }

        StringBuilder sb = new StringBuilder();
        Set<Throwable> visited = new HashSet<>(); // 防止循环引用
        // 增加一个 Set 防止重复拼接相同的错误信息
        Set<String> msgDedup = new HashSet<>();
        Queue<Throwable> queue = new LinkedList<>();

        queue.offer(t);

        while (!queue.isEmpty()) {
            Throwable current = queue.poll();

            if (visited.contains(current)) {
                continue;
            }
            visited.add(current);

            // 1. 提取类名
            String className = current.getClass().getSimpleName();

            // 2. 提取 getMessage()
            String msg = current.getMessage();
            String token1 = className + ": " + msg;

            if (StringUtils.isNotBlank(msg) && msgDedup.add(msg)) {
                sb.append(token1).append("; ");
            }

            // 3. 提取 toString()
            String toStringVal = current.toString();
            if (StringUtils.isNotBlank(toStringVal) && !toStringVal.equals(msg) && msgDedup.add(toStringVal)) {
                sb.append("[").append(toStringVal).append("]; ");
            }

            // 4. 挖掘 Cause
            if (current.getCause() != null) {
                queue.offer(current.getCause());
            }

            // 5. 挖掘 Suppressed
            for (Throwable suppressed : current.getSuppressed()) {
                queue.offer(suppressed);
            }
        }

        if (sb.length() > 2000) {
            return sb.substring(0, 2000) + "...";
        }
        return sb.toString();
    }

    /**
     * 提取最核心的根因信息 (清洗掉冗余的包装壳)
     * 目标格式: "UnknownHostException: mcp-test.local" 或 "ConnectException: Connection refused"
     */
    private String extractCleanRootCause(Throwable t) {
        if (t == null) {
            return "Unknown Error";
        }

        // 1. 深度挖掘：一直挖到最底层的 Root Cause
        Throwable root = t;
        while (root.getCause() != null) {
            root = root.getCause();
        }

        // 2. 获取核心信息
        String exceptionName = root.getClass().getSimpleName(); // 例如 "UnknownHostException"
        String message = root.getMessage();

        // 3. 针对常见网络错误的特殊优化
        if (root instanceof UnknownHostException) {
            return "Unknown Host: " + message;
        }
        if (root instanceof java.net.ConnectException) {
            return "Connection Refused: " + message;
        }
        if (root instanceof java.net.SocketTimeoutException) {
            return "Connect Timed Out: " + message;
        }

        // 4. 如果 Message 为空，只返回异常类名
        if (StringUtils.isBlank(message)) {
            return exceptionName;
        }

        // 5. 通用格式：异常名 + 消息
        // 并在最后做一个简单的清理，防止 message 里包含重复的类名
        if (message.startsWith(exceptionName)) {
            return message;
        }
        return exceptionName + ": " + message;
    }

    /**
     * 统一异常处理并写入数据库 (优化版: 只存精简信息)
     */
    private void handleExceptionWithError(McpServiceEntity serviceEntity, Throwable t, StudioError error) {
        String code = error.getCode();
        String debugInfo = "";

        if (t != null) {
            String rawStack = extractCleanRootCause(t);

            String safeStack = rawStack;
            try {
                // 依然需要脱敏，防止 URL 里带 Token
                safeStack = CommonUtil.maskUrlCredentials(rawStack);
            } catch (Exception ignored) {
                log.debug("Failed to mask credentials", ignored);
            }

            int maxInfoLength = 400;
            if (safeStack != null && safeStack.length() > maxInfoLength) {
                debugInfo = safeStack.substring(0, maxInfoLength) + "...";
            } else {
                debugInfo = safeStack;
            }
        }

        // 3. 序列化为 JSON 字符串
        String finalFailReasonJson;
        try {
            // 构造精简对象
            McpFailReasonDetailDto dto = new McpFailReasonDetailDto()
                    .setCode(code)
                    .setDebugInfo(debugInfo);

            ObjectMapper mapper = new ObjectMapper();
            mapper.setSerializationInclusion(JsonInclude.Include.NON_NULL);
            finalFailReasonJson = mapper.writeValueAsString(dto);

        } catch (Exception e) {
            log.error("Failed to serialize fail reason", e);
            finalFailReasonJson = String.format("{\"code\":\"%s\", \"debug_info\":\"Serialization Error\"}", code);
        }

        // 4. 准备上下文 & 5. 异步写入 (保持不变)
        String finalJsonToSave = finalFailReasonJson;
        String authToken = RequestContextUtils.getRequestAuthToken();
        String projectId = RequestContextUtils.getRequestProjectId();
        String tenantId = StringUtils.isNotBlank(serviceEntity.getTenantId())
                ? serviceEntity.getTenantId()
                : RequestContextUtils.getRequestUserDomainId();

        mcpTaskExecutor.execute(() -> {
            try {
                RequestContextUtils.setContext(authToken, projectId, tenantId);
                serviceDao.updateStatusWithReason(
                        serviceEntity.getId(),
                        EnumMcpStatus.STACK_FAIL.getValue(),
                        finalJsonToSave,
                        tenantId,
                        CommonUtil.getDeptCode()
                );
            } catch (Exception ex) {
                log.error("Failed to persist fail reason for service: {}", serviceEntity.getId(), ex);
            } finally {
                RequestContextUtils.remove();
            }
        });
    }

    /**
     * 获取工具列表 (核心方法：包含智能重试、异常拆包、条件放行侦察兵与智能推断机制)
     *
     */
    public String getMcpServiceToolList(McpServiceEntity serviceEntity) {
        log.info("Start to get MCP service tool list. Service ID: {}", serviceEntity.getId());

        String mcpUrl = serviceEntity.getFcInstanceUrl();
        // 解密并解析配置中的 URL Query 参数
        String query = CommonUtil.getRawQueryString(CommonUtil.parseUrlFromMcpConfig(
                JSONObject.parseObject(encryptionAdapter.decrypt(serviceEntity.getServerConfig())), 0));
        if (!StringUtils.isEmpty(query)) {
            mcpUrl += "?" + query;
        }

        Map<String, String> headerInfo = new HashMap<>();
        if (!StringUtils.isEmpty(serviceEntity.getAuthType()) && Strings.CI.equals(
                serviceEntity.getAuthType(), CommonConstant.MCP_AUTH_TYPE.IAM_TOKEN)) {
            headerInfo.put("X-Auth-Token", RequestContextUtils.getRequestAuthToken());
            constructHeaderInfo(RequestContextUtils.getRequestWorkspaceId(), headerInfo);
        } else if (!StringUtils.isEmpty(serviceEntity.getAuthType()) && Strings.CI.equals(
                serviceEntity.getAuthType(), CommonConstant.MCP_AUTH_TYPE.USE_IAM_TOKEN)) {
            String token = null;
            try {
                token = RequestContextUtils.getRequestAuthToken();
            } catch (AgentStudioException e) {
                token = serviceEntity.getTempToken();
            }
            headerInfo.put("X-Auth-Token", token);
        } else {
            headerInfo.putAll(CommonUtil.parseMcpConfigHeaderInfo(encryptionAdapter.decrypt(serviceEntity.getServerConfig())));
        }

        // 处理自定义认证
        mcpUrl = mcpBase.exchangeTokenByAuth(serviceEntity.getAuthInfo(), headerInfo, mcpUrl);
        log.info("Final URL for tools (Masked): {}", CommonUtil.maskUrlCredentials(mcpUrl));

        // 自定义 apikey 鉴权：出站前对 cust-* 做配置驱动 rename（cust-token→token, cust-userid→userId）
        McpCustomerHeaderProjection.renameOutboundCustomerHeaders(headerInfo, serviceEntity.getName());

        boolean isDirectConnectSuccess = true;
        // 进入主重试循环 (SDK调用)
        long startTime = System.currentTimeMillis();
        long maxDuration = 30 * 1000L;

        List<McpSchema.Tool> toolList = null;
        Exception lastException = null;
        int retryCount = 0;

        while (System.currentTimeMillis() - startTime < maxDuration) {
            Exception exceptionToAnalyze = null;

            try {
                // 调用 SDK (传入已处理好的 URL 和 Header)
                toolList = mcpClientService.getMcpServiceToolList(serviceEntity.getName(), mcpUrl,
                        serviceEntity.getOrgType(), headerInfo);

                // SDK 成功连接，覆盖之前的侦察结果
                log.info("SDK connection succeeded.");
                break;
            } catch (AgentStudioException e) {
                boolean isWrapper = (e.getErrorCode() == StudioError.MCP_SERVICE_BUSY ||
                        e.getErrorCode() == StudioError.MCP_NETWORK_CONNECTION_ERROR);

                if (!isWrapper) {
                    lastException = e;
                    log.error("Real business exception detected ({}). Stopping retries.", e.getErrorCode());
                    break;
                }
                exceptionToAnalyze = e;
            } catch (Exception e) {
                exceptionToAnalyze = e;
            }

            // --- 异常分析与智能推断 ---
            lastException = exceptionToAnalyze;
            retryCount++;

            String currentStackMsg = collectAllExceptionInfo(exceptionToAnalyze);
            StudioError currentError = matchErrorByMessage(currentStackMsg, null);

            // 智能推断：如果直连通但 SDK 不通 -> 可能是 SDK 内部代理或协议问题 (如 407)
            if (isDirectConnectSuccess &&
                    (currentError == StudioError.MCP_NETWORK_TIMEOUT || currentError == null)) {

                log.error("Conflict detected: Direct connection OK, but SDK timed out. Proxy 407 likely.");
                throw new AgentStudioException(StudioError.MCP_AUTHENTICATION_FAILED, lastException);
            }

            // SDK 再次确认硬错误，停止重试
            if (currentError == StudioError.MCP_AUTHENTICATION_FAILED ||
                    currentError == StudioError.MCP_TARGET_NOT_FOUND ||
                    currentError == StudioError.MCP_CONNECTION_REFUSED ||
                    currentError == StudioError.MCP_UNKNOWN_HOST) {

                log.error("SDK confirmed fatal error ({}). Stopping retries.", currentError.getCode());
                break;
            }

            // 常规重试检查
            if (System.currentTimeMillis() - startTime + 2000 >= maxDuration) {
                break;
            }

            if (retryCount % 2 == 0) {
                long elapsed = (System.currentTimeMillis() - startTime) / 1000;
                log.warn("Fetch tools retry... (Attempt {}, Elapsed {}s) Service: {}",
                        retryCount, elapsed, serviceEntity.getId());
            }

            try {
                Thread.sleep(2000);
            } catch (InterruptedException ex) {
                Thread.currentThread().interrupt();
                throw new AgentStudioException(StudioError.UNEXPECTED_ERROR);
            }
        }

        // 结果处理
        if (toolList == null) {
            if (lastException == null) {
                throw new AgentStudioException(StudioError.MCP_NETWORK_CONNECTION_ERROR);
            }
            if (lastException instanceof AgentStudioException) {
                AgentStudioException ase = (AgentStudioException) lastException;
                if (ase.getErrorCode() != StudioError.MCP_SERVICE_BUSY &&
                        ase.getErrorCode() != StudioError.MCP_NETWORK_CONNECTION_ERROR) {
                    throw ase;
                }
            }
            String fullStackMsg = collectAllExceptionInfo(lastException);
            StudioError networkError = matchErrorByMessage(fullStackMsg, null);
            if (networkError != null) {
                throw new AgentStudioException(networkError, lastException);
            }
            throw new AgentStudioException(StudioError.MCP_NETWORK_CONNECTION_ERROR, lastException);
        }

        if (CollectionUtils.isEmpty(toolList)) {
            log.warn("No tools found for service ID: {}", serviceEntity.getId());
            return "";
        }

        String tools = McpJsonUtils.toJson(toolList);
        log.info("Fetched tools success. Service ID: {}", serviceEntity.getId());
        return tools;
    }

    /**
     * 调用ces接口获取mcp的调用信息
     *
     */
    public McpServiceStatisticResp mcpServicesCesStatistic(String projectId, String workspaceId, String serviceId) {
        log.info("Operation log: Start to query MCP service statistic. Project ID: {}", projectId);

        String tenantId = RequestContextUtils.getRequestUserDomainId();

        McpServiceEntity serviceEntity = serviceDao.getMcpServiceByIdAndTenant(serviceId, tenantId,
            CommonUtil.getDeptCode(), workspaceId);

        if (ObjectUtils.isEmpty(serviceEntity)) {
            log.error("[mcpServicesCesStatistic] No MCP service found. Service ID: {}", serviceId);
            throw new AgentStudioException(StudioError.MCP_SERVICE_NOT_EXIST);
        }
        if (Strings.CI.equals(serviceEntity.getOrgType(), EnumOrgType.SSE.getValue()) ||
            Strings.CI.equals(serviceEntity.getOrgType(), EnumOrgType.STREAMABLE_HTTP.getValue())) { // 新增
            log.info("Service type is SSE, no statistics needed. Service ID: {}", serviceId);
            return new McpServiceStatisticResp();
        }

        LocalDateTime now = LocalDateTime.now();
        LocalDateTime startDateTime = now.minusDays(DEFAULT_MINUS_DAY).with(LocalTime.MIN);
        log.info("Querying statistics from: {} to: {}", startDateTime, now);

        long from = startDateTime.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli();
        long to = now.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli();

        CesMetricDataResp cesMetricDataResp = cesService.mcpServicesCesByCountMetric(String.valueOf(from),
            String.valueOf(to), DEFAULT_PERIOD, serviceEntity.getFunctionName());

        if (cesMetricDataResp == null || CollectionUtils.isEmpty(cesMetricDataResp.getDatapoints())) {
            log.warn("No metric data found for service ID: {}", serviceId);
            return new McpServiceStatisticResp();
        }

        double totalInvokingTimes = cesMetricDataResp.getDatapoints().stream().mapToDouble(Datapoints::getSum).sum();
        log.info("Total invoking times: {}", totalInvokingTimes);

        List<Datapoints> collectTop30 = cesMetricDataResp.getDatapoints()
            .stream()
            .sorted(Comparator.comparingLong(Datapoints::getTimestamp).reversed())
            .limit(DEFAULT_MINUS_DAY)
            .toList();

        double totalInvokingTimesPerMonth = collectTop30.stream().mapToDouble(Datapoints::getSum).sum();
        log.info("Total invoking times per month: {}", totalInvokingTimesPerMonth);

        Optional<Datapoints> max = cesMetricDataResp.getDatapoints()
            .stream()
            .max(Comparator.comparingLong(Datapoints::getTimestamp));

        double totalInvokingTimesCurrentDay = 0d;
        if (max.isPresent()) {
            totalInvokingTimesCurrentDay = max.get().getSum();
            log.info("Total invoking times current day: {}", totalInvokingTimesCurrentDay);
        }

        List<Datapoints> collectTop7 = cesMetricDataResp.getDatapoints()
            .stream()
            .sorted(Comparator.comparingLong(Datapoints::getTimestamp).reversed())
            .limit(DEFAULT_LIMIT)
            .toList();

        double totalInvokingTimesPerWeek = collectTop7.stream().mapToDouble(Datapoints::getSum).sum();
        log.info("Total invoking times per week: {}", totalInvokingTimesPerWeek);

        McpServiceStatisticResp mcpServiceStatisticResp = new McpServiceStatisticResp();
        mcpServiceStatisticResp.setTotalInvokingTimesPerMonth(totalInvokingTimesPerMonth);
        mcpServiceStatisticResp.setTotalInvokingTimesCurrentDay(totalInvokingTimesCurrentDay);
        mcpServiceStatisticResp.setTotalInvokingTimesCurrentWeek(totalInvokingTimesPerWeek);
        mcpServiceStatisticResp.setTotalInvokingTimes(totalInvokingTimes);

        log.info("Finished calculating statistics for service ID: {}", serviceId);
        return mcpServiceStatisticResp;
    }

    /**
     * 调用ces接口获取mcp的调用信息
     *
     */
    public Map<String, Long> mcpServicesCesStatisticListMcp(String projectId, String workspaceId,
        IdListRequest idListRequest) {
        log.info("Operation log: Start to query MCP service statistic list. Project ID: {}", projectId);

        String tenantId = RequestContextUtils.getRequestUserDomainId();

        Map<String, Long> result = new HashMap<>();

        if (idListRequest == null || CollectionUtils.isEmpty(idListRequest.getIds())) {
            log.warn("No service IDs provided in the request.");
            return result;
        }

        LocalDateTime now = LocalDateTime.now();
        LocalDateTime startDateTime = now.minusDays(DEFAULT_DAY).with(LocalTime.MIN);
        log.info("Querying statistics from: {} to: {}", startDateTime, now);

        long from = startDateTime.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli();
        long to = now.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli();

        for (String serviceId : idListRequest.getIds()) {
            log.info("Processing service ID: {}", serviceId);

            McpServiceEntity serviceEntity = serviceDao.getMcpServiceByIdAndTenant(serviceId, tenantId,
                CommonUtil.getDeptCode(), workspaceId);
            if (ObjectUtils.isEmpty(serviceEntity)) {
                log.warn("Service not found. Service ID: {}", serviceId);
                continue;
            }
            if (Strings.CI.equals(serviceEntity.getOrgType(), EnumOrgType.SSE.getValue()) ||
                Strings.CI.equals(serviceEntity.getOrgType(), EnumOrgType.STREAMABLE_HTTP.getValue())) { // 新增
                log.info("Service type is SSE/streamable_http, skipping statistics. Service ID: {}", serviceId);
                continue;
            }

            CesMetricDataResp cesMetricDataResp = cesService.mcpServicesCesByCountMetric(String.valueOf(from),
                String.valueOf(to), DEFAULT_PERIOD, serviceEntity.getFunctionName());
            if (cesMetricDataResp == null || CollectionUtils.isEmpty(cesMetricDataResp.getDatapoints())) {
                log.warn("No metric data found for service ID: {}", serviceId);
                result.put(serviceId, 0L);
                continue;
            }

            double totalInvokingTimes = cesMetricDataResp.getDatapoints()
                .stream()
                .mapToDouble(Datapoints::getSum)
                .sum();
            result.put(serviceId, (long) totalInvokingTimes);
        }

        log.info("Finished processing statistics for {} service(s).", idListRequest.getIds().size());
        return result;
    }

    /**
     * 调用ces接口获取mcp的调用次数的折线图
     *
     */
    public CesMetricDataResp mcpServicesCesLineChart(String projectId, String serviceId,
        McpServicesCesLineChartQo mcpServicesCesLineChartQo) {
        log.info("operation log {}:start to query the line chart of MCP call counts", projectId);
        String tenantId = RequestContextUtils.getRequestUserDomainId();

        McpServiceEntity serviceEntity = serviceDao.getMcpServiceByIdAndTenant(serviceId, tenantId,
            CommonUtil.getDeptCode(), mcpServicesCesLineChartQo.getWorkspaceId());

        if (ObjectUtils.isEmpty(serviceEntity)) {
            log.error("[mcpServicesCesLineChart] No MCP service found. Service ID: {}", serviceId);
            throw new AgentStudioException(StudioError.MCP_SERVICE_NOT_EXIST);
        }
        if (Strings.CI.equals(serviceEntity.getOrgType(), EnumOrgType.SSE.getValue()) ||
            Strings.CI.equals(serviceEntity.getOrgType(), EnumOrgType.STREAMABLE_HTTP.getValue())) { // 新增
            log.info("Service type is SSE/streamable_http, returning empty chart data. Service ID: {}", serviceId);
            return new CesMetricDataResp();
        }

        log.info("Querying CES metric data for service ID: {}", serviceId);
        CesMetricDataResp cesMetricDataResp = cesService.mcpServicesCesByCountMetric(
            mcpServicesCesLineChartQo.getFrom(), mcpServicesCesLineChartQo.getTo(),
            mcpServicesCesLineChartQo.getPeriod(), serviceEntity.getFunctionName());

        if (cesMetricDataResp == null || CollectionUtils.isEmpty(cesMetricDataResp.getDatapoints())) {
            log.warn("No metric data found for service ID: {}", serviceId);
            return new CesMetricDataResp();
        }

        log.info("Calculating max and min values from datapoints.");
        Optional<Datapoints> max = cesMetricDataResp.getDatapoints()
            .stream()
            .max(Comparator.comparingDouble(Datapoints::getSum));
        Datapoints datapointsMax = max.orElse(null);

        Optional<Datapoints> min = cesMetricDataResp.getDatapoints()
            .stream()
            .min(Comparator.comparingDouble(Datapoints::getSum));
        Datapoints datapointsMin = min.orElse(null);

        cesMetricDataResp.setMax(
            (datapointsMax == null || datapointsMax.getSum() == null) ? 0d : datapointsMax.getSum());
        cesMetricDataResp.setMin(
            (datapointsMin == null || datapointsMin.getSum() == null) ? 0d : datapointsMin.getSum());

        log.info("Finished processing line chart data for service ID: {}", serviceId);
        return cesMetricDataResp;
    }

    /**
     * 调用ces接口获取mcp的调用次数的折线图
     *
     */
    public CesMetricDataResp mcpServicesCesSuccessRateLineChart(String projectId, String serviceId,
        McpServicesCesSuccessRateLineChartQo param) {
        log.info("Operation log: Start to query the line chart of MCP call success rate. Project ID: {}", projectId);

        String tenantId = RequestContextUtils.getRequestUserDomainId();


        McpServiceEntity serviceEntity = serviceDao.getMcpServiceByIdAndTenant(serviceId, tenantId,
            CommonUtil.getDeptCode(), param.getWorkspaceId());

        if (ObjectUtils.isEmpty(serviceEntity)) {
            log.error("[mcpServicesCesSuccessRateLineChart] No MCP service found. Service ID: {}", serviceId);
            throw new AgentStudioException(StudioError.MCP_SERVICE_NOT_EXIST);
        }
        if (Strings.CI.equals(serviceEntity.getOrgType(), EnumOrgType.SSE.getValue()) ||
            Strings.CI.equals(serviceEntity.getOrgType(), EnumOrgType.STREAMABLE_HTTP.getValue())) { // 新增
            log.info("Service type is SSE/streamable_http, returning empty chart data. Service ID: {}", serviceId);
            return new CesMetricDataResp();
        }

        log.info("Querying CES success rate metric data for service ID: {}", serviceId);
        CesMetricDataResp cesFailRateResp = cesService.mcpServicesCesByFailRateMetric(param.getFrom(), param.getTo(),
            param.getPeriod(), serviceEntity.getFunctionName());

        if (cesFailRateResp == null || CollectionUtils.isEmpty(cesFailRateResp.getDatapoints())) {
            log.warn("No success rate metric data found for service ID: {}", serviceId);
            return new CesMetricDataResp();
        }

        log.info("Processing and formatting success rate data.");
        cesFailRateResp.getDatapoints()
            .forEach(dp -> dp.setAverage(
                BigDecimal.valueOf(dp.getAverage()).setScale(2, RoundingMode.HALF_UP).doubleValue()));

        cesFailRateResp.setMetricName("successRate");

        log.info("Calculating max and min success rate values.");
        Optional<Datapoints> max = cesFailRateResp.getDatapoints()
            .stream()
            .max(Comparator.comparingDouble(Datapoints::getAverage));
        Datapoints datapointsMax = max.orElse(null);

        Optional<Datapoints> min = cesFailRateResp.getDatapoints()
            .stream()
            .min(Comparator.comparingDouble(Datapoints::getAverage));
        Datapoints datapointsMin = min.orElse(null);

        cesFailRateResp.setMax(
            (datapointsMax == null || datapointsMax.getAverage() == null) ? 0d : datapointsMax.getAverage());
        cesFailRateResp.setMin(
            (datapointsMin == null || datapointsMin.getAverage() == null) ? 0d : datapointsMin.getAverage());

        log.info("Finished processing success rate line chart data for service ID: {}", serviceId);
        return cesFailRateResp;
    }

    /**
     * 装量、阅读量、创建时间排序 取前几条记录  页面服务推荐展示
     *
     */
    public List<McpServerBaseInfoDto> mcpServerRecommendation(String projectId, String workspaceId) {
        log.info("Operation log: Start to get MCP server recommendation. Project ID: {}", projectId);

        CommonUtil.validateTenantIdIsNotEmpty();
        log.info("Tenant ID validation passed.");

        List<McpServerEntity> mcpServerEntities = serverDao.selectServerList();

        if (CollectionUtils.isEmpty(mcpServerEntities)) {
            log.warn("No MCP server entities found.");
            return new ArrayList<>();
        }

        log.info("Found {} MCP server entities.", mcpServerEntities.size());

        List<String> serverIds = mcpServerEntities.stream()
            .map(McpServerEntity::getId)
            .toList();

        log.info("Querying scores for {} server(s).", serverIds.size());

        List<ServerScore> serverScores = mcpServerRatingDao.queryScoreByServerIds(serverIds);

        return mcpServerEntities.stream().map(mcp -> {
            McpServerBaseInfoDto mcpServerBaseInfoDto = mcpUtil.serverEntity2McpBaseInfoDto(mcp);
            double score = calculatedScore(mcp.getId(), serverScores);
            mcpServerBaseInfoDto.setScore(score);
            return mcpServerBaseInfoDto;
        }).toList();
    }

    /**
     * mcp服务评分
     *
     */
    public Boolean mcpServerRating(String projectId, String workspaceId, McpServerRatingReq mcpServerRatingReq) {
        log.info("Operation log: Start to rate MCP server. Project ID: {}", projectId);

        String tenantId = RequestContextUtils.getRequestUserDomainId();
        if (StringUtils.isBlank(tenantId)) {
            log.error("Tenant ID is empty, cannot proceed with rating.");
            McpServiceExceptionUtils.throwMissingParameterError("tenantId");
        }

        log.info("Validating rating request parameters.");
        // 校验评分是否合法
        validScore(mcpServerRatingReq);

        McpServerEntity mcpServerEntity = serverDao.selectById(mcpServerRatingReq.getServerId());
        if (mcpServerEntity == null) {
            log.error("Server not found. Server ID: {}", mcpServerRatingReq.getServerId());
            throw new AgentStudioException(StudioError.MCP_SERVICE_NOT_EXIST);
        }

        if (!CommonUtil.isIntegerAndLessThan10(mcpServerRatingReq.getScore())) {
            log.error("Invalid score value: {}", mcpServerRatingReq.getScore());
            McpServiceExceptionUtils.throwMissingParameterError("score");
        }

        log.info("Preparing to insert server rating. Server ID: {}, Score: {}",
            mcpServerRatingReq.getServerId(), mcpServerRatingReq.getScore());

        McpServerRatingEntity mcpServerRatingEntity = new McpServerRatingEntity();
        mcpServerRatingEntity.setCreatedDate(new Timestamp(new Date().getTime()));
        mcpServerRatingEntity.setServerId(mcpServerRatingReq.getServerId());
        mcpServerRatingEntity.setScore(Integer.parseInt(mcpServerRatingReq.getScore()));
        mcpServerRatingEntity.setTenantId(tenantId);
        return mcpServerRatingDao.insert(mcpServerRatingEntity) > 0;
    }

    private void validScore(McpServerRatingReq mcpServerRatingReq) {
        log.info("Start to validate server rating score. Input score: {}", mcpServerRatingReq.getScore());

        try {
            int score = Integer.parseInt(mcpServerRatingReq.getScore());
            if (score < 0 || score > 10) {
                log.error("Score value is out of valid range (0-10). Input score: {}", score);
                throw new AgentStudioException(StudioError.SCORE_PARAM_INVALID);
            }
            log.info("Score validation passed. Score: {}", score);
        } catch (Exception e) {
            log.error("Failed to parse or validate score. Input score: {}", mcpServerRatingReq.getScore(), e);
            throw new AgentStudioException(StudioError.SCORE_PARAM_INVALID);
        }
    }

    /**
     * 统计用户部署的mcp信息
     *
     */
    public Map<String, Integer> listServicesSummary(String projectId, String workspaceId) {
        log.info("operation log {}:start to list mcp services summary", projectId);
        String tenantId = RequestContextUtils.getRequestUserDomainId();
        List<McpServiceEntity> mcpServiceEntities = serviceDao.listMcpServiceByTenant(tenantId, workspaceId);
        List<McpServiceEntity> privateMcp = mcpServiceEntities.stream()
            .filter(mcp -> Strings.CI.equals(mcp.getServerId(), "1"))
            .toList();
        return Map.of("private_mcp", privateMcp.size(), "inner_mcp", mcpServiceEntities.size() - privateMcp.size(),
            "total_mcp", mcpServiceEntities.size());
    }

    private String decryptConfig(String config) {
        if (config.contains("mcpServers")) {
            return config;
        } else {
            return encryptionAdapter.decrypt(config);
        }
    }

    /**
     * 工作流中查询mcp服务工具
     *
     */

    public McpServiceToolsEntity mcpServicesToolsListWithFlow(String projectId, String workspaceId, String serviceId) {
        log.info("Operation log: Start to query MCP tools detail with flow. Project ID: {}", projectId);

        String tenantId = RequestContextUtils.getRequestUserDomainId();
        String authToken = RequestContextUtils.getRequestAuthToken();

        CommonUtil.validateProjectAndWorkspaceId(projectId, workspaceId);
        log.info("Project and workspace ID validation passed.");

        McpServiceEntity serviceEntity = serviceDao.getMcpServiceById(serviceId, tenantId, CommonUtil.getDeptCode(),
            projectId, workspaceId);

        if (ObjectUtils.isEmpty(serviceEntity)) {
            // 判断是不是团队共享mcp
            // 增加共享判断，如果插件被共享到当前空间,则可以使用
            return mcpUtil.mcpServiceEntity2McpServiceToolsEntity(getShareMcp(serviceId, workspaceId));
        }

        log.info("Service found. Service ID: {}", serviceId);

        McpServiceToolsEntity mcpServiceToolsEntity = mcpUtil.mcpServiceEntity2McpServiceToolsEntity(serviceEntity);

        if (StringUtils.isNotBlank(serviceEntity.getTools())) {
            log.info("Tools already exist in DB. Starting async update task.");
            mcpTaskExecutor.execute(() -> {
                try {
                    // 设置上下文
                    RequestContextUtils.setContext(authToken, projectId, tenantId);
                    this.getMcpServiceToolListAndUpdate(serviceEntity);
                } catch (Throwable t) {
                    log.error("Async update (Flow) failed for service: {}", serviceId, t);
                } finally {
                    RequestContextUtils.remove(); // 清理
                }
            });

            mcpServiceToolsEntity.setTools(
                McpJsonUtils.parseToolFromString(serviceEntity.getTools(), serviceEntity.getName()));
            return mcpServiceToolsEntity;
        }

        log.info("No tools found in DB. Starting to fetch from MCP.");
        String mcpUrl = serviceEntity.getFcInstanceUrl();

        String query = CommonUtil.getRawQueryString(CommonUtil.parseUrlFromMcpConfig(
            JSONObject.parseObject(encryptionAdapter.decrypt(serviceEntity.getServerConfig())), 0));

        if (!StringUtils.isEmpty(query)) {
            mcpUrl += "?" + query;
            log.info("Appending query parameters to URL: {}", query);
        }

        Map<String, String> headerInfo = new HashMap<>();
        if (!StringUtils.isEmpty(serviceEntity.getAuthType()) && Strings.CI.equals(
            serviceEntity.getAuthType(), "IAM-TOKEN")) {
            log.info("Using IAM-TOKEN authentication.");
            headerInfo.put("X-Auth-Token", RequestContextUtils.getRequestAuthToken());
            constructHeaderInfo(RequestContextUtils.getRequestWorkspaceId(), headerInfo);
        } else if (!StringUtils.isEmpty(serviceEntity.getAuthType()) && Strings.CI.equals(
            serviceEntity.getAuthType(), CommonConstant.MCP_AUTH_TYPE.USE_IAM_TOKEN)) {
            log.info("Using USE_IAM_TOKEN authentication.");
            String token = null;
            try {
                token = RequestContextUtils.getRequestAuthToken();
            } catch (AgentStudioException e) {
                // 跨线程无法传递token，使用serviceEntity临时传递
                token = serviceEntity.getTempToken();
            }
            headerInfo.put("X-Auth-Token", token);
        } else {
            log.info("Parsing headers from server config.");
            headerInfo = CommonUtil.parseMcpConfigHeaderInfo(encryptionAdapter.decrypt(serviceEntity.getServerConfig()));
        }

        // 自定义 apikey 鉴权：出站前对 cust-* 做配置驱动 rename（cust-token→token, cust-userid→userId）
        McpCustomerHeaderProjection.renameOutboundCustomerHeaders(headerInfo, serviceEntity.getName());

        List<McpSchema.Tool> toolList = mcpClientService.getMcpServiceToolList(serviceEntity.getName(), mcpUrl,
            serviceEntity.getOrgType(), headerInfo);

        if (CollectionUtils.isEmpty(toolList)) {
            log.warn("No tool list returned from MCP. Service ID: {}", serviceId);
            return new McpServiceToolsEntity();
        }

        String tools = McpJsonUtils.toJson(toolList);
        mcpTaskExecutor.execute(() -> {
            try {
                RequestContextUtils.setContext(authToken, projectId, tenantId);
                serviceDao.updateTools(serviceEntity.getId(), tools, tenantId);
                if (serviceEntity.getOrgType().equals(EnumOrgType.NPX.toString()) ||
                    serviceEntity.getOrgType().equals(EnumOrgType.UVX.toString())) {
                    serviceDao.updateFcInstanceStatus(serviceEntity.getId(), EnumMcpStatus.SUCCESS.getValue(),
                        tenantId, CommonUtil.getDeptCode());
                }
            } catch (Throwable t) {
                log.error("Async update (Flow/New) failed for service: {}", serviceId, t);
            } finally {
                RequestContextUtils.remove(); // 清理
            }
        });
        mcpServiceToolsEntity.setTools(McpJsonUtils.parseToolFromString(tools, serviceEntity.getName()));
        log.info("Finished processing tools for service ID: {}", serviceId);
        return mcpServiceToolsEntity;
    }

    /**
     * 修改mcp服务信息 只有sse方式执行修改配置，如果配置变更后， 需要清空工具信息及异步同步工具
     * 增加故障自愈逻辑。如果配置变更 OR 当前状态为失败，都触发异步工具获取。
     */
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "McpService",
        description = "修改MCP服务信息",
        resourceId = "serviceReq.id",
        resourceName = ""
    )
    public Boolean modifyService(String projectId, String workspaceId, McpServiceModifyReq serviceReq) {
        log.info("Operation log: Start to modify MCP service. Project ID: {}", projectId);

        String tenantId = RequestContextUtils.getRequestUserDomainId();
        String authToken = RequestContextUtils.getRequestAuthToken();

        if (StringUtils.isNotBlank(serviceReq.getIcon())) {
            log.info("Validating service icon.");
            ImageBase64Utils.validateImage(serviceReq.getIcon());
        }

        CommonUtil.validateProjectAndWorkspaceId(projectId, workspaceId);
        log.info("Project and workspace ID validation passed.");

        McpServiceEntity mcpServiceFromDb = this.serviceDao.getMcpServiceById(serviceReq.getId(), tenantId,
            CommonUtil.getDeptCode(), projectId, workspaceId);
        McpServiceEntity modifyService = new McpServiceEntity();
        if (mcpServiceFromDb == null) {
            log.error("MCP service not found. Service ID: {}", serviceReq.getId());
            throw new AgentStudioException(StudioError.MCP_SERVICE_NOT_EXIST);
        }
        if (StringUtils.isBlank(mcpServiceFromDb.getOrgType())) {
            log.error("orgType is invalid: {}", mcpServiceFromDb.getOrgType());
            throw new AgentStudioException(StudioError.MCP_SERVICE_ORG_TYPE_EMPTY, mcpServiceFromDb.getOrgType());
        }
        try {
            // STREAMABLE_HTTP("streamable_http")没办法直接用EnumOrgType.valueOf(mcpServiceFromDb.getOrgType());使用if校验streamable_http
            // 判断类型只能是SSE,UVX,NPX,streamable_http
            if (!Strings.CI.equals(mcpServiceFromDb.getOrgType(), EnumOrgType.STREAMABLE_HTTP.getValue())) {
                EnumOrgType.valueOf(mcpServiceFromDb.getOrgType());
            }
        } catch (IllegalArgumentException e) {
            log.error("orgType is invalid: {}", mcpServiceFromDb.getOrgType());
            throw new AgentStudioException(StudioError.MCP_SERVICE_ORG_TYPE_INVALID, mcpServiceFromDb.getOrgType());
        }
        if (!StringUtils.isBlank(serviceReq.getName())) {
            if (serviceReq.getName().length() > 64 || !NAME_PATTERN.matcher(serviceReq.getName()).matches()) {
                log.error("service name is invalid: {}", serviceReq.getName());
                throw new AgentStudioException(StudioError.MCP_SERVICE_NAME_INVALID);
            }
        }
        log.info("Service found. Starting name duplication check.");
        this.checkMcpNameDuplication(serviceReq, mcpServiceFromDb, workspaceId);

        // 判断当前状态是否为失败 (故障自愈触发条件)
        boolean isStatusFailed = EnumMcpStatus.STACK_FAIL.getValue().equals(mcpServiceFromDb.getFcInstanceStatus());
        boolean isConfigUpdated = false;

        // 增加 OR STREAMABLE_HTTP 判断
        if ((mcpServiceFromDb.getOrgType().equalsIgnoreCase(EnumOrgType.SSE.getValue()) ||
            mcpServiceFromDb.getOrgType().equalsIgnoreCase(EnumOrgType.STREAMABLE_HTTP.getValue()))
            && StringUtils.isNotBlank(serviceReq.getServerConfig())) {

            log.info("Parsing and validating server config for SSE/streamable_http service.");

            // 捕获 JSON 格式校验异常 (1146)
            try {
                JSONObject jsonObject = JSONObject.parseObject(serviceReq.getServerConfig());
                String url = removeQueryParamsFromUrl(CommonUtil.parseUrlFromMcpConfig(jsonObject, 0));

                // 配置修改判断
                isConfigUpdated = !Strings.CI.equals(encryptionAdapter.decrypt(mcpServiceFromDb.getServerConfig()),
                    serviceReq.getServerConfig());

                if (isConfigUpdated) {
                    log.info("Server config has been updated. Resetting instance URL.");
                    checkSwaggerUrlValid(url, connectorConfigHostBlacklist);
                    modifyService.setFcInstanceUrl(url);
                    mcpServiceFromDb.setFcInstanceUrl(url);
                    modifyService.setTools("");
                }
            } catch (Exception e) {
                log.error("MCP config format validation failed in modify", e);
                throw new AgentStudioException(StudioError.MCP_CONFIG_FORMAT_INVALID);
            }
        }

        mcpBase.validAuthInfo(serviceReq.getAuthInfo());
        // 判断oauth是否更新，如果更新，则需要重新部署MCP
        boolean isAUthInfoUpdated = false;
        if (serviceReq.getAuthInfo() != null) {
            isAUthInfoUpdated = !serviceReq.getAuthInfo().equals(mcpBase.decryptedAuthInfo(mcpServiceFromDb.getAuthInfo()));
        }
        // authInfo信息加密
        serviceReq.setAuthInfo(mcpBase.encryptedAuthInfo(serviceReq.getAuthInfo()));

        // 只要配置变更 OR 之前状态是失败，都重置状态并触发后续任务
        boolean shouldTriggerAsync = isConfigUpdated || isStatusFailed || isAUthInfoUpdated;
        if (shouldTriggerAsync) {
            log.info("Triggering re-deploy status reset. ConfigUpdated: {}, StatusFailed: {}", isConfigUpdated, isStatusFailed);
            modifyService.setFcInstanceStatus(EnumMcpStatus.CREATING_STACK.getValue());
            // 清空旧的失败原因
            modifyService.setFailReason("");
        }

        log.info("Preparing to update service fields.");
        modifyService.setServerConfig(encryptionAdapter.encrypt(serviceReq.getServerConfig(), tenantId));
        modifyService.setId(serviceReq.getId());
        modifyService.setName(serviceReq.getName());
        modifyService.setNameEn(serviceReq.getNameEn());
        modifyService.setDescription(serviceReq.getDescription());
        modifyService.setDescriptionEn(serviceReq.getDescriptionEn());
        modifyService.setIcon(serviceReq.getIcon());
        modifyService.setTenantId(tenantId);
        modifyService.setReadme(serviceReq.getReadme());
        modifyService.setAuthInfo(mcpBase.validIsNeedToUpdateAuthInfo(serviceReq.getAuthInfo(), mcpServiceFromDb.getAuthInfo()));

        int count = this.serviceDao.update(modifyService);
        log.info("Service update result: {} rows affected.", count);

        // 使用 shouldTriggerAsync 判断，且在异步线程中重新查询完整实体
        if (count > 0 && shouldTriggerAsync) {
            log.info("Starting async task to fetch tools and update status.");
            mcpTaskExecutor.execute(() -> {
                try {
                    RequestContextUtils.setContext(authToken, projectId, tenantId);
                    // modifyService 是部分对象，不包含 url/orgType 等完整信息。
                    // 必须重新查询最新的完整实体，否则 getMcpServiceToolListAndUpdateStatus 会报错
                    McpServiceEntity latestEntity = this.serviceDao.getMcpServiceById(serviceReq.getId(), tenantId,
                        CommonUtil.getDeptCode(), projectId, workspaceId);

                    if (latestEntity != null) {
                        this.getMcpServiceToolListAndUpdateStatus(latestEntity);
                    }
                } catch (Throwable t) {
                    log.error("Async update tools failed for service: {}", serviceReq.getId(), t);
                    // 兜底回滚状态
                    try {
                        this.serviceDao.updateStatus(serviceReq.getId(), EnumMcpStatus.STACK_FAIL.getValue(),
                            tenantId, CommonUtil.getDeptCode());
                    } catch (Exception ex) {
                        log.error("Failed to rollback status", ex);
                    }
                } finally {
                    RequestContextUtils.remove();
                }
            });
        }

        return count > 0;
    }

    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "McpService",
        description = "修改MCP服务鉴权信息",
        resourceId = "id",
        resourceName = ""
    )
    public Boolean updateMcpAuthInfo(String projectId, String id, String workspaceId, AuthInfo authInfo){
        String tenantId = RequestContextUtils.getRequestUserDomainId();
        String authToken = RequestContextUtils.getRequestAuthToken();
        // 判断MCP是否存在
        McpServiceEntity mcpServiceFromDb = this.serviceDao.getMcpServiceById(id, tenantId,
                CommonUtil.getDeptCode(), projectId, workspaceId);
        if (mcpServiceFromDb == null) {
            log.error("MCP service not found. Service ID: {}", id);
            throw new AgentStudioException(StudioError.MCP_SERVICE_NOT_EXIST);
        }
        // 设置MCP部署状态为部署中
        String fcInstanceUrl = EnumMcpStatus.CREATING_STACK.getValue();
        // 清空旧的失败原因
        String failReason = "";
        mcpBase.validAuthInfo(authInfo);
        AuthInfo authInfoEncrypted = mcpBase.encryptedAuthInfo(authInfo);  // authInfo key值加密
        int count = this.serviceDao.updateAuthInfo(id, authInfoEncrypted, fcInstanceUrl, failReason);
        // 如果数据库更新成功，就重新部署
        if (count > 0) {
            log.info("Starting async task to fetch tools and update status.");
            mcpTaskExecutor.execute(() -> {
                try {
                    RequestContextUtils.setContext(authToken, projectId, tenantId);
                    // modifyService 是部分对象，不包含 url/orgType 等完整信息。
                    // 必须重新查询最新的完整实体，否则 getMcpServiceToolListAndUpdateStatus 会报错
                    McpServiceEntity latestEntity = this.serviceDao.getMcpServiceById(id, tenantId,
                            CommonUtil.getDeptCode(), projectId, workspaceId);

                    if (latestEntity != null) {
                        this.getMcpServiceToolListAndUpdateStatus(latestEntity);
                    }
                } catch (Throwable t) {
                    log.error("Async update tools failed for service: {}", id, t);
                    // 兜底回滚状态
                    try {
                        this.serviceDao.updateStatus(id, EnumMcpStatus.STACK_FAIL.getValue(),
                                tenantId, CommonUtil.getDeptCode());
                    } catch (Exception ex) {
                        log.error("Failed to rollback status", ex);
                    }
                } finally {
                    RequestContextUtils.remove();
                }
            });
        }
        return count > 0;
    }
    /**
     * 验证MCP名称是否重复
     *
     */
    public void checkMcpNameDuplication(McpServiceModifyReq serviceReq, McpServiceEntity mcpServiceFromDb, String workspaceId) {
        if (StringUtils.isNotBlank(serviceReq.getName()) && !mcpNameEnCheck) {
            checkMcpNameZhDuplication(serviceReq, mcpServiceFromDb, workspaceId);
        }
        if(StringUtils.isNotBlank(serviceReq.getNameEn()) && mcpNameEnCheck) {
            checkMcpNameEnDuplication(serviceReq, mcpServiceFromDb, workspaceId);
        }
    }

    public void checkMcpNameZhDuplication(McpServiceModifyReq serviceReq, McpServiceEntity mcpServiceFromDb, String workspaceId) {
        List<McpServiceEntity> existService;
        if (!Strings.CI.equals(serviceReq.getName(), mcpServiceFromDb.getName())) {
            existService = serviceDao.getMcpServiceByNameAndTenant(serviceReq.getName(),
                RequestContextUtils.getRequestUserDomainId(), CommonUtil.getDeptCode(), workspaceId);
            if (!CollectionUtils.isEmpty(existService)) {
                if(existService.size() > 1 || (existService.size() == 1 && !existService.get(0).getId().equals(serviceReq.getId()))) {
                    log.error("service with name {} already exist", serviceReq.getName());
                    throw new AgentStudioException(StudioError.MCP_NAME_DUPLICATE);
                }
            }
        }
    }

    public void checkMcpNameEnDuplication(McpServiceModifyReq serviceReq, McpServiceEntity mcpServiceFromDb, String workspaceId) {
        List<McpServiceEntity> existService;
        if(!Strings.CI.equals(serviceReq.getNameEn(), mcpServiceFromDb.getNameEn())) {
            existService = serviceDao.getMcpServiceByNameEnAndTenant(serviceReq.getNameEn(),
                RequestContextUtils.getRequestUserDomainId(), CommonUtil.getDeptCode(), workspaceId);
            if (!CollectionUtils.isEmpty(existService)) {
                if(existService.size() > 1 || (existService.size() == 1 && !existService.get(0).getId().equals(serviceReq.getId()))) {
                    log.error("service with nameEn {} already exist", serviceReq.getNameEn());
                    throw new AgentStudioException(StudioError.MCP_NAME_DUPLICATE);
                }
            }
        }
    }

    @Override
    public McpDataProcessBaseInfoListResp dataProcessList(String projectId, String workspaceId, String language,
        String name, PageInfoV2 body) {
        log.info("operation log {}:start to query data processing list", projectId);
        String templateString = CommonUtil.getResourceContent(
            "template/data-process-mcp.json");
        return JSONObject.parseObject(templateString, McpDataProcessBaseInfoListResp.class);
    }

    /**
     * host 合法性检查
     *
     * @param swaggerUrl 调用url
     * @param hostBlackList 连接器host黑名单
     */
    public void checkSwaggerUrlValid(String swaggerUrl, String hostBlackList) {
        log.info("Start: check url {} from black list.", swaggerUrl);
        if (hostBlackList.isEmpty()) {
            return;
        }
        Set<String> connectorHostBlackList = Arrays.stream(hostBlackList.split(","))
            .map(String::trim)
            .collect(Collectors.toSet());
        if (!enableUrlCheck) {
            log.info("not check from black list");
            return;
        }
        try {
            URI uri = new URI(swaggerUrl);
            String host = uri.getHost();
            checkHostValid(host, connectorHostBlackList);
            try {
                InetAddress[] addresses = InetAddress.getAllByName(host);
                for (InetAddress address : addresses) {
                    checkHostValid(address.getHostAddress(), connectorHostBlackList);
                }
            } catch (UnknownHostException e) {
                // 不做控制，运行态DNS一样，有问题会调不通，没有影响
                log.warn("swagger base url is Unknown Host: {}", host);
            }
        } catch (URISyntaxException e) {
            // URL 格式本身不对，报 1029 是对的，或者报 1146 也可以
            throw new AgentStudioException(StudioError.INVALID_URL);
        } catch (Exception e) {
            // 捕获其他异常，防止程序崩溃
            // 只要是黑名单校验不通过，就抛出 1151
            log.error("Error while checking swagger URL: {}", swaggerUrl, e);
            throw new AgentStudioException(StudioError.MCP_ADDRESS_RESTRICTED);
        }
        log.info("End: check url from black list.");
    }

    /**
     * host 合法性检查
     *
     * @param host host
     * @param connectorHostBlackList 连接器host黑名单
     */
    private static void checkHostValid(String host, Set<String> connectorHostBlackList) {
        // 判断host是否在黑名单中
        if (connectorHostBlackList.contains(host)) {
            log.warn("checkHostValid failed, host: {}", host);
            throw new AgentStudioException(StudioError.INVALID_URL);
        }

        // 判断网段
        try {
            IPAddressString hostAddress = new IPAddressString(host);
            for (String ips : connectorHostBlackList) {
                if (StringUtils.isEmpty(ips)) continue;
                try {
                    IPAddressString ipAddress = new IPAddressString(ips);
                    if (ipAddress.contains(hostAddress) || host.contains(ips)) {
                        log.warn("checkHostValid failed, ipAddress:{}, hostAddress: {}, host: {}, ips:{}", ipAddress,
                            hostAddress, host, ips);
                        throw new AgentStudioException(StudioError.INVALID_URL);
                    }
                } catch (IllegalArgumentException e) {
                    // 忽略非法的IP格式
                    log.warn("Invalid IP format in blacklist: {}", ips);
                }
            }
        } catch (IllegalArgumentException e) {
            // host 不是合法的IP地址，可能是域名，不进行网段判断
            log.warn("Host is not a valid IP address, skip subnet check: {}", host);
        }
    }
}
