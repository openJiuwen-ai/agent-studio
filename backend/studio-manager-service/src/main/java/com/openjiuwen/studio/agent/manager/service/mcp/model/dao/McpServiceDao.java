/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.mcp.model.dao;

import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.manager.entity.McpServiceEntity;
import com.openjiuwen.studio.agent.manager.entity.ShareResourceEntity;
import com.openjiuwen.studio.agent.manager.enums.EnumMcpStatus;
import com.openjiuwen.studio.agent.manager.mapper.McpServiceMapper;
import com.openjiuwen.studio.agent.manager.utils.CommonUtil;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * NodeDao
 *
 * @Date: 2024/12/19 15:59
 * @Description:
 */

@Component
public class McpServiceDao {
    private final McpServiceMapper mcpServiceMapper;

    @Autowired
    public McpServiceDao(McpServiceMapper mcpServiceMapper) {
        this.mcpServiceMapper = mcpServiceMapper;
    }

    public List<McpServiceEntity> getMcpServiceByNameAndTenant(String name, String tenantId, String deptCode,
        String workspaceId) {
        return mcpServiceMapper.selectByName(name, tenantId, deptCode, workspaceId);
    }

    public List<McpServiceEntity> getMcpServiceByNameEnAndTenant(String nameEn, String tenantId, String deptCode,
                                                           String workspaceId) {
        return mcpServiceMapper.selectByNameEn(nameEn, tenantId, deptCode, workspaceId);
    }

    public McpServiceEntity getMcpServiceByIdAndTenant(String id, String tenantId, String deptCode,
        String workspaceId) {
        return mcpServiceMapper.selectById(id, tenantId, deptCode,  workspaceId);
    }

    public List<McpServiceEntity> listMcpServiceByIdAndTenant(List<String> ids, String tenantId, String deptCode,
         String workspaceId) {
        return mcpServiceMapper.selectList(ids, tenantId, deptCode,  workspaceId);
    }

    public List<McpServiceEntity> listMcpServiceByTenant(String tenantId, String workspaceId) {
        return mcpServiceMapper.selectListByTenant(tenantId, null, workspaceId);
    }

    public McpServiceEntity selectById(String id, String tenantId, String deptCode,
        String workspaceId) {
        return mcpServiceMapper.selectById(id, tenantId, deptCode, workspaceId);
    }

    public int updateStatus(String id, String status, String tenantId, String deptCode) {
        LocalDateTime now = LocalDateTime.now();
        Map<String, Object> params = new HashMap<>();
        params.put("id", id);
        params.put("status", status);
        params.put("tenantId", tenantId);
        params.put("deptCode", deptCode);
        params.put("lastUpdatedDate", new Timestamp(now.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli()));

        return mcpServiceMapper.updateStatus(params);
    }

    /**
     * 更新状态及失败原因
     * 用于异步记录部署失败的具体报错信息
     */
    public int updateStatusWithReason(String id, String status, String failReason, String tenantId, String deptCode) {
        return mcpServiceMapper.updateStatusWithReason(id, status, failReason, tenantId);
    }

    /**
     * 更新mcp服务状态
     *
     */
    public int updateFcInstanceStatus(String id, String status, String tenantId, String deptCode) {
        LocalDateTime now = LocalDateTime.now();
        Map<String, Object> params = new HashMap<>();
        params.put("id", id);
        params.put("status", status);
        params.put("tenantId", tenantId);
        params.put("deptCode", deptCode);
        params.put("lastUpdatedDate", new Timestamp(now.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli()));
        return mcpServiceMapper.updateFcInstanceStatus(params);
    }

    public int updateFcInstanceIdAndReadme(String id, String fcInstanceId, String readme, String tenantId) {
        LocalDateTime now = LocalDateTime.now();
        Map<String, Object> params = new HashMap<>();
        params.put("id", id);
        params.put("fcInstanceId", fcInstanceId);
        params.put("readme", readme);
        params.put("tenantId", tenantId);
        params.put("lastUpdatedDate", new Timestamp(now.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli()));

        return mcpServiceMapper.updateFcInstanceIdAndReadme(params);
    }

