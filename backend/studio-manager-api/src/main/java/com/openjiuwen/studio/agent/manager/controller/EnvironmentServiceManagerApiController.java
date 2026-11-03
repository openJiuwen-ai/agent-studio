/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.Environment;
import com.openjiuwen.studio.agent.manager.dto.EnvironmentInfoRequest;
import com.openjiuwen.studio.agent.manager.dto.ModifyEnvironmentInfoRequestBody;
import com.openjiuwen.studio.agent.manager.dto.EnvironmentInstances;
import com.openjiuwen.studio.agent.manager.dto.EnvironmentVariables;
import com.openjiuwen.studio.agent.manager.dto.EnvironmentVariablesExport;
import com.openjiuwen.studio.agent.manager.dto.EnvironmentVariablesResp;
import com.openjiuwen.studio.agent.manager.dto.Environments;
import com.openjiuwen.studio.agent.manager.dto.ListSubnets;
import com.openjiuwen.studio.agent.manager.dto.QueryEnvironmentInstancesQo;
import com.openjiuwen.studio.agent.manager.dto.QueryEnvironmentVariablesQo;
import com.openjiuwen.studio.agent.manager.dto.QueryEnvironmentsListQo;
import com.openjiuwen.studio.agent.manager.dto.ValidationVariablesImport;
import com.openjiuwen.studio.agent.manager.dto.VpcInfo;
import com.openjiuwen.studio.agent.manager.service.IEnvironmentServiceManagerService;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.Resource;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

/**
 * EnvironmentServiceManager controller
 */
@RestController

public class EnvironmentServiceManagerApiController implements EnvironmentServiceManagerApi {
    private static final Logger log = LoggerFactory.getLogger(EnvironmentServiceManagerApiController.class);

    @Autowired
    private IEnvironmentServiceManagerService environmentServiceManagerService;

    @Override
    public ResponseEntity<String> createEnvironmentInfo(String projectId, EnvironmentInfoRequest body) {
        return ResponseModel.success(environmentServiceManagerService.createEnvironmentInfo(projectId, body));
    }

    @Override
    public ResponseEntity<String> createEnvironmentVariables(String projectId, String environmentId, String workspaceId,
        EnvironmentVariables body) {
        return ResponseModel.success(
            environmentServiceManagerService.createEnvironmentVariables(projectId, environmentId, workspaceId, body));
    }

    @Override
    public ResponseEntity<Boolean> deleteEnvironment(String projectId, String environmentId) {
        return ResponseModel.success(environmentServiceManagerService.deleteEnvironment(projectId, environmentId));
    }

    @Override
    public ResponseEntity<String> deleteEnvironmentVariables(String projectId, String environmentId,
        String envVariableId, String workspaceId) {
        return ResponseModel.success(
            environmentServiceManagerService.deleteEnvironmentVariables(projectId, environmentId, envVariableId,
                workspaceId));
    }

    @Override
    public ResponseEntity<ValidationVariablesImport> environmentVariableImportFileValidation(String workspaceId,
        String projectId, String environmentId, MultipartFile file) {
        return ResponseModel.success(
            environmentServiceManagerService.environmentVariableImportFileValidation(workspaceId, projectId,
                environmentId, file));
    }

    @Override
    public ResponseEntity<Resource> exportEnvironmentVariable(String projectId, String workspaceId,
        EnvironmentVariablesExport body) {
        return ResponseModel.successDownload(
            environmentServiceManagerService.exportEnvironmentVariable(projectId, workspaceId, body));
    }

    @Override
    public ResponseEntity<Boolean> importEnvironmentVariable(String workspaceId, String projectId, String environmentId,
        List<String> coverVariables, MultipartFile file) {
        return ResponseModel.success(
            environmentServiceManagerService.importEnvironmentVariable(workspaceId, projectId, environmentId,
                coverVariables, file));
    }

    @Override
    public ResponseEntity<Boolean> isDefaultEnvironments(String projectId, String environmentId) {
        return ResponseModel.success(environmentServiceManagerService.isDefaultEnvironments(projectId, environmentId));
    }

    @Override
    public ResponseEntity<Boolean> modifyEnvironmentInfo(String projectId, String environmentId,
        ModifyEnvironmentInfoRequestBody body) {
        return ResponseModel.success(
            environmentServiceManagerService.modifyEnvironmentInfo(projectId, environmentId, body));
    }

    @Override
    public ResponseEntity<Environment> queryEnvironment(String projectId, String environmentId) {
        return ResponseModel.success(environmentServiceManagerService.queryEnvironment(projectId, environmentId));
    }

    @Override
    public ResponseEntity<EnvironmentInstances> queryEnvironmentInstances(String projectId, String environmentId,
        QueryEnvironmentInstancesQo queryEnvironmentInstancesQo) {
        return ResponseModel.success(
            environmentServiceManagerService.queryEnvironmentInstances(projectId, environmentId,
                queryEnvironmentInstancesQo));
    }

    @Override
    public ResponseEntity<EnvironmentVariablesResp> queryEnvironmentVariables(String projectId,
        QueryEnvironmentVariablesQo queryEnvironmentVariablesQo) {
        return ResponseModel.success(
            environmentServiceManagerService.queryEnvironmentVariables(projectId, queryEnvironmentVariablesQo));
    }

    @Override
    public ResponseEntity<Environments> queryEnvironmentsList(String projectId,
        QueryEnvironmentsListQo queryEnvironmentsListQo) {
        return ResponseModel.success(
            environmentServiceManagerService.queryEnvironmentsList(projectId, queryEnvironmentsListQo));
    }

    @Override
    public ResponseEntity<List<VpcInfo>> queryVpcs(String projectId) {
        return ResponseModel.success(environmentServiceManagerService.queryVpcs(projectId));
    }

    @Override
    public ResponseEntity<ListSubnets> queryVpcsSubnets(String projectId, String vpcId) {
        return ResponseModel.success(environmentServiceManagerService.queryVpcsSubnets(projectId, vpcId));
    }

    @Override
    public ResponseEntity<EnvironmentVariables> showEnvironmentVariables(String projectId, String environmentId,
        String workspaceId) {
        return ResponseModel.success(
            environmentServiceManagerService.showEnvironmentVariables(projectId, environmentId, workspaceId));
    }
}