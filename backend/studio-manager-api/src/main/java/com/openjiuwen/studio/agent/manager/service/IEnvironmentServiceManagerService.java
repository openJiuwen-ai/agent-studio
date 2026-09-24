/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

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

import org.springframework.core.io.Resource;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

/**
 * EnvironmentServiceManager service
 */

public interface IEnvironmentServiceManagerService {

    /**
     * createEnvironmentInfo
     *
     * @param projectId projectId
     * @param body body
     */
    String createEnvironmentInfo(String projectId, EnvironmentInfoRequest body);

    /**
     * createEnvironmentVariables
     *
     * @param projectId projectId
     * @param environmentId environmentId
     * @param workspaceId workspaceId
     * @param body body
     */
    String createEnvironmentVariables(String projectId, String environmentId, String workspaceId,
        EnvironmentVariables body);

    /**
     * deleteEnvironment
     *
     * @param projectId projectId
     * @param environmentId environmentId
     */
    Boolean deleteEnvironment(String projectId, String environmentId);

    /**
     * deleteEnvironmentVariables
     *
     * @param projectId projectId
     * @param environmentId environmentId
     * @param envVariableId envVariableId
     * @param workspaceId workspaceId
     */
    String deleteEnvironmentVariables(String projectId, String environmentId, String envVariableId, String workspaceId);

    /**
     * environmentVariableImportFileValidation
     *
     * @param workspaceId workspaceId
     * @param projectId projectId
     * @param environmentId environmentId
     * @param file file
     */
    ValidationVariablesImport environmentVariableImportFileValidation(String workspaceId, String projectId,
        String environmentId, MultipartFile file);

    /**
     * exportEnvironmentVariable
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param body body
     */
    Resource exportEnvironmentVariable(String projectId, String workspaceId, EnvironmentVariablesExport body);

    /**
     * importEnvironmentVariable
     *
     * @param workspaceId workspaceId
     * @param projectId projectId
     * @param environmentId environmentId
     * @param coverVariables coverVariables
     * @param file file
     */
    Boolean importEnvironmentVariable(String workspaceId, String projectId, String environmentId,
        List<String> coverVariables, MultipartFile file);

    /**
     * isDefaultEnvironments
     *
     * @param projectId projectId
     * @param environmentId environmentId
     */
    Boolean isDefaultEnvironments(String projectId, String environmentId);

    /**
     * modifyEnvironmentInfo
     *
     * @param projectId projectId
     * @param environmentId environmentId
     * @param body body
     */
    Boolean modifyEnvironmentInfo(String projectId, String environmentId, ModifyEnvironmentInfoRequestBody body);

    /**
     * queryEnvironment
     *
     * @param projectId projectId
     * @param environmentId environmentId
     */
    Environment queryEnvironment(String projectId, String environmentId);

    /**
     * queryEnvironmentInstances
     *
     * @param projectId projectId
     * @param environmentId environmentId
     * @param queryEnvironmentInstancesQo queryEnvironmentInstancesQo
     */
    EnvironmentInstances queryEnvironmentInstances(String projectId, String environmentId,
        QueryEnvironmentInstancesQo queryEnvironmentInstancesQo);

    /**
     * queryEnvironmentVariables
     *
     * @param projectId projectId
     * @param queryEnvironmentVariablesQo queryEnvironmentVariablesQo
     */
    EnvironmentVariablesResp queryEnvironmentVariables(String projectId,
        QueryEnvironmentVariablesQo queryEnvironmentVariablesQo);

    /**
     * queryEnvironmentsList
     *
     * @param projectId projectId
     * @param queryEnvironmentsListQo queryEnvironmentsListQo
     */
    Environments queryEnvironmentsList(String projectId, QueryEnvironmentsListQo queryEnvironmentsListQo);

    /**
     * queryVpcs
     *
     * @param projectId projectId
     */
    List<VpcInfo> queryVpcs(String projectId);

    /**
     * queryVpcsSubnets
     *
     * @param projectId projectId
     * @param vpcId vpcId
     */
    ListSubnets queryVpcsSubnets(String projectId, String vpcId);

    /**
     * showEnvironmentVariables
     *
     * @param projectId projectId
     * @param environmentId environmentId
     * @param workspaceId workspaceId
     */
    EnvironmentVariables showEnvironmentVariables(String projectId, String environmentId, String workspaceId);
}