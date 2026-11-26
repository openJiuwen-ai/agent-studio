
/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.utils;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.alibaba.fastjson.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.McpServerBaseInfoDto;
import com.openjiuwen.studio.agent.manager.dto.McpServerDetailInfoDto;
import com.openjiuwen.studio.agent.manager.dto.McpServerDetailReq;
import com.openjiuwen.studio.agent.manager.dto.McpServerRuntimeVo;
import com.openjiuwen.studio.agent.manager.dto.McpServiceBaseInfoDto;
import com.openjiuwen.studio.agent.manager.dto.McpServiceBatchDeployItem;
import com.openjiuwen.studio.agent.manager.dto.McpServiceDeployReq;
import com.openjiuwen.studio.agent.manager.dto.McpServiceDetailInfoDto;
import com.openjiuwen.studio.agent.manager.dto.McpServiceSkinnyEntity;
import com.openjiuwen.studio.agent.manager.dto.McpServiceToolsEntity;
import com.openjiuwen.studio.agent.manager.entity.McpServerEntity;
import com.openjiuwen.studio.agent.manager.entity.McpServiceEntity;
import com.openjiuwen.studio.agent.manager.service.mcp.infrastructure.apig.ApigService;
import com.openjiuwen.studio.agent.manager.service.mcp.model.ImportMcpServiceDependencyCheck;
import com.openjiuwen.studio.agent.manager.service.mcp.model.McpServiceFromProject;
import com.openjiuwen.studio.agent.manager.service.mcp.model.apig.ApigApiGroupDetailResp;
import com.openjiuwen.studio.agent.manager.service.mcp.model.apig.ApigBindDomainCertificateReq;
import com.openjiuwen.studio.agent.manager.service.mcp.model.apig.ApigBindDomainsReq;
import com.openjiuwen.studio.agent.manager.service.mcp.model.apig.ApigBindDomainsResp;
import com.openjiuwen.studio.agent.manager.service.mcp.model.apig.SslInfo;
import com.openjiuwen.studio.agent.manager.service.mcp.model.apig.UrlDomain;
import com.openjiuwen.studio.agent.manager.service.mcp.model.dao.McpServerDao;
import com.openjiuwen.studio.agent.manager.service.mcp.model.dao.McpServiceDao;
import com.openjiuwen.studio.common.service.service.EncryptionAdapter;
import com.openjiuwen.studio.agent.manager.dto.McpFailReasonDetailDto;

import jakarta.annotation.PostConstruct;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.util.CollectionUtils;

import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * MCP 工具类
 *
 */
@Slf4j
@Component
public class McpUtil {

    @PostConstruct
    public void decryptSensitiveFields() {
        mcpAuthSecret = CryptoUtils.decrypt(mcpAuthSecret);
    }

    @Resource
    private McpServerDao serverDao;

    @Resource
    private McpServiceDao serviceDao;

    @Resource
    private ApigService apigService;

    @Value("${agent.builder.mcp.domain:}")
    private String mcpSecondDomain;

    @Value("${agent.builder.mcp.custom.domain.switch:false}")
    private String bindDomainSwitch;

    @Value("${agent.builder.apigw.domain.cert.id:}")
    private String apigwDomainCertId;

    @Value("${apig.op.mcp_auth_secret:mcp_auth_secret}")
    private String mcpAuthSecret;

    @Value("${apig.op.mcp_auth_key:mcp_auth_key}")
    private String mcpAuthKey;

    @Value("${mcp.mcp-name-en-check:false}")
    private Boolean mcpNameEnCheck;

    @Value("${spring.is-soft-delete}")
    private Boolean isSoftDelete;

    @Autowired
    private EncryptionAdapter encryptionAdapter;

    public McpServerBaseInfoDto serverEntity2McpBaseInfoDto(McpServerEntity entity) {
        McpServerBaseInfoDto dto = new McpServerBaseInfoDto();
        BeanUtils.copyProperties(entity, dto);
        return dto;
    }