    public int updateFcInstanceUrlAndStatus(String id, String fcInstanceUrl, String fcInstanceStatus, String tenantId,
        String readme, String tools) {
        LocalDateTime now = LocalDateTime.now();
        Map<String, Object> params = new HashMap<>();
        params.put("id", id);
        params.put("fcInstanceUrl", fcInstanceUrl);
        params.put("fcInstanceStatus", fcInstanceStatus);
        params.put("tenantId", tenantId);
        params.put("lastUpdatedDate", new Timestamp(now.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli()));
        params.put("readme", readme);
        params.put("tools", tools);
        return mcpServiceMapper.updateFcInstanceUrlAndStatus(params);
    }

    public int updateToolsAndStatus(String id, String tenantId, String fcInstanceStatus, String tools) {
        LocalDateTime now = LocalDateTime.now();
        Map<String, Object> params = new HashMap<>();
        params.put("id", id);
        params.put("fcInstanceStatus", fcInstanceStatus);
        params.put("lastUpdatedDate", new Timestamp(now.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli()));
        params.put("tools", tools);
        params.put("tenantId", tenantId);
        return mcpServiceMapper.updateToolsAndStatus(params);
    }

    public int updateTools(String id, String tools, String tenantId) {
        LocalDateTime now = LocalDateTime.now();
        Map<String, Object> params = new HashMap<>();
        params.put("id", id);
        params.put("tools", tools);
        params.put("tenantId", tenantId);
        params.put("lastUpdatedDate", new Timestamp(now.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli()));

        return mcpServiceMapper.updateTools(params);
    }

    public int updateFcInstanceInfo(String fcInstanceId, String apigUrl, String apigGroupId, String apigInstanceId,
        String functionName, String functionUrn, String domainId) {
        Map<String, Object> params = new HashMap<>();
        params.put("fcInstanceId", fcInstanceId);
        params.put("apigUrl", apigUrl);
        params.put("apigGroupId", apigGroupId);
        params.put("apigInstanceId", apigInstanceId);
        params.put("functionName", functionName);
        params.put("functionUrn", functionUrn);
        params.put("domainId", domainId);

        return mcpServiceMapper.updateFcInstanceInfo(params);
    }

    public int updateAuthInfo(String id, AuthInfo authInfo, String fcInstanceStatus, String failReason) {
        LocalDateTime now = LocalDateTime.now();
        Map<String, Object> params = new HashMap<>();
        params.put("id", id);
        params.put("authInfo", authInfo);
        params.put("fcInstanceStatus", fcInstanceStatus);
        params.put("failReason", failReason);
        params.put("lastUpdatedDate", new Timestamp(now.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli()));
        return mcpServiceMapper.updateAuthInfo(params);
    }

    public int markAsDeleted(String id, String tenantId, String deptCode) {
        Map<String, Object> params = new HashMap<>();
        params.put("id", id);
        params.put("tenantId", tenantId);
        params.put("deptCode", deptCode);
        params.put("lastUpdatedDate", new Timestamp(System.currentTimeMillis()));
        return mcpServiceMapper.markAsDeleted(params);
    }

    public int update(McpServiceEntity entity) {
        entity.setLastUpdatedDate(new Timestamp(System.currentTimeMillis()));
        return mcpServiceMapper.update(entity);
    }

    public int insert(McpServiceEntity serviceEntity) {
        return mcpServiceMapper.insert(serviceEntity);
    }

    public Long getMcpServiceCountByTenantId(String tenantId) {
        return mcpServiceMapper.selectCount(tenantId, null);
    }

    /**
     * FEAT-134：清除导入待补配标记（modify 确认后）。
     */
    public int markImportConfigured(String serviceId, String tenantId, String workspaceId) {
        return mcpServiceMapper.markImportConfigured(serviceId, tenantId, workspaceId);
    }

