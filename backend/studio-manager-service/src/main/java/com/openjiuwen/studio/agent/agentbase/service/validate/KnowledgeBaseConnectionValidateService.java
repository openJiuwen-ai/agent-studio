/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.agentbase.service.validate;

import com.google.common.collect.Lists;
import com.openjiuwen.studio.agent.agentbase.common.constant.CommonConstant;
import com.openjiuwen.studio.agent.agentbase.entity.KnowledgeBaseConnectionEntity;
import com.openjiuwen.studio.agent.agentbase.entity.KnowledgeBaseConnectorEntity;
import com.openjiuwen.studio.agent.agentbase.enums.KnowledgeBaseConnectionSecretType;
import com.openjiuwen.studio.agent.agentbase.enums.KnowledgeBaseConnectorParamType;
import com.openjiuwen.studio.agent.agentbase.mapper.KnowledgeBaseConnectionMapper;
import com.openjiuwen.studio.agent.agentbase.mapper.KnowledgeBaseConnectorMapper;
import com.openjiuwen.studio.agent.agentbase.model.KnowledgeBaseConnectionParam;
import com.openjiuwen.studio.agent.agentbase.model.KnowledgeBaseConnectorParam;
import com.openjiuwen.studio.agent.agentbase.utils.KnowledgeBaseConnectionUtil;
import com.openjiuwen.studio.agent.agentbase.utils.SSRFValidator;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.foundation.base.exception.AgentBaseException;
import com.openjiuwen.studio.agent.foundation.base.exception.ErrorCode;
import com.openjiuwen.studio.agent.foundation.connection.ConnectorParamDefinition;
import com.openjiuwen.studio.agent.foundation.connection.constants.ConnectorTypeEnum;
import com.openjiuwen.studio.agent.manager.dto.ConnectionParamInfo;
import com.openjiuwen.studio.agent.manager.dto.ParamDefinitionInfo;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.function.Function;
import java.util.stream.Collectors;

@Slf4j
@Service
public class KnowledgeBaseConnectionValidateService {

    private static final String PARAM_NEED = "Y";

    public static final String ADDRESS = "endpoint";

    final KnowledgeBaseConnectionMapper connectionMapper;

    final KnowledgeBaseConnectorMapper connectorMapper;


    public KnowledgeBaseConnectionValidateService(KnowledgeBaseConnectionMapper connectionMapper,
        KnowledgeBaseConnectorMapper connectorMapper) {
        this.connectionMapper = connectionMapper;
        this.connectorMapper = connectorMapper;
    }

    public List<ConnectionParamInfo> checkAndEncryptedParams(String connectorId, List<ConnectionParamInfo> params) {
        final KnowledgeBaseConnectorEntity knowledgeBaseConnectorEntity = connectorMapper.find(connectorId);
        if (knowledgeBaseConnectorEntity == null) {
            log.error("connector {} not found", connectorId);
            throw new AgentBaseException(ErrorCode.RESOURCE_NOT_EXIST);
        }

        // 内部预置的外部知识库
        if (ConnectorTypeEnum.HIS.getValue().equals(connectorId)) {
            List<ConnectionParamInfo> connectionParamInfos = new ArrayList<>();
            knowledgeBaseConnectorEntity.getParams().forEach(item -> {
                ConnectionParamInfo connectionParamInfo = new ConnectionParamInfo().setValue(item.getValue())
                    .setCode(item.getCode());
                connectionParamInfos.add(connectionParamInfo);
            });
            return connectionParamInfos;
        }
        List<KnowledgeBaseConnectorParam> definitionParams = knowledgeBaseConnectorEntity.getParams();
        Set<String> definitionParamSet = definitionParams.stream()
            .map(KnowledgeBaseConnectorParam::getCode)
            .collect(Collectors.toSet());
        Set<String> createParamSet = params.stream().map(ConnectionParamInfo::getCode).collect(Collectors.toSet());
        if (!createParamSet.equals(definitionParamSet)) {
            log.error("params not match,please check it");
            throw new AgentBaseException(ErrorCode.INVALID_PARAMETER, knowledgeBaseConnectorEntity.getName());
        }
        Map<String, KnowledgeBaseConnectorParam> paramDefinitionMap = definitionParams.stream()
            .collect(Collectors.toMap(KnowledgeBaseConnectorParam::getCode, Function.identity()));
        for (ConnectionParamInfo param : params) {
            validAddress(param);
            if (ParamDefinitionInfo.TypeEnum.SECRET.name()
                .equalsIgnoreCase(paramDefinitionMap.get(param.getCode()).getType().name())) {
                param.setValue(encryptParam(knowledgeBaseConnectorEntity.getType(), param.getValue()));
            }
            checkParamPattern(paramDefinitionMap.get(param.getCode()), param);
        }
        return params;
    }