    public McpServiceBaseInfoDto serviceEntity2McpBaseInfoDto(McpServiceEntity entity) {
        McpServiceBaseInfoDto dto = new McpServiceBaseInfoDto();
        BeanUtils.copyProperties(entity, dto);
        fillFailReasonDetail(entity, dto);
        return dto;
    }

    public McpServiceFromProject serviceEntity2McpServiceFromProject(McpServiceEntity entity) {
        McpServiceFromProject dto = new McpServiceFromProject();
        BeanUtils.copyProperties(entity, dto);
        return dto;
    }

    public ImportMcpServiceDependencyCheck mcpServiceEntity2ImportMcpServiceFromProject(McpServiceEntity entity) {
        ImportMcpServiceDependencyCheck dto = new ImportMcpServiceDependencyCheck();
        BeanUtils.copyProperties(entity, dto);
        return dto;
    }

    public McpServiceToolsEntity mcpServiceEntity2McpServiceToolsEntity(McpServiceEntity entity) {
        McpServiceToolsEntity dto = new McpServiceToolsEntity();
        BeanUtils.copyProperties(entity, dto);
        return dto;
    }

    public McpServiceEntity mcpServiceFromProject2ServiceEntity(McpServiceFromProject mcpServiceFromProject) {
        McpServiceEntity entity = new McpServiceEntity();
        BeanUtils.copyProperties(mcpServiceFromProject, entity);
        return entity;
    }

    public McpServiceBaseInfoDto serviceEntity2McpBaseRuntimeInfoDto(McpServiceEntity entity) {
        McpServiceBaseInfoDto dto = new McpServiceBaseInfoDto();
        BeanUtils.copyProperties(entity, dto);
        fillFailReasonDetail(entity, dto);
        McpServerRuntimeVo agentMcp = new McpServerRuntimeVo();
        agentMcp.setId(entity.getId())
            .setName(entity.getName())
            .setType(entity.getDeployType())
            .setDescription(entity.getDescription());
        dto.setMcpServers(agentMcp);
        return dto;
    }

    public McpServerDetailInfoDto serverEntity2McpServerDetailInfoDto(McpServerEntity entity) {
        McpServerDetailInfoDto dto = new McpServerDetailInfoDto();
        BeanUtils.copyProperties(entity, dto);
        return dto;
    }

    public McpServiceDetailInfoDto serviceEntity2McpServiceDetailInfoDto(McpServiceEntity entity) {
        McpServiceDetailInfoDto dto = new McpServiceDetailInfoDto();
        BeanUtils.copyProperties(entity, dto);
        fillFailReasonDetail(entity, dto);
        return dto;
    }

    public McpServiceDetailInfoDto serviceReq2McpServiceDetailInfoDto(McpServiceDeployReq entity) {
        McpServiceDetailInfoDto dto = new McpServiceDetailInfoDto();
        BeanUtils.copyProperties(entity, dto);
        return dto;
    }

    public McpServiceDetailInfoDto serviceEntity2McpServiceRuntimeDetailInfoDto(McpServiceEntity entity) {
        McpServiceDetailInfoDto dto = new McpServiceDetailInfoDto();
        dto.setName(entity.getName()).setNameEn(entity.getNameEn());
        fillFailReasonDetail(entity, dto);
        McpServerRuntimeVo agentMcp = fillMcpRuntimeVo(entity);
        dto.setMcpServers(agentMcp);
        return dto;
    }

    public McpServerEntity mcpDetailInfoDto2ServerEntity(McpServerDetailReq serverDetail) {
        McpServerEntity entity = new McpServerEntity();
        try {
            String tools = serverDetail.getTools();
            JSON.parseObject(tools);
        } catch (Exception e) {
            log.error("tools is not json format. content is :{}", serverDetail.getTools());
            throw new AgentStudioException(StudioError.TOOLS_DATA_NOT_JSON_FORMAT);
        }
        BeanUtils.copyProperties(serverDetail, entity);
        if (StringUtils.isNotBlank(serverDetail.getId())) {
            List<McpServerEntity> mcpServerEntities = serverDao.listMineMcpServerEntities(serverDetail.getId(),
                CommonUtil.getTenantId(), CommonUtil.getDeptCode());
            if (!CollectionUtils.isEmpty(mcpServerEntities)) {
                entity.setId(serverDetail.getId());
                CommonUtil.setCommonUpdateProperties(entity);
                return entity;
            }
        }
        entity.setId(CommonUtil.getUUID());
        CommonUtil.setCommonCreateProperties(entity);
        return entity;
    }

