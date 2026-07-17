/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2020-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.common.dto.auth.AuthKeyInfo;
import com.openjiuwen.studio.agent.manager.dto.RequestInfo;
import com.openjiuwen.studio.agent.manager.entity.ToolEntity;
import com.openjiuwen.studio.agent.manager.enums.ToolType;
import com.openjiuwen.studio.agent.manager.enums.VisibilityEnum;
import com.openjiuwen.studio.agent.manager.mapper.ToolMapper;

import lombok.Generated;

import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Optional;

import javax.annotation.PostConstruct;

/**
 * 内置插件
 *
 */
@Service
public class InnerToolService {
    @Generated
    private static final Logger log = LoggerFactory.getLogger(InnerToolService.class);

    @Value("${op.svc.project-id}")
    private String opSvcProjectId;

    @Value("${jiuwen.base-url}")
    private String runtimeServerEndpoint;

    @Value("${inner.exclude-tools}")
    private String excludeInnerTools;

    @Value("${tool.Read-File.url}")
    private String readFileUrl;

    @Value("${tool.Read-File.icon}")
    private String readFileIcon;

    @Value("${tool.Create-Document.url}")
    private String createDocumentUrl;

    @Value("${tool.Create-Document.icon}")
    private String createDocumentIcon;

    private final ToolMapper toolMapper;

    public InnerToolService(ToolMapper toolMapper) {
        this.toolMapper = toolMapper;
    }

    @PostConstruct
    public void initInnerTool() {
        List<String> excludeTools = (List) Optional.ofNullable(this.excludeInnerTools).map((s) -> Arrays.stream(s.split(",")).toList()).orElseGet(
            ArrayList::new);
        this.preSetReadFile(excludeTools);
        this.preSetCreateDocument(excludeTools);
    }

    private void preSetReadFile(List<String> excludeTools) {
        if (!excludeTools.contains("Read_File")) {
            try {
                this.toolMapper.deleteOnlyByPrimaryKey("preset_Read_File");
                this.toolMapper.insert(this.buildReadFileToolEntity());
                log.info("success to register Read_File.");
            } catch (DuplicateKeyException var3) {
                log.warn("Read_File is exist, skip register.");
            } catch (Exception exception) {
                log.error("fail to register Read_File: [{}]", exception.getMessage());
            }

        }
    }

    private void preSetCreateDocument(List<String> excludeTools) {
        if (!excludeTools.contains("Create_Document")) {
            try {
                this.toolMapper.deleteOnlyByPrimaryKey("preset_Create_Document");
                this.toolMapper.insert(this.buildCreateDocumentToolEntity());
                log.info("success to register Create_Document.");
            } catch (DuplicateKeyException var3) {
                log.warn("Create_Document is exist, skip register.");
            } catch (Exception exception) {
                log.error("fail to register Create_Document: [{}]", exception.getMessage());
            }

        }
    }

    private ToolEntity buildReadFileToolEntity() {
        ToolEntity toolEntity = this.builderInnerToolEntity();
        toolEntity.setToolId("preset_Read_File");
        toolEntity.setToolDisplayName("Read_File");
        toolEntity.setToolChineseName("文件解析");
        toolEntity.setToolDesc("文件解析工具，可以解析txt、doc、docx、csv和xlsx类型的文件，不支持解析其中所包含的图片内容。服务来源：内置服务。");
        toolEntity.setIcon(this.readFileIcon);
        toolEntity.setRequestInfo(this.buildReadFileRequestInfo());
        toolEntity.setAuthInfo(this.buildPythonInterpreterAuthInfo());
        toolEntity.setInputSchema("{\"type\":\"object\",\"properties\":{\"file_url\":{\"location\":\"Query\",\"validate_rule\":\"\",\"validate_type\":\"CHAR\",\"validated\":false,\"name_cn\":\"文件链接\",\"type\":\"string\",\"description\":\"文件链接\"}},\"required\":[\"file_url\"]}");
        toolEntity.setIsInputList(false);
        toolEntity.setOutputSchema("{\"type\":\"object\",\"properties\":{\"content\":{\"type\":\"string\",\"description\":\"文件内容\"}},\"required\":[\"content\"]}");
        toolEntity.setIsOutputList(false);
        toolEntity.setCreatedOn(new Date());
        toolEntity.setAuthRequired(false);
        toolEntity.setPublished(1);
        toolEntity.setIsFree(0);
        toolEntity.setCategory("10d701db-8741-4556-90b9-c1bf66cd9737");
        return toolEntity;
    }

