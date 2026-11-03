/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.controller;

import com.openjiuwen.studio.agent.common.utils.ResponseModel;
import com.openjiuwen.studio.prompt.engineering.dto.CreatePromptResp;
import com.openjiuwen.studio.prompt.engineering.dto.GetPromptListsQo;
import com.openjiuwen.studio.prompt.engineering.dto.PePromptNewListVo;
import com.openjiuwen.studio.prompt.engineering.dto.PePromptTemplateNewVo;
import com.openjiuwen.studio.prompt.engineering.service.IPromptApiService;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;

/**
 * PromptApi controller
 */
@RestController

public class PromptApiApiController implements PromptApiApi {

    private static final Logger log = LoggerFactory.getLogger(PromptApiApiController.class);

    @Autowired
    private IPromptApiService promptApiService;

    @Override
    public ResponseEntity<String> createCustomPromptApiAction(String projectId, String workspaceId, PePromptTemplateNewVo body) {
        return ResponseModel.success(promptApiService.createCustomPromptApiAction(projectId, workspaceId, body));
    }

    @Override
    public ResponseEntity<PePromptNewListVo> getPromptLists(String projectId, GetPromptListsQo getPromptListsQo) {
        return ResponseModel.success(promptApiService.getPromptLists(projectId, getPromptListsQo));
    }

    @Override
    public ResponseEntity<CreatePromptResp> savePromptTemplate(String projectId, String workspaceId, PePromptTemplateNewVo body) {
        return ResponseModel.success(promptApiService.savePromptTemplate(projectId, workspaceId, body));
    }

    @Override
    public ResponseEntity<CreatePromptResp> updateCustomPromptApiAction(String projectId, String workspaceId, PePromptTemplateNewVo body) {
        return ResponseModel.success(promptApiService.updateCustomPromptApiAction(projectId, workspaceId, body));
    }
}