    public void checkNameDuplication(McpServiceDetailInfoDto serviceDetail, String workspaceId) {
        List<McpServiceEntity> existService;
        existService = serviceDao.getMcpServiceByNameAndTenant(serviceDetail.getName(),
                    RequestContextUtils.getRequestUserDomainId(), CommonUtil.getDeptCode(), workspaceId);
        if (!CollectionUtils.isEmpty(existService)) {
            log.error("service {} is exist", serviceDetail.getName());
            throw new AgentStudioException(StudioError.MCP_SERVICE_IS_EXIST);
        }
    }

    public void checkNameEnDuplication(McpServiceDetailInfoDto serviceDetail, String workspaceId) {
        List<McpServiceEntity> existService;
        existService = serviceDao.getMcpServiceByNameEnAndTenant(serviceDetail.getNameEn(),
                    RequestContextUtils.getRequestUserDomainId(), CommonUtil.getDeptCode(), workspaceId);
        if (!CollectionUtils.isEmpty(existService)) {
            throw new AgentStudioException(StudioError.MCP_SERVICE_IS_EXIST);
        }
    }

    public McpServiceEntity mcpServiceDetailInfoDto2ServiceEntity(McpServiceDetailInfoDto serviceDetail,
        String workspaceId) {
        McpServiceEntity entity = new McpServiceEntity();
        if (!mcpNameEnCheck) {
            checkNameDuplication(serviceDetail, workspaceId);
        } else {
            checkNameEnDuplication(serviceDetail, workspaceId);
        }
        // 校验deployType字段，不允许前端指定
        if (StringUtils.isNotEmpty(serviceDetail.getDeployType())) {
            log.error("The deployment type cannot be specified. service name is {}", serviceDetail.getName());
            throw new AgentStudioException(StudioError.INVALID_PARAMETER_ERROR, "deployment-type");
        }
        BeanUtils.copyProperties(serviceDetail, entity);
        // FEAT-134回归修复：import_config_pending为数据库NOT NULL列，普通(非导入)链路DTO该字段缺省null，
        // copyProperties会用null覆盖实体默认值false，导致insert报
        // Column 'import_config_pending' cannot be null(openjiuwen.02001042)。
        // 在DTO->Entity转换边界归一化null->false；导入链路McpTransferService不走此转换且入库前显式set，语义不受影响。
        if (entity.getImportConfigPending() == null) {
            entity.setImportConfigPending(Boolean.FALSE);
        }
        if (StringUtils.isNotBlank(serviceDetail.getId())) {
            entity.setId(serviceDetail.getId());
            McpServiceEntity mcpServiceById = this.serviceDao.getMcpServiceOnlyById(serviceDetail.getId());
            if (mcpServiceById != null) {
                CommonUtil.setCommonUpdateProperties(entity);
            } else {
                CommonUtil.setCommonCreateProperties(entity);
            }
        } else {
            entity.setId(CommonUtil.getUUID());
            CommonUtil.setCommonCreateProperties(entity);
        }
        entity.setTraceId(entity.getId());
        return entity;
    }

    /**
     * 填充运行态MCP信息
     */
    public McpServerRuntimeVo fillMcpRuntimeVo(McpServiceEntity service) {
        McpServerRuntimeVo vo = new McpServerRuntimeVo();
        log.info(">>>fillMcpRuntimeVo {}", JSON.toJSONString(service));
        vo.setId(service.getId())
            .setName(service.getName())
            .setType(service.getDeployType())
            .setDescription(service.getDescription())
            .setBaseUrl(service.getFcInstanceUrl());
        fillMcpRuntimeVoWithConfig(encryptionAdapter.decrypt(service.getServerConfig()), vo);
        return vo;
    }