    String encryptParam(String type, String plaintext) {
        if (type.equals(CommonConstant.INSIDE)) {
            return CryptoUtils.encrypt(plaintext);
        }

        // 调用kmsCryptoService，返回值兼容旧数据
        return CryptoUtils.encrypt(plaintext);
    }

    private void checkParamPattern(KnowledgeBaseConnectorParam connectorParam, ConnectionParamInfo connectionParam) {
        if (PARAM_NEED.equals(connectorParam.getNeed()) && StringUtils.isEmpty(connectionParam.getValue())) {
            log.error("param {} cannot be empty,please check it", connectorParam.getCode());
            throw new AgentBaseException(ErrorCode.EMPTY_PARAM, connectorParam.getName());
        }
        String pattern = connectorParam.getPattern();
        if (StringUtils.isEmpty(pattern) || StringUtils.isEmpty(connectionParam.getValue())) {
            return;
        }
        if (!connectionParam.getValue().matches(pattern)) {
            log.error("Invalid pattern:[{}]", connectionParam.getCode());
            throw new AgentBaseException(ErrorCode.INVALID_PARAMETER, connectorParam.getName());
        }
    }

    public void validateParamDefinitionsAddress(List<ConnectorParamDefinition> paramDefinitions) {
        if (CollectionUtils.isEmpty(paramDefinitions)) {
            return;
        }
        paramDefinitions.forEach(item -> {
            if (ADDRESS.equals(item.getCode())) {
                SSRFValidator.checkSSRF(item.getValue());
            }
        });
    }

    private void validAddress(ConnectionParamInfo connectionParamInfo) {
        if (ADDRESS.equals(connectionParamInfo.getCode())) {
            SSRFValidator.checkSSRF(connectionParamInfo.getValue());
        }
    }

    public KnowledgeBaseConnectionEntity validateKnowledgeBasePermission(String workspaceId,
        String knowledgeBaseConnectionId) {
        String projectId = RequestContextUtils.getRequestProjectId();
        final KnowledgeBaseConnectionEntity entity = connectionMapper.find(knowledgeBaseConnectionId, workspaceId,
            projectId);
        if (entity == null) {
            log.error("You have no permission to operate knowledge base connection{}", knowledgeBaseConnectionId);
            throw new AgentBaseException(ErrorCode.RESOURCE_NOT_EXIST);
        }
        return entity;
    }

    public void cleanSensitiveInformation(KnowledgeBaseConnectionEntity knowledgeBaseConnectionEntity) {
        knowledgeBaseConnectionEntity.getParams()
            .stream()
            .forEach(param -> KnowledgeBaseConnectionSecretType.anonymizeParameters(param));
    }

    public void checkThirdPartyKnowledgeBaseConnectionName(String workspaceId, String name,
        String knowledgeBaseConnectionId) {
        String existName = connectionMapper.findByName(name, knowledgeBaseConnectionId, workspaceId);
        if (name.equals(existName)) {
            log.error("KnowledgeBase name {} is duplicated.", name);
            throw new AgentBaseException(ErrorCode.RESOURCE_NAME_DUPLICATE, name);
        }
    }