    /**
     * 根据mcp主键、项目id、工作空间id、租户id、部门id 查询mcp服务信息
     *
     */
    public McpServiceEntity getMcpServiceByIdAndTenantDeptCode(String id, String tenantId,
        String workspaceId) {
        return mcpServiceMapper.selectById(id, tenantId, CommonUtil.getDeptCode(), workspaceId);
    }

    /**
     * 根据mcp主键查询mcp服务信息
     *
     */
    public McpServiceEntity getMcpServiceOnlyById(String id) {
        if (StringUtils.isBlank(id)) {
            return null;
        }
        return mcpServiceMapper.selectByMcpId(id);
    }

    public List<McpServiceEntity> selectPage(int offset, int limit, String tenantId, String deptCode) {
        return mcpServiceMapper.selectByTenant(offset, limit, tenantId, deptCode);
    }

    public List<McpServiceEntity> selectPage2(int offset, int limit, String name, String nameEn, String tenantId,
        String deptCode) {
        return mcpServiceMapper.selectByTenantAndName(offset, limit, name, nameEn, tenantId, deptCode);
    }

    public List<McpServiceEntity> selectServiceWithPage(int offset, int limit, String name, String nameEn,
        String tenantId, String deptCode, String orgType,  String workspaceId, String fcInstanceStatus,
        String nodeType, String visibility) {
        return mcpServiceMapper.selectVisibilityServiceWithPage(offset, limit, name, nameEn, tenantId, deptCode,
            orgType, workspaceId, fcInstanceStatus, nodeType, visibility);
    }

    public long selectServiceWithPageCount(String name, String nameEn, String tenantId, String deptCode, String orgType,
         String workspaceId, String fcInstanceStatus, String nodeType, String visibility) {
        return mcpServiceMapper.selectServiceWithPageCount(name, nameEn, tenantId, deptCode, orgType,
            workspaceId, fcInstanceStatus, nodeType, visibility);
    }

    public long selectCount(String tenantId, String deptCode) {
        return mcpServiceMapper.selectCount(tenantId, deptCode);
    }

    public McpServiceEntity getMcpServiceById(String id, String tenantId, String deptCode, String projectId,
        String workspaceId) {
        return mcpServiceMapper.selectById(id, tenantId, deptCode, workspaceId);
    }

    public void updateFcInstanceInfo2(McpServiceEntity serviceEntity) {
        Map<String, Object> params = new HashMap<>();
        params.put("apigGroupId", serviceEntity.getApigGroupId());
        params.put("apigInstanceId", serviceEntity.getApigInstanceId());
        params.put("functionName", serviceEntity.getFunctionName());
        params.put("functionUrn", serviceEntity.getFunctionUrn());
        params.put("domainId", serviceEntity.getDomainId());
        params.put("id", serviceEntity.getId());
        params.put("functionApplicationName", serviceEntity.getFunctionApplicationName());
        mcpServiceMapper.updateFcInstanceInfo2(params);
    }

    public List<String> listSoftDeletedMcpServiceBeforeTime(LocalDateTime twoYearsAgo) {
        return mcpServiceMapper.selectIdsToBeHardDeleted(twoYearsAgo, EnumMcpStatus.DELETED.getValue());
    }

    public int hardDeleteMcpService(List<String> ids) {
        mcpServiceMapper.hardDeleteService(ids);
        return ids.size();
    }

    public void hardDeleteSingleMcpServiceById(String id, String tenantId, String deptCode) {
        mcpServiceMapper.hardDeleteSingleService(id, tenantId, deptCode);
    }

    public void updateMcpShareStatus(String id, int status) {
        mcpServiceMapper.updateMcpShareStatus(id, status);
    }


    public List<McpServiceEntity> listMcpServiceByIdAndProjectId(List<String> mcpIds, String projectId) {
        return mcpServiceMapper.listMcpServiceByIdAndProjectId(mcpIds, projectId);
    }

    public List<McpServiceEntity> listMcpServiceByShareResourceEntity(List<ShareResourceEntity> shareResourceEntities) {
        return mcpServiceMapper.listMcpServiceByShareResourceEntity(shareResourceEntities);
    }


}