    public void fillMcpRuntimeVoWithConfig(String config, McpServerRuntimeVo service) {
        String oriConfig;
        oriConfig = config;
        JSONObject configObj = JSON.parseObject(oriConfig);
        try {
            Map<String, String> headerInfo = CommonUtil.parseMcpConfigHeaderInfo(oriConfig);
            service.setHeaders(headerInfo);
            JSONObject mcpServers = configObj.getJSONObject("mcpServers");
            // 拿不到name直接报错出去
            String mcpName = mcpServers.keySet().stream().findAny().get();
            JSONObject mcpConfig = mcpServers.getJSONObject(mcpName);
            String command = mcpConfig.getString("command");
            if (StringUtils.isNotEmpty(command)) {
                service.setCommand(command);
            }
            JSONArray args = mcpConfig.getJSONArray("args");
            if (ObjectUtils.isNotEmpty(args)) {
                service.setArgs(args.toJavaList(String.class));
            }
            JSONObject env = mcpConfig.getJSONObject("env");
            if (ObjectUtils.isNotEmpty(env)) {
                service.setEnv(env.toJavaObject(new TypeReference<>() { }));
            }
        } catch (Exception e) {
            log.error("mcp server config is not json format. MCP service name is :{}", service.getName());
        }
    }

    public void updateServiceDeletedInfoFromFG(String id, String tenantId, String deptCode) {
        if (isSoftDelete) {
            serviceDao.markAsDeleted(id, tenantId, deptCode);
        } else {
            serviceDao.hardDeleteSingleMcpServiceById(id, tenantId, deptCode);
        }
    }

    public void updateServiceStatus(String serviceId, String status, String tenantId, String deptCode) {
        serviceDao.updateStatus(serviceId, status, tenantId, deptCode);
    }

    public McpServiceSkinnyEntity serviceEntity2ServiceEntitySkinny(McpServiceEntity entity) {
        McpServiceSkinnyEntity serviceSkinny = new McpServiceSkinnyEntity();
        BeanUtils.copyProperties(entity, serviceSkinny);
        return serviceSkinny;
    }

    public String insertAuthHeadersIntoMcpServer(String jsonString) {
        ObjectMapper objectMapper = new ObjectMapper();
        try {
            // 将JSON字符串解析为JsonNode
            JsonNode rootNode = objectMapper.readTree(jsonString);
            // 检查 mcpServers 节点是否存在
            if (rootNode.has("mcpServers") && rootNode.get("mcpServers").isObject()) {
                ObjectNode mcpServersNode = (ObjectNode) rootNode.get("mcpServers");
                // 遍历 mcpServers 下的所有服务器配置
                mcpServersNode.fieldNames().forEachRemaining(serverName -> {
                    JsonNode serverConfigNode = mcpServersNode.get(serverName);
                    // 确保这是一个 ObjectNode 并且包含 command 字段
                    if (serverConfigNode.isObject() && serverConfigNode.has("command")) {
                        ObjectNode targetServerConfigNode = (ObjectNode) serverConfigNode;
                        // 创建要插入的 headers Map
                        Map<String, String> headers = new HashMap<>();
                        headers.put("X-HW-ID", mcpAuthKey);
                        headers.put("X-HW-APPKEY", mcpAuthSecret);
                        // 将 headers Map 添加到目标节点
                        // `put` 方法会自动将 Map 序列化为一个 JSON 对象
                        targetServerConfigNode.putPOJO("headers", headers);
                    }
                });
            }
            // 将修改后的 JsonNode 重新写回字符串
            return objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(rootNode);
        } catch (Exception e) {
            log.error("insert header into McpServers failed.", e);
            return jsonString;
        }
    }