    /**
     * 检查是否存在相同的连接
     *
     * @param workSpaceId
     * @param entity
     * @return true-存在相同连接，false-不存在相同连接
     */
    public boolean checkConnectionUnique(String workSpaceId, KnowledgeBaseConnectionEntity entity) {
        KnowledgeBaseConnectionEntity existConnection = getSameConnection(workSpaceId, entity);
        if (Objects.isNull(existConnection)) {
            return false;
        }
        return !Strings.CS.equals(entity.getId(), existConnection.getId());
    }

    /**
     * 检查是否存在相同的外部知识库连接
     *
     * @param workSpaceId
     * @param entity
     * @return
     */
    public KnowledgeBaseConnectionEntity getSameConnection(String workSpaceId, KnowledgeBaseConnectionEntity entity) {
        List<KnowledgeBaseConnectionParam> currentParams = Lists.newArrayList();
        KnowledgeBaseConnectorEntity connector = connectorMapper.find(entity.getConnectorId());
        Map<String, KnowledgeBaseConnectorParam> paramMap = connector.getParams()
            .stream()
            .collect(Collectors.toMap(KnowledgeBaseConnectorParam::getCode, item -> item));
        for (KnowledgeBaseConnectionParam param : ObjectUtils.firstNonNull(entity.getParams(),
            Collections.<KnowledgeBaseConnectionParam>emptyList())) {
            if (!paramMap.containsKey(param.getCode())) {
                continue;
            }
            if (KnowledgeBaseConnectorParamType.SECRET == paramMap.get(param.getCode()).getType()) {
                KnowledgeBaseConnectionParam tmpParam = new KnowledgeBaseConnectionParam();
                tmpParam.setCode(param.getCode());
                tmpParam.setValue(decryptParam(connector.getType(), param.getValue()));
                currentParams.add(tmpParam);
            } else {
                currentParams.add(param);
            }
        }

        List<KnowledgeBaseConnectionEntity> knowledgeBaseConnections = connectionMapper.listThirdPartyKnowledgeBases(
            null, entity.getConnectorId(), null, workSpaceId, null);
        for (KnowledgeBaseConnectionEntity knowledgeBaseConnectionEntity : ObjectUtils.firstNonNull(
            knowledgeBaseConnections, Collections.<KnowledgeBaseConnectionEntity>emptyList())) {
            List<KnowledgeBaseConnectionParam> param = new ArrayList<>();
            knowledgeBaseConnectionEntity.getParams().forEach(item -> {
                KnowledgeBaseConnectionParam tmpParam = new KnowledgeBaseConnectionParam();
                tmpParam.setCode(item.getCode());
                KnowledgeBaseConnectorParamType paramType = Optional.ofNullable(paramMap.get(item.getCode()))
                    .map(KnowledgeBaseConnectorParam::getType)
                    .orElse(null);
                if (KnowledgeBaseConnectorParamType.SECRET == paramType) {
                    tmpParam.setValue(decryptParam(connector.getType(), item.getValue()));
                } else {
                    tmpParam.setValue(item.getValue());
                }
                param.add(tmpParam);
            });
            if (KnowledgeBaseConnectionUtil.isSameConnection(currentParams, param)) {
                return knowledgeBaseConnectionEntity;
            }
        }
        return null;
    }

    String decryptParam(String type, String ciphertext ) {
        if (type.equals(CommonConstant.INSIDE)) {
            return CryptoUtils.decrypt(ciphertext);
        }

        // 调用kmsCryptoService，返回值兼容旧数据
        return CryptoUtils.decrypt(ciphertext);
    }

    public boolean defaultConnectionExisted(String connectorId) {
        List<KnowledgeBaseConnectionEntity> defaultConnections = connectionMapper.findDefaultConnection(connectorId);
        return CollectionUtils.isNotEmpty(defaultConnections);
    }
}