    private ToolEntity buildCreateDocumentToolEntity() {
        ToolEntity toolEntity = this.builderInnerToolEntity();
        toolEntity.setToolId("preset_Create_Document");
        toolEntity.setToolDisplayName("Create_Document");
        toolEntity.setToolChineseName("文档生成");
        toolEntity.setToolDesc("文档生成工具，可以根据文档内容和标题生成docx格式的文档。服务来源：内置服务。");
        toolEntity.setIcon(this.createDocumentIcon);
        toolEntity.setRequestInfo(this.buildCreateDocumentRequestInfo());
        toolEntity.setAuthInfo(this.buildPythonInterpreterAuthInfo());
        toolEntity.setInputSchema("{\"type\":\"object\",\"properties\":{\"input\":{\"location\":\"Body\",\"validate_rule\":\"\",\"validate_type\":\"CHAR\",\"validated\":false,\"name_cn\":\"文档内容\",\"type\":\"string\",\"description\":\"文档内容\"},\"document_name\":{\"location\":\"Body\",\"validate_rule\":\"\",\"validate_type\":\"CHAR\",\"validated\":false,\"name_cn\":\"文档名\",\"type\":\"string\",\"description\":\"文档名，不允许含有以下非法字符：\\\\/:*?\\\"<>|\"}},\"required\":[\"input\",\"document_name\"]}");
        toolEntity.setIsInputList(false);
        toolEntity.setOutputSchema("{\"type\":\"object\",\"properties\":{\"url\":{\"type\":\"string\",\"description\":\"文档下载链接\"}},\"required\":[]}");
        toolEntity.setIsOutputList(false);
        toolEntity.setCreatedOn(new Date());
        toolEntity.setAuthRequired(false);
        toolEntity.setPublished(1);
        toolEntity.setIsFree(0);
        toolEntity.setCategory("10d701db-8741-4556-90b9-c1bf66cd9737");
        return toolEntity;
    }

    private RequestInfo buildReadFileRequestInfo() {
        RequestInfo requestInfo = this.buildBaseRequestInfo();
        if (StringUtils.isBlank(this.readFileUrl) || StringUtils.isBlank(this.runtimeServerEndpoint)) {
            log.error("Fail to register Read_File, url or endpoint is blank.");
        }

        requestInfo.setUrl(this.runtimeServerEndpoint + this.readFileUrl);
        return requestInfo;
    }

    private RequestInfo buildCreateDocumentRequestInfo() {
        RequestInfo requestInfo = this.buildBaseRequestInfo();
        if (StringUtils.isBlank(this.createDocumentUrl) || StringUtils.isBlank(this.runtimeServerEndpoint)) {
            log.error("Fail to register Create_Document, url or endpoint is blank.");
        }

        requestInfo.setUrl(this.runtimeServerEndpoint + this.createDocumentUrl);
        return requestInfo;
    }

    private AuthInfo buildPythonInterpreterAuthInfo() {
        AuthInfo authInfo = new AuthInfo();
        authInfo.setScope(AuthInfo.ScopeEnum.USER);
        authInfo.setDomain(AuthInfo.DomainEnum.HEADERS);
        authInfo.setAuthKeys(List.of((new AuthKeyInfo()).setSourceName("X-Auth-Token").setTargetName("X-Auth-Token")));
        return authInfo;
    }

    private ToolEntity builderInnerToolEntity() {
        ToolEntity toolEntity = new ToolEntity();
        toolEntity.setProjectId(this.opSvcProjectId);
        toolEntity.setWorkspaceId("default");
        toolEntity.setType(ToolType.INNER.type);
        toolEntity.setCreator("官方预置");
        toolEntity.setCreatorId("openjiuwen");
        toolEntity.setVisibility(VisibilityEnum.GLOBAL.getValue());
        toolEntity.setIntfType("blocking");
        return toolEntity;
    }

    private RequestInfo buildBaseRequestInfo() {
        RequestInfo requestInfo = new RequestInfo();
        requestInfo.setMethod(RequestInfo.MethodEnum.POST);
        requestInfo.setHeaders(new HashMap());
        return requestInfo;
    }
}