    public String deleteAuthHeadersFromMcpServer(String jsonString) {
        ObjectMapper objectMapper = new ObjectMapper();
        try {
            // 将JSON字符串解析为JsonNode
            JsonNode rootNode = objectMapper.readTree(jsonString);
            // 检查 mcpServers 节点是否存在
            if (rootNode.has("mcpServers") && rootNode.get("mcpServers").isObject()) {
                ObjectNode mcpServersNode = (ObjectNode) rootNode.get("mcpServers");
                // 遍历 mcpServers 下的所有服务器配置
                mcpServersNode.fieldNames().forEachRemaining(serverName -> {
                    JsonNode serverConfigNode = mcpServersNode.get(serverName);
                    // 确保这是一个 ObjectNode 并且包含 command 字段
                    if (serverConfigNode.isObject() && serverConfigNode.has("headers")) {
                        ((ObjectNode) serverConfigNode).remove("headers");
                    }
                });
            }
            // 将修改后的 JsonNode 重新写回字符串
            return objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(rootNode);
        } catch (Exception e) {
            log.error("insert header into McpServers failed.", e);
            return jsonString;
        }
    }

    public McpServiceDetailInfoDto thirdService2McpServiceDetailInfoDto(McpServiceBatchDeployItem mcpService, String resource) {
        McpServiceDetailInfoDto dto = new McpServiceDetailInfoDto();
        BeanUtils.copyProperties(mcpService, dto);
        dto.setThirdResource(resource);
        dto.setThirdId(mcpService.getThirdId());
        dto.setThirdVersionId(mcpService.getThirdVersionId());
        dto.setAuthType(CommonConstant.MCP_AUTH_TYPE.USE_IAM_TOKEN);
        return dto;
    }

    public McpServerEntity mcpServiceInfoDto2ServerEntity(McpServiceDetailInfoDto serviceDetail) {
        McpServerEntity entity = new McpServerEntity();
        BeanUtils.copyProperties(serviceDetail, entity);
        return entity;
    }

    /**
     * [新增] 通用逻辑：解析数据库的 failReason JSON，注入全量国际化对象
     * 支持 McpServiceBaseInfoDto
     */
    private void fillFailReasonDetail(McpServiceEntity entity, McpServiceBaseInfoDto dto) {
        if (StringUtils.isBlank(entity.getFailReason())) {
            return;
        }
        try {
            // 1. 解析数据库存的 JSON (例如 {"code":"1161", "debug_info":"..."})
            JSONObject raw = JSON.parseObject(entity.getFailReason());
            if (raw != null) {
                String code = raw.getString("code");
                // 兼容新旧字段名 (debug_info / debugInfo)
                String debugInfo = raw.getString("debug_info");
                if (StringUtils.isBlank(debugInfo)) {
                    debugInfo = raw.getString("debugInfo");
                }

                if (StringUtils.isNotBlank(code)) {
                    // 2. 调用工厂，生成包含中英文的全量对象
                    McpFailReasonDetailDto detail = McpErrorFactory.buildFullDetail(code, debugInfo);
                    // 3. 塞入 DTO (该方法是 YAML 生成代码后自动拥有的)
                    dto.setFailReasonDetail(detail);
                }
            }
        } catch (Exception e) {
            // 解析失败不阻断流程，只打印日志，前端该字段为空
            log.warn("Failed to parse failReason for service id: {}", entity.getId());
        }
    }

    /**
     * [新增] 重载方法：支持 McpServiceDetailInfoDto (详情页)
     */
    private void fillFailReasonDetail(McpServiceEntity entity, McpServiceDetailInfoDto dto) {
        if (StringUtils.isBlank(entity.getFailReason())) {
            return;
        }
        try {
            JSONObject raw = JSON.parseObject(entity.getFailReason());
            if (raw != null) {
                String code = raw.getString("code");
                String debugInfo = raw.getString("debug_info");
                if (StringUtils.isBlank(debugInfo)) {
                    debugInfo = raw.getString("debugInfo");
                }

                if (StringUtils.isNotBlank(code)) {
                    McpFailReasonDetailDto detail = McpErrorFactory.buildFullDetail(code, debugInfo);
                    dto.setFailReasonDetail(detail);
                }
            }
        } catch (Exception e) {
            log.warn("Failed to parse failReason for service id: {}", entity.getId());
        }
    }

}

