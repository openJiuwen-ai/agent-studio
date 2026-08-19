/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.agentbase.converter;

import com.openjiuwen.studio.agent.agentbase.entity.KnowledgeBaseConnectionEntity;
import com.openjiuwen.studio.agent.agentbase.entity.KnowledgeBaseConnectorEntity;
import com.openjiuwen.studio.agent.agentbase.enums.KnowledgeBaseConnectionStatus;
import com.openjiuwen.studio.agent.agentbase.model.KnowledgeBaseConnectionParam;
import com.openjiuwen.studio.agent.agentbase.model.KnowledgeBaseConnectorParam;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.dto.ConnectionParamInfo;
import com.openjiuwen.studio.agent.manager.dto.CreateDefaultKnowledgeBaseConnectionRequestBody;
import com.openjiuwen.studio.agent.manager.dto.DefaultKnowledgeBaseConnectionDetail;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeBaseConnectorDetail;
import com.openjiuwen.studio.agent.manager.dto.ParamDefinitionInfo;
import com.openjiuwen.studio.agent.manager.dto.TestDefaultKnowledgeBaseConnectionRequestBody;
import com.openjiuwen.studio.agent.manager.dto.UpdateDefaultKnowledgeBaseConnectionRequestBody;

import java.util.List;

/**
 * 元数据相关的结构体转换工具类
 */
public interface KbConnectionConverter {

    String DEFAULT_WORKSPACE_ID = "default_workspace_id";
    String DEFAULT_CONNECTION_ID = "default_lakesearch_inside_connection_id";
    // 敏感字符不对外，特殊处理
    List<String> SECRET_CODE = List.of("authorization");

    default KnowledgeBaseConnectionEntity toKnowledgeBaseConnectionEntity(String projectId,
        CreateDefaultKnowledgeBaseConnectionRequestBody body) {
        KnowledgeBaseConnectionEntity entity = new KnowledgeBaseConnectionEntity();
        long currentTimeMillis = System.currentTimeMillis();
        entity.setId(DEFAULT_CONNECTION_ID);
        entity.setProjectId(projectId);
        entity.setConnectorId(body.getConnectorId());
        entity.setWorkspaceId(DEFAULT_WORKSPACE_ID);
        entity.setStatus(KnowledgeBaseConnectionStatus.OPEN);
        entity.setParams(body.getParams()
            .stream()
            .map(param -> new KnowledgeBaseConnectionParam(param.getCode(), param.getValue()))
            .toList());
        entity.setName(body.getConnectorId());
        entity.setDescription("");
        entity.setProjectId(projectId);
        entity.setDomainId(RequestContextUtils.getRequestUserDomainId());
        entity.setDomainName(RequestContextUtils.getRequestUserDomainName());
        entity.setCreatedUserId(RequestContextUtils.getRequestUserId());
        entity.setCreatedUserName(RequestContextUtils.getRequestUserName());
        entity.setCreateTime(currentTimeMillis);
        entity.setUpdateUserId(RequestContextUtils.getRequestUserId());
        entity.setUpdateUserName(RequestContextUtils.getRequestUserName());
        entity.setUpdateTime(currentTimeMillis);
        return entity;
    }

    default KnowledgeBaseConnectionEntity updateBodytoKnowledgeBaseConnectionEntity(
        UpdateDefaultKnowledgeBaseConnectionRequestBody body) {
        KnowledgeBaseConnectionEntity entity = new KnowledgeBaseConnectionEntity();
        long currentTimeMillis = System.currentTimeMillis();
        entity.setConnectorId(body.getConnectorId());
        entity.setName(body.getConnectorId());
        entity.setParams(body.getParams()
            .stream()
            .map(param -> new KnowledgeBaseConnectionParam(param.getCode(), param.getValue()))
            .toList());
        entity.setUpdateUserId(RequestContextUtils.getRequestUserId());
        entity.setUpdateUserName(RequestContextUtils.getRequestUserName());
        entity.setUpdateTime(currentTimeMillis);
        return entity;
    }

    DefaultKnowledgeBaseConnectionDetail toDefaultKnowledgeBaseConnectionDetail(
        KnowledgeBaseConnectionEntity knowledgeBaseConnectionEntity);

    default List<ConnectionParamInfo> kbConnectionParams2ConnectionParamInfos(
        List<KnowledgeBaseConnectionParam> knowledgeBaseConnectionParams) {
        List<ConnectionParamInfo> connectionParamInfos = knowledgeBaseConnectionParams.stream().map(param -> {
            // 敏感字符不对外，特殊处理
            if (SECRET_CODE.contains(param.getCode())) {
                return new ConnectionParamInfo().setCode(param.getCode()).setValue("******");
            }
            return new ConnectionParamInfo().setCode(param.getCode()).setValue(param.getValue());
        }).toList();
        return connectionParamInfos;

    }

    ConnectionParamInfo kbConnectionParam2ConnectionParamInfo(
        KnowledgeBaseConnectionParam knowledgeBaseConnectionParams);

    KnowledgeBaseConnectorDetail toKnowledgeBaseConnectorDetail(
        KnowledgeBaseConnectorEntity knowledgeBaseConnectorEntity);

    List<ParamDefinitionInfo> connectorParams2ParamDefinitionInfos(
        List<KnowledgeBaseConnectorParam> knowledgeBaseConnectorParams);

    ParamDefinitionInfo connectorParam2ParamDefinitionInfo(KnowledgeBaseConnectorParam knowledgeBaseConnectorParam);

    KnowledgeBaseConnectionEntity requestBodyToKbConnectionEntity(TestDefaultKnowledgeBaseConnectionRequestBody body);

    KnowledgeBaseConnectionParam connectionParamInfo2kbConnectionParam(ConnectionParamInfo connectionParamInfo);

    List<KnowledgeBaseConnectionParam> connectionParamInfos2kbConnectionParams(
        List<ConnectionParamInfo> connectionParamInfos);
}
