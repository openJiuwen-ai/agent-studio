/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.mcp.apigservice.apig;

import com.alibaba.fastjson.JSONObject;
import com.huaweicloud.sdk.apig.v2.model.ApiActionInfo;
import com.huaweicloud.sdk.apig.v2.model.ApiAuthCreate;
import com.huaweicloud.sdk.apig.v2.model.ApiAuthRelations;
import com.huaweicloud.sdk.apig.v2.model.ApiCreate;
import com.huaweicloud.sdk.apig.v2.model.ApiGroupCreate;
import com.huaweicloud.sdk.apig.v2.model.CreateApiGroupV2Response;
import com.huaweicloud.sdk.apig.v2.model.CreateApiV2Response;
import com.huaweicloud.sdk.apig.v2.model.DeleteApiV2Response;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.rce.client.ApigClient;
import com.openjiuwen.studio.agent.manager.service.mcp.apigservice.utils.JsonUtils;
import com.openjiuwen.studio.agent.manager.service.mcp.model.apig.ApigGroupResp;
import com.openjiuwen.studio.agent.manager.utils.IamServiceUtils;
import com.openjiuwen.studio.agent.manager.utils.McpServiceExceptionUtils;

import lombok.extern.slf4j.Slf4j;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;

/**
 * @ClassName : ApicApiService
 * @Description :专用于调用APIG API
 * @Date : Created in 2024/4/9 9:54
 * @Version : V1.0
 */
@Service
@Slf4j
public class ApigApiService {
    @Value("${op.svc.tenant-id:op_tenant_id}")
    private String tenantId;

    @Value("${op.svc.project-id:op_projectId}")
    private String projectId;

    @Value("${apig.op.instance_id:op_instance_id}")
    private String instanceId;

    // === 新增：PKI功能开关，默认关闭(false)，保证上环境不影响原有功能 ===
    @Value("${apig.auth.pki-enabled:false}")
    private boolean pkiEnabled;

    @Autowired
    private ApigRequestService apigRequestService;

    @Autowired
    private IamServiceUtils iamServiceUtils;

    @Autowired
    private ApigClient apigClient;

    private static final String SERVICE_NAME_APIG = "APIG";

    private void errorResponseThrow(ResponseEntity<String> response) {
        if (response.getStatusCode().value() >= 300) {
            log.error("Get apic response error!");
            try {
                JSONObject responseJsonObject = JSONObject.parseObject(response.getBody());
                if (responseJsonObject.get("error_code").equals("APIG.2015")) { // IP地址异常
                    throw new AgentStudioException(StudioError.INVALID_URL);
                }
            } catch (Exception e) {
                log.error("Failed to parse apic response body");
            }
            throw new AgentStudioException(StudioError.INVALID_URL);
        }
    }

    /**
     * 获取APIG认证Token
     * <p>
     * 受 apig.auth.pki-enabled 开关控制：
     * false (默认): 返回原始 OP Token (原有逻辑)
     * true: 使用 PKI 重新签发 Token (新架构逻辑)
     *
     * @return Token字符串，如果获取失败则返回 null
     */
    private String getApigAuthToken() {
        // 1. 获取基础 OP Token (无论新旧逻辑都需要)
        String currentToken = iamServiceUtils.getOpAccountAuthToken();

        return currentToken;
    }

    public CreateApiV2Response createApi(ApiCreate request) {
        ResponseEntity<CreateApiV2Response> resp;
        try {
            resp = apigClient.createApi(getApigAuthToken(), projectId, instanceId, request);
        } catch (Exception e) {
            log.error("Apig create api error,{}", e.getMessage());
            throw new AgentStudioException(StudioError.NO_CREATOR_PERMISSION);
        }
        return resp.getBody();
    }

    public ResponseEntity<DeleteApiV2Response> deleteApi(String apiId) {
        ResponseEntity<DeleteApiV2Response> resp;
        try {
            resp = apigClient.deleteApi(getApigAuthToken(), projectId, instanceId, apiId);
        } catch (Exception e) {
            log.error("Apig delete api error,{}", e.getMessage());
            throw new AgentStudioException(StudioError.API_DELETE_API_ERROR);
        }
        return resp;
    }

    public CreateApiGroupV2Response createApiGroup(ApiGroupCreate request) {
        ResponseEntity<CreateApiGroupV2Response> resp;
        try {
            resp = apigClient.createApiGroup(getApigAuthToken(), projectId, instanceId, request);
        } catch (Exception e) {
            log.error("Apig create api group error,{}", e.getMessage());
            throw new AgentStudioException(StudioError.API_KEY_CREATE_ERROR);
        }
        return resp.getBody();
    }

    public ApigGroupResp listApiGroup(String name) {
        ResponseEntity<ApigGroupResp> resp;
        try {
            resp = apigClient.listApiGroups(getApigAuthToken(), projectId, instanceId, name);
        } catch (Exception e) {
            McpServiceExceptionUtils.printException(log, e, "query APIG group fail");
            return null;
        }
        return resp.getBody();
    }

    /**
     * 发布或下线API
     *
     * @param request ApiActionInfo
     */
    public void publishOrOfflineApi(ApiActionInfo request) {
        String token = getApigAuthToken();
        try {
            apigClient.publishOrOfflineApi(token, projectId, instanceId, request);
        } catch (Exception e) {
            log.error("Apig publishOrOffline api group error,{}", e.getMessage());
            throw new AgentStudioException(StudioError.API_DELETE_API_ERROR);
        }
    }

    /**
     * 将APIG上的API与凭据进行绑定
     *
     * @param apiAuthCreate
     * @return ApiAuthRelations
     */
    public ApiAuthRelations apiBindCredentials(ApiAuthCreate apiAuthCreate) {
        ResponseEntity<String> response = apigClient.bindCredentials(getApigAuthToken(), projectId, instanceId,
            apiAuthCreate);
        errorResponseThrow(response);
        return JsonUtils.toObject(response.getBody(), ApiAuthRelations.class);
    }

}
